import io
import logging
import secrets
import sys
import time
from pathlib import Path

import pytest

from fakes.fake_interaction import FakeInteraction
from fakes.program_ssh import RIGHT_PASSWORD
from fakes.recording_listener import WAIT_TIMEOUT, RecordingListener
from fakes.screen_text import screen_lines
from n5terminal import askpass
from n5terminal.core.errors import (
    AskpassNotFoundError,
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    NamedPipeError,
    ProgramNotFoundError,
    TransportClosedError,
)
from n5terminal.core.transport.ssh_launch import SshLaunch
from n5terminal.core.transport.ssh_transport import SshTransport
from n5terminal.core.transport.transport import (
    ConnectionReport,
    Stream,
    TransportState,
)

pytestmark = pytest.mark.slow

FAKE_SSH = Path(__file__).parents[2] / "fakes" / "program_ssh.py"
ASKPASS = Path(sys.executable).parent / "n5terminal-askpass.exe"
S = TransportState


class OrderedListener(RecordingListener):
    """Also keeps what happened in the order it happened."""

    def __init__(self) -> None:
        super().__init__()
        self.order: list[str] = []

    def on_state_changed(self, state: TransportState) -> None:
        self.order.append(state.value)
        super().on_state_changed(state)

    def on_data(self, stream: Stream, data: bytes) -> None:
        self.order.append("data:" + data.decode("utf-8", errors="replace"))
        super().on_data(stream, data)


def make(
    flags: str,
    interaction: FakeInteraction,
    askpass_program: Path = ASKPASS,
    ssh_program: Path = Path(sys.executable),
) -> tuple[SshTransport, OrderedListener, SshLaunch]:
    launch = SshLaunch(
        target=f"fake@{flags}",
        askpass_program=askpass_program,
        pipe_name=rf"\\.\pipe\n5terminal-askpass-test-{secrets.token_hex(8)}",
        token=secrets.token_hex(8),
        ssh_program=ssh_program,
        program_arguments=(str(FAKE_SSH),),
    )
    return SshTransport(launch, interaction, Path.cwd()), OrderedListener(), launch


def run(flags: str, interaction: FakeInteraction) -> tuple[SshTransport, OrderedListener]:
    transport, listener, _ = make(flags, interaction)
    transport.start(listener)
    return transport, listener


def shown(listener: RecordingListener) -> list[str]:
    return screen_lines(listener.received(Stream.OUTPUT).decode(errors="replace"))


def wait_for(listener: RecordingListener, text: str) -> None:
    deadline = time.monotonic() + WAIT_TIMEOUT
    while not any(text in line for line in shown(listener)):
        assert time.monotonic() < deadline, f"{text!r} not shown in time: {shown(listener)}"
        time.sleep(0.05)


def leave(transport: SshTransport, listener: RecordingListener) -> None:
    """Type ``exit`` at the shell of the fake server, and wait for the end."""
    wait_for(listener, "fake$")
    transport.write(b"exit\r")
    listener.wait_closed()


@pytest.fixture(autouse=True)
def _needs_the_askpass_program() -> None:
    assert ASKPASS.is_file(), "install the project (pip install -e .) to get n5terminal-askpass.exe"


# A connection that asks nothing ----------------------------------------------------------------


def test_a_connection_by_key_goes_from_connecting_to_connected_to_closed() -> None:
    interaction = FakeInteraction()
    transport, listener = run("key", interaction)
    leave(transport, listener)
    assert listener.states == [S.CONNECTING, S.CONNECTED, S.CLOSED]
    assert listener.exit_codes == [0]
    assert (transport.failure, transport.cancelled) == (None, False)
    assert (interaction.host_key_texts, interaction.secret_questions) == ([], [])


def test_connected_comes_before_the_first_line_of_the_server() -> None:
    """``ssh`` waits for the signal before it opens the session: the order can be relied on."""
    transport, listener = run("key", FakeInteraction())
    leave(transport, listener)
    welcome = next(i for i, item in enumerate(listener.order) if "Welcome" in item)
    assert listener.order.index("connected") < welcome


def test_what_is_typed_reaches_the_server_and_its_answer_comes_back() -> None:
    transport, listener = run("key", FakeInteraction())
    wait_for(listener, "fake$")
    transport.write(b"hello\r")
    wait_for(listener, "you said: hello")
    transport.write(b"exit 7\r")
    listener.wait_closed()
    assert listener.exit_codes == [7]
    assert listener.states[-1] is S.CLOSED


def test_the_transport_reports_how_it_ended_to_who_asks() -> None:
    transport, _ = run("key", FakeInteraction())
    assert isinstance(transport, ConnectionReport)
    transport.close()


# The host key ----------------------------------------------------------------------------------


