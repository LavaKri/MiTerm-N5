"""The elements recognized in the last lines of the output (Terminal > Activities > Identify).

Each line is given to the analysis of the line (``line_analysis.py``); the lines of one menu that
follow each other are made one element. See "Identifying activities" in ``specs/interface.md``.
"""

from dataclasses import dataclass

from n5terminal.core.screen.addresses import find_addresses
from n5terminal.core.screen.line_analysis import (
    LAUNCH_PREFIX,
    SEND_PREFIX,
    ElementKind,
    LineElement,
    analyze_line,
)
from n5terminal.core.screen.text_search import cursor_is_on_line_text
from n5terminal.i18n import _

ADDRESS_KINDS = (ElementKind.URL, ElementKind.EMAIL)


@dataclass(slots=True, frozen=True)
class FoundElement:
    """An element of the screen: what is said, the index of the start of its line, its line number.

    The line number counts from 1 in the text of the output, as the status bar does.
    """

    kind: ElementKind
    text: str
    index: int
    number: int

    def describe(self) -> str:
        """The line of the list: what is said and where; an address is only the address."""
        if self.kind in ADDRESS_KINDS:
            return self.text
        return _("{text}, line {number}").format(text=self.text, number=self.number)


def find_elements(
    text: str, last_lines: int, *, selection_marks: bool, cursor_index: int
) -> list[FoundElement]:
    """The elements of the last ``last_lines`` lines of ``text``, in order.

    ``cursor_index`` is the terminal cursor in ``text``: a line it is inside of is the item chosen
    of a list that marks its choice by the cursor alone.
    """
    lines = text.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    found: list[tuple[int, LineElement]] = []
    addresses: list[FoundElement] = []
    for number in range(max(0, len(lines) - last_lines), len(lines)):
        on_text = cursor_is_on_line_text(text, starts[number], cursor_index)
        element = analyze_line(
            lines[number], selection_marks=selection_marks, cursor_on_text=on_text
        )
        if element:
            found.append((number, element))
        addresses += _addresses(lines[number], starts[number], number, selection_marks)
    elements = [_found(group, starts) for group in _menus(found)]
    return sorted([*elements, *addresses], key=lambda element: element.index)  # stable


def initial_selection(elements: list[FoundElement]) -> int:
    """The element to select when the list opens: the last that is not an address.

    That is usually the question that waits; an address found below it must not take its place.
    """
    for position in range(len(elements) - 1, -1, -1):
        if elements[position].kind not in ADDRESS_KINDS:
            return position
    return max(len(elements) - 1, 0)


def _addresses(line: str, start: int, number: int, selection_marks: bool) -> list[FoundElement]:
    """The addresses of a line of the program (not a command launched, nor a line sent)."""
    if line.startswith(LAUNCH_PREFIX) or (not selection_marks and line.startswith(SEND_PREFIX)):
        return []
    return [
        FoundElement(address.kind, address.text, start + address.start, number + 1)
        for address in find_addresses(line)
    ]


def _menus(found: list[tuple[int, LineElement]]) -> list[list[tuple[int, LineElement]]]:
    """The elements, the choices of lines that follow each other being one group."""
    groups: list[list[tuple[int, LineElement]]] = []
    for number, element in found:
        previous = groups[-1] if groups else None
        follows = (
            previous
            and element.kind is ElementKind.CHOICE
            and previous[-1][1].kind is ElementKind.CHOICE
            and previous[-1][0] + 1 == number
        )
        if previous is not None and follows:
            previous.append((number, element))
        else:
            groups.append([(number, element)])
    return groups


def _found(group: list[tuple[int, LineElement]], starts: list[int]) -> FoundElement:
    first_number, first = group[0]
    if first.kind is ElementKind.PROGRESS:
        text = _("Progress, {text}").format(text=first.text)
        return FoundElement(first.kind, text, starts[first_number], first_number + 1)
    if first.kind is not ElementKind.CHOICE:
        return FoundElement(first.kind, first.text, starts[first_number], first_number + 1)
    if len(group) == 1:
        text = _("Choice, {text}").format(text=first.text)
        return FoundElement(first.kind, text, starts[first_number], first_number + 1)
    chosen = next(((number, element) for number, element in group if element.selected), None)
    number = chosen[0] if chosen else first_number
    if chosen:
        text = _("Choice, {count} options, selected: {item}").format(
            count=len(group), item=chosen[1].item
        )
    else:
        text = _("Choice, {count} options").format(count=len(group))
    return FoundElement(ElementKind.CHOICE, text, starts[number], number + 1)
