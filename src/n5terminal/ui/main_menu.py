"""The menu bar: File, Edit, Session, Profile, Terminal, Develop (in develop mode), Help.

See "Menus" in ``specs/interface.md``.

Every item is greyed when the state of the session does not allow it, never hidden. The access keys
are unique inside a menu, in each language (they are part of the translated texts).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import wx

from n5terminal.core.config.keys import SentKey
from n5terminal.core.screen.terminal_size import STANDARD_SIZES, TerminalSize
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode
from n5terminal.i18n import _
from n5terminal.ui.connection_menu import ConnectionMenuActions, connection_menu
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.send_menu import build_send_menu


class MenuActions(ConnectionMenuActions, Protocol):
    """What the items of the menus do."""

    def run(self, command: CommandId) -> None: ...

    def open_recent(self, folder: Path) -> None: ...

    def recent_folders(self) -> list[Path]: ...

    def set_mode(self, mode: LaunchMode) -> None: ...

    def set_interpreter(self, interpreter: Interpreter) -> None: ...

    def set_size(self, size: TerminalSize | None) -> None: ...

    def set_terminal_view_only(self, view_only: bool) -> None: ...

    def profile_names(self) -> list[str]: ...

    def current_profile(self) -> str | None: ...

    def choose_profile(self, name: str | None) -> None: ...

    def send_key(self, key: SentKey) -> None: ...

    def test_programs(self) -> list[Path]: ...

    def run_test_program(self, program: Path) -> None: ...


def build_menu_bar(
    window: wx.Frame, builder: MenuBuilder, actions: MenuActions, develop: bool = False
) -> wx.MenuBar:
    """The menu bar of the main window, bound to ``actions``; the Develop menu only in its mode."""
    bar = wx.MenuBar()
    bar.Append(_file_menu(window, builder, actions), _("&File"))
    bar.Append(_edit_menu(builder, actions), _("&Edit"))
    bar.Append(_session_menu(builder, actions), _("&Session"))
    bar.Append(_profile_menu(window, builder, actions), _("&Profile"))
    bar.Append(connection_menu(window, builder, actions), _("&Connection"))
    bar.Append(_terminal_menu(builder, actions), _("&Terminal"))
    if develop:
        bar.Append(_develop_menu(window, builder, actions), _("&Develop"))
    bar.Append(_help_menu(builder, actions), _("&Help"))
    return bar


def _bind[T](action: Callable[[T], None], value: T) -> Callable[[wx.CommandEvent], None]:
    """A menu handler that calls ``action(value)``: the value is fixed when the item is made."""
    return lambda _event: action(value)


def _runner(actions: MenuActions, command: CommandId) -> Callable[[wx.CommandEvent], None]:
    return lambda _event: actions.run(command)


def _file_menu(window: wx.Frame, builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(
        menu, _("&New session"), CommandId.NEW_SESSION, _runner(actions, CommandId.NEW_SESSION)
    )
    builder.add(
        menu,
        _("&Working folder…"),
        CommandId.CHOOSE_FOLDER,
        _runner(actions, CommandId.CHOOSE_FOLDER),
    )
    recent = wx.Menu()
    builder.add_submenu(menu, _("&Recent folders"), CommandId.RECENT_FOLDERS, recent)
    window.Bind(wx.EVT_MENU_OPEN, lambda event: _fill_recent(window, recent, actions, event))
    menu.AppendSeparator()
    builder.add(
        menu, _("&Export the output…"), CommandId.EXPORT, _runner(actions, CommandId.EXPORT)
    )
    builder.add(
        menu, _("&Preferences…"), CommandId.PREFERENCES, _runner(actions, CommandId.PREFERENCES)
    )
    menu.AppendSeparator()
    builder.add(menu, _("&Quit"), CommandId.QUIT, _runner(actions, CommandId.QUIT))
    return menu


def _fill_recent(
    window: wx.Frame, recent: wx.Menu, actions: MenuActions, event: wx.MenuEvent
) -> None:
    """The list of recent folders is made when the menu opens, so it is always current."""
    event.Skip()
    for item in list(recent.GetMenuItems()):
        recent.Delete(item)
    folders = actions.recent_folders()
    for folder in folders:
        item = recent.Append(wx.ID_ANY, str(folder).replace("&", "&&"))
        window.Bind(wx.EVT_MENU, lambda _e, path=folder: actions.open_recent(path), item)
    if not folders:
        recent.Append(wx.ID_ANY, _("(none)")).Enable(False)


def _session_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(menu, _("&Stop the program"), CommandId.STOP, _runner(actions, CommandId.STOP))
    menu.AppendSeparator()
    modes = wx.Menu()
    cli_help = _("The program reads and writes text. Fits most commands.")
    tui_help = _(
        "The program believes it is in a real console. For python, ssh, passwords, shells."
    )
    for mode, text, help_text in (
        (LaunchMode.CLI, _("CLI, plain text"), cli_help),
        (LaunchMode.TUI, _("TUI, interactive terminal"), tui_help),
    ):
        builder.add_choice(
            modes,
            "mode",
            mode,
            text,
            CommandId.SET_MODE,
            _bind(actions.set_mode, mode),
            help_text,
        )
    builder.add_submenu(menu, _("&Mode"), CommandId.SET_MODE, modes)
    shells = wx.Menu()
    for interpreter, text in (
        (Interpreter.NONE, _("None")),
        (Interpreter.CMD, "Cmd"),
        (Interpreter.POWERSHELL, "PowerShell"),
    ):
        builder.add_choice(
            shells,
            "interpreter",
            interpreter,
            text,
            CommandId.SET_INTERPRETER,
            _bind(actions.set_interpreter, interpreter),
        )
    shells.AppendSeparator()
    builder.add(
        shells,
        _("PowerShell &selection…"),
        CommandId.SELECT_POWERSHELL,
        _runner(actions, CommandId.SELECT_POWERSHELL),
    )
    # The sub-menu follows the selection (a global setting, free while a profile is chosen); the
    # choices inside it follow SET_INTERPRETER.
    builder.add_submenu(menu, _("&Interpreter"), CommandId.SELECT_POWERSHELL, shells)
    menu.AppendSeparator()
    builder.add_submenu(
        menu, _("Send a key"), CommandId.SEND_KEY, build_send_menu(builder, actions)
    )
    menu.AppendSeparator()
    builder.add(
        menu,
        _("Session in&formation…"),
        CommandId.SESSION_INFO,
        _runner(actions, CommandId.SESSION_INFO),
    )
    return menu


def _profile_menu(window: wx.Frame, builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    choices = wx.Menu()
    builder.add_submenu(menu, _("&Choose profile"), CommandId.SET_PROFILE, choices)
    # The free profile stays in the menu, so that its shortcut works with the menu closed; the
    # profiles found follow it, made again each time the menu opens.
    free = builder.add_radio(
        choices,
        _("Free"),
        CommandId.CHOOSE_FREE_PROFILE,
        lambda _event: actions.choose_profile(None),
    )
    window.Bind(
        wx.EVT_MENU_OPEN, lambda event: _fill_profiles(window, choices, free, actions, event)
    )
    builder.add(
        menu,
        _("&Launch the program"),
        CommandId.LAUNCH_PROGRAM,
        _runner(actions, CommandId.LAUNCH_PROGRAM),
    )
    builder.add(menu, _("&Add…"), CommandId.ADD_PROFILE, _runner(actions, CommandId.ADD_PROFILE))
    builder.add(menu, _("&Edit…"), CommandId.EDIT_PROFILE, _runner(actions, CommandId.EDIT_PROFILE))
    builder.add(
        menu,
        _("&Delete"),
        CommandId.DELETE_PROFILE,
        _runner(actions, CommandId.DELETE_PROFILE),
    )
    menu.AppendSeparator()
    builder.add(
        menu,
        _("Define the &variables…"),
        CommandId.DEFINE_VARIABLES,
        _runner(actions, CommandId.DEFINE_VARIABLES),
    )
    return menu


def _fill_profiles(
    window: wx.Frame,
    choices: wx.Menu,
    free: wx.MenuItem,
    actions: MenuActions,
    event: wx.MenuEvent,
) -> None:
    """The profiles found are made when the menu opens, after the free profile."""
    event.Skip()
    for item in list(choices.GetMenuItems()):
        if item.GetId() != free.GetId():
            choices.Delete(item)
    current = actions.current_profile()
    free.Check(current is None)
    for name in actions.profile_names():
        item = choices.AppendRadioItem(wx.ID_ANY, name.replace("&", "&&"))
        item.Check(name == current)
        window.Bind(wx.EVT_MENU, lambda _e, chosen=name: actions.choose_profile(chosen), item)


def _edit_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(menu, _("&Copy"), CommandId.COPY, _runner(actions, CommandId.COPY))
    builder.add(
        menu, _("Select &all"), CommandId.SELECT_ALL, _runner(actions, CommandId.SELECT_ALL)
    )
    menu.AppendSeparator()
    builder.add(menu, _("&Find in the output…"), CommandId.FIND, _runner(actions, CommandId.FIND))
    builder.add(menu, _("Find &next"), CommandId.FIND_NEXT, _runner(actions, CommandId.FIND_NEXT))
    builder.add(
        menu,
        _("Find &previous"),
        CommandId.FIND_PREVIOUS,
        _runner(actions, CommandId.FIND_PREVIOUS),
    )
    menu.AppendSeparator()
    builder.add(menu, _("&History"), CommandId.HISTORY, _runner(actions, CommandId.HISTORY))
    builder.add(
        menu, _("&Resend the last command"), CommandId.RESEND, _runner(actions, CommandId.RESEND)
    )
    builder.add(
        menu, _("Multi-line &input…"), CommandId.MULTILINE, _runner(actions, CommandId.MULTILINE)
    )
    return menu


def _terminal_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    sizes = wx.Menu()
    for size in STANDARD_SIZES:
        text = _("{columns} x {rows}").format(columns=size.columns, rows=size.rows)
        builder.add_choice(
            sizes, "size", size, text, CommandId.SET_SIZE, _bind(actions.set_size, size)
        )
    builder.add_choice(
        sizes, "size", None, _("Automatic"), CommandId.SET_SIZE, _bind(actions.set_size, None)
    )
    builder.add_submenu(menu, _("&Terminal size"), CommandId.SET_SIZE, sizes)
    builder.add_toggle(
        menu,
        _("Terminal &view only"),
        CommandId.SET_TERMINAL_VIEW,
        lambda event: actions.set_terminal_view_only(event.IsChecked()),
    )
    builder.add_submenu(menu, _("&Move"), CommandId.MOVE, _move_menu(builder, actions))
    builder.add_submenu(
        menu, _("&Activities"), CommandId.ACTIVITIES, _activities_menu(builder, actions)
    )
    builder.add_submenu(
        menu,
        _("Comfortable &reading"),
        CommandId.PROMPT_PATTERNS,
        _comfort_menu(builder, actions),
    )
    menu.AppendSeparator()
    builder.add(menu, _("&Clear the output"), CommandId.CLEAR, _runner(actions, CommandId.CLEAR))
    return menu


def _move_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(
        menu,
        _("Go to the &cursor of the terminal"),
        CommandId.GO_TO_CURSOR,
        _runner(actions, CommandId.GO_TO_CURSOR),
    )
    builder.add(
        menu,
        _("Go to the &first line of the terminal"),
        CommandId.GO_TO_EMULATOR_START,
        _runner(actions, CommandId.GO_TO_EMULATOR_START),
    )
    builder.add(
        menu,
        _("Go to the &last line of the terminal"),
        CommandId.GO_TO_EMULATOR_END,
        _runner(actions, CommandId.GO_TO_EMULATOR_END),
    )
    return menu


def _comfort_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(
        menu,
        _("&Previous line, with filtering"),
        CommandId.COMFORT_PREVIOUS,
        _runner(actions, CommandId.COMFORT_PREVIOUS),
    )
    builder.add(
        menu,
        _("&Next line, with filtering"),
        CommandId.COMFORT_NEXT,
        _runner(actions, CommandId.COMFORT_NEXT),
    )
    menu.AppendSeparator()
    builder.add(
        menu,
        _("Line &filtering…"),
        CommandId.PROMPT_PATTERNS,
        _runner(actions, CommandId.PROMPT_PATTERNS),
    )
    return menu


def _activities_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(
        menu,
        _("&Read the line with formatting"),
        CommandId.READ_LINE,
        _runner(actions, CommandId.READ_LINE),
    )
    builder.add(
        menu,
        _("&Identify activities…"),
        CommandId.IDENTIFY_ACTIVITIES,
        _runner(actions, CommandId.IDENTIFY_ACTIVITIES),
    )
    builder.add_toggle(
        menu,
        _("&Signal activities"),
        CommandId.SIGNAL_ACTIVITIES,
        lambda _event: actions.run(CommandId.SIGNAL_ACTIVITIES),
    )
    return menu


def _develop_menu(window: wx.Frame, builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(menu, _("&Catalogs…"), CommandId.CATALOGS, _runner(actions, CommandId.CATALOGS))
    programs = wx.Menu()
    builder.add_submenu(menu, _("&Test programs"), CommandId.TEST_PROGRAMS, programs)
    window.Bind(wx.EVT_MENU_OPEN, lambda event: _fill_programs(window, programs, actions, event))
    builder.add(
        menu,
        _("Convert the &help to HTML"),
        CommandId.CONVERT_HELP,
        _runner(actions, CommandId.CONVERT_HELP),
    )
    return menu


def _fill_programs(
    window: wx.Frame, programs: wx.Menu, actions: MenuActions, event: wx.MenuEvent
) -> None:
    """The test programs are listed when the menu opens, so a new file shows at once."""
    event.Skip()
    for item in list(programs.GetMenuItems()):
        programs.Delete(item)
    found = actions.test_programs()
    for program in found:
        item = programs.Append(wx.ID_ANY, program.stem.replace("&", "&&"))
        window.Bind(wx.EVT_MENU, lambda _e, path=program: actions.run_test_program(path), item)
    if not found:
        programs.Append(wx.ID_ANY, _("(none)")).Enable(False)


def _help_menu(builder: MenuBuilder, actions: MenuActions) -> wx.Menu:
    menu = wx.Menu()
    builder.add(
        menu, _("&Open the help"), CommandId.OPEN_HELP, _runner(actions, CommandId.OPEN_HELP)
    )
    builder.add(
        menu, _("Open the &logs folder"), CommandId.OPEN_LOGS, _runner(actions, CommandId.OPEN_LOGS)
    )
    builder.add(menu, _("&About"), CommandId.ABOUT, _runner(actions, CommandId.ABOUT))
    return menu
