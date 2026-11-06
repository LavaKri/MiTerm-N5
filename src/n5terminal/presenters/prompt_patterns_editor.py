"""The draft of the dialog of the prompt patterns (Terminal > Comfortable reading > Prompts).

See "Comfortable reading" in ``specs/interface.md``. The dialog edits this draft; the settings
take it when the dialog is accepted. The order of the list is the order the patterns are tried in.
"""

from n5terminal.core.config.prompt_patterns import (
    PromptPattern,
    pattern_problem,
    start_patterns,
)
from n5terminal.i18n import N_
from n5terminal.presenters.choices import Translate
from n5terminal.presenters.comfort_reading import comfort_text

NAME_EMPTY = N_("The name cannot be empty.")
PATTERN_EMPTY = N_("The pattern cannot be empty.")
PATTERN_INVALID = N_("The pattern is not a valid regular expression: {error}")
NAME_TAKEN = N_("Another filter already has this name.")


class PromptPatternsEditor:
    """The list of patterns and the choice of the formatting, as the dialog changes them."""

    def __init__(
        self,
        patterns: list[PromptPattern],
        formatting: bool,
        titles: bool,
        translate: Translate,
    ) -> None:
        self._translate = translate
        self.patterns = list(patterns)
        self.formatting = formatting
        self.titles = titles

    def names(self) -> list[str]:
        """The names, in the order the patterns are tried."""
        return [item.name for item in self.patterns]

    def problem(
        self, name: str, pattern: str, replacement: str = "", replacing: int | None = None
    ) -> str | None:
        """Why ``name`` and ``pattern`` cannot be a pattern (in words), ``None`` if they can.

        ``replacing`` is the index of the pattern being edited, whose own name is not taken.
        """
        if not name.strip():
            return self._translate(NAME_EMPTY)
        taken = {item.name.casefold() for i, item in enumerate(self.patterns) if i != replacing}
        if name.strip().casefold() in taken:
            return self._translate(NAME_TAKEN)
        reason = pattern_problem(pattern, replacement)
        if reason == "empty":
            return self._translate(PATTERN_EMPTY)
        if reason is not None:
            return self._translate(PATTERN_INVALID).format(error=reason)
        return None

    def add(self, name: str, pattern: str, replacement: str = "") -> int | None:
        """Add a pattern at the end; its index, ``None`` if refused (see ``problem``)."""
        if self.problem(name, pattern, replacement) is not None:
            return None
        self.patterns.append(PromptPattern(name.strip(), pattern, replacement))
        return len(self.patterns) - 1

    def replace(self, index: int, name: str, pattern: str, replacement: str = "") -> bool:
        """Change the pattern at ``index``; whether it was (refused or no such line: ``False``)."""
        if (
            not 0 <= index < len(self.patterns)
            or self.problem(name, pattern, replacement, index) is not None
        ):
            return False
        self.patterns[index] = PromptPattern(name.strip(), pattern, replacement)
        return True

    def remove(self, index: int) -> int | None:
        """Remove the pattern at ``index``; the index to select afterwards, ``None`` if none."""
        if not 0 <= index < len(self.patterns):
            return None
        del self.patterns[index]
        return min(index, len(self.patterns) - 1) if self.patterns else None

    def move(self, index: int, step: int) -> int:
        """Move the pattern at ``index`` up (``-1``) or down (``1``); its index afterwards."""
        target = index + step
        if not 0 <= index < len(self.patterns) or not 0 <= target < len(self.patterns):
            return index
        self.patterns[index], self.patterns[target] = self.patterns[target], self.patterns[index]
        return target

    def restore_start_patterns(self) -> None:
        """Put back the patterns the application starts with, and keep the others.

        A pattern of the start list that is in the list (found by its name) is set back to what
        it was, in its place; one that was removed is added at the end. The patterns the user
        added are not touched.
        """
        places = {item.name: index for index, item in enumerate(self.patterns)}
        for item in start_patterns():
            if item.name in places:
                self.patterns[places[item.name]] = item
            else:
                self.patterns.append(item)

    def sample(self, pattern: str, replacement: str, line: str) -> str:
        """The line as it would be announced with this pattern alone, nothing more (the trial of
        the edit box): the line itself when the pattern does not find a prompt in it."""
        if not line or pattern_problem(pattern, replacement) is not None:
            return ""
        return comfort_text(line, [PromptPattern("", pattern, replacement)])
