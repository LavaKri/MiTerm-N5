"""The addresses among the elements of the screen."""

import pytest

from n5terminal.core.screen.line_analysis import ElementKind
from n5terminal.core.screen.screen_elements import (
    FoundElement,
    find_elements,
    initial_selection,
)

pytestmark = pytest.mark.unit


def elements(text: str, *, selection_marks: bool = True) -> list[FoundElement]:
    return find_elements(text, 24, selection_marks=selection_marks, cursor_index=-1)


def test_an_address_is_an_element_said_as_the_address_alone_in_the_order_of_the_text() -> None:
    text = "Visit https://example.org/doc\nContinue? [Y/n]\nwrite me@example.org\n"
    assert [e.describe() for e in elements(text)] == [
        "https://example.org/doc",
        "Question: Continue? Default answer: yes, line 2",
        "me@example.org",
    ]


def test_the_index_of_an_address_is_its_own_start_not_the_start_of_the_line() -> None:
    text = "Visit https://example.org/doc"
    [element] = elements(text)
    assert element.kind is ElementKind.URL
    assert text[element.index :] == "https://example.org/doc"
    assert element.number == 1


def test_a_line_may_hold_an_element_and_addresses() -> None:
    kinds = [e.kind for e in elements("error: see https://a.fr/log or b@c.fr")]
    assert kinds == [ElementKind.ERROR, ElementKind.URL, ElementKind.EMAIL]


def test_a_command_launched_or_sent_has_no_address_to_pick() -> None:
    assert elements("# curl https://a.fr\n") == []
    assert elements("> curl https://a.fr\n", selection_marks=False) == []


def test_the_list_opens_on_the_last_element_that_is_not_an_address() -> None:
    found = elements("Continue? [Y/n]\nsee https://a.fr/x\n")
    assert [e.kind for e in found] == [ElementKind.QUESTION, ElementKind.URL]
    assert initial_selection(found) == 0
    assert initial_selection(elements("https://a.fr/x")) == 0
    assert initial_selection([]) == 0
