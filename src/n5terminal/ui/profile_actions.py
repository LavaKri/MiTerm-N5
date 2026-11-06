"""What the Profile menu does: choose, add, edit and delete a profile, give its variables.

Split from ``actions.py`` (one subject per file). The profiles on disk are read through the
``ProfileCatalog``; the session takes the chosen one (``SessionPresenter.select_profile``), and the
window shows what the profile sets (the terminal view, the size).
"""

import wx

from n5terminal.core.config.launch_file import LaunchFile
from n5terminal.core.config.profiles import Profile
from n5terminal.core.errors import ProfileError
from n5terminal.core.screen.terminal_size import size_from_text
from n5terminal.core.session.session_state import CommandId, Phase
from n5terminal.i18n import _
from n5terminal.presenters.profile_catalog import ProfileCatalog
from n5terminal.presenters.profile_editor import ProfileEditor, variable_label
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.menus import MenuBuilder
from n5terminal.ui.output_area import OutputArea
from n5terminal.ui.profile_dialog import ProfileDialog
from n5terminal.ui.variables_dialog import VariablesDialog


class ProfileActions:
    """The commands of the Profile menu."""

    def __init__(
        self,
        frame: wx.Frame,
        presenter: SessionPresenter,
        feedback: Feedback,
        output: OutputArea,
        menus: MenuBuilder,
        catalog: ProfileCatalog,
    ) -> None:
        self._frame = frame
        self._presenter = presenter
        self._feedback = feedback
        self._output = output
        self._menus = menus
        self._catalog = catalog

    def names(self) -> list[str]:
        """The profiles on disk now (read again each time the menu opens)."""
        return self._catalog.names()

    def current(self) -> str | None:
        return self._presenter.state.profile

    def choose(self, name: str | None) -> None:
        """Choose the profile ``name`` (``None``: the free profile) and show what it sets."""
        profile = self._catalog.get(name) if name is not None else None
        if name is not None and profile is None:
            return  # the file went away since the menu was made
        if not self._presenter.select_profile(profile) or profile is None:
            return
        self._output.set_show_history(not profile.terminal_view_only)
        self._menus.set_checked(CommandId.SET_TERMINAL_VIEW, profile.terminal_view_only)
        self._menus.check("size", size_from_text(profile.terminal_size))

    def apply_launch_file(self, launch: LaunchFile) -> list[str]:
        """Choose the profile of the launch file and give it its variables.

        Returns what could not be done, in words for the user.
        """
        if launch.profile is None:
            return []
        self._catalog.reload()
        profile = self._catalog.find(launch.profile)
        if profile is None:
            return [_("The profile {name} does not exist.").format(name=launch.profile)]
        self.choose(profile.name)
        if launch.variables:
            self._presenter.profile_values.set(profile.name, launch.variables)
        return []

    def apply_startup_profile(self, name: str) -> list[str]:
        """Choose the profile the application starts on (empty: the free profile).

        A profile that no longer exists, or cannot be read, leaves the free profile. Returns what
        could not be done, in words for the user.
        """
        if not name:
            return []
        self._catalog.reload()
        profile = self._catalog.find(name)
        if profile is None:
            return [_("The startup profile {name} does not exist.").format(name=name)]
        self.choose(profile.name)
        return []

    def add(self) -> None:
        """Start the dialog on what the session uses now; the new profile is chosen once written."""
        start = self._presenter.session_values()
        start.terminal_view_only = not self._output.show_history
        self._edit(start)

    def edit(self) -> None:
        name = self._presenter.state.profile
        self._catalog.reload()  # the one to edit may have changed on disk
        profile = self._catalog.get(name) if name is not None else None
        if profile is None:
            self._feedback.show_error(_("The profile {name} no longer exists.").format(name=name))
            self._presenter.select_profile(None)
            return
        self._edit(profile)

    def delete(self) -> None:
        name = self._presenter.state.profile
        if name is None or not self._catalog.writable:
            return
        question = _("Delete the profile {profile}?").format(profile=name)
        if not self._feedback.confirm(_("Delete a profile"), question):
            return
        try:
            self._catalog.delete(name)
        except ProfileError as error:
            self._feedback.show_error(
                _("The profile could not be deleted.\n{error}").format(error=error)
            )
            return
        self._presenter.profile_values.forget(name)
        self._presenter.select_profile(None)

    def define_variables(self) -> None:
        name = self._presenter.state.profile
        if name is None:
            return
        values = self._presenter.profile_values
        fields = [(variable, variable_label(variable, _)) for variable in values.variables()]
        dialog = VariablesDialog(self._frame, name, fields, values.get(name))
        with dialog:
            if self._feedback.modal(dialog) == wx.ID_OK:
                values.set(name, dialog.values())

    def _edit(self, start: Profile) -> None:
        """Run the profile dialog on ``start`` and write the result."""
        if not self._catalog.writable:
            return
        editor = ProfileEditor(start, self._catalog.names(), _)
        dialog = ProfileDialog(self._frame, editor)
        with dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
            dialog.commit()
        profile = editor.build()
        try:
            self._catalog.save(profile, editor.replaces)
        except ProfileError as error:
            self._feedback.show_error(
                _("The profile could not be saved.\n{error}").format(error=error)
            )
            return
        if not editor.is_new:
            self._presenter.profile_values.rename(editor.replaces or "", profile.name)
        self._catalog.reload()
        # The profile in use is chosen again, so that its new values apply at once; a profile just
        # added is chosen too, unless a program runs (adding is allowed then, choosing is not).
        if not editor.is_new or self._presenter.state.phase is Phase.IDLE:
            self.choose(profile.name)
