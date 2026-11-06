"""Finding a word in the text of the output (see "Search" in ``specs/interface.md``).

Offsets are Python string indexes. The case is ignored; every occurrence counts, even when two
overlap. Nothing wraps around: past the last occurrence there is none. The term is plain text, or
a regular expression when ``regex`` is true (an occurrence that is empty does not count).
"""

import re


def regex_problem(term: str) -> str | None:
    """Why ``term`` is not a regular expression (the error, in English), ``None`` if it is."""
    try:
        re.compile(term)
    except re.error as error:
        return str(error)
    return None


def _pattern(term: str, regex: bool) -> re.Pattern[str]:
    """A pattern that matches *at* each start of ``term`` (a look-ahead, so overlaps count)."""
    body = term if regex else re.escape(term)
    return re.compile(f"(?=({body}))", re.IGNORECASE)


def find_next(text: str, term: str, start: int, *, regex: bool = False) -> int | None:
    """The index of the first occurrence of ``term`` that begins at or after ``start``."""
    if not term:
        return None
    for match in _pattern(term, regex).finditer(text, max(start, 0)):
        if match.group(1):
            return match.start()
    return None


def find_previous(text: str, term: str, before: int, *, regex: bool = False) -> int | None:
    """The index of the last occurrence of ``term`` that begins strictly before ``before``."""
    if not term or before <= 0:
        return None
    # The look-ahead must see the whole term of an occurrence that begins just before ``before``;
    # the length of a regular expression is not known, so it may look to the end of the text.
    end = len(text) if regex else min(len(text), before - 1 + len(term))
    found = None
    for match in _pattern(term, regex).finditer(text, 0, end):
        if match.start() >= before:
            break
        if match.group(1):
            found = match.start()
    return found


def cursor_is_on_line_text(text: str, line_index: int, cursor_index: int) -> bool:
    """Is the terminal cursor inside the text of the line that holds ``line_index``?

    Behind the text (after a prompt, at the end of what is typed) it is not: there the cursor waits
    for an answer. Inside it, on a line among others, it marks the item chosen in a list.
    """
    start = text.rfind("\n", 0, line_index) + 1
    if text.rfind("\n", 0, cursor_index) + 1 != start:
        return False
    return 0 <= cursor_index - start < len(line_at(text, line_index).rstrip())


def neighbour_line(text: str, index: int, *, forward: bool) -> int | None:
    """The index of the start of the line after (or before) the one that holds ``index``.

    ``None`` when there is none: the line is the last (or the first) of ``text``.
    """
    if forward:
        end = text.find("\n", index)
        return None if end == -1 else end + 1
    start = text.rfind("\n", 0, index) + 1
    return None if start == 0 else text.rfind("\n", 0, start - 1) + 1


def line_at(text: str, index: int) -> str:
    """The line of ``text`` that holds the character at ``index``, without its line break."""
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return text[start : end if end != -1 else len(text)]
