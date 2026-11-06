import pytest

from n5terminal.core.screen.text_search import (
    cursor_is_on_line_text,
    find_next,
    find_previous,
    line_at,
    neighbour_line,
    regex_problem,
)

pytestmark = pytest.mark.unit

TEXT = "# ls\nError one\nfine\nerror two\nERROR three\n"


def test_the_next_occurrence_begins_at_or_after_the_start() -> None:
    assert find_next(TEXT, "error", 0) == TEXT.index("Error")
    assert find_next(TEXT, "error", TEXT.index("Error")) == TEXT.index("Error")
    assert find_next(TEXT, "error", TEXT.index("Error") + 1) == TEXT.index("error two")


def test_the_case_is_ignored() -> None:
    assert find_next(TEXT, "ERROR", TEXT.index("fine")) == TEXT.index("error two")


def test_there_is_no_next_occurrence_past_the_last() -> None:
    assert find_next(TEXT, "error", TEXT.index("ERROR") + 1) is None
    assert find_next(TEXT, "absent", 0) is None
    assert find_next(TEXT, "error", len(TEXT) + 10) is None


def test_the_previous_occurrence_begins_strictly_before() -> None:
    last = TEXT.index("ERROR")
    assert find_previous(TEXT, "error", last) == TEXT.index("error two")
    assert find_previous(TEXT, "error", last + 3) == last  # inside an occurrence, its start counts
    assert find_previous(TEXT, "error", TEXT.index("Error")) is None
    assert find_previous(TEXT, "error", 0) is None


def test_overlapping_occurrences_all_count() -> None:
    assert find_next("aaa", "aa", 1) == 1
    assert find_previous("aaa", "aa", 2) == 1


def test_an_empty_word_finds_nothing() -> None:
    assert find_next(TEXT, "", 0) is None
    assert find_previous(TEXT, "", len(TEXT)) is None


def test_special_characters_of_a_pattern_are_plain_text() -> None:
    assert find_next("a.c abc a.c", ".", 0) == 1
    assert find_next("x (y) z", "(y)", 0) == 2


def test_the_line_of_an_occurrence_is_returned_without_its_break() -> None:
    assert line_at(TEXT, TEXT.index("error two")) == "error two"
    assert line_at(TEXT, 0) == "# ls"
    assert line_at("last line", 3) == "last line"


def test_the_cursor_is_on_the_text_of_a_line_when_it_is_inside_it() -> None:
    text = "first\nsecond\nC:\\>"
    second = text.index("second")
    assert cursor_is_on_line_text(text, second + 2, second)  # at the start of the line
    assert cursor_is_on_line_text(text, second, second + 3)
    assert not cursor_is_on_line_text(text, second, second + len("second"))  # behind the text
    assert not cursor_is_on_line_text(text, second, 0)  # on another line
    assert not cursor_is_on_line_text(text, len(text), len(text))  # behind a prompt


def test_the_neighbour_line_is_found_from_any_place_of_a_line() -> None:
    text = "one\ntwo\nthree"
    assert neighbour_line(text, 0, forward=True) == 4
    assert neighbour_line(text, 2, forward=True) == 4
    assert neighbour_line(text, 5, forward=True) == 8
    assert neighbour_line(text, 9, forward=True) is None
    assert neighbour_line(text, 9, forward=False) == 4
    assert neighbour_line(text, 4, forward=False) == 0
    assert neighbour_line(text, 2, forward=False) is None


def test_the_empty_line_after_the_last_break_is_a_line() -> None:
    text = "one\n"
    assert neighbour_line(text, 0, forward=True) == 4
    assert neighbour_line(text, 4, forward=True) is None
    assert neighbour_line(text, 4, forward=False) == 0


def test_a_regular_expression_finds_forward_and_backward() -> None:
    text = "a1 b22 c333 d"
    assert find_next(text, r"\d+", 0, regex=True) == 1
    assert find_next(text, r"\d{2,}", 0, regex=True) == 4
    # every place a match can begin counts, as for plain text: the last digit starts one
    assert find_previous(text, r"\d+", len(text), regex=True) == 10
    assert find_previous(text, r"[a-c]\d", 8, regex=True) == 7
    assert find_previous(text, r"[a-c]\d", 7, regex=True) == 3


def test_a_regular_expression_ignores_the_case_and_skips_an_empty_match() -> None:
    assert find_next("xx ERROR", "error", 0, regex=True) == 3
    assert find_next("abc", "x*", 0, regex=True) is None
    assert find_previous("abc", "x*", 3, regex=True) is None


def test_a_term_is_plain_text_unless_the_expression_is_asked_for() -> None:
    assert find_next("a1 a.", r"a.", 0) == 3
    assert find_next("a1 a.", r"a.", 0, regex=True) == 0


def test_a_regular_expression_is_checked() -> None:
    assert regex_problem(r"\d+") is None
    assert regex_problem("(") is not None
