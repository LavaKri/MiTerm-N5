"""The context menus of the output area and of the command field.

A popup menu is modal, so ``PopupMenu`` is replaced by a recorder: the tests check that our menu
is the one shown, and what it holds.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.settings import Settings
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


def pump() -> None:
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.Yield()


@pytest.fixture
def window(app: wx.App, tmp_path: Path) -> Iterator[MainWindow]:
    frame = MainWindow(Settings.load(None), FakeLauncher(), tmp_path)
    frame.Show()
    pump()
    yield frame
    frame.Close(force=True)


def record_popups(control: wx.Window) -> list[wx.Menu]:
    shown: list[wx.Menu] = []
    control.PopupMenu = lambda menu, *_position: shown.append(menu)
    return shown


def key_event(code: int, *, shift: bool = False) -> wx.KeyEvent:
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(code)
    event.SetShiftDown(shift)
    return event


def labels(menu: wx.Menu) -> list[str]:
    return [item.GetItemLabelText() for item in menu.GetMenuItems() if not item.IsSeparator()]


def test_the_output_area_shows_our_menu_with_send(window: MainWindow) -> None:
    shown = record_popups(window.output)
    window.output._on_right_up(wx.MouseEvent(wx.wxEVT_RIGHT_UP))
    assert len(shown) == 1
    names = labels(shown[0])
    assert len(names) == 5  # Copy, Select all, the two titles, Send
    assert "title" in names[2] or "Titre" in names[2]
    assert "title" in names[3] or "Titre" in names[3]
    assert "Send" in names[-1] or "Envoyer" in names[-1]
    assert shown[0].FindItemById(wx.ID_COPY) is not None
    assert shown[0].FindItemById(wx.ID_SELECTALL) is not None


@pytest.mark.parametrize(("code", "shift"), [(wx.WXK_WINDOWS_MENU, False), (wx.WXK_F10, True)])
def test_the_menu_keys_show_our_menu_in_the_output_area(
    window: MainWindow, code: int, shift: bool
) -> None:
    shown = record_popups(window.output)
    window.output._on_key(key_event(code, shift=shift))
    assert len(shown) == 1


def test_f10_alone_is_not_the_menu_key(window: MainWindow) -> None:
    shown = record_popups(window.output)
    window.output._on_key(key_event(wx.WXK_F10))
    assert shown == []


def test_the_send_items_are_greyed_without_a_program(window: MainWindow) -> None:
    shown = record_popups(window.output)
    window.output._on_right_up(wx.MouseEvent(wx.wxEVT_RIGHT_UP))
    send = shown[0].GetMenuItems()[-1]
    assert not send.IsEnabled()


def test_the_command_field_menu_has_history_and_no_send(window: MainWindow) -> None:
    shown = record_popups(window.command.field)
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, window.command.field.GetId())
    window.command._on_context_menu(event)
    assert len(shown) == 1
    assert shown[0].FindItemById(wx.ID_CUT) is not None
    assert not any("Send" in name or "Envoyer" in name for name in labels(shown[0]))


def test_the_command_field_menu_has_the_multi_line_input_after_the_history(
    window: MainWindow,
) -> None:
    shown = record_popups(window.command.field)
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, window.command.field.GetId())
    window.command._on_context_menu(event)
    names = labels(shown[0])
    assert names[0] in ("History", "Historique")
    assert names[1].startswith(
        ("Multi-line input", "Saisie sur plusieurs lignes", "Saisie multili")
    )
    item = shown[0].GetMenuItems()[1]
    assert item.IsEnabled()
    assert item.GetItemLabel().endswith("Ctrl+M")
