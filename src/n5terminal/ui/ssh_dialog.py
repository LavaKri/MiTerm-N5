"""The dialog "OpenSSH client": a :class:`ProgramDialog` with its words.

The options and their rules are in ``presenters/ssh_choice.py``. It says which ``ssh.exe`` is used
and that only the OpenSSH of Windows was tried.
"""

import wx

from n5terminal.i18n import _
from n5terminal.presenters.ssh_choice import SshChoice
from n5terminal.ui.program_dialog import ProgramDialog


class SshDialog(ProgramDialog):
    """Edit a :class:`SshChoice`. ``commit`` hands the controls to it."""

    def __init__(self, parent: wx.Window, draft: SshChoice) -> None:
        super().__init__(
            parent,
            draft,
            _("OpenSSH client"),
            _("ssh.exe used"),
            _("ssh.exe path"),
            note=draft.note,
        )
