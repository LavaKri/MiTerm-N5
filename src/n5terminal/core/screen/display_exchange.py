"""Exchange point between the thread that feeds the screen model and the UI thread.

See "Buffers" in ``specs/robustness.md``. The feeding thread publishes the updates of the screen
model; the UI thread takes what accumulated every 50 to 100 ms. The fixed lines accumulate (all
delivered, within a limit); for the live part only the latest state of each row is kept, so the
intermediate states a slow UI never sees are skipped. The lock is held for a few assignments only:
the UI never waits for the emulation, and the emulation never waits for the UI.
"""

import threading
from collections import deque
from dataclasses import dataclass

from n5terminal.core.screen.screen_model import FixedLine, ScreenModel, ScreenRow, ScreenUpdate
from n5terminal.core.transport.transport import Stream

# Output fed to the model at once. The emulation is pure Python and competes with the UI thread for
# the GIL: bounded blocks let the UI run between two of them.
BLOCK_SIZE = 16 * 1024
# What the exchange keeps for a UI that does not come. The limit of the lines kept in the output
# area itself is a decision of its own (see ``specs/open-questions.md``).
DEFAULT_MAX_FIXED_LINES = 10_000


@dataclass(slots=True, frozen=True)
class DisplayBatch:
    """What the UI takes: everything published since its previous call, as one update.

    ``dropped_lines`` is the number of fixed lines lost because the UI did not come in time; they
    come before the first line of ``update.fixed``.
    """

    update: ScreenUpdate
    dropped_lines: int = 0


class DisplayExchange:
    """Merges the published updates until the UI takes them. Safe between two threads."""

    def __init__(self, max_fixed_lines: int = DEFAULT_MAX_FIXED_LINES) -> None:
        self._max_fixed_lines = max_fixed_lines
        self._lock = threading.Lock()
        self._fixed: deque[FixedLine] = deque()
        self._rows: dict[int, ScreenRow] = {}
        self._overflows: list[int] = []
        self._replace_all = False
        self._dropped = 0
        self._closing: tuple[FixedLine, ...] | None = None
        self._latest: ScreenUpdate | None = None
        self._screen: ScreenUpdate | None = None  # the latest that says something of the screen

    def publish(self, update: ScreenUpdate) -> None:
        """Add an update of the screen model to what the UI will take."""
        with self._lock:
            self._fixed.extend(update.fixed)
            surplus = len(self._fixed) - self._max_fixed_lines
            for _ in range(max(surplus, 0)):
                self._fixed.popleft()
            self._dropped += max(surplus, 0)
            if update.replace_all:
                self._rows.clear()
                self._replace_all = True
            for row in update.rows:
                self._rows[row.number] = row
            self._overflows.extend(update.overflows)
            if update.closing is not None:  # the latest word on the closing part is the one kept
                self._closing = update.closing
            if update.row_count > 0:  # an update of the closing part alone has no screen to tell
                self._screen = update
            self._latest = update

    def take(self) -> DisplayBatch | None:
        """Return what was published since the previous call, or ``None`` when nothing was."""
        with self._lock:
            latest = self._latest
            if latest is None:
                return None
            fixed, rows, overflows = self._fixed, self._rows, self._overflows
            replace_all, dropped, closing = self._replace_all, self._dropped, self._closing
            screen = self._screen or latest
            self._fixed, self._rows, self._overflows = deque(), {}, []
            self._replace_all, self._dropped, self._latest = False, 0, None
            self._closing, self._screen = None, None
        update = ScreenUpdate(
            fixed=tuple(fixed),
            rows=tuple(rows[number] for number in sorted(rows)),
            replace_all=replace_all,
            overflows=tuple(overflows),
            columns=screen.columns,
            row_count=screen.row_count,
            cursor_row=screen.cursor_row,
            cursor_column=screen.cursor_column,
            closing=closing,
        )
        return DisplayBatch(update, dropped)


class ScreenPump:
    """Feeds a screen model in bounded blocks and publishes each block's update.

    Called from the thread that reads the transport. ``resize`` may come from another thread: it
    waits for the block being fed, at most a few milliseconds.
    """

    def __init__(
        self, model: ScreenModel, exchange: DisplayExchange, block_size: int = BLOCK_SIZE
    ) -> None:
        self._model = model
        self._exchange = exchange
        self._block_size = block_size
        self._lock = threading.Lock()

    @property
    def application_cursor_keys(self) -> bool:
        """Did the program put the terminal in the application cursor keys mode? (Pipes: no.)"""
        return self._model.application_cursor_keys

    def feed(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
        """Give the output of the program to the model, block by block, with its stream."""
        for start in range(0, len(data), self._block_size):
            block = data[start : start + self._block_size]
            with self._lock:
                self._model.feed(block, stream)
                update = self._model.take_update()
            self._exchange.publish(update)

    def finish(self) -> None:
        """No more output will come: a model that holds something back lets it go."""
        with self._lock:
            self._model.finish()
            update = self._model.take_update()
        self._exchange.publish(update)

    def resize(self, columns: int, rows: int) -> None:
        """Resize the model; the UI gets the whole live part at its next take."""
        with self._lock:
            self._model.resize(columns, rows)
            update = self._model.take_update()
        self._exchange.publish(update)
