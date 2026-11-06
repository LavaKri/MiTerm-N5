"""What Help > Open the help (F1) and Develop > Convert the help to HTML do.

The page of the language of the application is opened in the default browser. See "Help" in
``specs/interface.md``.
"""

import webbrowser
from pathlib import Path

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.help import convert_help, help_name, help_page
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import HelpError
from n5terminal.i18n import _
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.ui.feedback import Feedback


class HelpActions:
    """The commands of the help; ``folder`` is the Help folder (``None``: there is none)."""

    def __init__(
        self,
        presenter: SessionPresenter,
        feedback: Feedback,
        settings: Settings,
        folder: Path | None,
    ) -> None:
        self._presenter = presenter
        self._feedback = feedback
        self._settings = settings
        self._folder = folder

    def open(self) -> None:
        """Open the page of the language in the default browser, or say why it cannot be."""
        language = self._settings.language
        page = help_page(self._folder, language) if self._folder else None
        if page is None:
            self._presenter.say(Announce.HELP_NOT_FOUND, file=f"{help_name(language)}.html")
        elif not webbrowser.open(page.as_uri()):
            self._presenter.say(Announce.HELP_NOT_OPENED)

    def convert(self) -> None:
        """Write the HTML pages from the Markdown ones (develop mode), and tell how many."""
        failure = _("The help could not be converted.\n{error}")
        if self._folder is None:
            self._feedback.show_error(failure.format(error=_("There is no Help folder.")))
            return
        try:
            written = convert_help(self._folder)
        except HelpError as error:
            self._feedback.show_error(failure.format(error=error))
            return
        self._feedback.show_info(_("Help converted: {count} pages.").format(count=len(written)))
