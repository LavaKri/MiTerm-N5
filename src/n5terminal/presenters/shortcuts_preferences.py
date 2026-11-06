"""The Shortcuts page of the Preferences: the keyboard shortcut of each configurable command.

See "Preferences" in ``specs/interface.md``. The rules a shortcut must follow are in
``core/config/shortcuts.py``; this keeps the draft, says why a shortcut is refused and writes the
draft to the settings. Each line of the list says the command then its shortcut.
"""

from collections.abc import Callable

from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    MAIN_GROUP,
    ConfigurableCommand,
    ShortcutCheck,
    ShortcutProblem,
    check_shortcut,
    display_shortcut,
)
from n5terminal.i18n import N_
from n5terminal.presenters.preferences_changes import AppliedChanges

Translate = Callable[[str], str]
LINE_FORMAT = N_("{command}, {shortcut}")  # the command, then its shortcut
NO_SHORTCUT = N_("none")
TAKEN_MESSAGE = N_('{shortcut} is already used by the command "{command}".')
FIXED_MESSAGE = N_("{shortcut} is the shortcut of a standard command and cannot be reused.")
RESERVED_MESSAGE = N_(
    "{shortcut} cannot be used: a shortcut needs the Ctrl key, the Alt key or both "
    "(or be a function key), Enter needs at least one modifier key, and Tab, Insert and "
    "Esc (except Shift+Esc) are reserved for navigation and screen readers."
)
INVALID_MESSAGE = N_("{shortcut} is not a valid shortcut.")


class ShortcutsPreferences:
    """The draft of the shortcuts, started from ``settings``; ``translate`` is ``_``."""

    def __init__(self, settings: Settings, translate: Translate) -> None:
        self._settings = settings
        self._translate = translate
        self._shortcuts = settings.all_shortcuts()

    def groups(self) -> list[str]:
        """The groups the list can show (message ids), the main one first."""
        found: list[str] = []
        for command in CONFIGURABLE_COMMANDS:
            if command.group not in found:
                found.append(command.group)
        return found

    def commands(self, group: str = MAIN_GROUP) -> list[ConfigurableCommand]:
        """The configurable commands of a group, in the order of the list."""
        return [command for command in CONFIGURABLE_COMMANDS if command.group == group]

    def shortcut(self, command: ConfigurableCommand) -> str:
        """The draft shortcut of ``command`` (empty: none)."""
        return self._shortcuts[command.id]

    def shortcut_text(self, command: ConfigurableCommand) -> str:
        """The shortcut to show or read: its keys, or "none"."""
        shortcut = self.shortcut(command)
        return (
            display_shortcut(shortcut, self._translate)
            if shortcut
            else self._translate(NO_SHORTCUT)
        )

    def line(self, command: ConfigurableCommand) -> str:
        """The command then its shortcut, in one text."""
        return self._translate(LINE_FORMAT).format(
            command=command.text(self._translate), shortcut=self.shortcut_text(command)
        )

    def assign(self, command: ConfigurableCommand, shortcut: str) -> ShortcutCheck:
        """Give ``shortcut`` to ``command`` unless a rule refuses it; return the verdict."""
        check = check_shortcut(command, shortcut, self._shortcuts)
        if check.problem is None:
            self._shortcuts[command.id] = shortcut
        return check

    def restore_default(self, command: ConfigurableCommand) -> ShortcutCheck:
        """Back to the default shortcut of ``command`` (refused if another command took it)."""
        return self.assign(command, command.default)

    def clear(self, command: ConfigurableCommand) -> ShortcutCheck:
        """No shortcut for ``command``."""
        return self.assign(command, "")

    def problem_message(self, check: ShortcutCheck, shortcut: str) -> str:
        """Explain why ``shortcut`` was refused."""
        translate = self._translate
        shortcut = display_shortcut(shortcut, translate)
        if check.problem is ShortcutProblem.TAKEN and check.other is not None:
            return translate(TAKEN_MESSAGE).format(
                shortcut=shortcut, command=check.other.text(translate)
            )
        if check.problem is ShortcutProblem.FIXED:
            return translate(FIXED_MESSAGE).format(shortcut=shortcut)
        if check.problem is ShortcutProblem.RESERVED:
            return translate(RESERVED_MESSAGE).format(shortcut=shortcut)
        return translate(INVALID_MESSAGE).format(shortcut=shortcut)

    def apply(self) -> AppliedChanges:
        """Write the draft to the settings (not to the file) and tell if something changed."""
        changed = False
        for command in CONFIGURABLE_COMMANDS:
            chosen = self._shortcuts[command.id]
            if chosen != self._settings.shortcut_for(command):
                self._settings.set_shortcut(command, chosen)
                changed = True
        return AppliedChanges(shortcuts=changed)
