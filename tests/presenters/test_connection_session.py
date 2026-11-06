"""What is said of the start and the end of a connection, and the texts that name it."""

from dataclasses import replace

import pytest

from fakes.fake_transport import FakeTransport
from n5terminal.core.config.announcements import Announce
from n5terminal.core.errors import (
    AskpassNotFoundError,
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    InvalidConnectionError,
    NamedPipeError,
    ProgramNotFoundError,
)
from n5terminal.core.session.session_state import Interpreter, Phase, SessionState
from n5terminal.presenters.connection_session import (
    connected_status,
    connection_end,
    start_failure,
)
from n5terminal.presenters.session_info import (
    connection_dialog_title,
    connection_heading,
    connection_secret_title,
    connection_target_line,
    connection_title,
    connection_where,
    input_label,
)

pytestmark = pytest.mark.unit


def same(text: str) -> str:
    return text


# The end ---------------------------------------------------------------------------------------


def test_a_connection_that_closed_says_the_code_of_ssh() -> None:
    end = connection_end(FakeTransport(), 255, same)
    assert end.announce is Announce.DISCONNECTED
    assert end.values == {"code": 255}
    assert end.status == "Disconnected (code 255)"
    assert end.closing_line(same) == "Disconnected (code 255)."


def test_a_connection_that_closed_with_no_code_says_it_closed() -> None:
    end = connection_end(FakeTransport(), None, same)
    assert end.announce is Announce.CONNECTION_CLOSED
    assert (end.status, end.closing_line(same)) == ("Disconnected", "Disconnected.")


def test_a_dialog_cancelled_is_not_an_error() -> None:
    transport = FakeTransport()
    transport.cancelled = True
    end = connection_end(transport, 255, same)
    assert end.announce is Announce.CONNECTION_CANCELLED
    assert (end.status, end.closing_line(same)) == ("Connection cancelled", "Connection cancelled.")


@pytest.mark.parametrize(
    ("failure", "announce", "line"),
    [
        (
            AuthenticationError("Permission denied."),
            Announce.AUTHENTICATION_FAILED,
            "Authentication refused: Permission denied.",
        ),
        (
            HostKeyError("Host key verification failed."),
            Announce.HOST_KEY_FAILED,
            "Host key refused: Host key verification failed.",
        ),
        (
            ConnectionFailedError("Connection refused"),
            Announce.CONNECTION_FAILED,
            "Connection failed: Connection refused",
        ),
    ],
)
def test_an_error_is_said_with_its_cause(failure: Exception, announce: Announce, line: str) -> None:
    transport = FakeTransport()
    transport.failure = failure  # type: ignore[assignment]
    end = connection_end(transport, 255, same)
    assert end.announce is announce
    assert (end.status, end.closing_line(same)) == ("Connection failed", line)


def test_an_error_wins_over_a_cancel() -> None:
    transport = FakeTransport()
    transport.failure = ConnectionFailedError("x")
    transport.cancelled = True
    assert connection_end(transport, 255, same).announce is Announce.CONNECTION_FAILED


def test_a_transport_that_reports_nothing_just_closed() -> None:
    assert connection_end(object(), 0, same).announce is Announce.DISCONNECTED


# The start -------------------------------------------------------------------------------------


def test_a_missing_ssh_is_told_by_its_path() -> None:
    assert start_failure(ProgramNotFoundError(r"C:\ssh.exe")) == (
        Announce.SSH_NOT_FOUND,
        {"program": r"C:\ssh.exe"},
    )


def test_a_missing_askpass_program_is_not_taken_for_a_missing_ssh() -> None:
    assert start_failure(AskpassNotFoundError(r"C:\a.exe")) == (
        Announce.ASKPASS_NOT_FOUND,
        {"program": r"C:\a.exe"},
    )


@pytest.mark.parametrize(
    "error", [InvalidConnectionError("target", "option_like"), NamedPipeError("CreateNamedPipe", 5)]
)
def test_any_other_failure_to_start_is_a_plain_failure(error: Exception) -> None:
    assert start_failure(error) == (Announce.LAUNCH_FAILED, {"program": "SSH"})  # type: ignore[arg-type]


# The names -------------------------------------------------------------------------------------


def test_the_title_of_the_window_says_the_profile_and_the_connection() -> None:
    assert connection_title(None, "prod", True, same) == "MiTerm-N5: free profile on SSH prod"
    assert connection_title("git", "prod", True, same) == "MiTerm-N5: git on SSH prod"


def test_the_title_says_only_that_the_connection_is_not_open() -> None:
    assert connection_title(None, "prod", False, same) == (
        "MiTerm-N5: free profile on SSH prod (not connected)"
    )


def test_the_output_names_the_connection_and_its_target() -> None:
    assert connection_heading("prod", same) == "SSH prod"
    assert connection_target_line("admin@example.org", None, same) == "To admin@example.org"
    assert connection_target_line("admin@example.org", 2222, same) == "To admin@example.org:2222"


def test_the_dialogs_say_who_asks_and_where_it_goes() -> None:
    assert connection_dialog_title("prod", same) == "Connection to prod"
    assert connection_secret_title("prod", same) == "Connection prod: password"
    assert connection_where("admin@example.org", None, same) == "admin@example.org"
    assert connection_where("admin@example.org", 2222, same) == "admin@example.org, port 2222"


def test_the_status_once_connected_names_the_connection() -> None:
    assert connected_status("prod", same) == "Connected to prod"


def test_the_command_field_is_named_after_what_it_takes() -> None:
    idle = SessionState()
    assert input_label(idle, "", same) == "Command"
    assert input_label(idle, "dev", same) == "dev"
    assert input_label(replace(idle, connection="prod"), "dev", same) == "Command"
    running = replace(idle, phase=Phase.RUNNING)
    assert input_label(running, "dev", same) == "Message"
    shell = replace(running, interpreter=Interpreter.CMD, shell_at_prompt=True)
    assert input_label(shell, "", same) == "Command"
    assert input_label(replace(running, connection="prod"), "", same) == "Command"
