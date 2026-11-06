"""The dialog "PowerShell selection": a :class:`ProgramDialog` with its words.

The options and their rules are in ``presenters/powershell_choice.py``.
"""

import wx

from n5terminal.i18n import _
from n5terminal.presenters.powershell_choice import PowerShellChoice
from n5terminal.ui.program_dialog import ProgramDialog


class PowerShellDialog(ProgramDialog):
    """Edit a :class:`PowerShellChoice`. ``commit`` hands the controls to it."""

    def __init__(self, parent: wx.Window, draft: PowerShellChoice) -> None:
        super().__init__(
            parent,
            draft,
            _("PowerShell selection"),
            _("PowerShell version"),
            _("PowerShell path"),
        )
