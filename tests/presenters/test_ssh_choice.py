"""The draft of the dialog "OpenSSH client"."""

from pathlib import Path

import pytest

from n5terminal.core.transport.ssh_launch import system_ssh_path
from n5terminal.presenters.ssh_choice import SshChoice

pytestmark = pytest.mark.unit

GIT = r"C:\Program Files\Git\usr\bin\ssh.exe"
SYSTEM = str(system_ssh_path())


def same(text: str) -> str:
    return text


def choice(current: str = "", installs: tuple[str, ...] = (GIT,), valid: bool = True) -> SshChoice:
    return SshChoice(current, installs, same, lambda _path: valid)


def test_the_list_starts_with_the_ssh_of_windows_that_says_its_path() -> None:
    draft = choice()
    assert draft.labels[0] == f"OpenSSH of Windows (default, {SYSTEM})"
    assert draft.selected == 0
    assert draft.chosen_path() == ""  # nothing is stored for the default


def test_the_others_found_are_listed_as_not_tried_then_other() -> None:
    draft = choice()
    assert draft.labels[1:] == [f"{GIT} (not tried)", "Other…"]


def test_the_dialog_says_that_only_the_ssh_of_windows_was_tried() -> None:
    assert choice().note.startswith("Only the OpenSSH of Windows was tried")


def test_a_stored_path_that_is_listed_is_selected_whatever_its_case() -> None:
    draft = choice(GIT.upper())
    assert draft.selected == 1
    assert draft.chosen_path() == GIT


def test_a_stored_path_that_is_not_listed_opens_on_other_with_the_path() -> None:
    draft = choice(r"D:\tools\ssh.exe")
    assert draft.labels[draft.selected] == "Other…"
    assert (draft.custom_path, draft.path_enabled) == (r"D:\tools\ssh.exe", True)
    assert draft.chosen_path() == r"D:\tools\ssh.exe"


def test_the_path_typed_is_stripped_of_blanks_and_quotes() -> None:
    draft = choice(r"D:\tools\ssh.exe")
    draft.custom_path = '  "D:\\other dir\\ssh.exe" '
    assert draft.chosen_path() == r"D:\other dir\ssh.exe"


def test_other_with_a_path_that_is_not_an_ssh_is_refused_with_a_reason() -> None:
    draft = choice(r"D:\nothing", valid=False)
    assert draft.problem() == "Select a valid ssh.exe."


def test_the_listed_choices_need_no_check_and_the_path_is_greyed() -> None:
    draft = choice(valid=False)
    assert draft.problem() is None
    assert not draft.path_enabled


def test_the_choice_is_said_by_its_path_or_by_the_one_of_windows() -> None:
    assert choice().name() == SYSTEM
    assert choice(GIT).name() == GIT


def test_the_default_check_accepts_an_existing_exe_only(tmp_path: Path) -> None:
    exe = tmp_path / "ssh.exe"
    exe.write_text("", encoding="utf-8")
    other = tmp_path / "ssh.txt"
    other.write_text("", encoding="utf-8")
    draft = SshChoice(str(other), [], same)
    assert draft.problem() == "Select a valid ssh.exe."
    assert SshChoice(str(exe), [], same).problem() is None
