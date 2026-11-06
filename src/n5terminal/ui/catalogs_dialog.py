"""The dialog of the develop mode that edits the message catalogs.

A list of categories, a one column list of messages, and a field. Left and Right in the list change
what its lines show (ids, then each language) and keep the selected line; Up and Down are the usual
ones. The field holds the text of the selected line: read only for an id, a translation otherwise.
Tab order: categories, list, field, OK, Cancel; the focus starts in the list.
"""

import wx

from n5terminal.i18n import _
from n5terminal.presenters.catalogs_editor import CatalogsEditor


class CatalogsDialog(wx.Dialog):
    """Edits the translations of ``editor``; OK checks the fields, then saves."""

    def __init__(self, parent: wx.Window, editor: CatalogsEditor) -> None:
        super().__init__(
            parent, title=_("Catalogs"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._editor = editor
        category_label = wx.StaticText(self, label=_("Category"))
        self._categories = wx.Choice(self, choices=editor.category_names, name=_("Category"))
        self._categories.SetSelection(editor.category_index)
        list_label = wx.StaticText(self, label=_("Messages"))
        self._list = wx.ListBox(self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Messages"))
        self._field_label = wx.StaticText(self, label=editor.field_label)
        self._field = wx.TextCtrl(self, style=wx.TE_MULTILINE, name=editor.field_label)
        sizer = wx.BoxSizer(wx.VERTICAL)
        for control, proportion in (
            (category_label, 0),
            (self._categories, 0),
            (list_label, 0),
            (self._list, 1),
            (self._field_label, 0),
            (self._field, 1),
        ):
            sizer.Add(control, proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(640, 560))
        self._fill_list()
        self._show_selected()
        self._categories.Bind(wx.EVT_CHOICE, self._on_category)
        self._list.Bind(wx.EVT_LISTBOX, self._on_select)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._field.Bind(wx.EVT_TEXT, self._on_text)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._list.SetFocus()

    def _fill_list(self) -> None:
        self._list.Set(self._editor.lines())
        if self._list.GetCount():
            self._list.SetSelection(self._editor.selected)

    def _show_selected(self) -> None:
        """Put the label and the text of the selected line in the field (no change is made)."""
        label = self._editor.field_label
        self._field_label.SetLabel(label)
        self._field.SetName(label)
        self._field.SetEditable(not self._editor.read_only)
        self._field.ChangeValue(self._editor.field_text)

    def _on_category(self, _event: wx.CommandEvent) -> None:
        self._editor.choose_category(self._categories.GetSelection())
        self._fill_list()
        self._show_selected()

    def _on_select(self, _event: wx.CommandEvent) -> None:
        self._editor.select(self._list.GetSelection())
        self._show_selected()

    def _on_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if event.HasAnyModifiers() or code not in (wx.WXK_LEFT, wx.WXK_RIGHT):
            event.Skip()
            return
        if self._editor.change_view(1 if code == wx.WXK_RIGHT else -1):
            for index, line in enumerate(self._editor.lines()):
                self._list.SetString(index, line)  # in place: the selected line stays
            self._show_selected()

    def _on_text(self, _event: wx.CommandEvent) -> None:
        self._editor.edit(self._field.GetValue())

    def _on_ok(self, event: wx.CommandEvent) -> None:
        problem = self._editor.check()
        if problem is not None:
            self._categories.SetSelection(self._editor.category_index)
            self._fill_list()
            self._show_selected()
            wx.MessageBox(problem, _("Error"), wx.OK | wx.ICON_ERROR, self)
            self._field.SetFocus()
            return
        event.Skip()
