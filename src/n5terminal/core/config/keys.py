"""The keys the user can send to a program (see "Sending keys" in ``specs/interface.md``).

A key is sent as the bytes a terminal keyboard sends: control characters and ``Escape`` sequences
(VT). The cursor keys, Home and End have a second form when the program put the terminal in the
"application cursor keys" mode (``application``).
"""

from dataclasses import dataclass

from n5terminal.i18n import N_

ESC = b"\x1b"

NAVIGATION = N_("Navigation")
EDITING = N_("Editing")
CONTROL = N_("Control")
FUNCTION_KEYS = N_("Function keys")


@dataclass(slots=True, frozen=True)
class SentKey:
    """A key to send: ``name`` and ``group`` are message ids."""

    id: str
    name: str
    group: str
    data: bytes
    application: bytes | None = None
    shortcut: str = ""  # the shortcut the key has by default (none for most)

    def bytes_for(self, application_cursor_keys: bool) -> bytes:
        """The bytes to write, in the form the terminal is in."""
        if application_cursor_keys and self.application is not None:
            return self.application
        return self.data


def _cursor(key_id: str, name: str, final: bytes) -> SentKey:
    return SentKey(key_id, name, NAVIGATION, ESC + b"[" + final, ESC + b"O" + final)


SENT_KEYS = (
    _cursor("up", N_("Up arrow"), b"A"),
    _cursor("down", N_("Down arrow"), b"B"),
    _cursor("right", N_("Right arrow"), b"C"),
    _cursor("left", N_("Left arrow"), b"D"),
    _cursor("home", N_("Home"), b"H"),
    _cursor("end", N_("End"), b"F"),
    SentKey("page_up", N_("Page up"), NAVIGATION, ESC + b"[5~"),
    SentKey("page_down", N_("Page down"), NAVIGATION, ESC + b"[6~"),
    SentKey("enter", N_("Enter"), EDITING, b"\r", shortcut="Shift+Enter"),
    SentKey("tab", N_("Tab"), EDITING, b"\t"),
    SentKey("shift_tab", N_("Shift+Tab"), EDITING, ESC + b"[Z"),
    SentKey("escape", N_("Escape"), EDITING, ESC, shortcut="Shift+Esc"),
    SentKey("space", N_("Space"), EDITING, b" "),
    SentKey("backspace", N_("Backspace"), EDITING, b"\x7f"),
    SentKey("delete", N_("Delete"), EDITING, ESC + b"[3~"),
    SentKey("ctrl_c", N_("Ctrl+C (interrupt)"), CONTROL, b"\x03"),
    SentKey("ctrl_d", N_("Ctrl+D (end of input)"), CONTROL, b"\x04"),
    SentKey("ctrl_z", N_("Ctrl+Z (suspend)"), CONTROL, b"\x1a"),
    SentKey("ctrl_l", N_("Ctrl+L (redraw)"), CONTROL, b"\x0c"),
    SentKey("f1", N_("F1"), FUNCTION_KEYS, ESC + b"OP"),
    SentKey("f2", N_("F2"), FUNCTION_KEYS, ESC + b"OQ"),
    SentKey("f3", N_("F3"), FUNCTION_KEYS, ESC + b"OR"),
    SentKey("f4", N_("F4"), FUNCTION_KEYS, ESC + b"OS"),
    SentKey("f5", N_("F5"), FUNCTION_KEYS, ESC + b"[15~"),
    SentKey("f6", N_("F6"), FUNCTION_KEYS, ESC + b"[17~"),
    SentKey("f7", N_("F7"), FUNCTION_KEYS, ESC + b"[18~"),
    SentKey("f8", N_("F8"), FUNCTION_KEYS, ESC + b"[19~"),
    SentKey("f9", N_("F9"), FUNCTION_KEYS, ESC + b"[20~"),
    SentKey("f10", N_("F10"), FUNCTION_KEYS, ESC + b"[21~"),
    SentKey("f11", N_("F11"), FUNCTION_KEYS, ESC + b"[23~"),
    SentKey("f12", N_("F12"), FUNCTION_KEYS, ESC + b"[24~"),
)

#: The groups in the order of the menus, each with its keys.
KEY_GROUPS: tuple[tuple[str, tuple[SentKey, ...]], ...] = tuple(
    (group, tuple(key for key in SENT_KEYS if key.group == group))
    for group in (NAVIGATION, EDITING, CONTROL, FUNCTION_KEYS)
)


def key_named(key_id: str) -> SentKey | None:
    """The key with this id (``None`` if there is none)."""
    return next((key for key in SENT_KEYS if key.id == key_id), None)
