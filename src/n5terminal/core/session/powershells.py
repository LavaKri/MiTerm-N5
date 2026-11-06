"""The PowerShells installed on this computer, and the check of a path chosen by the user.

See "Interpreter" in ``specs/interface.md``. The setting ``powershell_path`` names the executable
the interpreter "PowerShell" starts; empty means Windows PowerShell (``powershell.exe``, the one
that comes with Windows). The others are PowerShell 7 and later (``pwsh.exe``), found in the
``PATH`` and in the folders of its installers; nothing is run to find them.
"""

import os
import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

WINDOWS_POWERSHELL_NAME = "Windows PowerShell"


def powershell_name(path: str) -> str:
    """How the PowerShell of ``path`` is said (``path`` itself, or Windows PowerShell for none)."""
    return path.strip() or WINDOWS_POWERSHELL_NAME


@dataclass(slots=True, frozen=True)
class PowerShellInstall:
    """A PowerShell found: its executable, and its version when the folder says it ("7")."""

    path: str
    version: str = ""


def is_valid_powershell(path: str) -> bool:
    """Is ``path`` an existing program (``.exe``) that can be started as a PowerShell?"""
    candidate = Path(path.strip().strip('"'))
    return candidate.suffix.lower() == ".exe" and candidate.is_file()


def _program_folders() -> Iterable[Path]:
    """The folders where PowerShell 7 and later install themselves (one subfolder per version)."""
    for variable in ("ProgramFiles", "ProgramW6432"):
        base = os.environ.get(variable)
        if base:
            yield Path(base) / "PowerShell"


def _version_of(executable: Path) -> str:
    """The version a folder name gives (``...\\PowerShell\\7\\pwsh.exe`` is "7"), else empty."""
    name = executable.parent.name
    return name if name[:1].isdigit() else ""


def installed_powershells(
    which: Callable[[str], str | None] = shutil.which,
    folders: Callable[[], Iterable[Path]] = _program_folders,
) -> list[PowerShellInstall]:
    """The PowerShell 7 and later found, without Windows PowerShell (that is the default).

    First the one the ``PATH`` gives (the Microsoft Store has its own there), then those of the
    installer folders; each executable is listed once, the case of its path ignored.
    """
    found: dict[str, PowerShellInstall] = {}

    def add(executable: Path) -> None:
        key = str(executable).lower()
        if key not in found and executable.is_file():
            found[key] = PowerShellInstall(str(executable), _version_of(executable))

    on_path = which("pwsh")
    if on_path:
        add(Path(on_path))
    for folder in folders():
        if folder.is_dir():
            for executable in sorted(folder.glob("*/pwsh.exe")):
                add(executable)
    return list(found.values())
