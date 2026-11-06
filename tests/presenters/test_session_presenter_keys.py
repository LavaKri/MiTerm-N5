"""Sending a key to the program (menu or shortcut)."""

import pytest

from fakes.session_support import Session, end_program, run_program
from n5terminal.core.config.keys import SentKey, key_named
from n5terminal.core.errors import InputQueueFullError
from n5terminal.core.session.session_state import CommandId, command_states
from n5terminal.core.transport.transport import TransportState

pytestmark = pytest.mark.unit


def key(key_id: str) -> SentKey:
    found = key_named(key_id)
    assert found is not None
    return found


def test_a_key_goes_to_the_program_and_is_announced_once(terminal: Session) -> None:
    run_program(terminal)
    assert terminal.presenter.send_key(key("escape"))
    assert terminal.transport.written == [b"\x1b"]
    assert terminal.sink.messages[-1] == "Sends Escape."


def test_the_cursor_keys_follow_the_mode_the_program_asked_for(terminal: Session) -> None:
    run_program(terminal)
    terminal.presenter.send_key(key("up"))
    terminal.transport.receive(b"\x1b[?1h")  # the program asks for the application mode
    terminal.presenter.tick()
    terminal.presenter.send_key(key("up"))
    assert terminal.transport.written == [b"\x1b[A", b"\x1bOA"]


def test_nothing_is_sent_without_a_program(terminal: Session) -> None:
    assert not terminal.presenter.send_key(key("escape"))
    assert terminal.launcher.transports == []
    assert terminal.sink.messages[-1] == "No program is running."


def test_nothing_is_sent_to_a_program_served_with_pipes(session: Session) -> None:
    run_program(session)
    assert not session.presenter.send_key(key("tab"))
    assert session.transport.written == []
    assert session.sink.messages[-1] == "Only for programs that use a terminal."


def test_nothing_is_sent_once_the_program_has_ended(terminal: Session) -> None:
    run_program(terminal)
    end_program(terminal)
    assert not terminal.presenter.send_key(key("tab"))
    assert terminal.transport.written == []


def test_the_command_is_available_for_a_terminal_program_only(
    terminal: Session, session: Session
) -> None:
    assert CommandId.SEND_KEY not in command_states(terminal.presenter.state)
    run_program(terminal)
    assert CommandId.SEND_KEY in command_states(terminal.presenter.state)
    run_program(session)
    assert CommandId.SEND_KEY not in command_states(session.presenter.state)


def test_a_key_sent_puts_the_focus_in_the_output_without_the_caret(terminal: Session) -> None:
    run_program(terminal)
    terminal.presenter.send_key(key("tab"))
    assert terminal.view.focus_calls == ["command:0", "output"]


def test_a_key_the_program_does_not_read_is_announced_and_leaves_the_focus(
    terminal: Session,
) -> None:
    run_program(terminal)

    def refuse(data: bytes) -> None:
        raise InputQueueFullError

    terminal.transport.write = refuse  # type: ignore[method-assign]
    assert not terminal.presenter.send_key(key("tab"))
    assert terminal.sink.messages[-1] == "Nothing sent: the program does not read its input."
    assert terminal.view.focus_calls == ["command:0"]


def test_a_key_sent_to_a_closed_transport_is_announced_and_leaves_the_focus(
    terminal: Session,
) -> None:
    run_program(terminal)
    terminal.transport.state = TransportState.CLOSED  # closed, the presenter not told yet
    assert not terminal.presenter.send_key(key("tab"))
    assert terminal.sink.messages[-1] == (
        "Nothing sent: the program has ended and only a process it started is still running."
    )
    assert terminal.view.focus_calls == ["command:0"]


def test_a_key_refused_leaves_the_focus_where_it_was(session: Session) -> None:
    run_program(session)
    session.presenter.send_key(key("tab"))
    assert session.view.focus_calls == ["command:2"]
