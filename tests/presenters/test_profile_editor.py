import pytest

from n5terminal.core.config.profiles import CommandUse, Profile
from n5terminal.presenters.profile_editor import ProfileEditor

pytestmark = pytest.mark.unit


def _editor(profile: Profile | None = None, existing: list[str] | None = None) -> ProfileEditor:
    return ProfileEditor(profile or Profile(""), existing or [], lambda text: text)


def test_the_draft_starts_from_the_profile() -> None:
    profile = Profile("git", "tui", "cmd", "100x30", True, ["name"], ["git status"])
    editor = _editor(profile)
    assert (editor.name, editor.launch_mode, editor.interpreter) == ("git", "tui", "cmd")
    assert (editor.terminal_size, editor.terminal_view_only) == ("100x30", True)
    assert (editor.variables, editor.commands) == (["name"], ["git status"])
    assert not editor.is_new
    assert editor.replaces == "git"


def test_the_program_is_kept_and_built_without_its_spaces_around() -> None:
    editor = _editor(Profile("git", program="git"))
    assert editor.program == "git"
    editor.program = r"  C:\Tools\git.exe  "
    assert editor.build().program == r"C:\Tools\git.exe"


def test_the_prompt_prefix_is_kept_with_its_spaces_and_only_means_something_with_a_shell() -> None:
    editor = _editor(Profile("c", interpreter="cmd", prompt_prefix="# "))
    assert editor.prompt_prefix == "# "
    assert editor.prompt_prefix_enabled
    assert editor.build().prompt_prefix == "# "
    editor.interpreter = "none"
    assert not editor.prompt_prefix_enabled


def test_a_profile_without_a_name_is_new() -> None:
    editor = _editor()
    assert editor.is_new
    assert editor.replaces is None


def test_the_variables_are_listed_with_their_text_to_write() -> None:
    lines = _editor().variable_lines()
    assert lines[0] == ("name", "Name, {name}")
    assert [variable for variable, _line in lines] == [
        "name",
        "source",
        "destination",
        "value1",
        "value2",
        "comment",
        "ip",
        "message",
    ]
    assert lines[7][1] == "Message, {message}"
    assert lines[3][1] == "Value 1, {value1}"


def test_the_variables_are_kept_in_the_usual_order_and_unknown_ones_dropped() -> None:
    editor = _editor()
    editor.set_variables(["value2", "bogus", "name"])
    assert editor.variables == ["name", "value2"]


def test_the_mode_is_greyed_with_a_shell() -> None:
    editor = _editor()
    assert editor.mode_enabled
    editor.interpreter = "powershell"
    assert not editor.mode_enabled


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("", "The name cannot be empty."),
        ("a" * 11, "The name cannot be longer than 10 characters."),
        ("a/b", "The character / is not allowed in a name."),
        ("con", "The name cannot hold any of these characters"),
        ("end.", "The name cannot hold any of these characters"),
        ("taken", "Another profile already has this name."),
    ],
)
def test_a_name_refused_says_why(name: str, text: str) -> None:
    editor = _editor(existing=["Taken"])
    editor.name = name
    message = editor.name_message()
    assert message is not None
    assert message.startswith(text)


def test_a_good_name_is_accepted() -> None:
    editor = _editor(existing=["git"])
    editor.name = "npm"
    assert editor.name_message() is None


def test_the_profile_keeps_its_own_name_when_edited() -> None:
    editor = _editor(Profile("git"), existing=["git", "npm"])
    assert editor.name_message() is None
    editor.name = "npm"
    assert editor.name_message() is not None


def test_commands_are_added_replaced_and_removed() -> None:
    editor = _editor()
    assert editor.add_command("one") == 0
    assert editor.add_command("two") == 1
    assert editor.add_command("  ") is None
    assert editor.replace_command(0, "uno") == 1  # "two" now comes first
    assert editor.replace_command(0, " ") is None
    assert editor.replace_command(5, "x") is None
    assert editor.commands == ["two", "uno"]
    assert editor.remove_command(0) == 0
    assert editor.remove_command(0) is None
    assert editor.remove_command(0) is None
    assert editor.commands == []


def test_removing_the_last_command_selects_the_one_before() -> None:
    editor = _editor(Profile("p", commands=["a", "b", "c"]))
    assert editor.remove_command(2) == 1


