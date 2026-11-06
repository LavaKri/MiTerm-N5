"""The Preferences dialog: one page per subject, in a notebook.

Only layout and wiring; the choices and their rules are in the ``presenters/*_preferences.py``.
Each control has an accessible name and is created right after its label, so that a screen reader
pairs them. Enter is OK, Escape is Cancel. The dialog opens with the focus on the tab of the first
page (General), so that the user hears where they are before going into a page.
"""

from collections.abc import Sequence

import wx

from n5terminal.core.config.file_association import FileAssociation
from n5terminal.core.config.settings import Settings
from n5terminal.i18n import _
from n5terminal.presenters.announcements_preferences import AnnouncementsPreferences
from n5terminal.presenters.general_preferences import GeneralPreferences
from n5terminal.presenters.preferences_changes import AppliedChanges
from n5terminal.presenters.shortcuts_preferences import ShortcutsPreferences
from n5terminal.ui.announcements_page import AnnouncementsPage
from n5terminal.ui.general_page import GeneralPage
from n5terminal.ui.shortcuts_page import ShortcutsPage


class PreferencesDialog(wx.Dialog):
    """The Preferences. ``commit`` writes the choices to the settings and tells what changed."""

    def __init__(
        self,
        parent: wx.Window,
        settings: Settings,
        association: FileAssociation | None = None,
        profile_names: Sequence[str] = (),
    ) -> None:
        super().__init__(
            parent, title=_("Preferences"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._general = GeneralPreferences(settings, association, _, profile_names)
        self._announcements = AnnouncementsPreferences(settings, _)
        self._shortcuts = ShortcutsPreferences(settings, _)
        self.notebook = wx.Notebook(self, name=_("Preferences"))
        self.general_page = GeneralPage(self.notebook, self._general)
        self.notebook.AddPage(self.general_page, _("General"))
        self.shortcuts_page = ShortcutsPage(self.notebook, self._shortcuts)
        self.notebook.AddPage(self.shortcuts_page, _("Shortcuts"))
        self.announcements_page = AnnouncementsPage(self.notebook, self._announcements)
        self.notebook.AddPage(self.announcements_page, _("Announcements"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize(wx.Size(680, 600))
        self.notebook.SetSelection(0)
        self.notebook.SetFocus()

    def commit(self) -> AppliedChanges:
        self.general_page.commit()
        self.announcements_page.commit()
        return (
            self._general.apply()
            .merged(self._announcements.apply())
            .merged(self._shortcuts.apply())
        )
