"""The main window: layout and wiring only, the logic is in the presenter.

From top to bottom: the output area, the command field and its button, the status bar. The widgets
are created in the order of the Tab key: the command field, the button, then the output area.
"""

from pathlib import Path

import wx

from n5terminal.core.config.announcements import Beeper
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.connections import ConnectionStore
from n5terminal.core.config.keys import SENT_KEYS, SentKey
from n5terminal.core.config.location import APP_NAME
from n5terminal.core.config.profiles import ProfileStore
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    KEY_COMMANDS,
    ConfigurableCommand,
)
from n5terminal.core.screen.terminal_size import size_from_text
from n5terminal.core.session.command_shortcuts import COMMAND_OF_SHORTCUT
from n5terminal.core.session.launcher import Launcher
from n5terminal.core.session.session_state import CommandId, Phase, command_states, refusal
from n5terminal.i18n import _
from n5terminal.presenters.connection_catalog import ConnectionCatalog
from n5terminal.presenters.profile_catalog import ProfileCatalog
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.presenters.session_run import SessionServices
from n5terminal.ui.actions import WindowActions
from n5terminal.ui.command_panel import CommandPanel
from n5terminal.ui.connection_prompts import ConnectionPrompts
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.foreground_guard import ForegroundGuard
from n5terminal.ui.main_menu import build_menu_bar
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.output_area import OutputArea
from n5terminal.ui.send_menu import build_command_menu, build_output_menu
from n5terminal.ui.session_view import WxSessionView
from n5terminal.ui.shortcut_keys import shortcut_from_event

TICK_MS = 50  # the output reaches the window every 50 ms


class MainWindow(wx.Frame):
    """One window, one session."""

    def __init__(
        self,
        settings: Settings,
        launcher: Launcher,
        folder: Path,
        context: AppContext | None = None,
        beeper: Beeper | None = None,
    ) -> None:
        super().__init__(None, title=APP_NAME, size=wx.Size(960, 680))
        context = context or AppContext()
        self._settings = settings
        self._closing = False
        self.feedback = Feedback(self, settings, lambda: self._closing, beeper)
        self.menus = menus = MenuBuilder(self, settings)
        panel = wx.Panel(self)
        self.command = CommandPanel(
            panel,
            on_submit=lambda text, hidden: self.presenter.submit(text, hidden=hidden),
        )
        output_label = wx.StaticText(panel, label=_("Output"))
        self.output = OutputArea(
            panel,
            settings.output_limit,
            on_title=lambda level, backwards: self.actions.title_key(level, backwards),
            on_position=self.feedback.set_position,
            show_history=not settings.terminal_view_only,
        )
        self._layout(panel, output_label)
        self.feedback.apply_screen_reader_output(settings.screen_reader_output)

        prompts = ConnectionPrompts(self, self.feedback)
        view = WxSessionView(self.output, self.command, self.feedback, menus, prompts)
        services = SessionServices(launcher, settings, self.feedback.announcements, wx.CallAfter)
        self.presenter = SessionPresenter(view, services, folder)
        store = ProfileStore(context.profiles_folder) if context.profiles_folder else None
        catalog = ProfileCatalog(store)
        self.profile_warnings = catalog.warnings  # to show once the window is up
        connection_store = (
            ConnectionStore(context.connections_folder) if context.connections_folder else None
        )
        connections = ConnectionCatalog(connection_store)
        self.connection_warnings = connections.warnings  # to show once the window is up
        self.actions = WindowActions(
            self,
            self.presenter,
            self.feedback,
            self.output,
            self.command,
            settings,
            menus,
            context,
            catalog,
            connections,
            self.refresh_shortcuts,
        )
        develop = context.develop_folder is not None
        self.SetMenuBar(build_menu_bar(self, menus, self.actions, develop))
        self.command.set_context_menu(build_command_menu(menus, self.actions))
        self.output.set_context_menu(build_output_menu(menus, self.actions))
        self.SetStatusBarPane(-1)  # the help of a menu item must not replace the state
        self._show_menu_state(menus)

        self._shortcuts = self._shortcut_commands()
        self.SetAcceleratorTable(wx.AcceleratorTable(menus.break_accelerators()))
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._timer = wx.Timer(self)
        self._foreground = ForegroundGuard(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(TICK_MS)
        wx.CallAfter(self.command.focus_field)  # the initial focus

    def _on_timer(self, _event: wx.TimerEvent) -> None:
        self.presenter.tick()
        self._foreground.check()

    def _layout(self, panel: wx.Panel, output_label: wx.StaticText) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(output_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.output, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.command, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(sizer)

    def _show_menu_state(self, menus: MenuBuilder) -> None:
        """The menus exist now: show them what the presenter showed to nobody at its start."""
        state = self.presenter.state
        menus.apply_enabled(command_states(state))
        menus.check("mode", state.effective_launch_mode)
        menus.check("interpreter", state.interpreter)
        menus.check("size", size_from_text(self._settings.terminal_size))
        menus.set_checked(CommandId.SET_TERMINAL_VIEW, self._settings.terminal_view_only)
        self.actions.refresh_activity_check()

    def refresh_shortcuts(self) -> None:
        """The shortcuts of the settings changed: write them in the menus and take them as keys."""
        self.menus.refresh_shortcuts()
        self._shortcuts = self._shortcut_commands()
        self.SetAcceleratorTable(wx.AcceleratorTable(self.menus.break_accelerators()))

    def _shortcut_commands(self) -> dict[str, CommandId | SentKey]:
        """The command of each shortcut chosen, and the key sent by each key shortcut chosen."""
        found: dict[str, CommandId | SentKey] = {}
        for shortcut in CONFIGURABLE_COMMANDS:
            command = COMMAND_OF_SHORTCUT.get(shortcut.id)
            keys = self._settings.shortcut_for(shortcut)
            if command is not None and keys:
                found[keys] = command
        for key in SENT_KEYS:
            keys = self._settings.shortcut_for(self._key_command(key))
            if keys:
                found[keys] = key
        return found

    @staticmethod
    def _key_command(key: SentKey) -> ConfigurableCommand:
        return next(command for command in KEY_COMMANDS if command.id == f"key.{key.id}")

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        """Tells why a shortcut does nothing; the menu does the command when it can be done.

        The shortcut of an item is its accelerator: wx runs the item, as a click would. But the
        accelerator of a greyed item is ignored in silence, and the key would go on to the control
        (Shift+Enter submits the command field): here the reason is announced and the key is
        taken. A command that is available is left to the menu.
        """
        shortcut = shortcut_from_event(event)
        command = self._shortcuts.get(shortcut) if shortcut else None
        if command is None:
            event.Skip()
            return
        asked = CommandId.SEND_KEY if isinstance(command, SentKey) else command
        if refusal(asked, self.presenter.state) is None:
            event.Skip()
        elif isinstance(command, SentKey):
            self.actions.send_key(command)  # refused: says why
        else:
            self.actions.run(command)  # refused: says why

    def _on_close(self, event: wx.CloseEvent) -> None:
        if self._closing:
            return  # wx destroys the window later: this close came before, all is already done
        running = self.presenter.state.phase is not Phase.IDLE
        if (
            running
            and event.CanVeto()
            and not self.feedback.confirm(_("Quit"), _("A program is running. Stop it and quit?"))
        ):
            event.Veto()
            return
        self._closing = True
        self._timer.Stop()
        self.presenter.stop()
        self.feedback.save_settings()
        self.feedback.close()
        self.Destroy()
