"""What went wrong when ``ssh`` ended with an error, from the end of its output.

See "Errors" in ``specs/architecture/connection.md``. ``ssh`` ends with 255 for every error of its
own, and says why only as text of the terminal, in English (it is not translated). The texts below
are the ones measured with the ``ssh.exe`` of Windows (``specs/architecture/transport.md``).

The output is the stream of a pseudo console, so it holds escape sequences, and a line the console
wrapped may be cut anywhere: the sequences are removed, and the patterns are looked for in the text
with its line breaks removed.
"""

import locale
import re

from n5terminal.core.errors import (
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    SshConnectionError,
)

SSH_ERROR_CODE = 255
TAIL_LENGTH = 4096  # only the end of the output says why ``ssh`` stopped

_SEQUENCE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI: cursor, colors, modes
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC: the title of the window
    r"|\x1b[()][0-9A-Za-z]"  # character set
    r"|\x1b[@-Z\\-_]"  # the other two-character sequences
)
_OCTAL = re.compile(r"(?<!\\)((?:\\[0-3][0-7]{2})+)")  # not after a backslash: that one is a pair
_HOST_KEY_CHANGED = "REMOTE HOST IDENTIFICATION HAS CHANGED"
_HOST_KEY_FAILED = "Host key verification failed"
_AUTHENTICATION = "Permission denied"
_UNREACHABLE = (
    "Connection timed out",
    "Connection refused",
    "banner exchange",
    "Could not resolve hostname",
    "No route to host",
)


def _decode_octal(match: re.Match[str]) -> str:
    """The bytes ``ssh`` wrote as ``\\364`` (what it does with a character outside ASCII), read
    with the code page of Windows, which is the one of the system messages it quotes."""
    raw = bytes(int(digits, 8) for digits in match.group(1).split("\\")[1:])
    return raw.decode(locale.getencoding(), errors="replace")


def _lines(output: str) -> list[str]:
    """The lines of the end of ``output`` without escape sequences, the empty ones dropped.

    The system messages ``ssh`` quotes are in the language of Windows (``Hôte inconnu.``) and
    it writes their accents in octal: they are put back, so that they can be read aloud.
    """
    text = _OCTAL.sub(_decode_octal, _SEQUENCE.sub("", output[-TAIL_LENGTH:]))
    return [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]


def _line_with(lines: list[str], pattern: str) -> str:
    """The last line that holds ``pattern``; else the last line."""
    return next((line for line in reversed(lines) if pattern in line), lines[-1] if lines else "")


def classify_ssh_end(
    output: str, exit_code: int | None, user_cancelled: bool = False
) -> SshConnectionError | None:
    """The error ``ssh`` ended with, ``None`` when it ended without one of its own.

    ``output`` is what the terminal received (only its end counts) and ``exit_code`` the code
    ``ssh`` ended with: 255 for its errors, else the code of the remote command. ``user_cancelled``
    is set when the user cancelled a dialog (the host key, the password): ``ssh`` then ends with
    255 and a refusal, which is not an error to announce.

    This is for an ``ssh`` that ended **before the connection was made**: once the shell of the
    server is open, its own output (a ``Permission denied`` of a command) must not be taken for
    the reason ``ssh`` stopped.
    """
    if exit_code != SSH_ERROR_CODE or user_cancelled:
        return None
    lines = _lines(output)
    flat = "".join(lines)
    if _HOST_KEY_CHANGED in flat:
        return HostKeyError(_HOST_KEY_CHANGED)
    if _HOST_KEY_FAILED in flat:
        return HostKeyError(_line_with(lines, _HOST_KEY_FAILED))
    if _AUTHENTICATION in flat:
        return AuthenticationError(_line_with(lines, _AUTHENTICATION))
    for pattern in _UNREACHABLE:
        if pattern in flat:
            return ConnectionFailedError(_line_with(lines, pattern))
    return ConnectionFailedError(lines[-1] if lines else "")
