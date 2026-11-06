from pathlib import Path

import pytest

from n5terminal.core.session.powershells import (
    PowerShellInstall,
    installed_powershells,
    is_valid_powershell,
    powershell_name,
)

pytestmark = pytest.mark.unit


def _exe(folder: Path, *parts: str) -> Path:
    path = folder.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_a_path_is_valid_when_it_is_an_existing_exe(tmp_path: Path) -> None:
    program = _exe(tmp_path, "pwsh.exe")
    assert is_valid_powershell(str(program))
    assert is_valid_powershell(f'  "{program}" ')
    assert not is_valid_powershell(str(tmp_path / "missing.exe"))
    assert not is_valid_powershell(str(_exe(tmp_path, "tool.cmd")))
    assert not is_valid_powershell(str(tmp_path))
    assert not is_valid_powershell("")


def test_the_pwsh_of_the_path_is_found(tmp_path: Path) -> None:
    program = _exe(tmp_path, "WindowsApps", "pwsh.exe")
    found = installed_powershells(lambda name: str(program), lambda: [])
    assert found == [PowerShellInstall(str(program), "")]


def test_the_installer_folders_give_one_entry_per_version(tmp_path: Path) -> None:
    seven = _exe(tmp_path, "PowerShell", "7", "pwsh.exe")
    preview = _exe(tmp_path, "PowerShell", "7-preview", "pwsh.exe")
    _exe(tmp_path, "PowerShell", "Modules", "other.exe")
    found = installed_powershells(lambda name: None, lambda: [tmp_path / "PowerShell"])
    assert found == [
        PowerShellInstall(str(seven), "7"),
        PowerShellInstall(str(preview), "7-preview"),
    ]


def test_an_executable_found_twice_is_listed_once_whatever_the_case(tmp_path: Path) -> None:
    seven = _exe(tmp_path, "PowerShell", "7", "pwsh.exe")
    found = installed_powershells(
        lambda name: str(seven).upper(), lambda: [tmp_path / "PowerShell"]
    )
    assert len(found) == 1


def test_a_path_that_does_not_exist_or_a_missing_folder_gives_nothing(tmp_path: Path) -> None:
    found = installed_powershells(
        lambda name: str(tmp_path / "gone" / "pwsh.exe"), lambda: [tmp_path / "none"]
    )
    assert found == []


def test_no_path_is_said_as_windows_powershell() -> None:
    assert powershell_name("") == "Windows PowerShell"
    assert powershell_name(r" C:\PS\pwsh.exe ") == r"C:\PS\pwsh.exe"
