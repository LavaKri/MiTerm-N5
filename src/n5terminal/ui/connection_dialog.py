"""The connection dialog (Add and Edit of the Connection menu): layout and wiring only.

The rules are in ``presenters/connection_editor.py``. Each control has an accessible name and is
created right after its label. Enter is OK, Escape is Cancel; OK is refused, with a message, while
a field is not acceptable, and the focus goes to that field. The focus starts in the name. No
secret is asked here: the password is asked when the connection opens.
"""

import unicodedata

import wx

from n5terminal.core.config.connections import MAX_NAME_LENGTH
from n5terminal.i18n import _
from n5terminal.presenters.connection_editor import ConnectionEditor, Field


class ConnectionDialog(wx.Dialog):
    """Edit a :class:`ConnectionEditor`. ``commit`` hands the controls to it."""

    def __init__(self, parent: wx.Window, editor: ConnectionEditor) -> None:
        title = _("New connection") if editor.is_new else _("Edit the connection {name}")
        super().__init__(
            parent, title=title.format(name=editor.name), style=wx.DEFAULT_DIALOG_STYLE
        )
        self._editor = editor
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        self.name = self._add_text(grid, _("Name"), editor.name)
        self.name.SetMaxLength(MAX_NAME_LENGTH)  # the check on OK stays, for what was pasted
        self.target = self._add_text(grid, _("Target (an alias or user@host)"), editor.target)
        self.port = self._add_text(grid, _("Port (optional)"), editor.port)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(520, self.GetSize().GetHeight()))
        self.SetSize(wx.Size(520, self.GetSize().GetHeight()))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.name.SetFocus()

    def _add_text(self, grid: wx.FlexGridSizer, label: str, value: str) -> wx.TextCtrl:
        text = wx.StaticText(self, label=label)
        control = wx.TextCtrl(self, value=value, name=label)
        grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def commit(self) -> None:
        """Hand what the controls show to the draft."""
        # One spelling for an accented letter: composed (``é``), not a letter and its accent.
        self._editor.name = unicodedata.normalize("NFC", self.name.GetValue().strip())
        self._editor.target = self.target.GetValue().strip()
        self._editor.port = self.port.GetValue().strip()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """OK only when everything is acceptable; otherwise say why and go to the field."""
        self.commit()
        problem = self._editor.problem()
        if problem is None:
            event.Skip()
            return
        field, message = problem
        with wx.MessageDialog(self, message, _("Value refused"), wx.OK | wx.ICON_WARNING) as box:
            box.ShowModal()
        {Field.NAME: self.name, Field.TARGET: self.target, Field.PORT: self.port}[field].SetFocus()
