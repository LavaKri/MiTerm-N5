"""A connection in the session presenter: chosen, opened, said, written, closed."""

import pytest

from fakes.session_support import Session
from n5terminal.core.config.connections import Connection
from n5terminal.core.config.profiles import Profile
from n5terminal.core.errors import (
    AskpassNotFoundError,
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    InvalidConnectionError,
    ProgramNotFoundError,
)
from n5terminal.core.session.session_state import CommandId, Phase
from n5terminal.core.transport.transport import TransportState

pytestmark = pytest.mark.unit

PROD = Connection("prod", target="admin@example.org", port=2222)


def choose(session: Session, connection: Connection | None = PROD) -> None:
    assert session.presenter.select_connection(connection)


def connect(session: Session, text: str = "") -> None:
    session.presenter.submit(text)
    session.presenter.tick()


def make_connected(session: Session, text: str = "") -> None:
    choose(session)
    connect(session, text)


def close(session: Session, code: int | None = 0) -> None:
    session.transport.exit(code)
    session.presenter.tick()


# The choice -----------------------------------------------------------------------------------


def test_a_connection_is_chosen_and_the_title_of_the_window_names_it(terminal: Session) -> None:
    choose(terminal)
    assert terminal.presenter.chosen_connection == PROD
    assert terminal.presenter.state.connection == "prod"
    assert terminal.view.titles[-1] == "MiTerm-N5: free profile on SSH prod (not connected)"
    assert terminal.sink.messages == []  # the title says it, nothing is announced


def test_locale_is_chosen_again_with_none(terminal: Session) -> None:
    choose(terminal)
    choose(terminal, None)
    assert terminal.presenter.chosen_connection is None
    assert terminal.presenter.state.connection is None
    assert terminal.view.titles[-1].startswith("MiTerm-N5: free profile in ")


def test_a_connection_chosen_greys_what_speaks_of_this_computer(terminal: Session) -> None:
    choose(terminal)
    enabled = terminal.view.last_enabled
    assert CommandId.CHOOSE_FOLDER not in enabled
    assert {CommandId.CONNECT, CommandId.SET_CONNECTION} <= enabled


def test_the_connection_cannot_be_chosen_while_a_program_runs(terminal: Session) -> None:
    terminal.presenter.submit("ping host")
    assert not terminal.presenter.select_connection(PROD)
    assert terminal.sink.messages[-1] == "Not available while a program is running."


def test_the_connection_cannot_be_changed_while_it_is_open(terminal: Session) -> None:
    make_connected(terminal)
    assert not terminal.presenter.select_connection(None)
    assert terminal.sink.messages[-1] == "Not available while a connection is open."
    assert terminal.presenter.chosen_connection == PROD


def test_the_profile_program_is_written_by_its_file_name_on_a_server(terminal: Session) -> None:
    terminal.presenter.profile_values.choose(
        Profile("git", program=r"C:\Program Files\Git\bin\git.exe", commands=["status"])
    )
    assert terminal.presenter.command_list()[0][0].text == "status"  # the field takes arguments
    choose(terminal)
    entries, _selected = terminal.presenter.command_list()
    assert [(e.label, e.text) for e in entries] == [("git status", "git status")]
    choose(terminal, None)
    assert terminal.presenter.command_list()[0][0].text == "status"


def test_launching_the_program_of_the_profile_opens_the_connection_and_types_its_name(
    terminal: Session,
) -> None:
    git = Profile("git", program=r"C:\Program Files\Git\bin\git.exe", commands=["status"])
    terminal.presenter.select_profile(git)
    choose(terminal)
    assert terminal.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    terminal.presenter.tick()
    assert len(terminal.launcher.connections) == 1
    assert terminal.launcher.calls == []  # nothing local
    assert terminal.transport.written == [b"git\r"]


# Opening --------------------------------------------------------------------------------------


def test_entering_with_a_connection_chosen_opens_it(terminal: Session) -> None:
    choose(terminal)
    connect(terminal)
    [call] = terminal.launcher.connections
    assert (call.connection, call.folder, call.ssh_path) == (PROD, terminal.folder, "")
    assert terminal.presenter.state.phase is Phase.RUNNING
    assert terminal.launcher.calls == []  # no local program


def test_the_ssh_chosen_in_the_settings_is_the_one_given_to_the_launcher(terminal: Session) -> None:
    terminal.settings.ssh_path = r"C:\Git\usr\bin\ssh.exe"
    choose(terminal)
    connect(terminal)
    assert terminal.launcher.connections[0].ssh_path == r"C:\Git\usr\bin\ssh.exe"


