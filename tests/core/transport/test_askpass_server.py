import contextlib
import io
import json
import logging
import threading
import uuid
from collections.abc import Iterator

import pytest

from n5terminal import askpass
from n5terminal.core.errors import NamedPipeError
from n5terminal.core.transport.askpass_server import (
    REFUSED,
    AskpassHandler,
    AskpassReply,
    AskpassRequest,
    AskpassServer,
    parse_request,
)
from n5terminal.core.transport.named_pipe import current_user_sid, security_descriptor_text

pytestmark = pytest.mark.slow

TOKEN = "t0k3n"
WAIT = 10.0


class Handler:
    """Answers each question with a fixed reply, and records what it was asked."""

    def __init__(self, reply: AskpassReply) -> None:
        self.reply = reply
        self.requests: list[AskpassRequest] = []
        self.lost: list[AskpassRequest] = []
        self.entered = threading.Event()
        self.gate: threading.Event | None = None  # when set, ``handle`` waits for it

    def handle(self, request: AskpassRequest) -> AskpassReply:
        self.requests.append(request)
        self.entered.set()
        if self.gate is not None:
            assert self.gate.wait(WAIT)
        return self.reply

    def reply_lost(self, request: AskpassRequest) -> None:
        self.lost.append(request)


def pipe_name() -> str:
    return rf"\\.\pipe\n5terminal-askpass-test-{uuid.uuid4().hex}"


@pytest.fixture
def served() -> Iterator[tuple[str, Handler, AskpassServer]]:
    name, handler = pipe_name(), Handler(AskpassReply(answer="yes"))
    server = AskpassServer(name, TOKEN, handler)
    server.start()
    yield name, handler, server
    server.close()


def call(
    name: str, event: str = "ask", text: str = "question: ", token: str = TOKEN
) -> tuple[int, bytes]:
    """The askpass program, run as ``ssh`` runs it: its exit code and what it wrote."""
    out = io.BytesIO()
    arguments = [askpass.CONNECTED_ARGUMENT] if event == "connected" else [text]
    environ = {askpass.PIPE_VARIABLE: name, askpass.TOKEN_VARIABLE: token}
    code = askpass.run(arguments, environ, out, watchdog=lambda _seconds: lambda: None)
    return code, out.getvalue()


def raw_exchange(name: str, data: bytes) -> bytes:
    """Write ``data`` to the pipe and read a line back (empty: the server closed with no reply)."""
    with contextlib.closing(askpass.open_pipe(name)) as pipe:
        pipe.write(data)
        return pipe.readline()


# What is parsed ----------------------------------------------------------------------------


def line(**fields: object) -> bytes:
    return json.dumps(fields).encode("utf-8") + b"\n"


def test_a_request_with_the_right_token_is_understood() -> None:
    parsed = parse_request(line(token=TOKEN, event="ask", text="q"), TOKEN)
    assert parsed == (AskpassRequest("ask", "q"), True)


def test_a_request_with_a_wrong_token_is_understood_but_not_trusted() -> None:
    parsed = parse_request(line(token="other", event="connected", text=""), TOKEN)
    assert parsed == (AskpassRequest("connected", ""), False)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"{}",  # no line break: it is not a whole line
        b"not json\n",
        b"[1]\n",
        line(token=TOKEN, event="other", text=""),
        line(token=TOKEN, event="ask"),
        line(token=1, event="ask", text=""),
        line(token=TOKEN, event="ask", text=3),
    ],
)
def test_anything_else_is_not_a_request(data: bytes) -> None:
    assert parse_request(data, TOKEN) is None


def test_the_reply_data_is_the_one_the_program_reads() -> None:
    assert AskpassReply(answer="x").to_data() == {"answer": "x"}
    assert AskpassReply(answer="").to_data() == {"answer": ""}
    assert AskpassReply(ok=True).to_data() == {"ok": True}
    assert REFUSED.to_data() == {"refused": True}


# The pipe ----------------------------------------------------------------------------------


