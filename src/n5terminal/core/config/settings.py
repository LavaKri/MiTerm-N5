"""User settings, stored as JSON (the file is chosen by ``location.py``).

Only what a feature already uses is here; the other settings (profiles) come with their feature.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from n5terminal.core.config.announcements import ACTIVITY, CATEGORIES, Category, Destination
from n5terminal.core.config.jsonstore import read_json, write_json
from n5terminal.core.config.prompt_patterns import (
    PromptPattern,
    current_pattern,
    start_patterns,
)
from n5terminal.core.config.screen_reader import default_output, output_named
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    ConfigurableCommand,
    check_shortcut,
    normalize_shortcut,
)
from n5terminal.core.errors import JsonStoreError, SettingsError

SETTINGS_FILE_NAME = "settings.json"
SUPPORTED_LANGUAGES = ("fr", "en")
MAX_RECENT_FOLDERS = 10
OUTPUT_LIMITS = range(1_000, 100_001)  # lines the output area keeps
DEFAULT_OUTPUT_LIMIT = 10_000
ACTIVITY_INTERVALS = range(1, 11)  # seconds between two checks of the activity
# What a new session starts with; the values are those of ``LaunchMode``, ``Interpreter`` (the
# session package comes after this one) and ``TerminalSize`` ("80x24", or "auto").
LAUNCH_MODES = ("cli", "tui")
INTERPRETERS = ("none", "cmd", "powershell")
AUTOMATIC_SIZE = "auto"
_SIZE_PATTERN = re.compile(r"[1-9]\d{0,3}x[1-9]\d{0,3}")


def is_valid_size(text: str) -> bool:
    """Is ``text`` a terminal size as the files write it: ``auto`` or ``<columns>x<rows>``?"""
    return text == AUTOMATIC_SIZE or _SIZE_PATTERN.fullmatch(text) is not None


def _destination_named(name: str) -> Destination | None:
    return next((d for d in Destination if d.value == name), None)


def _load_announcements(raw: object) -> dict[str, str]:
    """The destinations of the file that are known, accepted by their category, not the default."""
    if not isinstance(raw, dict):
        return {}
    known = {category.id: category for category in CATEGORIES}
    chosen: dict[str, str] = {}
    for category_id, name in raw.items():
        category = known.get(category_id)
        destination = _destination_named(name) if isinstance(name, str) else None
        if (
            category is not None
            and destination is not None
            and category.accepts(destination)
            and destination is not category.default
        ):
            chosen[category_id] = destination.value
    return chosen


def folder_key(folder: Path) -> str:
    """How a folder is compared in the recent folders (Windows paths ignore the case)."""
    return str(folder).lower()


@dataclass(slots=True)
class Settings:
    """Application settings. Unknown keys in the file are ignored."""

    language: str = "fr"
    recent_folders: list[str] = field(default_factory=list)  # the most recent first
    shortcuts: dict[str, str] = field(default_factory=dict)  # only the changed ones
    screen_reader_output: str = field(default_factory=lambda: default_output().id)
    announcements: dict[str, str] = field(default_factory=dict)  # category id -> destination
    output_limit: int = DEFAULT_OUTPUT_LIMIT  # lines kept in the output area, the oldest dropped
    launch_mode: str = "cli"  # how a new session serves programs
    interpreter: str = "none"  # the shell a new session goes through
    powershell_path: str = ""  # the PowerShell the interpreter starts (empty: Windows PowerShell)
    ssh_path: str = ""  # the ssh.exe of the connections (empty: the one of Windows)
    startup_profile: str = ""  # the profile the application starts on (empty: the free profile)
    terminal_size: str = AUTOMATIC_SIZE  # the size of a new session's terminal
    # The output area holds only the lines of the terminal ("Terminal view only" of the View menu),
    # not the history before them.
    terminal_view_only: bool = False
    stderr_prefix: bool = True  # a line of the standard error starts with "StdErr: " (pipes)
    maximize_at_start: bool = True  # the main window opens maximized
    activity_interval: int = 1  # seconds between two checks of the activity flag
    activity_only_in_output: bool = True  # the activity is signaled with the focus in the output
    activity_last_choice: str = ""  # the destination to bring back when the activity is switched on
    # Comfortable reading: the prompts left out of a line read, in the order they are tried,
    # and whether the line read keeps its formatting (as the Read the line key says it).
    # ``None``: the start list, made when it is used, in the language then in use.
    prompt_patterns: list[PromptPattern] | None = None
    comfort_formatting: bool = True
    comfort_titles: bool = False  # the move by titles says the title without its prompt too
    store: Path | None = None
    load_warning: str = ""  # what went wrong while reading the file, for the user

    def patterns(self) -> list[PromptPattern]:
        """The prompt patterns now in use: the ones chosen, else the start list."""
        return start_patterns() if self.prompt_patterns is None else self.prompt_patterns

    def shortcut_for(self, command: ConfigurableCommand) -> str:
        """The shortcut of ``command`` (empty: none)."""
        return self.shortcuts.get(command.id, command.default)

    def set_shortcut(self, command: ConfigurableCommand, shortcut: str) -> None:
        """Give ``shortcut`` to ``command``; only a difference from the default is stored."""
        if shortcut == command.default:
            self.shortcuts.pop(command.id, None)
        else:
            self.shortcuts[command.id] = shortcut

    def all_shortcuts(self) -> dict[str, str]:
        """The shortcut of every configurable command, by command id."""
        return {command.id: self.shortcut_for(command) for command in CONFIGURABLE_COMMANDS}

    def destination_for(self, category: Category) -> Destination:
        """Where the announcements of ``category`` go."""
        chosen = _destination_named(self.announcements.get(category.id, ""))
        return chosen if chosen is not None and category.accepts(chosen) else category.default

    def set_destination(self, category: Category, destination: Destination) -> None:
        """Send the announcements of ``category`` to ``destination``; the default is not stored."""
        if destination is category.default:
            self.announcements.pop(category.id, None)
        else:
            self.announcements[category.id] = destination.value

    def toggle_activity(self) -> bool:
        """Switch the activity off, or back on to the choice it had; True when it is now on.

        Off is the destination "No announcement". The choice to bring back is kept in the settings
        (``activity_last_choice``), "Messages or beep" when there is none.
        """
        current = self.destination_for(ACTIVITY)
        if current is not Destination.NONE:
            self.activity_last_choice = current.value
            self.set_destination(ACTIVITY, Destination.NONE)
            return False
        last = _destination_named(self.activity_last_choice)
        if last is None or last is Destination.NONE or not ACTIVITY.accepts(last):
            last = ACTIVITY.default
        self.set_destination(ACTIVITY, last)
        return True

    def add_recent_folder(self, folder: Path) -> None:
        """Put ``folder`` first in the recent folders (once), keeping the last ones only."""
        key = folder_key(folder)
        kept = [item for item in self.recent_folders if folder_key(Path(item)) != key]
        self.recent_folders = [str(folder), *kept][:MAX_RECENT_FOLDERS]

    @classmethod
    def load(cls, store: Path | None) -> Settings:
        """Read settings from ``store``; defaults if absent. ``store=None`` stays in memory."""
        settings = cls(store=store)
        if store is None:
            return settings
        result = read_json(store)
        settings.load_warning = result.warning
        if result.data is not None:
            settings._apply_values(result.data)
            settings._apply_shortcuts(result.data)
            settings.announcements = _load_announcements(result.data.get("announcements"))
        return settings

    def _apply_values(self, data: dict[str, object]) -> None:
        """The plain values of the file; a value of the wrong kind is ignored."""
        language = data.get("language")
        if language in SUPPORTED_LANGUAGES:
            self.language = str(language)
        recent = data.get("recent_folders")
        if isinstance(recent, list):
            items = [item for item in recent if isinstance(item, str)]
            self.recent_folders = items[:MAX_RECENT_FOLDERS]
        output = data.get("screen_reader_output")
        if isinstance(output, str) and output_named(output) is not None:
            self.screen_reader_output = output
        limit = data.get("output_limit")
        if isinstance(limit, int) and not isinstance(limit, bool) and limit in OUTPUT_LIMITS:
            self.output_limit = limit
        launch_mode = data.get("launch_mode")
        if launch_mode in LAUNCH_MODES:
            self.launch_mode = str(launch_mode)
        interpreter = data.get("interpreter")
        if interpreter in INTERPRETERS:
            self.interpreter = str(interpreter)
        startup = data.get("startup_profile")
        if isinstance(startup, str):
            self.startup_profile = startup.strip()
        size = data.get("terminal_size")
        if isinstance(size, str) and is_valid_size(size):
            self.terminal_size = size
        self._apply_program_values(data)
        self._apply_window_values(data)

    def _apply_program_values(self, data: dict[str, object]) -> None:
        """The programs the application starts for the user: PowerShell and ``ssh.exe``."""
        powershell = data.get("powershell_path")
        if isinstance(powershell, str):
            self.powershell_path = powershell.strip()
        ssh = data.get("ssh_path")
        if isinstance(ssh, str):
            self.ssh_path = ssh.strip()

    def _apply_window_values(self, data: dict[str, object]) -> None:
        """What the window shows at start: the terminal view and the maximized window."""
        view_only = data.get("terminal_view_only")
        if isinstance(view_only, bool):
            self.terminal_view_only = view_only
        maximize = data.get("maximize_at_start")
        if isinstance(maximize, bool):
            self.maximize_at_start = maximize
        prefix = data.get("stderr_prefix")
        if isinstance(prefix, bool):
            self.stderr_prefix = prefix
        interval = data.get("activity_interval")
        if (
            isinstance(interval, int)
            and not isinstance(interval, bool)
            and interval in ACTIVITY_INTERVALS
        ):
            self.activity_interval = interval
        only_in_output = data.get("activity_only_in_output")
        if isinstance(only_in_output, bool):
            self.activity_only_in_output = only_in_output
        last_choice = data.get("activity_last_choice")
        if isinstance(last_choice, str):
            self.activity_last_choice = last_choice
        formatting = data.get("comfort_formatting")
        if isinstance(formatting, bool):
            self.comfort_formatting = formatting
        titles = data.get("comfort_titles")
        if isinstance(titles, bool):
            self.comfort_titles = titles
        patterns = data.get("prompt_patterns")
        if isinstance(patterns, list):  # an empty list is a choice: no prompt is left out
            self.prompt_patterns = [
                PromptPattern(
                    item["name"], current_pattern(item["pattern"]), item.get("replacement", "")
                )
                for item in patterns
                if isinstance(item, dict)
                and isinstance(item.get("name"), str)
                and isinstance(item.get("pattern"), str)
                and isinstance(item.get("replacement", ""), str)
            ]

    def _apply_shortcuts(self, data: dict[str, object]) -> None:
        """The shortcuts that differ from the default; invalid or conflicting ones are ignored."""
        saved = data.get("shortcuts")
        if not isinstance(saved, dict):
            return
        for command in CONFIGURABLE_COMMANDS:
            value = saved.get(command.id)
            normalized = normalize_shortcut(value) if isinstance(value, str) else None
            if normalized is None:
                continue
            if check_shortcut(command, normalized, self.all_shortcuts()).problem is None:
                self.set_shortcut(command, normalized)

    def save(self) -> None:
        """Write the settings to their store, if any."""
        if self.store is None:
            return
        data: dict[str, object] = {
            "language": self.language,
            "recent_folders": self.recent_folders,
            "shortcuts": self.shortcuts,
            "screen_reader_output": self.screen_reader_output,
            "announcements": self.announcements,
            "output_limit": self.output_limit,
            "launch_mode": self.launch_mode,
            "interpreter": self.interpreter,
            "powershell_path": self.powershell_path,
            "ssh_path": self.ssh_path,
            "startup_profile": self.startup_profile,
            "terminal_size": self.terminal_size,
            "terminal_view_only": self.terminal_view_only,
            "stderr_prefix": self.stderr_prefix,
            "maximize_at_start": self.maximize_at_start,
            "activity_interval": self.activity_interval,
            "activity_only_in_output": self.activity_only_in_output,
            "activity_last_choice": self.activity_last_choice,
            "comfort_formatting": self.comfort_formatting,
            "comfort_titles": self.comfort_titles,
        }
        if self.prompt_patterns is not None:  # absent: the start list, whatever the language
            data["prompt_patterns"] = [
                {"name": item.name, "pattern": item.pattern, "replacement": item.replacement}
                for item in self.prompt_patterns
            ]
        try:
            write_json(self.store, data)
        except JsonStoreError as error:
            raise SettingsError(str(error)) from error