def test_the_title_and_the_target_are_written_first_and_the_focus_goes_to_the_title(
    terminal: Session,
) -> None:
    choose(terminal)
    connect(terminal)
    assert terminal.view.fixed_lines() == ["# SSH prod", "To admin@example.org:2222"]
    assert terminal.view.focus_calls[-1] == "command:2"  # the caret is put on the title


def test_a_target_without_a_port_is_written_as_it_is(terminal: Session) -> None:
    choose(terminal, Connection("box", target="box"))
    connect(terminal)
    assert terminal.view.fixed_lines()[1] == "To box"


def test_the_steps_are_said_once_and_shown_in_the_status_bar(terminal: Session) -> None:
    choose(terminal)
    connect(terminal)
    assert terminal.sink.messages == ["Connecting…", "Connected to prod."]
    assert terminal.view.states[-1] == "Connected to prod"
    assert terminal.view.titles[-1] == "MiTerm-N5: free profile on SSH prod"


def test_authenticating_is_a_step_of_its_own(terminal: Session) -> None:
    terminal.launcher.start_states = (TransportState.CONNECTING, TransportState.AUTHENTICATING)
    choose(terminal)
    connect(terminal)
    assert terminal.sink.messages == ["Connecting…", "Authenticating…"]
    assert terminal.view.states[-1] == "Authenticating…"
    terminal.transport.set_state(TransportState.CONNECTED)
    assert terminal.sink.messages[-1] == "Connected to prod."


def test_the_text_typed_is_sent_to_the_server_once_connected(terminal: Session) -> None:
    choose(terminal)
    connect(terminal, "ls -l")
    assert terminal.transport.written == [b"ls -l\r"]
    assert terminal.presenter.history_items() == ("ls -l",)


def test_an_empty_line_only_opens_the_connection(terminal: Session) -> None:
    make_connected(terminal)
    assert terminal.transport.written == []
    assert terminal.presenter.history_items() == ()


def test_what_is_typed_in_the_session_is_kept_as_a_command_of_the_server(terminal: Session) -> None:
    make_connected(terminal)
    terminal.presenter.submit("uptime")
    assert terminal.transport.written == [b"uptime\r"]
    assert terminal.presenter.history_items() == ("uptime",)


def test_a_hidden_message_is_not_kept_on_a_server_either(terminal: Session) -> None:
    make_connected(terminal)
    terminal.presenter.submit("s3cr3t", hidden=True)
    assert terminal.transport.written == [b"s3cr3t\r"]
    assert terminal.presenter.history_items() == ()


# Starting that fails --------------------------------------------------------------------------


def test_a_target_ssh_would_take_for_an_option_is_refused_before_anything_starts(
    terminal: Session,
) -> None:
    terminal.launcher.connect_error = InvalidConnectionError("target", "option_like")
    choose(terminal)
    connect(terminal)
    assert terminal.sink.messages[-1] == "SSH could not be started."
    assert terminal.presenter.state.phase is Phase.IDLE
    assert terminal.view.fixed_lines() == []


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (ProgramNotFoundError(r"C:\ssh.exe"), r"OpenSSH client not found: C:\ssh.exe."),
        (
            AskpassNotFoundError(r"C:\n5terminal-askpass.exe"),
            r"The program that asks for passwords was not found: C:\n5terminal-askpass.exe.",
        ),
    ],
)
def test_a_missing_program_is_told_by_its_path_and_leaves_the_session_ready(
    terminal: Session, error: Exception, message: str
) -> None:
    terminal.launcher.start_error = error
    choose(terminal)
    connect(terminal)
    assert terminal.sink.messages[-1] == message
    assert terminal.presenter.state.phase is Phase.IDLE
    assert terminal.presenter.state.connection == "prod"  # still chosen: the user may try again


# The end --------------------------------------------------------------------------------------


def test_the_end_is_announced_with_the_code_and_written_in_the_closing_part(
    terminal: Session,
) -> None:
    make_connected(terminal)
    close(terminal, 255)
    assert terminal.sink.messages[-1] == "Disconnected (code 255)."
    [update] = [u for u, _ in terminal.view.outputs if u.closing]
    assert [line.text for line in update.closing or ()] == ["Disconnected (code 255)."]
    assert terminal.view.states[-1] == "Disconnected (code 255)"
    assert terminal.presenter.state.phase is Phase.IDLE
    assert terminal.view.titles[-1] == "MiTerm-N5: free profile on SSH prod (not connected)"


