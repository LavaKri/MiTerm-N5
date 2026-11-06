"""Takes the foreground back when the console window of a pseudo terminal steals it.

The decisions are in ``core/transport/foreground.py``; this class gives them the window to give the
foreground to. Only a console window of this process is ever repaired, and only when a window of
the application held the foreground just before: a switch to another application is never touched.
"""

import wx

from n5terminal.core.transport.foreground import ForegroundWatch, ForegroundWindows, Win32Foreground


class ForegroundGuard:
    """Called often (the timer of the window): gives ``frame`` the foreground back when needed."""

    def __init__(self, frame: wx.Frame, windows: ForegroundWindows | None = None) -> None:
        self._frame = frame
        self._watch = ForegroundWatch(windows if windows is not None else Win32Foreground())

    def check(self) -> bool:
        """Look once; True if the foreground was taken back."""
        return self._watch.check(int(self._frame.GetHandle()))