def test_the_program_gets_its_answer_through_the_real_pipe(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    assert call(name, text="Enter passphrase: ") == (askpass.EXIT_ANSWERED, b"yes\n")
    assert handler.requests == [AskpassRequest("ask", "Enter passphrase: ")]


def test_the_connected_signal_reaches_the_handler(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    handler.reply = AskpassReply(ok=True)
    assert call(name, event="connected") == (askpass.EXIT_ANSWERED, b"")
    assert handler.requests == [AskpassRequest("connected", "")]


def test_a_refusal_ends_the_program_with_the_refusal_code(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    handler.reply = REFUSED
    assert call(name) == (askpass.EXIT_REFUSED, b"")


def test_a_wrong_token_is_refused_and_the_handler_never_hears_of_it(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    assert call(name, token="wrong") == (askpass.EXIT_REFUSED, b"")
    assert handler.requests == []


@pytest.mark.parametrize("data", [b"not json\n", b"[1]\n", b'{"token": 1}\n'])
def test_a_line_that_is_not_a_request_gets_no_reply(
    served: tuple[str, Handler, AskpassServer], data: bytes
) -> None:
    name, handler, _ = served
    assert raw_exchange(name, data) == b""
    assert handler.requests == []


def test_a_line_the_program_leaves_unfinished_is_dropped_when_it_leaves(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    pipe = askpass.open_pipe(name)
    pipe.write(line(token=TOKEN, event="ask", text="q")[:-1])  # without the line break
    pipe.close()
    assert call(name) == (askpass.EXIT_ANSWERED, b"yes\n")  # the pipe goes on
    assert [r.text for r in handler.requests] == ["question: "]


def test_a_line_longer_than_the_limit_is_dropped(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    try:
        reply = raw_exchange(name, b"x" * (70 * 1024) + b"\n")
    except OSError:  # the server stopped reading and closed before the whole line was written
        reply = b""
    assert reply == b""
    assert handler.requests == []


def test_calls_follow_each_other_on_the_same_pipe(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    for _ in range(8):
        assert call(name) == (askpass.EXIT_ANSWERED, b"yes\n")
    assert len(handler.requests) == 8


def test_a_question_waiting_for_the_user_does_not_stop_the_pipe(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    gate = threading.Event()
    handler.gate = gate
    waiting = threading.Thread(target=call, args=(name,), daemon=True)
    waiting.start()
    assert handler.entered.wait(WAIT)
    handler.gate = None  # the next call does not wait
    assert call(name, text="second: ") == (askpass.EXIT_ANSWERED, b"yes\n")  # served meanwhile
    assert waiting.is_alive()  # the first one still waits for the user
    gate.set()
    waiting.join(WAIT)
    assert not waiting.is_alive()


def test_an_answer_the_program_no_longer_waits_for_is_reported_lost(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, handler, _ = served
    handler.gate = threading.Event()
    pipe = askpass.open_pipe(name)
    pipe.write(line(token=TOKEN, event="ask", text="password: "))
    assert handler.entered.wait(WAIT)
    pipe.close()  # the program gave up
    handler.gate.set()
    deadline = threading.Event()
    for _ in range(100):
        if handler.lost:
            break
        deadline.wait(0.05)
    assert handler.lost == [AskpassRequest("ask", "password: ")]


def test_what_a_request_says_is_never_logged(
    served: tuple[str, Handler, AskpassServer], caplog: pytest.LogCaptureFixture
) -> None:
    name, _, _ = served
    caplog.set_level(logging.DEBUG)
    call(name, text="Enter passphrase for key 'hunter2-private': ")
    assert "hunter2" not in caplog.text
    assert "passphrase" not in caplog.text


# The doors of the pipe ---------------------------------------------------------------------


def test_the_descriptor_gives_everything_to_the_current_user_and_to_nobody_else() -> None:
    sid = current_user_sid()
    assert sid.startswith("S-1-")
    assert security_descriptor_text(sid) == f"D:P(A;;GA;;;{sid})"


def test_the_name_cannot_be_taken_twice() -> None:
    name = pipe_name()
    first = AskpassServer(name, TOKEN, Handler(REFUSED))
    first.start()
    try:
        with pytest.raises(NamedPipeError):
            AskpassServer(name, TOKEN, Handler(REFUSED)).start()
    finally:
        first.close()


def test_a_user_the_descriptor_does_not_name_cannot_open_the_pipe() -> None:
    """The descriptor is applied: here it names only the system account, not the test user."""
    name = pipe_name()
    server = AskpassServer(name, TOKEN, Handler(REFUSED), security_descriptor="D:P(A;;GA;;;SY)")
    server.start()
    try:
        with pytest.raises(PermissionError):
            askpass.open_pipe(name)
    finally:
        # Nobody can open the pipe to wake the thread that waits for a client, so it stays
        # blocked until the end of the tests (a daemon): this descriptor does not exist outside
        # this test, the real one always names the current user.
        server.close()


def test_a_name_that_is_not_a_pipe_is_refused() -> None:
    handler: AskpassHandler = Handler(REFUSED)
    with pytest.raises(NamedPipeError):
        AskpassServer(r"C:\temp\x", TOKEN, handler)


# The end -----------------------------------------------------------------------------------


def test_the_pipe_goes_away_when_the_server_is_closed(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, _, server = served
    assert call(name)[0] == askpass.EXIT_ANSWERED
    server.close()
    for _ in range(100):  # the thread that waited for a client ends
        if call(name)[0] == askpass.EXIT_UNREACHABLE:
            break
        threading.Event().wait(0.05)
    assert call(name)[0] == askpass.EXIT_UNREACHABLE


def test_a_call_that_never_writes_does_not_hold_the_close(
    served: tuple[str, Handler, AskpassServer],
) -> None:
    name, _, server = served
    silent = askpass.open_pipe(name)  # connected, and says nothing
    try:
        finished = threading.Event()

        def close_server() -> None:
            server.close()
            finished.set()

        threading.Thread(target=close_server, daemon=True).start()
        assert finished.wait(WAIT)
    finally:
        silent.close()
