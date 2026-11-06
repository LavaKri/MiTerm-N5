import pytest

from n5terminal.core.session.powershells import PowerShellInstall
from n5terminal.presenters.powershell_choice import PowerShellChoice

pytestmark = pytest.mark.unit

SEVEN = PowerShellInstall(r"C:\Program Files\PowerShell\7\pwsh.exe", "7")
STORE = PowerShellInstall(r"C:\Apps\pwsh.exe")


def _choice(current: str = "", valid: bool = True) -> PowerShellChoice:
    return PowerShellChoice(current, [SEVEN, STORE], lambda text: text, lambda path: valid)


def test_the_list_has_windows_powershell_first_the_installed_ones_then_other() -> None:
    assert _choice().labels == [
        "Windows PowerShell",
        f"PowerShell 7 ({SEVEN.path})",
        f"PowerShell ({STORE.path})",
        "Other…",
    ]


def test_without_a_path_stored_windows_powershell_is_selected() -> None:
    choice = _choice()
    assert choice.selected == 0
    assert choice.chosen_path() == ""
    assert not choice.path_enabled
    assert choice.name() == "Windows PowerShell"


def test_a_stored_path_that_is_installed_selects_its_line_whatever_the_case() -> None:
    choice = _choice(SEVEN.path.upper())
    assert choice.selected == 1
    assert choice.chosen_path() == SEVEN.path


def test_a_stored_path_that_is_not_listed_is_shown_in_other() -> None:
    choice = _choice(r"D:\Tools\pwsh.exe")
    assert choice.selected == 3
    assert choice.custom_path == r"D:\Tools\pwsh.exe"
    assert choice.path_enabled
    assert choice.chosen_path() == r"D:\Tools\pwsh.exe"


def test_the_path_typed_in_other_loses_its_quotes_and_spaces() -> None:
    choice = _choice()
    choice.selected = 3
    choice.custom_path = r'  "D:\My Tools\pwsh.exe" '
    assert choice.chosen_path() == r"D:\My Tools\pwsh.exe"


def test_other_with_a_path_that_is_not_a_powershell_is_refused_in_words() -> None:
    choice = _choice(valid=False)
    assert choice.problem() is None  # Windows PowerShell does not need a check
    choice.selected = 3
    assert choice.problem() == "Select a valid PowerShell."


def test_a_listed_choice_is_not_checked() -> None:
    choice = _choice(valid=False)
    choice.selected = 1
    assert choice.problem() is None
