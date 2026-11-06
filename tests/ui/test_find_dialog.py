"""The box of Find: a text with its label, and the check box of the direction."""

import pytest
import wx

from n5terminal.ui.find_dialog import FindDialog

pytestmark = pytest.mark.ui


def test_the_field_has_its_label_right_before_it_and_the_text_offered_is_selected(
    app: wx.App,
) -> None:
    frame = wx.Frame(None)
    dialog = FindDialog(frame, "Find in the output", "error", False, False)
    try:
        previous = dialog.text.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == "Text to search"
        assert dialog.text.GetName() == "Text to search"
        assert dialog.term() == "error"
        assert dialog.text.GetStringSelection() == "error"
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_the_check_box_of_the_direction_is_offered_as_it_was_and_read_back(app: wx.App) -> None:
    frame = wx.Frame(None)
    dialog = FindDialog(frame, "Find in the output", "", True, True)
    try:
        assert dialog.upwards.GetLabel() == "Search upwards"
        assert dialog.search_upwards()
        dialog.upwards.SetValue(False)
        assert not dialog.search_upwards()
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_the_check_box_of_the_regular_expression_is_offered_as_it_was_and_read_back(
    app: wx.App,
) -> None:
    frame = wx.Frame(None)
    dialog = FindDialog(frame, "Find in the output", "", False, True)
    try:
        assert dialog.regex.GetLabel() == "Regular expression"
        assert dialog.use_regex()
        dialog.regex.SetValue(False)
        assert not dialog.use_regex()
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_a_regular_expression_that_is_not_valid_is_refused_and_the_box_stays(
    app: wx.App, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = wx.Frame(None)
    dialog = FindDialog(frame, "Find in the output", "(", False, True)
    shown: list[str] = []

    def show(box: wx.MessageDialog) -> int:
        shown.append(box.GetMessage())
        return int(wx.ID_OK)

    monkeypatch.setattr(wx.MessageDialog, "ShowModal", show)
    skipped: list[bool] = []
    try:
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, wx.ID_OK)
        event.Skip = lambda *_a, **_k: skipped.append(True)
        dialog._on_ok(event)
        assert skipped == []  # not accepted
        assert len(shown) == 1
        assert shown[0].startswith("The regular expression is not valid:")
        dialog.regex.SetValue(False)  # as plain text "(" is fine
        dialog._on_ok(event)
        assert skipped == [True]
    finally:
        dialog.Destroy()
        frame.Destroy()
