"""The box of Find in the output: the text to search and the direction, layout and wiring only.

See "Search in the output" in ``specs/interface.md``. The field has an accessible name and is
created right after its label; Enter is OK and Escape is Cancel; the focus starts in the field, the
last text searched selected. The check box "Search upwards" only belongs to this box: Find next and
Find previous keep their own direction. "Regular expression" makes the text a regular expression;
one that is not valid is refused here, with the reason, and the box stays open.
"""

import wx

from n5terminal.core.screen.text_search import regex_problem
from n5terminal.i18n import _


class FindDialog(wx.Dialog):
    """``wx.ID_OK`` to search ``term`` from the caret, upwards if ``upwards`` is checked."""

    def __init__(
        self, parent: wx.Window, title: str, term: str, upwards: bool, regex: bool
    ) -> None:
        super().__init__(parent, title=title)
        label = wx.StaticText(self, label=_("Text to search"))
        self.text = wx.TextCtrl(self, value=term, name=_("Text to search"))
        self.upwards = wx.CheckBox(self, label=_("Search upwards"), name=_("Search upwards"))
        self.upwards.SetValue(upwards)
        self.regex = wx.CheckBox(self, label=_("Regular expression"), name=_("Regular expression"))
        self.regex.SetValue(regex)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.text, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.upwards, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.regex, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(420, self.GetSize().GetHeight()))
        self.SetSize(wx.Size(420, self.GetSize().GetHeight()))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.text.SelectAll()
        self.text.SetFocus()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """OK unless the text is a regular expression that is not valid: say why and stay."""
        problem = regex_problem(self.term()) if self.use_regex() else None
        if problem is None:
            event.Skip()
            return
        message = _("The regular expression is not valid: {error}").format(error=problem)
        with wx.MessageDialog(self, message, _("Search refused"), wx.OK | wx.ICON_WARNING) as box:
            box.ShowModal()
        self.text.SetFocus()

    def term(self) -> str:
        """The text now in the field."""
        return str(self.text.GetValue())

    def search_upwards(self) -> bool:
        """Is the check box of the direction checked?"""
        return bool(self.upwards.GetValue())

    def use_regex(self) -> bool:
        """Is the text a regular expression?"""
        return bool(self.regex.GetValue())
