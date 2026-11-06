"""Building blocks of the menus: items bound to a command, radio choices, the shortcut in the text.

The items are kept by command so that the presenter's set of enabled commands can grey them (never
hide them), and the radio choices by group so that the real mode or interpreter is checked.
"""

from collections.abc import Callable

import wx

from n5terminal.core.config.keys import SentKey
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import CONFIGURABLE_COMMANDS, display_shortcut
from n5terminal.core.session.command_shortcuts import shortcut_id_of
from n5terminal.core.session.session_state import CommandId
from n5terminal.i18n import _

Handler = Callable[[wx.CommandEvent], None]


class MenuBuilder:
    """Adds items to menus and remembers them."""

    def __init__(self, window: wx.Frame, settings: Settings) -> None:
        self._window = window
        self._settings = settings
        self._commands = {command.id: command for command in CONFIGURABLE_COMMANDS}
        self.items: dict[CommandId, list[wx.MenuItem]] = {}
        self.choices: dict[str, dict[object, wx.MenuItem]] = {}
        self.toggles: dict[CommandId, wx.MenuItem] = {}
        self._with_shortcut: list[tuple[wx.MenuItem, str, str | None]] = []

    def with_shortcut(self, text: str, command: CommandId | None) -> str:
        """``text`` followed by the shortcut of ``command`` (after a tab, as wx wants it)."""
        return self._with_shortcut_id(text, shortcut_id_of(command) if command else None)

    def _with_shortcut_id(self, text: str, shortcut_id: str | None) -> str:
        if shortcut_id is None:
            return text
        shortcut = self._settings.shortcut_for(self._commands[shortcut_id])
        return f"{text}\t{display_shortcut(shortcut, _)}" if shortcut else text

    def add(
        self, menu: wx.Menu, text: str, command: CommandId, handler: Handler, help_text: str = ""
    ) -> wx.MenuItem:
        """A plain item that runs ``handler`` and is greyed with ``command``."""
        item = menu.Append(wx.ID_ANY, self.with_shortcut(text, command), help_text)
        self._window.Bind(wx.EVT_MENU, handler, item)
        self.items.setdefault(command, []).append(item)
        self._with_shortcut.append((item, text, shortcut_id_of(command)))
        return item

    def add_radio(
        self, menu: wx.Menu, text: str, command: CommandId, handler: Handler
    ) -> wx.MenuItem:
        """A radio item that stays in its menu, greyed with ``command``; the caller checks it."""
        item = menu.AppendRadioItem(wx.ID_ANY, self.with_shortcut(text, command))
        self._window.Bind(wx.EVT_MENU, handler, item)
        self.items.setdefault(command, []).append(item)
        self._with_shortcut.append((item, text, shortcut_id_of(command)))
        return item

    def add_key(self, menu: wx.Menu, key: SentKey, handler: Handler) -> wx.MenuItem:
        """An item that sends ``key``; it shows the shortcut the user gave the key."""
        text = _(key.name).replace("&", "&&")
        shortcut_id = f"key.{key.id}"
        item = menu.Append(wx.ID_ANY, self._with_shortcut_id(text, shortcut_id))
        self._window.Bind(wx.EVT_MENU, handler, item)
        self.items.setdefault(CommandId.SEND_KEY, []).append(item)
        self._with_shortcut.append((item, text, shortcut_id))
        return item

    def break_accelerators(self) -> list[tuple[int, int, int]]:
        """The accelerators of the items whose key is Pause, for the key Windows really sends.

        Ctrl+Pause arrives as Ctrl+Break (``WXK_CANCEL``), while the accelerator of the item is
        made for ``WXK_PAUSE``: each is given as (flags, key, item id), to be added to the table of
        the window.
        """
        found = []
        for item, _text, _shortcut_id in self._with_shortcut:
            accel = item.GetAccel()
            if accel is not None and accel.GetKeyCode() == wx.WXK_PAUSE:
                found.append((accel.GetFlags(), wx.WXK_CANCEL, item.GetId()))
        return found

    def refresh_shortcuts(self) -> None:
        """Write the shortcuts now in the settings in the text of the items."""
        for item, text, shortcut_id in self._with_shortcut:
            item.SetItemLabel(self._with_shortcut_id(text, shortcut_id))

    def add_choice(
        self,
        menu: wx.Menu,
        group: str,
        value: object,
        text: str,
        command: CommandId,
        handler: Handler,
        help_text: str = "",
    ) -> wx.MenuItem:
        """A radio item of ``group``, greyed with ``command``."""
        item = menu.AppendRadioItem(wx.ID_ANY, text, help_text)
        self._window.Bind(wx.EVT_MENU, handler, item)
        self.items.setdefault(command, []).append(item)
        self.choices.setdefault(group, {})[value] = item
        return item

    def add_toggle(
        self, menu: wx.Menu, text: str, command: CommandId, handler: Handler, help_text: str = ""
    ) -> wx.MenuItem:
        """A check item, greyed with ``command``; ``set_checked`` shows its real state."""
        item = menu.AppendCheckItem(wx.ID_ANY, self.with_shortcut(text, command), help_text)
        self._window.Bind(wx.EVT_MENU, handler, item)
        self.items.setdefault(command, []).append(item)
        self.toggles[command] = item
        self._with_shortcut.append((item, text, shortcut_id_of(command)))
        return item

    def set_checked(self, command: CommandId, checked: bool) -> None:
        """Check or uncheck the check item of ``command``."""
        item = self.toggles.get(command)
        if item is not None:
            item.Check(checked)

    def add_submenu(
        self, menu: wx.Menu, text: str, command: CommandId, submenu: wx.Menu
    ) -> wx.MenuItem:
        """A sub-menu, greyed with ``command``."""
        item = menu.AppendSubMenu(submenu, text)
        self.items.setdefault(command, []).append(item)
        return item

    def apply_enabled(self, enabled: frozenset[CommandId]) -> None:
        """Enable the items of the commands in ``enabled`` and grey the others."""
        for command, items in self.items.items():
            for item in items:
                item.Enable(command in enabled)

    def check(self, group: str, value: object) -> None:
        """Check the item of ``value`` in the radio group."""
        item = self.choices.get(group, {}).get(value)
        if item is not None:
            item.Check(True)
