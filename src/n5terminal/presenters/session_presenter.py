"""The presenter of a session: one window, one program at a time.

It turns the events of a transport and the actions of the user into what the window shows (see
``specs/architecture/session.md``). The transport threads feed the screen model and publish to the
exchange (``ScreenPump``); the UI calls :meth:`SessionPresenter.tick` every 50 to 100 ms and the
presenter gives the window what accumulated. The events of the transport that change the state
(state, exit) are handed to the UI thread by ``post`` (``wx.CallAfter`` in the application).
"""

import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.keys import SentKey
from n5terminal.core.config.profiles import CommandUse, Profile, full_command, program_name
from n5terminal.core.errors import InputQueueFullError, TransportClosedError, TransportError
from n5terminal.core.screen.line_analysis import LAUNCH_PREFIX, SEND_PREFIX
from n5terminal.core.screen.screen_model import ScreenUpdate
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.command_history import CommandHistory
from n5terminal.core.session.session_state import (
    CommandId,
    Interpreter,
    LaunchMode,
    Mode,
    Phase,
    SessionState,
    refusal,
)
from n5terminal.core.session.shell import change_folder_command
from n5terminal.core.transport.transport import TransportState
from n5terminal.i18n import _
from n5terminal.presenters.activity_signal import ActivitySignal
from n5terminal.presenters.command_label import command_label, normalize_block
from n5terminal.presenters.connection_part import ConnectionPart
from n5terminal.presenters.connection_session import ConnectionChoice, start_failure
from n5terminal.presenters.output_flow import OutputFlow
from n5terminal.presenters.profile_values import CommandEntry, ProfileValues
from n5terminal.presenters.prompt_watch import PromptWatch
from n5terminal.presenters.session_choices import SessionChoices
from n5terminal.presenters.session_display import SessionDisplay
from n5terminal.presenters.session_info import (
    connection_title,
    end_text,
    input_label,
    launch_folder_line,
    run_text,
    window_title,
)
from n5terminal.presenters.session_run import (
    CHILD_GRACE,
    LaunchRequest,
    Run,
    RunListener,
    SessionServices,
    build_run,
    launch_failure,
)
from n5terminal.presenters.session_view import SessionView

logger = logging.getLogger(__name__)


