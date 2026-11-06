"""The line filters: the start list on prompts, filters anywhere in a line, the first one wins."""

from dataclasses import replace

import pytest

from n5terminal.core.config.prompt_patterns import (
    START_PATTERNS,
    PromptPattern,
    as_read,
    current_pattern,
    filter_line,
    pattern_problem,
    start_patterns,
)

pytestmark = pytest.mark.unit

#: The start list without the words it says in place of the prompts: the rest of a line alone.
BARE = [replace(item, replacement="") for item in START_PATTERNS]


@pytest.mark.parametrize(
    ("line", "rest"),
    [
        (r"C:\Users\Codeur\Dev>dir /b", "dir /b"),
        (r"C:\>cd ..", "cd .."),
        (r"C:\Program Files\Git>git status", "git status"),
        (r"# C:\Users\Codeur>dir", "dir"),
        (r"PS C:\Users\Codeur\Dev\Terminal> git status", "git status"),
        (r"# PS C:\Users\Codeur> Get-ChildItem", "Get-ChildItem"),
        (r"PS HKLM:\Software> dir", "dir"),
        (r"PS C:\a b\c> echo 1 > out.txt", "echo 1 > out.txt"),
        (">> Write-Output 1", "Write-Output 1"),
        ("user@host:~$ ls -la", "ls -la"),
        ("root@debian:/etc# cat hosts", "cat hosts"),
        ("# user@host:~/my dir$ pwd", "pwd"),
        ("(venv) user@host:~/app$ python x.py", "python x.py"),
        ("user@host project % make", "make"),
        ("TestSSH@DESKTOP-L0O651J:~$ ls", "ls"),
    ],
)
def test_the_start_list_leaves_out_the_prompt_of_the_default_prompts(line: str, rest: str) -> None:
    assert as_read(line, BARE) == rest


@pytest.mark.parametrize(
    "line",
    [
        "TestSSH@DESKTOP-L0O651J:~$",  # nothing typed: the output keeps no space at the end
        "root@debian:/etc#",
        "user@host project %",
        r"PS C:\Users\x>",
        ">>",
        r"C:\Users\x>",
    ],
)
def test_a_prompt_with_nothing_typed_after_it_leaves_nothing(line: str) -> None:
    assert as_read(line, BARE) == ""


@pytest.mark.parametrize(
    "line",
    [
        "# A title of the text",
        "## Another title: with a colon>",
        "Directory of C:\\Users",
        "just some output",
        "x@y",
        "",
    ],
)
def test_a_line_that_is_not_a_prompt_is_left_as_it_is(line: str) -> None:
    assert filter_line(line, BARE) is None
    assert as_read(line, BARE) == line


@pytest.mark.parametrize(
    "line",
    [
        r"echo C:\Users\x>",  # a prompt that is not at the start of the line
        "see user@host:~$ ls",
        "a PS C:\\x> b",
    ],
)
def test_the_start_list_finds_a_prompt_at_the_start_of_the_line_only(line: str) -> None:
    assert filter_line(line, BARE) is None


def test_a_filter_without_a_circumflex_finds_its_text_anywhere_in_the_line() -> None:
    patterns = [PromptPattern("date", r"\d{4}-\d\d-\d\d")]
    assert as_read("started 2026-11-05 at noon", patterns) == "started at noon"
    assert as_read("2026-11-05 started", patterns) == "started"
    assert as_read("ended 2026-11-05", patterns) == "ended"


def test_a_word_replaces_what_is_found_in_its_place() -> None:
    patterns = [PromptPattern("date", r"\d{4}-\d\d-\d\d", "date")]
    assert as_read("started 2026-11-05 at noon", patterns) == "started date at noon"


def test_only_the_first_filter_that_finds_something_is_applied_and_nothing_cascades() -> None:
    first = PromptPattern("first", "alpha", "beta")
    second = PromptPattern("second", "beta", "gamma")
    assert as_read("alpha", [first, second]) == "beta"  # not "gamma": the second does not follow
    assert as_read("alpha", [second, first]) == "beta"
    assert as_read("beta", [first, second]) == "gamma"


