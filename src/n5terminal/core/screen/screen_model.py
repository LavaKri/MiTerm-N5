"""Contract of the terminal screen model: what a terminal shows for the bytes a program wrote.

The model receives the bytes of a terminal transport (VT sequences included) and hands out what the
output area needs: the lines that left the screen (the fixed part, which only grows) and the rows of
the screen (the live part, replaced by the changed rows). See "Terminal display" in
``specs/interface.md`` and "Language strategy" in ``specs/architecture/stack.md``.

The data crossing the contract are plain (strings, numbers, booleans), never objects of the library
behind it, so that another implementation (a native module) can take the place of the pyte one and
pass the same contract tests.
"""

from dataclasses import dataclass
from typing import Protocol

from n5terminal.core.transport.transport import Stream


@dataclass(slots=True, frozen=True)
class FixedLine:
    """A line that left the screen and will not change any more.

    ``continued`` is true when the program did not end the line: the terminal wrapped it at the
    screen width, and the text goes on in the next line.
    """

    text: str
    continued: bool = False


@dataclass(slots=True, frozen=True)
class ScreenRow:
    """A row of the screen, numbered from 0 at the top. ``continued`` as in :class:`FixedLine`."""

    number: int
    text: str
    continued: bool = False


@dataclass(slots=True, frozen=True)
class ScreenUpdate:
    """What changed since the previous update.

    - ``fixed``: the lines that left the screen, in order, to append to the fixed part.
    - ``rows``: the rows of the live part that changed. When ``replace_all`` is true, it holds every
      row of the screen (first update, resize, clearing, or most rows changed) and the live part is
      replaced as a block.
    - ``overflows``: for each line the program wrote longer than the screen and then ended, the
      number of characters beyond the screen width (input of the automatic size).
    - ``cursor_row`` and ``cursor_column``: the cursor, from 0; the column may be ``columns`` when
      the last column is full and the next character will wrap.
    - ``closing``: the lines of the closing part, after the live part (the end of a connection);
      ``None`` leaves it as it is, an empty tuple empties it. Only the session writes it, with a
      ``row_count`` of 0: such an update says nothing of the live part (its cursor stays).

    Trailing blanks of a text are removed.
    """

    fixed: tuple[FixedLine, ...]
    rows: tuple[ScreenRow, ...]
    replace_all: bool
    overflows: tuple[int, ...]
    columns: int
    row_count: int
    cursor_row: int
    cursor_column: int
    closing: tuple[FixedLine, ...] | None = None


class ScreenModel(Protocol):
    """A virtual terminal screen. One instance serves one session and one thread only."""

    @property
    def columns(self) -> int:
        """The width of the screen."""
        ...

    @property
    def row_count(self) -> int:
        """The height of the screen."""
        ...

    @property
    def application_cursor_keys(self) -> bool:
        """Did the program ask for the cursor keys in application mode (DECCKM)?

        The arrows, Home and End are then sent as ``ESC O A`` and not ``ESC [ A``. Always false for
        a model that has no terminal (pipes).
        """
        ...

    def feed(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
        """Give the model bytes of the program's output (UTF-8, VT sequences included).

        The model keeps what it needs between calls: a character or a sequence can be split between
        two calls. ``stream`` says which stream of the transport the bytes come from; a model that
        has one stream (a terminal) takes them all the same, one that tells them apart (pipes)
        keeps them apart.
        """
        ...

    def finish(self) -> None:
        """No more output will come: let go of what the model holds back.

        Does nothing for a model that holds nothing back. Called once, after the last ``feed``;
        ``take_update`` still hands out what this released.
        """
        ...

    def resize(self, columns: int, rows: int) -> None:
        """Change the size of the screen; the next update replaces the whole live part."""
        ...

    def take_update(self) -> ScreenUpdate:
        """Return what changed since the previous call, and forget it."""
        ...
