"""A transport listener that records what it receives, safe to call from several threads."""

import threading

from n5terminal.core.transport.transport import Stream, TransportState

WAIT_TIMEOUT = 10.0


class RecordingListener:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.states: list[TransportState] = []
        self.chunks: list[tuple[Stream, bytes]] = []
        self.exit_codes: list[int | None] = []
        self.exited = threading.Event()
        self.closed = threading.Event()

    def on_state_changed(self, state: TransportState) -> None:
        with self._lock:
            self.states.append(state)
        if state in (TransportState.CLOSED, TransportState.FAILED):
            self.closed.set()

    def on_data(self, stream: Stream, data: bytes) -> None:
        with self._lock:
            self.chunks.append((stream, data))

    def on_exit(self, exit_code: int | None) -> None:
        with self._lock:
            self.exit_codes.append(exit_code)
        self.exited.set()

    def received(self, stream: Stream) -> bytes:
        with self._lock:
            return b"".join(data for source, data in self.chunks if source is stream)

    def wait_closed(self) -> None:
        assert self.closed.wait(WAIT_TIMEOUT), "the transport did not close in time"
