from pathlib import Path

import pytest

from fakes.catalog_files import make_catalog_folder
from n5terminal.core.config.catalogs import Catalogs
from n5terminal.presenters.catalogs_editor import CatalogsEditor, _excerpt, categories_of

pytestmark = pytest.mark.unit


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return make_catalog_folder(tmp_path)


def editor_for(folder: Path) -> CatalogsEditor:
    return CatalogsEditor(Catalogs.load(folder))


def test_the_lines_show_the_ids_then_the_language(folder: Path) -> None:
    editor = editor_for(folder)
    assert editor.lines() == ["&Quit", "Cannot read {name}"]
    assert editor.field_label == "Message"
    assert editor.read_only
    assert editor.change_view(1)
    assert editor.lines() == ["&Quitter", "Lecture de {name} impossible"]
    assert editor.field_label == "Message in French"
    assert not editor.read_only
    assert not editor.change_view(1)  # one language only
    assert editor.change_view(-1)
    assert not editor.change_view(-1)


def test_a_line_stops_at_the_first_line_break_or_at_50_characters() -> None:
    assert _excerpt("short") == "short"
    assert _excerpt("first\nsecond") == "first... Message excerpt"
    assert _excerpt("x" * 50) == "x" * 50
    assert _excerpt("x" * 51) == "x" * 50 + "... Message excerpt"


def test_changing_the_view_keeps_the_selected_line(folder: Path) -> None:
    editor = editor_for(folder)
    editor.select(1)
    editor.change_view(1)
    assert editor.selected == 1
    assert editor.field_text == "Lecture de {name} impossible"


def test_the_ids_cannot_be_edited(folder: Path) -> None:
    editor = editor_for(folder)
    editor.edit("changed")
    assert editor.lines()[0] == "&Quit"
    editor.change_view(1)
    assert editor.lines()[0] == "&Quitter"


def test_an_edit_goes_to_the_catalog(folder: Path) -> None:
    editor = editor_for(folder)
    editor.change_view(1)
    editor.edit("Q&uitter\n")
    assert editor.field_text == "Q&uitter "  # a one line message stays on one line


def test_a_category_lists_the_messages_of_its_files(folder: Path) -> None:
    editor = editor_for(folder)
    editor.choose_category(editor.category_ids.index("menus"))
    assert editor.lines() == ["&Quit"]
    editor.choose_category(editor.category_ids.index("dialogs"))
    assert editor.lines() == ["Cannot read {name}"]


def test_a_message_in_no_known_file_is_in_other() -> None:
    assert categories_of(()) == {"other"}
    assert categories_of(("src/n5terminal/ui/main_window.py",)) == {"other"}


def test_a_lost_field_is_refused_and_selected(folder: Path) -> None:
    editor = editor_for(folder)
    editor.change_view(1)
    editor.select(1)
    editor.edit("Lecture impossible")
    editor.choose_category(editor.category_ids.index("menus"))
    problem = editor.check()
    assert problem is not None
    assert "{name}" in problem
    assert editor.message_id == "Cannot read {name}"
    assert editor.category_index == 0


def test_the_untranslated_category_keeps_its_list_while_editing(folder: Path) -> None:
    path = folder / "fr" / "LC_MESSAGES" / "n5terminal.po"
    path.write_text(path.read_text(encoding="utf-8").replace("&Quitter", ""), encoding="utf-8")
    editor = editor_for(folder)
    editor.choose_category(editor.category_ids.index("untranslated"))
    editor.change_view(1)
    assert editor.lines() == ["(not translated)"]
    editor.edit("&Quitter")
    assert editor.lines() == ["&Quitter"]