def test_build_makes_the_profile_and_keeps_unknown_keys() -> None:
    editor = _editor(Profile("git", extra={"folder": "C:\\p"}))
    editor.name = "g2"
    editor.terminal_view_only = True
    editor.add_command("git status")
    profile = editor.build()
    assert profile == Profile(
        "g2", terminal_view_only=True, commands=["git status"], extra={"folder": "C:\\p"}
    )
    assert editor.replaces == "git"


def test_the_program_only_means_something_without_a_shell() -> None:
    editor = _editor(Profile("g", program="git"))
    assert editor.program_enabled
    editor.interpreter = "powershell"
    assert not editor.program_enabled
    assert editor.build().program == "git"  # kept in the file, ignored while a shell is chosen


def test_the_commands_are_kept_in_alphabetical_order_whatever_the_case() -> None:
    editor = _editor(Profile("p", commands=["pull", "Get-Help", "dir", "add"]))
    assert editor.commands == ["add", "dir", "Get-Help", "pull"]
    assert editor.add_command("fetch") == 2
    assert editor.add_command("Branch") == 1
    assert editor.commands == ["add", "Branch", "dir", "fetch", "Get-Help", "pull"]
    assert editor.replace_command(0, "zip") == 5
    assert editor.commands == ["Branch", "dir", "fetch", "Get-Help", "pull", "zip"]
    assert editor.build().commands == editor.commands


def test_the_list_shows_one_use_at_a_time_and_add_and_edit_work_on_it() -> None:
    profile = Profile("p", commands=["push"], program_commands=["/select", "/clear"])
    editor = _editor(profile)
    assert editor.use is CommandUse.LAUNCH
    assert editor.commands == ["push"]
    editor.use = CommandUse.PROGRAM
    assert editor.commands == ["/clear", "/select"]
    assert editor.add_command("/help") == 1
    assert editor.replace_command(0, "/zoom") == 2
    built = editor.build()
    assert built.commands == ["push"]
    assert built.program_commands == ["/help", "/select", "/zoom"]
    assert built.shell_commands == []


def test_the_list_starts_on_the_first_use_that_has_commands() -> None:
    assert _editor(Profile("p", interpreter="cmd", shell_commands=["dir"])).use is CommandUse.SHELL
    assert _editor(Profile("p", program_commands=["/a"])).use is CommandUse.PROGRAM
    assert _editor(Profile("p")).use is CommandUse.LAUNCH


def test_the_uses_are_offered_with_their_words_and_a_shell_has_only_shell() -> None:
    editor = _editor()
    assert [name for _use, name in editor.use_choices()] == ["Launch command", "Program command"]
    editor.interpreter = "cmd"
    assert [name for _use, name in editor.use_choices()] == ["Shell"]


def test_changing_the_shell_moves_the_commands_to_the_uses_it_offers_and_loses_none() -> None:
    editor = _editor(Profile("p", commands=["push"], program_commands=["/select", "push"]))
    editor.interpreter = "cmd"
    assert editor.commands == ["/select", "push"]
    editor.interpreter = "none"
    assert editor.use is CommandUse.LAUNCH
    built = editor.build()
    assert (built.commands, built.program_commands) == (["/select", "push"], ["/select", "push"])
    assert built.shell_commands == []


def test_a_command_already_in_the_list_is_refused_on_add_and_on_edit() -> None:
    editor = _editor(Profile("p", commands=["pull", "push"], program_commands=["pull"]))
    assert editor.duplicate_index("push") == 1
    assert editor.duplicate_index("push", skip=1) is None
    assert editor.duplicate_index("fetch") is None
    assert editor.add_command("push") is None
    assert editor.replace_command(0, "push") is None
    assert editor.commands == ["pull", "push"]
    assert editor.replace_command(1, "push") == 1  # itself is not a duplicate
    editor.use = CommandUse.PROGRAM
    assert editor.add_command("push") == 1  # another type may have the same text


def test_a_character_outside_the_list_is_named_in_the_message() -> None:
    editor = _editor()
    editor.name = "a&b"
    message = editor.name_message()
    assert message is not None
    assert "The character & is not allowed in a name" in message
    assert "- _ . + # ( ) @" in message


def test_an_invisible_character_is_named_by_its_name() -> None:
    editor = _editor()
    editor.name = "a" + chr(0x200B) + "b"
    message = editor.name_message()
    assert message is not None
    assert "zero width space" in message


def test_the_name_of_an_existing_profile_is_not_refused_while_it_is_not_changed() -> None:
    editor = _editor(Profile("old&one"), existing=["old&one"])
    assert editor.name_message() is None
    editor.name = "new&one"
    assert editor.name_message() is not None
