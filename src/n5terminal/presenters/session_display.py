"""What the window shows of the state of a session, given to it only when it changes.

Split from ``session_presenter.py`` (one subject per file): the window is not told twice the same
choices, enabled commands, input mode, status or title.
"""

from n5terminal.core.session.session_state import (
    CommandId,
    Interpreter,
    LaunchMode,
    Phase,
    SessionState,
    command_states,
)
from n5terminal.presenters.session_view import InputMode, SessionView


class SessionDisplay:
    """Pushes the changes of the state of a session to its window."""

    def __init__(self, view: SessionView) -> None:
        self._view = view
        self._choices: tuple[LaunchMode, Interpreter, str | None] | None = None
        self._enabled: frozenset[CommandId] | None = None
        self._mode: tuple[InputMode, str] | None = None
        self._status: str | None = None
        self._title: str | None = None

    def show(self, state: SessionState, status: str, title: str, label: str) -> None:
        """Give the window what differs from what it was given before."""
        choices = (state.effective_launch_mode, state.interpreter, state.connection)
        if choices != self._choices:
            self._choices = choices
            self._view.show_state(state)
        enabled = command_states(state)
        if enabled != self._enabled:
            self._enabled = enabled
            self._view.set_commands_enabled(enabled)
        mode = InputMode.COMMAND if state.phase is Phase.IDLE else InputMode.PROGRAM_INPUT
        if (mode, label) != self._mode:
            self._mode = (mode, label)
            self._view.set_input_mode(mode, label)
        if status != self._status:
            self._status = status
            self._view.set_status_state(status)
        if title != self._title:
            self._title = title
            self._view.set_title(title)
