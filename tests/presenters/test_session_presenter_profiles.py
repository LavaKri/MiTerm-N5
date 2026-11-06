"""Choosing a profile in the session presenter: what it sets, what it commands offers."""

import pytest

from fakes.session_support import Session, end_program, run_program, start_shell
from n5terminal.core.config.profiles import Profile
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode

pytestmark = pytest.mark.unit

GIT = Profile(
    "git",
    launch_mode="tui",
    interpreter="powershell",
    terminal_size="120x30",
    commands=["git status", "git switch {name}", "git push {NAME} {source}"],
)


def test_a_profile_replaces_the_mode_the_interpreter_and_the_size(session: Session) -> None:
    assert session.presenter.select_profile(GIT)
    state = session.presenter.state
    assert (state.profile, state.interpreter) == ("git", Interpreter.POWERSHELL)
    assert state.launch_mode is LaunchMode.TUI
    run_program(session)
    assert session.launcher.calls[0].size.columns == 120


def test_the_stderr_prefix_comes_from_the_settings_then_from_the_profile(session: Session) -> None:
    run_program(session)
    end_program(session)
    session.presenter.select_profile(Profile("quiet", stderr_prefix=False))
    run_program(session)
    assert [call.mark_stderr for call in session.launcher.calls] == [True, False]
    assert session.presenter.session_values().stderr_prefix is False


def test_a_profile_is_not_announced(session: Session) -> None:
    session.presenter.select_profile(GIT)
    assert session.sink.messages == []


def test_the_title_tells_the_profile_and_the_folder(session: Session) -> None:
    assert session.view.titles[-1] == f"MiTerm-N5: free profile in {session.folder.name}"
    session.presenter.select_profile(GIT)
    assert session.view.titles[-1] == f"MiTerm-N5: git in {session.folder.name}"
    session.presenter.select_profile(None)
    assert session.view.titles[-1] == f"MiTerm-N5: free profile in {session.folder.name}"


def test_the_status_bar_does_not_tell_the_profile(session: Session) -> None:
    session.presenter.select_profile(GIT)
    assert session.view.last_state == "Ready"


def test_the_free_profile_keeps_the_values_in_use(session: Session) -> None:
    session.presenter.select_profile(GIT)
    assert session.presenter.select_profile(None)
    state = session.presenter.state
    assert state.profile is None
    assert (state.interpreter, state.launch_mode) == (Interpreter.POWERSHELL, LaunchMode.TUI)
    assert session.presenter.profile_values.commands() == []


def test_a_profile_cannot_be_chosen_under_a_running_program(session: Session) -> None:
    run_program(session)
    assert not session.presenter.select_profile(GIT)
    assert session.presenter.state.profile is None
    assert session.sink.messages[-1] == "Not available while a program is running."


def test_the_commands_of_the_profile_get_the_values_of_the_variables(session: Session) -> None:
    session.presenter.select_profile(GIT)
    assert session.presenter.profile_values.commands() == [
        "git status",
        "git switch {name}",
        "git push {NAME} {source}",
    ]
    session.presenter.profile_values.set("git", {"name": "dev", "source": "origin"})
    assert session.presenter.profile_values.commands() == [
        "git status",
        "git switch dev",
        "git push dev origin",
    ]


def test_the_list_selects_the_last_command_typed_with_the_profile_commands_below(
    session: Session,
) -> None:
    run_program(session, "first")
    end_program(session)
    run_program(session, "second")
    end_program(session)
    session.presenter.select_profile(Profile("p", commands=["one", "two"]))
    entries, selected = session.presenter.command_list()
    assert ([entry.label for entry in entries], selected) == (["first", "second", "one", "two"], 1)
    assert [entry.text for entry in entries] == ["first", "second", "one", "two"]


def test_without_history_the_list_starts_on_its_first_line(session: Session) -> None:
    assert session.presenter.command_list() == ([], 0)
    session.presenter.select_profile(Profile("p", commands=["one", "two"]))
    entries, selected = session.presenter.command_list()
    assert ([entry.label for entry in entries], selected) == (["one", "two"], 0)


def test_the_state_knows_whether_the_profile_uses_variables(session: Session) -> None:
    session.presenter.select_profile(Profile("p", variables=["name", "source"]))
    assert session.presenter.state.has_variables
    assert session.presenter.profile_values.variables() == ["name", "source"]
    session.presenter.select_profile(Profile("q"))
    assert not session.presenter.state.has_variables
    session.presenter.select_profile(None)
    assert session.presenter.profile_values.variables() == []


def test_the_values_follow_a_renamed_profile_and_go_with_a_deleted_one(session: Session) -> None:
    session.presenter.profile_values.set("old", {"name": "dev"})
    session.presenter.profile_values.rename("old", "new")
    assert session.presenter.profile_values.get("old") == {}
    assert session.presenter.profile_values.get("new") == {"name": "dev"}
    session.presenter.profile_values.forget("new")
    assert session.presenter.profile_values.get("new") == {}
    session.presenter.profile_values.rename("none", "other")  # nothing to move: no error


