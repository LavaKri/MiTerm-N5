import pytest

from n5terminal.core.config.announcements import REFUSED, Announce
from n5terminal.core.config.settings import INTERPRETERS, LAUNCH_MODES
from n5terminal.core.session.session_state import (
    RULES,
    CommandId,
    Interpreter,
    LaunchMode,
    Mode,
    Phase,
    SessionState,
    command_states,
    refusal,
)

pytestmark = pytest.mark.unit

IDLE = SessionState()
RUNNING_PIPES = SessionState(Phase.RUNNING, Mode.PIPES, has_output=True)
RUNNING_TERMINAL = SessionState(Phase.RUNNING, Mode.TERMINAL_LINE, has_output=True)
CHILD_ACTIVE = SessionState(Phase.CHILD_ACTIVE, Mode.PIPES, has_output=True)
SHELL_AT_PROMPT = SessionState(
    Phase.RUNNING,
    Mode.TERMINAL_LINE,
    Interpreter.CMD,
    shell_at_prompt=True,
    has_output=True,
)
SHELL_BUSY = SessionState(Phase.RUNNING, Mode.TERMINAL_LINE, Interpreter.CMD, has_output=True)

ALWAYS = {
    CommandId.NEW_SESSION,
    CommandId.PREFERENCES,
    CommandId.QUIT,
    CommandId.COPY,
    CommandId.SELECT_ALL,
    CommandId.SET_SIZE,
    CommandId.MOVE,
    CommandId.ACTIVITIES,
    CommandId.SIGNAL_ACTIVITIES,
    CommandId.OPEN_HELP,
    CommandId.CONVERT_HELP,
    CommandId.ADD_PROFILE,
    CommandId.PROMPT_PATTERNS,
    CommandId.HISTORY,
    CommandId.OPEN_LOGS,
    CommandId.ABOUT,
    CommandId.SESSION_INFO,
}


def test_every_command_has_a_rule() -> None:
    assert set(RULES) == set(CommandId)


def test_a_command_that_can_be_refused_has_a_reason() -> None:
    for command, rule in RULES.items():
        if rule.refusal is None:
            assert rule.available(SessionState()), command
            assert rule.available(RUNNING_PIPES), command
            assert rule.available(CHILD_ACTIVE), command


@pytest.mark.parametrize(
    "state",
    [IDLE, RUNNING_PIPES, RUNNING_TERMINAL, CHILD_ACTIVE, SHELL_AT_PROMPT, SHELL_BUSY],
)
def test_the_always_available_commands_are_in_every_state(state: SessionState) -> None:
    assert command_states(state) >= ALWAYS


def test_idle_session_with_nothing_yet() -> None:
    assert command_states(IDLE) == ALWAYS | {
        CommandId.CHOOSE_FOLDER,
        CommandId.RECENT_FOLDERS,
        CommandId.SET_INTERPRETER,
        CommandId.SELECT_POWERSHELL,
        CommandId.SET_MODE,
        CommandId.SET_PROFILE,
        CommandId.CHOOSE_FREE_PROFILE,
        CommandId.SET_TERMINAL_VIEW,
        CommandId.CATALOGS,
        CommandId.TEST_PROGRAMS,
        CommandId.SET_CONNECTION,
        CommandId.CHOOSE_LOCAL,
        CommandId.ADD_CONNECTION,
        CommandId.SELECT_SSH,
        CommandId.MULTILINE,
    }


# A connection ---------------------------------------------------------------------------------

LOCAL_ONLY = {
    CommandId.CHOOSE_FOLDER,
    CommandId.RECENT_FOLDERS,
    CommandId.SET_INTERPRETER,
    CommandId.SELECT_POWERSHELL,
    CommandId.SET_MODE,
    CommandId.TEST_PROGRAMS,
}
CONNECTION_COMMANDS = {
    CommandId.SET_CONNECTION,
    CommandId.ADD_CONNECTION,
    CommandId.EDIT_CONNECTION,
    CommandId.DELETE_CONNECTION,
    CommandId.SELECT_SSH,
}
CHOSEN = SessionState(connection="prod", has_output=True, has_history=True, has_program=True)
OPENING = SessionState(Phase.RUNNING, Mode.TERMINAL_LINE, connection="prod", has_output=True)
CLOSING = SessionState(Phase.CHILD_ACTIVE, Mode.TERMINAL_LINE, connection="prod")


def test_a_connection_chosen_greys_everything_that_speaks_of_this_computer() -> None:
    enabled = command_states(CHOSEN)
    assert LOCAL_ONLY.isdisjoint(enabled)
    for command in LOCAL_ONLY:
        assert refusal(command, CHOSEN) is Announce.UNAVAILABLE_ON_CONNECTION, command


