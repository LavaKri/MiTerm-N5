"""The specs only cite files that exist and keep to the vocabulary of ``specs/glossaire.md``."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [ROOT / "CLAUDE.md", ROOT / "README.md", *sorted((ROOT / "specs").rglob("*.md"))]
#: Where a cited path may start: the repository, the package, the documents.
BASES = (ROOT, ROOT / "src" / "n5terminal", ROOT / "specs")
EXTENSIONS = (".py", ".md", ".bat", ".toml", ".cfg", ".spec", ".po", ".pot", ".mo", ".json")
CODE = re.compile(r"`([^`\n]+)`")
#: Files named in the documents that do not exist (yet), with the reason.
PLANNED = {
    "profiles/git.json": "example of a profile file, written by the profiles step",
    "n5terminal.exe": "the packaged application",
    "n5terminal.bak": "example of a backup file name",
    "settings.json": "the settings file, created when the application runs",
    "Fr.md": "the French help, written by the user in the Help folder",
    "En.md": "the English help, written by the user in the Help folder",
}


def cited_paths(text: str) -> set[str]:
    """What looks like a path to a file of the project in the code spans of ``text``."""
    found = set()
    for span in CODE.findall(text):
        token = span.strip()
        if " " in token or "\\" in token or "*" in token or "<" in token or "{" in token:
            continue
        if token.startswith(".") and "/" not in token:  # an extension, not a file
            continue
        if token.endswith(EXTENSIONS) and not token.startswith(("-", ".venv", "pip")):
            found.add(token.removeprefix("./"))
    return found


FOLDERS = ("src", "tests", "tools", "packaging", "specs")


def exists(path: str) -> bool:
    """A path from a base folder, or a bare file name found anywhere in the project."""
    if path in PLANNED or any((base / path).exists() for base in BASES):
        return True
    if "/" in path:
        return False
    in_folders = any(next((ROOT / folder).rglob(path), None) for folder in FOLDERS)
    return in_folders or (ROOT / path).exists()


@pytest.mark.unit
@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.relative_to(ROOT).as_posix())
def test_every_file_cited_in_a_document_exists(document: Path) -> None:
    missing = sorted(p for p in cited_paths(document.read_text(encoding="utf-8")) if not exists(p))
    assert not missing, f"{document.name} cites files that do not exist: {missing}"


def test_the_detection_finds_paths_and_leaves_commands_alone() -> None:
    text = "See `core/screen/titles.py`, `specs/roadmap.md` and `python -m pytest tests/x.py`."
    assert cited_paths(text) == {"core/screen/titles.py", "specs/roadmap.md"}


CODE_FOLDERS = ("src", "tools", "packaging", "tests")
#: A section of a spec cited in the code: the title in double quotes, then the file in double
#: backquotes (the title may be on the line before the file).
CITED_SECTION = re.compile(r'"([^"\n]+)"\s+in\s+``(specs/[\w/\-]+\.md)``')


def headings(markdown: str) -> list[str]:
    """The titles of the sections of a Markdown document."""
    return [line.lstrip("#").strip() for line in markdown.splitlines() if line.startswith("#")]


def section_exists(title: str, markdown: str) -> bool:
    """Is there a section called ``title`` (or starting with it, then a space or a colon)?"""
    return any(h == title or h.startswith((title + " ", title + ":")) for h in headings(markdown))


def cited_sections() -> list[tuple[Path, str, str]]:
    """Every (file, title, spec) cited in the Python files of the project."""
    found: list[tuple[Path, str, str]] = []
    for folder in CODE_FOLDERS:
        for path in sorted((ROOT / folder).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            found.extend((path, title, spec) for title, spec in CITED_SECTION.findall(text))
    return found


@pytest.mark.unit
def test_every_section_cited_in_the_code_exists_in_the_specs() -> None:
    missing = [
        f"{path.relative_to(ROOT).as_posix()}: {title!r} in {spec}"
        for path, title, spec in cited_sections()
        if not section_exists(title, (ROOT / spec).read_text(encoding="utf-8"))
    ]
    assert not missing, f"sections cited in the code that do not exist: {missing}"


def test_the_code_cites_some_sections() -> None:
    assert len(cited_sections()) > 10


def test_a_section_matches_by_its_title_or_by_the_start_of_it() -> None:
    markdown = "# Titre\n\n## Titres : aller plus loin\n\ntexte\n## Autre (modes 4)"
    assert section_exists("Titre", markdown)
    assert section_exists("Titres", markdown)
    assert section_exists("Autre", markdown)
    assert not section_exists("Tit", markdown)
    assert not section_exists("texte", markdown)


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
SENTENCE_END = re.compile(r"[.!?:][»)\"`*_]*$")


def is_prose(line: str) -> bool:
    """A line of text: not blank, a title, a table row or a quotation block."""
    return (
        bool(line.strip()) and not line.startswith("#") and not line.lstrip().startswith(("|", ">"))
    )


def continues(line: str, following: str) -> bool:
    """Does the text go on from ``line`` to ``following`` (the same paragraph or list item)?"""
    starts_something = LIST_ITEM.match(following) or following.lstrip().startswith("```")
    return is_prose(line) and is_prose(following) and not starts_something


def broken_sentences(markdown: str) -> list[str]:
    """The lines that go on on the next line in the middle of a sentence."""
    broken: list[str] = []
    fenced = False
    lines = markdown.splitlines()
    for line, following in zip(lines, [*lines[1:], ""], strict=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and continues(line, following) and not SENTENCE_END.search(line.rstrip()):
            broken.append(line.strip())
    return broken


@pytest.mark.unit
@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.relative_to(ROOT).as_posix())
def test_no_sentence_of_a_spec_is_cut_at_the_end_of_a_line(document: Path) -> None:
    broken = broken_sentences(document.read_text(encoding="utf-8"))
    assert not broken, f"{document.name}: sentences cut in the middle of a line: {broken[:3]}"


def test_the_detection_of_cut_sentences() -> None:
    assert broken_sentences("Une phrase.\nUne autre phrase.\n- Un item :\n  suite.") == []
    assert broken_sentences("Une phrase coupée\nen deux lignes.") == ["Une phrase coupée"]
    assert broken_sentences("- Un item coupé\n  sur deux lignes.") == ["- Un item coupé"]
