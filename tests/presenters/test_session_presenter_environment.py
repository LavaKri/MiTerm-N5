"""The working folder, the interpreter and the size of the terminal in the session presenter."""

from pathlib import Path

import pytest

from fakes.session_support import Session, run_program, show_prompt, start_shell
from n5terminal.core.config.profiles import Profile
from n5terminal.core.errors import ProgramNotFoundError
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode, Phase

pytestmark = pytest.mark.unit


# The working folder ----------------------------------------------------------------------------


def test_the_working_folder_is_chosen_remembered_and_used(session: Session, tmp_path: Path) -> None:
    folder = tmp_path / "sub"
    folder.mkdir()
    assert session.presenter.set_working_folder(folder)
    assert session.presenter.working_folder == folder
    assert session.settings.recent_folders == [str(folder)]
    assert session.sink.messages == [f"Working folder: {folder}."]
    run_program(session)
    assert session.launcher.calls[0].folder == folder


def test_a_folder_that_does_not_exist_is_refused(session: Session, tmp_path: Path) -> None:
    assert not session.presenter.set_working_folder(tmp_path / "missing")
    assert session.presenter.working_folder == session.folder
    assert session.sink.messages[-1].startswith("Folder not found:")


def test_the_folder_cannot_change_under_a_running_program(session: Session, tmp_path: Path) -> None:
    run_program(session)
    assert not session.presenter.set_working_folder(tmp_path)
    assert session.sink.messages[-1] == "Not available while a program is running."


# A shell that stays open -----------------------------------------------------------------------


def test_the_shell_is_started_and_the_first_line_typed_into_it(terminal: Session) -> None:
    start_shell(terminal)
    call = terminal.launcher.calls[0]
    assert (call.arguments, call.launch_mode) == (("cmd.exe",), LaunchMode.TUI)
    assert terminal.transport.written == [b"dir\r"]
    assert terminal.presenter.history_items() == ("dir",)
    assert terminal.view.last_state == "Running: cmd.exe"


def test_a_shell_started_with_an_empty_line_types_nothing(terminal: Session) -> None:
    start_shell(terminal, "")
    assert terminal.transport.written == []


def test_the_lines_typed_into_a_shell_are_commands_kept_in_the_history(terminal: Session) -> None:
    start_shell(terminal)
    terminal.presenter.submit("cd ..")
    assert terminal.presenter.history_items() == ("dir", "cd ..")


def test_the_interpreter_cannot_change_while_a_program_runs(session: Session) -> None:
    run_program(session)
    assert not session.presenter.set_interpreter(Interpreter.CMD)
    assert session.presenter.state.interpreter is Interpreter.NONE


def test_a_shell_at_its_prompt_is_sent_to_the_new_folder(terminal: Session, tmp_path: Path) -> None:
    start_shell(terminal)
    assert CommandId.CHOOSE_FOLDER not in terminal.view.last_enabled
    show_prompt(terminal)
    assert CommandId.CHOOSE_FOLDER in terminal.view.last_enabled
    folder = tmp_path / "deep" / "er"
    folder.mkdir(parents=True)
    assert terminal.presenter.set_working_folder(folder)
    assert terminal.transport.written[-1] == f'cd /d "{folder}"\r'.encode()


def test_a_busy_shell_keeps_its_folder(terminal: Session, tmp_path: Path) -> None:
    start_shell(terminal)
    assert not terminal.presenter.set_working_folder(tmp_path)
    assert terminal.transport.written == [b"dir\r"]


def test_a_shell_without_a_prefix_inherits_the_environment(terminal: Session) -> None:
    start_shell(terminal)
    assert terminal.launcher.calls[0].environment is None


def test_the_prefix_of_the_profile_goes_in_front_of_the_prompt_of_cmd(terminal: Session) -> None:
    assert terminal.presenter.select_profile(Profile("c", interpreter="cmd", prompt_prefix="# "))
    terminal.presenter.submit("dir")
    environment = terminal.launcher.calls[0].environment
    assert environment is not None
    assert environment["PROMPT"].startswith("# ")


