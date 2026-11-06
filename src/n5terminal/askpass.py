"""The program ``ssh`` runs to ask the user something, and to say that it is connected.

See "The askpass program" in ``specs/architecture/connection.md``. ``ssh`` starts it for each
question (``SSH_ASKPASS``, with the text of the question as its only argument) and, once the
connection is made, with ``--connected`` (``LocalCommand``). It passes the request to the
application through a named pipe, and gives the answer to ``ssh`` on its standard output.

It is started again for every question, so it imports nothing but the standard library: not
``wx``, not the rest of the package. The text it receives (a password, a passphrase) is never
written to a log, a file or the error output.

The exit code is what ``ssh`` sees: 0 for an answer (or the acknowledgement of ``--connected``),
1 when the user refused, 2 when the application cannot be reached or does not understand.
"""

import contextlib
import ctypes
import errno
import io
import json
import os
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import BinaryIO, Protocol

PIPE_VARIABLE = "N5_ASKPASS_PIPE"  # the full name of the pipe: \\.\pipe\n5terminal-askpass-<random>
TOKEN_VARIABLE = "N5_ASKPASS_TOKEN"  # a random value only this run of the application knows
CONNECTED_ARGUMENT = "--connected"

EXIT_ANSWERED = 0
EXIT_REFUSED = 1
EXIT_UNREACHABLE = 2

EVENT_ASK = "ask"
EVENT_CONNECTED = "connected"

#: How long the program waits for the application, so that it never holds ``ssh`` for good.
#: ``ssh`` waits for ``LocalCommand`` before it opens the shell (measured), so ``--connected`` is
#: short; a question waits for the user, who may take a while to find a password.
ASK_LIMIT = 120.0
CONNECTED_LIMIT = 5.0
BUSY_TRIES = 6  # the pipe has no free instance for a moment between two calls
BUSY_WAIT_MS = 100


class Pipe(Protocol):
    """The client end of the pipe, as the exchange uses it."""

    def write(self, data: bytes, /) -> object: ...

    def readline(self) -> bytes: ...

    def close(self) -> None: ...


PipeOpener = Callable[[str], Pipe]
#: Starts a timer that ends the program with ``EXIT_UNREACHABLE``; returns what stops the timer.
Watchdog = Callable[[float], Callable[[], None]]


class AskpassError(Exception):
    """The application cannot be reached, or its reply cannot be understood."""


def open_pipe(path: str) -> Pipe:
    """The client end of the named pipe ``path``, to read and write bytes without a buffer.

    The application creates the next instance of the pipe as soon as one is taken, but for that
    moment Windows says the pipe is busy: try again a few times before giving up.
    """
    for _ in range(BUSY_TRIES - 1):
        try:
            return io.FileIO(path, "r+")
        except OSError as error:
            if error.errno != errno.EINVAL:  # how ``FileIO`` reports ERROR_PIPE_BUSY
                raise
            wait_for_instance(path, BUSY_WAIT_MS)
    return io.FileIO(path, "r+")


def wait_for_instance(path: str, milliseconds: int) -> None:
    """Wait until the pipe has a free instance (``WaitNamedPipe``), at most ``milliseconds``."""
    windll = getattr(ctypes, "windll", None)
    if windll is None or not windll.kernel32.WaitNamedPipeW(path, milliseconds):
        time.sleep(milliseconds / 1000)  # no such call, or it gave up: let the other end catch up


def start_watchdog(seconds: float) -> Callable[[], None]:
    """End the program with ``EXIT_UNREACHABLE`` after ``seconds``, unless the result stops it."""
    timer = threading.Timer(seconds, os._exit, args=(EXIT_UNREACHABLE,))
    timer.daemon = True
    timer.start()
    return timer.cancel


def request_for(arguments: Sequence[str], token: str) -> dict[str, object]:
    """The request to send for the arguments ``ssh`` gave: ``--connected``, or a question."""
    if list(arguments) == [CONNECTED_ARGUMENT]:
        return {"token": token, "event": EVENT_CONNECTED, "text": ""}
    return {"token": token, "event": EVENT_ASK, "text": " ".join(arguments)}


def exchange(path: str, request: Mapping[str, object], opener: PipeOpener) -> dict[str, object]:
    """Send ``request`` as one line of JSON, and return the JSON line the application answers.

    Raises ``AskpassError`` if the pipe cannot be opened or the reply is missing or malformed.
    """
    line = json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n"
    try:
        pipe = opener(path)
    except OSError as error:
        raise AskpassError("the application cannot be reached") from error
    try:
        with contextlib.closing(pipe):
            pipe.write(line)
            reply = pipe.readline()
    except OSError as error:
        raise AskpassError("the exchange with the application failed") from error
    try:
        answer = json.loads(reply.decode("utf-8"))
    except ValueError as error:  # also an empty reply: the application closed the pipe
        raise AskpassError("the reply of the application cannot be understood") from error
    if not isinstance(answer, dict):
        raise AskpassError("the reply of the application is not an object")
    return answer


def run(
    arguments: Sequence[str],
    environ: Mapping[str, str],
    stdout: BinaryIO,
    opener: PipeOpener = open_pipe,
    watchdog: Watchdog = start_watchdog,
) -> int:
    """Do what ``ssh`` asked and return the exit code; ``stdout`` receives the answer."""
    path = environ.get(PIPE_VARIABLE, "")
    token = environ.get(TOKEN_VARIABLE, "")
    if not path or not token or not arguments:
        return EXIT_UNREACHABLE
    request = request_for(arguments, token)
    stop = watchdog(CONNECTED_LIMIT if request["event"] == EVENT_CONNECTED else ASK_LIMIT)
    try:
        answer = exchange(path, request, opener)
    except AskpassError:
        return EXIT_UNREACHABLE
    finally:
        stop()
    if answer.get("refused") is True:
        return EXIT_REFUSED
    if request["event"] == EVENT_CONNECTED:
        return EXIT_ANSWERED if answer.get("ok") is True else EXIT_UNREACHABLE
    text = answer.get("answer")
    if not isinstance(text, str):
        return EXIT_UNREACHABLE
    stdout.write(text.encode("utf-8") + b"\n")
    stdout.flush()
    return EXIT_ANSWERED


def main() -> int:
    """The entry point of ``n5terminal-askpass``."""
    return run(sys.argv[1:], os.environ, sys.stdout.buffer)


if __name__ == "__main__":
    sys.exit(main())
