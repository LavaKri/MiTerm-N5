"""The analysis of one line of the output: is it a progress, a question, a choice or an error?

A pure function of the text of a line: no state, no screen, no time, so that it is tested with
strings and with the lines of the captures. What is recognized is said in a short text (``Download,
60 %``) that the screen reader reads better than the raw line. See "Analysis of the output" in
``specs/architecture/screen.md`` and "Activities" in ``specs/interface.md``.

The rules read the text only, never colours or attributes. They are a start, to be adjusted on the
lines of real programs (``tests/data/captures``, ``specs/open-questions.md``).
"""

import enum
import re
from dataclasses import dataclass, field

from n5terminal.core.screen.line_output_model import STDERR_PREFIX
from n5terminal.i18n import _

LAUNCH_PREFIX = "# "  # a launched command is a Markdown title of level 1, reached with key 1
SEND_PREFIX = "> "  # a line sent to a running program (pipes)


class ElementKind(enum.Enum):
    """What was recognized; a closed list."""

    PROGRESS = "progress"  # a percentage, a fraction, a bar
    QUESTION = "question"  # the program waits for an answer ([Y/n], a password...)
    CHOICE = "choice"  # an item of a list, selected or numbered
    ERROR = "error"  # an error or a warning
    URL = "url"  # a web address; never found by ``analyze_line`` but by ``addresses.py``
    EMAIL = "email"  # a mail address; same


@dataclass(slots=True, frozen=True)
class LineElement:
    """What a line shows: its ``kind``, the ``text`` that is said and a ``value`` if there is one.

    The value is the percentage of a progress when the line gives it or lets it be computed. For a
    choice, ``item`` is the text of the item and ``selected`` tells whether it is the one chosen
    (they are what a whole menu is said from, and do not count in comparisons).
    """

    kind: ElementKind
    text: str
    value: int | None = None
    item: str = field(default="", compare=False)
    selected: bool = field(default=False, compare=False)


_FILL = "#=>█▓▒■*"
_PERCENT = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,]\d+)?)\s?%")
_FRACTION = re.compile(
    r"(?<![\w./])(\d+(?:[.,]\d+)?)\s?/\s?(\d+(?:[.,]\d+)?)(?:\s?([kKMGT]i?[oB]|bytes?))?(?![\w/])"
)
_BRACKET_BAR = re.compile(r"\[([#=>█▓▒■*\-.\s]{4,})\]")
_BLOCK_BAR = re.compile(r"[━█▓▒░■]{5,}")

_YES_NO = re.compile(r"\s*[\[(]\s*([A-Za-z])\s*/\s*([A-Za-z])\s*[\])]\s*[:?]?\s*$")
_YES_NO_WORDS = re.compile(r"\s*\(\s*(yes|oui)\s*/\s*(no|non)\s*\)\s*[:?]?\s*$", re.IGNORECASE)
_RANGE = re.compile(r"\s*\[\s*\d+\s*-\s*\d+\s*\]\s*:?\s*$")
_PASSWORD = re.compile(r"\b(password|passphrase|passcode|mot de passe)\b.*:\s*$", re.IGNORECASE)
_KEY = re.compile(r"press (any )?key|appuyez sur une touche|--more--|\(END\)", re.IGNORECASE)
_YES_LETTERS = "yo"  # y(es), o(ui)
_NO_LETTERS = "n"

_ERROR_START = re.compile(
    r"^\s*(?:\[(error|warn(?:ing)?|fatal|critical)\]|"
    r"(error|fatal(?: error)?|failed|failure|warning|warn|critical)\s*[:\-])\s*(.*)$",
    re.IGNORECASE,
)
_EXCEPTION = re.compile(
    r"^Traceback \(most recent call last\):|^[A-Za-z_][\w.]*(?:Error|Exception)\b(?::|$)"
)
_ERROR_PHRASE = re.compile(
    r"access is denied|permission denied|is not recognized as an internal or external command|"
    r"command not found|no such file or directory|cannot find the (?:file|path)",
    re.IGNORECASE,
)

#: The marks of a selected item; two of them are written by code (signs ruff finds ambiguous).
_MARKERS = ">*»" + chr(0x203A) + chr(0x276F) + "→▶"
_MARKED = re.compile(rf"^\s*[{re.escape(_MARKERS)}]\s+(\S.*)$")
_CHECKBOX = re.compile(r"^\s*[\[(]([xX* ])[\])]\s+(\S.*)$")
_NUMBERED = re.compile(r"^\s*(?:(\d+)\)|\[(\d+)\])\s+(\S.*)$")

