"""A session view that records what the presenter asks of it."""

from n5terminal.core.screen.screen_model import ScreenUpdate
from n5terminal.core.session.session_state import CommandId, SessionState
from n5terminal.presenters.session_view import InputMode


class FakeView:
    def __init__(self) -> None:
        self.outputs: list[tuple[ScreenUpdate, int]] = []
        self.cleared_outputs = 0
        self.shown_states: list[SessionState] = []
        self.enabled: list[frozenset[CommandId]] = []
        self.input_modes: list[InputMode] = []
        self.input_labels: list[str] = []
        self.cleared_inputs = 0
        self.states: list[str] = []
        self.titles: list[str] = []
        self.focus_calls: list[str] = []
        self.trimmed_lines = 0  # what the next show_output says the limit removed
        self.output_focused = True  # what output_has_focus says
        self.caret = ("", False)  # what caret_line says: the line, the cursor inside its text
        # The dialogs of a connection: answers given in advance, and what was asked.
        self.host_key_answers: list[bool] = []
        self.secret_answers: list[str | None] = []
        self.dialogs: list[tuple[str, str, str, str]] = []  # (kind, title, where, text)
        self.withdrawn_dialogs = 0

    def confirm_host_key(self, title: str, where: str, text: str) -> bool:
        self.dialogs.append(("host_key", title, where, text))
        return self.host_key_answers.pop(0) if self.host_key_answers else False

    def ask_secret(self, title: str, where: str, question: str) -> str | None:
        self.dialogs.append(("secret", title, where, question))
        return self.secret_answers.pop(0) if self.secret_answers else None

    def withdraw_dialog(self) -> None:
        self.withdrawn_dialogs += 1

    def output_has_focus(self) -> bool:
        return self.output_focused

    def caret_line(self) -> tuple[str, bool]:
        return self.caret

    def show_output(self, update: ScreenUpdate, dropped_lines: int) -> int:
        self.outputs.append((update, dropped_lines))
        return self.trimmed_lines

    def clear_output(self) -> None:
        self.cleared_outputs += 1

    def show_state(self, state: SessionState) -> None:
        self.shown_states.append(state)

    def set_commands_enabled(self, enabled: frozenset[CommandId]) -> None:
        self.enabled.append(enabled)

    def set_input_mode(self, mode: InputMode, label: str) -> None:
        self.input_modes.append(mode)
        self.input_labels.append(label)

    def clear_input(self) -> None:
        self.cleared_inputs += 1

    def set_status_state(self, text: str) -> None:
        self.states.append(text)

    def focus_output(self) -> None:
        self.focus_calls.append("output")

    def focus_output_on_command(self, lines: int) -> None:
        self.focus_calls.append(f"command:{lines}")

    def set_title(self, text: str) -> None:
        self.titles.append(text)

    # What the tests read.

    @property
    def last_enabled(self) -> frozenset[CommandId]:
        return self.enabled[-1]

    @property
    def last_state(self) -> str:
        return self.states[-1]

    def fixed_lines(self) -> list[str]:
        return [line.text for update, _dropped in self.outputs for line in update.fixed]

    def live_rows(self) -> dict[int, str]:
        rows: dict[int, str] = {}
        for update, _dropped in self.outputs:
            if update.replace_all:
                rows.clear()
            rows.update({row.number: row.text for row in update.rows})
        return rows
