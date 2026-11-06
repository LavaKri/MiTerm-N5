import ast
import errno
import io
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from multiprocessing.connection import Listener
from pathlib import Path

import pytest

from n5terminal import askpass
from n5terminal.askpass import (
    CONNECTED_ARGUMENT,
    EXIT_ANSWERED,
    EXIT_REFUSED,
    EXIT_UNREACHABLE,
    PIPE_VARIABLE,
    TOKEN_VARIABLE,
    Pipe,
    request_for,
    run,
)

pytestmark = pytest.mark.unit

QUESTION = "TestSSH@127.0.0.1's password: "
ENVIRON = {PIPE_VARIABLE: r"\\.\pipe\n5terminal-askpass-test", TOKEN_VARIABLE: "t0k3n"}


class FakePipe:
    """The application's end of the pipe: records what is sent, replies with a fixed line."""

    def __init__(self, reply: bytes) -> None:
        self.reply = reply
        self.sent = b""
        self.closed = False

    def write(self, data: bytes, /) -> int:
        self.sent += data
        return len(data)

    def readline(self) -> bytes:
        return self.reply

    def close(self) -> None:
        self.closed = True


LIMITS: list[float] = []  # the delays the program asked its watchdog for


def _watchdog(seconds: float) -> Callable[[], None]:
    LIMITS.append(seconds)
    return lambda: LIMITS.append(0.0)  # stopping it is noted as 0


def _run(
    arguments: list[str], reply: bytes, environ: dict[str, str] | None = None
) -> tuple[int, bytes, FakePipe]:
    pipe = FakePipe(reply)
    out = io.BytesIO()
    LIMITS.clear()
    code = run(arguments, ENVIRON if environ is None else environ, out, lambda _p: pipe, _watchdog)
    return code, out.getvalue(), pipe


def _reply(**fields: object) -> bytes:
    return json.dumps(fields).encode("utf-8") + b"\n"


# The request -----------------------------------------------------------------------------------


def test_a_question_is_sent_with_the_token() -> None:
    assert request_for([QUESTION], "t") == {"token": "t", "event": "ask", "text": QUESTION}


def test_connected_is_its_own_event() -> None:
    request = request_for([CONNECTED_ARGUMENT], "t")
    assert request == {"token": "t", "event": "connected", "text": ""}


def test_the_request_is_one_line_of_json_with_the_text_as_it_is() -> None:
    question = "Enter passphrase for key 'C:\\Users\\Été\\.ssh\\id': "
    _, _, pipe = _run([question], _reply(answer="x"))
    assert pipe.sent.endswith(b"\n")
    assert pipe.sent.count(b"\n") == 1
    assert json.loads(pipe.sent.decode("utf-8")) == {
        "token": "t0k3n",
        "event": "ask",
        "text": question,
    }


# The answer ------------------------------------------------------------------------------------


def test_the_answer_goes_to_the_standard_output_for_ssh() -> None:
    code, out, pipe = _run([QUESTION], _reply(answer="secret"))
    assert (code, out) == (EXIT_ANSWERED, b"secret\n")
    assert pipe.closed


def test_the_answer_is_written_as_utf8() -> None:
    _, out, _ = _run([QUESTION], _reply(answer="mdp-é€"))
    assert out == "mdp-é€\n".encode()


def test_an_empty_answer_is_an_answer() -> None:
    code, out, _ = _run([QUESTION], _reply(answer=""))
    assert (code, out) == (EXIT_ANSWERED, b"\n")


def test_a_refusal_writes_nothing_and_stops_ssh() -> None:
    code, out, _ = _run([QUESTION], _reply(refused=True))
    assert (code, out) == (EXIT_REFUSED, b"")


def test_connected_is_acknowledged_without_any_output() -> None:
    code, out, _ = _run([CONNECTED_ARGUMENT], _reply(ok=True))
    assert (code, out) == (EXIT_ANSWERED, b"")


