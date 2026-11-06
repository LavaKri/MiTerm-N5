"""A locale folder in a temporary folder: a template and a French catalog."""

from pathlib import Path

TEMPLATE = """\
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\\n"

#: src/n5terminal/ui/main_menu.py
msgid "&Quit"
msgstr ""

#: src/n5terminal/ui/actions.py src/n5terminal/ui/feedback.py
#, python-brace-format
msgid "Cannot read {name}"
msgstr ""
"""

FRENCH = """\
msgid ""
msgstr ""
"Language: fr\\n"
"Content-Type: text/plain; charset=utf-8\\n"

#, python-brace-format
msgid "Cannot read {name}"
msgstr "Lecture de {name} impossible"

msgid "&Quit"
msgstr "&Quitter"
"""


def make_catalog_folder(root: Path) -> Path:
    (root / "n5terminal.pot").write_text(TEMPLATE, encoding="utf-8")
    catalog = root / "fr" / "LC_MESSAGES"
    catalog.mkdir(parents=True)
    (catalog / "n5terminal.po").write_text(FRENCH, encoding="utf-8")
    return root
