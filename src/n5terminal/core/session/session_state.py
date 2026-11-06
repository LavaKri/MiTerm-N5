"""The state of a session and the commands it allows.

One frozen state decides what the interface offers (see "State of the session and available
commands" in ``specs/architecture/session.md``). The presenter changes the state; ``command_states``
says which commands are enabled and ``refusal`` why another one is not. The view disables the
others, it never hides them. Nothing here knows about ``wx``.
"""

import enum
from collections.abc import Callable
from dataclasses import dataclass

from n5terminal.core.config.announcements import Announce


class Phase(enum.Enum):
    """Where the program of the session is."""

    IDLE = "idle"  # no program: the command field launches one
    RUNNING = "running"
    CHILD_ACTIVE = "child_active"  # the program ended, a process it started still writes


class Mode(enum.Enum):
    """How the program is served (see "Vocabulary" in ``specs/architecture.md``)."""

    PIPES = "pipes"  # modes 1 to 3
    TERMINAL_LINE = "terminal_line"  # mode 4
    TERMINAL_SCREEN = "terminal_screen"  # mode 5

    @property
    def is_terminal(self) -> bool:
        """Is the program served through a pseudo console?"""
        return self is not Mode.PIPES


class LaunchMode(enum.Enum):
    """How the user wants the next program served; the designation is the acronym.

    CLI (plain text, pipes) or TUI (interactive terminal, pseudo console). The hint shown beside
    each ("texte simple", "terminal interactif") only explains it. A shell is always TUI.
    """

    CLI = "cli"
    TUI = "tui"


class Interpreter(enum.Enum):
    """The shell the commands go through (None: direct launch of programs)."""

    NONE = "none"
    CMD = "cmd"
    POWERSHELL = "powershell"


@dataclass(slots=True, frozen=True)
class SessionState:
    """What the commands depend on. Only the session presenter makes a new one.

    ``mode`` only means something while a program runs. ``shell_at_prompt`` only means something
    when the program is a shell that stays open (``interpreter`` is not ``NONE``): it waits for a
    command rather than runs one.
    """

    phase: Phase = Phase.IDLE
    mode: Mode = Mode.PIPES
    interpreter: Interpreter = Interpreter.NONE
    shell_at_prompt: bool = False
    has_output: bool = False
    has_history: bool = False  # does the list of Ctrl+Space hold a typed line for this moment?
    launch_mode: LaunchMode = LaunchMode.CLI
    profile: str | None = None  # the name of the chosen profile (None: the free profile)
    has_variables: bool = False  # does the chosen profile use variables?
    has_program: bool = False  # does the chosen profile name a program?
    connection: str | None = None  # the name of the chosen connection (None: Locale)

    @property
    def on_server(self) -> bool:
        """Is a connection chosen? Then everything runs on the server: nothing local is launched."""
        return self.connection is not None

    @property
    def effective_launch_mode(self) -> LaunchMode:
        """The mode the next program gets: a shell that stays open is always TUI."""
        return LaunchMode.TUI if self.interpreter is not Interpreter.NONE else self.launch_mode

    @property
    def program_active(self) -> bool:
        """Is a program, or a process it left, still there?"""
        return self.phase is not Phase.IDLE

    @property
    def shell_ready(self) -> bool:
        """Is a shell that stays open waiting at its prompt?"""
        return (
            self.phase is Phase.RUNNING
            and self.interpreter is not Interpreter.NONE
            and self.shell_at_prompt
        )


