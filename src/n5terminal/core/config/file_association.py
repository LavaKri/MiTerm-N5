"""Opening the launch files (``.n5term``) with MiTerm-N5, by a double click.

See "Launch file" in ``specs/interface.md``. The association is written for the current Windows user
only (``HKEY_CURRENT_USER\\Software\\Classes``): no administrator rights, and removing it removes
everything this module wrote. It is done on a user's request, never by itself, and not in portable
mode, which must leave nothing on the computer.
"""

import ctypes
import sys
import winreg
from pathlib import Path
from typing import Protocol

from n5terminal.core.config.launch_file import LAUNCH_FILE_EXTENSION
from n5terminal.core.config.packaged import is_packaged
from n5terminal.core.errors import AssociationError

PROG_ID = "MiTermN5.LaunchFile"
DESCRIPTION = "MiTerm-N5 launch file"
_CLASSES = r"Software\Classes"
_SHCNE_ASSOCCHANGED = 0x08000000


class Registry(Protocol):
    """The part of the Windows registry the association needs (under ``Software\\Classes``)."""

    def read(self, key: str) -> str | None:
        """The default value of ``key``, ``None`` if there is none."""
        ...

    def write(self, key: str, value: str) -> None:
        """Set the default value of ``key``, creating it."""
        ...

    def delete(self, key: str) -> None:
        """Remove ``key`` and everything under it (nothing happens if it is not there)."""
        ...

    def changed(self) -> None:
        """Tell Windows the associations changed, so that Explorer shows it at once."""
        ...


class WinRegistry:
    """:class:`Registry` on the real registry of the current user."""

    def read(self, key: str) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{_CLASSES}\\{key}") as handle:
                value, _kind = winreg.QueryValueEx(handle, "")
        except FileNotFoundError:
            return None
        return str(value)

    def write(self, key: str, value: str) -> None:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{_CLASSES}\\{key}") as handle:
            winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, value)

    def delete(self, key: str) -> None:
        path = f"{_CLASSES}\\{key}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as handle:
                while True:
                    try:
                        child = winreg.EnumKey(handle, 0)
                    except OSError:  # no more sub-key
                        break
                    self.delete(f"{key}\\{child}")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            return

    def changed(self) -> None:
        ctypes.windll.shell32.SHChangeNotify(_SHCNE_ASSOCCHANGED, 0, None, None)


def open_command(executable: str | None = None, frozen: bool | None = None) -> str:
    """The command line Windows runs for a launch file: the program, then the file (``%1``).

    The executable itself when packaged; ``pythonw -m n5terminal`` (no console window) otherwise.
    """
    program = executable or sys.executable
    if frozen if frozen is not None else is_packaged():
        return f'"{program}" "%1"'
    windowless = Path(program).with_name("pythonw.exe")
    return f'"{windowless if windowless.exists() else program}" -m n5terminal "%1"'


class FileAssociation:
    """Associate or dissociate the launch files, on ``registry``, with ``command``."""

    def __init__(self, registry: Registry, command: str) -> None:
        self._registry = registry
        self._command = command

    @property
    def _command_key(self) -> str:
        return f"{PROG_ID}\\shell\\open\\command"

    def is_associated(self) -> bool:
        """Do launch files open with this program (and exactly this command line)?"""
        registry = self._registry
        return (
            registry.read(LAUNCH_FILE_EXTENSION) == PROG_ID
            and registry.read(self._command_key) == self._command
        )

    def associate(self) -> None:
        """Make launch files open with MiTerm-N5. Raises ``AssociationError``."""
        try:
            self._registry.write(LAUNCH_FILE_EXTENSION, PROG_ID)
            self._registry.write(PROG_ID, DESCRIPTION)
            self._registry.write(self._command_key, self._command)
            self._registry.changed()
        except OSError as error:
            raise AssociationError(str(error)) from error

    def dissociate(self) -> None:
        """Remove the association, if it is ours; another program's is left alone."""
        try:
            if self._registry.read(LAUNCH_FILE_EXTENSION) == PROG_ID:
                self._registry.delete(LAUNCH_FILE_EXTENSION)
            self._registry.delete(PROG_ID)
            self._registry.changed()
        except OSError as error:
            raise AssociationError(str(error)) from error
