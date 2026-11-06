"""A transport driven by the test: no process, no thread, no network.

It plays any scenario a real transport can produce (states, data, exit, failure), so presenters are
tested without a program; SSH-like states (authenticating) included.
"""

from n5terminal.core.errors import TransportClosedError, TransportError
from n5terminal.core.transport.transport import Stream, TransportListener, TransportState


class FakeTransport:
    def __init__(self) -> None:
        self.state = TransportState.CLOSED
        self.listener: TransportListener | None = None
        self.written: list[bytes] = []
        self.sizes: list[tuple[int, int]] = []
        self.closed = False
        self.start_error: Exception | None = None  # raised by ``start``, as a real launch can
        self.process_count: int | None = 1  # what ``active_processes`` answers
        # The states ``start`` goes through; a test of a connection may stop before CONNECTED.
        self.start_states: tuple[TransportState, ...] = (
            TransportState.CONNECTING,
            TransportState.CONNECTED,
        )
        # What a remote transport tells of how it ended (``ConnectionReport``).
        self.failure: TransportError | None = None
        self.cancelled = False

    def start(self, listener: TransportListener) -> None:
        if self.start_error is not None:
            raise self.start_error
        self.listener = listener
        for state in self.start_states:
            self.set_state(state)

    def write(self, data: bytes) -> None:
        if self.state is not TransportState.CONNECTED:
            raise TransportClosedError
        self.written.append(data)

    def resize(self, columns: int, rows: int) -> None:
        self.sizes.append((columns, rows))

    def active_processes(self) -> int | None:
        return self.process_count

    def close(self) -> None:
        self.closed = True

    # What the test drives.

    def set_state(self, state: TransportState) -> None:
        self.state = state
        self._listener().on_state_changed(state)

    def receive(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
        self._listener().on_data(stream, data)

    def exit(self, exit_code: int | None) -> None:
        self._listener().on_exit(exit_code)
        self.set_state(TransportState.CLOSED)

    def _listener(self) -> TransportListener:
        assert self.listener is not None, "start the transport first"
        return self.listener
