"""The dialog that gives a value to each variable the chosen profile uses.

One text field per variable, each right after its label, in the usual order of the variables. The
values are not checked. Enter is OK, Escape is Cancel; the focus starts in the first field.
"""

import wx

from n5terminal.i18n import _


class VariablesDialog(wx.Dialog):
    """``fields`` are the (variable, label) to ask, ``values`` what was typed before."""

    def __init__(
        self,
        parent: wx.Window,
        profile: str,
        fields: list[tuple[str, str]],
        values: dict[str, str],
    ) -> None:
        super().__init__(
            parent,
            title=_("Variables of the profile {name}").format(name=profile),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.controls: dict[str, wx.TextCtrl] = {}
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        for variable, label in fields:
            text = wx.StaticText(self, label=label)
            control = wx.TextCtrl(self, value=values.get(variable, ""), name=label)
            grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
            self.controls[variable] = control
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(420, -1))
        self.SetSize(wx.Size(max(self.GetSize().width, 420), self.GetSize().height))
        next(iter(self.controls.values())).SetFocus()

    def values(self) -> dict[str, str]:
        """What the fields hold now, by variable."""
        return {variable: control.GetValue() for variable, control in self.controls.items()}
