import pytest

from n5terminal.core.errors import (
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    SshConnectionError,
)
from n5terminal.core.transport.ssh_errors import TAIL_LENGTH, classify_ssh_end

pytestmark = pytest.mark.unit

# The texts are the ones measured with the ssh.exe of Windows (specs/architecture/transport.md).
HOST_KEY_CHANGED = (
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\r\n"
    "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\r\n"
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\r\n"
    "IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!\r\n"
    "Offending ED25519 key in C:\\Users\\Codeur/.ssh/known_hosts:3\r\n"
    "Host key verification failed.\r\n"
)
WRONG_PASSWORD = (
    "Permission denied, please try again.\r\n"
    "Permission denied, please try again.\r\n"
    "TestSSH@127.0.0.1: Permission denied (publickey,password).\r\n"
)


def kind(output: str, code: int | None = 255, cancelled: bool = False) -> type | None:
    error = classify_ssh_end(output, code, cancelled)
    return None if error is None else type(error)


# The three kinds -------------------------------------------------------------------------------


def test_a_changed_host_key() -> None:
    error = classify_ssh_end(HOST_KEY_CHANGED, 255)
    assert isinstance(error, HostKeyError)
    assert "REMOTE HOST IDENTIFICATION HAS CHANGED" in error.detail


def test_a_host_key_that_cannot_be_verified() -> None:
    error = classify_ssh_end("Host key verification failed.\r\n", 255)
    assert isinstance(error, HostKeyError)
    assert error.detail == "Host key verification failed."


def test_a_wrong_password_after_the_last_try() -> None:
    error = classify_ssh_end(WRONG_PASSWORD, 255)
    assert isinstance(error, AuthenticationError)
    assert error.detail == "TestSSH@127.0.0.1: Permission denied (publickey,password)."


@pytest.mark.parametrize(
    ("text", "detail"),
    [
        (
            "ssh: connect to host 127.0.0.1 port 2222: Connection timed out\r\n",
            "ssh: connect to host 127.0.0.1 port 2222: Connection timed out",
        ),
        (
            "ssh: connect to host 127.0.0.1 port 2222: Connection refused\r\n",
            "ssh: connect to host 127.0.0.1 port 2222: Connection refused",
        ),
        (
            "banner exchange: Connection to UNKNOWN port -1: Connection refused\r\n",
            "banner exchange: Connection to UNKNOWN port -1: Connection refused",
        ),
        (
            "ssh: Could not resolve hostname nohost: No such host is known.\r\n",
            "ssh: Could not resolve hostname nohost: No such host is known.",
        ),
        (
            "ssh: connect to host 10.9.9.9 port 22: No route to host\r\n",
            "ssh: connect to host 10.9.9.9 port 22: No route to host",
        ),
    ],
)
def test_a_server_that_cannot_be_reached(text: str, detail: str) -> None:
    error = classify_ssh_end(text, 255)
    assert isinstance(error, ConnectionFailedError)
    assert error.detail == detail


def test_any_other_255_is_a_connection_failure_with_the_last_line() -> None:
    error = classify_ssh_end("something odd\r\nssh_dispatch_run_fatal: protocol error\r\n", 255)
    assert isinstance(error, ConnectionFailedError)
    assert error.detail == "ssh_dispatch_run_fatal: protocol error"


def test_a_255_with_no_text_is_a_connection_failure_with_no_detail() -> None:
    error = classify_ssh_end("", 255)
    assert isinstance(error, ConnectionFailedError)
    assert error.detail == ""


def test_the_errors_are_ssh_connection_errors() -> None:
    for text in (HOST_KEY_CHANGED, WRONG_PASSWORD, "Connection refused"):
        assert isinstance(classify_ssh_end(text, 255), SshConnectionError)


# When it is not an error -----------------------------------------------------------------------


@pytest.mark.parametrize("code", [0, 1, 7, 130, None])
def test_only_255_is_an_error_of_ssh(code: int | None) -> None:
    """The code of the remote command is not an error of the connection."""
    assert kind(WRONG_PASSWORD, code) is None


def test_a_cancelled_dialog_is_not_an_error() -> None:
    assert kind("Host key verification failed.\r\n", cancelled=True) is None
    assert kind(WRONG_PASSWORD, cancelled=True) is None


# What the terminal adds ------------------------------------------------------------------------


def test_escape_sequences_of_the_pseudo_console_are_ignored() -> None:
    output = (
        "\x1b[?25l\x1b[2J\x1b[m\x1b[H\x1b]0;C:\\Windows\\System32\\OpenSSH\\ssh.exe\x07"
        "\x1b[1;1HHost key verification failed.\x1b[?25h\r\n"
    )
    error = classify_ssh_end(output, 255)
    assert isinstance(error, HostKeyError)
    assert error.detail == "Host key verification failed."


def test_a_pattern_cut_by_the_wrapping_of_the_console_is_still_found() -> None:
    output = "ssh: connect to host long.server.example.org port 22: Connection ti\r\nmed out\r\n"
    assert kind(output) is ConnectionFailedError
    assert kind("TestSSH@127.0.0.1: Permission de\r\nnied (publickey).\r\n") is AuthenticationError


def test_the_accents_ssh_writes_in_octal_are_put_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Measured: a French Windows gives ``ssh: Could not resolve hostname x: H\\364te inconnu.``"""
    monkeypatch.setattr("locale.getencoding", lambda: "cp1252")
    error = classify_ssh_end("ssh: Could not resolve hostname x: H\\364te inconnu.\r\n", 255)
    assert isinstance(error, ConnectionFailedError)
    assert error.detail == "ssh: Could not resolve hostname x: Hôte inconnu."


def test_several_escaped_bytes_in_a_row_are_one_character_of_the_code_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("locale.getencoding", lambda: "utf-8")
    error = classify_ssh_end("Connection refused \\303\\251\r\n", 255)
    assert error is not None
    assert error.detail == "Connection refused é"


def test_a_backslash_pair_is_not_taken_for_an_octal_escape() -> None:
    error = classify_ssh_end("Connection refused C:\\\\123\\Users\r\n", 255)
    assert error is not None
    assert error.detail == "Connection refused C:\\\\123\\Users"


def test_only_the_end_of_the_output_counts() -> None:
    start = "TestSSH@127.0.0.1: Permission denied (publickey,password).\r\n"
    end = "\r\nssh: connect to host h port 22: Connection refused\r\n"
    assert kind(start + "x" * TAIL_LENGTH + end) is ConnectionFailedError
