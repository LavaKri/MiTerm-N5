"""The list of the elements recognized, with its copy button."""

from collections.abc import Iterator

import pytest
import wx

from n5terminal.ui.elements_dialog import ElementsDialog

pytestmark = pytest.mark.ui


@pytest.fixture
def dialog_and_copies(app: wx.App) -> Iterator[tuple[ElementsDialog, list[int]]]:
    frame = wx.Frame(None)
    copies: list[int] = []
    box = ElementsDialog(
        frame, "Identify", "Elements recognized", ["a", "b", "c"], 1, copies.append
    )
    yield box, copies
    box.Destroy()
    frame.Destroy()


def test_the_list_has_its_label_and_opens_on_the_line_asked(
    dialog_and_copies: tuple[ElementsDialog, list[int]],
) -> None:
    box, _copies = dialog_and_copies
    previous = box.list.GetPrevSibling()
    assert isinstance(previous, wx.StaticText)
    assert previous.GetLabel() == "Elements recognized"
    assert box.list.GetName() == "Elements recognized"
    assert box.selection() == 1


def test_the_copy_button_hands_the_selected_line_and_leaves_the_dialog_open(
    dialog_and_copies: tuple[ElementsDialog, list[int]],
) -> None:
    box, copies = dialog_and_copies
    assert box.copy_button.IsEnabled()
    box.copy_button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, box.copy_button.GetId()))
    box.list.SetSelection(2)
    box.copy_button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, box.copy_button.GetId()))
    assert copies == [1, 2]