def test_the_program_of_the_profile_can_be_launched_on_a_server_until_it_is_open() -> None:
    assert CommandId.LAUNCH_PROGRAM in command_states(CHOSEN)
    assert refusal(CommandId.LAUNCH_PROGRAM, OPENING) is Announce.UNAVAILABLE_PROGRAM_RUNNING
    no_program = SessionState(connection="prod")
    assert CommandId.LAUNCH_PROGRAM not in command_states(no_program)


def test_a_connection_chosen_leaves_the_rest_alone() -> None:
    enabled = command_states(CHOSEN)
    assert {CommandId.SET_PROFILE, CommandId.SET_SIZE, CommandId.CLEAR, CommandId.EXPORT} <= enabled
    assert enabled >= ALWAYS


def test_a_chosen_connection_can_be_opened_but_not_closed() -> None:
    enabled = command_states(CHOSEN)
    assert CommandId.CONNECT in enabled
    assert CommandId.DISCONNECT not in enabled
    assert refusal(CommandId.DISCONNECT, CHOSEN) is Announce.UNAVAILABLE_NO_CONNECTION_OPEN


def test_the_connections_can_be_managed_when_none_is_open() -> None:
    assert command_states(CHOSEN) >= CONNECTION_COMMANDS


def test_locale_cannot_be_connected_edited_or_deleted_but_a_connection_can_be_added() -> None:
    enabled = command_states(IDLE)
    assert {CommandId.SET_CONNECTION, CommandId.ADD_CONNECTION, CommandId.SELECT_SSH} <= enabled
    for command in (CommandId.CONNECT, CommandId.EDIT_CONNECTION, CommandId.DELETE_CONNECTION):
        assert command not in enabled
        assert refusal(command, IDLE) is Announce.UNAVAILABLE_NO_CONNECTION
    assert refusal(CommandId.DISCONNECT, IDLE) is Announce.UNAVAILABLE_NO_CONNECTION_OPEN


@pytest.mark.parametrize("state", [OPENING, CLOSING])
def test_an_open_connection_cannot_be_changed_added_edited_deleted_or_opened_again(
    state: SessionState,
) -> None:
    enabled = command_states(state)
    assert (CONNECTION_COMMANDS | {CommandId.CONNECT}).isdisjoint(enabled)
    for command in CONNECTION_COMMANDS | {CommandId.CONNECT}:
        assert refusal(command, state) is Announce.UNAVAILABLE_CONNECTION_OPEN, command


def test_an_open_connection_can_be_closed() -> None:
    assert CommandId.DISCONNECT in command_states(OPENING)
    assert CommandId.STOP in command_states(OPENING)  # Ctrl+Pause does the same
    assert CommandId.DISCONNECT in command_states(CLOSING)


def test_a_local_program_locks_the_connections_with_the_reason_of_a_program() -> None:
    for command in CONNECTION_COMMANDS - {CommandId.EDIT_CONNECTION, CommandId.DELETE_CONNECTION}:
        assert command not in command_states(RUNNING_PIPES)
        assert refusal(command, RUNNING_PIPES) is Announce.UNAVAILABLE_PROGRAM_RUNNING
    assert refusal(CommandId.CONNECT, RUNNING_PIPES) is Announce.UNAVAILABLE_NO_CONNECTION


def test_a_connection_open_still_sends_keys_once_it_runs() -> None:
    assert CommandId.SEND_KEY in command_states(OPENING)


def test_a_chosen_profile_greys_the_mode_and_the_interpreter() -> None:
    state = SessionState(profile="git")
    enabled = command_states(state)
    assert {CommandId.SET_MODE, CommandId.SET_INTERPRETER}.isdisjoint(enabled)
    assert {CommandId.SET_PROFILE, CommandId.DELETE_PROFILE, CommandId.SET_SIZE} <= enabled
    assert refusal(CommandId.SET_MODE, state) is Announce.UNAVAILABLE_PROFILE_CHOSEN
    assert refusal(CommandId.SET_INTERPRETER, state) is Announce.UNAVAILABLE_PROFILE_CHOSEN


def test_the_powershell_can_be_selected_with_a_profile_but_not_under_a_program() -> None:
    assert CommandId.SELECT_POWERSHELL in command_states(SessionState(profile="git"))
    assert CommandId.SELECT_POWERSHELL not in command_states(RUNNING_PIPES)
    assert CommandId.SELECT_POWERSHELL not in command_states(SHELL_AT_PROMPT)
    assert (
        refusal(CommandId.SELECT_POWERSHELL, RUNNING_PIPES) is Announce.UNAVAILABLE_PROGRAM_RUNNING
    )


