import copy
import json
from dataclasses import fields
from pathlib import Path

import pytest

from n5terminal.core.config.announcements import ACTIVITY, PROGRAM, SEARCH_FAILED, Destination
from n5terminal.core.config.prompt_patterns import (
    START_PATTERNS,
    PromptPattern,
    start_patterns,
)
from n5terminal.core.config.screen_reader import default_output
from n5terminal.core.config.settings import DEFAULT_OUTPUT_LIMIT, MAX_RECENT_FOLDERS, Settings
from n5terminal.core.config.shortcuts import NEW_SESSION_COMMAND, STOP_COMMAND

pytestmark = pytest.mark.unit


def test_defaults() -> None:
    settings = Settings.load(None)
    assert settings.comfort_formatting is True
    assert settings.prompt_patterns is None
    assert settings.patterns() == start_patterns()
    assert settings.language == "fr"
    assert settings.recent_folders == []
    assert settings.screen_reader_output == default_output().id
    assert settings.shortcut_for(STOP_COMMAND) == STOP_COMMAND.default
    assert settings.destination_for(PROGRAM) is PROGRAM.default


def test_changes_survive_a_save_and_a_load(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    settings.language = "en"
    settings.add_recent_folder(Path("C:/Premier/SRC"))
    settings.set_shortcut(STOP_COMMAND, "Ctrl+K")
    settings.set_destination(SEARCH_FAILED, Destination.DIALOG)
    settings.save()
    again = Settings.load(store)
    assert again.language == "en"
    assert again.recent_folders == [str(Path("C:/Premier/SRC"))]
    assert again.shortcut_for(STOP_COMMAND) == "Ctrl+K"
    assert again.destination_for(SEARCH_FAILED) is Destination.DIALOG


# One value that is not the default for each field the file holds. A field added to ``Settings``
# must be added here, or ``test_the_table_names_every_stored_field`` fails; once it is here, the
# test after it fails if the field is not written by ``save`` or not read by ``load``.
CHANGED_VALUES: dict[str, object] = {
    "language": "en",
    "recent_folders": ["C:\\b", "C:\\a"],
    "shortcuts": {STOP_COMMAND.id: "Ctrl+K"},
    "screen_reader_output": "none",  # the default is UI Automation
    "announcements": {SEARCH_FAILED.id: Destination.DIALOG.value},
    "output_limit": 25_000,
    "launch_mode": "tui",
    "interpreter": "cmd",
    "powershell_path": "C:\\PS7\\pwsh.exe",
    "ssh_path": "C:\\Git\\usr\\bin\\ssh.exe",
    "startup_profile": "git",
    "terminal_size": "120x30",
    "terminal_view_only": True,
    "stderr_prefix": False,
    "maximize_at_start": False,
    "activity_interval": 5,
    "activity_only_in_output": False,
    "activity_last_choice": "element",
    "comfort_formatting": False,  # the default is to include it
    "comfort_titles": True,
    "prompt_patterns": [PromptPattern("Mine", "X> ", "mine")],
}
NOT_STORED = {"store", "load_warning"}  # where the file is, and what went wrong reading it


def test_the_table_names_every_stored_field() -> None:
    stored = {field.name for field in fields(Settings)} - NOT_STORED
    assert set(CHANGED_VALUES) == stored


@pytest.mark.parametrize("name", sorted(CHANGED_VALUES))
def test_every_stored_field_survives_a_save_and_a_load(tmp_path: Path, name: str) -> None:
    assert getattr(Settings(), name) != CHANGED_VALUES[name]  # else the test proves nothing
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    for field_name, value in CHANGED_VALUES.items():
        setattr(settings, field_name, copy.deepcopy(value))
    settings.save()
    assert getattr(Settings.load(store), name) == CHANGED_VALUES[name]


def test_only_differences_from_the_defaults_are_stored(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    settings.set_shortcut(STOP_COMMAND, "Ctrl+K")
    settings.set_shortcut(STOP_COMMAND, STOP_COMMAND.default)
    settings.set_destination(PROGRAM, PROGRAM.default)
    settings.save()
    data = json.loads(store.read_text(encoding="utf-8"))
    assert data["shortcuts"] == {}
    assert data["announcements"] == {}


def test_recent_folders_are_most_recent_first_without_duplicates() -> None:
    settings = Settings.load(None)
    settings.add_recent_folder(Path("C:/a"))
    settings.add_recent_folder(Path("C:/b"))
    settings.add_recent_folder(Path("c:/A"))
    assert settings.recent_folders == [str(Path("c:/A")), str(Path("C:/b"))]


def test_recent_folders_are_limited() -> None:
    settings = Settings.load(None)
    for number in range(MAX_RECENT_FOLDERS + 5):
        settings.add_recent_folder(Path(f"C:/folder{number}"))
    assert len(settings.recent_folders) == MAX_RECENT_FOLDERS
    assert settings.recent_folders[0].endswith(f"folder{MAX_RECENT_FOLDERS + 4}")


def test_bad_values_in_the_file_are_ignored(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    store.write_text(
        json.dumps(
            {
                "language": "klingon",
                "recent_folders": ["C:/ok", 3, None],
                "screen_reader_output": "nonsense",
                "shortcuts": {
                    STOP_COMMAND.id: "Ctrl+Ctrl+X",  # invalid
                    NEW_SESSION_COMMAND.id: "Ctrl+Q",  # a standard command
                },
                "announcements": {"program": "dialog", "unknown": "message", "folder": 5},
            }
        ),
        encoding="utf-8",
    )
    settings = Settings.load(store)
    assert settings.language == "fr"
    assert settings.recent_folders == ["C:/ok"]
    assert settings.screen_reader_output == default_output().id
    assert settings.shortcut_for(STOP_COMMAND) == STOP_COMMAND.default
    assert settings.shortcut_for(NEW_SESSION_COMMAND) == NEW_SESSION_COMMAND.default
    assert settings.announcements == {}


def test_a_damaged_file_gives_the_defaults_and_a_warning(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    store.write_text("{not json", encoding="utf-8")
    settings = Settings.load(store)
    assert settings.language == "fr"
    assert settings.load_warning


def test_the_output_limit_defaults_to_10000_and_survives_a_save(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert settings.output_limit == DEFAULT_OUTPUT_LIMIT == 10_000
    settings.output_limit = 25_000
    settings.save()
    assert Settings.load(store).output_limit == 25_000


def test_the_startup_settings_default_and_survive_a_save(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert (settings.launch_mode, settings.interpreter) == ("cli", "none")
    assert (settings.terminal_size, settings.terminal_view_only) == ("auto", False)
    settings.launch_mode, settings.interpreter = "tui", "cmd"
    settings.terminal_size, settings.terminal_view_only = "120x30", True
    settings.save()
    loaded = Settings.load(store)
    assert (loaded.launch_mode, loaded.interpreter) == ("tui", "cmd")
    assert (loaded.terminal_size, loaded.terminal_view_only) == ("120x30", True)


def test_startup_settings_of_the_wrong_kind_are_ignored(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    bad = {
        "launch_mode": "gui",
        "interpreter": 3,
        "terminal_size": "big",
        "terminal_view_only": "yes",
    }
    store.write_text(json.dumps(bad), encoding="utf-8")
    settings = Settings.load(store)
    assert (settings.launch_mode, settings.interpreter) == ("cli", "none")
    assert (settings.terminal_size, settings.terminal_view_only) == ("auto", False)


def test_the_window_is_maximized_at_start_by_default_and_the_choice_survives_a_save(
    tmp_path: Path,
) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert settings.maximize_at_start is True
    settings.maximize_at_start = False
    settings.save()
    assert Settings.load(store).maximize_at_start is False


def test_the_stderr_prefix_is_on_by_default_and_the_choice_survives_a_save(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert settings.stderr_prefix is True
    settings.stderr_prefix = False
    settings.save()
    assert Settings.load(store).stderr_prefix is False


@pytest.mark.parametrize("value", ["yes", 0, None])
def test_a_stderr_prefix_of_the_wrong_kind_is_ignored(tmp_path: Path, value: object) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"stderr_prefix": value}), encoding="utf-8")
    assert Settings.load(store).stderr_prefix is True


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_a_maximize_choice_of_the_wrong_kind_is_ignored(tmp_path: Path, value: object) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"maximize_at_start": value}), encoding="utf-8")
    assert Settings.load(store).maximize_at_start is True


@pytest.mark.parametrize("value", [0, 999, 100_001, "many", None, True, 5.5])
def test_an_output_limit_out_of_range_or_of_the_wrong_kind_is_ignored(
    tmp_path: Path, value: object
) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"output_limit": value}), encoding="utf-8")
    assert Settings.load(store).output_limit == DEFAULT_OUTPUT_LIMIT