def test_connected_without_an_acknowledgement_is_unreachable() -> None:
    code, out, _ = _run([CONNECTED_ARGUMENT], _reply())
    assert (code, out) == (EXIT_UNREACHABLE, b"")


# What goes wrong -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [b"", b"\n", b"not json\n", b"[1]\n", b'"text"\n', _reply(), _reply(answer=3), _reply(x=1)],
)
def test_a_missing_or_malformed_reply_is_unreachable_and_writes_nothing(reply: bytes) -> None:
    code, out, _ = _run([QUESTION], reply)
    assert (code, out) == (EXIT_UNREACHABLE, b"")


@pytest.mark.parametrize(
    "environ",
    [{}, {PIPE_VARIABLE: "x"}, {TOKEN_VARIABLE: "x"}, {PIPE_VARIABLE: "", TOKEN_VARIABLE: "x"}],
)
def test_without_the_pipe_or_the_token_nothing_is_sent(environ: dict[str, str]) -> None:
    code, out, pipe = _run([QUESTION], _reply(answer="x"), environ)
    assert (code, out, pipe.sent) == (EXIT_UNREACHABLE, b"", b"")


def test_without_an_argument_nothing_is_sent() -> None:
    code, out, pipe = _run([], _reply(answer="x"))
    assert (code, out, pipe.sent) == (EXIT_UNREACHABLE, b"", b"")


def test_an_application_that_is_gone_is_unreachable() -> None:
    def missing(_path: str) -> Pipe:
        raise FileNotFoundError("no pipe")

    out = io.BytesIO()
    assert run([QUESTION], ENVIRON, out, missing) == EXIT_UNREACHABLE
    assert out.getvalue() == b""


def test_a_pipe_that_breaks_during_the_exchange_is_unreachable() -> None:
    class Broken(FakePipe):
        def readline(self) -> bytes:
            raise BrokenPipeError("closed")

    pipe = Broken(b"")
    out = io.BytesIO()
    assert run([QUESTION], ENVIRON, out, lambda _path: pipe) == EXIT_UNREACHABLE
    assert pipe.closed


def test_a_question_waits_for_the_user_and_the_connected_signal_does_not() -> None:
    """``ssh`` waits for LocalCommand before opening the shell (measured): it must be short."""
    _run([QUESTION], _reply(answer="x"))
    assert LIMITS == [askpass.ASK_LIMIT, 0.0]  # started, then stopped when the answer came
    _run([CONNECTED_ARGUMENT], _reply(ok=True))
    assert LIMITS == [askpass.CONNECTED_LIMIT, 0.0]
    assert askpass.CONNECTED_LIMIT < askpass.ASK_LIMIT


def test_the_watchdog_is_stopped_when_the_exchange_fails() -> None:
    _run([QUESTION], b"")
    assert LIMITS == [askpass.ASK_LIMIT, 0.0]


def test_nothing_is_watched_when_nothing_is_sent() -> None:
    _run([], _reply(answer="x"))
    assert LIMITS == []


def test_the_real_watchdog_can_be_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    ended: list[int] = []
    monkeypatch.setattr(os, "_exit", ended.append)
    askpass.start_watchdog(0.05)()  # started and stopped at once
    time.sleep(0.15)
    assert ended == []
    askpass.start_watchdog(0.05)  # not stopped: it ends the program
    time.sleep(0.3)
    assert ended == [EXIT_UNREACHABLE]