def test_the_exit_of_the_connection_does_not_say_a_program_ended(terminal: Session) -> None:
    make_connected(terminal)
    close(terminal, 0)
    assert not any("ended" in message for message in terminal.sink.messages)


def test_a_cancelled_connection_is_not_an_error(terminal: Session) -> None:
    make_connected(terminal)
    terminal.transport.cancelled = True
    close(terminal, 255)
    assert terminal.sink.messages[-1] == "Connection cancelled."
    assert terminal.view.states[-1] == "Connection cancelled"


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (
            AuthenticationError("Permission denied (publickey)."),
            "Authentication refused: Permission denied (publickey).",
        ),
        (
            HostKeyError("Host key verification failed."),
            "Host key refused: Host key verification failed.",
        ),
        (
            ConnectionFailedError("Connection refused"),
            "Connection failed: Connection refused",
        ),
    ],
)
def test_an_error_is_announced_with_its_cause_and_written_too(
    terminal: Session, failure: Exception, message: str
) -> None:
    choose(terminal)
    connect(terminal)
    terminal.transport.failure = failure  # type: ignore[assignment]
    terminal.transport.exit(255)
    terminal.transport.set_state(TransportState.FAILED)
    terminal.presenter.tick()
    assert terminal.sink.messages[-1] == message
    assert terminal.view.states[-1] == "Connection failed"
    closing = [line.text for u, _ in terminal.view.outputs for line in u.closing or ()]
    assert closing == [message]


def test_the_connection_can_be_opened_again_after_it_closed(terminal: Session) -> None:
    make_connected(terminal)
    close(terminal)
    connect(terminal)
    assert len(terminal.launcher.connections) == 2
    assert terminal.view.fixed_lines().count("# SSH prod") == 2


# The commands ---------------------------------------------------------------------------------


def test_connect_and_disconnect_are_commands_of_the_session(terminal: Session) -> None:
    choose(terminal)
    assert terminal.presenter.run_command(CommandId.CONNECT)
    assert terminal.presenter.state.phase is Phase.RUNNING
    assert not terminal.presenter.run_command(CommandId.CONNECT)  # already open
    assert terminal.sink.messages[-1] == "Not available while a connection is open."
    assert terminal.presenter.run_command(CommandId.DISCONNECT)
    assert terminal.transport.closed


def test_disconnecting_does_not_say_the_program_stopped(terminal: Session) -> None:
    make_connected(terminal)
    terminal.presenter.run_command(CommandId.DISCONNECT)
    assert "Program stopped." not in terminal.sink.messages


def test_disconnect_needs_an_open_connection(terminal: Session) -> None:
    choose(terminal)
    assert not terminal.presenter.run_command(CommandId.DISCONNECT)
    assert terminal.sink.messages[-1] == "No connection is open."


def test_a_local_command_is_refused_with_a_connection_chosen(terminal: Session) -> None:
    choose(terminal)
    assert not terminal.presenter.run_command(CommandId.CHOOSE_FOLDER)
    assert terminal.sink.messages[-1] == "Not available with a connection."


def test_resend_is_available_with_a_connection_once_a_line_was_typed(terminal: Session) -> None:
    choose(terminal)
    assert not terminal.presenter.run_command(CommandId.RESEND)
    assert terminal.sink.messages[-1] == "There is no command to resend."
    make_connected(terminal)
    terminal.presenter.submit("ls")
    assert terminal.presenter.run_command(CommandId.RESEND)
    assert terminal.transport.written[-2:] == [b"ls\r", b"ls\r"]


# What the information of the session reads -----------------------------------------------------


def test_the_presenter_tells_the_target_the_state_and_how_long(terminal: Session) -> None:
    assert terminal.presenter.connection_target == ""
    assert terminal.presenter.connected_for is None
    choose(terminal)
    assert terminal.presenter.connection_target == "admin@example.org:2222"
    assert terminal.presenter.connection_state == "not connected"
    connect(terminal)
    assert terminal.presenter.connection_state == "Connected to prod"
    terminal.now[0] = 125.0
    assert terminal.presenter.connected_for == 125.0
    close(terminal)
    assert terminal.presenter.connected_for is None
    assert terminal.presenter.connection_state == "not connected"


def test_a_target_without_a_port_is_told_as_it_is(terminal: Session) -> None:
    choose(terminal, Connection("box", target="box"))
    assert terminal.presenter.connection_target == "box"