def test_variables_can_be_defined_only_for_a_profile_that_uses_some() -> None:
    assert CommandId.DEFINE_VARIABLES not in command_states(SessionState(profile="git"))
    assert refusal(CommandId.DEFINE_VARIABLES, IDLE) is Announce.UNAVAILABLE_NO_VARIABLES
    with_variables = SessionState(profile="git", has_variables=True)
    assert CommandId.DEFINE_VARIABLES in command_states(with_variables)
    running = SessionState(Phase.RUNNING, Mode.PIPES, profile="git", has_variables=True)
    assert CommandId.DEFINE_VARIABLES in command_states(running)  # it only changes the commands


def test_the_free_profile_cannot_be_edited_or_deleted_but_a_profile_can_be_added() -> None:
    enabled = command_states(IDLE)
    assert CommandId.ADD_PROFILE in enabled
    for command in (CommandId.EDIT_PROFILE, CommandId.DELETE_PROFILE):
        assert command not in enabled
        assert refusal(command, IDLE) is Announce.UNAVAILABLE_NO_PROFILE


def test_a_running_program_locks_the_choice_of_a_profile() -> None:
    state = SessionState(Phase.RUNNING, Mode.PIPES, profile="git")
    locked = {CommandId.SET_PROFILE, CommandId.EDIT_PROFILE, CommandId.DELETE_PROFILE}
    assert locked.isdisjoint(command_states(state))
    assert refusal(CommandId.SET_PROFILE, state) is Announce.UNAVAILABLE_PROGRAM_RUNNING


def test_idle_session_after_a_run() -> None:
    state = SessionState(has_output=True, has_history=True)
    enabled = command_states(state)
    assert {
        CommandId.RESEND,
        CommandId.EXPORT,
        CommandId.CLEAR,
        CommandId.FIND,
        CommandId.FIND_NEXT,
        CommandId.FIND_PREVIOUS,
    } <= enabled
    assert CommandId.STOP not in enabled


def test_resend_needs_a_line_in_the_history() -> None:
    assert CommandId.RESEND not in command_states(SessionState(has_output=True))
    assert refusal(CommandId.RESEND, IDLE) is Announce.UNAVAILABLE_NO_LAST_COMMAND


def test_resend_is_available_when_a_line_can_be_sent_with_the_field() -> None:
    """The moments of Enter in the command field: at rest, with a program running, on a server."""
    for state in (
        SessionState(has_history=True),
        SessionState(Phase.RUNNING, Mode.PIPES, has_history=True),
        SessionState(connection="prod", has_history=True),
        SessionState(Phase.RUNNING, Mode.TERMINAL_LINE, connection="prod", has_history=True),
    ):
        assert CommandId.RESEND in command_states(state)
    ended = SessionState(Phase.CHILD_ACTIVE, Mode.PIPES, has_history=True)
    assert CommandId.RESEND not in command_states(ended)
    assert refusal(CommandId.RESEND, ended) is Announce.SEND_REFUSED_CHILD_ACTIVE


@pytest.mark.parametrize("state", [RUNNING_PIPES, RUNNING_TERMINAL, CHILD_ACTIVE])
def test_a_running_program_locks_the_folder_and_the_interpreter(
    state: SessionState,
) -> None:
    enabled = command_states(state)
    assert CommandId.STOP in enabled
    for command in (
        CommandId.CHOOSE_FOLDER,
        CommandId.RECENT_FOLDERS,
        CommandId.SET_INTERPRETER,
    ):
        assert command not in enabled
    assert refusal(CommandId.CHOOSE_FOLDER, state) is Announce.UNAVAILABLE_PROGRAM_RUNNING


def test_a_shell_waiting_at_its_prompt_accepts_a_folder_change() -> None:
    enabled = command_states(SHELL_AT_PROMPT)
    assert {CommandId.CHOOSE_FOLDER, CommandId.RECENT_FOLDERS} <= enabled
    assert CommandId.SET_INTERPRETER not in enabled


def test_a_busy_shell_refuses_a_folder_change() -> None:
    assert CommandId.CHOOSE_FOLDER not in command_states(SHELL_BUSY)
    assert refusal(CommandId.CHOOSE_FOLDER, SHELL_BUSY) is Announce.UNAVAILABLE_PROGRAM_RUNNING


def test_prompt_flag_means_nothing_without_a_shell() -> None:
    state = SessionState(Phase.RUNNING, Mode.PIPES, Interpreter.NONE, shell_at_prompt=True)
    assert not state.shell_ready
    assert CommandId.CHOOSE_FOLDER not in command_states(state)


def test_a_shell_whose_program_ended_is_not_ready() -> None:
    state = SessionState(
        Phase.CHILD_ACTIVE, Mode.TERMINAL_LINE, Interpreter.CMD, shell_at_prompt=True
    )
    assert not state.shell_ready


def test_stop_needs_a_program() -> None:
    assert CommandId.STOP not in command_states(IDLE)
    assert refusal(CommandId.STOP, IDLE) is Announce.UNAVAILABLE_NO_PROGRAM


