"""The way of the output from the exchange to the window, and the lines the session writes itself.

Split from ``session_presenter.py`` (one subject per file). The transport threads publish to the
exchange; the presenter asks for what accumulated at each tick and the window shows it. Announced
here: what the window dropped for lack of room, and what was lost because it came too slowly.
"""

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.config.settings import Settings
from n5terminal.core.screen.display_exchange import DisplayExchange
from n5terminal.core.screen.screen_model import FixedLine, ScreenUpdate
from n5terminal.presenters.session_view import SessionView


class OutputFlow:
    """Hands the output to the window and writes the lines of the session (echo of a command)."""

    def __init__(self, view: SessionView, settings: Settings, say: Say) -> None:
        self.exchange = DisplayExchange()
        self._view = view
        self._settings = settings
        self._say = say
        self._trim_announced = False  # the limit of the output was said since it was last cleared

    def show(self) -> ScreenUpdate | None:
        """Give the window what accumulated; that update, or ``None`` when nothing did."""
        batch = self.exchange.take()
        if batch is None:
            return None
        trimmed = self._view.show_output(batch.update, batch.dropped_lines)
        self._report_dropped(batch.dropped_lines, trimmed)
        return batch.update

    def clear(self) -> None:
        """Empty the output area; what accumulated and was not shown is forgotten."""
        self.exchange.take()
        self._view.clear_output()
        self._trim_announced = False

    def echo(self, line: str, prefix: str, *details: str) -> int:
        """Write the typed line in the output, so that the session reads as a complete log.

        ``details`` are lines written under it. Returns how many lines were written.
        """
        fixed = (FixedLine(f"{prefix}{line}"), *(FixedLine(text) for text in details))
        self.exchange.publish(
            ScreenUpdate(
                fixed=fixed,
                rows=(),
                replace_all=False,
                overflows=(),
                columns=0,
                row_count=1,
                cursor_row=0,
                cursor_column=0,
            )
        )
        return len(fixed)

    def close_with(self, line: str) -> None:
        """Write ``line`` in the closing part, after the live part (the end of a connection).

        The update says nothing of the screen (``row_count`` 0): the cursor of the terminal stays.
        """
        self.exchange.publish(
            ScreenUpdate(
                fixed=(),
                rows=(),
                replace_all=False,
                overflows=(),
                columns=0,
                row_count=0,
                cursor_row=0,
                cursor_column=0,
                closing=(FixedLine(line),),
            )
        )

    def _report_dropped(self, lost: int, trimmed: int) -> None:
        """Lines lost to a slow window are said each time; those past the limit, once per output."""
        if lost:
            self._say(Announce.LINES_LOST, count=lost)
        if trimmed and not self._trim_announced:
            self._trim_announced = True
            self._say(Announce.LINES_DROPPED, limit=self._settings.output_limit)
