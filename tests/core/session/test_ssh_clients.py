"""The ``ssh.exe`` found on the computer, besides the one of Windows."""

from collections.abc import Iterable
from pathlib import Path

import pytest

from n5terminal.core.session.ssh_clients import installed_ssh_clients, is_valid_ssh

pytestmark = pytest.mark.unit


def make(tmp_path: Path, *names: str) -> list[Path]:
    made = []
    for name in names:
        path = tmp_path / name / "ssh.exe"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        made.append(path)
    return made


def found(
    tmp_path: Path,
    on_path: str | None = None,
    folders: Iterable[Path] = (),
    system: Path | None = None,
) -> list[str]:

    def which(_name: str) -> str | None:
        return on_path

    def system_ssh() -> Path:
        return system or tmp_path / "windows.exe"

    return installed_ssh_clients(which, lambda: folders, system_ssh)


def test_nothing_found_is_an_empty_list(tmp_path: Path) -> None:
    assert found(tmp_path) == []


def test_the_one_of_the_path_comes_first_then_those_of_the_folders(tmp_path: Path) -> None:
    git, other = make(tmp_path, "git", "other")
    assert found(tmp_path, on_path=str(git), folders=[other.parent]) == [str(git), str(other)]


def test_an_ssh_is_listed_once_whatever_the_case_of_its_path(tmp_path: Path) -> None:
    (git,) = make(tmp_path, "git")
    assert found(tmp_path, on_path=str(git).upper(), folders=[git.parent]) == [str(git).upper()]


def test_the_ssh_of_windows_is_the_default_not_one_of_the_others(tmp_path: Path) -> None:
    (windows,) = make(tmp_path, "windows")
    assert found(tmp_path, on_path=str(windows), folders=[windows.parent], system=windows) == []


def test_a_folder_without_ssh_or_a_path_that_does_not_exist_gives_nothing(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert found(tmp_path, on_path=str(tmp_path / "gone" / "ssh.exe"), folders=[empty]) == []


def test_a_valid_ssh_is_an_existing_exe(tmp_path: Path) -> None:
    (git,) = make(tmp_path, "git")
    assert is_valid_ssh(str(git))
    assert is_valid_ssh(f'  "{git}" ')
    assert not is_valid_ssh(str(tmp_path / "gone" / "ssh.exe"))
    assert not is_valid_ssh(str(git.parent))
    (tmp_path / "ssh.txt").write_text("", encoding="utf-8")
    assert not is_valid_ssh(str(tmp_path / "ssh.txt"))
