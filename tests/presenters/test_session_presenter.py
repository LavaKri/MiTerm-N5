import os

import pytest

from fakes.fake_transport import FakeTransport
from fakes.session_support import Session, end_program, run_program
from n5terminal.core.errors import (
    InputQueueFullError,
    LaunchError,
    ProgramNotFoundError,
    TransportError,
    WorkingFolderError,
)
from n5terminal.core.screen.terminal_size import DEFAULT_SIZE
from n5terminal.core.session.session_state import CommandId, LaunchMode, Mode, Phase
from n5terminal.core.transport.transport import Stream, TransportListener, TransportState
from n5terminal.presenters.session_run import CHILD_GRACE
from n5terminal.presenters.session_view import InputMode

pytestmark = pytest.mark.unit


def from_line(session: Session) -> str:
    """The line under the title of a launched command."""
    return f"From {session.folder}{os.sep}"


# The start -------------------------------------------------------------------------------------


def test_a_new_session_is_idle_and_ready(session: Session) -> None:
    assert session.presenter.state.phase is Phase.IDLE
    assert session.view.input_modes == [InputMode.COMMAND]
    assert session.view.last_state == "Ready"
    enabled = session.view.last_enabled
    assert CommandId.CHOOSE_FOLDER in enabled
    assert CommandId.STOP not in enabled
    assert CommandId.EXPORT not in enabled


def test_an_empty_line_is_ignored_when_no_program_runs(session: Session) -> None:
    session.presenter.submit("   ")
    assert session.launcher.calls == []


# Launching -------------------------------------------------------------------------------------


def test_a_command_is_split_and_launched_in_the_working_folder(session: Session) -> None:
    session.presenter.submit('ping -n 1 "my host"')
    call = session.launcher.calls[0]
    assert call.arguments == ("ping", "-n", "1", "my host")
    assert call.folder == session.folder
    assert call.size == DEFAULT_SIZE
    assert call.launch_mode is LaunchMode.CLI


def test_launching_changes_the_state_the_field_and_the_status(session: Session) -> None:
    session.presenter.submit("ping host")
    state = session.presenter.state
    assert (state.phase, state.mode) == (Phase.RUNNING, Mode.PIPES)
    assert session.view.input_modes[-1] is InputMode.PROGRAM_INPUT
    assert session.view.last_state == "Running: ping"
    assert session.view.cleared_inputs == 1
    assert session.sink.messages == ["Started: ping."]
    assert CommandId.STOP in session.view.last_enabled
    assert CommandId.CHOOSE_FOLDER not in session.view.last_enabled


def test_the_program_is_named_without_its_folder(session: Session) -> None:
    session.presenter.submit(r"C:\tools\prog.exe --x")
    assert session.view.last_state == "Running: prog.exe"


def test_the_typed_command_is_echoed_before_the_output_for_pipes(session: Session) -> None:
    run_program(session, "ping host")
    session.transport.receive(b"reply\n")
    session.presenter.tick()
    assert session.view.fixed_lines() == ["# ping host", from_line(session), "reply"]


