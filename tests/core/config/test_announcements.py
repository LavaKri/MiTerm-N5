import pytest

from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import (
    ACTIVITY,
    CATEGORIES,
    FOLDER,
    LAUNCH_FAILED,
    LINE_READING,
    MOVEMENT_BLOCKED,
    PROGRAM,
    SEARCH_FAILED,
    Announce,
    AnnouncementCenter,
    Category,
    Destination,
    NullMessageSink,
)
from n5terminal.core.config.screen_reader import (
    NONE,
    UIA,
    available_outputs,
    default_output,
    output_named,
)
from n5terminal.core.errors import ScreenReaderOutputError

pytestmark = pytest.mark.unit


class _FailingSink:
    def show(self, text: str) -> None:
        raise ScreenReaderOutputError("broken")

    def close(self) -> None:
        pass


def _center(
    destinations: dict[Category, Destination] | None = None,
) -> tuple[AnnouncementCenter, RecordingMessageSink]:
    sink = RecordingMessageSink()
    chosen = destinations or {}
    center = AnnouncementCenter(sink, lambda category: chosen.get(category, category.default))
    return center, sink


def test_notify_fills_the_text_and_sends_it() -> None:
    center, sink = _center()
    assert center.notify(Announce.PROGRAM_ENDED, program="ping", code=0) == (
        "ping ended with the code 0."
    )
    assert sink.messages == ["ping ended with the code 0."]


def test_a_fixed_announcement_is_always_a_message() -> None:
    center, sink = _center()
    center.notify(Announce.UNAVAILABLE_PROGRAM_RUNNING)
    assert sink.messages == ["Not available while a program is running."]


def test_none_says_nothing() -> None:
    center, sink = _center({PROGRAM: Destination.NONE})
    assert center.notify(Announce.PROGRAM_STOPPED) is None
    assert sink.messages == []


def test_the_dialog_destination_shows_the_text_in_a_dialog_and_nowhere_else() -> None:
    shown: list[str] = []
    sink = RecordingMessageSink()
    center = AnnouncementCenter(
        sink,
        lambda category: Destination.DIALOG if category is SEARCH_FAILED else category.default,
        show_dialog=shown.append,
    )
    assert center.notify(Announce.SEARCH_NO_NEXT, term="x") is None
    assert shown == ['No next occurrence of "x".']
    assert sink.messages == []


def test_a_destination_the_category_does_not_accept_gives_the_default() -> None:
    center, _sink = _center({PROGRAM: Destination.DIALOG})
    assert center.destination(Announce.PROGRAM_STOPPED) is PROGRAM.default


def test_the_defaults_are_accepted_and_nothing_comes_first_except_for_a_failure_to_launch() -> None:
    for category in CATEGORIES:
        assert category.accepts(category.default)
        if category is not LAUNCH_FAILED:  # an error to start is never switched off
            assert category.choices[0] is Destination.NONE
    assert not LAUNCH_FAILED.accepts(Destination.NONE)


def test_every_announcement_has_a_category_and_every_category_is_listed() -> None:
    """A member of ``Announce`` once took the tuple of its own name instead of a category."""
    assert all(announce.category in CATEGORIES for announce in Announce)
    assert {announce.category for announce in Announce} == set(CATEGORIES)


def test_some_announcements_go_with_the_category_that_can_always_say_them() -> None:
    assert Announce.NO_ELEMENT_FOUND.category is MOVEMENT_BLOCKED
    assert Announce.LINE_READ.category is LINE_READING
    # Not ACTIVITY: switched off, that category would say nothing, not even that it is off.
    assert Announce.ACTIVITY_OFF.category is FOLDER
    assert Announce.ACTIVITY.category is ACTIVITY
    assert Announce.POWERSHELL_CHANGED.category is FOLDER
    assert Announce.FOLDER_NOT_FOUND.category is LAUNCH_FAILED
    assert Announce.LINES_DROPPED.category is Announce.SIZE_CHANGED.category


def test_every_text_can_be_filled_by_its_named_fields() -> None:
    for announce in Announce:
        assert all(name and not name.isdigit() for name in announce.fields), announce
        assert announce.text.format(**dict.fromkeys(announce.fields, "x"))


def test_the_fields_of_a_text_are_its_named_fields() -> None:
    assert Announce.PROGRAM_ENDED.fields == {"program", "code"}
    assert Announce.PROGRAM_STOPPED.fields == frozenset()


def test_a_failing_sink_is_reported_once_then_replaced() -> None:
    errors: list[ScreenReaderOutputError] = []
    center = AnnouncementCenter(_FailingSink(), on_error=errors.append)
    center.notify(Announce.PROGRAM_STOPPED)
    center.notify(Announce.PROGRAM_STOPPED)
    assert len(errors) == 1
    assert isinstance(center.message_sink, NullMessageSink)


def test_outputs_depend_on_the_platform() -> None:
    assert available_outputs("win32") == (NONE, UIA)
    assert available_outputs("linux") == (NONE,)
    assert default_output("win32") is UIA
    assert default_output("linux") is NONE


def test_output_named_ignores_unavailable_outputs() -> None:
    assert output_named("uia", "win32") is UIA
    assert output_named("uia", "linux") is None
    assert output_named("unknown", "win32") is None


def test_a_text_asked_for_is_said_whatever_the_destinations() -> None:
    sink = RecordingMessageSink()
    center = AnnouncementCenter(sink, destination_of=lambda category: Destination.NONE)
    center.say_text("Read as: ls")
    assert sink.messages == ["Read as: ls"]
