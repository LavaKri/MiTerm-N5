import sys
import time
from pathlib import Path

import pytest
import winpty

from fakes.recording_listener import WAIT_TIMEOUT, RecordingListener
from fakes.screen_text import screen_lines
from n5terminal.core.errors import (
    LaunchError,
    ProgramNotFoundError,
    TransportClosedError,
    WorkingFolderError,
)
from n5terminal.core.transport.conpty_transport import ConPtyLaunch, ConPtyTransport
from n5terminal.core.transport.pipe_transport import PipeLaunch, PipeTransport
from n5terminal.core.transport.transport import Stream, TransportState

pytestmark = pytest.mark.slow

PROGRAM = str(Path(__file__).parents[2] / "fakes" / "program_tui_line.py")


def run(*scenario: str) -> tuple[ConPtyTransport, RecordingListener]:
    transport = ConPtyTransport(ConPtyLaunch((sys.executable, PROGRAM, *scenario), Path.cwd()))
    listener = RecordingListener()
    transport.start(listener)
    return transport, listener


def shown(listener: RecordingListener) -> list[str]:
    return screen_lines(listener.received(Stream.OUTPUT).decode())


def wait_for(listener: RecordingListener, text: str) -> None:
    deadline = time.monotonic() + WAIT_TIMEOUT
    while not any(text in line for line in shown(listener)):
        assert time.monotonic() < deadline, f"{text!r} not shown in time: {shown(listener)}"
        time.sleep(0.05)


def test_the_program_sees_a_terminal() -> None:
    _, listener = run("terminal")
    listener.wait_closed()
    assert shown(listener) == ["terminal: yes", "red plain"]
    assert listener.exit_codes == [0]
    assert listener.states == [
        TransportState.CONNECTING,
        TransportState.CONNECTED,
        TransportState.CLOSED,
    ]


def test_the_same_program_refuses_pipes() -> None:
    launch = PipeLaunch((sys.executable, PROGRAM, "terminal"), Path.cwd())
    listener = RecordingListener()
    PipeTransport(launch).start(listener)
    listener.wait_closed()
    assert listener.received(Stream.ERROR).decode().strip() == "not a terminal"
    assert listener.exit_codes == [2]


def test_typed_input_is_echoed_by_the_terminal() -> None:
    transport, listener = run("echo-input")
    wait_for(listener, "name?")
    transport.write(b"hello\r")
    listener.wait_closed()
    assert shown(listener) == ["name? hello", "got: hello"]


def test_a_password_is_not_echoed() -> None:
    transport, listener = run("password")
    wait_for(listener, "password:")
    transport.write(b"secret\r")
    listener.wait_closed()
    assert shown(listener) == ["password:", "length 6"]


def test_resize_reaches_the_program() -> None:
    transport, listener = run("size")
    wait_for(listener, "ready?")
    transport.resize(100, 30)
    transport.write(b"\r")
    listener.wait_closed()
    assert "size 100x30" in listener.received(Stream.OUTPUT).decode()


def test_exit_code() -> None:
    _, listener = run("exit", "3")
    listener.wait_closed()
    assert listener.exit_codes == [3]


def test_close_stops_a_running_program() -> None:
    transport, listener = run("sleep")
    transport.close()
    listener.wait_closed()
    assert listener.exit_codes != [0]
    with pytest.raises(TransportClosedError):
        transport.write(b"late\r")


def test_unknown_program_fails() -> None:
    transport = ConPtyTransport(ConPtyLaunch(("n5terminal-no-such-program",), Path.cwd()))
    listener = RecordingListener()
    with pytest.raises(ProgramNotFoundError):
        transport.start(listener)
    assert listener.states == [TransportState.CONNECTING, TransportState.FAILED]


@pytest.mark.parametrize("failure", [OSError("refused"), ValueError("refused")])
def test_a_failure_of_the_pseudo_console_is_a_launch_error(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def refuse(*_arguments: object, **_keywords: object) -> None:
        raise failure

    monkeypatch.setattr(winpty, "PTY", refuse)
    transport = ConPtyTransport(ConPtyLaunch((sys.executable,), Path.cwd()))
    listener = RecordingListener()
    with pytest.raises(LaunchError):
        transport.start(listener)
    assert listener.states == [TransportState.CONNECTING, TransportState.FAILED]


def test_missing_working_folder_fails(tmp_path: Path) -> None:
    launch = ConPtyLaunch((sys.executable,), tmp_path / "missing")
    with pytest.raises(WorkingFolderError):
        ConPtyTransport(launch).start(RecordingListener())