def test_the_prefix_of_the_profile_is_given_to_powershell_as_its_prompt(terminal: Session) -> None:
    profile = Profile("p", interpreter="powershell", prompt_prefix="# ")
    assert terminal.presenter.select_profile(profile)
    terminal.presenter.submit("dir")
    arguments = terminal.launcher.calls[0].arguments
    assert arguments[:4] == ("powershell.exe", "-NoLogo", "-NoExit", "-Command")


def test_a_shell_with_a_prefix_is_at_its_prompt_when_the_line_starts_with_it(
    terminal: Session,
) -> None:
    assert terminal.presenter.select_profile(Profile("c", interpreter="cmd", prompt_prefix="# "))
    terminal.presenter.submit("dir")
    show_prompt(terminal, b"C:\\work>")
    assert CommandId.CHOOSE_FOLDER not in terminal.view.last_enabled
    show_prompt(terminal, b"\r\n# C:\\work>")
    assert CommandId.CHOOSE_FOLDER in terminal.view.last_enabled


def test_the_values_of_the_session_hold_the_prefix(terminal: Session) -> None:
    assert terminal.presenter.select_profile(Profile("c", interpreter="cmd", prompt_prefix="# "))
    assert terminal.presenter.session_values().prompt_prefix == "# "


# The mode: CLI or TUI -------------------------------------------------------------------------


def test_the_mode_chosen_is_given_to_the_launcher(session: Session) -> None:
    assert session.presenter.set_launch_mode(LaunchMode.TUI)
    run_program(session, "python")
    assert session.launcher.calls[0].launch_mode is LaunchMode.TUI


def test_cli_is_the_default_mode(session: Session) -> None:
    run_program(session)
    assert session.launcher.calls[0].launch_mode is LaunchMode.CLI


def test_the_mode_cannot_change_while_a_program_runs(session: Session) -> None:
    run_program(session)
    assert not session.presenter.set_launch_mode(LaunchMode.TUI)
    assert session.sink.messages[-1] == "Not available while a program is running."
    assert session.presenter.state.launch_mode is LaunchMode.CLI


def test_a_shell_is_always_tui_and_the_mode_cannot_be_changed(session: Session) -> None:
    assert session.presenter.set_interpreter(Interpreter.CMD)
    assert not session.presenter.set_launch_mode(LaunchMode.CLI)
    assert session.sink.messages[-1] == "A shell always uses the TUI mode."
    assert session.presenter.state.effective_launch_mode is LaunchMode.TUI


def test_the_mode_chosen_comes_back_when_the_shell_is_given_up(session: Session) -> None:
    session.presenter.set_launch_mode(LaunchMode.TUI)
    session.presenter.set_interpreter(Interpreter.CMD)
    session.presenter.set_interpreter(Interpreter.NONE)
    assert session.presenter.state.effective_launch_mode is LaunchMode.TUI


# The size of the terminal ----------------------------------------------------------------------


def test_a_line_too_long_for_the_terminal_makes_it_grow(terminal: Session) -> None:
    run_program(terminal, "tool")
    terminal.transport.receive(b"x" * 150 + b"\r\n")
    terminal.presenter.tick()
    assert terminal.transport.sizes == [(132, 43)]
    assert terminal.sink.messages[-1] == "Terminal size: 132 columns, 43 rows."
    terminal.presenter.tick()
    update = terminal.view.outputs[-1][0]
    assert (update.columns, update.row_count) == (132, 43)


def test_a_slightly_long_line_does_not_make_it_grow(terminal: Session) -> None:
    run_program(terminal, "tool")
    terminal.transport.receive(b"x" * 121 + b"\r\n")
    terminal.presenter.tick()
    assert terminal.transport.sizes == []


def test_pipes_never_resize(session: Session) -> None:
    run_program(session)
    session.transport.receive(b"x" * 500 + b"\n")
    session.presenter.tick()
    assert session.transport.sizes == []


def test_a_chosen_size_is_used_at_launch_and_never_grows(terminal: Session) -> None:
    terminal.presenter.set_terminal_size(TerminalSize(80, 24))
    run_program(terminal, "tool")
    assert terminal.launcher.calls[0].size == TerminalSize(80, 24)
    terminal.transport.receive(b"x" * 300 + b"\r\n")
    terminal.presenter.tick()
    assert terminal.transport.sizes == []