class SessionPresenter(ConnectionPart):
    """Drives the window of one session. Only the data come in on a thread other than the UI's."""

    def __init__(self, view: SessionView, services: SessionServices, working_folder: Path) -> None:
        self._view = view
        self._launcher = services.launcher
        self._settings = services.settings
        self._announcements = services.announcements
        self.post = services.post
        self._clock = services.clock
        self._folder = working_folder
        self._flow = OutputFlow(view, services.settings, self.say)
        self._display = SessionDisplay(view)
        self.profile_values = ProfileValues()
        self._history = CommandHistory()
        self._prompt = PromptWatch()
        self._activity = ActivitySignal(view, self._settings, self._announcements, self.say)
        self._state = SessionState(
            launch_mode=LaunchMode(self._settings.launch_mode),
            interpreter=Interpreter(self._settings.interpreter),
        )
        self._run: Run | None = None
        self._last_end_text = ""
        self._choices = SessionChoices(
            self._settings, self.profile_values, lambda: self._state, self._set_state, self.say
        )
        self._connection = ConnectionChoice(lambda: self._state, self._set_state, self.say)
        self._refresh()

    # What the window can read -------------------------------------------------------------------

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def working_folder(self) -> Path:
        return self._folder

    @property
    def running_program(self) -> str | None:
        """The program of the session (``None`` when there is none)."""
        return self._run.program if self._run is not None else None

    @property
    def last_end_text(self) -> str:
        """How the last program ended, as the status bar said it (empty: none ended yet)."""
        return self._last_end_text

    @property
    def terminal_size(self) -> TerminalSize:
        return self._choices.size.size

    def history_items(self) -> tuple[str, ...]:
        """All the commands typed so far, of any use, the most recent last.

        The list of Ctrl+Space (``command_list``) shows only those of the use that fits the moment.
        """
        return self._history.items()

    # The command field --------------------------------------------------------------------------

    def submit(self, text: str, title: str | None = None, hidden: bool = False) -> None:
        """Enter or the Send button: launch a command, or send the text to the program.

        With the program of a profile, the text of the field is its arguments. ``text`` may be a
        block of several lines (the multi-line input): it is one entry of the history.

        ``title`` is what the output shows for a launched command instead of ``text`` (a test
        program is shown by its file name, not by the whole command line). ``hidden`` is set when
        the user ticked "Mask the message": the text is a secret for the running program.
        """
        text = normalize_block(text)
        phase = self._state.phase
        if phase is Phase.IDLE and self._state.on_server:
            self._connect(text)
        elif phase is Phase.IDLE:
            self._launch_from_field(text, title)
        elif phase is Phase.RUNNING:
            self._send(text, hidden)
        else:
            self.say(Announce.SEND_REFUSED_CHILD_ACTIVE)

    def _launch_from_field(self, text: str, title: str | None) -> None:
        """Launch what the field holds; with the program of a profile, it holds its arguments.

        The output then shows the name of the program (``# Git``), as for F5.
        """
        if self.profile_values.takes_arguments and title is None:
            program = self.profile_values.program()
            title = program_name(program)
            text = full_command(program, text).strip()
        self._launch(text, title)

    def _launch(self, line: str, title: str | None = None) -> None:
        """Launch ``line``. The steps go in this order, and the order matters.

        The command is echoed before the session follows the run, and before the transport starts,
        so that the first output of the program cannot come before it.
        """
        request = self._launch_request(line)
        run = build_run(self._launcher, self._flow.exchange, request)
        if run is None:
            return  # an empty line is ignored when no program runs
        self._remember_command(run, line)
        echoed = self._echo_command(run, title or line)
        self._follow(run, line)
        self._start(run, request, echoed)

    def _launch_request(self, line: str) -> LaunchRequest:
        return LaunchRequest(
            line,
            self._state,
            self._folder,
            self._choices.size.size,
            self._choices.mark_stderr,
            self._choices.prompt_prefix,
            self._settings.powershell_path,
        )

    def _remember_command(self, run: Run, line: str) -> None:
        """Keep what was typed: for a shell, the line it is given once connected (if any)."""
        typed = run.pending_line if run.types_lines else line
        if typed is not None:
            self._history.add(typed, CommandUse.LAUNCH)

    def _echo_command(self, run: Run, shown: str) -> int:
        """Write the command in the output (pipes only); the lines it takes, for the caret."""
        if run.mode is not Mode.PIPES:
            return 0
        lines = self._echo_lines(shown, LAUNCH_PREFIX, launch_folder_line(self._folder, _))
        self._show_output()  # now, so that the program's first output cannot come before
        return lines

    def _follow(self, run: Run, line: str) -> None:
        """The session follows ``run`` from now on: its state says that a program runs."""
        self._run = run
        logger.info("Launching %s (%s)", run.program, run.mode.value)
        logger.debug("Command line: %s", line)  # the arguments may hold secrets: DEBUG only
        self._prompt.reset()
        self._activity.reset(self._clock())
        self._set_state(
            replace(
                self._state,
                phase=Phase.RUNNING,
                mode=run.mode,
                shell_at_prompt=False,
            )
        )
        self._view.clear_input()

    def _start(self, run: Run, request: LaunchRequest | None, echoed: int) -> None:
        """Start the transport; a failure is announced and leaves the session ready again.

        ``request`` is the launch of a program; a connection has none.
        """
        try:
            run.transport.start(RunListener(self, run))
        except TransportError as error:  # whatever the failure, the session must not stay stuck
            if request is None:
                announce, values = start_failure(error)
            else:
                announce, values = launch_failure(error, request, run.program, run.is_shell)
            self._launch_failed(announce, **values)
        else:
            if run.connection is None:  # the first state of a connection is its announcement
                self.say(Announce.PROGRAM_STARTED, program=run.program)
            self._view.focus_output_on_command(echoed)

    def _launch_failed(self, announce: Announce, **values: object) -> None:
        logger.warning("Launch failed: %s", announce.name)
        self._run = None
        self._set_state(replace(self._state, phase=Phase.IDLE))
        self.say(announce, **values)

    def _send(self, text: str, hidden: bool = False) -> None:
        run = self._run
        if run is None:
            return
        # Whatever the program, what is typed is kept so that it can be sent again, except a hidden
        # message: that is a secret, not kept and not written in the output. The history lives in
        # memory only and is never saved (``specs/robustness.md``).
        if not hidden:
            self._history.add(text, CommandUse.PROGRAM)
            self._refresh()  # the line may be the first one: Resend is available now
        self._activity.sent(self._clock())
        sent = self._write(run, text)
        if sent and run.mode is Mode.PIPES:
            self._echo_lines(_("(hidden message)") if hidden else text, SEND_PREFIX)
        self._view.clear_input()
        if sent:
            self._view.focus_output()

    def send_key(self, key: SentKey) -> bool:
        """Send a key to the program, as a terminal keyboard would; whether it was sent.

        Only to a program served through a pseudo console. The arrows, Home and End take the form
        the program asked for. The key is announced once; a refusal is announced instead.
        """
        reason = refusal(CommandId.SEND_KEY, self._state)
        if reason is not None:
            self.say(reason)
            return False
        run = self._run
        if run is None:
            return False
        self._activity.sent(self._clock())
        if not self._transmit(run, key.bytes_for(run.pump.application_cursor_keys)):
            return False
        self.say(Announce.KEY_SENT, key=_(key.name))
        self._view.focus_output()
        return True

    def _echo_lines(self, text: str, prefix: str, *details: str) -> int:
        """Write ``text`` in the output: the prefix on its first line, the others under it."""
        first, *others = text.split("\n")
        return self._flow.echo(first, prefix, *others, *details)

    def _encode(self, run: Run, text: str) -> bytes:
        """The bytes of a line, or of a block: its lines joined by the line end of the program.

        A block for PowerShell ends with an empty line: without PSReadLine (which PowerShell turns
        off when a screen reader runs) it waits for one to run what it was given.
        """
        end = run.line_end
        lines = text.split("\n")
        data = end.join(line.encode("utf-8") for line in lines) + end
        if len(lines) > 1 and run.is_shell and self._state.interpreter is Interpreter.POWERSHELL:
            data += end
        return data

    def _write(self, run: Run, text: str) -> bool:
        """Send a line of text, or a block, to the program; whether it went (a shell is watched)."""
        sent = self._transmit(run, self._encode(run, text))
        if sent and run.is_shell:
            self._prompt.typed()
            self._watch_prompt()
        return sent

    def _transmit(self, run: Run, data: bytes) -> bool:
        """Write ``data`` to the transport; whether it went. A refusal is announced, once, here."""
        try:
            run.transport.write(data)
        except TransportClosedError:
            self.say(Announce.SEND_REFUSED_CHILD_ACTIVE)
        except InputQueueFullError:
            self.say(Announce.INPUT_NOT_READ)
        else:
            return True
        return False

    # Commands -----------------------------------------------------------------------------------

    def run_command(self, command: CommandId) -> bool:
        """Ask for a command: refused with an announcement when the state does not allow it.

        Returns whether it is allowed. The commands the presenter does itself are done here; the
        others (dialogs, menus of choices) are the window's, which calls the matching method.
        """
        reason = refusal(command, self._state)
        if reason is not None:
            self.say(reason)
            return False
        if command is CommandId.STOP:
            self.stop()
        elif command is CommandId.CLEAR:
            self.clear_output()
        elif command is CommandId.RESEND:
            self._resend_last()
        elif command is CommandId.LAUNCH_PROGRAM:
            self.launch_profile_program()
        elif command is CommandId.CONNECT:
            self.submit("")
        elif command is CommandId.DISCONNECT:
            self.stop()
        return True

    def _resend_last(self) -> None:
        """Do what Ctrl+Space then Enter on the line selected at its opening does."""
        history = self._view_history()
        if history:
            self.submit(history[-1].text)

    def launch_profile_program(self) -> None:
        """Launch the program of the chosen profile, as if its path were typed in the field.

        The output shows its name only (``# Git``); a shell that stays open gets it typed. On a
        server only the file name is written (a path of Windows does not exist there), and a closed
        connection opens first.
        """
        program = self.profile_values.program()
        name = program_name(program)
        line = name if self._state.on_server else full_command(program, "").strip()
        self.submit(line, name)

    def stop(self) -> None:
        """Stop the program and everything it started."""
        run = self._run
        if run is not None:
            run.transport.close()
            if run.connection is None:  # a connection says how it ended by itself
                self.say(Announce.PROGRAM_STOPPED)

    def clear_output(self) -> None:
        """Empty the output area; the program goes on."""
        self._flow.clear()
        self._set_state(replace(self._state, has_output=False))

    def set_working_folder(self, folder: Path) -> bool:
        """Choose the working folder; a shell waiting at its prompt is sent there at once."""
        reason = refusal(CommandId.CHOOSE_FOLDER, self._state)
        if reason is not None:
            self.say(reason)
            return False
        if not folder.is_dir():
            self.say(Announce.FOLDER_NOT_FOUND, folder=folder)
            return False
        self._folder = folder
        self._refresh()  # the title of the window names the folder
        self._settings.add_recent_folder(folder)
        run = self._run
        if run is not None and self._state.shell_ready:
            line = change_folder_command(self._state.interpreter, folder)
            if line is not None:
                self._write(run, line)
        self.say(Announce.FOLDER_CHANGED, folder=folder)
        return True

    def set_interpreter(self, interpreter: Interpreter) -> bool:
        """Choose the shell the commands go through; only with no program."""
        return self._choices.set_interpreter(interpreter)

    @property
    def powershell_path(self) -> str:
        """The PowerShell the interpreter starts (empty: Windows PowerShell)."""
        return self._choices.powershell_path

    def set_powershell_path(self, path: str) -> bool:
        """Choose the PowerShell for the next shell (a global setting); only with no program."""
        return self._choices.set_powershell_path(path)

    def set_launch_mode(self, launch_mode: LaunchMode) -> bool:
        """Choose CLI or TUI for the next program; only with no program and no shell."""
        return self._choices.set_launch_mode(launch_mode)

    def select_profile(self, profile: Profile | None) -> bool:
        """Choose a profile, or ``None`` for the free profile; only with no program."""
        return self._choices.select_profile(profile)

    def session_values(self, name: str = "") -> Profile:
        """A profile named ``name`` holding the mode, interpreter and size now in use."""
        return self._choices.session_values(name)

    def command_list(self) -> tuple[list[CommandEntry], int]:
        """The list of Ctrl+Space and the line selected when it opens.

        The commands typed so far, the oldest first, then those of the profile. With no program
        they are the launch commands; with a program that stays open, the program commands. The
        last command typed is selected, so Up reads the older ones and Down reaches the commands of
        the profile just below it; with no history the first line is selected.
        """
        running = self._state.phase is Phase.RUNNING
        history = self._view_history()
        return [*history, *self.profile_values.entries(running)], max(len(history) - 1, 0)

    def _view_history(self) -> list[CommandEntry]:
        """The typed lines the list of Ctrl+Space shows now, the most recent last."""
        running = self._state.phase is Phase.RUNNING
        typed = self._history.items_of(CommandUse.PROGRAM if running else CommandUse.LAUNCH)
        return self._history_entries(typed, running)

    def _history_entries(self, typed: Sequence[str], running: bool) -> list[CommandEntry]:
        """The lines typed, as the list shows them.

        With the program of a profile and nothing running, the field takes arguments: the lines of
        that program are shown and written as their arguments, those of other programs are left
        out (the free profile lists them).
        """
        if running or not self.profile_values.takes_arguments:
            return [CommandEntry(command_label(command, _), command) for command in typed]
        name = program_name(self.profile_values.program())
        entries: list[CommandEntry] = []
        for command in typed:
            arguments = self.profile_values.arguments_of(command)
            if arguments is not None:
                label = command_label(f"{name} {arguments}".strip(), _)
                entries.append(CommandEntry(label, arguments))
        return entries

    def set_terminal_size(self, size: TerminalSize | None) -> None:
        """Choose a standard size, or ``None`` for the automatic size (which only grows)."""
        run = self._run
        running = run if run is not None and run.mode.is_terminal else None
        current = self._choices.size
        current.choose(size, running.size if running is not None else current.size)
        if size is not None and running is not None:
            self._resize(running, size)

    def _watch_prompt(self) -> None:
        """A shell that stays open: does it wait at its prompt now? (``shell_prompt.py``)"""
        run = self._run
        if run is None or not run.is_shell or self._state.phase is not Phase.RUNNING:
            return
        waiting = self._prompt.at_prompt(self._state.interpreter, run.transport, run.prompt_prefix)
        if waiting != self._state.shell_at_prompt:
            self._set_state(replace(self._state, shell_at_prompt=waiting))

    # Time ---------------------------------------------------------------------------------------

    def tick(self) -> None:
        """Give the window what accumulated. The window calls it every 50 to 100 ms."""
        self._show_output()
        self._watch_prompt()
        self._check_child()
        self._activity.check(self._state, self._clock())

    def _show_output(self) -> None:
        update = self._flow.show()
        if update is None:
            return
        if self._run is not None and self._run.is_shell:
            self._prompt.screen(update)
        if not self._state.has_output and (update.fixed or any(row.text for row in update.rows)):
            self._set_state(replace(self._state, has_output=True))
        self._grow_if_needed(update)
        if update.fixed or update.rows:
            self._activity.note(self._clock())

    def _grow_if_needed(self, update: ScreenUpdate) -> None:
        run = self._run
        if run is None or not run.mode.is_terminal or not update.overflows:
            return
        grown = self._choices.size.observe(update.overflows)
        if grown is not None:
            self._resize(run, grown)
            self.say(Announce.SIZE_CHANGED, columns=grown.columns, rows=grown.rows)

    def _resize(self, run: Run, size: TerminalSize) -> None:
        """The pseudo console and the screen model change size together."""
        run.size = size
        run.pump.resize(size.columns, size.rows)
        run.transport.resize(size.columns, size.rows)

    def _check_child(self) -> None:
        run = self._run
        if run is None or run.child_since is None or run.child_announced:
            return
        if self._clock() - run.child_since >= CHILD_GRACE:
            run.child_announced = True
            self.say(Announce.CHILD_ACTIVE)
            self._refresh()

    # Events of the transport (on the UI thread, through ``post``) -------------------------------

    def handle_state(self, run: Run, state: TransportState) -> None:
        if run is not self._run:
            return
        logger.info("Transport state of %s: %s", run.program, state.value)
        if run.connection is not None:
            self._handle_connection_state(run, state)
            return
        if state is TransportState.CONNECTED and run.pending_line is not None:
            line, run.pending_line = run.pending_line, None
            self._write(run, line)
        elif state in (TransportState.CLOSED, TransportState.FAILED):
            self._closed(run)

    def handle_exit(self, run: Run, exit_code: int | None) -> None:
        if run is not self._run:
            return
        run.exit_code, run.ended = exit_code, True
        logger.info("%s ended with the code %s", run.program, exit_code)
        if run.connection is not None:  # said when the connection closes, with its cause
            return
        if exit_code is None:
            self.say(Announce.PROGRAM_ENDED_UNKNOWN, program=run.program)
        else:
            self.say(Announce.PROGRAM_ENDED, program=run.program, code=exit_code)
        run.child_since = self._clock()
        self._set_state(replace(self._state, phase=Phase.CHILD_ACTIVE, shell_at_prompt=False))

    def _closed(self, run: Run) -> None:
        """No more output can arrive: the session is ready for another command."""
        run.pump.finish()
        if not run.ended:
            self.say(Announce.PROGRAM_ENDED_UNKNOWN, program=run.program)
        self._last_end_text = end_text(run.exit_code, _)
        self._run = None
        self._set_state(replace(self._state, phase=Phase.IDLE, shell_at_prompt=False))

    # The state and what the window shows of it --------------------------------------------------

    def _set_state(self, state: SessionState) -> None:
        """Take ``state``, made with ``replace(self._state, ...)`` (mypy checks its fields)."""
        self._state = state
        self._refresh()

    def _refresh(self) -> None:
        has_history = bool(self._view_history())
        if has_history != self._state.has_history:
            self._state = replace(self._state, has_history=has_history)
        run = self._run
        name = self._state.connection
        if name is None:
            title = window_title(self._state.profile, self._folder, _)
        else:
            title = connection_title(
                self._state.profile, name, run is not None and run.connected, _
            )
        if run is not None and run.connection is not None:
            text = run.status
        else:
            text = run_text(
                run.program if run is not None else None,
                run is not None and run.child_announced,
                self._last_end_text,
                _,
            )
        profile = self._state.profile if self.profile_values.takes_arguments else None
        label = input_label(self._state, profile or "", _)
        self._display.show(self._state, text, title, label)

    def say(self, announce: Announce, **values: object) -> None:
        self._announcements.notify(announce, **values)
