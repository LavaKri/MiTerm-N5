import pytest

from fakes.fake_view import FakeView
from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.settings import Settings
from n5terminal.core.screen.screen_model import FixedLine, ScreenUpdate
from n5terminal.presenters.output_flow import OutputFlow

pytestmark = pytest.mark.unit


def update(*lines: str) -> ScreenUpdate:
    return ScreenUpdate(
        fixed=tuple(FixedLine(line) for line in lines),
        rows=(),
        replace_all=False,
        overflows=(),
        columns=0,
        row_count=1,
        cursor_row=0,
        cursor_column=0,
    )


class Flow:
    def __init__(self) -> None:
        self.view = FakeView()
        self.said: list[tuple[Announce, dict[str, object]]] = []
        self.flow = OutputFlow(self.view, Settings(output_limit=2_000), self.say)

    def say(self, announce: Announce, **values: object) -> None:
        self.said.append((announce, values))


def test_nothing_published_gives_nothing() -> None:
    flow = Flow()
    assert flow.flow.show() is None
    assert flow.view.outputs == []


def test_what_is_published_is_given_to_the_window_once() -> None:
    flow = Flow()
    flow.flow.exchange.publish(update("one", "two"))
    shown = flow.flow.show()
    assert shown is not None
    assert flow.view.fixed_lines() == ["one", "two"]
    assert flow.flow.show() is None


def test_an_echo_is_written_as_fixed_lines_with_its_prefix_and_details() -> None:
    flow = Flow()
    flow.flow.echo("ping host", "# ", "From C:\\work\\")
    flow.flow.show()
    assert flow.view.fixed_lines() == ["# ping host", "From C:\\work\\"]


def test_an_echo_tells_how_many_lines_it_writes() -> None:
    flow = Flow()
    assert flow.flow.echo("answer", "> ") == 1
    assert flow.flow.echo("ping host", "# ", "From C:\\work\\") == 2


def test_clearing_forgets_what_was_not_shown_yet() -> None:
    flow = Flow()
    flow.flow.exchange.publish(update("late"))
    flow.flow.clear()
    assert flow.view.cleared_outputs == 1
    assert flow.flow.show() is None


def test_lost_lines_are_said_each_time() -> None:
    flow = Flow()
    flow.flow.exchange.publish(update(*(f"line {i}" for i in range(11_000))))
    flow.flow.show()
    assert flow.said == [(Announce.LINES_LOST, {"count": 1_000})]


def test_the_limit_of_the_output_is_said_once_until_the_output_is_cleared() -> None:
    flow = Flow()
    flow.view.trimmed_lines = 5
    flow.flow.exchange.publish(update("a"))
    flow.flow.show()
    flow.flow.exchange.publish(update("b"))
    flow.flow.show()
    assert flow.said == [(Announce.LINES_DROPPED, {"limit": 2_000})]
    flow.flow.clear()
    flow.flow.exchange.publish(update("c"))
    flow.flow.show()
    assert len(flow.said) == 2