class CommandId(enum.Enum):
    """The commands of the menus, buttons and shortcuts."""

    NEW_SESSION = "new_session"
    CHOOSE_FOLDER = "choose_folder"
    RECENT_FOLDERS = "recent_folders"
    EXPORT = "export"
    PREFERENCES = "preferences"
    QUIT = "quit"
    STOP = "stop"
    RESEND = "resend"
    MULTILINE = "multiline"
    COMFORT_PREVIOUS = "comfort_previous"
    COMFORT_NEXT = "comfort_next"
    PROMPT_PATTERNS = "prompt_patterns"  # the dialog of the prompts left out of a line read
    CLEAR = "clear"
    SET_INTERPRETER = "set_interpreter"
    SELECT_POWERSHELL = "select_powershell"  # also the Interpreter sub-menu that holds it
    SET_MODE = "set_mode"
    SET_CONNECTION = "set_connection"
    CHOOSE_LOCAL = "choose_local"  # the item Local of that sub-menu
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ADD_CONNECTION = "add_connection"
    EDIT_CONNECTION = "edit_connection"
    DELETE_CONNECTION = "delete_connection"
    SELECT_SSH = "select_ssh"
    SET_PROFILE = "set_profile"
    CHOOSE_FREE_PROFILE = "choose_free_profile"  # the item Free of that sub-menu
    ADD_PROFILE = "add_profile"
    EDIT_PROFILE = "edit_profile"
    DELETE_PROFILE = "delete_profile"
    DEFINE_VARIABLES = "define_variables"
    LAUNCH_PROGRAM = "launch_program"
    COPY = "copy"
    SELECT_ALL = "select_all"
    FIND = "find"
    FIND_NEXT = "find_next"
    FIND_PREVIOUS = "find_previous"
    NEXT_TITLE = "next_title"  # in the context menu of the output (keys T, 1 to 6)
    PREVIOUS_TITLE = "previous_title"
    SET_SIZE = "set_size"
    SET_TERMINAL_VIEW = "set_terminal_view"
    MOVE = "move"  # the sub-menu of the movements in the terminal
    ACTIVITIES = "activities"  # the sub-menu of the activities
    READ_LINE = "read_line"
    IDENTIFY_ACTIVITIES = "identify_activities"
    SIGNAL_ACTIVITIES = "signal_activities"
    GO_TO_CURSOR = "go_to_cursor"
    GO_TO_EMULATOR_START = "go_to_emulator_start"
    GO_TO_EMULATOR_END = "go_to_emulator_end"
    HISTORY = "history"
    OPEN_LOGS = "open_logs"
    ABOUT = "about"
    OPEN_HELP = "open_help"
    CONVERT_HELP = "convert_help"  # develop mode
    SEND_KEY = "send_key"
    SESSION_INFO = "session_info"
    CATALOGS = "catalogs"  # develop mode
    TEST_PROGRAMS = "test_programs"  # develop mode


@dataclass(slots=True, frozen=True)
class Rule:
    """When a command is available, and what is said when it is not."""

    available: Callable[[SessionState], bool]
    # None: the command is always available. A function when the reason depends on the state.
    refusal: Announce | Callable[[SessionState], Announce] | None = None


def _always(_state: SessionState) -> bool:
    return True


def _folder_can_change(state: SessionState) -> bool:
    return state.phase is Phase.IDLE or state.shell_ready


def _display_applies(state: SessionState) -> bool:
    return state.phase is Phase.IDLE or state.mode.is_terminal


def _live_part_can_be_reached(state: SessionState) -> bool:
    return state.has_output and _display_applies(state)


def _why_live_part_cannot_be_reached(state: SessionState) -> Announce:
    if not state.has_output:
        return Announce.UNAVAILABLE_NO_OUTPUT
    return Announce.UNAVAILABLE_NOT_TERMINAL


def _key_can_be_sent(state: SessionState) -> bool:
    return state.phase is Phase.RUNNING and state.mode.is_terminal


def _why_key_cannot_be_sent(state: SessionState) -> Announce:
    if state.phase is Phase.IDLE:
        return Announce.UNAVAILABLE_NO_PROGRAM
    if state.phase is Phase.CHILD_ACTIVE:
        return Announce.SEND_REFUSED_CHILD_ACTIVE
    return Announce.UNAVAILABLE_NOT_TERMINAL


def _interpreter_can_change(state: SessionState) -> bool:
    return state.phase is Phase.IDLE and state.profile is None


def _why_interpreter_is_fixed(state: SessionState) -> Announce:
    if state.phase is not Phase.IDLE:
        return Announce.UNAVAILABLE_PROGRAM_RUNNING
    return Announce.UNAVAILABLE_PROFILE_CHOSEN


def _mode_can_change(state: SessionState) -> bool:
    return _interpreter_can_change(state) and state.interpreter is Interpreter.NONE


def _why_mode_is_fixed(state: SessionState) -> Announce:
    if not _interpreter_can_change(state):
        return _why_interpreter_is_fixed(state)
    return Announce.UNAVAILABLE_SHELL_USES_TUI


def _profile_can_be_changed(state: SessionState) -> bool:
    return state.phase is Phase.IDLE and state.profile is not None


