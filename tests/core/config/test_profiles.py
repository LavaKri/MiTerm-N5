import json
from pathlib import Path

import pytest

from n5terminal.core.config.profiles import (
    MAX_NAME_LENGTH,
    CommandUse,
    NameProblem,
    Profile,
    ProfileStore,
    expand_variables,
    first_disallowed_character,
    full_command,
    name_problem,
    program_name,
)
from n5terminal.core.errors import ProfileError

pytestmark = pytest.mark.unit


# Names -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "problem"),
    [
        ("git", None),
        ("Projet été", None),
        ("", NameProblem.EMPTY),
        ("   ", NameProblem.EMPTY),
        ("a" * (MAX_NAME_LENGTH + 1), NameProblem.TOO_LONG),
        ("a/b", NameProblem.FORBIDDEN_CHARACTER),
        ('a"b', NameProblem.FORBIDDEN_CHARACTER),
        ("a\tb", NameProblem.FORBIDDEN_CHARACTER),
        ("end.", NameProblem.FORBIDDEN_CHARACTER),
        (" lead", NameProblem.FORBIDDEN_CHARACTER),
        ("CON", NameProblem.FORBIDDEN_CHARACTER),
        ("nul.txt", NameProblem.FORBIDDEN_CHARACTER),
    ],
)
def test_name_problem(name: str, problem: NameProblem | None) -> None:
    assert name_problem(name, taken=[]) is problem


def test_a_taken_name_is_refused_whatever_its_case() -> None:
    assert name_problem("GIT", taken=["git"]) is NameProblem.TAKEN


def test_the_profile_being_edited_does_not_take_its_own_name() -> None:
    assert name_problem("git", taken=["git"], current="git") is None
    assert name_problem("GIT", taken=["git"], current="git") is None
    assert name_problem("npm", taken=["git", "npm"], current="git") is NameProblem.TAKEN


# Variables -------------------------------------------------------------------------------------


def test_a_variable_with_a_value_is_replaced() -> None:
    values = {"source": "a.txt", "destination": "b.txt"}
    assert expand_variables("copy {source} {Destination}", values) == "copy a.txt b.txt"


def test_a_variable_without_a_value_stays_as_it_is() -> None:
    assert (
        expand_variables("copy {source} {destination}", {"source": "a"}) == "copy a {destination}"
    )
    assert expand_variables("echo {name}", {"name": ""}) == "echo {name}"


def test_other_braces_are_left_alone() -> None:
    command = "git show HEAD@{1} && echo {other} {source}"
    assert expand_variables(command, {"source": "x"}) == "git show HEAD@{1} && echo {other} x"


def test_a_variable_is_replaced_everywhere_it_appears() -> None:
    command = "git switch {name} && git push origin {NAME} # {name}"
    expected = "git switch dev && git push origin dev # dev"
    assert expand_variables(command, {"name": "dev"}) == expected


def test_comment_ip_and_message_are_variables_whatever_their_case() -> None:
    values = {"comment": "a@b.fr", "ip": "10.0.0.1", "message": "fix the bug"}
    command = 'ssh {Comment}@{IP} "{message}"'
    assert expand_variables(command, values) == 'ssh a@b.fr@10.0.0.1 "fix the bug"'


def test_a_value_is_not_expanded_again() -> None:
    assert expand_variables("{name}", {"name": "{source}", "source": "x"}) == "{source}"


# The files -------------------------------------------------------------------------------------


def _full() -> Profile:
    return Profile(
        "git",
        launch_mode="tui",
        interpreter="cmd",
        terminal_size="120x30",
        terminal_view_only=True,
        variables=["name", "source"],
        shell_commands=["git status", "git switch {name}"],
        stderr_prefix=False,
        program=r"C:\Tools\Git.exe",
        prompt_prefix="# ",
    )


@pytest.mark.parametrize(
    ("program", "name"),
    [
        ("git", "git"),
        ("Git.exe", "Git"),
        (r"C:\Program Files\Git\bin\git.exe", "git"),
        ('"C:\\My Tools\\Run.cmd"', "Run"),
        ("  ", ""),
        ("", ""),
    ],
)
def test_a_program_is_said_by_its_name_alone(program: str, name: str) -> None:
    assert program_name(program) == name


