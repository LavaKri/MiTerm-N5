"""The activity of the output: the flag, the interval, the beep or the line of an element."""

from pathlib import Path

import pytest

from fakes.session_support import Session, end_program, make_session, run_program
from n5terminal.core.config.announcements import ACTIVITY, Category, Destination
from n5terminal.core.session.session_state import Mode

pytestmark = pytest.mark.unit


def session_with(tmp_path: Path, destination: Destination | None = None) -> Session:
    def destination_of(category: Category) -> Destination:
        return destination if destination and category is ACTIVITY else category.default

    session = make_session(tmp_path, Mode.TERMINAL_LINE, destination_of=destination_of)
    run_program(session)
    session.sink.messages.clear()  # "Started: ping host."
    return session


def output_then(session: Session, text: bytes, at: float, line: str = "") -> None:
    """The program writes at ``at`` seconds; the caret is on ``line``; the window takes it."""
    session.now[0] = at
    session.view.caret = (line, False)
    session.transport.receive(text)
    session.presenter.tick()


@pytest.fixture
def idle(tmp_path: Path) -> Session:
    """A session whose program just started, with the default destination of the activity."""
    return session_with(tmp_path)


def test_a_change_is_signaled_by_a_beep_at_the_next_interval(idle: Session) -> None:
    output_then(idle, b"hello\r\n", 0.5, "hello")
    assert idle.beeper.count == 0  # not yet: the flag is looked at once per second
    idle.now[0] = 1.1
    idle.presenter.tick()
    assert idle.beeper.count == 1
    assert idle.sink.messages == []


def test_nothing_changed_nothing_is_signaled(idle: Session) -> None:
    for second in (1.1, 2.2, 3.3):
        idle.now[0] = second
        idle.presenter.tick()
    assert idle.beeper.count == 0


def test_an_element_on_the_line_of_the_caret_is_said_instead_of_the_beep(idle: Session) -> None:
    output_then(idle, b"x\r\n", 0.5, "Download  60%")
    idle.now[0] = 1.1
    idle.presenter.tick()
    assert idle.sink.messages == ["Download, 60 %"]
    assert idle.beeper.count == 0


def test_a_bar_that_stands_still_is_said_again_while_the_output_changes_elsewhere(
    idle: Session,
) -> None:
    for second in (0.5, 1.5, 2.5):
        output_then(idle, b"log\r\n", second, "Download  60%")
        idle.now[0] = second + 0.6
        idle.presenter.tick()
    assert idle.sink.messages == ["Download, 60 %"] * 3


def test_when_the_output_no_longer_changes_nothing_is_said(idle: Session) -> None:
    output_then(idle, b"x\r\n", 0.5, "Download  60%")
    for second in (1.1, 2.2, 3.3, 14.0):
        idle.now[0] = second
        idle.presenter.tick()
    assert idle.sink.messages == ["Download, 60 %"]  # said once, for the one change


def test_with_messages_only_a_plain_line_says_nothing(tmp_path: Path) -> None:
    session = session_with(tmp_path, Destination.ELEMENT)
    output_then(session, b"x\r\n", 0.5, "just text")
    session.now[0] = 1.1
    session.presenter.tick()
    assert session.beeper.count == 0
    assert session.sink.messages == []
    output_then(session, b"y\r\n", 1.5, "Download  80%")
    session.now[0] = 2.2
    session.presenter.tick()
    assert session.sink.messages == ["Download, 80 %"]


def test_with_no_announcement_nothing_is_signaled(tmp_path: Path) -> None:
    session = session_with(tmp_path, Destination.NONE)
    output_then(session, b"x\r\n", 0.5, "Download  60%")
    session.now[0] = 1.1
    session.presenter.tick()
    assert session.beeper.count == 0
    assert session.sink.messages == []


def test_outside_the_output_area_nothing_is_signaled_and_the_flag_is_lowered(idle: Session) -> None:
    idle.view.output_focused = False
    output_then(idle, b"x\r\n", 0.5, "plain")
    idle.now[0] = 1.1
    idle.presenter.tick()
    idle.view.output_focused = True
    idle.now[0] = 2.2
    idle.presenter.tick()
    assert idle.beeper.count == 0  # no beep waiting for the focus to come back


def test_anywhere_when_the_setting_is_off(idle: Session) -> None:
    idle.settings.activity_only_in_output = False
    idle.view.output_focused = False
    output_then(idle, b"x\r\n", 0.5, "plain")
    idle.now[0] = 1.1
    idle.presenter.tick()
    assert idle.beeper.count == 1


def test_the_interval_is_the_one_of_the_settings(idle: Session) -> None:
    idle.settings.activity_interval = 3
    output_then(idle, b"x\r\n", 0.5, "plain")
    idle.now[0] = 2.9
    idle.presenter.tick()
    assert idle.beeper.count == 0
    idle.now[0] = 3.0
    idle.presenter.tick()
    assert idle.beeper.count == 1


def test_the_echo_of_what_the_user_sent_is_no_activity(idle: Session) -> None:
    idle.now[0] = 0.9
    idle.presenter.submit("y")
    output_then(idle, b"y\r\n", 1.0, "plain")  # the program echoes right away
    idle.now[0] = 2.1
    idle.presenter.tick()
    assert idle.beeper.count == 0


def test_after_the_program_ended_nothing_is_signaled(idle: Session) -> None:
    output_then(idle, b"x\r\n", 0.5, "plain")
    end_program(idle)
    idle.now[0] = 2.0
    idle.presenter.tick()
    assert idle.beeper.count == 0


def test_the_mark_of_a_sent_line_is_no_selection_in_pipes_mode(tmp_path: Path) -> None:
    session = make_session(tmp_path, Mode.PIPES)
    run_program(session)
    output_then(session, b"x\n", 0.5, "> y")
    session.now[0] = 1.1
    session.presenter.tick()
    assert session.beeper.count == 1  # a plain line, so a beep: not "y, selected"
