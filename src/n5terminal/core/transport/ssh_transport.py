"""SSH transport: the ``ssh.exe`` of Windows in a pseudo console, with the states of a connection.

See "How a connection is made" in ``specs/architecture/connection.md``. The pseudo console is a
:class:`ConPtyTransport`; this class adds what a connection needs on top of it:

- the pipe of the askpass program, created *before* ``ssh`` starts, which says when a question must
  be asked (``authenticating``) and when the connection is made (``connected``);
- the dialogs, through the ``TransportInteraction`` the presenter gives;
- the end: ``closed`` with the exit code, or ``failed`` with the error ``ssh`` ended with (before
  ``connected`` only, see ``classify_ssh_end``). A dialog the user cancelled is not an error.

The signal ``connected`` is the only one: ``ssh`` ignores a failing ``LocalCommand`` (measured), and
a connection by key makes no call that could stand for it, so nothing is guessed from the time or
the output. A session that ends without it is logged. Nothing a question holds goes to a log.
"""

import logging
import os
import threading
from collections.abc import Mapping
from pathlib import Path

from n5terminal.askpass import EVENT_CONNECTED
from n5terminal.core.errors import (
    AskpassNotFoundError,
    SshConnectionError,
    TransportClosedError,
    TransportError,
)
from n5terminal.core.transport.askpass_server import (
    REFUSED,
    AskpassReply,
    AskpassRequest,
    AskpassServer,
)
from n5terminal.core.transport.conpty_transport import (
    DEFAULT_COLUMNS,
    DEFAULT_ROWS,
    ConPtyLaunch,
    ConPtyTransport,
)
from n5terminal.core.transport.ssh_errors import classify_ssh_end
from n5terminal.core.transport.ssh_launch import SshLaunch
from n5terminal.core.transport.ssh_questions import QuestionKind, question_kind
from n5terminal.core.transport.transport import (
    Stream,
    TransportInteraction,
    TransportListener,
    TransportState,
)

logger = logging.getLogger(__name__)

TAIL_SIZE = 8192  # bytes of output kept to tell, at the end, why ``ssh`` stopped


