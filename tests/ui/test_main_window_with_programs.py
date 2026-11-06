"""The main window with the real launcher and a real program (the simulators of ``tests/fakes``)."""

import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import wx

from fakes.wx_loop import run_until
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.process_launcher import ProcessLauncher
from n5terminal.core.session.session_state import LaunchMode, Phase
from n5terminal.ui.main_window import MainWindow

pytestmark = [pytest.mark.ui, pytest.mark.slow]

FAKES = Path(__file__).parent.parent / "fakes"
TIMEOUT = 15.0


@pytest.fixture
def window(app: wx.App, tmp_path: Path) -> Iterator[MainWindow]:
    frame = MainWindow(Settings.load(None), ProcessLauncher(), tmp_path)
    frame.Show()
    yield frame
    frame.Close(force=True)


def wait_until(condition: Callable[[], bool]) -> None:
    if not run_until(condition, TIMEOUT):
        pytest.fail("timeout")


def command(program: str, *arguments: str) -> str:
    return " ".join(f'"{part}"' for part in (sys.executable, "-u", FAKES / program, *arguments))


def test_a_cli_program_writes_in_the_output_area(window: MainWindow) -> None:
    window.presenter.submit(command("program_cli.py", "both-streams"))
    wait_until(lambda: {"out", "StdErr: err"} <= set(window.output.GetValue().split("\n")))
    wait_until(lambda: window.GetStatusBar().GetStatusText(1) == "Ended (code 3)")
    assert window.output.GetValue().startswith("# ")


def test_a_tui_program_works_through_the_emulator(window: MainWindow) -> None:
    window.actions.set_mode(LaunchMode.TUI)
    window.presenter.submit(command("program_tui_line.py", "echo-input"))
    wait_until(lambda: "name?" in window.output.GetValue())
    window.presenter.submit("Ada")
    wait_until(lambda: "got: Ada" in window.output.GetValue())
    wait_until(lambda: window.presenter.state.phase is Phase.IDLE)
    assert "# " not in window.output.GetValue()  # a terminal draws its own echo, no mark


def test_the_field_keeps_the_focus_while_a_program_writes(window: MainWindow) -> None:
    window.command.focus_field()
    window.presenter.submit(command("program_cli.py", "flood", "2000"))
    wait_until(lambda: window.output.GetValue().count("\nline ") == 2000)
    wait_until(lambda: window.presenter.state.phase is Phase.IDLE)
    assert wx.Window.FindFocus() is window.command.field
