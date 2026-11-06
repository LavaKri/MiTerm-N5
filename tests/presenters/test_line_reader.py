import pytest

from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import Announce, AnnouncementCenter, Destination
from n5terminal.core.session.session_state import Mode
from n5terminal.presenters.line_reader import LineReader

pytestmark = pytest.mark.unit


def reader() -> tuple[LineReader, RecordingMessageSink]:
    sink = RecordingMessageSink()
    center = AnnouncementCenter(sink, lambda category: category.default)

    def say(announce: Announce, **values: object) -> None:
        center.notify(announce, **values)

    return LineReader(say), sink


def test_a_recognized_line_is_said_as_its_element() -> None:
    line_reader, sink = reader()
    line_reader.read("Download [#####.....]  50%", Mode.TERMINAL_LINE)
    assert sink.messages == ["Download, 50 %"]


def test_any_other_line_is_said_without_its_decor() -> None:
    line_reader, sink = reader()
    line_reader.read("┌────────┐ box ┌─┐", Mode.TERMINAL_LINE)
    assert sink.messages == ["box"]


def test_an_empty_line_is_said_as_blank() -> None:
    line_reader, sink = reader()
    line_reader.read("────────", Mode.TERMINAL_LINE)
    line_reader.read("", Mode.PIPES)
    assert sink.messages == ["blank", "blank"]


def test_the_mark_of_a_selected_item_is_one_in_a_terminal_and_a_sent_line_with_pipes() -> None:
    line_reader, sink = reader()
    line_reader.read("> Red", Mode.TERMINAL_LINE)
    line_reader.read("> yes", Mode.PIPES)
    assert sink.messages == ["Red, selected", "> yes"]


def test_the_cursor_inside_the_text_of_the_line_marks_the_item_chosen() -> None:
    line_reader, sink = reader()
    line_reader.read("Green", Mode.TERMINAL_LINE, cursor_on_text=True)
    assert sink.messages == ["Green, selected"]


def _said_with(destination: Destination) -> RecordingMessageSink:
    sink = RecordingMessageSink()
    center = AnnouncementCenter(sink, lambda category: destination)

    def say(announce: Announce, **values: object) -> None:
        center.notify(announce, **values)

    LineReader(say).read("Downloading  60%", Mode.PIPES)
    return sink


def test_the_destination_decides_between_the_formatted_text_the_line_and_nothing() -> None:
    assert _said_with(Destination.NONE).messages == []
    formatted = _said_with(Destination.MESSAGE).messages
    assert formatted == ["Downloading, 60 %"]
    assert _said_with(Destination.READ_LINE).messages == ["Downloading  60%"]
