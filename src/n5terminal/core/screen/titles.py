"""Titles of the output (Markdown headings) and the move from one to another.

A command launched in CLI mode is written ``# command``, a title of level 1; the programs' own
Markdown gives more (see "Titles" in ``specs/interface.md``). The keys 1 to 6 go to a title of that
level, T to any title, Shift backwards.

Offsets here are Python string indexes of a text that uses ``\\n`` as line break. A Windows text
field counts a character outside the basic plane as two units: ``to_utf16`` and ``from_utf16``
convert.
"""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

from markdown_it import MarkdownIt

_PARSER = MarkdownIt("commonmark")


@dataclass(slots=True, frozen=True)
class Title:
    """A title: its level (1 to 6), its text without the ``#``, and the line it lies on."""

    level: int
    text: str
    start: int  # first character of the line
    end: int  # end of its last line, without the line break


def parse_titles(text: str) -> list[Title]:
    """The titles of ``text`` (``#`` and underlined; code blocks are ignored), in order."""
    line_starts = [0]
    line_starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    tokens = _PARSER.parse(text)
    titles: list[Title] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        first_line, after_last_line = token.map
        start = line_starts[first_line]
        end = line_starts[after_last_line] - 1 if after_last_line < len(line_starts) else len(text)
        titles.append(
            Title(int(token.tag[1:]), tokens[index + 1].content.strip(), start, max(start, end))
        )
    return titles


def next_title(titles: list[Title], position: int, level: int | None = None) -> Title | None:
    """The first title (of ``level`` if given) that starts after ``position``."""
    starts = [title.start for title in titles]
    for title in titles[bisect_right(starts, position) :]:
        if level is None or title.level == level:
            return title
    return None


def previous_title(titles: list[Title], position: int, level: int | None = None) -> Title | None:
    """The last title (of ``level`` if given) that starts before ``position``."""
    starts = [title.start for title in titles]
    for title in reversed(titles[: bisect_left(starts, position)]):
        if level is None or title.level == level:
            return title
    return None


def to_utf16(text: str, index: int) -> int:
    """The position, in UTF-16 units, of the string index ``index``."""
    return len(text[:index].encode("utf-16-le", errors="surrogatepass")) // 2


def from_utf16(text: str, position: int) -> int:
    """The string index of the UTF-16 position ``position``.

    A position in the middle of a pair of units gives the index of that character.
    """
    units = 0
    for index, char in enumerate(text):
        if units >= position:
            return index
        units += 2 if ord(char) > 0xFFFF else 1
        if units > position:
            return index
    return len(text)
