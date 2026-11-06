"""What the user chooses for the next program of a session: shell, mode, profile, size.

Split from ``session_presenter.py`` (one subject per file). It owns the values that are not part of
the state (the size, the mark of the standard error, the prompt prefix) and changes the others
through the presenter's ``get_state`` and ``set_state``. Every choice is refused, with an
announcement that says why, when the state does not allow it (``refusal``).
"""

from collections.abc import Callable
from dataclasses import replace

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.config.profiles import Profile
from n5terminal.core.config.settings import AUTOMATIC_SIZE, Settings
from n5terminal.core.screen.terminal_size import (
    DEFAULT_SIZE,
    SizeChoice,
    size_from_text,
    size_text,
)
from n5terminal.core.session.powershells import powershell_name
from n5terminal.core.session.session_state import (
    CommandId,
    Interpreter,
    LaunchMode,
    SessionState,
    refusal,
)
from n5terminal.presenters.profile_values import ProfileValues


class SessionChoices:
    """The choices of a session. ``say`` announces a refusal or a change."""

    def __init__(
        self,
        settings: Settings,
        profile_values: ProfileValues,
        get_state: Callable[[], SessionState],
        set_state: Callable[[SessionState], None],
        say: Say,
    ) -> None:
        self._settings = settings
        self._profile_values = profile_values
        self._get_state = get_state
        self._set_state = set_state
        self._say = say
        self.size = SizeChoice()
        self.size.choose(size_from_text(settings.terminal_size), DEFAULT_SIZE)
        self.mark_stderr = settings.stderr_prefix
        self.prompt_prefix = ""  # the profile's, for a shell that stays open

    def _allowed(self, command: CommandId) -> bool:
        reason = refusal(command, self._get_state())
        if reason is not None:
            self._say(reason)
        return reason is None

    def set_interpreter(self, interpreter: Interpreter) -> bool:
        """Choose the shell the commands go through; only with no program."""
        if not self._allowed(CommandId.SET_INTERPRETER):
            return False
        self._set_state(replace(self._get_state(), interpreter=interpreter))
        return True

    @property
    def powershell_path(self) -> str:
        """The PowerShell the interpreter starts (empty: Windows PowerShell)."""
        return self._settings.powershell_path

    def set_powershell_path(self, path: str) -> bool:
        """Choose the PowerShell for the next shell (a global setting); only with no program.

        The caller saves the settings. The change is announced.
        """
        if not self._allowed(CommandId.SELECT_POWERSHELL):
            return False
        self._settings.powershell_path = path.strip()
        self._say(Announce.POWERSHELL_CHANGED, powershell=powershell_name(path))
        return True

    def set_launch_mode(self, launch_mode: LaunchMode) -> bool:
        """Choose CLI or TUI for the next program; only with no program and no shell."""
        if not self._allowed(CommandId.SET_MODE):
            return False
        self._set_state(replace(self._get_state(), launch_mode=launch_mode))
        return True

    def select_profile(self, profile: Profile | None) -> bool:
        """Choose a profile, or ``None`` for the free profile; only with no program.

        A profile replaces the mode, the interpreter, the size, the mark of the standard error and
        the prompt prefix of the session (the terminal view is the window's). The free profile
        changes no value. Nothing is announced.
        """
        if not self._allowed(CommandId.SET_PROFILE):
            return False
        state = self._get_state()
        self._profile_values.choose(profile)
        if profile is None:
            self._set_state(replace(state, profile=None, has_variables=False, has_program=False))
            return True
        self.size.choose(size_from_text(profile.terminal_size), self.size.size)
        self.mark_stderr = profile.stderr_prefix
        self.prompt_prefix = profile.prompt_prefix
        self._set_state(
            replace(
                state,
                profile=profile.name,
                has_variables=bool(profile.variables),
                has_program=bool(profile.program) and profile.interpreter == "none",
                interpreter=Interpreter(profile.interpreter),
                launch_mode=LaunchMode(profile.launch_mode),
            )
        )
        return True

    def session_values(self, name: str = "") -> Profile:
        """A profile named ``name`` holding the mode, interpreter and size now in use.

        The display is the window's to add. Used to start the profile dialog on what is in use.
        """
        state = self._get_state()
        return Profile(
            name,
            launch_mode=state.effective_launch_mode.value,
            interpreter=state.interpreter.value,
            terminal_size=AUTOMATIC_SIZE if self.size.is_automatic else size_text(self.size.size),
            stderr_prefix=self.mark_stderr,
            prompt_prefix=self.prompt_prefix,
        )
