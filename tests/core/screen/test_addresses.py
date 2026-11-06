import pytest

from n5terminal.core.screen.addresses import find_addresses
from n5terminal.core.screen.line_analysis import ElementKind

pytestmark = pytest.mark.unit

URL = ElementKind.URL
EMAIL = ElementKind.EMAIL


def found(line: str) -> list[tuple[int, ElementKind, str]]:
    return [(a.start, a.kind, a.text) for a in find_addresses(line)]


def test_a_web_address_is_found_with_its_start() -> None:
    assert found("See https://example.org/a?b=1#c for help") == [
        (4, URL, "https://example.org/a?b=1#c")
    ]
    assert found("go to www.example.fr now") == [(6, URL, "www.example.fr")]
    assert found("HTTP://EXAMPLE.ORG") == [(0, URL, "HTTP://EXAMPLE.ORG")]


@pytest.mark.parametrize(
    ("line", "address"),
    [
        ("(see https://a.fr/x).", "https://a.fr/x"),
        ("see https://a.fr/x, then", "https://a.fr/x"),
        ("is it https://a.fr/x?", "https://a.fr/x"),
        ('"https://a.fr/x"', "https://a.fr/x"),
        ("[https://a.fr/x]", "https://a.fr/x"),
        ("https://fr.wikipedia.org/wiki/A_(b)", "https://fr.wikipedia.org/wiki/A_(b)"),
    ],
)
def test_the_signs_of_the_sentence_are_not_part_of_the_address(line: str, address: str) -> None:
    assert [a.text for a in find_addresses(line)] == [address]


def test_a_mail_address_is_found() -> None:
    assert found("write to me.you+tag@mail.example.org, please") == [
        (9, EMAIL, "me.you+tag@mail.example.org")
    ]


def test_several_addresses_of_a_line_come_in_the_order_they_are_written() -> None:
    kinds = [a.kind for a in find_addresses("a@b.fr then https://c.fr and d@e.org")]
    assert kinds == [EMAIL, URL, EMAIL]


@pytest.mark.parametrize(
    "line",
    [
        "user@host",  # no dot: a prompt, not a mail address
        "git@github.com:user/repo.git",  # an address of ssh
        "plain text, 3.5 and v1.2.3",
        "http",
        "",
    ],
)
def test_what_looks_like_an_address_but_is_not_is_left_alone(line: str) -> None:
    assert found(line) == []


def test_a_mail_inside_a_web_address_is_not_found_twice() -> None:
    assert found("https://user@example.org/path") == [(0, URL, "https://user@example.org/path")]