def test_the_activity_is_on_by_default_with_messages_or_beep() -> None:
    settings = Settings()
    assert settings.destination_for(ACTIVITY) is Destination.ELEMENT_OR_BEEP
    assert (settings.activity_interval, settings.activity_only_in_output) == (1, True)


def test_the_switch_of_the_activity_brings_back_the_choice_it_had() -> None:
    settings = Settings()
    settings.set_destination(ACTIVITY, Destination.ELEMENT)
    assert settings.toggle_activity() is False
    assert settings.destination_for(ACTIVITY) is Destination.NONE
    assert settings.toggle_activity() is True
    assert settings.destination_for(ACTIVITY) is Destination.ELEMENT


def test_the_switch_goes_to_the_default_when_there_is_no_choice_to_bring_back() -> None:
    settings = Settings()
    settings.set_destination(ACTIVITY, Destination.NONE)
    assert settings.toggle_activity() is True
    assert settings.destination_for(ACTIVITY) is Destination.ELEMENT_OR_BEEP


def test_the_activity_settings_are_saved_and_read_back(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    settings.activity_interval = 5
    settings.activity_only_in_output = False
    settings.set_destination(ACTIVITY, Destination.ELEMENT)
    settings.toggle_activity()
    settings.save()
    again = Settings.load(store)
    assert (again.activity_interval, again.activity_only_in_output) == (5, False)
    assert again.destination_for(ACTIVITY) is Destination.NONE
    assert again.toggle_activity() is True
    assert again.destination_for(ACTIVITY) is Destination.ELEMENT


@pytest.mark.parametrize("interval", [0, 11, "3", True, 2.5])
def test_an_interval_of_the_file_out_of_range_or_of_the_wrong_kind_is_ignored(
    tmp_path: Path, interval: object
) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"activity_interval": interval}), encoding="utf-8")
    assert Settings.load(store).activity_interval == 1


