"""The profile dialog (Add and Edit of the Profile menu): layout and wiring only.

The choices and their rules are in ``presenters/profile_editor.py``. Each control has an accessible
name and is created right after its label. Enter is OK, Escape is Cancel; OK is refused, with a
message, while the name is not acceptable. The focus starts in the name.
"""

import unicodedata

import wx

from n5terminal.core.config.profiles import MAX_NAME_LENGTH
from n5terminal.i18n import _
from n5terminal.presenters.choices import Choices
from n5terminal.presenters.profile_editor import ProfileEditor


class ProfileDialog(wx.Dialog):
    """Edit a :class:`ProfileEditor`. ``commit`` hands the controls to it."""

    def __init__(self, parent: wx.Window, editor: ProfileEditor) -> None:
        title = _("New profile") if editor.is_new else _("Edit the profile {name}")
        super().__init__(
            parent,
            title=title.format(name=editor.name),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._editor = editor
        self._modes = editor.mode_choices()
        self._interpreters = editor.interpreter_choices()
        self._sizes = editor.size_choices()
        self._variables = editor.variable_lines()

        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)
        self.name = self._add_text(grid, _("Name"), editor.name)
        self.name.SetMaxLength(MAX_NAME_LENGTH)  # the check on OK stays, for what was pasted
        self.program = self._add_text(grid, _("Program"), editor.program)
        self.interpreter = self._add_choice(
            grid, _("Interpreter"), self._interpreters, editor.interpreter
        )
        self.prompt_prefix = self._add_text(grid, _("Prompt prefix"), editor.prompt_prefix)
        self.mode = self._add_choice(grid, _("Mode"), self._modes, editor.launch_mode)
        self.size = self._add_choice(grid, _("Terminal size"), self._sizes, editor.terminal_size)
        self.terminal_view_only = wx.CheckBox(
            self, label=_("Terminal view only"), name=_("Terminal view only")
        )
        self.terminal_view_only.SetValue(editor.terminal_view_only)
        self.stderr_prefix = wx.CheckBox(self, label=_("StdErr prefix"), name=_("StdErr prefix"))
        self.stderr_prefix.SetValue(editor.stderr_prefix)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.terminal_view_only, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.stderr_prefix, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._add_variables(sizer)
        self._add_commands(sizer)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(640, 640))

        self._bind_controls()
        self._show_mode_state()
        self._show_command_buttons()
        self.name.SetFocus()

    # Building ----------------------------------------------------------------------------------

    def _add_variables(self, sizer: wx.BoxSizer) -> None:
        label = wx.StaticText(self, label=_("Variables"))
        self.variables = wx.CheckListBox(
            self, choices=[line for _variable, line in self._variables], name=_("Variables")
        )
        self.variables.SetCheckedItems(
            [
                i
                for i, (variable, _line) in enumerate(self._variables)
                if variable in self._editor.variables
            ]
        )
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.variables, 0, wx.EXPAND | wx.ALL, 8)

    def _add_commands(self, sizer: wx.BoxSizer) -> None:
        """The type of command, the list of the commands of that type and the buttons."""
        editor = self._editor
        self._uses = editor.use_choices()
        use_label = wx.StaticText(self, label=_("Command type"))
        self.use = wx.Choice(
            self, choices=[name for _use, name in self._uses], name=_("Command type")
        )
        self.use.SetSelection([use for use, _name in self._uses].index(editor.use))
        commands_label = wx.StaticText(self, label=_("Common commands"))
        self.commands = wx.ListBox(self, choices=list(editor.commands), name=_("Common commands"))
        self.add_command = wx.Button(self, label=_("Add a command…"))
        self.edit_command = wx.Button(self, label=_("Edit the command…"))
        self.remove_command = wx.Button(self, label=_("Remove the command"))
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for button in (self.add_command, self.edit_command, self.remove_command):
            buttons.Add(button, 0, wx.RIGHT, 8)
        sizer.Add(use_label, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.use, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(commands_label, 0, wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.commands, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    def _add_text(self, grid: wx.FlexGridSizer, label: str, value: str) -> wx.TextCtrl:
        text = wx.StaticText(self, label=label)
        control = wx.TextCtrl(self, value=value, name=label)
        grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _add_choice(
        self, grid: wx.FlexGridSizer, label: str, choices: Choices, current: str
    ) -> wx.Choice:
        text = wx.StaticText(self, label=label)
        control = wx.Choice(self, choices=[name for _value, name in choices], name=label)
        control.SetSelection([value for value, _name in choices].index(current))
        grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _bind_controls(self) -> None:
        self.interpreter.Bind(wx.EVT_CHOICE, lambda _event: self._show_mode_state())
        self.use.Bind(wx.EVT_CHOICE, lambda _event: self._show_use())
        self.add_command.Bind(wx.EVT_BUTTON, lambda _event: self._add_command())
        self.edit_command.Bind(wx.EVT_BUTTON, lambda _event: self._edit_command())
        self.remove_command.Bind(wx.EVT_BUTTON, lambda _event: self._remove_command())
        self.commands.Bind(wx.EVT_LISTBOX, lambda _event: self._show_command_buttons())
        self.commands.Bind(wx.EVT_LISTBOX_DCLICK, lambda _event: self._edit_command())
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        if self._editor.commands:
            # A list of one line gets no selection from the arrows: select the first one, so that
            # Edit and Remove are available at once.
            self.commands.SetSelection(0)

    # Behaviour ---------------------------------------------------------------------------------

    def _show_mode_state(self) -> None:
        """A shell is always a TUI and has no program: both are greyed, not hidden; so is the
        prefix of the prompt when there is no shell."""
        self._editor.interpreter = self._interpreters[self.interpreter.GetSelection()][0]
        self.mode.Enable(self._editor.mode_enabled)
        self.program.Enable(self._editor.program_enabled)
        self.prompt_prefix.Enable(self._editor.prompt_prefix_enabled)
        self._show_uses()

    def _show_uses(self) -> None:
        """The types offered follow the shell: only Shell with one, else launch and program."""
        editor = self._editor
        self._uses = editor.use_choices()
        self.use.Set([name for _use, name in self._uses])
        self.use.SetSelection([use for use, _name in self._uses].index(editor.use))
        self.commands.Set(list(editor.commands))
        if editor.commands:
            self.commands.SetSelection(0)
        self._show_command_buttons()

    def _show_use(self) -> None:
        """The list shows the commands of the type chosen; Add and Edit work on that type."""
        self._editor.use = self._uses[self.use.GetSelection()][0]
        self.commands.Set(list(self._editor.commands))
        if self._editor.commands:
            self.commands.SetSelection(0)
        self._show_command_buttons()

    def _show_command_buttons(self) -> None:
        has_command = self.commands.GetSelection() != wx.NOT_FOUND
        self.edit_command.Enable(has_command)
        self.remove_command.Enable(has_command)

    def _ask_command(self, title: str, current: str) -> str | None:
        with wx.TextEntryDialog(self, _("Command"), title, current) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return str(dialog.GetValue())

    def _show_commands(self, select: int | None) -> None:
        self.commands.Set(list(self._editor.commands))
        if select is not None:
            self.commands.SetSelection(select)
        self._show_command_buttons()
        self.commands.SetFocus()

    def _refuse_duplicate(self, command: str, skip: int | None = None) -> bool:
        """Say so, and select the line, when ``command`` is already in the list; whether it is."""
        existing = self._editor.duplicate_index(command, skip)
        if existing is None:
            return False
        with wx.MessageDialog(
            self,
            _("This command is already in the list."),
            _("Command refused"),
            wx.OK | wx.ICON_WARNING,
        ) as box:
            box.ShowModal()
        self._show_commands(existing)
        return True

    def _add_command(self) -> None:
        command = self._ask_command(_("Add a command"), "")
        if command is not None and not self._refuse_duplicate(command):
            self._show_commands(self._editor.add_command(command))

    def _edit_command(self) -> None:
        index = self.commands.GetSelection()
        if index == wx.NOT_FOUND:
            return
        command = self._ask_command(_("Edit the command"), self._editor.commands[index])
        if command is None or self._refuse_duplicate(command, skip=index):
            return
        new_index = self._editor.replace_command(index, command)
        if new_index is not None:
            self._show_commands(new_index)

    def _remove_command(self) -> None:
        index = self.commands.GetSelection()
        if index != wx.NOT_FOUND:
            self._show_commands(self._editor.remove_command(index))

    def commit(self) -> None:
        """Hand what the controls show to the draft."""
        editor = self._editor
        # One spelling for an accented letter: composed (``é``), not a letter and its accent.
        editor.name = unicodedata.normalize("NFC", self.name.GetValue().strip())
        editor.program = self.program.GetValue().strip()
        editor.interpreter = self._interpreters[self.interpreter.GetSelection()][0]
        editor.prompt_prefix = self.prompt_prefix.GetValue()  # not stripped: its last space matters
        editor.launch_mode = self._modes[self.mode.GetSelection()][0]
        editor.terminal_size = self._sizes[self.size.GetSelection()][0]
        editor.terminal_view_only = self.terminal_view_only.GetValue()
        editor.stderr_prefix = self.stderr_prefix.GetValue()
        editor.set_variables([self._variables[i][0] for i in self.variables.GetCheckedItems()])

    def _on_ok(self, event: wx.CommandEvent) -> None:
        """OK only when the name is acceptable; otherwise say why and stay in the name."""
        self.commit()
        message = self._editor.name_message()
        if message is None:
            event.Skip()
            return
        with wx.MessageDialog(self, message, _("Name refused"), wx.OK | wx.ICON_WARNING) as box:
            box.ShowModal()
        self.name.SetFocus()
