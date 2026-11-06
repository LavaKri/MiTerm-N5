from pathlib import Path

import pytest

from n5terminal.core.session.session_state import Interpreter
from n5terminal.core.session.shell import (
    change_folder_command,
    shell_command,
    shell_environment,
)

pytestmark = pytest.mark.unit


def test_a_direct_launch_has_no_shell() -> None:
    assert shell_command(Interpreter.NONE) is None
    assert change_folder_command(Interpreter.NONE, Path("C:/a")) is None


def test_the_shells() -> None:
    assert shell_command(Interpreter.CMD) == ("cmd.exe",)
    assert shell_command(Interpreter.POWERSHELL) == ("powershell.exe", "-NoLogo")


def test_without_a_prefix_the_shells_and_their_environment_are_untouched() -> None:
    assert shell_command(Interpreter.POWERSHELL, "") == ("powershell.exe", "-NoLogo")
    assert shell_environment(Interpreter.CMD, "", {"PROMPT": "$G"}) is None
    assert shell_environment(Interpreter.POWERSHELL, "# ", {}) is None
    assert shell_environment(Interpreter.NONE, "# ", {}) is None


def test_cmd_puts_the_prefix_before_the_prompt_of_the_user() -> None:
    environment = shell_environment(Interpreter.CMD, "# ", {"PROMPT": "[$T] $P$G", "A": "1"})
    assert environment == {"PROMPT": "# [$T] $P$G", "A": "1"}


def test_cmd_without_a_prompt_of_its_own_gets_the_default_one() -> None:
    assert shell_environment(Interpreter.CMD, "# ", {}) == {"PROMPT": "# $P$G"}


def test_cmd_does_not_change_the_environment_it_is_given() -> None:
    inherited = {"PROMPT": "$G"}
    shell_environment(Interpreter.CMD, "# ", inherited)
    assert inherited == {"PROMPT": "$G"}


def test_cmd_takes_no_argument_for_the_prefix() -> None:
    assert shell_command(Interpreter.CMD, "# ") == ("cmd.exe",)


def test_powershell_wraps_the_prompt_it_has() -> None:
    command = shell_command(Interpreter.POWERSHELL, "# ")
    assert command is not None
    assert command[:4] == ("powershell.exe", "-NoLogo", "-NoExit", "-Command")
    assert command[4] == "$n5prompt = $function:prompt; function prompt { '# ' + (& $n5prompt) }"


def test_powershell_doubles_a_quote_of_the_prefix() -> None:
    command = shell_command(Interpreter.POWERSHELL, "it's ")
    assert command is not None
    assert "'it''s '" in command[4]


def test_cmd_changes_drive_and_folder_in_one_command() -> None:
    line = change_folder_command(Interpreter.CMD, Path("C:/Premier/SRC"))
    assert line == f'cd /d "{Path("C:/Premier/SRC")}"'


def test_powershell_reads_the_path_literally() -> None:
    line = change_folder_command(Interpreter.POWERSHELL, Path("C:/a [1]/it's"))
    assert line == f"Set-Location -LiteralPath '{Path('C:/a [1]/it')}''s'"


def test_the_powershell_chosen_replaces_windows_powershell() -> None:
    assert shell_command(Interpreter.POWERSHELL, "", r"C:\PS7\pwsh.exe") == (
        r"C:\PS7\pwsh.exe",
        "-NoLogo",
    )
    command = shell_command(Interpreter.POWERSHELL, "# ", r' "C:\My PS\pwsh.exe" ')
    assert command is not None
    assert command[:4] == (r"C:\My PS\pwsh.exe", "-NoLogo", "-NoExit", "-Command")


def test_the_powershell_chosen_does_not_touch_the_other_shells() -> None:
    assert shell_command(Interpreter.CMD, "", r"C:\PS7\pwsh.exe") == ("cmd.exe",)
    assert shell_command(Interpreter.NONE, "", r"C:\PS7\pwsh.exe") is None
