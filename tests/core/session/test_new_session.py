from pathlib import Path

import pytest

from n5terminal.core.session.new_session import new_session_command

pytestmark = pytest.mark.unit


def test_a_new_session_starts_in_the_working_folder(tmp_path: Path) -> None:
    command = new_session_command(tmp_path)
    assert command[command.index("--folder") + 1] == str(tmp_path)
    assert "--data-folder" not in command
    assert "--develop" not in command


def test_the_develop_mode_is_passed_on(tmp_path: Path) -> None:
    assert "--develop" in new_session_command(tmp_path, develop=True)


def test_the_data_folder_given_on_the_command_line_is_passed_on(tmp_path: Path) -> None:
    command = new_session_command(tmp_path, tmp_path / "keys")
    assert command[command.index("--data-folder") + 1] == str(tmp_path / "keys")
