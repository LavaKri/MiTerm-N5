"""The Shortcuts page of the Preferences: a list of commands and a field to press a new shortcut.

A choice above the list picks the group of commands it shows (the main ones, or the keys sent to a
program). The list has one line per command, saying the command then its shortcut (nothing depends
on columns). The field below shows the shortcut of the selected command; pressing a key
combination in
it gives that shortcut to the command, unless a rule refuses it, in which case a message says why.
Tab always leaves the field. Two buttons restore the default shortcut or remove the shortcut.
"""

import wx

from n5terminal.core.config.shortcuts import ConfigurableCommand, ShortcutCheck
from n5terminal.i18n import _
from n5terminal.presenters.shortcuts_preferences import ShortcutsPreferences
from n5terminal.ui.fields import read_only_field
from n5terminal.ui.shortcut_keys import shortcut_from_event


class ShortcutsPage(wx.Panel):
    """The list of the commands, a field to press the new shortcut, and two buttons."""

    def __init__(self, parent: wx.Window, preferences: ShortcutsPreferences) -> None:
        super().__init__(parent)
        self._preferences = preferences
        self._groups = preferences.groups()
        self._commands: list[ConfigurableCommand] = preferences.commands(self._groups[0])

        group_label = wx.StaticText(self, label=_("Commands to show"))
        self.group_choice = wx.Choice(
            self, choices=[_(group) for group in self._groups], name=_("Commands to show")
        )
        self.group_choice.SetSelection(0)
        list_label = wx.StaticText(self, label=_("Shortcut list"))
        self.command_list = wx.ListBox(
            self,
            choices=[preferences.line(command) for command in self._commands],
            name=_("Shortcut list"),
        )
        capture_label = wx.StaticText(self, label=_("Press the new shortcut here"))
        self.capture = read_only_field(self, 2, _("Press the new shortcut here"))
        self.default_button = wx.Button(self, label=_("Restore the default shortcut"))
        self.clear_button = wx.Button(self, label=_("No shortcut"))

        self.group_choice.Bind(wx.EVT_CHOICE, lambda _event: self._show_group())
        self.command_list.Bind(wx.EVT_LISTBOX, lambda _event: self._show_current())
        self.capture.Bind(wx.EVT_KEY_DOWN, self._on_capture_key)
        self.default_button.Bind(wx.EVT_BUTTON, lambda _event: self.restore_default())
        self.clear_button.Bind(wx.EVT_BUTTON, lambda _event: self.clear_shortcut())

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(self.default_button, 0, wx.RIGHT, 8)
        buttons.Add(self.clear_button)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(group_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.group_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.command_list, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(capture_label, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.capture, 0, wx.EXPAND | wx.ALL, 12)
        sizer.Add(buttons, 0, wx.ALL, 12)
        self.SetSizer(sizer)
        self.command_list.SetSelection(0)
        self._show_current()

    def _show_group(self) -> None:
        """The list shows the commands of the chosen group, from the first."""
        group = self._groups[self.group_choice.GetSelection()]
        self._commands = self._preferences.commands(group)
        self.command_list.Set([self._preferences.line(command) for command in self._commands])
        self.command_list.SetSelection(0)
        self._show_current()

    def selected_command(self) -> ConfigurableCommand:
        """The command selected in the list."""
        index: int = self.command_list.GetSelection()
        return self._commands[index]

    def restore_default(self) -> None:
        """Back to the default shortcut of the selected command."""
        command = self.selected_command()
        self._after(command, self._preferences.restore_default(command), command.default)

    def clear_shortcut(self) -> None:
        """Remove the shortcut of the selected command."""
        command = self.selected_command()
        self._after(command, self._preferences.clear(command), "")

    def assign_pressed(self, shortcut: str) -> None:
        """Give the shortcut pressed to the selected command."""
        command = self.selected_command()
        self._after(command, self._preferences.assign(command, shortcut), shortcut)

    def _after(self, command: ConfigurableCommand, check: ShortcutCheck, shortcut: str) -> None:
        """Show the new state, or say why the shortcut was refused."""
        self.command_list.SetString(
            self.command_list.GetSelection(), self._preferences.line(command)
        )
        self._show_current()
        if check.problem is not None:
            message = self._preferences.problem_message(check, shortcut)
            with wx.MessageDialog(self, message, _("Preferences"), wx.OK | wx.ICON_WARNING) as box:
                box.ShowModal()

    def _show_current(self) -> None:
        self.capture.SetValue(self._preferences.shortcut_text(self.selected_command()))

    def _on_capture_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_TAB and not event.ControlDown() and not event.AltDown():
            # Tab and Shift+Tab must always let the user leave the field.
            flags = (
                wx.NavigationKeyEvent.IsBackward
                if event.ShiftDown()
                else wx.NavigationKeyEvent.IsForward
            )
            self.capture.Navigate(flags)
            return
        shortcut = shortcut_from_event(event)
        if shortcut is None:
            event.Skip()  # a modifier on its own, or a key that cannot be a shortcut
            return
        self.assign_pressed(shortcut)
