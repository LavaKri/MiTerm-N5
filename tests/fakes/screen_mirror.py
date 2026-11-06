"""Applies screen model updates as the output area will: fixed lines appended, rows replaced."""

from n5terminal.core.screen.screen_model import FixedLine, ScreenModel, ScreenRow, ScreenUpdate


class ScreenMirror:
    """The fixed part and the live part of the output area, as a model's updates build them."""

    def __init__(self) -> None:
        self.fixed: list[FixedLine] = []
        self.rows: dict[int, ScreenRow] = {}
        self.overflows: list[int] = []
        self.cursor = (0, 0)
        self.updates: list[ScreenUpdate] = []

    def apply(self, update: ScreenUpdate) -> None:
        self.updates.append(update)
        self.fixed.extend(update.fixed)
        if update.replace_all:
            self.rows.clear()
        self.rows.update({row.number: row for row in update.rows})
        self.overflows.extend(update.overflows)
        self.cursor = (update.cursor_row, update.cursor_column)

    def take(self, model: ScreenModel) -> ScreenUpdate:
        update = model.take_update()
        self.apply(update)
        return update

    def lines(self) -> list[str]:
        """The text the output area holds: the fixed part, then the live part, without the blank
        lines at the end."""
        lines = [line.text for line in self.fixed]
        lines.extend(self.rows[number].text for number in sorted(self.rows))
        while lines and not lines[-1]:
            lines.pop()
        return lines
