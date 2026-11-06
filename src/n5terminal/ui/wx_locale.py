"""Language of wxWidgets' own texts (stock buttons such as Cancel, standard dialogs)."""

import wx

from n5terminal.i18n import LOCALE_DIR

KEYS_DOMAIN = "wxkeys"  # made by tools/make_wx_keys.py

_WX_LANGUAGES = {"fr": wx.LANGUAGE_FRENCH, "en": wx.LANGUAGE_ENGLISH}


def init_wx_locale(language: str) -> wx.Locale:
    """Make wx use ``language`` for its own texts. Keep the result alive as long as the app runs.

    The texts of the application are translated by ``n5terminal.i18n``; this covers what wx itself
    shows, for example the buttons of its standard dialogs. The catalog ``wxkeys`` is added after
    wx's own, so that the names of keys in a menu are the ones of the application (a catalog added
    later is searched first); English needs none.
    """
    locale = wx.Locale(_WX_LANGUAGES.get(language, wx.LANGUAGE_DEFAULT))
    if (LOCALE_DIR / language / "LC_MESSAGES" / f"{KEYS_DOMAIN}.mo").is_file():
        wx.Locale.AddCatalogLookupPathPrefix(str(LOCALE_DIR))
        locale.AddCatalog(KEYS_DOMAIN)
    return locale
