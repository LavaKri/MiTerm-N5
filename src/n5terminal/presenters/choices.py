"""The lists of choices the dialogs offer: mode, interpreter, terminal size.

Each choice is a (value stored in the file, label) pair; the labels are translated by the caller.
The profile dialog is the one that offers them. A shell that stays open is always served as a TUI,
so the mode is not offered while an interpreter is chosen.
"""

from collections.abc import Callable

from n5terminal.core.config.settings import AUTOMATIC_SIZE, INTERPRETERS, LAUNCH_MODES
from n5terminal.core.screen.terminal_size import STANDARD_SIZES, size_text
from n5terminal.i18n import N_

Translate = Callable[[str], str]
Choices = list[tuple[str, str]]  # (value stored in the file, label)

_MODE_LABELS = {"cli": N_("CLI, plain text"), "tui": N_("TUI, interactive terminal")}
_INTERPRETER_LABELS = {"none": N_("None"), "cmd": "Cmd", "powershell": "PowerShell"}
_SIZE_FORMAT = N_("{columns} x {rows}")
_AUTOMATIC = N_("Automatic")


def mode_choices(translate: Translate) -> Choices:
    """CLI and TUI, as the profile dialog offers them."""
    return [(mode, translate(_MODE_LABELS[mode])) for mode in LAUNCH_MODES]


def interpreter_choices(translate: Translate) -> Choices:
    return [(name, translate(_INTERPRETER_LABELS[name])) for name in INTERPRETERS]


def size_choices(translate: Translate) -> Choices:
    """The standard sizes, then the automatic one."""
    sizes = [
        (size_text(size), translate(_SIZE_FORMAT).format(columns=size.columns, rows=size.rows))
        for size in STANDARD_SIZES
    ]
    return [*sizes, (AUTOMATIC_SIZE, translate(_AUTOMATIC))]
