"""The dialogs of ``Feedback``: where the focus goes back, what the text and choice dialogs hold.

``ShowModal`` is replaced, so that no dialog is really shown. For the focus, ``wx.Window.FindFocus``
is replaced too: the real focus of Windows depends on which window is in front while the tests run,
and a test that relied on it could pass without checking anything.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import pytest
import wx

from n5terminal.core.config.settings import Settings
from n5terminal.ui.feedback import Feedback

pytestmark = pytest.mark.ui


def pump() -> None:
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.Yield()


@dataclass
class Rig:
    frame: wx.Frame
    field: wx.TextCtrl  # a control of the window
    feedback: Feedback
    closing: list[bool] = field(default_factory=lambda: [False])


@pytest.fixture
def rig(app: wx.App) -> Iterator[Rig]:
    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    control = wx.TextCtrl(panel)
    closing = [False]
    feedback = Feedback(frame, Settings.load(None), lambda: closing[0])
    yield Rig(frame, control, feedback, closing)
    frame.Destroy()
    pump()


class Target:
    """What had the focus before the dialog: it only notes that the focus was given back."""

    def __init__(self) -> None:
        self.given_back = 0

    def SetFocus(self) -> None:  # noqa: N802 (wx API)
        self.given_back += 1


def see_focus(monkeypatch: pytest.MonkeyPatch, *seen: object) -> None:
    """The calls of ``wx.Window.FindFocus`` answer ``seen``, one after the other."""
    answers = iter(seen)
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: next(answers)))


def show(rig: Rig, monkeypatch: pytest.MonkeyPatch, result: int = wx.ID_OK) -> int:
    """Run ``Feedback.modal`` on a dialog that closes at once with ``result``."""
    dialog = wx.Dialog(rig.frame)
    monkeypatch.setattr(dialog, "ShowModal", lambda: result)
    try:
        return rig.feedback.modal(dialog)
    finally:
        dialog.Destroy()


# Where the focus goes back (rule A of "Focus and caret", specs/interface.md) --------------------


def test_the_dialog_gives_its_result_back(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    see_focus(monkeypatch, None)
    assert show(rig, monkeypatch, wx.ID_CANCEL) == wx.ID_CANCEL
    pump()


@pytest.mark.parametrize("where", ["nowhere", "another window"])
def test_the_focus_goes_back_when_it_is_nowhere_or_outside_the_window(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    other = wx.Frame(None)
    target = Target()
    after = None if where == "nowhere" else other
    see_focus(monkeypatch, target, after)
    show(rig, monkeypatch)
    pump()
    other.Destroy()
    assert target.given_back == 1


def test_the_focus_is_left_where_the_user_put_it_inside_the_window(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Target()
    see_focus(monkeypatch, target, rig.field)  # a control of the window has it now
    show(rig, monkeypatch)
    pump()
    assert target.given_back == 0


def test_the_focus_is_left_alone_when_the_window_is_closing(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Target()
    rig.closing[0] = True
    see_focus(monkeypatch, target, None)
    show(rig, monkeypatch)
    pump()
    assert target.given_back == 0


def test_nothing_is_given_back_when_nothing_had_the_focus(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    see_focus(monkeypatch, None, None)
    show(rig, monkeypatch)
    pump()  # no error: there is nobody to give it to


def test_the_focus_goes_back_even_when_the_dialog_fails(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Target()
    see_focus(monkeypatch, target, None)
    dialog = wx.Dialog(rig.frame)

    def fail() -> int:
        raise RuntimeError("the dialog broke")

    monkeypatch.setattr(dialog, "ShowModal", fail)
    with pytest.raises(RuntimeError):
        rig.feedback.modal(dialog)
    dialog.Destroy()
    pump()
    assert target.given_back == 1


# The text dialog (About, Session information) -----------------------------------------------------


def capture(rig: Rig, monkeypatch: pytest.MonkeyPatch, look: Callable[[wx.Dialog], int]) -> None:
    """The next dialog goes to ``look`` instead of the screen; its result is what ``look`` gives."""
    monkeypatch.setattr(rig.feedback, "modal", look)


def test_the_text_dialog_holds_a_read_only_field_named_like_its_title(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def look(dialog: wx.Dialog) -> int:
        control = next(child for child in dialog.GetChildren() if isinstance(child, wx.TextCtrl))
        seen.update(
            title=dialog.GetTitle(),
            name=control.GetName(),
            text=control.GetValue(),
            editable=control.IsEditable(),
            multiline=control.IsMultiLine(),
            ok_button=dialog.FindWindowById(wx.ID_OK) is not None,
        )
        return int(wx.ID_OK)

    capture(rig, monkeypatch, look)
    rig.feedback.show_text("About", "line one\nline two")
    assert seen == {
        "title": "About",
        "name": "About",  # the accessible name: a screen reader says it when the field is reached
        "text": "line one\nline two",
        "editable": False,
        "multiline": True,
        "ok_button": True,
    }


# The choice dialog (the history) ------------------------------------------------------------------


def test_the_choice_dialog_opens_on_the_line_asked_and_gives_the_one_picked(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[tuple[str, int]] = []

    def look(dialog: wx.Dialog) -> int:
        assert isinstance(dialog, wx.SingleChoiceDialog)
        opened.append((dialog.GetTitle(), dialog.GetSelection()))
        dialog.SetSelection(0)  # the user picks the first line
        return int(wx.ID_OK)

    capture(rig, monkeypatch, look)
    picked = rig.feedback.choose("Command history", "Commands", ["a", "b", "c"], selected=2)
    assert opened == [("Command history", 2)]
    assert picked == 0


def test_a_cancelled_choice_gives_nothing(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    capture(rig, monkeypatch, lambda dialog: wx.ID_CANCEL)
    assert rig.feedback.choose("Command history", "Commands", ["a", "b"]) is None
