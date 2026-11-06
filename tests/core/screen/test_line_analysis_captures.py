"""The analysis of the lines of real programs: the captures of ``tests/data/captures``."""

import pytest

from fakes.capture_replay import replay
from fakes.captures import load_capture
from n5terminal.core.screen.line_analysis import ElementKind, LineElement, analyze_line

pytestmark = pytest.mark.unit


def final_lines(name: str) -> list[str]:
    """The lines of the capture once drawn: those that left the screen, then the screen."""
    fixed: list[str] = []
    live: dict[int, str] = {}
    for step in replay(load_capture(name), chunk=4096):
        fixed.extend(line.text for line in step.update.fixed)
        if step.update.replace_all:
            live.clear()
        live.update({row.number: row.text for row in step.update.rows})
    return [*fixed, *(text for _number, text in sorted(live.items()))]


def seen_lines(name: str) -> list[str]:
    """Every row the capture showed on the way, one byte at a time."""
    seen: list[str] = []
    for step in replay(load_capture(name), chunk=1):
        seen.extend(row.text for row in step.update.rows if row.text)
    return seen


def elements(lines: list[str]) -> list[LineElement]:
    return [element for line in lines if (element := analyze_line(line))]


def test_a_bar_rewritten_in_place_climbs_to_a_hundred() -> None:
    found = elements(seen_lines("bar_cr"))
    values = [element.value for element in found]
    assert all(element.kind is ElementKind.PROGRESS for element in found)
    assert values == sorted(values, key=lambda value: value or 0)
    assert {0, 20, 40, 60, 80, 100} <= set(values)
    assert found[-1].text == "Downloading, 100 %"


def test_two_bars_drawn_by_positioning_the_cursor() -> None:
    found = elements(final_lines("two_bars"))
    assert [element.text for element in found] == ["Download, 100 %", "Unpack, 50 %"]


def test_a_question_is_found_while_it_waits_and_not_once_answered() -> None:
    waiting = [element.text for element in elements(seen_lines("questions"))]
    assert "Question: Overwrite the file? Default answer: no" in waiting
    assert "Question: Password" in waiting
    # The answers that echo are on the line, so those questions are gone; a password echoes
    # nothing, so its line looks the same after the answer (a known limit, open-questions.md).
    left = [element.text for element in elements(final_lines("questions"))]
    assert left == ["Question: Password"]


def test_the_items_of_a_numbered_menu() -> None:
    found = elements(final_lines("numbered_menu"))
    assert [element.text for element in found] == [
        "Option 1, Alpha",
        "Option 2, Beta",
        "Option 3, Gamma",
    ]
    assert all(element.kind is ElementKind.CHOICE for element in found)


def test_the_selected_item_of_a_menu_marked_by_a_glyph() -> None:
    found = elements(final_lines("glyph_menu"))
    assert [element.text for element in found] == ["Red, selected"]


def test_the_errors_of_a_program() -> None:
    found = elements(final_lines("errors"))
    assert [element.text for element in found] == [
        "Error: file not found",
        "Warning: using the default",
        "Error: Access is denied.",
        "Error: Traceback (most recent call last):",
        "Error: ValueError: boom",
    ]


def test_pip_without_a_bar_shows_no_progress() -> None:
    assert not any(e.kind is ElementKind.PROGRESS for e in elements(final_lines("pip_dry_run")))


def test_a_table_of_winget_shows_nothing_to_recognize() -> None:
    assert elements(final_lines("winget_search")) == []


@pytest.mark.parametrize("name", ["echo", "many_lines", "long_line", "accents", "colors"])
def test_ordinary_output_shows_nothing_to_recognize(name: str) -> None:
    assert elements(final_lines(name)) == []
