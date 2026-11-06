"""The dialog of the prompt patterns and the box that edits one of them: layout and wiring only.

The rules are in ``presenters/prompt_patterns_editor.py``. Each control has an accessible name and
is created right after its label. The list is in the order the patterns are tried; Move up and Move
down change it. Enter is OK and Escape is Cancel; the focus starts in the list. The result of the
trial is a read-only text of several lines (the rule for a field to read), and F1, from anywhere in
the box, says it.
"""

from collections.abc import Callable

import wx

from n5terminal.core.config.prompt_patterns import PromptPattern
from n5terminal.i18n import _
from n5terminal.presenters.prompt_patterns_editor import PromptPatternsEditor


class PromptPatternDialog(wx.Dialog):
    """Name and regular expression of one pattern, with a line to try it on."""

    def __init__(
        self,
        parent: wx.Window,
        editor: PromptPatternsEditor,
        title: str,
        speak: Callable[[str], None],
        pattern: PromptPattern | None = None,
        replacing: int | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._editor = editor
        self._speak = speak
        self._replacing = replacing
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        self.name = self._add_text(grid, _("Name"), pattern.name if pattern else "")
        self.pattern = self._add_text(
            grid, _("Pattern (regular expression)"), pattern.pattern if pattern else ""
        )
        self.replacement = self._add_text(
            grid,
            _("Replacement (said instead of the prompt)"),
            pattern.replacement if pattern else "",
        )
        self.line = self._add_text(grid, _("Line to try"), "")
        self.result = self._add_text(grid, _("Result (F1 to hear)"), "", read_only=True)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(wx.Size(560, self.GetSize().GetHeight()))
        self.SetSize(wx.Size(560, self.GetSize().GetHeight()))
        self.pattern.Bind(wx.EVT_TEXT, lambda _event: self._try())
        self.replacement.Bind(wx.EVT_TEXT, lambda _event: self._try())
        self.line.Bind(wx.EVT_TEXT, lambda _event: self._try())
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.name.SetFocus()

    def _add_text(
        self, grid: wx.FlexGridSizer, label: str, value: str, read_only: bool = False
    ) -> wx.TextCtrl:
        text = wx.StaticText(self, label=label)
        # A field to read is a text of several lines that Tab reaches: a screen reader skips a
        # read-only line (``specs/working-rules.md``).
        style = wx.TE_MULTILINE | wx.TE_READONLY if read_only else 0
        control = wx.TextCtrl(self, value=value, style=style, name=label)
        if read_only:
            control.SetMinSize(wx.Size(-1, control.GetCharHeight() * 3))
        grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        """F1, from any control of the box, says the result of the trial."""
        if event.GetKeyCode() == wx.WXK_F1 and not event.HasAnyModifiers():
            self.say_result()
            return
        event.Skip()

    def say_result(self) -> None:
        """Announce what the pattern makes of the line to try (or that there is nothing yet)."""
        self._speak(self.result.GetValue() or _("Nothing to try yet."))

    def _try(self) -> None:
        self.result.SetValue(
            self._editor.sample(
                self.pattern.GetValue(), self.replacement.GetValue(), self.line.GetValue()
            )
        )

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """OK only when name and pattern are acceptable; otherwise say why and stay."""
        message = self._editor.problem(
            self.name.GetValue(),
            self.pattern.GetValue(),
            self.replacement.GetValue(),
            self._replacing,
        )
        if message is None:
            event.Skip()
            return
        with wx.MessageDialog(self, message, _("Filter refused"), wx.OK | wx.ICON_WARNING) as box:
            box.ShowModal()
        self.name.SetFocus()


class PromptPatternsDialog(wx.Dialog):
    """The list of the patterns, in the order they are tried, and the choice of the formatting."""

    def __init__(
        self, parent: wx.Window, editor: PromptPatternsEditor, speak: Callable[[str], None]
    ) -> None:
        super().__init__(
            parent, title=_("Line filtering"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._editor = editor
        self._speak = speak
        label = wx.StaticText(self, label=_("Filters, in the order they are tried"))
        self.list = wx.ListBox(
            self, choices=editor.names(), name=_("Filters, in the order they are tried")
        )
        self.add_button = wx.Button(self, label=_("Add a filter…"))
        self.edit_button = wx.Button(self, label=_("Edit the filter…"))
        self.remove_button = wx.Button(self, label=_("Remove the filter"))
        self.up_button = wx.Button(self, label=_("Move up"))
        self.down_button = wx.Button(self, label=_("Move down"))
        self.restore_button = wx.Button(self, label=_("Restore the start filters"))
        self.formatting = wx.CheckBox(
            self,
            label=_("Include the formatting of the activities"),
            name=_("Include the formatting of the activities"),
        )
        self.formatting.SetValue(editor.formatting)
        self.titles = wx.CheckBox(
            self,
            label=_("Comfortable reading for the moves by titles"),
            name=_("Comfortable reading for the moves by titles"),
        )
        self.titles.SetValue(editor.titles)
        buttons = wx.BoxSizer(wx.VERTICAL)
        for button in (
            self.add_button,
            self.edit_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.restore_button,
        ):
            buttons.Add(button, 0, wx.EXPAND | wx.BOTTOM, 4)
        middle = wx.BoxSizer(wx.HORIZONTAL)
        middle.Add(self.list, 1, wx.EXPAND | wx.RIGHT, 8)
        middle.Add(buttons, 0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 8)
        sizer.Add(middle, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.formatting, 0, wx.ALL, 8)
        sizer.Add(self.titles, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(640, 420))
        self._bind()
        if editor.patterns:
            self.list.SetSelection(0)
        self._show_buttons()
        self.list.SetFocus()

    def _bind(self) -> None:
        self.add_button.Bind(wx.EVT_BUTTON, lambda _event: self._add())
        self.edit_button.Bind(wx.EVT_BUTTON, lambda _event: self._edit())
        self.remove_button.Bind(wx.EVT_BUTTON, lambda _event: self._remove())
        self.up_button.Bind(wx.EVT_BUTTON, lambda _event: self._move(-1))
        self.down_button.Bind(wx.EVT_BUTTON, lambda _event: self._move(1))
        self.restore_button.Bind(wx.EVT_BUTTON, lambda _event: self._restore())
        self.list.Bind(wx.EVT_LISTBOX, lambda _event: self._show_buttons())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _event: self._edit())
        self.formatting.Bind(wx.EVT_CHECKBOX, lambda _event: self._take_formatting())
        self.titles.Bind(wx.EVT_CHECKBOX, lambda _event: self._take_titles())

    def _take_formatting(self) -> None:
        self._editor.formatting = self.formatting.GetValue()

    def _take_titles(self) -> None:
        self._editor.titles = self.titles.GetValue()

    def _show_buttons(self) -> None:
        index = self.list.GetSelection()
        chosen = index != wx.NOT_FOUND
        self.edit_button.Enable(chosen)
        self.remove_button.Enable(chosen)
        self.up_button.Enable(chosen and index > 0)
        self.down_button.Enable(chosen and index < self.list.GetCount() - 1)

    def _show(self, select: int | None) -> None:
        self.list.Set(self._editor.names())
        if select is not None:
            self.list.SetSelection(select)
        self._show_buttons()
        self.list.SetFocus()

    def _add(self) -> None:
        with PromptPatternDialog(self, self._editor, _("Add a filter"), self._speak) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            index = self._editor.add(
                dialog.name.GetValue(), dialog.pattern.GetValue(), dialog.replacement.GetValue()
            )
        self._show(index)

    def _edit(self) -> None:
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND:
            return
        current = self._editor.patterns[index]
        with PromptPatternDialog(
            self, self._editor, _("Edit the filter"), self._speak, current, replacing=index
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self._editor.replace(
                index,
                dialog.name.GetValue(),
                dialog.pattern.GetValue(),
                dialog.replacement.GetValue(),
            )
        self._show(index)

    def _remove(self) -> None:
        index = self.list.GetSelection()
        if index != wx.NOT_FOUND:
            self._show(self._editor.remove(index))

    def _move(self, step: int) -> None:
        index = self.list.GetSelection()
        if index != wx.NOT_FOUND:
            self._show(self._editor.move(index, step))

    def _restore(self) -> None:
        self._editor.restore_start_patterns()
        self._show(0 if self._editor.patterns else None)
