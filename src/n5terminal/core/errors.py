"""Errors of MiTerm-N5. Every error the project raises derives from :class:`MiTermError`."""


class MiTermError(Exception):
    """Base of the errors raised by MiTerm-N5."""


class SettingsError(MiTermError):
    """The settings file cannot be written."""


class ProfileError(MiTermError):
    """A profile file cannot be written or deleted."""


class ConnectionFileError(MiTermError):
    """A connection file cannot be written or deleted."""


class CatalogError(MiTermError):
    """A message catalog cannot be read or written (develop mode)."""


class LaunchFileError(MiTermError):
    """The launch file given to the application cannot be read."""


class AssociationError(MiTermError):
    """The launch files cannot be associated with the application, or dissociated."""


class ExportError(MiTermError):
    """The output cannot be written to the file the user chose."""


class HelpError(MiTermError):
    """The help files cannot be read or converted."""


class JsonStoreError(MiTermError):
    """A JSON file of the application cannot be written."""


class ScreenReaderOutputError(MiTermError):
    """A message cannot be sent to the screen reader (or its output cannot be set up)."""


class NewSessionError(MiTermError):
    """Another instance of the application cannot be started."""


class TransportError(MiTermError):
    """A transport cannot do what was asked."""


class LaunchError(TransportError):
    """A program cannot be started."""

    def __init__(self, program: str) -> None:
        super().__init__(program)
        self.program = program


class ProgramNotFoundError(LaunchError):
    """The program to start does not exist."""


class AskpassNotFoundError(ProgramNotFoundError):
    """The program ``ssh`` runs to ask the user (and to say it is connected) does not exist."""


class WorkingFolderError(LaunchError):
    """The working folder does not exist or is not a folder."""

    def __init__(self, program: str, folder: str) -> None:
        super().__init__(program)
        self.folder = folder


class InvalidConnectionError(TransportError):
    """The target or the port of a connection cannot be given to ``ssh``."""

    def __init__(self, field: str, problem: str) -> None:
        super().__init__(field, problem)
        self.field = field  # "target" or "port"
        self.problem = problem


class NamedPipeError(TransportError):
    """The named pipe the askpass program talks to cannot be created or used."""

    def __init__(self, action: str, code: int) -> None:
        super().__init__(action, code)
        self.action = action
        self.code = code


class SshConnectionError(TransportError):
    """``ssh`` ended with an error; ``detail`` is the line of its output that says why."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthenticationError(SshConnectionError):
    """The server refused the user (wrong password, no accepted key)."""


class HostKeyError(SshConnectionError):
    """The key of the server is not the one that was trusted, or cannot be verified."""


class ConnectionFailedError(SshConnectionError):
    """The server cannot be reached (timeout, refusal, unknown name, no route)."""


class TransportClosedError(TransportError):
    """Data was sent to a transport that is not connected."""


class InputQueueFullError(TransportError):
    """The program does not read its input and the input queue is full."""


class ProcessTreeError(TransportError):
    """A Windows call on the job holding a program failed."""

    def __init__(self, action: str, code: int) -> None:
        super().__init__(action, code)
        self.action = action
        self.code = code
