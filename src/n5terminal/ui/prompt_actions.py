"""What the dialog of the prompt patterns does: open it, and keep the result in the settings.

Split from ``actions.py`` (one subject per file). See "Comfortable reading" in
``specs/interface.md``.
"""

import wx

from n5terminal.core.config.settings import Settings
from n5terminal.i18n import _
from n5terminal.presenters.prompt_patterns_editor import PromptPatternsEditor
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.prompt_patterns_dialog import PromptPatternsDialog


class PromptActions:
    """Terminal > Comfortable reading > Command prompts…"""

    def __init__(self, frame: wx.Frame, feedback: Feedback, settings: Settings) -> None:
        self._frame = frame
        self._feedback = feedback
        self._settings = settings

    def _speak(self, text: str) -> None:
        """Say a text of the box (always as a message, whatever the destinations chosen)."""
        self._feedback.announcements.say_text(text)

    def edit(self) -> None:
        """Show the patterns; the settings take them, and are saved, when the box is accepted."""
        editor = PromptPatternsEditor(
            self._settings.patterns(),
            self._settings.comfort_formatting,
            self._settings.comfort_titles,
            _,
        )
        with PromptPatternsDialog(self._frame, editor, self._speak) as dialog:
            if self._feedback.modal(dialog) != wx.ID_OK:
                return
        self._settings.prompt_patterns = editor.patterns
        self._settings.comfort_formatting = editor.formatting
        self._settings.comfort_titles = editor.titles
        self._feedback.save_settings()
