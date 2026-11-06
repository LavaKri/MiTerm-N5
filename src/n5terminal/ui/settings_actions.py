"""What the commands that change a setting do: the Preferences, the PowerShell, the activity signal.

Split from ``actions.py`` (one subject per file). Each command saves the settings once it has
changed them (``Feedback.save_settings`` tells the user if that fails).
"""

from collections.abc import Callable

import wx

from n5terminal.core.config.announcements import ACTIVITY, Announce, Destination
from n5terminal.core.config.file_association import FileAssociation
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.powershells import installed_powershells, is_valid_powershell
from n5terminal.core.session.session_state import CommandId
from n5terminal.i18n import _
from n5terminal.presenters.powershell_choice import PowerShellChoice
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.output_area import OutputArea
from n5terminal.ui.powershell_dialog import PowerShellDialog
from n5terminal.ui.preferences_dialog import PreferencesDialog


class SettingsActions:
    """The commands that change a setting.

    ``profile_names`` gives the profiles the Preferences offer to start on; ``on_shortcuts_changed``
    is called when the shortcuts changed, so that the window takes the new ones.
    """

    def __init__(
        self,
        frame: wx.Frame,
        presenter: SessionPresenter,
        feedback: Feedback,
        output: OutputArea,
        settings: Settings,
        menus: MenuBuilder,
        association: FileAssociation | None,
        profile_names: Callable[[], list[str]],
        on_shortcuts_changed: Callable[[], None],
    ) -> None:
        self._frame = frame
        self._presenter = presenter
        self._feedback = feedback
        self._output = output
        self._settings = settings
        self._menus = menus
        self._association = association
        self._profile_names = profile_names
        self._on_shortcuts_changed = on_shortcuts_changed

    def refresh_activity_check(self) -> None:
        """Check the item "Signal activities" when the activity is signaled somewhere."""
        signaled = self._settings.destination_for(ACTIVITY) is not Destination.NONE
        self._menus.set_checked(CommandId.SIGNAL_ACTIVITIES, signaled)

    def toggle_activity(self) -> None:
        """Ctrl+B and the item: switch the activity off, or back on to the choice it had."""
        signaled = self._settings.toggle_activity()
        self._feedback.save_settings()
        self.refresh_activity_check()
        self._presenter.say(Announce.ACTIVITY_ON if signaled else Announce.ACTIVITY_OFF)

    def select_powershell(self) -> None:
        """The PowerShell the interpreter starts: one found on the computer, or a path."""
        draft = PowerShellChoice(
            self._presenter.powershell_path, installed_powershells(), _, is_valid_powershell
        )
        dialog = PowerShellDialog(self._frame, draft)
        with dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
            dialog.commit()
        if self._presenter.set_powershell_path(draft.chosen_path()):
            self._feedback.save_settings()

    def preferences(self) -> None:
        """Show the Preferences, then apply what changed."""
        dialog = PreferencesDialog(
            self._frame, self._settings, self._association, self._profile_names()
        )
        with dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
            changes = dialog.commit()
        if not changes.any:
            return
        self._feedback.save_settings()
        self.refresh_activity_check()
        if changes.screen_reader_output:
            self._feedback.apply_screen_reader_output(self._settings.screen_reader_output)
        if changes.shortcuts:
            self._on_shortcuts_changed()
        if changes.output_limit:
            self._output.set_limit(self._settings.output_limit)
        if changes.language:
            self._feedback.show_info(_("The language will change at the next start."))
