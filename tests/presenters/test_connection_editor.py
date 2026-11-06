"""The draft of the connection dialog: what is refused, and what is built."""

import pytest

from n5terminal.core.config.connections import Connection
from n5terminal.presenters.connection_editor import ConnectionEditor, Field

pytestmark = pytest.mark.unit


def same(text: str) -> str:
    return text


def editor(
    connection: Connection | None = None, existing: list[str] | None = None
) -> ConnectionEditor:
    return ConnectionEditor(connection or Connection(""), existing or [], same)


def filled(
    name: str = "prod", target: str = "admin@example.org", port: str = ""
) -> ConnectionEditor:
    draft = editor()
    draft.name, draft.target, draft.port = name, target, port
    return draft


def test_a_connection_with_no_name_is_new() -> None:
    assert editor().is_new
    assert editor().replaces is None
    existing = editor(Connection("prod", target="x"))
    assert not existing.is_new
    assert existing.replaces == "prod"


def test_the_draft_starts_on_the_values_of_the_connection() -> None:
    draft = editor(Connection("prod", target="admin@example.org", port=2222))
    assert (draft.name, draft.target, draft.port) == ("prod", "admin@example.org", "2222")
    assert editor(Connection("prod", target="x")).port == ""


def test_a_good_draft_has_no_problem() -> None:
    assert filled().problem() is None
    assert filled(port="22").problem() is None


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "The name cannot be empty."),
        ("a" * 21, "The name cannot be longer than 20 characters."),
        ("a/b", "The character / is not allowed in a name."),
        ("CON", "The name cannot hold any of these characters"),
    ],
)
def test_a_name_that_cannot_be_a_file_is_refused_with_its_reason(name: str, message: str) -> None:
    problem = filled(name=name).problem()
    assert problem is not None
    field, text = problem
    assert field is Field.NAME
    assert text.startswith(message)


def test_a_name_already_taken_is_refused_whatever_its_case() -> None:
    draft = editor(existing=["prod"])
    draft.name, draft.target = "PROD", "x"
    assert draft.problem() == (Field.NAME, "Another connection already has this name.")


def test_the_connection_being_edited_does_not_take_its_own_name() -> None:
    draft = editor(Connection("prod", target="x"), ["prod", "nas"])
    assert draft.problem() is None
    draft.name = "nas"
    assert draft.problem() is not None


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("", "The target cannot be empty."),
        ("admin@", "The target cannot be empty."),
        (
            "-oProxyCommand=calc",
            "The target cannot start with a dash, nor can the server after the @.",
        ),
        (
            "admin@-oProxyCommand=calc",
            "The target cannot start with a dash, nor can the server after the @.",
        ),
        ("a b", "The target cannot hold a space or a control character."),
    ],
)
def test_a_target_ssh_would_take_for_something_else_is_refused(target: str, message: str) -> None:
    assert filled(target=target).problem() == (Field.TARGET, message)


@pytest.mark.parametrize("port", ["0", "65536", "-1", "22.5", "ssh", "٢٢", "1 2"])
def test_a_port_that_is_not_a_whole_number_in_range_is_refused(port: str) -> None:
    problem = filled(port=port).problem()
    assert problem is not None
    assert problem[0] is Field.PORT
    assert problem[1] == "The port is a whole number from 1 to 65535, or nothing."


def test_no_port_is_fine_and_blanks_are_ignored() -> None:
    assert filled(port="").problem() is None
    assert filled(port="  ").problem() is None
    assert filled(port=" 2222 ").build().port == 2222


def test_the_first_problem_is_the_name_then_the_target_then_the_port() -> None:
    draft = filled(name="", target="", port="x")
    assert draft.problem() is not None
    assert draft.problem()[0] is Field.NAME  # type: ignore[index]
    draft.name = "prod"
    assert draft.problem()[0] is Field.TARGET  # type: ignore[index]
    draft.target = "box"
    assert draft.problem()[0] is Field.PORT  # type: ignore[index]


def test_the_connection_built_is_stripped_and_keeps_the_unknown_keys() -> None:
    original = Connection("prod", target="old", extra={"fingerprint": "SHA256:abc"})
    draft = editor(original)
    draft.name, draft.target, draft.port = " web ", " me@web.example ", "2200"
    built = draft.build()
    assert (built.name, built.target, built.port) == ("web", "me@web.example", 2200)
    assert built.extra == {"fingerprint": "SHA256:abc"}
    assert original.name == "prod"  # the original was not touched


def test_no_port_is_none_in_the_connection() -> None:
    assert filled(port="").build().port is None


def test_a_character_outside_the_list_is_named_in_the_message() -> None:
    editor = ConnectionEditor(Connection(""), [], lambda text: text)
    editor.name = "a&b"
    message = editor.name_message()
    assert message is not None
    assert message.startswith("The character & is not allowed in a name.")


def test_the_name_of_an_existing_connection_is_not_refused_while_it_is_not_changed() -> None:
    editor = ConnectionEditor(Connection("old&one", "host"), ["old&one"], lambda text: text)
    assert editor.name_message() is None
    editor.name = "new&one"
    assert editor.name_message() is not None
