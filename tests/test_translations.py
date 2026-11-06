"""The French catalog is complete and keeps the named fields of every text."""

import gettext
from pathlib import Path
from string import Formatter

import pytest
from babel.messages.pofile import read_po

from n5terminal import i18n
from n5terminal.core.config.shortcuts import WX_KEY_IDS

pytestmark = pytest.mark.unit

CATALOG = i18n.LOCALE_DIR / "fr" / "LC_MESSAGES" / "n5terminal.po"


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(text) if name}


def messages() -> list[tuple[str, str]]:
    with Path(CATALOG).open("rb") as file:
        catalog = read_po(file, locale="fr")
    return [(str(m.id), str(m.string)) for m in catalog if m.id]


def test_every_text_is_translated() -> None:
    assert [text for text, translation in messages() if not translation] == []


def test_no_translation_is_marked_approximate() -> None:
    with Path(CATALOG).open("rb") as file:
        catalog = read_po(file, locale="fr")
    assert [str(m.id) for m in catalog if m.id and m.fuzzy] == []


def test_a_translation_keeps_the_named_fields_of_the_text() -> None:
    wrong = [text for text, translation in messages() if fields(text) != fields(translation)]
    assert wrong == []


def test_the_compiled_catalog_is_there_and_used() -> None:
    assert CATALOG.with_suffix(".mo").is_file()
    i18n.install("fr")
    try:
        assert i18n._("Ready") == "Prêt"
        assert i18n._("Running: {program}").format(program="ping") == "En cours : ping"
    finally:
        i18n.install("en")


def test_the_catalog_of_the_key_names_of_wx_says_the_keys_as_the_application_does() -> None:
    """``tools/make_wx_keys.py`` makes it from the catalog of the application: no drift."""
    ours = gettext.translation(i18n.DOMAIN, localedir=i18n.LOCALE_DIR, languages=["fr"])
    wx_keys = gettext.translation("wxkeys", localedir=i18n.LOCALE_DIR, languages=["fr"])
    for wx_id, key in WX_KEY_IDS.items():
        assert wx_keys.pgettext("keyboard key", wx_id) == ours.gettext(key), wx_id
