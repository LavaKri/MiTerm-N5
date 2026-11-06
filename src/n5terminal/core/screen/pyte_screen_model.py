"""The terminal screen model, built on pyte.

pyte does the emulation. Two things are ours: the journal of the lines that leave the screen (pyte's
``HistoryScreen`` drops old lines silently and wraps every event), and the mark on the rows the
terminal wrapped itself (``continued``), told apart from the lines the program ended. Nothing of
pyte crosses the :class:`~n5terminal.core.screen.screen_model.ScreenModel` contract.
"""

import codecs

import pyte
from pyte.screens import Margins

from n5terminal.core.screen.screen_model import FixedLine, ScreenRow, ScreenUpdate
from n5terminal.core.transport.transport import Stream

# The texts of the rows are the same objects for as long as nothing changes, so a row is compared
# with what was delivered before as a pair (text, continued).
_RowState = tuple[str, bool]


DECCKM = 1 << 5  # cursor keys mode: private mode 1, shifted as pyte stores the private modes


class _TerminalScreen(pyte.Screen):
    """A pyte screen keeping the lines that scroll off the top and the rows it wrapped."""

    def __init__(self, columns: int, lines: int) -> None:
        self.left: list[FixedLine] = []  # lines that left the screen, not handed out yet
        self.overflows: list[int] = []  # excess of the wrapped lines that ended, not handed out yet
        # Rows wrapped while drawing, with the width at which they wrapped: the mark outlives a
        # widening of the screen. It may be stale, see ``row_continued``.
        self._continued: dict[int, int] = {}
        self._drawing = False  # inside ``draw``, where pyte itself wraps with CR + LF
        self._wraps = 0  # wraps since the current line started
        super().__init__(columns, lines)

    def row_text(self, y: int) -> str:
        # A wide character leaves an empty stub in the next cell, so the cells join as they read.
        row = self.buffer[y]
        return "".join(row[x].data for x in range(self.columns)).rstrip()

    def row_continued(self, y: int) -> bool:
        # A row erased or overwritten after its wrap has a blank cell where it wrapped (its last
        # cell at that time): its mark is stale.
        width = self._continued.get(y)
        return width is not None and bool(self.buffer[y][width - 1].data.strip())

    def row_state(self, y: int) -> _RowState:
        return self.row_text(y), self.row_continued(y)

    def draw(self, data: str) -> None:
        self._drawing = True
        try:
            super().draw(data)
        finally:
            self._drawing = False

    def linefeed(self) -> None:
        if self._drawing:
            self._continued[self.cursor.y] = self.columns
            self._wraps += 1
        else:
            self._end_line()
            if self._continued.pop(self.cursor.y, None) is not None:
                self.dirty.add(self.cursor.y)
        super().linefeed()

    def index(self) -> None:
        top, bottom = self.margins or Margins(0, self.lines - 1)
        if self.cursor.y == bottom:
            if top == 0:
                self.left.append(FixedLine(self.row_text(0), self.row_continued(0)))
            self._continued = {
                (y - 1 if top < y <= bottom else y): width
                for y, width in self._continued.items()
                if y != top
            }
        super().index()

    def reverse_index(self) -> None:
        self._end_line()
        top, bottom = self.margins or Margins(0, self.lines - 1)
        if self.cursor.y == top:
            self._continued = {
                (y + 1 if top <= y < bottom else y): width
                for y, width in self._continued.items()
                if y != bottom
            }
        super().reverse_index()

    def carriage_return(self) -> None:
        self._end_line()
        super().carriage_return()

    def cursor_position(self, line: int | None = None, column: int | None = None) -> None:
        self._end_line()
        super().cursor_position(line, column)

    def cursor_up(self, count: int | None = None) -> None:
        self._end_line()
        super().cursor_up(count)

    def cursor_down(self, count: int | None = None) -> None:
        self._end_line()
        super().cursor_down(count)

    def insert_lines(self, count: int | None = None) -> None:
        self._forget_continued_from(self.cursor.y)
        super().insert_lines(count)

    def delete_lines(self, count: int | None = None) -> None:
        self._forget_continued_from(self.cursor.y)
        super().delete_lines(count)

    def resize(self, lines: int | None = None, columns: int | None = None) -> None:
        if columns and columns != self.columns:
            self._wraps = 0  # the line being written is measured against another width
        super().resize(lines, columns)

    def reset(self) -> None:
        self._wraps = 0
        self._continued.clear()
        super().reset()

    def _end_line(self) -> None:
        """The program leaves the line it was writing: report how far past the screen it went."""
        if self._drawing:
            return
        if self._wraps:
            self.overflows.append((self._wraps - 1) * self.columns + self.cursor.x)
            self._wraps = 0

    def _forget_continued_from(self, row: int) -> None:
        self._continued = {y: width for y, width in self._continued.items() if y < row}
        self.dirty.update(range(row, self.lines))


