"""The analysis of one line: progress, question, choice, error, and the lines that are none."""

import pytest

from n5terminal.core.screen.line_analysis import (
    ElementKind,
    LineElement,
    analyze_line,
    clean_line,
    read_line,
)

pytestmark = pytest.mark.unit

PROGRESS = ElementKind.PROGRESS
QUESTION = ElementKind.QUESTION
CHOICE = ElementKind.CHOICE
ERROR = ElementKind.ERROR


@pytest.mark.parametrize(
    ("line", "text", "value"),
    [
        ("50%", "50 %", 50),
        ("Download  100%", "Download, 100 %", 100),
        ("Downloading [########            ]  40 %", "Downloading, 40 %", 40),
        ("Downloading: 45%|████▌     | 4.5M/10M [00:01<00:01]", "Downloading, 45 %", 45),
        ("Installing [#####.....]", "Installing, 50 %", 50),
        ("Installing [##########]", "Installing, 100 %", 100),
        ("Progress 12,5 %", "Progress, 12.5 %", 12),
        ("   ━━━━━━━━━━━━━━━━ 11.0/11.0 kB 2.2 MB/s eta 0:00:00", "11.0 of 11.0 kB", 100),
        ("Files [3/10]", "Files, 3 of 10", 30),
        ("Copying 4.2/12 MB", "Copying, 4.2 of 12 MB", 35),
        ("StdErr: Téléchargement [###.......] 30 %", "Téléchargement, 30 %", 30),
    ],
)
def test_a_progress_is_said_with_its_label_and_its_value(line: str, text: str, value: int) -> None:
    assert analyze_line(line) == LineElement(PROGRESS, text, value)


def test_a_bar_of_blocks_without_a_number_is_a_progress_without_a_value() -> None:
    assert analyze_line("Fetching ━━━━━━━━━━━━") == LineElement(PROGRESS, "Fetching")
    assert analyze_line("━━━━━━━━━━━━") == LineElement(PROGRESS, "Progress")


@pytest.mark.parametrize(
    "line",
    [
        "Downloading six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)",
        "Date 12/05/2026",
        "See a/b and 3/4 of the text",
        "200% of nothing is more than 100",
        "[----]",
        "[ERROR] 3 failed",
        "",
        "   ",
    ],
)
def test_a_line_that_is_not_a_progress_is_not_one(line: str) -> None:
    element = analyze_line(line)
    assert element is None or element.kind is not PROGRESS


@pytest.mark.parametrize(
    ("line", "text"),
    [
        ("Overwrite the file? [y/N] ", "Question: Overwrite the file? Default answer: no"),
        ("Continue? [Y/n]", "Question: Continue? Default answer: yes"),
        ("Continuer ? [O/n]", "Question: Continuer ? Default answer: yes"),
        ("Remove it? (y/n)", "Question: Remove it?"),
        ("Proceed (yes/no)?", "Question: Proceed"),
        ("Choice [1-3]: ", "Question: Choice [1-3]"),
        ("Password:", "Question: Password"),
        ("Enter passphrase for key 'id_rsa':", "Question: Enter passphrase for key 'id_rsa'"),
        ("Press any key to continue . . .", "Question: Press any key to continue . . ."),
        ("--More--", "Question: --More--"),
        ("Do you agree?", "Question: Do you agree?"),
        ("? Pick a color", None),
    ],
)
def test_a_question_waiting_for_an_answer(line: str, text: str | None) -> None:
    element = analyze_line(line)
    if text is None:
        assert element is None or element.kind is not QUESTION
    else:
        assert element == LineElement(QUESTION, text)


def test_an_answered_question_is_not_waiting() -> None:
    assert analyze_line("Overwrite the file? [y/N] y") is None
    assert analyze_line("Your name: Ada") is None
    assert analyze_line("Your name:") is None


@pytest.mark.parametrize(
    ("line", "text"),
    [
        ("> Red", "Red, selected"),
        ("  > Green", "Green, selected"),
        (chr(0x276F) + " Blue", "Blue, selected"),  # a heavy angle quotation mark
        ("* main", "main, selected"),
        ("[x] Tests", "Tests, checked"),
        ("[ ] Docs", "Docs, not checked"),
        ("(*) One", "One, checked"),
        ("  2) Beta", "Option 2, Beta"),
        ("[3] Gamma", "Option 3, Gamma"),
    ],
)
def test_an_item_of_a_list(line: str, text: str) -> None:
    assert analyze_line(line) == LineElement(CHOICE, text)


@pytest.mark.parametrize("line", ["  Green", "1. A step of a guide", "a > b", "Select an option:"])
def test_a_plain_line_is_not_a_choice(line: str) -> None:
    assert analyze_line(line) is None


def test_the_mark_of_a_sent_line_is_not_a_selection_in_pipes_mode() -> None:
    assert analyze_line("> y", selection_marks=False) is None
    assert analyze_line("> y") == LineElement(CHOICE, "y, selected")


def test_a_launched_command_is_not_analyzed() -> None:
    assert analyze_line("# pip install what?") is None


@pytest.mark.parametrize(
    ("line", "text"),
    [
        ("error: file not found", "Error: file not found"),
        ("Error: bad", "Error: bad"),
        ("StdErr: error: file not found", "Error: file not found"),
        ("[ERROR] disk full", "Error: disk full"),
        ("fatal: not a git repository", "Error: not a git repository"),
        ("warning: using the default", "Warning: using the default"),
        ("Traceback (most recent call last):", "Error: Traceback (most recent call last):"),
        ("ValueError: boom", "Error: ValueError: boom"),
        ("Access is denied.", "Error: Access is denied."),
        ("'foo' is not recognized as an internal or external command", None),
        ("bash: foo: command not found", "Error: bash: foo: command not found"),
    ],
)
def test_an_error_or_a_warning(line: str, text: str | None) -> None:
    element = analyze_line(line)
    assert element is not None
    assert element.kind is ERROR
    if text is not None:
        assert element.text == text


@pytest.mark.parametrize("line", ["terror: in the dark", "Done without errors", "hello world"])
def test_an_ordinary_line_is_no_error(line: str) -> None:
    assert analyze_line(line) is None


def test_a_line_without_element_is_read_without_its_decor() -> None:
    assert read_line("┌──────────┐") == ""
    assert read_line("│ Name   Id  │") == "Name Id"
    assert read_line("==== Results ====") == "Results"
    assert read_line("hello    world") == "hello world"
    assert clean_line("[   ] Loading.....") == "Loading"


def test_a_recognized_line_is_read_as_its_element() -> None:
    assert read_line("Download  60%") == "Download, 60 %"
    assert read_line("StdErr: plain line") == "StdErr: plain line"


def test_a_line_with_the_terminal_cursor_inside_its_text_is_the_item_chosen() -> None:
    assert analyze_line("Green", cursor_on_text=True) == LineElement(CHOICE, "Green, selected")
    assert analyze_line("Green") is None
    # What the line shows by itself comes first.
    assert analyze_line("50%", cursor_on_text=True) == LineElement(PROGRESS, "50 %", 50)
    assert analyze_line("", cursor_on_text=True) is None
    assert read_line("Green", cursor_on_text=True) == "Green, selected"
