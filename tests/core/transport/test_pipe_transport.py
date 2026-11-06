import sys
import time
from pathlib import Path

import pytest

from fakes.recording_listener import WAIT_TIMEOUT, RecordingListener
from n5terminal.core.errors import (
    LaunchError,
    ProgramNotFoundError,
    TransportClosedError,
    WorkingFolderError,
)
from n5terminal.core.transport.pipe_transport import PipeLaunch, PipeTransport
from n5terminal.core.transport.transport import Stream, TransportState

pytestmark = pytest.mark.slow

PROGRAM = Path(__file__).parents[2] / "fakes" / "program_cli.py"


def run(*scenario: str) -> tuple[PipeTransport, RecordingListener]:
    launch = PipeLaunch((sys.executable, "-u", str(PROGRAM), *scenario), Path.cwd())
    transport = PipeTransport(launch)
    listener = RecordingListener()
    transport.start(listener)
    return transport, listener


def lines(data: bytes) -> list[str]:
    return data.decode().splitlines()


def test_stdout_and_stderr_arrive_apart_with_the_exit_code() -> None:
    _, listener = run("both-streams")
    listener.wait_closed()
    assert lines(listener.received(Stream.OUTPUT)) == ["out"]
    assert lines(listener.received(Stream.ERROR)) == ["err"]
    assert listener.exit_codes == [3]
    assert listener.states == [
        TransportState.CONNECTING,
        TransportState.CONNECTED,
        TransportState.CLOSED,
    ]


def test_input_reaches_the_program() -> None:
    transport, listener = run("echo-input")
    transport.write(b"hello\n")
    transport.write(b"quit\n")
    listener.wait_closed()
    assert lines(listener.received(Stream.OUTPUT)) == ["got: hello"]
    assert listener.exit_codes == [0]


def test_no_output_is_lost_when_the_program_writes_fast() -> None:
    _, listener = run("flood", "20000")
    listener.wait_closed()
    received = lines(listener.received(Stream.OUTPUT))
    assert len(received) == 20000
    assert received[-1] == "line 19999"


def test_a_character_split_between_two_writes_arrives_whole_once_joined() -> None:
    _, listener = run("split-character")
    listener.wait_closed()
    assert listener.received(Stream.OUTPUT).decode() == "é"


def test_close_stops_a_running_program() -> None:
    transport, listener = run("sleep")
    transport.close()
    listener.wait_closed()
    assert listener.exit_codes != [0]
    assert transport.state is TransportState.CLOSED


def wait_for_output(listener: RecordingListener, text: bytes) -> None:
    deadline = time.monotonic() + WAIT_TIMEOUT
    while text not in listener.received(Stream.OUTPUT):
        assert time.monotonic() < deadline, "the program did not write in time"
        time.sleep(0.05)


@pytest.mark.parametrize("scenario", ["child-and-wait", "child-and-end"])
def test_close_stops_the_processes_the_program_started(scenario: str) -> None:
    transport, listener = run(scenario)
    wait_for_output(listener, b"child started")
    # The child holds the output pipes: the session only ends when the child is stopped too.
    assert not listener.closed.wait(0.5)
    transport.close()
    listener.wait_closed()


def test_the_end_of_the_program_is_reported_while_its_child_still_runs() -> None:
    transport, listener = run("child-and-end")
    assert listener.exited.wait(WAIT_TIMEOUT)
    assert listener.exit_codes == [0]
    assert not listener.closed.is_set()
    assert transport.state is TransportState.CONNECTED
    with pytest.raises(TransportClosedError):
        transport.write(b"too late\n")
    transport.close()
    listener.wait_closed()
    assert listener.states[-1] is TransportState.CLOSED


def test_writing_after_the_end_is_refused() -> None:
    transport, listener = run("both-streams")
    listener.wait_closed()
    with pytest.raises(TransportClosedError):
        transport.write(b"late\n")


def test_unknown_program_fails() -> None:
    transport = PipeTransport(PipeLaunch(("n5terminal-no-such-program",), Path.cwd()))
    listener = RecordingListener()
    with pytest.raises(ProgramNotFoundError):
        transport.start(listener)
    assert listener.states == [TransportState.CONNECTING, TransportState.FAILED]


def test_an_argument_the_system_refuses_is_a_launch_error() -> None:
    transport = PipeTransport(PipeLaunch((sys.executable, "a\0b"), Path.cwd()))
    listener = RecordingListener()
    with pytest.raises(LaunchError):
        transport.start(listener)
    assert listener.states == [TransportState.CONNECTING, TransportState.FAILED]


def test_missing_working_folder_fails(tmp_path: Path) -> None:
    launch = PipeLaunch((sys.executable,), tmp_path / "missing")
    with pytest.raises(WorkingFolderError):
        PipeTransport(launch).start(RecordingListener())