def test_a_host_key_the_user_trusts_is_answered_yes() -> None:
    interaction = FakeInteraction(host_keys=[True])
    transport, listener = run("hostkey", interaction)
    leave(transport, listener)
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.CONNECTED, S.CLOSED]
    [text] = interaction.host_key_texts
    assert "ED25519 key fingerprint is SHA256:" in text
    assert text.endswith("(yes/no/[fingerprint])? ")
    assert interaction.secret_questions == []


def test_a_host_key_the_user_refuses_ends_the_connection_without_an_error() -> None:
    interaction = FakeInteraction(host_keys=[False])
    transport, listener = run("hostkey", interaction)
    listener.wait_closed()
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.CLOSED]
    assert listener.exit_codes == [255]
    assert (transport.failure, transport.cancelled) == (None, True)
    assert "Host key verification failed." in shown(listener)


def test_a_changed_host_key_is_an_error_of_the_host_key() -> None:
    interaction = FakeInteraction()
    transport, listener = run("changedkey", interaction)
    listener.wait_closed()
    assert listener.states == [S.CONNECTING, S.FAILED]
    assert isinstance(transport.failure, HostKeyError)
    assert transport.cancelled is False
    assert interaction.host_key_texts == []  # ssh does not ask: it refuses by itself


# The password ----------------------------------------------------------------------------------


def test_a_password_is_asked_with_the_question_of_ssh_and_its_answer_given_back() -> None:
    interaction = FakeInteraction(host_keys=[True], secrets=[RIGHT_PASSWORD])
    transport, listener = run("hostkey.password", interaction)
    leave(transport, listener)
    assert interaction.secret_questions == ["fake@hostkey.password's password: "]
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.CONNECTED, S.CLOSED]


def test_a_wrong_password_is_asked_again_and_the_right_one_connects() -> None:
    interaction = FakeInteraction(secrets=["wrong", RIGHT_PASSWORD])
    transport, listener = run("password", interaction)
    leave(transport, listener)
    assert len(interaction.secret_questions) == 2
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.CONNECTED, S.CLOSED]


def test_three_wrong_passwords_are_an_authentication_error() -> None:
    interaction = FakeInteraction(secrets=["a", "b", "c"])
    transport, listener = run("password", interaction)
    listener.wait_closed()
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.FAILED]
    assert isinstance(transport.failure, AuthenticationError)
    assert "Permission denied" in transport.failure.detail
    assert transport.cancelled is False
    assert listener.exit_codes == [255]


def test_a_cancelled_password_is_not_asked_again_though_ssh_asks_three_times() -> None:
    interaction = FakeInteraction(secrets=[None, "never used", "never used"])
    transport, listener = run("password", interaction)
    listener.wait_closed()
    assert len(interaction.secret_questions) == 1  # the other two calls were refused unasked
    assert listener.states == [S.CONNECTING, S.AUTHENTICATING, S.CLOSED]
    assert (transport.failure, transport.cancelled) == (None, True)


def test_a_password_never_goes_to_the_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    interaction = FakeInteraction(host_keys=[True], secrets=[RIGHT_PASSWORD])
    transport, listener = run("hostkey.password", interaction)
    leave(transport, listener)
    assert RIGHT_PASSWORD not in caplog.text
    assert "password" not in caplog.text.lower()
    assert "fingerprint" not in caplog.text


# Errors before the connection ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flags", "word"), [("refused", "Connection refused"), ("timeout", "Connection timed out")]
)
def test_a_server_that_cannot_be_reached_is_a_connection_failure(flags: str, word: str) -> None:
    transport, listener = run(flags, FakeInteraction())
    listener.wait_closed()
    assert listener.states == [S.CONNECTING, S.FAILED]
    assert isinstance(transport.failure, ConnectionFailedError)
    assert word in transport.failure.detail
    assert listener.exit_codes == [255]
    assert any(word in line for line in shown(listener))  # the text stays in the output


# What happens after the connection -------------------------------------------------------------


def test_a_connection_that_drops_closes_with_255_and_is_not_an_error_of_the_connection() -> None:
    transport, listener = run("drop", FakeInteraction())
    listener.wait_closed()
    assert listener.states == [S.CONNECTING, S.CONNECTED, S.CLOSED]
    assert listener.exit_codes == [255]
    assert transport.failure is None  # it was connected: 255 is the code, not a refusal


def test_a_remote_text_that_looks_like_an_error_does_not_make_one_after_connected() -> None:
    transport, listener = run("key", FakeInteraction())
    wait_for(listener, "fake$")
    transport.write(b"Permission denied (publickey,password).\r")
    wait_for(listener, "you said: Permission denied")
    transport.write(b"exit 255\r")
    listener.wait_closed()
    assert listener.states[-1] is S.CLOSED
    assert transport.failure is None


def test_close_stops_the_connection() -> None:
    transport, listener = run("key", FakeInteraction())
    wait_for(listener, "fake$")
    transport.close()
    listener.wait_closed()
    assert listener.states[-1] is S.CLOSED
    assert transport.failure is None


# The signal that can be lost -------------------------------------------------------------------


