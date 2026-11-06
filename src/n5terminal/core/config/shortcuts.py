"""Keyboard shortcuts: the configurable commands, the rules a shortcut must follow, conflicts.

A shortcut is written ``Ctrl+Shift+O``: optional modifiers (``Ctrl``, ``Alt``, ``Shift``, in this
order) then a key name. The empty string means "no shortcut".
"""

import enum
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from n5terminal.core.config.keys import SENT_KEYS
from n5terminal.i18n import N_

_MODIFIER_ORDER = ("Ctrl", "Alt", "Shift")
_NAMED_KEYS = (
    "Enter",
    "Space",
    "Tab",
    "Esc",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "Up",
    "Down",
    "Left",
    "Right",
    "Delete",
    "Insert",
    "Backspace",
    "Pause",
)
_FUNCTION_KEY = re.compile(r"F([1-9]|1[0-2])")
_LETTER_OR_DIGIT = re.compile(r"[A-Z0-9]")

#: Keys that are never allowed: they move the focus or close dialogs, and Insert is the modifier
#: key of screen readers.
_RESERVED_KEYS = frozenset({"Tab", "Insert"})  # Esc too, except with Shift alone

#: Shortcuts of the standard commands, which cannot be changed or reused. Ctrl+C stays "copy" in
#: the command field: stopping a program has a shortcut of its own.
FIXED_SHORTCUTS = frozenset(
    {
        "Ctrl+Q",
        "Alt+F4",
        "Ctrl+Z",
        "Ctrl+Y",
        "Ctrl+X",
        "Ctrl+C",
        "Ctrl+V",
        "Ctrl+A",
        "Ctrl+Tab",
        "Ctrl+Shift+Tab",
        "Ctrl+PageUp",
        "Ctrl+PageDown",
        "F10",  # activates the menu bar
        "Shift+F10",  # opens the context menu
        # Access keys of the menu bar (French and English): Fichier/File, Session, Édition/Edit,
        # Terminal, Develop and Aide (Ai&de)/Help.
        "Alt+F",
        "Alt+S",
        "Alt+E",
        "Alt+T",
        "Alt+D",
        "Alt+H",
    }
)


MAIN_GROUP = N_("Main")
KEYS_GROUP = N_("Key sending")
SEND_FORMAT = N_("Send {key}")


@dataclass(slots=True, frozen=True)
class ConfigurableCommand:
    """A command whose shortcut the user can change; ``label`` is a message id.

    ``group`` (a message id) sorts the commands in the Shortcuts page. A command that sends a key
    has the name of that key in ``key_name``: its text is then "Send" and the key.
    """

    id: str
    label: str
    default: str = ""
    group: str = MAIN_GROUP
    key_name: str = ""

    def text(self, translate: Callable[[str], str]) -> str:
        """The name of the command to show or read, in the language of ``translate``."""
        if self.key_name:
            return translate(SEND_FORMAT).format(key=translate(self.key_name))
        return translate(self.label)


