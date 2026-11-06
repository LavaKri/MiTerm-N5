"""Hide or show what is typed in a one-line text field, without making another field (Windows).

A secret typed to a program (a password that ``ssh`` asks in the terminal) must not be on the
screen, and a screen reader must not read it letter by letter. The field of Windows can be turned
into a password field and back (``EM_SETPASSWORDCHAR``): its text and its caret stay, and it sets
or clears the style ``ES_PASSWORD``, which is what screen readers look at to know the field is
protected. A password field also refuses Copy, so the text cannot leave through the clipboard.
"""

import ctypes
import sys
from ctypes import wintypes

import wx

EM_SETPASSWORDCHAR = 0x00CC
GWL_STYLE = -16
ES_PASSWORD = 0x0020
MASK_CHARACTER = ord("*")

if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.SendMessageW.argtypes = (
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    _user32.SendMessageW.restype = wintypes.LPARAM
    _user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
    _user32.GetWindowLongW.restype = wintypes.LONG


def hide_text(field: wx.TextCtrl, hidden: bool) -> None:
    """Show ``*`` for each character of ``field`` when ``hidden``, else the characters."""
    if sys.platform != "win32":
        return
    _user32.SendMessageW(field.GetHandle(), EM_SETPASSWORDCHAR, MASK_CHARACTER if hidden else 0, 0)
    field.Refresh()


def is_text_hidden(field: wx.TextCtrl) -> bool:
    """Is ``field`` a password field now? (What a screen reader sees.)"""
    if sys.platform != "win32":
        return False
    return bool(_user32.GetWindowLongW(field.GetHandle(), GWL_STYLE) & ES_PASSWORD)