def test_a_session_that_ends_without_the_signal_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    transport, listener = run("nosignal.bye", FakeInteraction())
    listener.wait_closed()
    assert S.CONNECTED not in listener.states  # nothing is guessed from the output or the time
    assert listener.states[-1] is S.CLOSED
    assert transport.failure is None
    assert "without having said the connection was made" in caplog.text


def test_without_the_signal_nothing_can_be_written() -> None:
    transport, listener = run("nosignal", FakeInteraction())
    wait_for(listener, "fake$")
    with pytest.raises(TransportClosedError):
        transport.write(b"hello\r")
    transport.close()
    listener.wait_closed()


# The dialog still open -------------------------------------------------------------------------


def test_writing_is_refused_while_a_question_is_open() -> None:
    interaction = FakeInteraction(host_keys=[False])
    interaction.hold = True
    transport, listener = run("hostkey", interaction)
    assert interaction.opened.wait(WAIT_TIMEOUT)
    assert transport.state is S.AUTHENTICATING
    with pytest.raises(TransportClosedError):
        transport.write(b"x")
    interaction.release()
    listener.wait_closed()


def test_closing_withdraws_the_open_dialog() -> None:
    interaction = FakeInteraction(host_keys=[True])
    interaction.hold = True
    transport, listener = run("hostkey", interaction)
    assert interaction.opened.wait(WAIT_TIMEOUT)
    transport.close()
    listener.wait_closed()
    assert interaction.withdrawn >= 1
    assert listener.states[-1] is S.CLOSED
    assert transport.failure is None


def test_a_second_question_while_one_is_open_withdraws_the_first() -> None:
    """The program that asked the first one gave up (its limit): ssh asks again, the old dialog
    is stale, and nothing is asked twice."""
    interaction = FakeInteraction(secrets=[RIGHT_PASSWORD])
    interaction.hold = True
    transport, listener, launch = make("password", interaction)
    transport.start(listener)
    assert interaction.opened.wait(WAIT_TIMEOUT)
    environ = {askpass.PIPE_VARIABLE: launch.pipe_name, askpass.TOKEN_VARIABLE: launch.token}
    out = io.BytesIO()
    code = askpass.run(["a second password: "], environ, out, watchdog=lambda _s: lambda: None)
    assert (code, out.getvalue()) == (askpass.EXIT_REFUSED, b"")
    assert interaction.withdrawn == 1
    assert len(interaction.secret_questions) == 1
    assert transport.cancelled is True
    interaction.release()
    listener.wait_closed()


def test_ssh_ending_while_a_question_is_open_withdraws_it_without_an_error() -> None:
    """The program gave up and ssh ended: the user did not answer in time, which is a cancel."""
    interaction = FakeInteraction()
    interaction.hold = True
    transport, listener = run("hostkey", interaction)
    assert interaction.opened.wait(WAIT_TIMEOUT)
    inner = transport._inner
    assert inner is not None
    inner.close()  # ssh is killed while the dialog is still on screen
    listener.wait_closed()
    assert interaction.withdrawn >= 1
    assert (transport.failure, transport.cancelled) == (None, True)


# Starting that fails ---------------------------------------------------------------------------


def test_a_missing_askpass_program_is_refused_before_anything_starts() -> None:
    transport, listener, launch = make(
        "key", FakeInteraction(), askpass_program=Path("C:/no/a.exe")
    )
    with pytest.raises(AskpassNotFoundError):
        transport.start(listener)
    assert listener.states == [S.CONNECTING, S.FAILED]
    with pytest.raises(FileNotFoundError):  # no pipe was left
        askpass.open_pipe(launch.pipe_name)


def test_a_missing_ssh_is_a_program_not_found_and_leaves_no_pipe() -> None:
    transport, listener, launch = make("key", FakeInteraction(), ssh_program=Path("C:/no/ssh.exe"))
    with pytest.raises(ProgramNotFoundError) as refused:
        transport.start(listener)
    assert not isinstance(refused.value, AskpassNotFoundError)
    assert listener.states[0] is S.CONNECTING
    assert listener.states[-1] is S.FAILED
    time.sleep(0.2)  # the thread that waited for a client ends
    with pytest.raises(FileNotFoundError):
        askpass.open_pipe(launch.pipe_name)


def test_a_pipe_name_already_in_use_is_a_pipe_error() -> None:
    first, first_listener, launch = make("key", FakeInteraction())
    first.start(first_listener)
    try:
        second = SshTransport(launch, FakeInteraction(), Path.cwd())
        with pytest.raises(NamedPipeError):
            second.start(OrderedListener())
    finally:
        first.close()
        first_listener.wait_closed()


def test_a_transport_cannot_be_started_twice() -> None:
    transport, listener = run("key", FakeInteraction())
    try:
        with pytest.raises(Exception, match="already started"):
            transport.start(listener)
    finally:
        transport.close()
        listener.wait_closed()
