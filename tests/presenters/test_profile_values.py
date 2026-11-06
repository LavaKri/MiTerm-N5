import pytest

from n5terminal.core.config.profiles import Profile
from n5terminal.presenters.profile_values import ProfileValues

pytestmark = pytest.mark.unit

GIT = Profile("git", commands=["git switch {name}", "git status"], variables=["name"])


def test_with_the_free_profile_there_is_nothing() -> None:
    values = ProfileValues()
    assert values.variables() == []
    assert values.commands() == []


def test_the_chosen_profile_gives_its_variables_and_its_commands() -> None:
    values = ProfileValues()
    values.choose(GIT)
    assert values.variables() == ["name"]
    assert values.commands() == ["git switch {name}", "git status"]
    values.choose(None)
    assert values.commands() == []


def test_the_values_fill_the_commands_of_their_own_profile() -> None:
    values = ProfileValues()
    values.set("git", {"name": "dev"})
    values.choose(GIT)
    assert values.commands() == ["git switch dev", "git status"]
    values.choose(Profile("other", commands=["run {name}"]))
    assert values.commands() == ["run {name}"]


def test_without_a_program_the_lines_are_the_commands() -> None:
    values = ProfileValues()
    values.choose(GIT)
    assert [(e.label, e.text) for e in values.entries()] == [
        ("git switch {name}", "git switch {name}"),
        ("git status", "git status"),
    ]
    values.choose(None)
    assert values.entries() == []


def test_with_a_program_a_line_says_its_name_and_writes_only_the_arguments() -> None:
    values = ProfileValues()
    values.set("git", {"name": "dev"})
    git = Profile(
        "git",
        program=r"C:\Program Files\Git\bin\Git.exe",
        commands=["switch {name}", "status"],
        variables=["name"],
    )
    values.choose(git)
    assert [(e.label, e.text) for e in values.entries()] == [
        ("Git switch dev", "switch dev"),
        ("Git status", "status"),
    ]
    values.on_server = True  # typed to a shell: the name of the program comes first
    assert [e.text for e in values.entries()] == ["Git switch dev", "Git status"]


def test_a_program_given_by_its_name_is_said_as_it_is() -> None:
    values = ProfileValues()
    values.choose(Profile("g", program="git", commands=["pull"]))
    assert [(e.label, e.text) for e in values.entries()] == [("git pull", "pull")]


def test_the_values_given_back_are_a_copy() -> None:
    values = ProfileValues()
    given = {"name": "dev"}
    values.set("git", given)
    given["name"] = "changed"
    values.get("git")["name"] = "changed"
    assert values.get("git") == {"name": "dev"}
    assert values.get("unknown") == {}


def test_the_values_follow_a_renamed_profile_and_go_with_a_deleted_one() -> None:
    values = ProfileValues()
    values.set("old", {"name": "dev"})
    values.rename("old", "new")
    assert values.get("old") == {}
    assert values.get("new") == {"name": "dev"}
    values.rename("none", "other")  # nothing to move
    values.forget("new")
    values.forget("new")  # already gone
    assert values.get("new") == {}


def _values_of(profile: Profile) -> ProfileValues:
    values = ProfileValues()
    values.choose(profile)
    return values


MIXED = Profile(
    "claude",
    program="claude",
    commands=["--resume"],
    program_commands=["/select"],
    shell_commands=["/help"],
)


def test_with_no_program_running_the_list_has_the_launch_and_shell_commands_as_arguments() -> None:
    entries = _values_of(MIXED).entries()
    assert [(e.label, e.text) for e in entries] == [
        ("claude --resume", "--resume"),
        ("claude /help", "/help"),
    ]


def test_the_arguments_are_found_in_a_line_launched_with_the_program() -> None:
    values = _values_of(Profile("g", program=r"C:\Program Files\Git\git.exe"))
    program = r'"C:\Program Files\Git\git.exe"'
    assert values.takes_arguments
    assert values.arguments_of(f"{program} status") == "status"
    assert values.arguments_of(program) == ""
    assert values.arguments_of("ping host") is None
    assert values.arguments_of(f"{program}x status") is None
    values.on_server = True
    assert not values.takes_arguments


def test_with_a_program_running_the_list_has_its_commands_and_those_for_both_as_they_are() -> None:
    entries = _values_of(MIXED).entries(running=True)
    assert [(e.label, e.text) for e in entries] == [("/select", "/select"), ("/help", "/help")]


def test_the_variables_are_replaced_in_every_use() -> None:
    values = _values_of(Profile("p", program_commands=["/go {name}"]))
    values.set("p", {"name": "dev"})
    assert [e.text for e in values.entries(running=True)] == ["/go dev"]