class SshTransport:
    """Runs ``ssh`` for one connection; its single stream carries the VT sequences of the server."""

    def __init__(
        self,
        launch: SshLaunch,
        interaction: TransportInteraction,
        working_folder: Path,
        environment: Mapping[str, str] | None = None,
        size: tuple[int, int] = (DEFAULT_COLUMNS, DEFAULT_ROWS),
    ) -> None:
        self._launch = launch
        self._interaction = interaction
        self._folder = working_folder
        self._environment = dict(os.environ if environment is None else environment)
        self._size = size  # columns and rows of the pseudo console
        self._lock = threading.RLock()  # the listener is called under it, to keep the order
        self._state = TransportState.CLOSED
        self._listener: TransportListener | None = None
        self._inner: ConPtyTransport | None = None
        self._server: AskpassServer | None = None
        self._asking = False  # a dialog is open
        self._cancelled = False  # the user cancelled a dialog: nothing else is asked
        self._closing = False  # the user asked to close the connection
        self._failure: SshConnectionError | None = None
        self._exit_code: int | None = None
        self._tail = bytearray()

    @property
    def state(self) -> TransportState:
        with self._lock:
            return self._state

    @property
    def failure(self) -> SshConnectionError | None:
        """The error ``ssh`` ended with, once the state is FAILED."""
        with self._lock:
            return self._failure

    @property
    def cancelled(self) -> bool:
        """Did the user cancel a dialog (a refused host key, a password not given)?"""
        with self._lock:
            return self._cancelled

    def start(self, listener: TransportListener) -> None:
        """Create the pipe, then start ``ssh``; raises a ``TransportError`` if it cannot be done.

        ``AskpassNotFoundError`` if the askpass program is missing, ``NamedPipeError`` if the pipe
        cannot be created, ``ProgramNotFoundError`` if ``ssh.exe`` is missing.
        """
        if self._listener is not None:
            raise TransportError("already started")
        self._listener = listener
        self._set_state(TransportState.CONNECTING)
        try:
            self._open()
        except TransportError:
            self._stop_server()
            self._set_state(TransportState.FAILED)
            raise

    def write(self, data: bytes) -> None:
        """Send typed input to the server; refused until the connection is made."""
        inner = self._inner
        if self.state is not TransportState.CONNECTED or inner is None:
            raise TransportClosedError
        inner.write(data)

    def resize(self, columns: int, rows: int) -> None:
        inner = self._inner
        if inner is not None:
            inner.resize(columns, rows)

    def close(self) -> None:
        """Close the connection: ``ssh`` is stopped, and a dialog still open is withdrawn."""
        with self._lock:
            self._closing = True
            asking = self._asking
        if asking:
            self._interaction.withdraw()
        if self._inner is not None:
            self._inner.close()

    # Starting ------------------------------------------------------------------------------

    def _open(self) -> None:
        launch = self._launch
        if not launch.askpass_program.is_file():
            raise AskpassNotFoundError(str(launch.askpass_program))
        server = AskpassServer(launch.pipe_name, launch.token, _Handler(self))
        server.start()
        self._server = server
        columns, rows = self._size
        inner = ConPtyTransport(
            ConPtyLaunch(
                launch.arguments(),
                self._folder,
                launch.environment(self._environment),
                columns,
                rows,
            )
        )
        self._inner = inner
        inner.start(_InnerListener(self))

    def _stop_server(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.close()

    # The askpass program -------------------------------------------------------------------

    def _handle(self, request: AskpassRequest) -> AskpassReply:
        if request.event == EVENT_CONNECTED:
            with self._lock:
                self._advance(TransportState.CONNECTED)
            return AskpassReply(ok=True)
        return self._ask(request.text)

    def _ask(self, text: str) -> AskpassReply:
        with self._lock:
            if self._cancelled or self._closing:
                return REFUSED
            stale = self._asking  # a question is still open: the program that asked it is gone
            if stale:
                self._cancelled = True
            else:
                self._asking = True
                self._advance(TransportState.AUTHENTICATING)
        if stale:
            self._interaction.withdraw()
            return REFUSED
        try:
            reply = self._ask_user(text)
        finally:
            with self._lock:
                self._asking = False
        if reply.refused:
            with self._lock:
                self._cancelled = True
        return reply

    def _ask_user(self, text: str) -> AskpassReply:
        if question_kind(text) is QuestionKind.HOST_KEY:
            trusted = self._interaction.confirm_host_key(text)
            return AskpassReply(answer="yes") if trusted else REFUSED
        secret = self._interaction.ask_secret(text)
        return REFUSED if secret is None else AskpassReply(answer=secret)

    def _reply_lost(self) -> None:
        """The askpass program gave up waiting (its limit): the user's answer is of no use."""
        with self._lock:
            self._cancelled = True

    # What the pseudo console reports -------------------------------------------------------

    def _on_data(self, stream: Stream, data: bytes) -> None:
        with self._lock:
            if self._state is not TransportState.CONNECTED:
                self._tail.extend(data)
                del self._tail[:-TAIL_SIZE]
        self._require_listener().on_data(stream, data)

    def _on_exit(self, exit_code: int | None) -> None:
        with self._lock:
            self._exit_code = exit_code
            asking = self._asking
            if asking:  # ssh is gone while a question is open: it was not answered in time
                self._cancelled = True
        if asking:
            self._interaction.withdraw()
        self._require_listener().on_exit(exit_code)

    def _on_closed(self) -> None:
        """``ssh`` ended and its last output was handed out: the pipe goes, the state is final."""
        self._stop_server()
        with self._lock:
            final = TransportState.CLOSED
            if self._state is not TransportState.CONNECTED:
                output = bytes(self._tail).decode("utf-8", errors="replace")
                failure = classify_ssh_end(output, self._exit_code, self._cancelled)
                if failure is not None:
                    self._failure = failure
                    final = TransportState.FAILED
                elif self._exit_code == 0 and not self._cancelled:
                    logger.warning("ssh ended without having said the connection was made")
            self._set_state_locked(final)

    # The states ----------------------------------------------------------------------------

    def _advance(self, state: TransportState) -> None:
        """Move forward to AUTHENTICATING or CONNECTED, never back (the lock is held)."""
        order = (
            TransportState.CONNECTING,
            TransportState.AUTHENTICATING,
            TransportState.CONNECTED,
        )
        if self._state in order and order.index(state) > order.index(self._state):
            self._set_state_locked(state)

    def _set_state(self, state: TransportState) -> None:
        with self._lock:
            self._set_state_locked(state)

    def _set_state_locked(self, state: TransportState) -> None:
        self._state = state
        self._require_listener().on_state_changed(state)

    def _require_listener(self) -> TransportListener:
        if self._listener is None:
            raise TransportError("not started")
        return self._listener


class _Handler:
    """What the pipe asks of the transport (see ``AskpassHandler``)."""

    def __init__(self, transport: SshTransport) -> None:
        self._transport = transport

    def handle(self, request: AskpassRequest) -> AskpassReply:
        return self._transport._handle(request)

    def reply_lost(self, request: AskpassRequest) -> None:
        self._transport._reply_lost()


class _InnerListener:
    """What the pseudo console reports, handed to the transport; its own states do not count."""

    def __init__(self, transport: SshTransport) -> None:
        self._transport = transport

    def on_state_changed(self, state: TransportState) -> None:
        if state is TransportState.CLOSED:
            self._transport._on_closed()

    def on_data(self, stream: Stream, data: bytes) -> None:
        self._transport._on_data(stream, data)

    def on_exit(self, exit_code: int | None) -> None:
        self._transport._on_exit(exit_code)