@pytest.mark.parametrize(
    ("program", "line"),
    [
        ("", "status"),
        ("git", "git status"),
        (r"C:\Tools\git.exe", r"C:\Tools\git.exe status"),
        (r"C:\Program Files\Git\git.exe", r'"C:\Program Files\Git\git.exe" status'),
        (r'"C:\Program Files\Git\git.exe"', r'"C:\Program Files\Git\git.exe" status'),
    ],
)
def test_the_command_line_has_the_program_in_front_between_quotes_if_it_has_a_space(
    program: str, line: str
) -> None:
    assert full_command(program, "status") == line


def test_a_program_that_is_not_text_is_ignored() -> None:
    assert Profile.from_data("p", {"program": 3}).program == ""
    assert Profile.from_data("p", {"program": " git "}).program == "git"


def test_the_prompt_prefix_is_kept_as_written_and_ignored_when_it_is_not_text() -> None:
    assert Profile.from_data("p", {"prompt_prefix": "# "}).prompt_prefix == "# "
    assert Profile.from_data("p", {"prompt_prefix": 3}).prompt_prefix == ""
    assert Profile.from_data("p", {}).prompt_prefix == ""


def test_a_profile_survives_a_save(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path / "profiles")
    store.save(_full())
    loaded = store.load_all()
    assert loaded.warnings == []
    assert loaded.profiles == [_full()]


def test_a_missing_folder_means_no_profile(tmp_path: Path) -> None:
    loaded = ProfileStore(tmp_path / "none").load_all()
    assert (loaded.profiles, loaded.warnings) == ([], [])


