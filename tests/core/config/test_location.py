from pathlib import Path

import pytest

from n5terminal.core.config.location import (
    MARKER_FILE,
    application_folder,
    choose_location,
    develop_location,
    known_hosts_file,
    local_location,
    portable_location,
)

pytestmark = pytest.mark.unit


def test_the_local_files_are_in_the_profile_of_the_user() -> None:
    location = local_location()
    assert not location.portable
    assert location.explicit_folder is None
    assert "Roaming" in location.settings_file.parts
    assert location.settings_file.name == "settings.json"
    assert location.profiles_folder.parent == location.settings_file.parent
    assert location.connections_folder == location.settings_file.parent / "connections"
    assert "Roaming" not in location.log_file.parts  # the logs stay on the PC
    assert location.log_file.name == "n5terminal.log"


def test_the_portable_files_are_all_in_one_folder(tmp_path: Path) -> None:
    location = portable_location(tmp_path / "data")
    assert location.portable
    assert location.settings_file == tmp_path / "data" / "settings.json"
    assert location.profiles_folder == tmp_path / "data" / "profiles"
    assert location.connections_folder == tmp_path / "data" / "connections"
    assert location.log_file == tmp_path / "data" / "logs" / "n5terminal.log"


def test_without_the_file_nor_the_option_it_is_local(tmp_path: Path) -> None:
    assert choose_location(tmp_path) == local_location()


def test_the_file_beside_the_program_makes_it_portable(tmp_path: Path) -> None:
    (tmp_path / MARKER_FILE).write_text("", encoding="utf-8")
    location = choose_location(tmp_path)
    assert location == portable_location(tmp_path / "data")
    assert location.explicit_folder is None  # a new session finds the file by itself


def test_a_folder_in_the_marker_name_is_not_a_marker(tmp_path: Path) -> None:
    (tmp_path / MARKER_FILE).mkdir()
    assert not choose_location(tmp_path).portable


def test_the_option_wins_over_the_file(tmp_path: Path) -> None:
    (tmp_path / MARKER_FILE).write_text("", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    location = choose_location(tmp_path, elsewhere)
    assert location.settings_file == elsewhere.resolve() / "settings.json"
    assert location.explicit_folder == elsewhere.resolve()


def test_the_option_makes_it_portable_without_any_file(tmp_path: Path) -> None:
    assert choose_location(tmp_path, tmp_path / "keys").portable


def test_develop_keeps_settings_connections_and_logs_in_its_folder_and_profiles_in_the_starters(
    tmp_path: Path,
) -> None:
    location = develop_location(tmp_path)
    assert location.develop
    assert location.portable  # nothing is written outside the application
    assert location.settings_file == tmp_path / "DevelopMode" / "settings.json"
    assert location.log_file == tmp_path / "DevelopMode" / "logs" / "n5terminal.log"
    assert location.profiles_folder == tmp_path / "starter_profiles"
    assert location.connections_folder == tmp_path / "DevelopMode" / "connections"


def test_develop_wins_over_the_option_and_the_file(tmp_path: Path) -> None:
    (tmp_path / MARKER_FILE).write_text("", encoding="utf-8")
    location = choose_location(tmp_path, tmp_path / "keys", develop=True)
    assert location == develop_location(tmp_path)


def test_the_other_modes_are_not_develop(tmp_path: Path) -> None:
    assert not local_location().develop
    assert not portable_location(tmp_path).develop


def test_the_folder_of_the_program_in_development_is_the_repository() -> None:
    assert (application_folder() / "pyproject.toml").is_file()


def test_the_host_keys_of_the_portable_and_develop_versions_are_kept_in_their_folder(
    tmp_path: Path,
) -> None:
    assert (
        known_hosts_file(portable_location(tmp_path / "data")) == tmp_path / "data" / "known_hosts"
    )
    assert known_hosts_file(develop_location(tmp_path)) == tmp_path / "DevelopMode" / "known_hosts"


def test_the_local_version_leaves_the_known_hosts_of_the_system_alone() -> None:
    assert known_hosts_file(local_location()) is None
