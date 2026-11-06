"""A dialog that picks a program among the ones found, or a path: layout and wiring only.

Shared by "PowerShell selection" and "OpenSSH client". The options and their rules are in the
draft (``presenters/powershell_choice.py``, ``presenters/ssh_choice.py``). Each control has an
accessible name and is created right after its label. Enter is OK, Escape is Cancel; OK is refused,
with a message, while "Other…" holds a path that is not that program. The focus starts in the list.
"""

from typing import Protocol

import wx

from n5terminal.i18n import _


class ProgramDraft(Protocol):
    """What the dialog needs of the draft it edits."""

    selected: int
    custom_path: str

    @property
    def labels(self) -> list[str]: ...

    @property
    def path_enabled(self) -> bool: ...

    def problem(self) -> str | None: ...


class ProgramDialog(wx.Dialog):
    """Edit a :class:`ProgramDraft`. ``commit`` hands the controls to it.

    ``note`` is a line of text under the list (what the user should know about the choice).
    """

    def __init__(
        self,
        parent: wx.Window,
        draft: ProgramDraft,
        title: str,
        list_label: str,
        path_label: str,
        note: str = "",
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._draft = draft
        self._path_label = path_label
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        version_label = wx.StaticText(self, label=list_label)
        self.versions = wx.Choice(self, choices=draft.labels, name=list_label)
        self.versions.SetSelection(draft.selected)
        label = wx.StaticText(self, label=path_label)
        self.path = wx.TextCtrl(self, value=draft.custom_path, name=path_label)
        self.browse = wx.Button(self, label=_("Browse…"))
        grid.Add(version_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.versions, 1, wx.EXPAND)
        grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        path_row.Add(self.path, 1, wx.EXPAND | wx.RIGHT, 8)
        path_row.Add(self.browse, 0)
        grid.Add(path_row, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        if note:
            sizer.Add(wx.StaticText(self, label=note), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(560, self.GetSize().GetHeight()))
        self.SetSize(wx.Size(560, self.GetSize().GetHeight()))

        self.versions.Bind(wx.EVT_CHOICE, lambda _event: self._show_path_state())
        self.browse.Bind(wx.EVT_BUTTON, lambda _event: self._browse())
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._show_path_state()
        self.versions.SetFocus()

    def _show_path_state(self) -> None:
        """The path and its button are for "Other…" only: greyed, not hidden, for the others."""
        self._draft.selected = self.versions.GetSelection()
        enabled = self._draft.path_enabled
        self.path.Enable(enabled)
        self.browse.Enable(enabled)

    def _browse(self) -> None:
        files = "{programs}|*.exe".format(programs=_("Programs (*.exe)"))
        with wx.FileDialog(
            self, self._path_label, wildcard=files, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.path.SetValue(dialog.GetPath())
        self.path.SetFocus()

    def commit(self) -> None:
        """Hand what the controls show to the draft."""
        self._draft.selected = self.versions.GetSelection()
        self._draft.custom_path = self.path.GetValue()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """OK only when the choice is that program; otherwise say why and stay in the path."""
        self.commit()
        message = self._draft.problem()
        if message is None:
            event.Skip()
            return
        with wx.MessageDialog(self, message, _("Choice refused"), wx.OK | wx.ICON_WARNING) as box:
            box.ShowModal()
        self.path.SetFocus()
