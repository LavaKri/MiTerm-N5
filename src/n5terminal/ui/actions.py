"""What the commands of the main window do: the glue between the menus, the keys and the presenter.

A command is first asked of the presenter (``run_command``), which refuses it with an announcement
that says why when the state of the session does not allow it; only an allowed command reaches the
dialogs and widgets handled here.
"""

import logging
import os
from collections.abc import Callable
from pathlib import Path

import wx

from n5terminal import __version__
from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.keys import SentKey
from n5terminal.core.config.launch_file import LaunchFile
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import NewSessionError
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.new_session import start_new_session
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode
from n5terminal.i18n import _
from n5terminal.presenters.command_label import is_block
from n5terminal.presenters.connection_catalog import ConnectionCatalog
from n5terminal.presenters.profile_catalog import ProfileCatalog
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.presenters.session_report import session_report
from n5terminal.presenters.title_navigation import TitleNavigator
from n5terminal.ui.command_panel import CommandPanel
from n5terminal.ui.connection_actions import ConnectionActions
from n5terminal.ui.develop_actions import DevelopActions
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.help_actions import HelpActions
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.multiline_dialog import MultilineDialog
from n5terminal.ui.output_area import OutputArea
from n5terminal.ui.output_commands import OutputCommands
from n5terminal.ui.profile_actions import ProfileActions
from n5terminal.ui.prompt_actions import PromptActions
from n5terminal.ui.settings_actions import SettingsActions

logger = logging.getLogger(__name__)


