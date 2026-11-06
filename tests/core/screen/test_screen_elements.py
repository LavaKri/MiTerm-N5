"""The elements found in the last lines of the output, and the menus made of several lines."""

import pytest

from n5terminal.core.screen.line_analysis import ElementKind
from n5terminal.core.screen.screen_elements import find_elements

pytestmark = pytest.mark.unit


def found(text: str, last_lines: int = 24, cursor_index: int = -1) -> list[str]:
    return [
        element.describe()
        for element in find_elements(
            text, last_lines, selection_marks=True, cursor_index=cursor_index
        )
    ]


def test_each_element_is_said_with_its_kind_and_its_line() -> None:
    text = "# run\nDownload [####......] 40 %\nContinue? [Y/n]\nerror: disk full\nplain"
    assert found(text) == [
        "Progress, Download, 40 %, line 2",
        "Question: Continue? Default answer: yes, line 3",
        "Error: disk full, line 4",
    ]


def test_the_lines_of_a_menu_that_follow_each_other_are_one_element() -> None:
    text = "Pick one:\n  1) Alpha\n  2) Beta\n  3) Gamma\nChoice [1-3]:"
    assert found(text) == ["Choice, 3 options, line 2", "Question: Choice [1-3], line 5"]


def test_a_menu_names_the_item_chosen_and_points_at_its_line() -> None:
    text = "? Pick a color\n  Red\n> Green\n  Blue"
    elements = find_elements(text, 24, selection_marks=True, cursor_index=-1)
    assert [element.text for element in elements] == ["Choice, Green, selected"]
    text = "[ ] One\n[x] Two\n> Three\nother\n> Four"
    elements = find_elements(text, 24, selection_marks=True, cursor_index=-1)
    assert [element.text for element in elements] == [
        "Choice, 3 options, selected: Three",
        "Choice, Four, selected",
    ]
    assert elements[0].number == 3
    assert text[elements[0].index :].startswith("> Three")


def test_choices_that_are_not_next_to_each_other_are_two_elements() -> None:
    assert len(found("1) a\ntext\n2) b")) == 2


def test_the_terminal_cursor_inside_a_line_marks_the_item_chosen() -> None:
    text = "Pick:\nRed\nGreen\nBlue"
    assert found(text, cursor_index=text.index("Green")) == ["Choice, Green, selected, line 3"]


def test_only_the_last_lines_are_looked_at() -> None:
    text = "50%\nfiller\nfiller\n80%"
    assert found(text, last_lines=2) == ["Progress, 80 %, line 4"]
    assert found(text, last_lines=4) == ["Progress, 50 %, line 1", "Progress, 80 %, line 4"]


def test_nothing_recognized_gives_an_empty_list() -> None:
    assert found("hello\nworld\n") == []
    assert found("") == []


def test_the_kind_of_an_element_is_the_one_of_its_line() -> None:
    elements = find_elements("Password:", 24, selection_marks=True, cursor_index=-1)
    assert [element.kind for element in elements] == [ElementKind.QUESTION]
