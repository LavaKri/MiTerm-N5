"""What the Develop menu does (develop mode): edit the translations, launch a test program.

Split from ``actions.py`` (one subject per file). Which programs there are and how one is launched
is in ``presenters/develop_programs.py``.
"""

from pathlib import Path

import wx

from n5terminal.core.config.catalogs import Catalogs
from n5terminal.core.errors import CatalogError
from n5terminal.i18n import LOCALE_DIR, _
from n5terminal.presenters.catalogs_editor import CatalogsEditor
from n5terminal.presenters.develop_programs import list_test_programs, program_command
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.ui.catalogs_dialog import CatalogsDialog
from n5terminal.ui.feedback import Feedback


class DevelopActions:
    """The commands of the Develop menu; ``develop_folder`` is ``None`` outside the develop mode."""

    def __init__(
        self,
        frame: wx.Frame,
        presenter: SessionPresenter,
        feedback: Feedback,
        develop_folder: Path | None,
    ) -> None:
        self._frame = frame
        self._presenter = presenter
        self._feedback = feedback
        self._develop_folder = develop_folder

    def catalogs(self) -> None:
        """Edit the translations, then write the catalogs."""
        try:
            editor = CatalogsEditor(Catalogs.load(LOCALE_DIR))
            with CatalogsDialog(self._frame, editor) as dialog:
                if self._feedback.modal(dialog) != wx.ID_OK:
                    return
            editor.save()
        except CatalogError as error:
            self._feedback.show_error(
                _("The catalogs could not be used.\n{error}").format(error=error)
            )
            return
        self._feedback.show_info(_("The catalogs are saved. The changes show at the next start."))

    def test_programs(self) -> list[Path]:
        """The test programs of the develop folder, read again each time the menu opens."""
        return list_test_programs(self._develop_folder)

    def run_test_program(self, program: Path) -> None:
        """Launch ``program`` as a typed command, shown in the output by its file name."""
        self._presenter.submit(program_command(program), program.name)