def test_a_size_chosen_while_a_terminal_runs_is_applied(terminal: Session) -> None:
    run_program(terminal, "tool")
    terminal.presenter.set_terminal_size(TerminalSize(132, 43))
    assert terminal.transport.sizes == [(132, 43)]
    terminal.presenter.tick()
    assert terminal.view.outputs[-1][0].replace_all


def test_the_automatic_size_goes_on_from_the_current_one(terminal: Session) -> None:
    terminal.presenter.set_terminal_size(TerminalSize(120, 30))
    run_program(terminal, "tool")
    terminal.presenter.set_terminal_size(None)
    terminal.transport.receive(b"x" * 300 + b"\r\n")
    terminal.presenter.tick()
    assert terminal.transport.sizes == [(132, 43)]


def mode_shown(session: Session) -> LaunchMode:
    return session.view.shown_states[-1].effective_launch_mode


def test_the_view_is_told_the_real_mode_and_interpreter(session: Session) -> None:
    assert mode_shown(session) is LaunchMode.CLI
    session.presenter.set_launch_mode(LaunchMode.TUI)
    assert mode_shown(session) is LaunchMode.TUI
    session.presenter.set_interpreter(Interpreter.CMD)
    assert session.view.shown_states[-1].interpreter is Interpreter.CMD


def test_the_view_is_not_told_again_when_the_choices_did_not_change(session: Session) -> None:
    count = len(session.view.shown_states)
    run_program(session)
    session.transport.exit(0)
    session.presenter.tick()
    assert len(session.view.shown_states) == count


# The PowerShell the interpreter starts ----------------------------------------------------------


def test_powershell_starts_windows_powershell_unless_a_path_was_chosen(terminal: Session) -> None:
    assert terminal.presenter.set_interpreter(Interpreter.POWERSHELL)
    terminal.presenter.submit("dir")
    assert terminal.launcher.calls[0].arguments == ("powershell.exe", "-NoLogo")


def test_the_powershell_chosen_is_the_one_started(terminal: Session) -> None:
    assert terminal.presenter.set_powershell_path(r"C:\PS7\pwsh.exe")
    assert terminal.settings.powershell_path == r"C:\PS7\pwsh.exe"
    assert terminal.sink.messages[-1] == r"PowerShell: C:\PS7\pwsh.exe."
    assert terminal.presenter.set_interpreter(Interpreter.POWERSHELL)
    terminal.presenter.submit("dir")
    assert terminal.launcher.calls[0].arguments == (r"C:\PS7\pwsh.exe", "-NoLogo")


def test_choosing_windows_powershell_again_clears_the_path(terminal: Session) -> None:
    terminal.presenter.set_powershell_path(r"C:\PS7\pwsh.exe")
    assert terminal.presenter.set_powershell_path("")
    assert terminal.settings.powershell_path == ""
    assert terminal.sink.messages[-1] == "PowerShell: Windows PowerShell."


def test_the_powershell_cannot_be_chosen_under_a_running_program(session: Session) -> None:
    run_program(session)
    assert not session.presenter.set_powershell_path(r"C:\PS7\pwsh.exe")
    assert session.settings.powershell_path == ""
    assert session.sink.messages[-1] == "Not available while a program is running."


def test_a_powershell_that_is_gone_says_to_select_a_valid_one(terminal: Session) -> None:
    terminal.presenter.set_powershell_path(r"C:\gone\pwsh.exe")
    terminal.presenter.set_interpreter(Interpreter.POWERSHELL)
    terminal.launcher.start_error = ProgramNotFoundError("pwsh.exe")
    terminal.presenter.submit("dir")
    assert terminal.sink.messages[-1] == r"Select a valid PowerShell. Not found: C:\gone\pwsh.exe."
    assert terminal.presenter.state.phase is Phase.IDLE


def test_a_cmd_that_is_gone_is_a_program_not_found(terminal: Session) -> None:
    terminal.presenter.set_powershell_path(r"C:\gone\pwsh.exe")  # not used by Cmd
    terminal.presenter.set_interpreter(Interpreter.CMD)
    terminal.launcher.start_error = ProgramNotFoundError("cmd.exe")
    terminal.presenter.submit("dir")
    assert terminal.sink.messages[-1] == "Program not found: cmd.exe."
