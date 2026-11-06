import pytest

from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import (
    SEARCH,
    SEARCH_FAILED,
    Announce,
    AnnouncementCenter,
    Category,
    Destination,
)
from n5terminal.presenters.output_search import OutputSearch

pytestmark = pytest.mark.unit

TEXT = "# ls\nError one\nfine\nerror two\n"


def search(
    destinations: dict[Category, Destination] | None = None,
) -> tuple[OutputSearch, RecordingMessageSink]:
    sink = RecordingMessageSink()
    chosen = destinations or {}
    center = AnnouncementCenter(sink, lambda category: chosen.get(category, category.default))

    def say(announce: Announce, **values: object) -> None:
        center.notify(announce, **values)

    return OutputSearch(say), sink


def test_the_search_starts_at_the_caret_and_reads_the_line() -> None:
    found, sink = search()
    assert found.start("error", TEXT, 0) == TEXT.index("Error")
    assert sink.messages == ["Error one"]


def test_an_occurrence_at_the_caret_counts_for_a_new_search() -> None:
    found, _sink = search()
    assert found.start("error", TEXT, TEXT.index("Error")) == TEXT.index("Error")


def test_next_goes_past_the_occurrence_the_caret_is_on() -> None:
    found, sink = search()
    first = found.start("error", TEXT, 0)
    assert first is not None
    assert found.next(TEXT, first) == TEXT.index("error two")
    assert sink.messages == ["Error one", "error two"]


def test_previous_goes_back_and_the_word_is_kept() -> None:
    found, _sink = search()
    assert found.start("error", TEXT, len(TEXT)) is None
    assert found.term == "error"
    assert found.previous(TEXT, len(TEXT)) == TEXT.index("error two")
    assert found.previous(TEXT, TEXT.index("error two")) == TEXT.index("Error")


def test_a_missing_occurrence_is_announced_in_each_direction() -> None:
    found, sink = search()
    found.start("error", TEXT, TEXT.index("error two") + 1)
    assert found.next(TEXT, len(TEXT)) is None
    assert found.previous(TEXT, 0) is None
    assert sink.messages == [
        'No next occurrence of "error".',
        'No next occurrence of "error".',
        'No previous occurrence of "error".',
    ]


def test_the_search_can_be_silenced() -> None:
    found, sink = search({SEARCH: Destination.NONE, SEARCH_FAILED: Destination.NONE})
    assert found.start("error", TEXT, 0) == TEXT.index("Error")
    assert found.next(TEXT, len(TEXT)) is None
    assert sink.messages == []


def test_a_search_upwards_starts_before_the_caret_and_is_remembered() -> None:
    searching, sink = search()
    caret = TEXT.index("error two")
    assert searching.start("error", TEXT, caret, upwards=True) == TEXT.index("Error one")
    assert searching.upwards is True
    assert searching.start("error", TEXT, 0, upwards=True) is None
    assert sink.messages[-1] == 'No previous occurrence of "error".'
    assert searching.start("error", TEXT, 0) == TEXT.index("Error one")
    assert searching.upwards is False


def test_a_regular_expression_search_is_kept_for_next_and_previous() -> None:
    searching, _sink = search()
    assert searching.start(r"err\w+ (one|two)", TEXT, 0, regex=True) == TEXT.index("Error one")
    assert searching.regex is True
    assert searching.next(TEXT, TEXT.index("Error one")) == TEXT.index("error two")
    assert searching.previous(TEXT, TEXT.index("error two")) == TEXT.index("Error one")
    searching.start("(", TEXT, 0)  # plain text now: the kind is not kept from before
    assert searching.regex is False


def test_a_regular_expression_that_is_not_valid_is_said_and_searches_nothing() -> None:
    searching, sink = search()
    searching.start("fine", TEXT, 0)
    assert searching.start("(", TEXT, 0, regex=True) is None
    assert sink.messages[-1].startswith("The regular expression is not valid:")
    assert searching.term == "fine"  # the term before is kept
