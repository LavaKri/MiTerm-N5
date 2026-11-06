"""A shell that stays open: when does the session count it as waiting at its prompt?

The rule is in ``core/session/shell_prompt.py`` (two signals that must agree); here is how the
presenter follows the screen and the number of processes, and what it does with the answer.
"""

import pytest

from fakes.session_support import Session, show_prompt, start_shell
from n5terminal.core.session.session_state import CommandId

pytestmark = pytest.mark.unit


def can_change_folder(session: Session) -> bool:
    return CommandId.CHOOSE_FOLDER in session.view.last_enabled


def test_a_shell_that_shows_its_prompt_is_waiting(terminal: Session) -> None:
    start_shell(terminal, "")
    assert not terminal.presenter.state.shell_at_prompt  # nothing shown yet
    show_prompt(terminal)
    assert terminal.presenter.state.shell_at_prompt
    assert can_change_folder(terminal)


def test_a_line_sent_makes_the_shell_busy_at_once_although_the_old_prompt_is_still_shown(
    terminal: Session,
) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.presenter.submit("dir")
    assert not terminal.presenter.state.shell_at_prompt
    terminal.presenter.tick()  # nothing new was shown yet
    assert not terminal.presenter.state.shell_at_prompt
    assert not can_change_folder(terminal)


def test_the_shell_is_waiting_again_when_it_shows_its_prompt_again(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.presenter.submit("dir")
    show_prompt(terminal, b"dir\r\nfile.txt\r\nC:\\work>")
    assert terminal.presenter.state.shell_at_prompt


def test_a_program_running_in_the_shell_makes_it_busy(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.presenter.submit("ping host")
    terminal.transport.process_count = 2
    show_prompt(terminal, b"ping host\r\nC:\\work>")  # the old prompt text may still be around
    assert not terminal.presenter.state.shell_at_prompt


def test_the_end_of_the_program_is_noticed_without_new_output(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.presenter.submit("ping host")
    terminal.transport.process_count = 2
    show_prompt(terminal, b"ping host\r\nC:\\work>")
    terminal.transport.process_count = 1
    terminal.presenter.tick()
    assert terminal.presenter.state.shell_at_prompt


def test_a_built_in_command_waiting_for_a_line_is_not_a_prompt(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.presenter.submit("set /p NAME=Name:")
    show_prompt(terminal, b"set /p NAME=Name:\r\nName:")  # no process, but not a prompt either
    assert not terminal.presenter.state.shell_at_prompt


def test_an_unknown_number_of_processes_counts_as_busy(terminal: Session) -> None:
    start_shell(terminal, "")
    terminal.transport.process_count = None
    show_prompt(terminal)
    assert not terminal.presenter.state.shell_at_prompt


def test_a_program_launched_directly_is_never_a_shell_at_its_prompt(terminal: Session) -> None:
    terminal.presenter.submit("python")
    show_prompt(terminal, b"C:\\work>")
    assert not terminal.presenter.state.shell_at_prompt


def test_a_new_shell_starts_busy(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal)
    terminal.transport.exit(0)
    terminal.presenter.tick()
    assert not terminal.presenter.state.shell_at_prompt
    terminal.presenter.submit("")
    assert not terminal.presenter.state.shell_at_prompt


def test_a_prompt_wrapped_over_two_rows_is_still_a_prompt(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal, b"C:\\" + b"deep\\" * 20 + b">")  # 105 characters on 80 columns
    assert terminal.presenter.state.shell_at_prompt


def test_a_wrapped_line_that_is_not_a_prompt_stays_busy(terminal: Session) -> None:
    start_shell(terminal, "")
    show_prompt(terminal, b"C:\\" + b"deep\\" * 20 + b"?")
    assert not terminal.presenter.state.shell_at_prompt