def test_the_profiles_are_sorted_by_name_whatever_the_case(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    for name in ("npm", "Git", "docker"):
        store.save(Profile(name))
    assert [p.name for p in store.load_all().profiles] == ["docker", "Git", "npm"]


def test_values_of_the_wrong_kind_are_ignored(tmp_path: Path) -> None:
    bad = {
        "launch_mode": "gui",
        "interpreter": 3,
        "terminal_size": "big",
        "terminal_view_only": "yes",
        "stderr_prefix": 0,
        "variables": ["SOURCE", "bogus", "name"],
        "commands": ["ok", "", 5, "  "],
    }
    (tmp_path / "x.json").write_text(json.dumps(bad), encoding="utf-8")
    profile = ProfileStore(tmp_path).load_all().profiles[0]
    assert profile == Profile("x", variables=["name", "source"], commands=["ok"])


def test_unknown_keys_are_kept_when_the_profile_is_written_again(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text(json.dumps({"folder": "C:\\p"}), encoding="utf-8")
    store = ProfileStore(tmp_path)
    store.save(store.load_all().profiles[0])
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["folder"] == "C:\\p"


def test_a_damaged_file_is_reported_and_the_others_are_still_listed(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.save(Profile("good"))
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    loaded = store.load_all()
    assert [p.name for p in loaded.profiles] == ["good"]
    assert len(loaded.warnings) == 1
    assert (tmp_path / "bad.json.corrupt").exists()


def test_renaming_removes_the_old_file(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.save(Profile("old"))
    store.save(Profile("new"), replaces="old")
    assert [p.name for p in store.load_all().profiles] == ["new"]
    assert not (tmp_path / "old.json").exists()


def test_changing_only_the_case_of_a_name_keeps_the_file(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.save(Profile("git"))
    store.save(Profile("Git"), replaces="git")
    assert len(store.load_all().profiles) == 1


def test_delete_removes_the_file_and_its_backup(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.save(Profile("git"))
    store.save(Profile("git", terminal_view_only=True))  # makes a .bak
    assert (tmp_path / "git.json.bak").exists()
    store.delete("git")
    assert list(tmp_path.iterdir()) == []


def test_deleting_a_profile_that_is_gone_is_not_an_error(tmp_path: Path) -> None:
    ProfileStore(tmp_path).delete("nothing")


def test_an_unwritable_folder_raises_a_profile_error(tmp_path: Path) -> None:
    blocker = tmp_path / "profiles"
    blocker.write_text("a file, not a folder", encoding="utf-8")
    with pytest.raises(ProfileError):
        ProfileStore(blocker).save(Profile("git"))


def test_the_commands_are_sorted_when_read_and_when_written(tmp_path: Path) -> None:
    profile = Profile.from_data("p", {"commands": ["pull", "Get-Help", "dir", "add"]})
    assert profile.commands == ["add", "dir", "Get-Help", "pull"]
    unsorted = Profile("p", commands=["b", "A", "c"])
    assert unsorted.to_data()["commands"] == ["A", "b", "c"]
    store = ProfileStore(tmp_path)
    store.save(unsorted)
    written = json.loads((tmp_path / "p.json").read_text(encoding="utf-8"))
    assert written["commands"] == ["A", "b", "c"]


def test_a_command_with_no_use_is_a_launch_command_and_the_others_have_theirs() -> None:
    profile = Profile.from_data(
        "p",
        {
            "commands": [
                "push",
                {"text": "/select", "use": "program"},
                {"text": "dir", "use": "both"},
                {"text": "old", "use": "launch"},
                {"text": "odd", "use": "nothing"},
                {"text": "  ", "use": "program"},
                {"use": "program"},
                3,
            ]
        },
    )
    # no shell: a Shell command is typed in either state, so it joins both lists
    assert profile.commands == ["dir", "odd", "old", "push"]
    assert profile.program_commands == ["/select", "dir"]
    assert profile.shell_commands == []


def test_a_profile_with_a_shell_has_only_shell_commands_and_the_old_word_is_read() -> None:
    profile = Profile.from_data(
        "p",
        {
            "interpreter": "cmd",
            "commands": [
                "push",
                {"text": "/select", "use": "program"},
                {"text": "dir", "use": "both"},
                {"text": "ver", "use": "shell"},
            ],
        },
    )
    assert (profile.commands, profile.program_commands) == ([], [])
    assert profile.shell_commands == ["/select", "dir", "push", "ver"]
    assert {"text": "dir", "use": "shell"} in profile.to_data()["commands"]  # type: ignore[operator]


def test_the_file_keeps_a_launch_command_as_a_text_and_sorts_all_the_commands() -> None:
    profile = Profile("p", commands=["Add", "push"], program_commands=["/select", "dir"])
    assert profile.to_data()["commands"] == [
        {"text": "/select", "use": "program"},  # "/" sorts before the letters
        "Add",
        {"text": "dir", "use": "program"},
        "push",
    ]
    assert Profile.from_data("p", profile.to_data()) == profile
    assert profile.commands_of(CommandUse.PROGRAM) == ["/select", "dir"]


def test_the_old_email_variable_is_read_as_comment() -> None:
    profile = Profile.from_data(
        "k",
        {
            "variables": ["name", "email"],
            "commands": ['-C "{email}"', {"text": "x {Email}", "use": "program"}],
        },
    )
    assert profile.variables == ["name", "comment"]
    assert profile.commands == ['-C "{comment}"']
    assert profile.program_commands == ["x {comment}"]


@pytest.mark.parametrize(
    "name", ["git", "Mon outil", "C++", "a#1", "(test)", "x_y-z.1", "é", "me@work"]
)
def test_a_name_of_letters_digits_spaces_and_a_few_signs_is_allowed(name: str) -> None:
    assert name_problem(name, taken=[], strict=True) is None


@pytest.mark.parametrize(
    ("name", "character"),
    [
        ("a&b", "&"),
        ("a%", "%"),
        ("x" + chr(0x200B), chr(0x200B)),
        ("a" + chr(0x301), chr(0x301)),
        ("😀", "😀"),
        ("a/b", "/"),
        ("a	b", "	"),
        ("a=b", "="),
    ],
)
def test_any_other_character_is_refused_with_the_first_one_found(name: str, character: str) -> None:
    assert name_problem(name, taken=[], strict=True) is NameProblem.NOT_ALLOWED
    assert first_disallowed_character(name) == character


def test_the_list_of_characters_only_applies_when_asked() -> None:
    assert name_problem("a&b", taken=[]) is None  # the connections keep their own rules
