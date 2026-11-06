"""The multi-line input: a box of text for a block of several lines, sent with its one button.

See "Multi-line input" in ``specs/interface.md``. Layout and wiring only. The text field has an
accessible name and is created right after its label; Enter makes a new line, Tab goes to the
Send button, and Escape closes the box without sending (the caller keeps what was typed). The
focus starts in the text, the caret at its end.
"""

import wx

from n5terminal.i18n import _


class MultilineDialog(wx.Dialog):
    """``wx.ID_OK`` when the Send button was used, ``wx.ID_CANCEL`` for Escape."""

    def __init__(self, parent: wx.Window, text: str) -> None:
        super().__init__(
            parent, title=_("Multi-line input"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        label = wx.StaticText(self, label=_("Lines to send"))
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE, name=_("Lines to send"))
        self.send = wx.Button(self, wx.ID_ANY, _("Send"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 8)
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.send, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(640, 360))
        self.send.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_OK))
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.text.SetFocus()
        self.text.SetInsertionPointEnd()

    def value(self) -> str:
        """The lines now in the text field."""
        return str(self.text.GetValue())

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
