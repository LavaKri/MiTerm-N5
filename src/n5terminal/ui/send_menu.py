"""The menus that send a key to the program: the Send sub-menu and the menu of the command field.

The Send sub-menu is in the Session menu and in the context menu of the output area (the
Application key, Shift+F10 or a right click). Both use the same items, greyed unless a program
served through a terminal runs (``CommandId.SEND_KEY``). The command field has a context menu of
its own: History, then its text commands. See "Sending keys" in ``specs/interface.md``.
"""

from collections.abc import Callable
from typing import Protocol

import wx

from n5terminal.core.config.keys import KEY_GROUPS, SentKey
from n5terminal.core.config.shortcuts import display_shortcut
from n5terminal.core.session.session_state import CommandId
from n5terminal.i18n import _
from n5terminal.ui.menus import MenuBuilder


class KeyActions(Protocol):
    """What the items of the send menus do."""

    def run(self, command: CommandId) -> None: ...

    def send_key(self, key: SentKey) -> None: ...


def build_send_menu(builder: MenuBuilder, actions: KeyActions) -> wx.Menu:
    """The keys by group, each group a sub-menu."""
    menu = wx.Menu()
    for group, keys in KEY_GROUPS:
        submenu = wx.Menu()
        for key in keys:
            builder.add_key(submenu, key, _sender(actions, key))
        menu.AppendSubMenu(submenu, _(group))
    return menu


def _sender(actions: KeyActions, key: SentKey) -> Callable[[wx.CommandEvent], None]:
    return lambda _event: actions.send_key(key)


def build_command_menu(builder: MenuBuilder, actions: KeyActions) -> wx.Menu:
    """The context menu of the command field: History, Multi-line input, then the text commands.

    A context menu of our own replaces the native one of the field, so its editing commands are
    kept: they are the standard ones (``wx.ID_CUT``...), which the field handles itself.
    """
    menu = wx.Menu()
    builder.add(menu, _("&History"), CommandId.HISTORY, lambda _e: actions.run(CommandId.HISTORY))
    builder.add(
        menu,
        _("Multi-line &input…"),
        CommandId.MULTILINE,
        lambda _e: actions.run(CommandId.MULTILINE),
    )
    menu.AppendSeparator()
    for stock_id in (wx.ID_CUT, wx.ID_COPY, wx.ID_PASTE, wx.ID_SELECTALL):
        menu.Append(stock_id)
    return menu


def build_output_menu(builder: MenuBuilder, actions: KeyActions) -> wx.Menu:
    """The context menu of the output area: Copy, Select all (the control's own), titles, Send."""
    menu = wx.Menu()
    menu.Append(wx.ID_COPY)
    menu.Append(wx.ID_SELECTALL)
    menu.AppendSeparator()
    for command, label, shortcut in (
        (CommandId.PREVIOUS_TITLE, _("Previous title (1 to 6)"), "Shift+T"),
        (CommandId.NEXT_TITLE, _("Next title (1 to 6)"), "T"),
    ):
        # The keys of the output area are fixed, not configurable: written here as they are said.
        text = f"{label}\t{display_shortcut(shortcut, _)}"
        builder.add(menu, text, command, _runner(actions, command))
    menu.AppendSeparator()
    builder.add_submenu(menu, _("Send"), CommandId.SEND_KEY, build_send_menu(builder, actions))
    return menu


def _runner(actions: KeyActions, command: CommandId) -> Callable[[wx.CommandEvent], None]:
    return lambda _event: actions.run(command)