def test_the_terminal_view_only_applies_to_terminal_programs() -> None:
    assert CommandId.SET_TERMINAL_VIEW in command_states(IDLE)
    assert CommandId.SET_TERMINAL_VIEW in command_states(RUNNING_TERMINAL)
    assert CommandId.SET_TERMINAL_VIEW not in command_states(RUNNING_PIPES)
    assert refusal(CommandId.SET_TERMINAL_VIEW, RUNNING_PIPES) is Announce.UNAVAILABLE_NOT_TERMINAL


def test_commands_on_the_output_need_some_output() -> None:
    enabled = command_states(SessionState(Phase.RUNNING))
    for command in (CommandId.EXPORT, CommandId.CLEAR, CommandId.FIND):
        assert command not in enabled
        assert refusal(command, SessionState(Phase.RUNNING)) is Announce.UNAVAILABLE_NO_OUTPUT


def test_the_ends_of_the_emulator_part_need_output_from_a_terminal_program() -> None:
    both = (CommandId.GO_TO_EMULATOR_START, CommandId.GO_TO_EMULATOR_END)
    for command in both:
        assert command in command_states(RUNNING_TERMINAL)
        assert command not in command_states(RUNNING_PIPES)
        assert refusal(command, RUNNING_PIPES) is Announce.UNAVAILABLE_NOT_TERMINAL
        assert refusal(command, SessionState(Phase.RUNNING)) is Announce.UNAVAILABLE_NO_OUTPUT
        assert command in command_states(
            SessionState(has_output=True)
        )  # no program: the last output


def test_no_refusal_for_an_available_command() -> None:
    for command in command_states(RUNNING_TERMINAL):
        assert refusal(command, RUNNING_TERMINAL) is None


def test_every_refusal_belongs_to_the_category_of_the_refusals() -> None:
    for command, rule in RULES.items():
        if rule.refusal is None:
            continue
        refusals = (
            [rule.refusal]
            if isinstance(rule.refusal, Announce)
            else [
                refusal(command, state)
                for state in (RUNNING_PIPES, CHILD_ACTIVE, SHELL_BUSY, SHELL_AT_PROMPT)
            ]
        )
        for announce in refusals:
            assert announce is None or announce.category is REFUSED


def test_the_mode_is_chosen_with_no_program_and_no_shell() -> None:
    assert CommandId.SET_MODE in command_states(IDLE)
    assert CommandId.SET_MODE not in command_states(RUNNING_PIPES)
    assert refusal(CommandId.SET_MODE, RUNNING_PIPES) is Announce.UNAVAILABLE_PROGRAM_RUNNING


def test_a_shell_fixes_the_mode_as_tui_and_says_so() -> None:
    state = SessionState(interpreter=Interpreter.CMD, launch_mode=LaunchMode.CLI)
    assert state.effective_launch_mode is LaunchMode.TUI
    assert CommandId.SET_MODE not in command_states(state)
    assert refusal(CommandId.SET_MODE, state) is Announce.UNAVAILABLE_SHELL_USES_TUI


def test_the_mode_chosen_is_the_one_used_without_a_shell() -> None:
    assert SessionState().effective_launch_mode is LaunchMode.CLI
    assert SessionState(launch_mode=LaunchMode.TUI).effective_launch_mode is LaunchMode.TUI


def test_a_refusal_needs_no_value_to_be_said() -> None:
    """The presenter says a refusal with no values: its text has no field, in any state."""
    states = (
        SessionState(phase, mode, interpreter, has_output=has_output, profile=profile)
        for phase in Phase
        for mode in Mode
        for interpreter in Interpreter
        for has_output in (False, True)
        for profile in (None, "git")
    )
    for state in states:
        for command in CommandId:
            reason = refusal(command, state)
            assert reason is None or not reason.fields, (command, state, reason)


def test_the_values_the_settings_accept_are_those_of_the_enums() -> None:
    """``settings.py`` comes before this package, so it lists the values instead of the enums."""
    assert tuple(mode.value for mode in LaunchMode) == LAUNCH_MODES
    assert tuple(interpreter.value for interpreter in Interpreter) == INTERPRETERS


def test_multi_line_input_is_available_when_enter_in_the_field_would_send() -> None:
    for state in (IDLE, SessionState(Phase.RUNNING, Mode.PIPES), SessionState(connection="prod")):
        assert CommandId.MULTILINE in command_states(state)
    ended = SessionState(Phase.CHILD_ACTIVE, Mode.PIPES)
    assert CommandId.MULTILINE not in command_states(ended)
    assert refusal(CommandId.MULTILINE, ended) is Announce.SEND_REFUSED_CHILD_ACTIVE
