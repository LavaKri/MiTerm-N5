"""The list of the elements recognized in the output, with a button to copy the one selected.

Layout and wiring only. The label of the list is created right before it; Enter on a line is OK,
Escape is Cancel; the focus starts in the list. The button works for every line.
"""

from collections.abc import Callable

import wx

from n5terminal.i18n import _


class ElementsDialog(wx.Dialog):
    """A list of lines to pick one from; "Copy to the clipboard" hands the index to ``copy``."""

    def __init__(
        self,
        parent: wx.Window,
        title: str,
        prompt: str,
        labels: list[str],
        selected: int,
        copy: Callable[[int], None],
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._copy = copy
        label = wx.StaticText(self, label=prompt)
        self.list = wx.ListBox(self, choices=labels, name=prompt)
        self.list.SetSelection(selected)
        self.copy_button = wx.Button(self, label=_("Copy to the clipboard"))
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(self.copy_button, 0, wx.RIGHT, 8)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(560, 420))
        self.copy_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_copy())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _event: self.EndModal(wx.ID_OK))
        self.list.SetFocus()

    def selection(self) -> int:
        """The index of the line selected."""
        return int(self.list.GetSelection())

    def _on_copy(self) -> None:
        index = self.selection()
        if index != wx.NOT_FOUND:
            self._copy(index)
