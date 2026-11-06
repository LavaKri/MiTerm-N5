from pathlib import Path

import pytest

from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.location import develop_location, local_location, portable_location

pytestmark = pytest.mark.unit


def test_a_context_without_anything_has_no_folder_and_no_develop_mode() -> None:
    context = AppContext()
    assert context.profiles_folder is None
    assert context.develop_folder is None
    assert context.location is None


def test_a_normal_run_has_the_folders_of_the_user_and_no_develop_folder() -> None:
    location = local_location()
    context = AppContext.from_location(location, None)
    assert context.profiles_folder == location.profiles_folder
    assert context.log_folder == location.log_file.parent
    assert context.data_folder is None
    assert context.develop_folder is None
    assert context.location is location


def test_the_folder_given_on_the_command_line_is_kept_for_a_new_session(tmp_path: Path) -> None:
    context = AppContext.from_location(portable_location(tmp_path, explicit=True), None)
    assert context.data_folder == tmp_path


def test_the_develop_mode_gives_the_develop_folder(tmp_path: Path) -> None:
    location = develop_location(tmp_path)
    context = AppContext.from_location(location, None)
    assert context.develop_folder == location.settings_file.parent
