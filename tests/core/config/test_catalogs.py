from pathlib import Path

import pytest

from fakes.catalog_files import make_catalog_folder
from n5terminal.core.config.catalogs import Catalogs, fields_of
from n5terminal.core.errors import CatalogError

pytestmark = pytest.mark.unit


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return make_catalog_folder(tmp_path)


def test_the_ids_follow_the_template_and_know_their_files(folder: Path) -> None:
    catalogs = Catalogs.load(folder)
    assert catalogs.ids == ["&Quit", "Cannot read {name}"]
    assert catalogs.files["Cannot read {name}"] == (
        "src/n5terminal/ui/actions.py",
        "src/n5terminal/ui/feedback.py",
    )
    assert catalogs.languages == ["fr"]
    assert catalogs.text("fr", "&Quit") == "&Quitter"


def test_a_change_is_written_to_the_po_and_the_mo(folder: Path) -> None:
    catalogs = Catalogs.load(folder)
    catalogs.set_text("fr", "&Quit", "Q&uitter")
    catalogs.save()
    again = Catalogs.load(folder)
    assert again.text("fr", "&Quit") == "Q&uitter"
    assert (folder / "fr" / "LC_MESSAGES" / "n5terminal.mo").is_file()
    assert not list(folder.rglob("*.tmp"))


def test_nothing_is_written_without_a_change(folder: Path) -> None:
    path = folder / "fr" / "LC_MESSAGES" / "n5terminal.po"
    before = path.read_bytes()
    Catalogs.load(folder).save()
    assert path.read_bytes() == before


def test_a_translation_that_loses_a_field_is_a_problem(folder: Path) -> None:
    catalogs = Catalogs.load(folder)
    catalogs.set_text("fr", "Cannot read {name}", "Lecture impossible")
    assert catalogs.problem() == ("fr", "Cannot read {name}")
    catalogs.set_text("fr", "Cannot read {name}", "Lecture de {name} impossible")
    assert catalogs.problem() is None


def test_a_translation_with_broken_braces_is_a_problem(folder: Path) -> None:
    catalogs = Catalogs.load(folder)
    catalogs.set_text("fr", "Cannot read {name}", "Lecture de {name impossible")
    assert catalogs.problem() == ("fr", "Cannot read {name}")


def test_the_fields_of_a_text() -> None:
    assert fields_of("a {x} b {y}") == {"x", "y"}
    assert fields_of("{") is None


def test_a_message_not_in_the_catalog_cannot_be_set(folder: Path) -> None:
    with pytest.raises(CatalogError):
        Catalogs.load(folder).set_text("fr", "unknown", "x")


def test_an_unreadable_catalog_is_an_error(folder: Path) -> None:
    (folder / "fr" / "LC_MESSAGES" / "n5terminal.po").write_bytes(b"\xff\xfe\x00 msgid")
    with pytest.raises(CatalogError):
        Catalogs.load(folder)
