"""The guard gives the foreground watch the main window to give the foreground to."""

import pytest
import wx

from fakes.fake_foreground import FakeForeground
from n5terminal.core.transport.foreground import Holder
from n5terminal.ui.foreground_guard import ForegroundGuard

pytestmark = pytest.mark.ui


def test_the_foreground_is_given_to_the_main_window(app: wx.App) -> None:
    frame = wx.Frame(None)
    windows = FakeForeground(Holder.OWN_WINDOW)
    guard = ForegroundGuard(frame, windows)
    assert not guard.check()
    windows.current = Holder.OWN_CONSOLE
    assert guard.check()
    assert windows.calls == ["unlock", f"take_back {int(frame.GetHandle())}"]
    frame.Destroy()