PROGRAM_PROFILE = Profile("git", program=r"C:\Program Files\Git\Git.exe", commands=["status"])


def test_the_program_of_the_profile_is_launched_and_shown_by_its_name(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    assert session.presenter.state.has_program
    assert session.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    session.presenter.tick()
    assert session.launcher.calls[0].arguments == (r"C:\Program Files\Git\Git.exe",)
    assert "# Git" in session.view.fixed_lines()


def test_without_a_profile_the_program_cannot_be_launched(session: Session) -> None:
    assert not session.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    assert session.sink.messages == ["No profile is chosen."]
    assert session.launcher.calls == []


def test_a_profile_without_a_program_cannot_launch_one(session: Session) -> None:
    session.presenter.select_profile(Profile("p", commands=["git status"]))
    assert not session.presenter.state.has_program
    assert not session.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    assert session.sink.messages == ["The chosen profile has no program."]


def test_the_program_cannot_be_launched_while_another_runs(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    run_program(session)
    session.sink.messages.clear()
    assert not session.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    assert session.sink.messages == ["Not available while a program is running."]


def test_the_free_profile_has_no_program(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    session.presenter.select_profile(None)
    assert not session.presenter.state.has_program


def test_the_values_belong_to_their_profile(session: Session) -> None:
    session.presenter.profile_values.set("git", {"name": "dev"})
    session.presenter.select_profile(Profile("npm", commands=["npm run {name}"]))
    assert session.presenter.profile_values.commands() == ["npm run {name}"]


def test_a_profile_with_a_shell_has_no_program(session: Session) -> None:
    profile = Profile("c", interpreter="cmd", program="git", commands=["status"])
    session.presenter.select_profile(profile)
    assert not session.presenter.state.has_program
    assert not session.presenter.run_command(CommandId.LAUNCH_PROGRAM)
    assert session.presenter.profile_values.program() == ""
    assert [entry.text for entry in session.presenter.profile_values.entries()] == ["status"]


MIXED = Profile(
    "claude",
    program="claude",
    commands=["--resume"],
    program_commands=["/select"],
    shell_commands=["/help"],
)


def test_the_list_follows_the_state_of_the_session(session: Session) -> None:
    session.presenter.select_profile(MIXED)
    entries, _selected = session.presenter.command_list()
    assert [entry.text for entry in entries] == ["--resume", "/help"]
    run_program(session)
    entries, _selected = session.presenter.command_list()
    assert [entry.text for entry in entries] == ["/select", "/help"]
    end_program(session)
    entries, _selected = session.presenter.command_list()
    # what was typed in the field was the arguments of claude: the history gives them back as such
    assert [entry.text for entry in entries] == ["ping host", "--resume", "/help"]


def test_the_lines_typed_in_a_shell_are_program_commands_in_the_history(terminal: Session) -> None:
    start_shell(terminal, "dir")
    terminal.presenter.submit("cd ..")
    running, _selected = terminal.presenter.command_list()
    assert [entry.text for entry in running] == ["cd .."]
    terminal.transport.exit(0)
    terminal.presenter.tick()
    idle, _selected = terminal.presenter.command_list()
    assert [entry.text for entry in idle] == ["dir"]


# The command field with the program of a profile ------------------------------------------------


def test_with_a_program_the_field_holds_its_arguments(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    session.presenter.submit("status")
    session.presenter.tick()
    assert session.launcher.calls[0].arguments == (r"C:\Program Files\Git\Git.exe", "status")
    assert "# Git" in session.view.fixed_lines()


def test_with_a_program_an_empty_field_launches_the_program_alone(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    session.presenter.submit("")
    session.presenter.tick()
    assert session.launcher.calls[0].arguments == (r"C:\Program Files\Git\Git.exe",)


def test_without_the_program_of_a_profile_the_field_holds_the_whole_command(
    session: Session,
) -> None:
    session.presenter.select_profile(Profile("free", commands=["x"]))
    session.presenter.submit("ping host")
    session.presenter.tick()
    assert session.launcher.calls[0].arguments == ("ping", "host")


def test_sending_again_puts_the_program_in_front_once(session: Session) -> None:
    session.presenter.select_profile(PROGRAM_PROFILE)
    session.presenter.submit("status")
    session.presenter.tick()
    end_program(session)
    assert session.presenter.run_command(CommandId.RESEND)
    session.presenter.tick()
    assert session.launcher.calls[1].arguments == (r"C:\Program Files\Git\Git.exe", "status")


def test_the_field_is_named_after_the_state_and_the_profile(session: Session) -> None:
    assert session.view.input_labels[-1] == "Command"
    session.presenter.select_profile(PROGRAM_PROFILE)
    assert session.view.input_labels[-1] == "git"
    run_program(session)
    assert session.view.input_labels[-1] == "Message"
    end_program(session)
    session.presenter.select_profile(Profile("c", interpreter="cmd", program="git"))
    assert session.view.input_labels[-1] == "Command"