_DECOR = re.compile(r"[─-▟]+")  # box drawing and block elements
_RUNS = re.compile(r"([#=\-_*~.])\1{3,}")  # the same sign four times or more
_EMPTY_BRACKETS = re.compile(r"\[\s*\]")
_LABEL_END = " \t:-|[(,"


def _without_marks(text: str, *, selection_marks: bool) -> str | None:
    """The line without the marks the application wrote, None for a line that is not the program's.

    A launched command (``# ...``) is not analyzed. A sent line (``> ...``) is not either in pipes
    mode, where ``selection_marks`` is false, because a program there has no list to mark.
    """
    if text.startswith(LAUNCH_PREFIX):
        return None
    if not selection_marks and text.startswith(SEND_PREFIX):
        return None
    return text.removeprefix(STDERR_PREFIX)


def clean_line(text: str) -> str:
    """The line without its decor (boxes, runs of ``#`` or ``=``, empty brackets), spaces joined."""
    text = _DECOR.sub(" ", text)
    text = _RUNS.sub(" ", text)
    text = _EMPTY_BRACKETS.sub(" ", text)
    return " ".join(text.split())


def analyze_line(
    text: str, *, selection_marks: bool = True, cursor_on_text: bool = False
) -> LineElement | None:
    """The element the line shows, None when it shows none.

    ``selection_marks`` is false in pipes mode, where ``> `` starts a line the user sent.
    ``cursor_on_text`` says the terminal cursor is inside the text of the line: a line that shows
    nothing else is then the item chosen in a list that marks its choice by the cursor alone.
    """
    line = _without_marks(text, selection_marks=selection_marks)
    if line is None or not line.strip():
        return None
    element = (
        _question(line)
        or _progress(line)
        or _error(line)
        or _choice(line, selection_marks=selection_marks)
    )
    if element is None and cursor_on_text:
        return _selected(clean_line(line))
    return element


def read_line(text: str, *, selection_marks: bool = True, cursor_on_text: bool = False) -> str:
    """What is said for the line: its element, or the line without its decor."""
    element = analyze_line(text, selection_marks=selection_marks, cursor_on_text=cursor_on_text)
    return element.text if element else clean_line(text)


# Progress ----------------------------------------------------------------------------------------


def _number(raw: str) -> float:
    return float(raw.replace(",", "."))


def _shown(value: float) -> str:
    return f"{value:g}"


def _label(line: str, end: int) -> str:
    """What the line says before the bar or the number: ``Download`` in ``Download [##..] 40 %``."""
    return clean_line(line[:end]).strip(_LABEL_END).strip()


def _with_label(label: str, value_text: str) -> str:
    if label:
        return _("{label}, {value}").format(label=label, value=value_text)
    return value_text


def _progress(line: str) -> LineElement | None:
    percent = _PERCENT.search(line)
    if percent and _number(percent.group(1)) > 100:
        percent = None
    bar = _bar(line)
    fraction = _fraction(line)
    found = [match.start() for match in (percent, bar, fraction) if match]
    if not found:
        return None
    label = _label(line, min(found))
    if percent:
        value = _number(percent.group(1))
        text = _with_label(label, _("{percent} %").format(percent=_shown(value)))
        return LineElement(ElementKind.PROGRESS, text, round(value))
    if fraction:
        done, total = _number(fraction.group(1)), _number(fraction.group(2))
        return LineElement(
            ElementKind.PROGRESS,
            _with_label(label, _fraction_text(fraction)),
            round(done / total * 100),
        )
    ratio = _bar_ratio(bar)
    if ratio is not None:
        text = _with_label(label, _("{percent} %").format(percent=ratio))
        return LineElement(ElementKind.PROGRESS, text, ratio)
    return LineElement(ElementKind.PROGRESS, label or _("Progress"))


def _bar(line: str) -> re.Match[str] | None:
    """A bar: signs between brackets with at least one filled (``[##..]``), or a run of blocks."""
    bracket = _BRACKET_BAR.search(line)
    if bracket and any(sign in _FILL for sign in bracket.group(1)):
        return bracket
    return _BLOCK_BAR.search(line)


