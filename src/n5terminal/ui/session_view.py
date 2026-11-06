"""The window of a session as the presenter sees it: ``SessionView`` on the widgets."""

import wx

from n5terminal.core.screen.screen_model import ScreenUpdate
from n5terminal.core.screen.text_search import cursor_is_on_line_text, line_at
from n5terminal.core.session.session_state import CommandId, SessionState
from n5terminal.presenters.session_view import InputMode
from n5terminal.ui.command_panel import CommandPanel
from n5terminal.ui.connection_prompts import ConnectionPrompts
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.output_area import OutputArea


class WxSessionView:
    """Implements :class:`~n5terminal.presenters.session_view.SessionView`."""

    def __init__(
        self,
        output: OutputArea,
        command: CommandPanel,
        feedback: Feedback,
        menus: MenuBuilder,
        prompts: ConnectionPrompts,
    ) -> None:
        self._output = output
        self._command = command
        self._feedback = feedback
        self._menus = menus
        self._prompts = prompts

    def show_output(self, update: ScreenUpdate, dropped_lines: int) -> int:
        return self._output.show(update)

    def focus_output(self) -> None:
        self._output.SetFocus()

    def focus_output_on_command(self, lines: int) -> None:
        self._output.focus_on_command(lines)

    def output_has_focus(self) -> bool:
        return wx.Window.FindFocus() is self._output

    def caret_line(self) -> tuple[str, bool]:
        text, caret = self._output.text, self._output.caret_index()
        on_text = cursor_is_on_line_text(text, caret, self._output.terminal_cursor_index())
        return line_at(text, caret), on_text

    def clear_output(self) -> None:
        self._output.clear_text()

    def show_state(self, state: SessionState) -> None:
        self._menus.check("mode", state.effective_launch_mode)
        self._menus.check("interpreter", state.interpreter)

    def confirm_host_key(self, title: str, where: str, text: str) -> bool:
        return self._prompts.confirm_host_key(title, where, text)

    def ask_secret(self, title: str, where: str, question: str) -> str | None:
        return self._prompts.ask_secret(title, where, question)

    def withdraw_dialog(self) -> None:
        self._prompts.withdraw()

    def set_commands_enabled(self, enabled: frozenset[CommandId]) -> None:
        self._menus.apply_enabled(enabled)

    def set_input_mode(self, mode: InputMode, label: str) -> None:
        self._command.set_input_mode(mode, label)

    def clear_input(self) -> None:
        self._command.clear()

    def set_status_state(self, text: str) -> None:
        self._feedback.set_state(text)

    def set_title(self, text: str) -> None:
        self._feedback.set_title(text)
