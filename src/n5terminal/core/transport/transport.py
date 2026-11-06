"""Contract between a session and the way it reaches a program.

Implemented by the local pipe transport now, by the ConPTY transport and an SSH transport later. See
"Transport" in ``specs/architecture/transport.md``: bytes, not text; data is pushed to a listener,
never read by blocking; local notions (folder, environment) stay in each transport's launch
settings.
"""

from enum import Enum
from typing import Protocol, runtime_checkable

from n5terminal.core.errors import TransportError


class TransportState(Enum):
    """Life cycle of a transport. Local transports go from connecting to connected at once."""

    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    CLOSED = "closed"
    FAILED = "failed"


class Stream(Enum):
    """Where received data comes from. Only transports with separate streams (pipes) use ERROR."""

    OUTPUT = "output"
    ERROR = "error"


class TransportListener(Protocol):
    """Receives what a transport does.

    Called from the transport's own threads, never from the UI thread: the receiver posts to the UI
    itself.

    Order: ``on_exit`` comes as soon as the program ends, possibly before the last ``on_data``
    (output still in the pipes, or written by a process the program left running). The CLOSED
    state comes last, once no more data can arrive. Between ``on_exit`` and CLOSED, ``write``
    is refused but ``close`` still stops what is left.
    """

    def on_state_changed(self, state: TransportState) -> None:
        """The transport has a new state."""
        ...

    def on_data(self, stream: Stream, data: bytes) -> None:
        """Data was received from the program."""
        ...

    def on_exit(self, exit_code: int | None) -> None:
        """The program ended; ``None`` when its exit code is not known."""
        ...


@runtime_checkable
class ProcessCounter(Protocol):
    """Optional: a transport that knows how many local processes its program makes.

    Only the local transports can; it is how a shell waiting at its prompt is told from a busy one
    (see ``core/session/shell_prompt.py``). A remote transport (SSH) does not have it.
    """

    def active_processes(self) -> int | None:
        """The program and everything it started that is alive; ``None`` when unknown."""
        ...


class TransportInteraction(Protocol):
    """What a remote transport asks the user (the contract of ``specs/architecture/transport.md``).

    Implemented by a presenter that opens a native, accessible dialog. The transport calls it from
    its own thread and waits for the answer; the implementation posts to the UI thread and never
    blocks it. The local transports never call it.
    """

    def confirm_host_key(self, text: str) -> bool:
        """Show the host key question of ``ssh``; ``True`` to trust the server and go on."""
        ...

    def ask_secret(self, question: str) -> str | None:
        """Ask for a password or a passphrase (the answer is hidden); ``None`` if cancelled."""
        ...

    def withdraw(self) -> None:
        """Close the dialog still open: its question is no longer waiting for an answer."""
        ...


@runtime_checkable
class ConnectionReport(Protocol):
    """Optional: how a remote connection ended, once the state is CLOSED or FAILED."""

    @property
    def failure(self) -> TransportError | None:
        """Why the connection could not be made, ``None`` when there is no error to announce."""
        ...

    @property
    def cancelled(self) -> bool:
        """Did the user cancel a dialog? It is not an error: the connection just does not go on."""
        ...


class Transport(Protocol):
    """A way to reach one program."""

    @property
    def state(self) -> TransportState:
        """The current state."""
        ...

    def start(self, listener: TransportListener) -> None:
        """Start the program (or the connection) and report to ``listener``."""
        ...

    def write(self, data: bytes) -> None:
        """Send data to the program's input. Raise ``TransportClosedError`` when not connected."""
        ...

    def resize(self, columns: int, rows: int) -> None:
        """Tell the program the size of the screen; does nothing when the transport has none."""
        ...

    def close(self) -> None:
        """Stop the program (or the connection). Does nothing when already closed."""
        ...
