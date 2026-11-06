"""Does pyte find the text in reverse video in what a real ConPTY emits? (Experiment of 6f.)

A list of choices often shows the chosen line in reverse video, with no other mark. The analysis of
the output would need to know which rows have such text (``marked_rows``, see
``specs/architecture/screen.md``, "Analysis of the output"). These tests replay the capture
``reverse.vt``, made by ``tools/capture_conpty.py`` with a real ConPTY. Its five lines were written
plain, in VT reverse video, with the reverse video attribute of the Windows console API, with two
colours only, and in reverse video up to the edge of the screen.
"""

import pyte
import pytest

from fakes.captures import load_capture

pytestmark = pytest.mark.unit

PLAIN, VT, WIN32, COLOURS, TO_THE_EDGE = range(5)


@pytest.fixture(scope="module")
def screen() -> pyte.Screen:
    capture = load_capture("reverse")
    screen = pyte.Screen(capture.columns, capture.rows)
    pyte.Stream(screen).feed(capture.text)
    return screen


def text_of(screen: pyte.Screen, row: int) -> str:
    return "".join(screen.buffer[row][x].data for x in range(screen.columns)).rstrip()


def reverse_columns(screen: pyte.Screen, row: int) -> list[int]:
    """The columns of the row that show a character in reverse video (blanks included)."""
    return [x for x in range(screen.columns) if screen.buffer[row][x].reverse]


def test_the_capture_holds_the_five_lines(screen: pyte.Screen) -> None:
    assert [text_of(screen, row) for row in range(5)] == [
        "plain line",
        "vt reverse",
        "win32 reverse",
        "colours only",
        "to the edge",
    ]


def test_a_plain_line_has_no_reverse_video(screen: pyte.Screen) -> None:
    assert reverse_columns(screen, PLAIN) == []


def test_vt_reverse_video_is_found_on_the_text_and_only_there(screen: pyte.Screen) -> None:
    assert reverse_columns(screen, VT) == list(range(len("vt reverse")))


def test_the_reverse_video_attribute_of_the_windows_console_arrives_as_vt_reverse_video(
    screen: pyte.Screen,
) -> None:
    """A program that never writes a VT sequence is seen the same way: ConPTY turns it into one."""
    assert reverse_columns(screen, WIN32) == list(range(len("win32 reverse")))


def test_two_colours_are_not_reverse_video(screen: pyte.Screen) -> None:
    """Black on white is colours, not an attribute: a list marked that way is not found."""
    cell = screen.buffer[COLOURS][0]
    assert (cell.fg, cell.bg) == ("black", "white")
    assert reverse_columns(screen, COLOURS) == []


def test_reverse_video_erased_to_the_end_of_the_line_runs_to_the_edge(screen: pyte.Screen) -> None:
    """The row is in reverse video to the last column: only the cells with text count."""
    columns = reverse_columns(screen, TO_THE_EDGE)
    assert columns == list(range(screen.columns))
    with_text = [x for x in columns if screen.buffer[TO_THE_EDGE][x].data.strip()]
    assert with_text == [x for x, char in enumerate("to the edge") if char != " "]
