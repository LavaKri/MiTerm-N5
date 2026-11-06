"""Contract of the filter applied to the output of a program before it is displayed.

The output of a program is untrusted text. The filter removes what could distort the display or
what the screen reader says (control characters, escape sequences, text direction marks). What it
removes and how is data (:class:`FilterRules`), so the policy can change without touching the code
that applies it. See ``specs/robustness.md``.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class CarriageReturnPolicy(Enum):
    """What a carriage return not followed by a line feed means."""

    REPLACE_LINE = "replace_line"  # a progress bar: only the last state of the line is kept
    NEW_LINE = "new_line"  # every carriage return starts a new line


class RemovedAction(Enum):
    """What replaces a removed character."""

    DROP = "drop"  # nothing
    MARK = "mark"  # `FilterRules.mark`


# Control characters kept as they are: tab and line feed.
DEFAULT_KEPT = frozenset({"\t", "\n"})


@dataclass(slots=True, frozen=True)
class FilterRules:
    """The policy of the filter. The defaults are the ones decided in ``specs/robustness.md``."""

    kept: frozenset[str] = DEFAULT_KEPT
    carriage_return: CarriageReturnPolicy = CarriageReturnPolicy.REPLACE_LINE
    strip_escape_sequences: bool = True
    strip_c1_controls: bool = True
    strip_direction_marks: bool = True
    strip_zero_width: bool = True
    on_removed: RemovedAction = RemovedAction.DROP
    mark: str = field(default="\N{REPLACEMENT CHARACTER}", repr=False)


@dataclass(slots=True, frozen=True)
class FilteredChunk:
    """A piece of filtered text.

    ``replaces_current_line`` is true when the text replaces the unfinished last line of the output
    instead of being appended (a carriage return in the source, see
    :attr:`CarriageReturnPolicy.REPLACE_LINE`).
    """

    text: str
    replaces_current_line: bool = False


class OutputFilter(Protocol):
    """Filters the decoded output of a program, piece by piece.

    The filter keeps a state between calls, since a sequence or a carriage return can be split
    between two pieces of text. One instance serves one stream of one session.
    """

    def feed(self, text: str) -> list[FilteredChunk]:
        """Filter a piece of decoded text and return what can be displayed now."""
        ...

    def finish(self) -> list[FilteredChunk]:
        """Return what is still held back (end of the stream); an unfinished sequence is dropped."""
        ...
