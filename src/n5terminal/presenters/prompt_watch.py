"""Follows the screen of a shell that stays open and says whether it waits at its prompt.

The rule itself is in ``core/session/shell_prompt.py``; this keeps what it needs from the stream of
updates: the rows of the screen and the cursor. A line typed into the shell makes the answer "busy"
at once, and it stays so until the shell has shown something new (otherwise the old prompt, still on
the screen for a few milliseconds, would be taken for a new one).
"""

from n5terminal.core.screen.screen_model import ScreenRow, ScreenUpdate
from n5terminal.core.session.session_state import Interpreter
from n5terminal.core.session.shell_prompt import at_prompt
from n5terminal.core.transport.transport import ProcessCounter, Transport


class PromptWatch:
    """The screen of one shell, as the updates build it."""

    def __init__(self) -> None:
        self._rows: dict[int, ScreenRow] = {}
        self._cursor_row = 0
        self._settled = False

    def reset(self) -> None:
        """A new shell starts: nothing is known of its screen."""
        self._rows = {}
        self._cursor_row = 0
        self._settled = False

    def typed(self) -> None:
        """A line was written into the shell: busy until it shows something new."""
        self._settled = False

    def screen(self, update: ScreenUpdate) -> None:
        """The shell showed something."""
        if update.replace_all:
            self._rows = {}
        self._rows.update({row.number: row for row in update.rows})
        self._cursor_row = update.cursor_row
        self._settled = True

    def _cursor_line(self) -> str:
        """The line the cursor is on, as the shell wrote it.

        A prompt longer than the screen is wrapped by the terminal over several rows (a deep
        folder): the rows marked ``continued`` before the cursor belong to the same line.
        """
        first = self._cursor_row
        while first > 0 and first - 1 in self._rows and self._rows[first - 1].continued:
            first -= 1
        rows = (self._rows.get(number) for number in range(first, self._cursor_row + 1))
        return "".join(row.text for row in rows if row is not None)

    def at_prompt(
        self, interpreter: Interpreter, transport: Transport, prompt_prefix: str = ""
    ) -> bool:
        """Does the shell wait at its prompt now? ``prompt_prefix`` is the shell's own."""
        if not self._settled:
            return False
        processes = transport.active_processes() if isinstance(transport, ProcessCounter) else None
        return at_prompt(interpreter, processes, self._cursor_line(), prompt_prefix)
