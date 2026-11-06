import pytest

from n5terminal.presenters.choices import interpreter_choices, mode_choices, size_choices

pytestmark = pytest.mark.unit


def test_the_sizes_are_the_standard_ones_then_automatic() -> None:
    choices = size_choices(lambda text: text)
    assert choices[0] == ("80x24", "80 x 24")
    assert choices[-1] == ("auto", "Automatic")
    assert len(choices) == 7


def test_the_modes_and_the_interpreters() -> None:
    assert [value for value, _label in mode_choices(lambda text: text)] == ["cli", "tui"]
    assert [value for value, _label in interpreter_choices(lambda text: text)] == [
        "none",
        "cmd",
        "powershell",
    ]
