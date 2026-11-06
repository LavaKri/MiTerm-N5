"""The box of one prompt pattern: the trial, its result to read, and F1 to hear it."""

from collections.abc import Iterator

import pytest
import wx

from n5terminal.core.config.prompt_patterns import START_PATTERNS
from n5terminal.presenters.prompt_patterns_editor import PromptPatternsEditor
from n5terminal.ui.prompt_patterns_dialog import PromptPatternDialog, PromptPatternsDialog

pytestmark = pytest.mark.ui


class Spoken:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def __call__(self, text: str) -> None:
        self.texts.append(text)


@pytest.fixture
def box(app: wx.App) -> Iterator[tuple[PromptPatternDialog, Spoken]]:
    frame = wx.Frame(None)
    spoken = Spoken()
    editor = PromptPatternsEditor(list(START_PATTERNS), False, False, lambda text: text)
    dialog = PromptPatternDialog(frame, editor, "Add a filter", spoken)
    yield dialog, spoken
    dialog.Destroy()
    frame.Destroy()


def key_f1() -> wx.KeyEvent:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_F1)
    return event


def test_the_result_is_a_read_only_text_of_several_lines_named_with_its_key(
    box: tuple[PromptPatternDialog, Spoken],
) -> None:
    dialog, _spoken = box
    assert dialog.result.IsMultiLine()
    assert not dialog.result.IsEditable()
    assert dialog.result.GetName() == "Result (F1 to hear)"
    previous = dialog.result.GetPrevSibling()
    assert isinstance(previous, wx.StaticText)
    assert previous.GetLabel() == "Result (F1 to hear)"


def test_the_result_follows_the_pattern_the_replacement_and_the_line(
    box: tuple[PromptPatternDialog, Spoken],
) -> None:
    dialog, _spoken = box
    dialog.pattern.SetValue(r"\w+@[\w\-]+:[^$]*\$")
    dialog.replacement.SetValue("Debian")
    dialog.line.SetValue("me@box:~$ ls")
    assert dialog.result.GetValue() == "Debian ls"


def test_f1_says_the_result_from_any_control_of_the_box(
    box: tuple[PromptPatternDialog, Spoken],
) -> None:
    dialog, spoken = box
    dialog.pattern.SetValue(r"\w+@[\w\-]+:[^$]*\$")
    dialog.line.SetValue("me@box:~$ ls")
    dialog._on_char_hook(key_f1())
    assert spoken.texts == ["ls"]


def test_f1_says_that_there_is_nothing_to_try_when_the_result_is_empty(
    box: tuple[PromptPatternDialog, Spoken],
) -> None:
    dialog, spoken = box
    dialog._on_char_hook(key_f1())
    assert spoken.texts == ["Nothing to try yet."]


def test_the_two_choices_of_the_reading_are_checkboxes_named_for_what_they_cover(
    app: wx.App,
) -> None:
    frame = wx.Frame(None)
    editor = PromptPatternsEditor(list(START_PATTERNS), False, True, lambda text: text)
    dialog = PromptPatternsDialog(frame, editor, Spoken())
    try:
        assert dialog.formatting.GetLabel() == "Include the formatting of the activities"
        assert dialog.titles.GetLabel() == "Comfortable reading for the moves by titles"
        assert not dialog.formatting.GetValue()  # as the editor was given
        assert dialog.titles.GetValue()
        dialog.titles.SetValue(False)
        dialog._take_titles()
        dialog.formatting.SetValue(True)
        dialog._take_formatting()
        assert (editor.formatting, editor.titles) == (True, False)
    finally:
        dialog.Destroy()
        frame.Destroy()
