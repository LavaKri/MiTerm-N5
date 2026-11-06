"""The draft of the dialog "PowerShell selection": which PowerShell the interpreter starts.

See "Interpreter" in ``specs/interface.md``. The list holds Windows PowerShell (the default, no
path stored), every PowerShell 7 or later found on the computer, and "Other…", which asks for a
path. The dialog edits this draft; ``chosen_path`` is what to store once it is accepted.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from n5terminal.core.session.powershells import (
    PowerShellInstall,
    is_valid_powershell,
    powershell_name,
)
from n5terminal.i18n import N_
from n5terminal.presenters.choices import Translate

_DEFAULT = N_("Windows PowerShell")
_INSTALLED = N_("PowerShell {version} ({path})")
_INSTALLED_NO_VERSION = N_("PowerShell ({path})")
_OTHER = N_("Other…")
INVALID = N_("Select a valid PowerShell.")


@dataclass(slots=True, frozen=True)
class PowerShellOption:
    """A line of the list: the path it stands for (``None``: the one typed) and its text."""

    path: str | None
    label: str


class PowerShellChoice:
    """The options, the one selected and the path typed for "Other…"."""

    def __init__(
        self,
        current: str,
        installs: Sequence[PowerShellInstall],
        translate: Translate,
        is_valid: Callable[[str], bool] = is_valid_powershell,
    ) -> None:
        self._translate = translate
        self._is_valid = is_valid
        current = current.strip()
        self.options = [
            PowerShellOption("", translate(_DEFAULT)),
            *(PowerShellOption(install.path, self._label(install)) for install in installs),
            PowerShellOption(None, translate(_OTHER)),
        ]
        known = [option.path for option in self.options]
        paths = [path.casefold() if path is not None else None for path in known]
        self.selected = paths.index(current.casefold()) if current.casefold() in paths else -1
        self.custom_path = ""
        if self.selected < 0:  # a path the user typed: "Other…" shows it
            self.selected = len(self.options) - 1
            self.custom_path = current

    def _label(self, install: PowerShellInstall) -> str:
        if install.version:
            return self._translate(_INSTALLED).format(version=install.version, path=install.path)
        return self._translate(_INSTALLED_NO_VERSION).format(path=install.path)

    @property
    def labels(self) -> list[str]:
        return [option.label for option in self.options]

    @property
    def path_enabled(self) -> bool:
        """The path is typed only for "Other…"."""
        return self.options[self.selected].path is None

    def problem(self) -> str | None:
        """Why the choice is refused, in words; ``None`` if it is fine."""
        if self.path_enabled and not self._is_valid(self.custom_path):
            return self._translate(INVALID)
        return None

    def chosen_path(self) -> str:
        """The path to store: empty for Windows PowerShell."""
        path = self.options[self.selected].path
        return self.custom_path.strip().strip('"') if path is None else path

    def name(self) -> str:
        """The choice as it is said."""
        return powershell_name(self.chosen_path())