class WindowActions:
    """Implements ``MenuActions`` and the keys of the output area and of the command field.

    The Profile menu is ``ProfileActions``, the Develop menu ``DevelopActions``; the methods the
    menus call for them are passed on from here. The commands that change a setting are
    ``SettingsActions``.
    """

    def __init__(
        self,
        frame: wx.Frame,
        presenter: SessionPresenter,
        feedback: Feedback,
        output: OutputArea,
        command: CommandPanel,
        settings: Settings,
        menus: MenuBuilder,
        context: AppContext,
        catalog: ProfileCatalog,
        connection_catalog: ConnectionCatalog,
        on_shortcuts_changed: Callable[[], None] = lambda: None,
    ) -> None:
        self._context = context
        self._frame = frame
        self._presenter = presenter
        self._feedback = feedback
        self._output = output
        self._command = command
        self._draft = ""  # lines typed in the multi-line input and not sent (never saved)
        self._settings = settings
        self._menus = menus
        self._profiles = ProfileActions(frame, presenter, feedback, output, menus, catalog)
        self._connections = ConnectionActions(
            frame, presenter, feedback, settings, connection_catalog
        )
        self._develop = DevelopActions(frame, presenter, feedback, context.develop_folder)
        self._settings_actions = SettingsActions(
            frame,
            presenter,
            feedback,
            output,
            settings,
            menus,
            context.association,
            self._profiles.names,
            on_shortcuts_changed,
        )
        help_actions = HelpActions(presenter, feedback, settings, context.help_folder)
        self._navigator = TitleNavigator(presenter.say, settings)
        output_commands = OutputCommands(presenter, feedback, output, settings)
        prompts = PromptActions(frame, feedback, settings)
        self._handlers: dict[CommandId, Callable[[], None]] = {
            CommandId.NEW_SESSION: self._new_session,
            CommandId.CHOOSE_FOLDER: self._choose_folder,
            CommandId.EXPORT: output_commands.export,
            CommandId.QUIT: lambda: self._frame.Close(),
            CommandId.COPY: self._copy,
            CommandId.SELECT_ALL: self._select_all,
            CommandId.FIND: output_commands.find,
            CommandId.FIND_NEXT: output_commands.find_next,
            CommandId.FIND_PREVIOUS: output_commands.find_previous,
            CommandId.GO_TO_CURSOR: output_commands.go_to_cursor,
            CommandId.GO_TO_EMULATOR_START: output_commands.go_to_emulator_start,
            CommandId.GO_TO_EMULATOR_END: output_commands.go_to_emulator_end,
            CommandId.READ_LINE: output_commands.read_line,
            CommandId.PROMPT_PATTERNS: prompts.edit,
            CommandId.COMFORT_PREVIOUS: output_commands.comfort_previous,
            CommandId.COMFORT_NEXT: output_commands.comfort_next,
            CommandId.IDENTIFY_ACTIVITIES: output_commands.identify_activities,
            CommandId.SIGNAL_ACTIVITIES: self._settings_actions.toggle_activity,
            CommandId.NEXT_TITLE: lambda: self.go_to_title(None, backwards=False),
            CommandId.PREVIOUS_TITLE: lambda: self.go_to_title(None, backwards=True),
            CommandId.HISTORY: self.show_history,
            CommandId.MULTILINE: self._multiline_input,
            CommandId.PREFERENCES: self._settings_actions.preferences,
            CommandId.SELECT_POWERSHELL: self._settings_actions.select_powershell,
            CommandId.ADD_PROFILE: self._profiles.add,
            CommandId.EDIT_PROFILE: self._profiles.edit,
            CommandId.DELETE_PROFILE: self._profiles.delete,
            CommandId.DEFINE_VARIABLES: self._profiles.define_variables,
            CommandId.ADD_CONNECTION: self._connections.add,
            CommandId.EDIT_CONNECTION: self._connections.edit,
            CommandId.DELETE_CONNECTION: self._connections.delete,
            CommandId.SELECT_SSH: self._connections.select_ssh,
            CommandId.OPEN_LOGS: self._open_logs,
            CommandId.ABOUT: self._about,
            CommandId.OPEN_HELP: help_actions.open,
            CommandId.CONVERT_HELP: help_actions.convert,
            CommandId.CATALOGS: self._develop.catalogs,
            CommandId.SESSION_INFO: self._session_info,
            CommandId.CHOOSE_FREE_PROFILE: lambda: self.choose_profile(None),
            CommandId.CHOOSE_LOCAL: lambda: self.choose_connection(None),
        }

    def run(self, command: CommandId) -> None:
        """Do ``command``, or say why it cannot be done now."""
        logger.debug("Command: %s", command.name)
        if not self._presenter.run_command(command):
            return
        handler = self._handlers.get(command)
        if handler is not None:
            handler()

    # Choices of the menus ----------------------------------------------------------------------

    def recent_folders(self) -> list[Path]:
        return [Path(folder) for folder in self._settings.recent_folders]

    def open_recent(self, folder: Path) -> None:
        self._presenter.set_working_folder(folder)

    def set_mode(self, mode: LaunchMode) -> None:
        self._presenter.set_launch_mode(mode)
        self._menus.check("mode", self._presenter.state.effective_launch_mode)

    def set_interpreter(self, interpreter: Interpreter) -> None:
        self._presenter.set_interpreter(interpreter)
        self._menus.check("interpreter", self._presenter.state.interpreter)

    def set_size(self, size: TerminalSize | None) -> None:
        self._presenter.set_terminal_size(size)

    def set_terminal_view_only(self, view_only: bool) -> None:
        self._output.set_show_history(not view_only)

    def refresh_activity_check(self) -> None:
        self._settings_actions.refresh_activity_check()

    def _session_info(self) -> None:
        """Show what is known of the session in the box of text of the application."""
        text = session_report(
            self._presenter,
            self._settings,
            self._context,
            output_lines=self._output.GetNumberOfLines(),
            terminal_view_only=not self._output.show_history,
        )
        self._feedback.show_text(_("Session information"), text)

    # The Profile and Develop menus (see ``ProfileActions`` and ``DevelopActions``) -------------

    def profile_names(self) -> list[str]:
        return self._profiles.names()

    def current_profile(self) -> str | None:
        return self._profiles.current()

    def choose_profile(self, name: str | None) -> None:
        self._profiles.choose(name)

    def connection_names(self) -> list[str]:
        return self._connections.names()

    def current_connection(self) -> str | None:
        return self._connections.current()

    def choose_connection(self, name: str | None) -> None:
        self._connections.choose(name)

    def apply_launch_file(self, launch: LaunchFile) -> list[str]:
        return self._profiles.apply_launch_file(launch)

    def apply_startup_profile(self, name: str) -> list[str]:
        return self._profiles.apply_startup_profile(name)

    def test_programs(self) -> list[Path]:
        return self._develop.test_programs()

    def run_test_program(self, program: Path) -> None:
        self._develop.run_test_program(program)

    def send_key(self, key: SentKey) -> None:
        """Send ``key`` to the program, or say why it cannot be (the menus and the shortcuts)."""
        self._presenter.send_key(key)

    # Keys --------------------------------------------------------------------------------------

    def title_key(self, level: int | None, backwards: bool) -> None:
        """The keys 1 to 6 and T of the output area: the same command as the menu's two items.

        With no output the command is refused, and the reason announced, whichever way it is asked.
        """
        command = CommandId.PREVIOUS_TITLE if backwards else CommandId.NEXT_TITLE
        if level is None:
            self.run(command)
        elif self._presenter.run_command(command):
            self.go_to_title(level, backwards)

    def go_to_title(self, level: int | None, backwards: bool) -> None:
        """The keys 1 to 6 and T of the output area: the caret goes to the title."""
        index = self._navigator.go(
            self._output.text, self._output.caret_index(), level, backwards=backwards
        )
        if index is not None:
            self._output.move_to(index)

    def show_history(self) -> None:
        """Ctrl+Space: the commands typed so far, to pick one into the field."""
        entries, selected = self._presenter.command_list()
        if not entries:
            self._presenter.say(Announce.HISTORY_EMPTY)
            return
        self._command.focus_field()
        labels = [entry.label for entry in entries]
        choice = self._feedback.choose(_("Command history"), _("Commands"), labels, selected)
        if choice is None:
            return
        text = entries[choice].text
        if is_block(text):  # a block does not fit the field: it is read and sent in its own box
            # After this box is gone and the focus given back, not from inside its handler.
            wx.CallAfter(self._multiline_input, text)
        else:
            self._command.show_text(text)

    def _multiline_input(self, block: str | None = None) -> None:
        """Ctrl+M: a box for several lines. Send sends them, Escape keeps them for the next time.

        It opens on ``block`` (picked in the history), else on the lines kept the last time, else
        on the text of the command field.
        """
        start = block if block is not None else (self._draft or self._command.field.GetValue())
        with MultilineDialog(self._frame, start) as dialog:
            sent = self._feedback.modal(dialog) == wx.ID_OK
            value = dialog.value()
        if sent:
            self._draft = ""
            if value.strip():
                self._presenter.submit(value)
        elif block is None:
            self._draft = value

    # Commands with a dialog --------------------------------------------------------------------

    def _new_session(self) -> None:
        try:
            start_new_session(
                self._presenter.working_folder,
                self._context.data_folder,
                self._context.develop_folder is not None,
            )
        except NewSessionError as error:
            self._feedback.show_error(
                _("A new session could not be started.\n{error}").format(error=error)
            )

    def _choose_folder(self) -> None:
        folder = self._feedback.choose_folder(self._presenter.working_folder)
        if folder is not None:
            self._presenter.set_working_folder(folder)

    def _copy(self) -> None:
        focused = wx.Window.FindFocus()
        if isinstance(focused, wx.TextCtrl):
            focused.Copy()

    def _select_all(self) -> None:
        focused = wx.Window.FindFocus()
        if isinstance(focused, wx.TextCtrl):
            focused.SelectAll()

    def _open_logs(self) -> None:
        """Show the folder of the log file in the file explorer."""
        folder = self._context.log_folder
        if folder is None or not folder.is_dir():
            self._feedback.show_info(_("There is no log yet."))
            return
        try:
            os.startfile(folder)
        except OSError as error:
            self._feedback.show_error(
                _("The log folder could not be opened.\n{error}").format(error=error)
            )

    def _about(self) -> None:
        self._feedback.show_text(
            _("About"),
            _("MiTerm-N5 {version}\nA terminal that a screen reader can read.").format(
                version=__version__
            ),
        )
