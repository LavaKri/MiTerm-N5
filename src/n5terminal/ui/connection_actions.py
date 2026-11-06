"""What the Connection menu does: choose, add, edit and delete a connection, pick the ``ssh.exe``.

Split from ``actions.py`` (one subject per file). The connections on disk are read through the
``ConnectionCatalog``; the session takes the chosen one (``SessionPresenter.select_connection``).
Opening and closing the connection are commands of the session itself.
"""

import wx

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.connections import Connection
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import ConnectionFileError
from n5terminal.core.session.ssh_clients import installed_ssh_clients
from n5terminal.i18n import _
from n5terminal.presenters.connection_catalog import ConnectionCatalog
from n5terminal.presenters.connection_editor import ConnectionEditor
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.presenters.ssh_choice import SshChoice
from n5terminal.ui.connection_dialog import ConnectionDialog
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.ssh_dialog import SshDialog


class ConnectionActions:
    """The commands of the Connection menu."""

    def __init__(
        self,
        frame: wx.Frame,
        presenter: SessionPresenter,
        feedback: Feedback,
        settings: Settings,
        catalog: ConnectionCatalog,
    ) -> None:
        self._frame = frame
        self._presenter = presenter
        self._feedback = feedback
        self._settings = settings
        self._catalog = catalog

    def names(self) -> list[str]:
        """The connections on disk now (read again each time the menu opens)."""
        return self._catalog.names()

    def current(self) -> str | None:
        return self._presenter.state.connection

    def choose(self, name: str | None) -> None:
        """Choose the connection ``name`` (``None``: Locale)."""
        connection = self._catalog.get(name) if name is not None else None
        if name is not None and connection is None:
            return  # the file went away since the menu was made
        self._presenter.select_connection(connection)

    def add(self) -> None:
        """Start the dialog on an empty connection; the new one is chosen once written."""
        self._edit(Connection(""))

    def edit(self) -> None:
        name = self._presenter.state.connection
        self._catalog.reload()  # the one to edit may have changed on disk
        connection = self._catalog.get(name) if name is not None else None
        if connection is None:
            self._feedback.show_error(
                _("The connection {name} no longer exists.").format(name=name)
            )
            self._presenter.select_connection(None)
            return
        self._edit(connection)

    def delete(self) -> None:
        name = self._presenter.state.connection
        if name is None or not self._catalog.writable:
            return
        question = _("Delete the connection {name}?").format(name=name)
        if not self._feedback.confirm(_("Delete a connection"), question):
            return
        try:
            self._catalog.delete(name)
        except ConnectionFileError as error:
            self._feedback.show_error(
                _("The connection could not be deleted.\n{error}").format(error=error)
            )
            return
        self._presenter.select_connection(None)

    def select_ssh(self) -> None:
        """The ``ssh.exe`` the connections start: the one of Windows, another found, or a path."""
        draft = SshChoice(self._settings.ssh_path, installed_ssh_clients(), _)
        dialog = SshDialog(self._frame, draft)
        with dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
            dialog.commit()
        self._settings.ssh_path = draft.chosen_path()
        self._feedback.save_settings()
        self._presenter.say(Announce.SSH_CHANGED, ssh=draft.name())

    def _edit(self, start: Connection) -> None:
        """Run the connection dialog on ``start`` and write the result."""
        if not self._catalog.writable:
            return
        editor = ConnectionEditor(start, self._catalog.names(), _)
        dialog = ConnectionDialog(self._frame, editor)
        with dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
            dialog.commit()
        connection = editor.build()
        try:
            self._catalog.save(connection, editor.replaces)
        except ConnectionFileError as error:
            self._feedback.show_error(
                _("The connection could not be saved.\n{error}").format(error=error)
            )
            return
        self._catalog.reload()
        # A connection just added is chosen (adding is only possible with none open); one edited
        # was the chosen one, and the session takes its new values.
        saved = self._catalog.get(connection.name) or connection
        if editor.is_new:
            self._presenter.select_connection(saved)
        else:
            self._presenter.refresh_connection(saved)
