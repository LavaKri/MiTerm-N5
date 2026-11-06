r"""Makes the catalog of the key names of wxWidgets (``wxkeys``) from ours.

Usage: ``.venv\Scripts\python.exe tools\make_wx_keys.py``. For each language that has a catalog
of the application, writes ``locale/<language>/LC_MESSAGES/wxkeys.po`` and ``.mo``: every name wx
uses in an accelerator (``WX_KEY_IDS``, context "keyboard key") with the translation this
application gives the key. Run it after the translations of the keys change
(``specs/packaging.md``).
"""

import gettext
from pathlib import Path

from babel.messages import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import write_po

from n5terminal.core.config.shortcuts import WX_KEY_IDS
from n5terminal.i18n import DOMAIN, LOCALE_DIR

KEYS_DOMAIN = "wxkeys"
CONTEXT = "keyboard key"


def key_catalog(language: str) -> Catalog:
    """The names of wx for ``language``, in the words of the application."""
    translation = gettext.translation(DOMAIN, localedir=LOCALE_DIR, languages=[language])
    catalog = Catalog(
        locale=language, project="MiTerm-N5 key names", version="", fuzzy=False, charset="utf-8"
    )
    for wx_id, key in WX_KEY_IDS.items():
        catalog.add(wx_id, translation.gettext(key), context=CONTEXT)
    return catalog


def main() -> None:
    for folder in sorted(LOCALE_DIR.glob("*/LC_MESSAGES")):
        language = folder.parent.name
        catalog = key_catalog(language)
        with Path(folder / f"{KEYS_DOMAIN}.po").open("wb") as file:
            write_po(file, catalog, width=100)
        with Path(folder / f"{KEYS_DOMAIN}.mo").open("wb") as file:
            write_mo(file, catalog)
        print(f"{language}: {len(catalog)} names")


if __name__ == "__main__":
    main()