class PyteScreenModel:
    """:class:`~n5terminal.core.screen.screen_model.ScreenModel` implemented with pyte."""

    def __init__(self, columns: int = 80, rows: int = 24) -> None:
        self._screen = _TerminalScreen(columns, rows)
        self._stream = pyte.Stream(self._screen)
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._shown: dict[int, _RowState] = {}  # the rows as last handed out
        self._replace_all = True
        # The last screen that had text: a program that erases the screen as it ends (a full-screen
        # program leaving) would otherwise take its last view away, see ``finish``.
        self._last_view: list[FixedLine] = []

    @property
    def application_cursor_keys(self) -> bool:
        """Did the program ask for the cursor keys in application mode (DECCKM)?"""
        return DECCKM in self._screen.mode

    @property
    def columns(self) -> int:
        return int(self._screen.columns)

    @property
    def row_count(self) -> int:
        return int(self._screen.lines)

    def feed(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
        """A terminal has one stream: ``stream`` makes no difference."""
        self._stream.feed(self._decoder.decode(data))

    def resize(self, columns: int, rows: int) -> None:
        self._screen.resize(lines=rows, columns=columns)
        self._replace_all = True

    def _remember_view(self) -> None:
        """Keep the screen as last handed out when it has text, down to its last line with text."""
        rows = [self._shown[y] for y in range(self.row_count) if y in self._shown]
        last = max((i for i, (text, _continued) in enumerate(rows) if text), default=None)
        if last is not None:
            self._last_view = [FixedLine(text, continued) for text, continued in rows[: last + 1]]

    def finish(self) -> None:
        """The program ended: if it left an empty screen, its last view goes to the fixed part.

        A program that erases the screen as it leaves (a full-screen one restoring the terminal)
        would take its last view away: no line scrolled off, so nothing of it was kept. Programs
        that leave text on the screen are not touched.
        """
        if self._last_view and not any(text for text, _continued in self._shown.values()):
            self._screen.left.extend(self._last_view)
        self._last_view = []

    def take_update(self) -> ScreenUpdate:
        screen = self._screen
        row_count = self.row_count
        fixed = tuple(screen.left)
        overflows = tuple(screen.overflows)
        screen.left.clear()
        screen.overflows.clear()
        if self._replace_all:
            candidates = list(range(row_count))
        else:
            candidates = sorted(y for y in screen.dirty if y < row_count)
        screen.dirty.clear()
        current = {y: screen.row_state(y) for y in candidates}
        changed = [y for y in candidates if self._shown.get(y) != current[y]]
        replace_all = self._replace_all or len(changed) * 2 > row_count
        self._shown.update({y: current[y] for y in changed})
        if changed:
            self._remember_view()
        self._replace_all = False
        if replace_all:
            changed = list(range(row_count))
        rows = tuple(ScreenRow(y, *self._shown[y]) for y in changed)
        return ScreenUpdate(
            fixed=fixed,
            rows=rows,
            replace_all=replace_all,
            overflows=overflows,
            columns=self.columns,
            row_count=row_count,
            cursor_row=int(screen.cursor.y),
            cursor_column=int(screen.cursor.x),
        )
