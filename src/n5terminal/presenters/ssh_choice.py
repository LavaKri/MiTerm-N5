"""The draft of the dialog "OpenSSH client": which ``ssh.exe`` the connections start.

See "Connections" in ``specs/interface.md``. The list holds the OpenSSH of Windows (the default, no
path stored), every other ``ssh.exe`` found on the computer, and "Other…", which asks for a path.
The dialog edits this draft; ``chosen_path`` is what to store once it is accepted. It always says
which one is used, and that only the OpenSSH of Windows was tried.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from n5terminal.core.session.ssh_clients import is_valid_ssh
from n5terminal.core.transport.ssh_launch import system_ssh_path
from n5terminal.i18n import N_
from n5terminal.presenters.choices import Translate

_DEFAULT = N_("OpenSSH of Windows (default, {path})")
_OTHER_FOUND = N_("{path} (not tried)")
_OTHER = N_("Other…")
INVALID = N_("Select a valid ssh.exe.")
NOTE = N_(
    "Only the OpenSSH of Windows was tried with MiTerm-N5: the others may behave differently."
)


@dataclass(slots=True, frozen=True)
class SshOption:
    """A line of the list: the path it stands for (``None``: the one typed) and its text."""

    path: str | None
    label: str


class SshChoice:
    """The options, the one selected and the path typed for "Other…"."""

    def __init__(
        self,
        current: str,
        installs: Sequence[str],
        translate: Translate,
        is_valid: Callable[[str], bool] = is_valid_ssh,
    ) -> None:
        self._translate = translate
        self._is_valid = is_valid
        current = current.strip()
        self.options = [
            SshOption("", translate(_DEFAULT).format(path=system_ssh_path())),
            *(SshOption(path, translate(_OTHER_FOUND).format(path=path)) for path in installs),
            SshOption(None, translate(_OTHER)),
        ]
        paths = [
            option.path.casefold() if option.path is not None else None for option in self.options
        ]
        self.selected = paths.index(current.casefold()) if current.casefold() in paths else -1
        self.custom_path = ""
        if self.selected < 0:  # a path the user typed: "Other…" shows it
            self.selected = len(self.options) - 1
            self.custom_path = current

    @property
    def labels(self) -> list[str]:
        return [option.label for option in self.options]

    @property
    def note(self) -> str:
        """What the dialog says about the choice."""
        return self._translate(NOTE)

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
        """The path to store: empty for the OpenSSH of Windows."""
        path = self.options[self.selected].path
        return self.custom_path.strip().strip('"') if path is None else path

    def name(self) -> str:
        """The choice as it is said."""
        return self.chosen_path() or str(system_ssh_path())