def test_the_echo_comes_before_the_output_that_arrives_while_the_program_starts(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = FakeTransport.start

    def start_and_reply(transport: FakeTransport, listener: TransportListener) -> None:
        start(transport, listener)
        transport.receive(b"reply\n")  # the program writes at once, on its own thread

    monkeypatch.setattr(FakeTransport, "start", start_and_reply)
    session.presenter.submit("ping host")
    session.presenter.tick()
    assert session.view.fixed_lines() == ["# ping host", from_line(session), "reply"]


def test_a_given_title_replaces_the_command_in_the_echo_only(session: Session) -> None:
    session.presenter.submit('"C:\\py\\python.exe" "C:\\t\\Progress.py"', "Progress.py")
    assert session.view.fixed_lines()[0] == "# Progress.py"
    assert session.presenter.history_items()[-1] == '"C:\\py\\python.exe" "C:\\t\\Progress.py"'


def test_a_launched_command_tells_the_folder_it_runs_in(session: Session) -> None:
    run_program(session, "git --version")
    assert from_line(session) == f"From {session.folder}{os.sep}"
    assert session.view.fixed_lines()[:2] == ["# git --version", from_line(session)]


def test_text_sent_to_a_running_program_does_not_tell_the_folder(session: Session) -> None:
    run_program(session)
    session.presenter.submit("answer")
    session.presenter.tick()
    assert session.view.fixed_lines().count(from_line(session)) == 1


def test_a_terminal_program_has_no_echo_of_its_command(terminal: Session) -> None:
    run_program(terminal)
    assert from_line(terminal) not in terminal.view.fixed_lines()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (ProgramNotFoundError("nosuch"), "Program not found: nosuch."),
        (WorkingFolderError("nosuch", "x"), None),
        (LaunchError("nosuch"), "nosuch could not be started."),
        (TransportError("unexpected"), "nosuch could not be started."),
    ],
)
def test_a_launch_that_fails_is_announced_and_leaves_the_session_idle(
    session: Session, error: TransportError, message: str | None
) -> None:
    session.launcher.start_error = error
    session.presenter.submit("nosuch")
    assert session.presenter.state.phase is Phase.IDLE
    assert session.presenter.running_program is None
    assert session.view.input_modes[-1] is InputMode.COMMAND
    assert session.sink.messages
    if message is not None:
        assert session.sink.messages == [message]


def test_a_command_can_be_launched_after_a_launch_that_failed(session: Session) -> None:
    session.launcher.start_error = TransportError("unexpected")
    session.presenter.submit("nosuch")
    session.launcher.start_error = None
    session.presenter.submit("ping host")
    assert session.presenter.state.phase is Phase.RUNNING
    assert session.presenter.running_program == "ping"


# Output ----------------------------------------------------------------------------------------


def test_output_is_given_to_the_window_at_each_tick(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"one\ntwo\nthr")
    assert session.view.fixed_lines() == ["# ping host", from_line(session)]
    session.presenter.tick()
    assert session.view.fixed_lines() == ["# ping host", from_line(session), "one", "two"]
    assert session.view.live_rows() == {0: "thr"}


def test_a_tick_without_news_gives_nothing(session: Session) -> None:
    run_program(session)
    count = len(session.view.outputs)
    session.presenter.tick()
    assert len(session.view.outputs) == count


def test_standard_error_comes_in_the_same_output(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"out\n")
    session.transport.receive(b"err\n", Stream.ERROR)
    session.presenter.tick()
    assert session.view.fixed_lines()[2:] == ["out", "StdErr: err"]


def test_the_commands_on_the_output_wait_for_some_output(session: Session) -> None:
    assert CommandId.CLEAR not in session.view.last_enabled
    run_program(session)
    assert CommandId.CLEAR in session.view.last_enabled  # the echo is output


def test_the_terminal_shows_its_rows_as_the_live_part(terminal: Session) -> None:
    run_program(terminal, "python")
    terminal.transport.receive(b">>> ")
    terminal.presenter.tick()
    assert terminal.view.live_rows()[0] == ">>>"
    assert terminal.view.fixed_lines() == []  # no echo with a terminal


# Sending to the program ------------------------------------------------------------------------


def test_text_is_sent_with_a_line_feed_for_pipes_and_echoed(session: Session) -> None:
    run_program(session)
    session.presenter.submit("answer")
    session.presenter.tick()
    assert session.transport.written == [b"answer\n"]
    assert session.view.fixed_lines() == ["# ping host", from_line(session), "> answer"]
    assert session.view.cleared_inputs == 2


def test_an_empty_line_is_sent_when_a_program_runs(session: Session) -> None:
    run_program(session)
    session.presenter.submit("")
    assert session.transport.written == [b"\n"]


def test_text_is_sent_with_a_carriage_return_for_a_terminal_and_not_echoed(
    terminal: Session,
) -> None:
    run_program(terminal, "python")
    terminal.presenter.submit("1 + 1")
    terminal.presenter.tick()
    assert terminal.transport.written == [b"1 + 1\r"]
    assert terminal.view.fixed_lines() == []


def test_unicode_text_is_sent_as_utf8(session: Session) -> None:
    run_program(session)
    session.presenter.submit("caf\u00e9")
    assert session.transport.written == ["caf\u00e9\n".encode()]


