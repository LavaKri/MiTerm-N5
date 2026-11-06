"""What the session presenter asks of its window. The wx window implements it; tests use a fake."""

import enum
from typing import Protocol

from n5terminal.core.screen.screen_model import ScreenUpdate
from n5terminal.core.session.session_state import CommandId, SessionState


class InputMode(enum.Enum):
    """What the command field is for; the box that hides the text follows it."""

    COMMAND = "command"  # no program: the text is a command line to launch
    PROGRAM_INPUT = "program_input"  # a program runs: the text is sent to it


class DialogView(Protocol):
    """The dialogs a connection opens, as the window gives them. Always called on the UI thread.

    ``title`` and ``where`` say which connection asks and where it goes (``Connection to prod``,
    ``admin@example.org, port 2222``): the user always knows who is asking for a password.
    """

    def confirm_host_key(self, title: str, where: str, text: str) -> bool:
        """Show the host key question of ``ssh`` (the text holds the fingerprint); ``True`` to trust
        the server. Cancelling is the default answer."""
        ...

    def ask_secret(self, title: str, where: str, question: str) -> str | None:
        """Ask for a password, a passphrase or a code in a hidden field; ``None`` if cancelled."""
        ...

    def withdraw_dialog(self) -> None:
        """Close the dialog still open, if any, as a cancel (its question is not waiting)."""
        ...


class SessionView(DialogView, Protocol):
    """The window of a session, seen from its presenter. Always called from the UI thread."""

    def show_output(self, update: ScreenUpdate, dropped_lines: int) -> int:
        """Append ``update.fixed`` to the fixed part and change the live part as the update says.

        ``dropped_lines`` fixed lines were lost before the first one of this update. Returns how
        many of the oldest lines the limit of the output removed to make room.
        """
        ...

    def focus_output(self) -> None:
        """Put the focus in the output area; the text caret stays where it is."""
        ...

    def focus_output_on_command(self, lines: int) -> None:
        """Put the focus in the output area and the caret at the start of the command written.

        ``lines`` is how many lines the written command takes; 0 if it is not written (then the
        caret goes to the start of the live part).
        """
        ...

    def output_has_focus(self) -> bool:
        """Is the focus in the output area?"""
        ...

    def caret_line(self) -> tuple[str, bool]:
        """The line of the text caret, and whether the terminal cursor is inside its text."""
        ...

    def clear_output(self) -> None:
        """Empty the output area."""
        ...

    def show_state(self, state: SessionState) -> None:
        """The state changed: the choices of the menus (mode, interpreter) show the real values."""
        ...

    def set_commands_enabled(self, enabled: frozenset[CommandId]) -> None:
        """Enable these commands and disable (never hide) the others."""
        ...

    def set_input_mode(self, mode: InputMode, label: str) -> None:
        """Change what the command field is for; ``label`` is its name, as the user hears it."""
        ...

    def clear_input(self) -> None:
        """Empty the command field."""
        ...

    def set_status_state(self, text: str) -> None:
        """Second field of the status bar: the state of the session."""
        ...

    def set_title(self, text: str) -> None:
        """The title of the window: the profile and the working folder."""
        ...
