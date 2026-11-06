"""A line said without its prompt, and the editor of the list of patterns."""

from dataclasses import replace

import pytest

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.prompt_patterns import START_PATTERNS, PromptPattern
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import Mode
from n5terminal.presenters.comfort_reading import ComfortReader
from n5terminal.presenters.prompt_patterns_editor import PromptPatternsEditor

pytestmark = pytest.mark.unit


class Said:
    def __init__(self) -> None:
        self.calls: list[tuple[Announce, dict[str, object]]] = []

    def __call__(self, announce: Announce, **values: object) -> None:
        self.calls.append((announce, values))


def reader(said: Said, formatting: bool = False) -> ComfortReader:
    settings = Settings.load(None)
    settings.comfort_formatting = formatting
    settings.prompt_patterns = [replace(item, replacement="") for item in START_PATTERNS]
    return ComfortReader(said, settings)


def test_the_replacement_is_said_in_place_of_the_prompt() -> None:
    said = Said()
    settings = Settings.load(None)
    settings.prompt_patterns = [PromptPattern("srv", r"\w+@[\w\-]+:[^$]*\$", "Debian")]
    comfortable = ComfortReader(said, settings)
    comfortable.read("me@box:~$ ls", Mode.TERMINAL_LINE)
    comfortable.read("me@box:~$", Mode.TERMINAL_LINE)
    assert [call[1]["text"] for call in said.calls] == ["Debian ls", "Debian"]


def test_a_line_is_said_without_its_prompt() -> None:
    said = Said()
    reader(said).read(r"PS C:\Users\x> git status", Mode.TERMINAL_LINE)
    assert said.calls == [(Announce.COMFORT_LINE, {"text": "git status", "line": "git status"})]


def test_a_line_with_no_known_prompt_is_said_as_it_is() -> None:
    said = Said()
    reader(said).read("Everything is fine", Mode.TERMINAL_LINE)
    assert said.calls[0][1]["text"] == "Everything is fine"


def test_a_prompt_alone_and_an_empty_line_are_both_said_as_blank() -> None:
    said = Said()
    comfortable = reader(said)
    comfortable.read(r"PS C:\Users\x> ", Mode.TERMINAL_LINE)
    comfortable.read("", Mode.TERMINAL_LINE)
    assert [call[1]["text"] for call in said.calls] == ["blank", "blank"]


def test_the_formatting_of_the_read_the_line_key_is_kept_when_asked() -> None:
    said = Said()
    reader(said, formatting=True).read(r"C:\x>Download 40%", Mode.TERMINAL_LINE)
    text = str(said.calls[0][1]["text"])
    assert text != "Download 40%"  # the progress is read as an element, as the key does
    assert "40" in text
    assert said.calls[0][1]["line"] == "Download 40%"  # the line alone, for the other destination


def test_without_the_formatting_only_the_prompt_is_left_out() -> None:
    said = Said()
    reader(said, formatting=False).read(r"C:\x>Download 40%", Mode.TERMINAL_LINE)
    assert said.calls[0][1]["text"] == "Download 40%"


def editor(patterns: list[PromptPattern] | None = None) -> PromptPatternsEditor:
    return PromptPatternsEditor(
        list(START_PATTERNS) if patterns is None else patterns, False, False, lambda text: text
    )


def test_a_pattern_is_added_at_the_end_edited_and_removed() -> None:
    draft = editor([])
    assert draft.add("mine", r"\$ ") == 0
    assert draft.add("other", r"> ") == 1
    assert draft.replace(0, "mine", r"\$\$ ")
    assert draft.patterns[0].pattern == r"\$\$ "
    assert draft.remove(0) == 0
    assert draft.names() == ["other"]
    assert draft.remove(0) is None


def test_the_order_is_changed_by_moving_a_pattern_up_or_down() -> None:
    draft = editor([PromptPattern("a", "a"), PromptPattern("b", "b"), PromptPattern("c", "c")])
    assert draft.move(2, -1) == 1
    assert draft.names() == ["a", "c", "b"]
    assert draft.move(0, -1) == 0  # already first
    assert draft.move(2, 1) == 2  # already last
    assert draft.move(0, 1) == 1
    assert draft.names() == ["c", "a", "b"]


def test_a_name_or_a_pattern_that_cannot_be_is_refused_with_the_reason() -> None:
    draft = editor([PromptPattern("Mine", "x")])
    assert draft.problem("", "x") == "The name cannot be empty."
    assert draft.problem("mine", "y") == "Another filter already has this name."
    assert draft.problem("mine", "y", replacing=0) is None
    assert draft.problem("n", "") == "The pattern cannot be empty."
    problem = draft.problem("n", "(")
    assert problem is not None
    assert problem.startswith("The pattern is not a valid regular expression:")
    assert draft.add("n", "(") is None
    assert not draft.replace(0, "n", "(")


def test_a_pattern_keeps_its_replacement_and_a_bad_one_is_refused() -> None:
    draft = editor([])
    assert draft.add("srv", r"\w+@(\w+):", r"\1") == 0
    assert draft.patterns[0].replacement == r"\1"
    assert draft.replace(0, "srv", r"\w+@(\w+):", "the server")
    assert draft.patterns[0].replacement == "the server"
    problem = draft.problem("x", r"\w+@", r"\2")
    assert problem is not None
    assert problem.startswith("The pattern is not a valid regular expression:")
    assert draft.add("x", r"\w+@", r"\2") is None


def test_the_start_patterns_can_be_put_back() -> None:
    draft = editor([])
    draft.restore_start_patterns()
    assert draft.names() == [item.name for item in START_PATTERNS]


def test_putting_back_the_start_patterns_keeps_the_ones_the_user_added() -> None:
    mine = PromptPattern("Mine", "X> ", "mine")
    changed = PromptPattern("bash", "other", "my word")
    draft = editor([mine, changed])
    draft.restore_start_patterns()
    names = draft.names()
    assert names[:2] == ["Mine", "bash"]  # the user's pattern stays, bash stays in its place
    assert draft.patterns[0] == mine
    assert draft.patterns[1].pattern != "other"  # bash is what the start list says again
    assert set(names) == {"Mine", *(item.name for item in START_PATTERNS)}  # the others came back
    assert len(names) == len(set(names))


def test_the_try_line_gives_the_line_as_it_would_be_announced() -> None:
    draft = editor()
    assert draft.sample(r"PS .*> ", "", r"PS C:\x> dir") == "dir"
    assert draft.sample(r"PS .*> ", "", "dir") == "dir"  # no prompt found: the line as it is
    assert draft.sample(r"PS .*> ", "", r"PS C:\x> ") == "blank"
    assert draft.sample("(", "", "dir") == ""
    assert draft.sample(r"PS .*> ", "", "") == ""
    assert draft.sample(r"PS .*> ", "Windows", r"PS C:\x> dir") == "Windows dir"
    assert draft.sample(r"PS .*> ", "Windows", r"PS C:\x> ") == "Windows"
