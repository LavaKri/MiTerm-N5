"""The multi-line input: one Send button, Escape to leave, a draft kept until it is sent."""

import pytest
import wx

from n5terminal.ui.multiline_dialog import MultilineDialog

pytestmark = pytest.mark.ui


@pytest.fixture
def dialog(app: wx.App) -> object:
    frame = wx.Frame(None)
    box = MultilineDialog(frame, "first\nsecond")
    yield box
    box.Destroy()
    frame.Destroy()


def test_the_text_has_a_name_and_its_label_right_before_it(dialog: MultilineDialog) -> None:
    previous = dialog.text.GetPrevSibling()
    assert isinstance(previous, wx.StaticText)
    assert previous.GetLabel() == "Lines to send"
    assert dialog.text.GetName() == "Lines to send"
    assert dialog.GetTitle() == "Multi-line input"


def test_it_opens_on_the_text_given_with_the_focus_in_the_text(dialog: MultilineDialog) -> None:
    assert dialog.value() == "first\nsecond"
    assert dialog.text.GetInsertionPoint() == dialog.text.GetLastPosition()


def test_the_text_is_multiline_and_enter_is_not_a_default_button(dialog: MultilineDialog) -> None:
    assert dialog.text.IsMultiLine()
    assert dialog.GetDefaultItem() is None


def test_the_only_button_is_send_and_there_is_no_cancel_button(dialog: MultilineDialog) -> None:
    buttons = [child for child in dialog.GetChildren() if isinstance(child, wx.Button)]
    assert [button.GetLabel() for button in buttons] == ["Send"]


def test_send_ends_the_box_with_ok_and_escape_with_cancel(dialog: MultilineDialog) -> None:
    wx.CallLater(
        50, dialog.send.Command, wx.CommandEvent(wx.EVT_BUTTON.typeId, dialog.send.GetId())
    )
    assert dialog.ShowModal() == wx.ID_OK
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    wx.CallLater(50, dialog._on_char_hook, event)
    assert dialog.ShowModal() == wx.ID_CANCEL