def test_a_pipe_busy_between_two_calls_is_tried_again(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []
    waits: list[tuple[str, int]] = []
    opened = object()

    def file_io(path: str, mode: str) -> object:
        attempts.append(path)
        if len(attempts) < 3:
            raise OSError(errno.EINVAL, "busy")  # how FileIO reports ERROR_PIPE_BUSY
        return opened

    monkeypatch.setattr(io, "FileIO", file_io)
    monkeypatch.setattr(askpass, "wait_for_instance", lambda p, ms: waits.append((p, ms)))
    assert askpass.open_pipe(r"\\.\pipe\x") is opened
    assert len(attempts) == 3
    assert waits == [(r"\\.\pipe\x", askpass.BUSY_WAIT_MS)] * 2


def test_a_pipe_that_does_not_exist_is_not_waited_for(monkeypatch: pytest.MonkeyPatch) -> None:
    def file_io(path: str, mode: str) -> object:
        raise FileNotFoundError(errno.ENOENT, "no pipe")

    monkeypatch.setattr(io, "FileIO", file_io)
    monkeypatch.setattr(askpass, "wait_for_instance", lambda p, ms: pytest.fail("waited"))
    with pytest.raises(FileNotFoundError):
        askpass.open_pipe(r"\\.\pipe\none")


def test_a_pipe_that_stays_busy_ends_with_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def file_io(path: str, mode: str) -> object:
        raise OSError(errno.EINVAL, "busy")

    monkeypatch.setattr(io, "FileIO", file_io)
    monkeypatch.setattr(askpass, "wait_for_instance", lambda p, ms: None)
    with pytest.raises(OSError, match="busy"):
        askpass.open_pipe(r"\\.\pipe\busy")


def test_the_module_imports_nothing_but_the_standard_library() -> None:
    """It is started for every question: no wx, nothing of the rest of the package."""
    assert askpass.__file__ is not None
    tree = ast.parse(Path(askpass.__file__).read_text(encoding="utf-8"))
    imported = {
        (node.module or "") if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias("")])
    }
    assert imported
    assert {name.split(".")[0] for name in imported} <= set(sys.stdlib_module_names)


# With a real named pipe ------------------------------------------------------------------------


def _serve_once(listener: Listener, reply: bytes, received: list[bytes]) -> threading.Thread:
    def serve() -> None:
        with listener.accept() as connection:
            received.append(connection.recv_bytes())
            connection.send_bytes(reply)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread


def _pipe_name() -> str:
    return rf"\\.\pipe\n5terminal-askpass-test-{uuid.uuid4().hex}"


@pytest.mark.skipif(sys.platform != "win32", reason="named pipes of Windows")
def test_the_real_pipe_carries_the_request_and_the_answer() -> None:
    name = _pipe_name()
    received: list[bytes] = []
    with Listener(name, family="AF_PIPE") as listener:
        thread = _serve_once(listener, _reply(answer="mdp-é"), received)
        out = io.BytesIO()
        environ = {PIPE_VARIABLE: name, TOKEN_VARIABLE: "t0k3n"}
        assert run([QUESTION], environ, out) == EXIT_ANSWERED
        thread.join(5)
    assert out.getvalue() == "mdp-é\n".encode()
    assert json.loads(received[0])["text"] == QUESTION


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="named pipes of Windows")
def test_the_program_run_as_ssh_runs_it() -> None:
    """A separate process: the arguments, the environment, the bytes on stdout, the exit code."""
    name = _pipe_name()
    received: list[bytes] = []
    with Listener(name, family="AF_PIPE") as listener:
        thread = _serve_once(listener, _reply(answer="mdp-é"), received)
        environment = {**os.environ, PIPE_VARIABLE: name, TOKEN_VARIABLE: "t0k3n"}
        done = subprocess.run(
            [sys.executable, "-m", "n5terminal.askpass", QUESTION],
            env=environment,
            capture_output=True,
            timeout=30,
            check=False,
        )
        thread.join(5)
    assert (done.returncode, done.stdout, done.stderr) == (0, "mdp-é\n".encode(), b"")
    assert json.loads(received[0])["token"] == "t0k3n"


@pytest.mark.slow
def test_the_program_without_the_application_exits_with_a_code_and_says_nothing() -> None:
    environment = {**os.environ, PIPE_VARIABLE: _pipe_name(), TOKEN_VARIABLE: "t"}
    done = subprocess.run(
        [sys.executable, "-m", "n5terminal.askpass", QUESTION],
        env=environment,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert (done.returncode, done.stdout, done.stderr) == (EXIT_UNREACHABLE, b"", b"")