def test_a_program_that_does_not_read_is_announced(session: Session) -> None:
    run_program(session)

    def refuse(data: bytes) -> None:
        raise InputQueueFullError

    session.transport.write = refuse  # type: ignore[method-assign]
    session.presenter.submit("x")
    assert session.sink.messages[-1] == "Nothing sent: the program does not read its input."


def test_text_sent_to_a_closed_transport_is_announced(session: Session) -> None:
    run_program(session)
    session.transport.state = TransportState.CLOSED  # closed, the presenter not told yet
    session.presenter.submit("x")
    assert session.sink.messages[-1] == (
        "Nothing sent: the program has ended and only a process it started is still running."
    )


# History ---------------------------------------------------------------------------------------


def test_launched_commands_are_kept_in_order(session: Session) -> None:
    run_program(session, "first")
    end_program(session)
    run_program(session, "second")
    end_program(session)
    presenter = session.presenter
    assert presenter.history_items() == ("first", "second")


def test_lines_typed_to_a_running_terminal_program_are_kept_for_resending(
    terminal: Session,
) -> None:
    run_program(terminal, "ssh host")
    terminal.presenter.submit("a line")
    assert terminal.presenter.history_items() == ("ssh host", "a line")


def test_lines_typed_to_a_program_served_with_pipes_are_kept_for_resending(
    session: Session,
) -> None:
    run_program(session, "ping host")
    session.presenter.submit("a line")
    assert session.presenter.history_items() == ("ping host", "a line")


def test_the_lines_of_a_running_program_do_not_come_back_as_launch_lines(session: Session) -> None:
    run_program(session, "ping host")
    session.presenter.submit("a line")
    end_program(session)
    entries, _selected = session.presenter.command_list()
    assert [entry.text for entry in entries] == ["ping host"]


# The end of a program --------------------------------------------------------------------------


def test_the_end_of_a_program_is_announced_with_its_code(session: Session) -> None:
    run_program(session)
    end_program(session, 3)
    assert session.sink.messages[-1] == "ping ended with the code 3."
    assert session.presenter.state.phase is Phase.IDLE
    assert session.view.last_state == "Ended (code 3)"
    assert session.view.input_modes[-1] is InputMode.COMMAND
    assert CommandId.STOP not in session.view.last_enabled


def test_the_output_is_kept_and_a_new_program_can_run(session: Session) -> None:
    run_program(session, "first")
    session.transport.receive(b"kept\n")
    end_program(session)
    run_program(session, "second")
    assert "kept" in session.view.fixed_lines()
    assert len(session.launcher.calls) == 2


def test_the_last_unfinished_line_stays_when_the_output_ends(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"no line end")
    end_program(session)
    assert session.view.live_rows() == {0: "no line end"}


def test_what_the_decoder_held_back_is_released_when_the_output_ends(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"ab\xc3")  # may be the start of a UTF-8 character
    session.presenter.tick()
    assert session.view.live_rows() == {0: "ab"}
    end_program(session)
    assert session.view.live_rows() == {0: "ab├"}  # it was not: cp850 reads it as a box


def test_an_exit_without_a_code_is_announced(session: Session) -> None:
    run_program(session)
    end_program(session, None)  # type: ignore[arg-type]
    assert session.sink.messages[-1] == "ping ended."
    assert session.view.last_state == "Ended"


def test_a_process_left_running_is_announced_after_a_short_wait(session: Session) -> None:
    run_program(session)
    listener = session.transport.listener
    assert listener is not None
    listener.on_exit(0)  # the program ended, the transport is not closed: output may come
    assert session.presenter.state.phase is Phase.CHILD_ACTIVE
    session.presenter.tick()
    assert session.view.last_state == "Running: ping"  # not announced yet
    session.now[0] += CHILD_GRACE
    session.presenter.tick()
    assert session.sink.messages[-1] == "A process started by the program is still running."
    assert session.view.last_state == "Child process active"


