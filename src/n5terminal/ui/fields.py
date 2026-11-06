"""Small helpers to build controls that several dialogs need."""

import wx


def read_only_field(parent: wx.Window, lines: int, name: str) -> wx.TextCtrl:
    """A read-only text field that the Tab key reaches and a screen reader can read.

    wx does not give the keyboard focus to a read-only single-line text control, so the field is
    a multi-line one, sized for ``lines`` lines.
    """
    field = wx.TextCtrl(parent, style=wx.TE_READONLY | wx.TE_MULTILINE, name=name)
    field.SetMinSize(wx.Size(-1, field.GetCharHeight() * lines + 10))
    return field