NEW_SESSION_COMMAND = ConfigurableCommand("session.new", N_("New session"), "Ctrl+N")
CHOOSE_FOLDER_COMMAND = ConfigurableCommand("folder.choose", N_("Working folder"), "Ctrl+O")
EXPORT_COMMAND = ConfigurableCommand("output.export", N_("Export the output"), "Ctrl+S")
STOP_COMMAND = ConfigurableCommand("program.stop", N_("Stop the program"), "Ctrl+Pause")
RESEND_COMMAND = ConfigurableCommand(
    "program.relaunch", N_("Resend the last command"), "Ctrl+R"
)  # the id is the one older settings files know
CLEAR_COMMAND = ConfigurableCommand("output.clear", N_("Clear the output"), "Ctrl+L")
HISTORY_COMMAND = ConfigurableCommand("history.show", N_("Command history"), "Ctrl+Space")
FIND_COMMAND = ConfigurableCommand("search.find", N_("Find in the output"), "Ctrl+F")
FIND_NEXT_COMMAND = ConfigurableCommand("search.next", N_("Find next"), "F3")
FIND_PREVIOUS_COMMAND = ConfigurableCommand("search.previous", N_("Find previous"), "Shift+F3")
TERMINAL_CURSOR_COMMAND = ConfigurableCommand(
    "display.terminal_cursor", N_("Go to the cursor of the terminal"), "Ctrl+G"
)
# Ctrl+Home and Ctrl+End stay those of the text control (start and end of the whole text).
EMULATOR_START_COMMAND = ConfigurableCommand(
    "display.emulator_start", N_("Go to the first line of the terminal"), "Alt+Home"
)
EMULATOR_END_COMMAND = ConfigurableCommand(
    "display.emulator_end", N_("Go to the last line of the terminal"), "Alt+End"
)
READ_LINE_COMMAND = ConfigurableCommand(
    "activity.read_line", N_("Read the line with formatting"), "F4"
)
IDENTIFY_COMMAND = ConfigurableCommand("activity.identify", N_("Identify activities"), "Shift+F4")
SIGNAL_COMMAND = ConfigurableCommand("activity.signal", N_("Signal activities"), "Ctrl+B")
HELP_COMMAND = ConfigurableCommand("help.open", N_("Open the help"), "F1")
LAUNCH_PROGRAM_COMMAND = ConfigurableCommand(
    "profile.launch", N_("Launch the program of the profile"), "F5"
)
MULTILINE_COMMAND = ConfigurableCommand("input.multiline", N_("Multi-line input"), "Ctrl+M")
COMFORT_PREVIOUS_COMMAND = ConfigurableCommand(
    "output.comfort_previous", N_("Previous line, with filtering"), "Ctrl+Alt+Up"
)
COMFORT_NEXT_COMMAND = ConfigurableCommand(
    "output.comfort_next", N_("Next line, with filtering"), "Ctrl+Alt+Down"
)
# F5 launches the program of the profile, F6 connects and F7 disconnects (Stop, Ctrl+Pause, also
# does); with Shift, F5 chooses the free profile and F6 the local connection.
CONNECT_COMMAND = ConfigurableCommand("connection.connect", N_("Connect"), "F6")
DISCONNECT_COMMAND = ConfigurableCommand("connection.disconnect", N_("Disconnect"), "F7")
FREE_PROFILE_COMMAND = ConfigurableCommand(
    "profile.free", N_("Choose the free profile"), "Shift+F5"
)
LOCAL_CONNECTION_COMMAND = ConfigurableCommand(
    "connection.local", N_("Choose the local connection"), "Shift+F6"
)
DEFINE_VARIABLES_COMMAND = ConfigurableCommand(
    "profile.variables", N_("Define the variables"), "Ctrl+D"
)
SESSION_INFO_COMMAND = ConfigurableCommand("session.info", N_("Session information"), "Ctrl+I")

#: One command per key that can be sent; only Escape and Enter have a shortcut by default.
KEY_COMMANDS = tuple(
    ConfigurableCommand(
        f"key.{key.id}", key.name, key.shortcut, group=KEYS_GROUP, key_name=key.name
    )
    for key in SENT_KEYS
)

#: Every configurable command, in the order of the Shortcuts list.
CONFIGURABLE_COMMANDS = (
    NEW_SESSION_COMMAND,
    CHOOSE_FOLDER_COMMAND,
    EXPORT_COMMAND,
    STOP_COMMAND,
    RESEND_COMMAND,
    MULTILINE_COMMAND,
    CLEAR_COMMAND,
    HISTORY_COMMAND,
    FIND_COMMAND,
    FIND_NEXT_COMMAND,
    FIND_PREVIOUS_COMMAND,
    TERMINAL_CURSOR_COMMAND,
    EMULATOR_START_COMMAND,
    EMULATOR_END_COMMAND,
    READ_LINE_COMMAND,
    IDENTIFY_COMMAND,
    SIGNAL_COMMAND,
    COMFORT_PREVIOUS_COMMAND,
    COMFORT_NEXT_COMMAND,
    HELP_COMMAND,
    LAUNCH_PROGRAM_COMMAND,
    FREE_PROFILE_COMMAND,
    DEFINE_VARIABLES_COMMAND,
    CONNECT_COMMAND,
    DISCONNECT_COMMAND,
    LOCAL_CONNECTION_COMMAND,
    SESSION_INFO_COMMAND,
    *KEY_COMMANDS,
)


class ShortcutProblem(enum.Enum):
    """Why a shortcut is refused."""

    INVALID = "invalid"
    RESERVED = "reserved"
    FIXED = "fixed"
    TAKEN = "taken"


@dataclass(slots=True, frozen=True)
class ShortcutCheck:
    """Outcome of ``check_shortcut``: no problem, or the problem and what it collides with."""

    problem: ShortcutProblem | None = None
    other: ConfigurableCommand | None = None  # the command already using it (TAKEN)


#: The names of the modifier keys and of the named keys as the user hears them. The shortcuts are
#: stored and compared in the English spelling (``Alt+Home``); a French voice reads "Home" as
#: "dossier personnel", so what is shown or read is written with these names (``Alt+Début``).
_KEY_NAMES = {
    "Ctrl": N_("Ctrl"),
    "Alt": N_("Alt"),
    "Shift": N_("Shift"),
    "Enter": N_("Enter"),
    "Space": N_("Space"),
    "Tab": N_("Tab"),
    "Esc": N_("Esc"),
    "Home": N_("Home"),
    "End": N_("End"),
    "PageUp": N_("PageUp"),
    "PageDown": N_("PageDown"),
    "Up": N_("Up"),
    "Down": N_("Down"),
    "Left": N_("Left"),
    "Right": N_("Right"),
    "Delete": N_("Delete"),
    "Insert": N_("Insert"),
    "Backspace": N_("Backspace"),
    "Pause": N_("Pause"),
}


