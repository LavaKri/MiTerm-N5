"""The user is told when lines of the output are dropped (see "Robustness" in the specs)."""

import pytest

from fakes.session_support import Session, run_program
from n5terminal.core.screen.display_exchange import DEFAULT_MAX_FIXED_LINES
from n5terminal.core.session.session_state import CommandId

pytestmark = pytest.mark.unit


def test_the_limit_of_the_output_is_said_once(session: Session) -> None:
    run_program(session)
    session.view.trimmed_lines = 3
    session.transport.receive(b"a\n")
    session.presenter.tick()
    session.transport.receive(b"b\n")
    session.presenter.tick()
    limit = session.settings.output_limit
    said = f"The output keeps only the last {limit} lines: the oldest are dropped."
    assert session.sink.messages.count(said) == 1


def test_no_message_while_the_limit_is_not_reached(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"a\n")
    session.presenter.tick()
    assert not any("oldest" in message for message in session.sink.messages)


def test_the_limit_is_said_again_after_the_output_is_cleared(session: Session) -> None:
    run_program(session)
    session.view.trimmed_lines = 1
    for _ in range(2):
        session.transport.receive(b"a\n")
        session.presenter.tick()
        assert session.presenter.run_command(CommandId.CLEAR)
    assert sum("oldest" in message for message in session.sink.messages) == 2


def test_lines_lost_because_the_window_was_late_are_counted(session: Session) -> None:
    run_program(session)
    flood = b"x\n" * (DEFAULT_MAX_FIXED_LINES + 5)
    session.transport.receive(flood)
    session.presenter.tick()
    assert session.sink.messages[-1] == (
        "5 lines of output were lost: they arrived faster than the window could show."
    )
