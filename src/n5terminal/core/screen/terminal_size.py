"""Sizes of the terminal and the automatic size, which only grows.

See "Terminal size" in ``specs/interface.md``: the user picks a standard size or the automatic
mode, which starts at 120 x 30 (the default size of Windows Terminal) and grows one standard size
at a time when lines are clearly too long for the screen. The values here are a start, to adjust
with use.
"""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TerminalSize:
    columns: int
    rows: int


STANDARD_SIZES = (
    TerminalSize(80, 24),
    TerminalSize(100, 30),
    TerminalSize(120, 30),
    TerminalSize(132, 43),
    TerminalSize(160, 50),
    TerminalSize(200, 60),
)
DEFAULT_SIZE = TerminalSize(120, 30)  # where the automatic size starts


def size_text(size: TerminalSize) -> str:
    """The size as the settings write it (``80x24``)."""
    return f"{size.columns}x{size.rows}"


def size_from_text(text: str) -> TerminalSize | None:
    """The standard size written ``text`` in the settings; ``None`` for the automatic size."""
    return next((size for size in STANDARD_SIZES if size_text(size) == text), None)


# One or two characters too many may be a display mistake of the program.
SMALL_EXCESS = 2  # more than this, seen SMALL_EXCESS_COUNT times, makes the screen grow
SMALL_EXCESS_COUNT = 2
LARGE_EXCESS = 10  # more than this, once, makes the screen grow


class SizeChoice:
    """The size the user asked for: a standard size, or the automatic one (starts at 120 x 30)."""

    def __init__(self) -> None:
        self._automatic: AutoSizePolicy | None = AutoSizePolicy()
        self._fixed = DEFAULT_SIZE

    @property
    def size(self) -> TerminalSize:
        """The size to give to the next terminal."""
        return self._automatic.size if self._automatic is not None else self._fixed

    @property
    def is_automatic(self) -> bool:
        return self._automatic is not None

    def choose(self, size: TerminalSize | None, current: TerminalSize) -> None:
        """Choose ``size``, or the automatic size (``None``), which goes on from ``current``."""
        if size is None:
            self._automatic = AutoSizePolicy(current)
        else:
            self._automatic = None
            self._fixed = size

    def observe(self, overflows: Iterable[int]) -> TerminalSize | None:
        """The larger size to move to after these overflows; always ``None`` for a chosen size."""
        return self._automatic.observe(overflows) if self._automatic is not None else None


class AutoSizePolicy:
    """Decides when the automatic size grows, from the excess of the lines that wrapped.

    The excess of a line is the number of characters beyond the screen width (``overflows`` of a
    :class:`~n5terminal.core.screen.screen_model.ScreenUpdate`).
    """

    def __init__(self, size: TerminalSize = DEFAULT_SIZE) -> None:
        self._size = size
        self._small_seen = 0

    @property
    def size(self) -> TerminalSize:
        return self._size

    def observe(self, overflows: Iterable[int]) -> TerminalSize | None:
        """Take the excess of the lines that wrapped; return the new size when it must grow.

        The screen grows by one standard size at most for each call. Nothing is returned when the
        screen is already the largest.
        """
        grow = False
        for excess in overflows:
            if excess > LARGE_EXCESS:
                grow = True
            elif excess > SMALL_EXCESS:
                self._small_seen += 1
                grow = grow or self._small_seen >= SMALL_EXCESS_COUNT
        if not grow:
            return None
        larger = next((size for size in STANDARD_SIZES if size.columns > self._size.columns), None)
        if larger is not None:
            self._size = larger
            self._small_seen = 0
        return larger
