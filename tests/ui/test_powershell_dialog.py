"""The dialog "PowerShell selection"."""

from collections.abc import Iterator

import pytest
import wx

from n5terminal.core.session.powershells import PowerShellInstall
from n5terminal.presenters.powershell_choice import PowerShellChoice
from n5terminal.ui.powershell_dialog import PowerShellDialog

pytestmark = pytest.mark.ui

SEVEN = PowerShellInstall(r"C:\Program Files\PowerShell\7\pwsh.exe", "7")


def _make(current: str) -> tuple[wx.Frame, PowerShellChoice, PowerShellDialog]:
    frame = wx.Frame(None)
    draft = PowerShellChoice(current, [SEVEN], lambda text: text, lambda path: bool(path))
    return frame, draft, PowerShellDialog(frame, draft)


@pytest.fixture
def dialog(app: wx.App) -> Iterator[PowerShellDialog]:
    frame, _draft, box = _make("")
    yield box
    box.Destroy()
    frame.Destroy()


def test_each_label_comes_right_before_its_control(dialog: PowerShellDialog) -> None:
    for control, label in (
        (dialog.versions, "PowerShell version"),
        (dialog.path, "PowerShell path"),
    ):
        previous = control.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == label
        assert control.GetName() == label


def test_the_list_starts_on_windows_powershell_and_the_path_is_greyed(
    dialog: PowerShellDialog,
) -> None:
    assert dialog.versions.GetStrings()[0] == "Windows PowerShell"
    assert dialog.versions.GetSelection() == 0
    assert not dialog.path.IsEnabled()
    assert not dialog.browse.IsEnabled()


def test_other_enables_the_path_and_its_button(dialog: PowerShellDialog) -> None:
    dialog.versions.SetSelection(dialog.versions.GetCount() - 1)
    dialog._show_path_state()
    assert dialog.path.IsEnabled()
    assert dialog.browse.IsEnabled()


def test_a_stored_path_that_is_not_listed_opens_on_other_with_the_path(app: wx.App) -> None:
    frame, draft, box = _make(r"D:\Tools\pwsh.exe")
    try:
        assert box.versions.GetStringSelection() == "Other…"
        assert box.path.GetValue() == r"D:\Tools\pwsh.exe"
        assert box.path.IsEnabled()
        box.commit()
        assert draft.chosen_path() == r"D:\Tools\pwsh.exe"
    finally:
        box.Destroy()
        frame.Destroy()


def test_commit_hands_the_choice_to_the_draft(app: wx.App) -> None:
    frame, draft, box = _make("")
    try:
        box.versions.SetSelection(1)
        box.commit()
        assert draft.chosen_path() == SEVEN.path
    finally:
        box.Destroy()
        frame.Destroy()
