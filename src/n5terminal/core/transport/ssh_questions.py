"""Which dialog a question of ``ssh`` needs.

See "Which dialog for which question" in ``specs/architecture/connection.md``. The question reaches
the askpass program as the text ``ssh`` would have written in the terminal, in English (``ssh`` is
not translated), so it is recognised by its words.
"""

import enum

_HOST_KEY_ENDING = "(yes/no/[fingerprint])?"
_HOST_KEY_AGAIN = "Please type 'yes', 'no' or the fingerprint"


class QuestionKind(enum.Enum):
    """What the user is asked for."""

    HOST_KEY = "host_key"  # trust this server? a yes or no, with the fingerprint to read
    SECRET = "secret"  # a password, a passphrase, a code: typed hidden


def question_kind(text: str) -> QuestionKind:
    """The kind of ``text``; any question that is not about the host key is a secret.

    A second factor (``Verification code:``) is a secret too: typed hidden, which does no harm for
    a code and is what a one-time password needs.
    """
    stripped = text.strip()
    if stripped.endswith(_HOST_KEY_ENDING) or stripped.startswith(_HOST_KEY_AGAIN):
        return QuestionKind.HOST_KEY
    return QuestionKind.SECRET