def test_sending_while_only_a_child_runs_is_refused(session: Session) -> None:
    run_program(session)
    listener = session.transport.listener
    assert listener is not None
    listener.on_exit(0)
    session.presenter.submit("text")
    assert session.sink.messages[-1].startswith("Nothing sent: the program has ended")
    assert session.transport.written == []


def test_a_normal_end_does_not_announce_a_child(session: Session) -> None:
    run_program(session)
    end_program(session)
    session.now[0] += 10
    session.presenter.tick()
    assert "A process started by the program is still running." not in session.sink.messages


def test_events_of_a_run_that_is_over_are_ignored(session: Session) -> None:
    run_program(session)
    listener = session.transport.listener
    assert listener is not None
    end_program(session)
    run_program(session, "second")
    listener.on_exit(5)
    listener.on_state_changed(TransportState.CLOSED)
    assert session.presenter.state.phase is Phase.RUNNING


# Commands --------------------------------------------------------------------------------------


def test_stop_closes_the_transport_and_is_announced(session: Session) -> None:
    run_program(session)
    assert session.presenter.run_command(CommandId.STOP)
    assert session.transport.closed
    assert session.sink.messages[-1] == "Program stopped."


def test_a_refused_command_says_why(session: Session) -> None:
    assert not session.presenter.run_command(CommandId.STOP)
    assert session.sink.messages == ["No program is running."]
    assert not session.presenter.run_command(CommandId.RESEND)
    assert session.sink.messages[-1] == "There is no command to resend."


def test_clear_empties_the_output_and_what_waits(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"stale\n")
    assert session.presenter.run_command(CommandId.CLEAR)
    session.presenter.tick()
    assert session.view.cleared_outputs == 1
    assert "stale" not in session.view.fixed_lines()
    assert CommandId.CLEAR not in session.view.last_enabled


def test_resend_launches_the_last_line_again(session: Session) -> None:
    run_program(session, "ping host")
    end_program(session)
    assert session.presenter.run_command(CommandId.RESEND)
    assert [call.arguments for call in session.launcher.calls] == [("ping", "host")] * 2


def test_resend_sends_the_last_message_to_the_program_that_runs(session: Session) -> None:
    run_program(session, "python")
    assert CommandId.RESEND not in session.view.last_enabled  # nothing was sent to it yet
    session.presenter.submit("1")
    session.presenter.submit("2")
    assert CommandId.RESEND in session.view.last_enabled
    assert session.presenter.run_command(CommandId.RESEND)
    assert session.transport.written[-2:] == [b"2\n", b"2\n"]


def test_resend_does_as_ctrl_space_then_enter_on_the_selected_line(session: Session) -> None:
    run_program(session, "ping a")
    end_program(session)
    run_program(session, "ping b")
    end_program(session)
    entries, selected = session.presenter.command_list()
    assert entries[selected].text == "ping b"
    assert session.presenter.run_command(CommandId.RESEND)
    assert [call.arguments for call in session.launcher.calls][-1] == ("ping", "b")


# Where the focus goes after a command is sent ---------------------------------------------------


def test_launching_a_program_puts_the_focus_on_its_command_line(session: Session) -> None:
    run_program(session)
    assert session.view.focus_calls == ["command:2"]  # the title and the folder line


def test_launching_a_terminal_program_puts_the_focus_at_the_start_of_the_live_part(
    terminal: Session,
) -> None:
    run_program(terminal)
    assert terminal.view.focus_calls == ["command:0"]


def test_a_failed_launch_leaves_the_focus_where_it_was(session: Session) -> None:
    session.launcher.start_error = ProgramNotFoundError("nothing")
    session.presenter.submit("nothing")
    assert session.view.focus_calls == []


def test_text_sent_to_a_program_puts_the_focus_in_the_output_without_the_caret(
    session: Session,
) -> None:
    run_program(session)
    session.presenter.submit("answer")
    assert session.view.focus_calls == ["command:2", "output"]


def test_a_refused_text_leaves_the_focus_where_it_was(session: Session) -> None:
    run_program(session)

    def refuse(data: bytes) -> None:
        raise InputQueueFullError

    session.transport.write = refuse  # type: ignore[method-assign]
    session.presenter.submit("answer")
    assert session.view.focus_calls == ["command:2"]
