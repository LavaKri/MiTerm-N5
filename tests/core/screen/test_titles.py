import pytest

from n5terminal.core.screen.titles import (
    from_utf16,
    next_title,
    parse_titles,
    previous_title,
    to_utf16,
)

pytestmark = pytest.mark.unit

SESSION = "# git status\nOn branch main\n# git log\ncommit abc\n## Details\nmore\n"


def test_a_launched_command_is_a_title_of_level_one() -> None:
    titles = parse_titles("# ping host\nreply\n")
    assert [(title.level, title.text) for title in titles] == [(1, "ping host")]
    assert (titles[0].start, titles[0].end) == (0, 11)


def test_titles_come_in_order_with_their_level() -> None:
    assert [(title.level, title.text) for title in parse_titles(SESSION)] == [
        (1, "git status"),
        (1, "git log"),
        (2, "Details"),
    ]


def test_text_that_is_not_a_title_is_ignored() -> None:
    assert parse_titles("plain\n> sent line\n#nospace\n") == []


def test_code_blocks_hide_the_lines_that_look_like_titles() -> None:
    titles = parse_titles("```\n# not a title\n```\n# a title\n")
    assert [title.text for title in titles] == ["a title"]


def test_next_and_previous_of_any_level() -> None:
    titles = parse_titles(SESSION)
    assert next_title(titles, 0) == titles[1]  # strictly after the caret
    assert next_title(titles, titles[1].start) == titles[2]
    assert next_title(titles, titles[2].start) is None
    assert previous_title(titles, titles[2].start) == titles[1]
    assert previous_title(titles, titles[0].start) is None


def test_the_caret_in_the_middle_of_a_title_line_counts_as_after_its_start() -> None:
    titles = parse_titles(SESSION)
    assert previous_title(titles, titles[1].start + 3) == titles[1]
    assert next_title(titles, titles[0].start + 3) == titles[1]


def test_only_the_titles_of_the_level_asked() -> None:
    titles = parse_titles(SESSION)
    assert next_title(titles, 0, level=2) == titles[2]
    assert next_title(titles, 0, level=3) is None
    assert previous_title(titles, len(SESSION), level=1) == titles[1]


def test_no_title_at_all() -> None:
    assert next_title([], 0) is None
    assert previous_title([], 10) is None


def test_utf16_positions_count_characters_outside_the_basic_plane_twice() -> None:
    text = "a\U0001f600b# x"
    assert to_utf16(text, 0) == 0
    assert to_utf16(text, 2) == 3
    assert from_utf16(text, 3) == 2
    assert from_utf16(text, 2) == 1  # the middle of the pair: its character
    assert from_utf16(text, 99) == len(text)
