from pathlib import Path

import pytest

from n5terminal.core.config.help import convert_help, help_name, help_page, to_html
from n5terminal.core.errors import HelpError

pytestmark = pytest.mark.unit

SOURCE = "# Aide de MiTerm-N5\n\nUn *mot* accentué : été.\n\n- un\n- deux\n"


def test_a_page_has_the_name_of_its_language() -> None:
    assert help_name("fr") == "Fr"
    assert help_name("en") == "En"


def test_the_page_of_the_language_is_found(tmp_path: Path) -> None:
    (tmp_path / "Fr.html").write_text("fr", encoding="utf-8")
    (tmp_path / "En.html").write_text("en", encoding="utf-8")
    assert help_page(tmp_path, "fr") == tmp_path / "Fr.html"
    assert help_page(tmp_path, "en") == tmp_path / "En.html"


def test_without_the_page_of_the_language_the_english_one_is_used(tmp_path: Path) -> None:
    (tmp_path / "En.html").write_text("en", encoding="utf-8")
    assert help_page(tmp_path, "fr") == tmp_path / "En.html"


def test_without_any_page_there_is_none(tmp_path: Path) -> None:
    assert help_page(tmp_path, "fr") is None
    assert help_page(tmp_path / "absent", "fr") is None


def test_the_page_is_as_simple_as_possible() -> None:
    page = to_html(SOURCE, "fr", "Fr")
    assert page.startswith('<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n')
    assert "<title>Aide de MiTerm-N5</title>" in page
    assert "<h1>Aide de MiTerm-N5</h1>" in page
    assert "<em>mot</em>" in page
    assert "<li>deux</li>" in page
    assert page.endswith("</body>\n</html>\n")
    for forbidden in ("<style", "<script", "<link", "style="):
        assert forbidden not in page


def test_without_a_heading_the_title_is_the_name() -> None:
    assert "<title>Fr</title>" in to_html("Just text.", "fr", "Fr")


def test_the_title_is_escaped() -> None:
    assert "<title>A &lt;b&gt; &amp; c</title>" in to_html("# A <b> & c", "en", "En")


def test_each_markdown_file_gets_its_html_page(tmp_path: Path) -> None:
    (tmp_path / "Fr.md").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "En.md").write_text("# Help\n\nText.\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not converted", encoding="utf-8")
    written = convert_help(tmp_path)
    assert [path.name for path in written] == ["En.html", "Fr.html"]
    french = (tmp_path / "Fr.html").read_text(encoding="utf-8")
    assert '<html lang="fr">' in french
    assert "accentué : été" in french
    assert '<html lang="en">' in (tmp_path / "En.html").read_text(encoding="utf-8")
    assert not (tmp_path / "notes.html").exists()


def test_converting_again_replaces_the_pages(tmp_path: Path) -> None:
    (tmp_path / "En.md").write_text("# One\n", encoding="utf-8")
    convert_help(tmp_path)
    (tmp_path / "En.md").write_text("# Two\n", encoding="utf-8")
    convert_help(tmp_path)
    assert "<title>Two</title>" in (tmp_path / "En.html").read_text(encoding="utf-8")


def test_a_folder_without_markdown_files_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(HelpError):
        convert_help(tmp_path)
    with pytest.raises(HelpError):
        convert_help(tmp_path / "absent")
