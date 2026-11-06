"""Searching the output (Find, Find next, Find previous).

The window gives the text of the output and the caret; this remembers the word searched, finds the
occurrence, says it through the announcement center and returns where the caret goes. See "Search"
in ``specs/interface.md``.
"""

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.screen.text_search import find_next, find_previous, line_at, regex_problem


class OutputSearch:
    """The word searched, kept for the session, and the search itself."""

    def __init__(self, say: Say) -> None:
        self._say = say
        self.term = ""
        # The last choices of the box of Find, kept until the application ends; the other keys keep
        # their own direction, and use the same kind of term.
        self.upwards = False
        self.regex = False

    def start(
        self, term: str, text: str, caret: int, *, upwards: bool = False, regex: bool = False
    ) -> int | None:
        """Search ``term`` from the caret: forward (an occurrence at the caret counts), or upwards
        (the first occurrence before the caret). ``term`` is a regular expression if ``regex``;
        one that is not valid is said and searches nothing."""
        problem = regex_problem(term) if regex else None
        if problem is not None:
            self._say(Announce.SEARCH_BAD_EXPRESSION, error=problem)
            return None
        self.term = term
        self.upwards = upwards
        self.regex = regex
        if upwards:
            found = find_previous(text, term, caret, regex=regex)
            return self._report(found, backwards=True, text=text)
        return self._report(find_next(text, term, caret, regex=regex), backwards=False, text=text)

    def next(self, text: str, caret: int) -> int | None:
        """The next occurrence of the word searched, after the caret."""
        return self._report(
            find_next(text, self.term, caret + 1, regex=self.regex),
            backwards=False,
            text=text,
        )

    def previous(self, text: str, caret: int) -> int | None:
        """The previous occurrence of the word searched, before the caret."""
        return self._report(
            find_previous(text, self.term, caret, regex=self.regex),
            backwards=True,
            text=text,
        )

    def _report(self, index: int | None, *, backwards: bool, text: str) -> int | None:
        if index is None:
            missing = Announce.SEARCH_NO_PREVIOUS if backwards else Announce.SEARCH_NO_NEXT
            self._say(missing, term=self.term)
            return None
        self._say(Announce.SEARCH_FOUND, line=line_at(text, index), term=self.term)
        return index
