import os
from pathlib import Path

import pytest

from n5terminal.core.session.session_state import Interpreter
from n5terminal.presenters.session_info import (
    SessionInfo,
    end_text,
    folder_name,
    folder_text,
    launch_folder_line,
    run_text,
    session_info_lines,
    window_title,
)

pytestmark = pytest.mark.unit

FRENCH = {
    "free profile": "profil libre",
    "none": "aucun",
    "From {folder}": "Depuis {folder}",
    "Ready": "Prêt",
}


def translate(text: str) -> str:
    return FRENCH.get(text, text)


def info(**changes: object) -> SessionInfo:
    values: dict[str, object] = {
        "folder": Path("C:/work"),
        "profile": None,
        "program": None,
        "last_end": "",
        "launch_mode": "CLI",
        "interpreter": Interpreter.NONE,
        "terminal_size": "80 x 24",
        "terminal_view_only": False,
        "output_lines": 12,
        "output_limit": 10000,
        "data_mode": "normal",
        "settings_file": Path("C:/data/settings.json"),
        "profiles_folder": None,
        "log_file": None,
        "version": "1.0",
    }
    return SessionInfo(**{**values, **changes})  # type: ignore[arg-type]


def test_a_folder_ends_with_a_separator() -> None:
    assert folder_text(Path("C:/test")).endswith(os.sep)
    assert folder_text(Path("C:/test") / "") == folder_text(Path("C:/test"))


def test_the_name_of_a_folder_is_its_last_name_and_a_root_its_whole_path() -> None:
    assert folder_name(Path("C:/Users/Dev/MiTerm-N5")) == "MiTerm-N5"
    assert folder_name(Path("C:/")) == str(Path("C:/"))


def test_the_title_names_the_profile_and_the_folder() -> None:
    assert window_title(None, Path("C:/work/Dev"), lambda text: text) == (
        "MiTerm-N5: free profile in Dev"
    )
    assert window_title("git", Path("C:/work/Dev"), lambda text: text) == "MiTerm-N5: git in Dev"
    assert window_title(None, Path("C:/work/Dev"), translate) == "MiTerm-N5: profil libre in Dev"


def test_the_line_under_a_launched_command_names_the_folder() -> None:
    assert (
        launch_folder_line(Path("C:/test"), translate) == f"Depuis {folder_text(Path('C:/test'))}"
    )


def test_the_end_of_a_program_gives_its_code_when_it_is_known() -> None:
    assert end_text(3, lambda text: text) == "Ended (code 3)"
    assert end_text(0, lambda text: text) == "Ended (code 0)"
    assert end_text(None, lambda text: text) == "Ended"


def test_the_state_with_no_program_is_how_the_last_one_ended_or_ready() -> None:
    assert run_text(None, False, "", lambda text: text) == "Ready"
    assert run_text(None, False, "Ended (code 3)", lambda text: text) == "Ended (code 3)"
    assert run_text(None, False, "", translate) == "Prêt"


def test_the_state_of_a_running_program_names_it_or_its_child() -> None:
    assert run_text("ping", False, "", lambda text: text) == "Running: ping"
    assert run_text("ping", True, "", lambda text: text) == "Child process active"
    assert run_text("ping", False, "Ended", lambda text: text) == "Running: ping"


def test_the_information_gives_the_full_path_and_the_type_of_session() -> None:
    lines = session_info_lines(info(data_mode="develop"), translate)
    assert lines[0] == f"Working folder: {Path('C:/work')}"
    assert lines[1] == "Session type: develop"
    assert "Profile: profil libre" in lines
    assert "Running program: aucun" in lines
    assert f"Settings file: {Path('C:/data/settings.json')}" in lines
    assert "Profiles folder: aucun" in lines
    assert lines[-1] == "Version: 1.0"


def test_the_information_tells_the_program_and_the_profile() -> None:
    lines = session_info_lines(
        info(program="ping host", profile="git", interpreter=Interpreter.CMD), translate
    )
    assert "Running program: ping host" in lines
    assert "Profile: git" in lines
    assert "Interpreter: Cmd" in lines


# A connection ----------------------------------------------------------------------------------


def lines_of(**changes: object) -> list[str]:
    return session_info_lines(info(**changes), lambda text: text)


def test_locale_has_no_line_of_connection_but_names_the_client_and_the_folder() -> None:
    lines = lines_of()
    assert not any(line.startswith(("Connection:", "Target:")) for line in lines)
    assert any(line.startswith("OpenSSH client: ") and "ssh.exe" in line for line in lines)
    assert "Connections folder: none" in lines


def test_a_connection_chosen_says_its_name_its_target_and_its_state() -> None:
    lines = lines_of(
        connection="prod",
        connection_target="admin@example.org:2222",
        connection_state="not connected",
    )
    assert lines[1:4] == [
        "Connection: prod",
        "Target: admin@example.org:2222",
        "Connection state: not connected",
    ]


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(5, "5 s"), (59.9, "59 s"), (60, "1 min"), (12 * 60 + 30, "12 min"), (3600, "1 h 0 min"),
     (2 * 3600 + 5 * 60, "2 h 5 min")],
)  # fmt: skip
def test_an_open_connection_says_for_how_long(seconds: float, text: str) -> None:
    lines = lines_of(
        connection="prod",
        connection_target="box",
        connection_state="Connected to prod",
        connected_for=seconds,
    )
    assert f"Connection state: Connected to prod, since {text}" in lines


def test_the_client_set_is_named_by_its_path() -> None:
    ssh = r"C:\Git\usr\bin\ssh.exe"
    assert f"OpenSSH client: {ssh}" in lines_of(ssh_path=ssh)


def test_the_folder_of_the_connections_is_named() -> None:
    folder = Path("C:/data/connections")
    assert f"Connections folder: {folder}" in lines_of(connections_folder=folder)
