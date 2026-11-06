"""The dialogs ``ssh`` opens through a connection: its host key, its password.

Layout and wiring only (the texts and the rules are in ``presenters/connection_session.py`` and
``presenters/session_info.py``). Each control has an accessible name and is created right after its
label; the title says which connection asks and the first line where it goes. The host key is
a read-only text the user reads (the fingerprint is on its second line), Cancel is the default
button; the secret is typed in a hidden field. Either can be closed from outside
(``withdraw``), as a cancel, when its question is no longer waiting for an answer.
"""

import wx

from n5terminal.i18n import _
from n5terminal.ui.feedback import Feedback


class HostKeyDialog(wx.Dialog):
    """The question of ``ssh`` about a server it does not know. ``wx.ID_YES`` trusts it."""

    def __init__(self, parent: wx.Window, title: str, where: str, text: str) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        where_label = wx.StaticText(self, label=where)
        self.text = wx.TextCtrl(
            self,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            name=_("Host key"),
        )
        self.trust = wx.Button(self, wx.ID_YES, _("Trust and continue"))
        self.cancel = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(self.trust, 0, wx.RIGHT, 8)
        buttons.Add(self.cancel, 0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(where_label, 0, wx.ALL, 8)
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(620, 320))
        self.trust.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_YES))
        self.SetEscapeId(wx.ID_CANCEL)
        self.cancel.SetDefault()  # Enter does not trust a server by accident
        self.text.SetFocus()  # reading starts here


class SecretDialog(wx.Dialog):
    """A question for a password, a passphrase or a code, answered in a hidden field."""

    def __init__(self, parent: wx.Window, title: str, where: str, question: str) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        where_label = wx.StaticText(self, label=where)
        instruction = wx.StaticText(
            self, label=_("Type the password or the answer the server asks for; it stays hidden.")
        )
        label = wx.StaticText(self, label=question.strip())
        self.secret = wx.TextCtrl(
            self, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, name=question.strip() or _("Secret")
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(where_label, 0, wx.ALL, 8)
        sizer.Add(instruction, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.secret, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(460, self.GetSize().GetHeight()))
        self.SetSize(wx.Size(460, self.GetSize().GetHeight()))
        self.secret.Bind(wx.EVT_TEXT_ENTER, lambda _event: self.EndModal(wx.ID_OK))
        self.secret.SetFocus()


class ConnectionPrompts:
    """Implements ``DialogView``: opens the dialog, answers, closes it on request."""

    def __init__(self, frame: wx.Frame, feedback: Feedback) -> None:
        self._frame = frame
        self._feedback = feedback
        self._open: wx.Dialog | None = None

    def confirm_host_key(self, title: str, where: str, text: str) -> bool:
        with HostKeyDialog(self._frame, title, where, text) as dialog:
            return bool(self._run(dialog) == wx.ID_YES)

    def ask_secret(self, title: str, where: str, question: str) -> str | None:
        with SecretDialog(self._frame, title, where, question) as dialog:
            if self._run(dialog) != wx.ID_OK:
                return None
            return str(dialog.secret.GetValue())

    def withdraw(self) -> None:
        """Close the dialog still open, as a cancel (its question is not waiting any more)."""
        dialog = self._open
        if dialog is not None and dialog.IsModal():
            dialog.EndModal(wx.ID_CANCEL)

    def _run(self, dialog: wx.Dialog) -> int:
        self._open = dialog
        try:
            return self._feedback.modal(dialog)
        finally:
            self._open = None
