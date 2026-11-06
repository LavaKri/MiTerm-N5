"""An announcement is said with the values its text needs.

``say(Announce.X, key=...)`` fills ``{key}`` in the text of ``X``. A value that is missing raises a
``KeyError`` when the message is said, which no test sees unless it follows that very path. This
reads the code and checks each call that names its announcement in place; the announcements said
through a variable are checked where they are chosen (the refusals in ``test_session_state.py``) or
by the behaviour test named in ``SAID_THROUGH_A_VARIABLE``.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

import n5terminal
from n5terminal.core.config.announcements import Announce, Destination

pytestmark = pytest.mark.unit

PACKAGE = Path(n5terminal.__file__).parent

# The announcements with fields that are never named in a call: the call gets them from a variable.
# Each is said by a test of its own, which would fail on a missing value.
SAID_THROUGH_A_VARIABLE = {
    Announce.NO_NEXT_TITLE_OF_LEVEL,  # tests/presenters/test_title_navigation.py
    Announce.NO_PREVIOUS_TITLE_OF_LEVEL,  # tests/presenters/test_title_navigation.py
    Announce.SEARCH_NO_NEXT,  # tests/presenters/test_output_search.py
    Announce.SEARCH_NO_PREVIOUS,  # tests/presenters/test_output_search.py
    Announce.MOVED_TO_CURSOR,  # tests/ui/test_main_window_output.py
    Announce.MOVED_TO_EMULATOR_START,  # tests/ui/test_main_window_output.py
    Announce.MOVED_TO_EMULATOR_END,  # tests/ui/test_main_window_output.py
    Announce.PROGRAM_NOT_FOUND,  # tests/presenters/test_session_run.py
    Announce.POWERSHELL_NOT_FOUND,  # tests/presenters/test_session_run.py
    Announce.LAUNCH_FAILED,  # tests/presenters/test_session_run.py
    Announce.CONNECTED,  # tests/presenters/test_session_presenter_connection.py
    Announce.DISCONNECTED,  # tests/presenters/test_session_presenter_connection.py
    Announce.CONNECTION_FAILED,  # tests/presenters/test_session_presenter_connection.py
    Announce.AUTHENTICATION_FAILED,  # tests/presenters/test_session_presenter_connection.py
    Announce.HOST_KEY_FAILED,  # tests/presenters/test_session_presenter_connection.py
    Announce.SSH_NOT_FOUND,  # tests/presenters/test_session_presenter_connection.py
    Announce.ASKPASS_NOT_FOUND,  # tests/presenters/test_session_presenter_connection.py
}


@dataclass(slots=True, frozen=True)
class Call:
    """A call whose first argument is ``Announce.<NAME>``, and the values it gives."""

    path: Path
    line: int
    announce: Announce
    values: frozenset[str]

    @property
    def id(self) -> str:
        return f"{self.path.relative_to(PACKAGE).as_posix()}:{self.line} {self.announce.name}"


def named_announce(node: ast.expr) -> Announce | None:
    """The announcement ``node`` names (``Announce.NAME``), if it does."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Announce"
    ):
        return Announce.__members__.get(node.attr)
    return None


def calls_in(path: Path) -> list[Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        announce = named_announce(node.args[0])
        if announce is None or any(keyword.arg is None for keyword in node.keywords):
            continue  # not an announcement, or values given as ``**values``
        values = frozenset(keyword.arg for keyword in node.keywords if keyword.arg)
        found.append(Call(path, node.lineno, announce, values))
    return found


def all_calls() -> list[Call]:
    return [call for path in sorted(PACKAGE.rglob("*.py")) for call in calls_in(path)]


def needed(announce: Announce) -> frozenset[str]:
    """The values to give: the fields of the text, and the line when the category can read it."""
    category = announce.category
    reads_line = category is not None and category.accepts(Destination.READ_LINE)
    return announce.fields | ({"line"} if reads_line else frozenset())


def test_the_calls_are_found() -> None:
    names = {call.announce for call in all_calls()}
    assert {Announce.PROGRAM_ENDED, Announce.MOVED_TITLE, Announce.KEY_SENT} <= names


@pytest.mark.parametrize("call", all_calls(), ids=lambda call: call.id)
def test_a_call_gives_the_values_the_text_needs(call: Call) -> None:
    assert needed(call.announce) <= call.values


def test_what_the_calls_cannot_check_is_listed() -> None:
    named = {call.announce for call in all_calls()}
    unchecked = {announce for announce in Announce if needed(announce) and announce not in named}
    assert unchecked == SAID_THROUGH_A_VARIABLE