def _why_profile_cannot_be_changed(state: SessionState) -> Announce:
    if state.phase is not Phase.IDLE:
        return Announce.UNAVAILABLE_PROGRAM_RUNNING
    return Announce.UNAVAILABLE_NO_PROFILE


def _program_can_be_launched(state: SessionState) -> bool:
    return (state.phase is Phase.IDLE or state.shell_ready) and state.has_program


def _why_program_cannot_be_launched(state: SessionState) -> Announce:
    if state.phase is not Phase.IDLE and not state.shell_ready:
        return Announce.UNAVAILABLE_PROGRAM_RUNNING
    if state.profile is None:
        return Announce.UNAVAILABLE_NO_PROFILE
    return Announce.UNAVAILABLE_NO_PROFILE_PROGRAM


def _can_send(state: SessionState) -> bool:
    return state.phase is not Phase.CHILD_ACTIVE


def _can_resend(state: SessionState) -> bool:
    return _can_send(state) and state.has_history


def _why_cannot_resend(state: SessionState) -> Announce:
    if state.phase is Phase.CHILD_ACTIVE:
        return Announce.SEND_REFUSED_CHILD_ACTIVE
    return Announce.UNAVAILABLE_NO_LAST_COMMAND


def _unless_on_server(rule: Rule) -> Rule:
    """``rule`` for this computer: with a connection chosen it is refused, whatever else.

    The commands that speak of this computer (a folder, a shell, a program of the profile) have no
    meaning on a server; the single fact "a connection is chosen" greys them all.
    """
    inner = rule.refusal
    assert inner is not None, "a command that can be refused says why"

    def available(state: SessionState) -> bool:
        return not state.on_server and rule.available(state)

    def reason(state: SessionState) -> Announce:
        if state.on_server:
            return Announce.UNAVAILABLE_ON_CONNECTION
        return inner if isinstance(inner, Announce) else inner(state)

    return Rule(available, reason)


def _why_connection_is_fixed(state: SessionState) -> Announce:
    if state.on_server:
        return Announce.UNAVAILABLE_CONNECTION_OPEN
    return Announce.UNAVAILABLE_PROGRAM_RUNNING


def _connection_can_be_changed(state: SessionState) -> bool:
    return state.phase is Phase.IDLE and state.on_server


def _why_connection_cannot_be_changed(state: SessionState) -> Announce:
    if state.phase is not Phase.IDLE:
        return _why_connection_is_fixed(state)
    return Announce.UNAVAILABLE_NO_CONNECTION


def _why_cannot_connect(state: SessionState) -> Announce:
    if not state.on_server:
        return Announce.UNAVAILABLE_NO_CONNECTION
    return Announce.UNAVAILABLE_CONNECTION_OPEN