def test_one_match_only_is_replaced_even_if_the_text_comes_twice() -> None:
    patterns = [PromptPattern("x", "ab", "-")]
    assert as_read("ab ab", patterns) == "- ab"


def test_the_first_filter_in_the_list_wins_over_a_later_one_that_would_also_find() -> None:
    narrow = PromptPattern("narrow", r"^PS [^>]*> ")
    short = PromptPattern("short", r"^PS ")
    line = r"PS C:\x> echo a > b"
    assert as_read(line, [narrow, short]) == "echo a > b"
    assert as_read(line, [short, narrow]) == r"C:\x> echo a > b"


def test_a_filter_that_is_not_valid_or_finds_an_empty_text_is_skipped() -> None:
    patterns = [
        PromptPattern("broken", "("),
        PromptPattern("empty", "x*"),
        PromptPattern("ok", "ls"),
    ]
    assert as_read("a ls b", patterns) == "a b"


def test_an_empty_list_leaves_every_line_whole() -> None:
    assert as_read(r"C:\x>dir", []) == r"C:\x>dir"


def test_the_replacement_is_said_in_place_of_the_prompt() -> None:
    patterns = [PromptPattern("server", r"^TestSSH@[\w.\-]+:[^$]*\$", "Debian")]
    assert as_read("TestSSH@DESKTOP-1:~$ ls", patterns) == "Debian ls"
    assert as_read("TestSSH@DESKTOP-1:~$", patterns) == "Debian"


def test_a_replacement_can_keep_a_part_of_what_is_found_through_a_group() -> None:
    named = [PromptPattern("host", r"^\w+@(?P<host>[\w\-]+):[^$]*\$", r"on \g<host>")]
    numbered = [PromptPattern("one", r"^\w+@(\w+):[^$]*\$", r"\1")]
    assert as_read("me@box:~/src$ make", named) == "on box make"
    assert as_read("me@box:~/src$ make", numbered) == "box make"


def test_a_replacement_that_names_a_group_the_filter_lacks_says_nothing_in_its_place() -> None:
    patterns = [PromptPattern("bad", r"\$ ", r"\3")]
    assert as_read("$ ls", patterns) == "ls"


def test_each_prompt_of_the_start_list_has_a_word_said_in_its_place() -> None:
    assert [item.replacement for item in START_PATTERNS] == [
        "Command",
        "Command",
        "Continuation",
        "Command",
        "Command",
    ]
    patterns = start_patterns()
    assert as_read(r"C:\Users\x>dir", patterns) == "Command dir"
    assert as_read("TestSSH@DESKTOP-L0O651J:~$ ls", patterns) == "Command ls"
    assert as_read(">> echo 1", patterns) == "Continuation echo 1"
    assert as_read("TestSSH@DESKTOP-L0O651J:~$", patterns) == "Command"


def test_every_filter_of_the_start_list_starts_at_the_start_of_the_line() -> None:
    assert all(item.pattern.startswith("^") for item in START_PATTERNS)


def test_a_filter_of_an_older_start_list_is_brought_to_the_current_one() -> None:
    older = START_PATTERNS[0].pattern.removeprefix("^")
    assert current_pattern(older) == START_PATTERNS[0].pattern
    assert current_pattern("mine") == "mine"
    assert current_pattern(START_PATTERNS[3].pattern) == START_PATTERNS[3].pattern


def test_a_pattern_is_checked_as_a_regular_expression_and_so_is_its_replacement() -> None:
    assert pattern_problem(r"PS .*> ") is None
    assert pattern_problem("") == "empty"
    assert pattern_problem("  ") == "empty"
    assert pattern_problem("(") is not None
    assert pattern_problem(r"(\w+)@", r"\1") is None
    assert pattern_problem(r"\w+@", r"\1") is not None  # no group 1
    assert pattern_problem(r"\w+@", "a word") is None