#: The names wxWidgets reads and writes in a menu accelerator, by our name for the key: its message
#: ids in the context "keyboard key" (``accelcmn.cpp``), some keys having two. The catalog
#: ``wxkeys`` gives them the translations of ``_KEY_NAMES``, so that a menu reads and writes
#: ``Maj+Entrée`` as this application says it, not ``Majuscule+Entrée`` (``tools/make_wx_keys.py``).
WX_KEY_IDS: dict[str, str] = {
    "Ctrl": "Ctrl",
    "Alt": "Alt",
    "Shift": "Shift",
    "Enter": "Enter",
    "Space": "Space",
    "Tab": "Tab",
    "Esc": "Esc",
    "Home": "Home",
    "End": "End",
    "PageUp": "PageUp",
    "Page Up": "PageUp",
    "PageDown": "PageDown",
    "Page Down": "PageDown",
    "Up": "Up",
    "Down": "Down",
    "Left": "Left",
    "Right": "Right",
    "Delete": "Delete",
    "Insert": "Insert",
    "Backspace": "Backspace",
    "Back": "Backspace",
    "Pause": "Pause",
}


def display_shortcut(shortcut: str, translate: Callable[[str], str]) -> str:
    """``shortcut`` with each key name in the language of ``translate`` (letters stay the same)."""
    return "+".join(
        translate(_KEY_NAMES[part]) if part in _KEY_NAMES else part for part in shortcut.split("+")
    )


def normalize_shortcut(text: str) -> str | None:
    """Canonical spelling of ``text`` (``ctrl + shift + o`` -> ``Ctrl+Shift+O``), None if invalid.

    The empty string is valid and stands for "no shortcut".
    """
    text = text.strip()
    if not text:
        return ""
    parts = [part.strip() for part in text.split("+")]
    if "" in parts:
        return None
    *modifiers, key = parts
    names = {name.lower(): name for name in _MODIFIER_ORDER}
    chosen = set()
    for modifier in modifiers:
        name = names.get(modifier.lower())
        if name is None or name in chosen:
            return None
        chosen.add(name)
    normalized_key = _normalize_key(key)
    if normalized_key is None:
        return None
    ordered = [name for name in _MODIFIER_ORDER if name in chosen]
    return "+".join([*ordered, normalized_key])


def _normalize_key(key: str) -> str | None:
    upper = key.upper()
    if _FUNCTION_KEY.fullmatch(upper) or _LETTER_OR_DIGIT.fullmatch(upper):
        return upper
    for name in _NAMED_KEYS:
        if name.lower() == key.lower():
            return name
    return None


def _is_reserved(modifiers: list[str], key: str) -> bool:
    """Is the key, with these modifiers, one a shortcut may never be?"""
    if key == "Esc":
        return modifiers != ["Shift"]  # Shift+Esc closes nothing: it is the shortcut of Escape
    if key in _RESERVED_KEYS:
        return True
    if key == "Enter":
        return not modifiers
    return not _FUNCTION_KEY.fullmatch(key) and not {"Ctrl", "Alt"} & set(modifiers)


def check_shortcut(
    command: ConfigurableCommand, shortcut: str, current: Mapping[str, str]
) -> ShortcutCheck:
    """Can ``command`` use ``shortcut``? ``current`` maps command ids to their shortcut.

    Rules: it must be well formed; a function key (F1 to F12) is allowed alone or with any
    modifiers; Enter needs at least one modifier (alone it sends the command); any other key
    needs Ctrl, Alt or both (Shift may be added; a plain letter would block typing); Tab, Esc
    (except Shift+Esc) and Insert are never allowed; it must not be the shortcut of a standard
    command or the access key of a menu, nor of another configurable command.
    """
    normalized = normalize_shortcut(shortcut)
    if normalized is None:
        return ShortcutCheck(ShortcutProblem.INVALID)
    if not normalized:
        return ShortcutCheck()
    *modifiers, key = normalized.split("+")
    if _is_reserved(modifiers, key):
        return ShortcutCheck(ShortcutProblem.RESERVED)
    if normalized in FIXED_SHORTCUTS:
        return ShortcutCheck(ShortcutProblem.FIXED)
    for other in CONFIGURABLE_COMMANDS:
        if other.id != command.id and current.get(other.id, other.default) == normalized:
            return ShortcutCheck(ShortcutProblem.TAKEN, other)
    return ShortcutCheck()