RULES: dict[CommandId, Rule] = {
    CommandId.NEW_SESSION: Rule(_always),
    CommandId.CHOOSE_FOLDER: _unless_on_server(
        Rule(_folder_can_change, Announce.UNAVAILABLE_PROGRAM_RUNNING)
    ),
    CommandId.RECENT_FOLDERS: _unless_on_server(
        Rule(_folder_can_change, Announce.UNAVAILABLE_PROGRAM_RUNNING)
    ),
    CommandId.EXPORT: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.PREFERENCES: Rule(_always),
    CommandId.QUIT: Rule(_always),
    CommandId.STOP: Rule(lambda s: s.program_active, Announce.UNAVAILABLE_NO_PROGRAM),
    # As Enter in the command field: the same moments, on this computer or on a server.
    CommandId.RESEND: Rule(_can_resend, _why_cannot_resend),
    CommandId.MULTILINE: Rule(_can_send, Announce.SEND_REFUSED_CHILD_ACTIVE),
    CommandId.CLEAR: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.SET_INTERPRETER: _unless_on_server(
        Rule(_interpreter_can_change, _why_interpreter_is_fixed)
    ),
    CommandId.SELECT_POWERSHELL: _unless_on_server(
        Rule(lambda s: s.phase is Phase.IDLE, Announce.UNAVAILABLE_PROGRAM_RUNNING)
    ),
    CommandId.SET_MODE: _unless_on_server(Rule(_mode_can_change, _why_mode_is_fixed)),
    CommandId.SET_CONNECTION: Rule(lambda s: s.phase is Phase.IDLE, _why_connection_is_fixed),
    CommandId.CHOOSE_LOCAL: Rule(lambda s: s.phase is Phase.IDLE, _why_connection_is_fixed),
    CommandId.CONNECT: Rule(lambda s: s.phase is Phase.IDLE and s.on_server, _why_cannot_connect),
    CommandId.DISCONNECT: Rule(
        lambda s: s.on_server and s.program_active, Announce.UNAVAILABLE_NO_CONNECTION_OPEN
    ),
    CommandId.ADD_CONNECTION: Rule(lambda s: s.phase is Phase.IDLE, _why_connection_is_fixed),
    CommandId.EDIT_CONNECTION: Rule(_connection_can_be_changed, _why_connection_cannot_be_changed),
    CommandId.DELETE_CONNECTION: Rule(
        _connection_can_be_changed, _why_connection_cannot_be_changed
    ),
    CommandId.SELECT_SSH: Rule(lambda s: s.phase is Phase.IDLE, _why_connection_is_fixed),
    CommandId.SET_PROFILE: Rule(
        lambda s: s.phase is Phase.IDLE, Announce.UNAVAILABLE_PROGRAM_RUNNING
    ),
    CommandId.CHOOSE_FREE_PROFILE: Rule(
        lambda s: s.phase is Phase.IDLE, Announce.UNAVAILABLE_PROGRAM_RUNNING
    ),
    CommandId.ADD_PROFILE: Rule(_always),
    CommandId.EDIT_PROFILE: Rule(_profile_can_be_changed, _why_profile_cannot_be_changed),
    CommandId.DELETE_PROFILE: Rule(_profile_can_be_changed, _why_profile_cannot_be_changed),
    CommandId.DEFINE_VARIABLES: Rule(lambda s: s.has_variables, Announce.UNAVAILABLE_NO_VARIABLES),
    # On a server too: the program is typed by its file name, once the connection is open.
    CommandId.LAUNCH_PROGRAM: Rule(_program_can_be_launched, _why_program_cannot_be_launched),
    CommandId.COPY: Rule(_always),
    CommandId.SELECT_ALL: Rule(_always),
    CommandId.FIND: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.FIND_NEXT: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.FIND_PREVIOUS: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.COMFORT_PREVIOUS: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.COMFORT_NEXT: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.PROMPT_PATTERNS: Rule(_always),
    CommandId.NEXT_TITLE: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.PREVIOUS_TITLE: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.SET_SIZE: Rule(_always),
    CommandId.SET_TERMINAL_VIEW: Rule(_display_applies, Announce.UNAVAILABLE_NOT_TERMINAL),
    CommandId.MOVE: Rule(_always),
    CommandId.ACTIVITIES: Rule(_always),
    CommandId.READ_LINE: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.IDENTIFY_ACTIVITIES: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.SIGNAL_ACTIVITIES: Rule(_always),
    CommandId.GO_TO_CURSOR: Rule(lambda s: s.has_output, Announce.UNAVAILABLE_NO_OUTPUT),
    CommandId.GO_TO_EMULATOR_START: Rule(
        _live_part_can_be_reached, _why_live_part_cannot_be_reached
    ),
    CommandId.GO_TO_EMULATOR_END: Rule(_live_part_can_be_reached, _why_live_part_cannot_be_reached),
    CommandId.HISTORY: Rule(_always),
    CommandId.OPEN_LOGS: Rule(_always),
    CommandId.ABOUT: Rule(_always),
    CommandId.OPEN_HELP: Rule(_always),
    CommandId.CONVERT_HELP: Rule(_always),
    CommandId.SEND_KEY: Rule(_key_can_be_sent, _why_key_cannot_be_sent),
    CommandId.SESSION_INFO: Rule(_always),
    CommandId.CATALOGS: Rule(_always),
    CommandId.TEST_PROGRAMS: _unless_on_server(
        Rule(lambda s: s.phase is Phase.IDLE, Announce.UNAVAILABLE_PROGRAM_RUNNING)
    ),
}


def command_states(state: SessionState) -> frozenset[CommandId]:
    """The commands that are enabled in ``state``."""
    return frozenset(command for command, rule in RULES.items() if rule.available(state))


def refusal(command: CommandId, state: SessionState) -> Announce | None:
    """What to announce when ``command`` is asked in ``state`` and is not available.

    None when the command is available.
    """
    rule = RULES[command]
    if rule.available(state):
        return None
    return rule.refusal(state) if callable(rule.refusal) else rule.refusal
