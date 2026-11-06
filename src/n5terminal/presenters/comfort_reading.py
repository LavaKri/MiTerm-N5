"""Comfortable reading: a line of the output said with the line filters applied.

See "Comfortable reading" in ``specs/interface.md``. The window moves the caret to the line before
or after and gives that line; this says it as the first filter that finds something in it makes it
(the text found is left out, or replaced by the word of the filter), and, if the settings ask for
it, with the formatting that the Read the line key adds. The output itself is never changed: the
arrows still read the truth.
"""

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.config.prompt_patterns import PromptPattern, filter_line
from n5terminal.core.config.settings import Settings
from n5terminal.core.screen.line_analysis import read_line
from n5terminal.core.session.session_state import Mode
from n5terminal.i18n import _


def comfort_text(line: str, patterns: list[PromptPattern]) -> str:
    """``line`` as the line filtering says it, without the formatting; ``blank`` when nothing is
    left."""
    filtered = filter_line(line, patterns)
    text = line if filtered is None else filtered.text
    return text.strip() or _("blank")


class ComfortReader:
    """Says a line with the filters applied."""

    def __init__(self, say: Say, settings: Settings) -> None:
        self._say = say
        self._settings = settings

    def read(self, line: str, mode: Mode) -> None:
        """Say ``line`` as the filters make it; an empty one as blank.

        ``mode`` tells whether ``> `` marks a line sent by the user (pipes) or a selected item, as
        for the Read the line key.
        """
        plain = comfort_text(line, self._settings.patterns())
        text = plain
        if self._settings.comfort_formatting and plain != _("blank"):
            text = read_line(plain, selection_marks=mode is not Mode.PIPES) or plain
        self._say(Announce.COMFORT_LINE, text=text, line=plain)
