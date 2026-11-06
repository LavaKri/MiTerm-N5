"""The Connection menu: Choose connection, Connect, Disconnect, Add, Edit, Delete, the SSH client.

See "Menus" and "Connections" in ``specs/interface.md``. Split from ``main_menu.py`` (one menu per
subject, and that file is near its limit). Every item is greyed when the state of the session does
not allow it, never hidden; the access keys are unique inside the menu, in each language.
"""

from collections.abc import Callable
from typing import Protocol

import wx

from n5terminal.core.session.session_state import CommandId
from n5terminal.i18n import _
from n5terminal.ui.menus import MenuBuilder


class ConnectionMenuActions(Protocol):
    """What the items of the Connection menu do."""

    def run(self, command: CommandId) -> None: ...

    def connection_names(self) -> list[str]: ...

    def current_connection(self) -> str | None: ...

    def choose_connection(self, name: str | None) -> None: ...


def _runner(
    actions: ConnectionMenuActions, command: CommandId
) -> Callable[[wx.CommandEvent], None]:
    return lambda _event: actions.run(command)


def connection_menu(
    window: wx.Frame, builder: MenuBuilder, actions: ConnectionMenuActions
) -> wx.Menu:
    """The menu; the choices are made when it opens (the files are read again)."""
    menu = wx.Menu()
    choices = wx.Menu()
    builder.add_submenu(menu, _("C&hoose connection"), CommandId.SET_CONNECTION, choices)
    # Local stays in the menu, so that its shortcut works with the menu closed; the connections
    # found follow it, made again each time the menu opens.
    local = builder.add_radio(
        choices,
        _("Local"),
        CommandId.CHOOSE_LOCAL,
        lambda _event: actions.choose_connection(None),
    )
    window.Bind(
        wx.EVT_MENU_OPEN, lambda event: _fill_connections(window, choices, local, actions, event)
    )
    builder.add(menu, _("&Connect"), CommandId.CONNECT, _runner(actions, CommandId.CONNECT))
    builder.add(
        menu, _("&Disconnect"), CommandId.DISCONNECT, _runner(actions, CommandId.DISCONNECT)
    )
    menu.AppendSeparator()
    builder.add(
        menu, _("&Add…"), CommandId.ADD_CONNECTION, _runner(actions, CommandId.ADD_CONNECTION)
    )
    builder.add(
        menu, _("&Edit…"), CommandId.EDIT_CONNECTION, _runner(actions, CommandId.EDIT_CONNECTION)
    )
    builder.add(
        menu,
        _("De&lete"),
        CommandId.DELETE_CONNECTION,
        _runner(actions, CommandId.DELETE_CONNECTION),
    )
    menu.AppendSeparator()
    builder.add(
        menu, _("&SSH client…"), CommandId.SELECT_SSH, _runner(actions, CommandId.SELECT_SSH)
    )
    return menu


def _fill_connections(
    window: wx.Frame,
    choices: wx.Menu,
    local: wx.MenuItem,
    actions: ConnectionMenuActions,
    event: wx.MenuEvent,
) -> None:
    """The connections found, after Local; the one in use is checked."""
    event.Skip()
    for item in list(choices.GetMenuItems()):
        if item.GetId() != local.GetId():
            choices.Delete(item)
    current = actions.current_connection()
    local.Check(current is None)
    for name in actions.connection_names():
        item = choices.AppendRadioItem(wx.ID_ANY, name.replace("&", "&&"))
        item.Check(name == current)
        window.Bind(wx.EVT_MENU, lambda _e, chosen=name: actions.choose_connection(chosen), item)
