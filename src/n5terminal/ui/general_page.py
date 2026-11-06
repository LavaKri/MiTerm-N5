"""The General page of the Preferences: language, startup profile, lines of the output, window."""

import wx

from n5terminal.core.errors import AssociationError
from n5terminal.i18n import _
from n5terminal.presenters.general_preferences import (
    MAX_OUTPUT_LIMIT,
    MIN_OUTPUT_LIMIT,
    GeneralPreferences,
)


class GeneralPage(wx.Panel):
    """Language, profile to start on, number of lines kept in the output."""

    def __init__(self, parent: wx.Window, preferences: GeneralPreferences) -> None:
        super().__init__(parent)
        self._preferences = preferences
        self._language_codes = [code for code, _name in preferences.language_choices()]

        language_label = wx.StaticText(self, label=_("Language"))
        self.language = wx.Choice(
            self,
            choices=[name for _code, name in preferences.language_choices()],
            name=_("Language"),
        )
        self.language.SetSelection(self._language_codes.index(preferences.language))
        self._profile_names = [name for name, _label in preferences.profile_choices()]
        profile_label = wx.StaticText(self, label=_("Startup profile"))
        self.startup_profile = wx.Choice(
            self,
            choices=[label for _name, label in preferences.profile_choices()],
            name=_("Startup profile"),
        )
        self.startup_profile.SetSelection(self._profile_names.index(preferences.startup_profile))
        self._shown_profile = self.startup_profile.GetSelection()
        limit_label = wx.StaticText(self, label=_("Lines kept in the output"))
        self.limit = wx.SpinCtrl(
            self,
            min=MIN_OUTPUT_LIMIT,
            max=MAX_OUTPUT_LIMIT,
            initial=preferences.output_limit,
            name=_("Lines kept in the output"),
        )

        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        for label, control in (
            (language_label, self.language),
            (profile_label, self.startup_profile),
            (limit_label, self.limit),
        ):
            grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
        grid.AddGrowableCol(1)
        self.maximize = wx.CheckBox(self, label=_("Maximize the window at start"))
        self.maximize.SetValue(preferences.maximize_at_start)
        self.association = wx.Button(self, label=preferences.association_label())
        self.association.Bind(wx.EVT_BUTTON, lambda _event: self._toggle_association())
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        outer.Add(self.maximize, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        outer.Add(self.association, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizer(outer)

    def _toggle_association(self) -> None:
        """Associate or dissociate the launch files now, then say what was done."""
        try:
            message, icon = self._preferences.toggle_association(), wx.ICON_INFORMATION
        except AssociationError as error:
            text = _("The association could not be changed.\n{error}")
            message, icon = text.format(error=error), wx.ICON_ERROR
        caption = _("Error") if icon == wx.ICON_ERROR else _("Information")
        with wx.MessageDialog(self, message, caption, wx.OK | icon) as box:
            box.ShowModal()
        self.association.SetLabel(self._preferences.association_label())
        self.association.SetFocus()

    def commit(self) -> None:
        """Hand what the controls show to the draft."""
        self._preferences.select_language(self._language_codes[self.language.GetSelection()])
        if self.startup_profile.GetSelection() != self._shown_profile:  # only a choice is written
            self._preferences.select_startup_profile(
                self._profile_names[self.startup_profile.GetSelection()]
            )
        self._preferences.set_output_limit(self.limit.GetValue())
        self._preferences.maximize_at_start = self.maximize.GetValue()
