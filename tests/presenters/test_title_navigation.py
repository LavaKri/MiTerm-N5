import pytest

from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import (
    MOVEMENT,
    Announce,
    AnnouncementCenter,
    Category,
    Destination,
)
from n5terminal.core.config.settings import Settings
from n5terminal.presenters.title_navigation import TitleNavigator

pytestmark = pytest.mark.unit

TEXT = "# git status\nOn branch main\n# git log\ncommit abc\n## Details\nmore\n"


def navigator(
    destinations: dict[Category, Destination] | None = None,
) -> tuple[TitleNavigator, RecordingMessageSink]:
    sink = RecordingMessageSink()
    chosen = destinations or {}
    center = AnnouncementCenter(sink, lambda category: chosen.get(category, category.default))

    def say(announce: Announce, **values: object) -> None:
        center.notify(announce, **values)

    return TitleNavigator(say), sink


def test_it_returns_where_the_title_starts_and_announces_it() -> None:
    nav, sink = navigator()
    assert nav.go(TEXT, 0, None, backwards=False) == TEXT.index("# git log")
    assert sink.messages == ["git log, title 1"]


def test_the_key_of_a_level_skips_the_other_levels() -> None:
    nav, _sink = navigator()
    assert nav.go(TEXT, 0, 2, backwards=False) == TEXT.index("## Details")


def test_backwards_goes_to_the_title_before() -> None:
    nav, _sink = navigator()
    assert nav.go(TEXT, len(TEXT), 1, backwards=True) == TEXT.index("# git log")


def test_the_end_of_the_output_is_announced() -> None:
    nav, sink = navigator()
    assert nav.go(TEXT, len(TEXT), None, backwards=False) is None
    assert nav.go(TEXT, 0, None, backwards=True) is None
    assert nav.go(TEXT, 0, 3, backwards=False) is None
    assert sink.messages == ["No next title.", "No previous title.", "No next title 3."]


def test_no_title_of_a_level_before_is_announced_with_the_level() -> None:
    nav, sink = navigator()
    assert nav.go(TEXT, 0, 3, backwards=True) is None
    assert sink.messages == ["No previous title 3."]


def test_the_line_can_be_read_instead_of_the_description() -> None:
    nav, sink = navigator({MOVEMENT: Destination.READ_LINE})
    nav.go(TEXT, 0, 1, backwards=False)
    assert sink.messages == ["git log"]


def test_the_movement_can_be_silenced() -> None:
    nav, sink = navigator({MOVEMENT: Destination.NONE})
    assert nav.go(TEXT, 0, 1, backwards=False) == TEXT.index("# git log")
    assert sink.messages == []


PROMPT_TEXT = "# PS C:\\x> git status\nOn branch main\n# PS C:\\x> git log\ncommit abc\n"


def comfortable_navigator(titles: bool) -> tuple[TitleNavigator, RecordingMessageSink]:
    sink = RecordingMessageSink()
    center = AnnouncementCenter(sink)
    settings = Settings.load(None)
    settings.comfort_titles = titles

    def say(announce: Announce, **values: object) -> None:
        center.notify(announce, **values)

    return TitleNavigator(say, settings), sink


def test_a_title_is_said_without_its_prompt_when_comfortable_reading_covers_titles() -> None:
    nav, sink = comfortable_navigator(titles=True)
    nav.go(PROMPT_TEXT, 0, None, backwards=False)
    assert sink.messages == ["Command git log, title 1"]


def test_a_title_is_said_as_it_is_when_comfortable_reading_does_not_cover_titles() -> None:
    nav, sink = comfortable_navigator(titles=False)
    nav.go(PROMPT_TEXT, 0, None, backwards=False)
    assert sink.messages == [r"PS C:\x> git log, title 1"]


def test_a_title_that_is_only_a_prompt_is_said_as_prompt() -> None:
    nav, sink = comfortable_navigator(titles=True)
    nav.go("# PS C:\\x>\n# PS C:\\x>\n", 0, None, backwards=False)
    assert sink.messages == ["Command, title 1"]
