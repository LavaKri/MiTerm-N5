"""The session presenter with the real launcher and transports, run on the simulated programs.

Nothing here is faked but the window: a command typed in the field goes through the splitting, the
launcher, a real process, the decoder or the emulator, the exchange and the ticks, up to what the
view receives. The programs are the simulators of ``tests/fakes`` (independent of the system).
"""

import os
import queue
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from fakes.fake_view import FakeView
from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import AnnouncementCenter
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.process_launcher import ProcessLauncher
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode, Phase
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.presenters.session_run import SessionServices

pytestmark = pytest.mark.slow

FAKES = Path(__file__).parent.parent / "fakes"
CLI_PROGRAM = FAKES / "program_cli.py"
TUI_PROGRAM = FAKES / "program_tui_line.py"
TIMEOUT = 15.0


@dataclass
class Window:
    """A presenter wired to the real launcher; the UI thread is played by ``wait_until``."""

    presenter: SessionPresenter
    view: FakeView
    sink: RecordingMessageSink
    posted: queue.Queue[Callable[[], None]]

    def pump(self) -> None:
        while not self.posted.empty():
            self.posted.get()()
        self.presenter.tick()

    def wait_until(self, condition: Callable[[], bool]) -> None:
        deadline = time.monotonic() + TIMEOUT
        while time.monotonic() < deadline:
            self.pump()
            if condition():
                return
            time.sleep(0.01)
        pytest.fail(f"timeout; output {self.text()!r}, messages {self.sink.messages!r}")

    def wait_idle(self) -> None:
        self.wait_until(lambda: self.presenter.state.phase is Phase.IDLE)

    def text(self) -> list[str]:
        live = [text for _number, text in sorted(self.view.live_rows().items()) if text]
        return [*self.view.fixed_lines(), *live]


@pytest.fixture
def window(tmp_path: Path) -> Window:
    view, sink, posted = FakeView(), RecordingMessageSink(), queue.Queue[Callable[[], None]]()
    services = SessionServices(
        ProcessLauncher(), Settings.load(None), AnnouncementCenter(sink), post=posted.put
    )
    return Window(SessionPresenter(view, services, tmp_path), view, sink, posted)


def command(program: Path, *arguments: str) -> str:
    return " ".join(f'"{part}"' for part in (sys.executable, "-u", program, *arguments))


def test_cli_program_with_both_streams_and_an_exit_code(window: Window) -> None:
    window.presenter.submit(command(CLI_PROGRAM, "both-streams"))
    window.wait_idle()
    assert {"out", "StdErr: err"} <= set(window.text())
    assert window.sink.messages[-1].endswith("ended with the code 3.")
    assert window.view.last_state == "Ended (code 3)"


def test_cli_program_answers_what_is_typed_to_it(window: Window) -> None:
    window.presenter.submit(command(CLI_PROGRAM, "echo-input"))
    window.presenter.submit("hello")
    window.wait_until(lambda: "got: hello" in window.text())
    window.presenter.submit("quit")
    window.wait_idle()
    assert window.text()[-5:] == [
        f"# {command(CLI_PROGRAM, 'echo-input')}",
        f"From {window.presenter.working_folder}{os.sep}",
        "> hello",
        "got: hello",
        "> quit",
    ]
    assert window.sink.messages[-1].endswith("ended with the code 0.")


def test_a_cli_flood_arrives_whole(window: Window) -> None:
    window.presenter.submit(command(CLI_PROGRAM, "flood", "5000"))
    window.wait_idle()
    lines = [line for line in window.text() if line.startswith("line ")]
    assert lines == [f"line {number}" for number in range(5000)]


def test_a_program_that_needs_a_terminal_refuses_the_cli_mode(window: Window) -> None:
    window.presenter.submit(command(TUI_PROGRAM, "terminal"))
    window.wait_idle()
    assert "StdErr: not a terminal" in window.text()
    assert window.view.last_state == "Ended (code 2)"


def test_the_same_program_works_in_the_tui_mode_with_its_colours_removed(window: Window) -> None:
    assert window.presenter.set_launch_mode(LaunchMode.TUI)
    window.presenter.submit(command(TUI_PROGRAM, "terminal"))
    window.wait_idle()
    assert "terminal: yes" in window.text()
    assert "red plain" in window.text()


def test_tui_program_prompts_and_answers(window: Window) -> None:
    window.presenter.set_launch_mode(LaunchMode.TUI)
    window.presenter.submit(command(TUI_PROGRAM, "echo-input"))
    window.wait_until(lambda: "name?" in window.view.live_rows().get(0, ""))
    window.presenter.submit("Ada")
    window.wait_idle()
    assert "got: Ada" in window.text()
    assert window.presenter.history_items() == (command(TUI_PROGRAM, "echo-input"), "Ada")


def test_a_program_that_does_not_exist_is_announced_in_both_modes(window: Window) -> None:
    window.presenter.submit("no-such-program-for-n5terminal")
    assert window.sink.messages[-1] == "Program not found: no-such-program-for-n5terminal."
    window.presenter.set_launch_mode(LaunchMode.TUI)
    window.presenter.submit("no-such-program-for-n5terminal")
    assert window.sink.messages[-1] == "Program not found: no-such-program-for-n5terminal."
    assert window.presenter.state.phase is Phase.IDLE


def test_stop_ends_a_program_that_never_ends(window: Window) -> None:
    window.presenter.submit(command(CLI_PROGRAM, "sleep"))
    window.wait_until(lambda: window.presenter.state.phase is Phase.RUNNING)
    assert window.presenter.run_command(CommandId.STOP)
    window.wait_idle()
    assert "Program stopped." in window.sink.messages


def test_a_real_cmd_is_told_from_busy_to_waiting_and_follows_the_folder(
    window: Window, tmp_path: Path
) -> None:
    assert window.presenter.set_interpreter(Interpreter.CMD)
    window.presenter.submit("")  # starts cmd.exe, nothing typed yet
    window.wait_until(lambda: window.presenter.state.shell_at_prompt)
    assert CommandId.CHOOSE_FOLDER in window.view.last_enabled

    window.presenter.submit("ping -n 4 127.0.0.1 >nul")
    window.wait_until(lambda: not window.presenter.state.shell_at_prompt)
    assert CommandId.CHOOSE_FOLDER not in window.view.last_enabled
    window.wait_until(lambda: window.presenter.state.shell_at_prompt)

    folder = tmp_path / "deeper" / "still"
    folder.mkdir(parents=True)
    assert window.presenter.set_working_folder(folder)
    window.wait_until(lambda: "".join(window.text()[-2:]).endswith(f"{folder}>"))
    window.wait_until(lambda: window.presenter.state.shell_at_prompt)

    window.presenter.submit("exit")
    window.wait_idle()
