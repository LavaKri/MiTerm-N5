"""The application's end of the askpass pipe: one short exchange per call of the askpass program.

See "The askpass program" in ``specs/architecture/connection.md``. The program (``askpass.py``)
sends one line of JSON, ``{"token", "event", "text"}``, and reads one line back: ``{"answer"}``,
``{"ok"}`` or ``{"refused"}``. A request with a wrong token is refused before the handler hears of
it. A line that is not that is dropped: the connection is closed with no reply, which the program
takes as "the application cannot be reached".

The handler may take as long as the user does to answer (a dialog): each connection has its own
thread, so a pending question does not stop the pipe from being served. What the requests say (a
password) never goes to a log.
"""

import contextlib
import hmac
import io
import json
import logging
import threading
from dataclasses import dataclass
from typing import Protocol

from n5terminal.askpass import EVENT_ASK, EVENT_CONNECTED
from n5terminal.core.errors import NamedPipeError, TransportError
from n5terminal.core.transport.named_pipe import (
    PIPE_PREFIX,
    PipeConnection,
    PipeInstance,
    current_user_sid,
    security_descriptor_text,
)

logger = logging.getLogger(__name__)

_EVENTS = (EVENT_ASK, EVENT_CONNECTED)


@dataclass(slots=True, frozen=True)
class AskpassRequest:
    """What the askpass program sent: a question to ask the user, or "the connection is made"."""

    event: str
    text: str


@dataclass(slots=True, frozen=True)
class AskpassReply:
    """What goes back: an answer to a question, or an acknowledgement, or a refusal."""

    answer: str | None = None
    ok: bool = False
    refused: bool = False

    def to_data(self) -> dict[str, object]:
        if self.refused:
            return {"refused": True}
        if self.answer is not None:
            return {"answer": self.answer}
        return {"ok": self.ok}


REFUSED = AskpassReply(refused=True)


class AskpassHandler(Protocol):
    """What the server asks of the transport."""

    def handle(self, request: AskpassRequest) -> AskpassReply:
        """The reply to a request; may wait for the user."""
        ...

    def reply_lost(self, request: AskpassRequest) -> None:
        """The program was gone when the reply came (it gave up waiting): the answer is dropped."""
        ...


def parse_request(line: bytes, token: str) -> tuple[AskpassRequest, bool] | None:
    """The request in a line and whether its token is the right one; ``None`` if not a request."""
    if not line.endswith(b"\n"):  # also a line that hit the size limit, or an empty one
        return None
    try:
        data = json.loads(line.decode("utf-8"))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    sent, event, text = data.get("token"), data.get("event"), data.get("text")
    if not isinstance(sent, str) or event not in _EVENTS or not isinstance(text, str):
        return None
    right = hmac.compare_digest(sent.encode("utf-8"), token.encode("utf-8"))
    return AskpassRequest(event, text), right


class AskpassServer:
    """Serves the pipe ``pipe_name`` to the askpass program, until :meth:`close`."""

    def __init__(
        self,
        pipe_name: str,
        token: str,
        handler: AskpassHandler,
        security_descriptor: str | None = None,
    ) -> None:
        if not pipe_name.startswith(PIPE_PREFIX):
            raise NamedPipeError("name", 0)
        self._name = pipe_name
        self._token = token
        self._handler = handler
        self._descriptor = security_descriptor
        self._next: PipeInstance | None = None
        self._lock = threading.Lock()
        self._active: set[PipeConnection] = set()
        self._closing = False

    def start(self) -> None:
        """Create the pipe (so that it exists before ``ssh`` is started) and serve it.

        Raises ``NamedPipeError`` if the name is already in use or the pipe cannot be created.
        """
        descriptor = self._descriptor or security_descriptor_text(current_user_sid())
        self._descriptor = descriptor
        self._next = PipeInstance(self._name, first=True, security_descriptor=descriptor)
        threading.Thread(target=self._serve, name="askpass-pipe", daemon=True).start()

    def close(self) -> None:
        """Stop serving: the calls in progress are cut, and the pipe goes away."""
        with self._lock:
            self._closing = True
            active = list(self._active)
        for connection in active:
            connection.cancel()
        # The thread is waiting for a client: be that client once, so that it wakes and ends.
        with contextlib.suppress(OSError), io.FileIO(self._name, "r+"):
            pass

    def _serve(self) -> None:
        while True:
            instance, self._next = self._next, None
            if instance is None:
                return
            try:
                connection = instance.wait_for_client()
            except NamedPipeError:
                logger.exception("The askpass pipe stopped being served")
                instance.close()
                return
            if self._closing:
                connection.close()
                return
            self._prepare_next_instance()
            with self._lock:
                self._active.add(connection)
            threading.Thread(
                target=self._serve_one, args=(connection,), name="askpass-call", daemon=True
            ).start()

    def _prepare_next_instance(self) -> None:
        """Another instance waits at once: the name is never free for someone else to take."""
        try:
            self._next = PipeInstance(
                self._name, first=False, security_descriptor=self._descriptor or ""
            )
        except NamedPipeError:
            logger.exception("The askpass pipe cannot take another call")

    def _serve_one(self, connection: PipeConnection) -> None:
        request: AskpassRequest | None = None
        try:
            parsed = parse_request(connection.readline(), self._token)
            if parsed is None:
                logger.debug("Askpass call dropped: not a request")
                return
            request, right = parsed
            logger.debug("Askpass call: %s", request.event)  # never its text
            reply = self._handler.handle(request) if right else REFUSED
            connection.write(json.dumps(reply.to_data()).encode("utf-8") + b"\n")
        except OSError:
            logger.debug("Askpass call cut", exc_info=True)
            if request is not None:
                self._report_lost(request)
        finally:
            with self._lock:
                self._active.discard(connection)
            with contextlib.suppress(OSError):
                connection.close()

    def _report_lost(self, request: AskpassRequest) -> None:
        try:
            self._handler.reply_lost(request)
        except TransportError:
            logger.exception("The loss of a reply could not be handled")