def test_the_powershell_path_is_empty_by_default_and_survives_a_save(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert settings.powershell_path == ""
    settings.powershell_path = r"C:\PS7\pwsh.exe"
    settings.save()
    assert Settings.load(store).powershell_path == r"C:\PS7\pwsh.exe"


@pytest.mark.parametrize("value", [3, None, ["a"]])
def test_a_powershell_path_of_the_wrong_kind_is_ignored(tmp_path: Path, value: object) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"powershell_path": value}), encoding="utf-8")
    assert Settings.load(store).powershell_path == ""


def test_the_startup_profile_is_free_by_default_and_survives_a_save(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    assert settings.startup_profile == ""
    settings.startup_profile = "git"
    settings.save()
    assert Settings.load(store).startup_profile == "git"


@pytest.mark.parametrize("value", [3, None, ["a"]])
def test_a_startup_profile_of_the_wrong_kind_is_ignored(tmp_path: Path, value: object) -> None:
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"startup_profile": value}), encoding="utf-8")
    assert Settings.load(store).startup_profile == ""


def test_a_saved_list_with_the_old_patterns_gets_the_current_ones(tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    old_bash = r"(?:#+ )?(?:\([^)\r\n]*\) )?[\w.\-]+@[\w.\-]+:[^\r\n$#]*[$#] "
    store.write_text(
        json.dumps(
            {
                "prompt_patterns": [
                    {"name": "bash", "pattern": old_bash, "replacement": "Debian"},
                    {"name": "mine", "pattern": "X> "},
                ]
            }
        ),
        encoding="utf-8",
    )
    patterns = Settings.load(store).patterns()
    assert patterns[0].pattern == START_PATTERNS[3].pattern  # the end of the line is allowed now
    assert patterns[0].replacement == "Debian"  # what the user wrote is kept
    assert patterns[1].pattern == "X> "  # a pattern of the user is not touched
