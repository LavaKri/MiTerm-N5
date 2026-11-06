from collections.abc import Iterator

import pytest

from n5terminal import i18n

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.install("en")


def test_an_unknown_language_falls_back_to_the_message_ids() -> None:
    i18n.install("xx")
    assert i18n._("Message") == "Message"


def test_n_marks_without_translating() -> None:
    assert i18n.N_("Message") == "Message"


def test_the_default_language_is_french() -> None:
    assert i18n.DEFAULT_LANGUAGE == "fr"
    assert i18n.LOCALE_DIR.name == "locale"
