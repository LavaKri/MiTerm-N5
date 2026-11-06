"""A message the user ticked "Mask the message" for: a secret, which is sent and then forgotten."""

import logging

import pytest

from fakes.session_support import Session, end_program, run_program, start_shell
from n5terminal.core.session.session_state import CommandId, Phase

pytestmark = pytest.mark.unit

SECRET = "hunter2-p4ss"


def test_a_hidden_message_is_sent_like_any_other(terminal: Session, session: Session) -> None:
    run_program(session)
    session.presenter.submit(SECRET, hidden=True)
    assert session.transport.written == [f"{SECRET}\n".encode()]  # pipes: a line feed
    run_program(terminal, "ssh host")
    terminal.presenter.submit(SECRET, hidden=True)
    assert terminal.transport.written == [f"{SECRET}\r".encode()]  # terminal: a carriage return


def test_a_hidden_message_is_not_written_in_the_output_of_a_program_served_with_pipes(
    session: Session,
) -> None:
    run_program(session)
    session.presenter.submit(SECRET, hidden=True)
    session.presenter.tick()
    lines = session.view.fixed_lines()
    assert lines[-1] == "> (hidden message)"
    assert not any(SECRET in line for line in lines)


def test_a_message_that_is_not_hidden_is_still_written(session: Session) -> None:
    run_program(session)
    session.presenter.submit("answer", hidden=False)
    session.presenter.tick()
    assert session.view.fixed_lines()[-1] == "> answer"


def test_a_hidden_message_typed_into_a_shell_never_enters_the_history(terminal: Session) -> None:
    start_shell(terminal)
    terminal.presenter.submit("cd ..")
    terminal.presenter.submit(SECRET, hidden=True)
    assert terminal.presenter.history_items() == ("dir", "cd ..")


def test_a_hidden_message_is_not_what_is_sent_again(terminal: Session) -> None:
    start_shell(terminal)
    terminal.presenter.submit(SECRET, hidden=True)
    end_program(terminal)
    assert terminal.presenter.run_command(CommandId.RESEND)
    assert terminal.transport.written == [b"dir\r"]  # the line typed before, not the secret


def test_a_hidden_message_never_reaches_the_log_nor_an_announcement(
    terminal: Session, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    run_program(terminal, "ssh host")
    terminal.presenter.submit(SECRET, hidden=True)
    terminal.presenter.tick()
    assert SECRET not in caplog.text
    assert not any(SECRET in message for message in terminal.sink.messages)


def test_a_hidden_message_that_cannot_be_sent_is_not_written_either(session: Session) -> None:
    run_program(session)
    session.transport.state = session.transport.state.CLOSED  # closed, the presenter not told yet
    session.presenter.submit(SECRET, hidden=True)
    session.presenter.tick()
    assert not any(SECRET in line for line in session.view.fixed_lines())
    assert "> (hidden message)" not in session.view.fixed_lines()  # nothing was sent


def test_hiding_means_nothing_when_a_command_is_typed(session: Session) -> None:
    """The box is greyed then; if it were set, the command is launched as any command."""
    assert session.presenter.state.phase is Phase.IDLE
    session.presenter.submit("ping host", hidden=True)
    session.presenter.tick()
    assert session.launcher.calls[0].arguments == ("ping", "host")
    assert session.view.fixed_lines()[0] == "# ping host"
