"""The line filters: how a line of the output is read for comfort (line filtering).

See "Comfortable reading" in ``specs/interface.md``. A filter is a regular expression searched in
the whole line, with a replacement: what is said instead of the text it finds (nothing, a word such
as the name of a server, or a part of the text through the groups of the expression). The filters
are tried in the order of the list and **the first that finds something is the only one applied**:
no replacement follows another, so the result is the same wherever it is computed. Nothing here
changes the output: only what is announced. The start list is made of the default prompts of the
shells (a filter that starts with ``^`` finds its text at the start of the line only); they also
accept a ``# `` in front of the prompt (the prefix of the prompt of a profile), but never need it:
a title of a text that starts with ``#`` is not taken for a prompt, since the filter also asks for
the shape of the prompt itself.
"""

import re
from dataclasses import dataclass, replace

from n5terminal.i18n import N_, _

#: What the filters of the start list allow in front of a prompt: the prefix of the profile.
_PREFIX = r"(?:#+ )?"
#: An environment in front of a prompt of a server: ``(venv) ``.
_ENVIRONMENT = r"(?:\([^)\r\n]*\) )?"
#: The end of a prompt: a space, or the end of the line when nothing was typed after it (the text
#: of the output does not keep the space that ends a line).
_END = r"(?: |$)"


@dataclass(slots=True, frozen=True)
class PromptPattern:
    """A named regular expression searched in a line, and what replaces what it finds.

    ``replacement`` is a template as ``re.sub`` takes it: text, with ``\\1`` or ``\\g<name>`` for
    a group of the expression. Empty: what is found is left out and nothing takes its place.
    """

    name: str
    pattern: str
    replacement: str = ""


@dataclass(slots=True, frozen=True)
class Filtered:
    """A line cut by the filter that found something: what comes before, what is said in place of
    what was found, and what comes after."""

    before: str
    replacement: str
    after: str

    @property
    def text(self) -> str:
        """The three parts one after the other, a space between those that are not empty."""
        parts = (self.before.strip(), self.replacement.strip(), self.after.strip())
        return " ".join(part for part in parts if part)


#: The start list: the default prompts of Cmd, PowerShell, bash and zsh. The replacement of each is
#: a message id (``start_patterns`` translates it): the word said in place of the prompt.
START_PATTERNS = (
    PromptPattern("Cmd", "^" + _PREFIX + r'[A-Za-z]:\\[^<>:"|?*\r\n]*>', N_("Command")),
    PromptPattern("PowerShell", "^" + _PREFIX + r"PS [^\r\n>]*>" + _END, N_("Command")),
    PromptPattern("PowerShell >>", "^" + _PREFIX + r">>" + _END, N_("Continuation")),
    PromptPattern(
        "bash",
        "^" + _PREFIX + _ENVIRONMENT + r"[\w.\-]+@[\w.\-]+:[^\r\n$#]*[$#]" + _END,
        N_("Command"),
    ),
    PromptPattern(
        "zsh",
        "^" + _PREFIX + _ENVIRONMENT + r"[\w.\-]+@[\w.\-]+ [^\r\n%#]*[%#]" + _END,
        N_("Command"),
    ),
)


def start_patterns() -> list[PromptPattern]:
    """The start list, with its words in the language now in use."""
    return [replace(item, replacement=_(item.replacement)) for item in START_PATTERNS]


def _previous_patterns() -> dict[str, str]:
    """The filters the start list had before, each with the one that replaced it.

    First the filters that matched only at the start of the line (they had no ``^``), then those
    from before the end of a prompt could be the end of the line. A saved list that holds one of
    them as it was gets the current one: the user did not write it.
    """
    found = {item.pattern.removeprefix("^"): item.pattern for item in START_PATTERNS}
    found[_PREFIX + r"PS [^\r\n>]*> "] = START_PATTERNS[1].pattern
    found[_PREFIX + r">> "] = START_PATTERNS[2].pattern
    found[_PREFIX + _ENVIRONMENT + r"[\w.\-]+@[\w.\-]+:[^\r\n$#]*[$#] "] = START_PATTERNS[3].pattern
    found[_PREFIX + _ENVIRONMENT + r"[\w.\-]+@[\w.\-]+ [^\r\n%#]*[%#] "] = START_PATTERNS[4].pattern
    return found


_PREVIOUS_PATTERNS = _previous_patterns()


def current_pattern(pattern: str) -> str:
    """``pattern``, or the pattern of the start list that replaced it."""
    return _PREVIOUS_PATTERNS.get(pattern, pattern)


def pattern_problem(pattern: str, replacement: str = "") -> str | None:
    """Why ``pattern`` (or its ``replacement``) is not valid (the error, in English), else None.

    ``"empty"`` is returned for a pattern with nothing in it.
    """
    if not pattern.strip():
        return "empty"
    try:
        compiled = re.compile(pattern)
        compiled.sub(replacement, "")  # a replacement that names a group the pattern lacks
    except (re.error, IndexError) as error:
        return str(error)
    return None


def filter_line(line: str, patterns: list[PromptPattern]) -> Filtered | None:
    """``line`` cut by the first filter that finds something in it, and by that one only.

    ``None`` when no filter finds anything. A filter that is not valid is skipped, and so is one
    that finds nothing (an empty match); a replacement that cannot be filled says nothing.
    """
    for candidate in patterns:
        try:
            found = re.search(candidate.pattern, line)
        except re.error:
            continue
        if found is None or found.end() == found.start():
            continue
        try:
            spoken = found.expand(candidate.replacement)
        except re.error, IndexError:
            spoken = ""
        return Filtered(line[: found.start()], spoken, line[found.end() :])
    return None


def as_read(line: str, patterns: list[PromptPattern]) -> str:
    """``line`` as the line filtering says it; the line as it is when no filter finds anything."""
    filtered = filter_line(line, patterns)
    return line if filtered is None else filtered.text
