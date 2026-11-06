"""Keeps the foreground on the main window when a pseudo console takes it.

The hidden console window of a pseudo console belongs to this process. Windows gives it the
foreground when a program starts, or asks its terminal to restore its window (``ESC [ 1 t``):
nothing can be done in that window, a screen reader only says "pythonw", and Alt+Tab is the only way
back. Two means, see "The window" in ``specs/architecture/window.md`` (the foreground guard):
- :func:`hold_foreground` forbids the change while the pseudo console starts;
- :class:`ForegroundWatch` takes the foreground back when it was lost all the same, and keeps trying
  for a second, because Windows may refuse the first call.
"""

import ctypes
import logging
import os
import threading
from ctypes import wintypes
from enum import Enum
from typing import Protocol

logger = logging.getLogger(__name__)

CONSOLE_WINDOW_CLASSES = ("ConsoleWindowClass", "PseudoConsoleWindow")
HOLD_SECONDS = 0.4  # the console takes the foreground about 60 ms after the program starts
ATTEMPTS = 20  # looks of the guard (50 ms each) during which a lost foreground is claimed again
LSFW_LOCK = 1
LSFW_UNLOCK = 2
CLASS_NAME_LENGTH = 64


class Holder(Enum):
    """Who holds the foreground."""

    OWN_WINDOW = "own window"  # a window of this application: the main window, a dialog
    OWN_CONSOLE = "own console"  # the hidden console window of a pseudo console of this process
    OTHER = "other"  # another application, or nothing


def classify(class_name: str, pid: int, own_pid: int) -> Holder:
    """Who a window of this class and process is: a console window is only ours if our process."""
    if pid != own_pid:
        return Holder.OTHER  # Windows Terminal and other applications own console windows too
    return Holder.OWN_CONSOLE if class_name in CONSOLE_WINDOW_CLASSES else Holder.OWN_WINDOW


class ForegroundWindows(Protocol):
    """What the guard asks of Windows: a fake in the tests."""

    def holder(self) -> Holder:
        """Who holds the foreground now."""
        ...

    def lock(self) -> bool:
        """Forbid the change of the foreground; refused unless this process holds it."""
        ...

    def unlock(self) -> bool:
        """Allow the change of the foreground again."""
        ...

    def take_back(self, window: int) -> bool:
        """Give the foreground to ``window``; False when Windows refused."""
        ...

    def describe_foreground(self) -> str:
        """The window that holds the foreground, for the log."""
        ...


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.GetForegroundWindow.argtypes = ()
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.LockSetForegroundWindow.argtypes = (wintypes.UINT,)
_user32.LockSetForegroundWindow.restype = wintypes.BOOL
_user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
_user32.AttachThreadInput.restype = wintypes.BOOL
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetCurrentThreadId.argtypes = ()
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class Win32Foreground:
    """:class:`ForegroundWindows` on the Windows API."""

    def holder(self) -> Holder:
        window = _user32.GetForegroundWindow()
        if not window:
            return Holder.OTHER
        class_name, pid, _thread = self._identify(window)
        return classify(class_name, pid, os.getpid())

    def lock(self) -> bool:
        return bool(_user32.LockSetForegroundWindow(LSFW_LOCK))

    def unlock(self) -> bool:
        return bool(_user32.LockSetForegroundWindow(LSFW_UNLOCK))

    def take_back(self, window: int) -> bool:
        if _user32.SetForegroundWindow(window):
            return True
        holder = _user32.GetForegroundWindow()
        if not holder:
            return False
        # Attached to the input of the thread that holds the foreground, this thread may take it.
        theirs = self._identify(holder)[2]
        ours = _kernel32.GetCurrentThreadId()
        if not _user32.AttachThreadInput(ours, theirs, True):
            return False
        try:
            return bool(_user32.SetForegroundWindow(window))
        finally:
            _user32.AttachThreadInput(ours, theirs, False)

    def describe_foreground(self) -> str:
        window = _user32.GetForegroundWindow()
        if not window:
            return "no window"
        class_name, pid, _thread = self._identify(window)
        return f"{class_name} of process {pid}"

    @staticmethod
    def _identify(window: int) -> tuple[str, int, int]:
        """The class, the process and the thread of a window."""
        name = ctypes.create_unicode_buffer(CLASS_NAME_LENGTH)
        _user32.GetClassNameW(window, name, CLASS_NAME_LENGTH)
        pid = wintypes.DWORD()
        thread = _user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
        return name.value, int(pid.value), int(thread)


def hold_foreground(windows: ForegroundWindows, seconds: float = HOLD_SECONDS) -> bool:
    """Forbid the change of the foreground for ``seconds``; False when Windows does not allow it.

    Called just before a pseudo console starts, while this process holds the foreground. Windows
    ends the lock by itself when the user presses Alt or clicks another window.
    """
    if not windows.lock():
        logger.debug("The foreground cannot be locked: this process does not hold it")
        return False
    timer = threading.Timer(seconds, windows.unlock)
    timer.daemon = True
    timer.start()
    return True


class ForegroundWatch:
    """Decides, at each look, whether the main window must claim the foreground again.

    It looks at the window that holds the foreground, not at the activation state of the main
    window: while the console holds the foreground, ``wx`` still says the main window is active
    (measured: no activation event arrives, ``IsActive()`` stays true).
    """

    def __init__(self, windows: ForegroundWindows) -> None:
        self._windows = windows
        self._was_ours = False  # a window of this application held the foreground at the last look
        self._attempts = 0  # looks left to claim the foreground again

    def check(self, window: int) -> bool:
        """Look once; True if the foreground was given back to ``window``.

        Claiming starts when a window of this application held the foreground at the previous look
        and the console of the pseudo terminal holds it now, and goes on only while it does: a
        switch to another application is never touched.
        """
        holder = self._windows.holder()
        if holder is Holder.OWN_WINDOW:
            self._was_ours, self._attempts = True, 0
            return False
        if holder is Holder.OTHER:
            self._was_ours, self._attempts = False, 0
            return False
        if self._was_ours:
            self._was_ours, self._attempts = False, ATTEMPTS
        if not self._attempts:
            return False
        self._attempts -= 1
        # An earlier lock may still stand, and would refuse the call.
        self._windows.unlock()
        if self._windows.take_back(window):
            logger.info("The foreground was taken back from the console window")
            return True
        if not self._attempts:
            logger.warning(
                "The foreground could not be taken back; it is held by %s",
                self._windows.describe_foreground(),
            )
        return False
