"""The ``ssh.exe`` that can serve a connection: the one of Windows, and the others found here.

See "Connections" in ``specs/interface.md``. The setting ``ssh_path`` names the executable the
connections start; empty means the OpenSSH that comes with Windows, which is the only one whose
behaviour was measured (``specs/architecture/transport.md``). The others (the one of Git for
Windows, for instance) are found in the ``PATH`` and in the folders of their installers; nothing is
run to find them.
"""

import os
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path

from n5terminal.core.transport.ssh_launch import system_ssh_path


def is_valid_ssh(path: str) -> bool:
    """Is ``path`` an existing program (``.exe``) that can be started as ``ssh``?"""
    candidate = Path(path.strip().strip('"'))
    return candidate.suffix.lower() == ".exe" and candidate.is_file()


def _git_folders() -> Iterable[Path]:
    """The folders of Git for Windows that hold an ``ssh.exe``."""
    for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            yield Path(base) / "Git" / "usr" / "bin"


def installed_ssh_clients(
    which: Callable[[str], str | None] = shutil.which,
    folders: Callable[[], Iterable[Path]] = _git_folders,
    system: Callable[[], Path] = system_ssh_path,
) -> list[str]:
    """The paths of the other ``ssh.exe`` found, without the one of Windows (the default).

    First the one the ``PATH`` gives, then those of the installer folders; each is listed once, the
    case of its path ignored.
    """
    skip = str(system()).casefold()
    found: dict[str, str] = {}

    def add(executable: Path) -> None:
        key = str(executable).casefold()
        if key != skip and key not in found and executable.is_file():
            found[key] = str(executable)

    on_path = which("ssh")
    if on_path:
        add(Path(on_path))
    for folder in folders():
        add(folder / "ssh.exe")
    return list(found.values())
