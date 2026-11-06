from pathlib import Path

import pytest

from n5terminal.core.config.announcements import Announce, AnnouncementCenter
from n5terminal.core.errors import (
    InputQueueFullError,
    LaunchError,
    ProgramNotFoundError,
    TransportError,
    WorkingFolderError,
)
from n5terminal.core.screen.terminal_size import DEFAULT_SIZE
from n5terminal.core.session.session_state import Interpreter, SessionState
from n5terminal.presenters.session_run import LaunchRequest, launch_failure

pytestmark = pytest.mark.unit

FOLDER = Path("C:/work")


def request(
    interpreter: Interpreter = Interpreter.NONE, powershell_path: str = ""
) -> LaunchRequest:
    return LaunchRequest(
        "git status",
        SessionState(interpreter=interpreter),
        FOLDER,
        DEFAULT_SIZE,
        powershell_path=powershell_path,
    )


def test_a_program_not_found_is_told_by_its_name() -> None:
    failure = launch_failure(ProgramNotFoundError("git"), request(), "git", is_shell=False)
    assert failure == (Announce.PROGRAM_NOT_FOUND, {"program": "git"})


def test_a_powershell_the_user_chose_and_not_found_is_told_by_its_path() -> None:
    chosen = request(Interpreter.POWERSHELL, "C:/ps7/pwsh.exe")
    failure = launch_failure(ProgramNotFoundError("pwsh"), chosen, "pwsh.exe", is_shell=True)
    assert failure == (Announce.POWERSHELL_NOT_FOUND, {"path": "C:/ps7/pwsh.exe"})


def test_windows_powershell_not_found_is_told_as_a_program() -> None:
    default = request(Interpreter.POWERSHELL)
    failure = launch_failure(ProgramNotFoundError("x"), default, "powershell.exe", is_shell=True)
    assert failure == (Announce.PROGRAM_NOT_FOUND, {"program": "powershell.exe"})


def test_a_chosen_powershell_does_not_hide_a_program_not_found_without_a_shell() -> None:
    chosen = request(Interpreter.POWERSHELL, "C:/ps7/pwsh.exe")
    failure = launch_failure(ProgramNotFoundError("x"), chosen, "git", is_shell=False)
    assert failure == (Announce.PROGRAM_NOT_FOUND, {"program": "git"})


def test_a_missing_working_folder_is_told_by_its_path() -> None:
    failure = launch_failure(WorkingFolderError("git", "C:/work"), request(), "git", is_shell=False)
    assert failure == (Announce.FOLDER_NOT_FOUND, {"folder": FOLDER})


@pytest.mark.parametrize("error", [LaunchError("boom"), InputQueueFullError("full")])
def test_any_other_failure_is_a_plain_failure_to_launch(error: TransportError) -> None:
    failure = launch_failure(error, request(), "git", is_shell=False)
    assert failure == (Announce.LAUNCH_FAILED, {"program": "git"})


# These announcements are said through a variable, so ``test_announcement_calls.py`` cannot check
# their values in the code: here each one fills its text, or the missing value raises a KeyError.
@pytest.mark.parametrize(
    ("error", "chosen", "is_shell", "said"),
    [
        (ProgramNotFoundError("git"), request(), False, "Program not found: git."),
        (
            ProgramNotFoundError("pwsh"),
            request(Interpreter.POWERSHELL, "C:/ps7/pwsh.exe"),
            True,
            "Select a valid PowerShell. Not found: C:/ps7/pwsh.exe.",
        ),
        (WorkingFolderError("git", "C:/work"), request(), False, f"Folder not found: {FOLDER}."),
        (LaunchError("git"), request(), False, "git could not be started."),
    ],
)
def test_the_values_fill_the_text_of_the_announcement(
    error: TransportError, chosen: LaunchRequest, is_shell: bool, said: str
) -> None:
    announce, values = launch_failure(error, chosen, "git", is_shell=is_shell)
    assert AnnouncementCenter.text(announce, **values) == said