def _fraction(line: str) -> re.Match[str] | None:
    """A ``3/10`` that is a progress: with a unit (``4.2/12 MB``) or in brackets (``[3/10]``)."""
    for match in _FRACTION.finditer(line):
        if _number(match.group(2)) <= 0 or _number(match.group(1)) > _number(match.group(2)):
            continue
        before = line[match.start() - 1 : match.start()]
        after = line[match.end() : match.end() + 1]
        if match.group(3) or (before in "[(" and after in "])" and before and after):
            return match
    return None


def _fraction_text(match: re.Match[str]) -> str:
    done, total, unit = match.group(1), match.group(2), match.group(3)
    if unit:
        return _("{done} of {total} {unit}").format(done=done, total=total, unit=unit)
    return _("{done} of {total}").format(done=done, total=total)


def _bar_ratio(bar: re.Match[str] | None) -> int | None:
    """The part filled of a bar between brackets (``[###...]``); None for a bar of one sign."""
    if bar is None or not bar.group(0).startswith("["):
        return None
    inside = bar.group(1)
    filled = sum(1 for sign in inside if sign in _FILL)
    empty = sum(1 for sign in inside if sign in "-. ")
    if not filled or not empty:
        return 100 if filled and not empty else None
    return round(filled / (filled + empty) * 100)


# Question ----------------------------------------------------------------------------------------


def _question(line: str) -> LineElement | None:
    text = line.rstrip()
    yes_no = _YES_NO.search(text)
    if yes_no:
        default = _default_answer(yes_no.group(1), yes_no.group(2))
        if default is not None:
            return _asked(text[: yes_no.start()], default or None)
    words = _YES_NO_WORDS.search(text)
    if words:
        return _asked(text[: words.start()], None)
    if _RANGE.search(text) or _PASSWORD.search(text) or _KEY.search(text):
        return _asked(text.rstrip(": ").removeprefix("? "), None)
    if text.endswith("?"):
        return _asked(text.removeprefix("? "), None)
    return None


def _default_answer(first: str, second: str) -> str | None:
    """The default of ``[Y/n]``: its answer, ``""`` for none, None when it is not a yes/no pair."""
    pair = first.lower() + second.lower()
    if not (pair[0] in _YES_LETTERS and pair[1] in _NO_LETTERS) or pair[0] == pair[1]:
        return None
    if first.isupper() and second.islower():
        return _("yes")
    if second.isupper() and first.islower():
        return _("no")
    return ""


def _asked(question: str, default: str | None) -> LineElement:
    question = question.strip().removeprefix("? ")
    if default:
        text = _("Question: {question} Default answer: {answer}").format(
            question=question, answer=default
        )
    else:
        text = _("Question: {question}").format(question=question)
    return LineElement(ElementKind.QUESTION, text)


# Error -------------------------------------------------------------------------------------------


def _error(line: str) -> LineElement | None:
    start = _ERROR_START.match(line)
    if start:
        word = (start.group(1) or start.group(2)).lower()
        message = start.group(3).strip()
        if word.startswith("warn"):
            text = _("Warning: {message}").format(message=message)
        else:
            text = _("Error: {message}").format(message=message)
        return LineElement(ElementKind.ERROR, text.rstrip(": "))
    if _EXCEPTION.search(line.strip()) or _ERROR_PHRASE.search(line):
        return LineElement(ElementKind.ERROR, _("Error: {message}").format(message=line.strip()))
    return None


# Choice ------------------------------------------------------------------------------------------


def _selected(item: str) -> LineElement:
    return LineElement(
        ElementKind.CHOICE, _("{item}, selected").format(item=item), item=item, selected=True
    )


def _choice(line: str, *, selection_marks: bool) -> LineElement | None:
    box = _CHECKBOX.match(line)
    if box:
        item = box.group(2).strip()
        state = _("not checked") if box.group(1) == " " else _("checked")
        text = _("{item}, {state}").format(item=item, state=state)
        return LineElement(ElementKind.CHOICE, text, item=item)
    if selection_marks:
        marked = _MARKED.match(line)
        if marked:
            return _selected(marked.group(1).strip())
    numbered = _NUMBERED.match(line)
    if numbered:
        number = numbered.group(1) or numbered.group(2)
        item = numbered.group(3).strip()
        text = _("Option {number}, {item}").format(number=number, item=item)
        return LineElement(ElementKind.CHOICE, text, item=item)
    return None
