"""The Announcements page of the Preferences: the output, then where each category goes.

At the top, the output of the announcements (UI Automation or none). Below, a list with one line
per category, saying the category then its destination (nothing depends on columns), and a choice
of the destination of the selected category, which only offers what the category accepts.
"""

import wx

from n5terminal.core.config.announcements import Category, Destination
from n5terminal.core.config.settings import ACTIVITY_INTERVALS
from n5terminal.i18n import _
from n5terminal.presenters.announcements_preferences import AnnouncementsPreferences


class AnnouncementsPage(wx.Panel):
    """The output of the announcements and the destination of each category."""

    def __init__(self, parent: wx.Window, preferences: AnnouncementsPreferences) -> None:
        super().__init__(parent)
        self._preferences = preferences
        self._categories: list[Category] = preferences.categories()
        self._choices: list[Destination] = []
        self._output_ids = [output.id for output in preferences.output_choices()]

        output_label = wx.StaticText(self, label=_("Announcement output"))
        self.output = wx.Choice(
            self,
            choices=[preferences.output_name(output) for output in preferences.output_choices()],
            name=_("Announcement output"),
        )
        self.output.SetSelection(self._output_ids.index(preferences.screen_reader_output))
        categories_label = wx.StaticText(self, label=_("Categories of announcements"))
        self.categories = wx.ListBox(
            self,
            choices=[preferences.line(category) for category in self._categories],
            name=_("Categories of announcements"),
        )
        destination_label = wx.StaticText(self, label=_("Destination"))
        self.destination = wx.Choice(self, name=_("Destination"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(output_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.output, 0, wx.EXPAND | wx.ALL, 12)
        sizer.Add(categories_label, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.categories, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(destination_label, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.destination, 0, wx.EXPAND | wx.ALL, 12)
        interval_label = wx.StaticText(
            self, label=_("Interval of the check of the activity (in seconds)")
        )
        self.interval = wx.SpinCtrl(
            self,
            min=ACTIVITY_INTERVALS.start,
            max=ACTIVITY_INTERVALS.stop - 1,
            initial=preferences.activity_interval,
            name=_("Interval of the check of the activity (in seconds)"),
        )
        self.only_in_output = wx.CheckBox(
            self,
            label=_("Activity announced only in the output area"),
            name=_("Activity announced only in the output area"),
        )
        self.only_in_output.SetValue(preferences.activity_only_in_output)
        sizer.Add(interval_label, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.interval, 0, wx.ALL, 12)
        sizer.Add(self.only_in_output, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizer(sizer)
        self.categories.Bind(wx.EVT_LISTBOX, lambda _event: self._show_destination())
        self.destination.Bind(wx.EVT_CHOICE, lambda _event: self._choose_destination())
        self.categories.SetSelection(0)
        self._show_destination()

    def commit(self) -> None:
        """Hand the output chosen to the draft (the destinations are handed when chosen)."""
        self._preferences.select_output(self._output_ids[self.output.GetSelection()])
        self._preferences.set_activity_interval(self.interval.GetValue())
        self._preferences.activity_only_in_output = self.only_in_output.GetValue()

    def _selected(self) -> Category:
        index: int = self.categories.GetSelection()
        return self._categories[index]

    def _show_destination(self) -> None:
        """Offer the destinations the selected category accepts, with its current one chosen."""
        category = self._selected()
        self._choices = self._preferences.choices(category)
        self.destination.Set([self._preferences.destination_name(d) for d in self._choices])
        self.destination.SetSelection(self._choices.index(self._preferences.destination(category)))

    def _choose_destination(self) -> None:
        index = self.categories.GetSelection()
        self._preferences.select(
            self._categories[index], self._choices[self.destination.GetSelection()]
        )
        self.categories.SetString(index, self._preferences.line(self._categories[index]))
