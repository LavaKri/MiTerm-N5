import pytest

from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.screen_model import FixedLine

pytestmark = pytest.mark.unit

ERASE = b"\x1b[2J\x1b[H"


def _model(*outputs: bytes) -> PyteScreenModel:
    """A 5 x 20 screen that was fed ``outputs`` one after the other, each one handed out."""
    model = PyteScreenModel(20, 5)
    model.take_update()
    for output in outputs:
        model.feed(output)
        model.take_update()
    return model


def test_an_erased_screen_gives_its_last_view_to_the_fixed_part_at_the_end() -> None:
    model = _model(b"first\r\nsecond\r\n\r\nfourth", ERASE)
    model.finish()
    assert model.take_update().fixed == (
        FixedLine("first"),
        FixedLine("second"),
        FixedLine(""),
        FixedLine("fourth"),
    )


def test_the_last_view_is_the_last_screen_that_had_text() -> None:
    model = _model(b"one", ERASE, b"two", ERASE)
    model.finish()
    assert model.take_update().fixed == (FixedLine("two"),)


def test_a_screen_with_text_at_the_end_is_left_as_it_is() -> None:
    model = _model(b"first\r\nsecond", ERASE, b"after")
    model.finish()
    assert model.take_update().fixed == ()


def test_a_screen_that_never_had_text_gives_nothing() -> None:
    model = _model(ERASE)
    model.finish()
    assert model.take_update().fixed == ()


def test_the_last_view_is_given_once() -> None:
    model = _model(b"text", ERASE)
    model.finish()
    model.take_update()
    model.finish()
    assert model.take_update().fixed == ()


def test_the_last_view_is_what_the_screen_showed_not_what_scrolled_off_before() -> None:
    model = _model(b"1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7", ERASE)  # "1" and "2" scrolled off earlier
    model.finish()
    assert model.take_update().fixed == tuple(FixedLine(text) for text in ("3", "4", "5", "6", "7"))
