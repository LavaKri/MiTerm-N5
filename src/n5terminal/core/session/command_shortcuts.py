"""Which command of the menus each configurable shortcut stands for."""

from n5terminal.core.config.shortcuts import (
    CHOOSE_FOLDER_COMMAND,
    CLEAR_COMMAND,
    COMFORT_NEXT_COMMAND,
    COMFORT_PREVIOUS_COMMAND,
    CONNECT_COMMAND,
    DEFINE_VARIABLES_COMMAND,
    DISCONNECT_COMMAND,
    EMULATOR_END_COMMAND,
    EMULATOR_START_COMMAND,
    EXPORT_COMMAND,
    FIND_COMMAND,
    FIND_NEXT_COMMAND,
    FIND_PREVIOUS_COMMAND,
    FREE_PROFILE_COMMAND,
    HELP_COMMAND,
    HISTORY_COMMAND,
    IDENTIFY_COMMAND,
    LAUNCH_PROGRAM_COMMAND,
    LOCAL_CONNECTION_COMMAND,
    MULTILINE_COMMAND,
    NEW_SESSION_COMMAND,
    READ_LINE_COMMAND,
    RESEND_COMMAND,
    SESSION_INFO_COMMAND,
    SIGNAL_COMMAND,
    STOP_COMMAND,
    TERMINAL_CURSOR_COMMAND,
)
from n5terminal.core.session.session_state import CommandId

#: The command (``CommandId``) of each shortcut, by the id of the configurable command.
COMMAND_OF_SHORTCUT: dict[str, CommandId] = {
    NEW_SESSION_COMMAND.id: CommandId.NEW_SESSION,
    CHOOSE_FOLDER_COMMAND.id: CommandId.CHOOSE_FOLDER,
    EXPORT_COMMAND.id: CommandId.EXPORT,
    STOP_COMMAND.id: CommandId.STOP,
    RESEND_COMMAND.id: CommandId.RESEND,
    MULTILINE_COMMAND.id: CommandId.MULTILINE,
    CLEAR_COMMAND.id: CommandId.CLEAR,
    HISTORY_COMMAND.id: CommandId.HISTORY,
    FIND_COMMAND.id: CommandId.FIND,
    FIND_NEXT_COMMAND.id: CommandId.FIND_NEXT,
    FIND_PREVIOUS_COMMAND.id: CommandId.FIND_PREVIOUS,
    TERMINAL_CURSOR_COMMAND.id: CommandId.GO_TO_CURSOR,
    EMULATOR_START_COMMAND.id: CommandId.GO_TO_EMULATOR_START,
    EMULATOR_END_COMMAND.id: CommandId.GO_TO_EMULATOR_END,
    READ_LINE_COMMAND.id: CommandId.READ_LINE,
    IDENTIFY_COMMAND.id: CommandId.IDENTIFY_ACTIVITIES,
    SIGNAL_COMMAND.id: CommandId.SIGNAL_ACTIVITIES,
    COMFORT_PREVIOUS_COMMAND.id: CommandId.COMFORT_PREVIOUS,
    COMFORT_NEXT_COMMAND.id: CommandId.COMFORT_NEXT,
    HELP_COMMAND.id: CommandId.OPEN_HELP,
    LAUNCH_PROGRAM_COMMAND.id: CommandId.LAUNCH_PROGRAM,
    CONNECT_COMMAND.id: CommandId.CONNECT,
    DISCONNECT_COMMAND.id: CommandId.DISCONNECT,
    FREE_PROFILE_COMMAND.id: CommandId.CHOOSE_FREE_PROFILE,
    LOCAL_CONNECTION_COMMAND.id: CommandId.CHOOSE_LOCAL,
    DEFINE_VARIABLES_COMMAND.id: CommandId.DEFINE_VARIABLES,
    SESSION_INFO_COMMAND.id: CommandId.SESSION_INFO,
}

_BY_COMMAND = {command: shortcut_id for shortcut_id, command in COMMAND_OF_SHORTCUT.items()}


def shortcut_id_of(command: CommandId) -> str | None:
    """The id of the configurable command that gives ``command`` its shortcut, if there is one."""
    return _BY_COMMAND.get(command)
