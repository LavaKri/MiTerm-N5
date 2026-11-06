"""Reading a line of the output with its formatting (Terminal > Activities > Read the line).

The window gives the line of the caret; this says what the analysis of the line makes of it: the
element (``Download, 60 %``), or the line without its decor. It changes neither the caret nor the
focus. See "Reading a line" in ``specs/interface.md``.
"""

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.screen.line_analysis import read_line
from n5terminal.core.session.session_state import Mode
from n5terminal.i18n import _


class LineReader:
    """Says a line as the analysis reads it."""

    def __init__(self, say: Say) -> None:
        self._say = say

    def read(self, line: str, mode: Mode, *, cursor_on_text: bool = False) -> None:
        """Say ``line``; with pipes ``> `` marks a line sent by the user, not a selected item.

        ``cursor_on_text``: the terminal cursor is inside the text of the line (a list item).
        """
        text = read_line(
            line, selection_marks=mode is not Mode.PIPES, cursor_on_text=cursor_on_text
        )
        self._say(Announce.LINE_READ, text=text or _("blank"), line=line.strip() or _("blank"))
