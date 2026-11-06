"""A block of several lines: one entry of the history, one write."""

import pytest

from fakes.session_support import Session, end_program, run_program, start_shell
from n5terminal.core.session.session_state import CommandId, Interpreter

pytestmark = pytest.mark.unit

BLOCK = "foreach ($i in 1..3) {\n  $i\n}\nGet-Date"


def test_a_block_sent_to_a_terminal_program_is_written_in_one_go_with_carriage_returns(
    terminal: Session,
) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit("a\nb\nc")
    assert terminal.transport.written == [b"a\rb\rc\r"]


def test_a_block_sent_to_a_program_served_with_pipes_uses_line_feeds(session: Session) -> None:
    run_program(session, "python")
    session.presenter.submit("a\nb")
    assert session.transport.written == [b"a\nb\n"]


def test_windows_line_breaks_and_empty_lines_at_the_end_are_dropped(terminal: Session) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit("a\r\nb\r\n\r\n")
    assert terminal.transport.written == [b"a\rb\r"]


def test_a_block_for_powershell_ends_with_an_empty_line(terminal: Session) -> None:
    assert terminal.presenter.set_interpreter(Interpreter.POWERSHELL)
    terminal.presenter.submit(BLOCK)
    terminal.presenter.tick()
    terminal.presenter.submit("Get-Item .")  # a single line: nothing added
    assert terminal.transport.written[-1] == b"Get-Item .\r"
    terminal.presenter.submit(BLOCK)
    expected = BLOCK.replace("\n", "\r").encode() + b"\r\r"
    assert terminal.transport.written[-1] == expected


def test_a_block_for_cmd_has_no_empty_line_added(terminal: Session) -> None:
    start_shell(terminal, "echo one")
    terminal.presenter.submit("echo a\necho b")
    assert terminal.transport.written[-1] == b"echo a\recho b\r"


def test_a_block_that_starts_a_shell_is_sent_once_it_is_connected(terminal: Session) -> None:
    assert terminal.presenter.set_interpreter(Interpreter.CMD)
    terminal.presenter.submit("echo a\necho b")
    terminal.presenter.tick()
    assert terminal.transport.written == [b"echo a\recho b\r"]


def test_a_block_is_one_entry_of_the_history_with_its_line_breaks(terminal: Session) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit("a\nb\nc")
    assert terminal.presenter.history_items() == ("python", "a\nb\nc")


def test_the_list_reads_a_block_as_its_first_line_and_its_number_of_lines(
    terminal: Session,
) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit(BLOCK)
    entries, selected = terminal.presenter.command_list()
    assert entries[selected].label == "foreach ($i in 1..3) { (4 lines)"
    assert entries[selected].text == BLOCK


def test_sending_again_sends_the_whole_block(terminal: Session) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit("a\nb")
    assert terminal.presenter.run_command(CommandId.RESEND)
    assert terminal.transport.written == [b"a\rb\r", b"a\rb\r"]


def test_a_block_of_a_launched_program_is_one_launch_line_in_the_history(session: Session) -> None:
    session.presenter.submit('echo "a\nb"')
    session.presenter.tick()
    end_program(session)
    entries, selected = session.presenter.command_list()
    assert entries[selected].text == 'echo "a\nb"'
    assert entries[selected].label == 'echo "a (2 lines)'
