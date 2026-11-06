"""A fake ``ssh`` for the tests of ``SshTransport``: it behaves as the ``ssh.exe`` of Windows was
measured to (``specs/architecture/transport.md``), without a network or a server.

Run as ``python program_ssh.py <the options of ssh> -- user@<flags>``: the flags are the words of
the host name separated by dots, and say what happens.

- ``hostkey``: asks whether to trust the host key (through ``SSH_ASKPASS``, with the text of the
  measured question); anything but ``yes``, or a program that fails, ends with
  ``Host key verification failed.`` and 255.
- ``password``: asks for the password up to 3 times (the right one is ``secret``) and ends with
  ``Permission denied (publickey,password).`` and 255; ``wrongpass``: no password is the right one.
  A program that fails (the user cancelled) counts as a wrong answer, and ``ssh`` asks again.
- ``refused``, ``timeout``, ``changedkey``: the errors, with the measured texts, and 255.
- Else the connection is made: ``LocalCommand`` is run (not with ``nosignal``), the banner is
  written and a shell answers: ``exit`` or ``exit N`` end it, ``bye`` ends it at once with 0, and
  ``drop`` ends it at once with 255, as a network cut does.
"""

import os
import subprocess
import sys

RIGHT_PASSWORD = "p4ssw0rd-t3st"
ATTEMPTS = 3
HOST_KEY_QUESTION = (
    "The authenticity of host '{host} (10.0.0.1)' can't be established.\n"
    "ED25519 key fingerprint is SHA256:abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG.\n"
    "This key is not known by any other names.\n"
    "Are you sure you want to continue connecting (yes/no/[fingerprint])? "
)
CHANGED_KEY = (
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
    "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\n"
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
    "IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!"
)


def say(text: str) -> None:
    print(text, flush=True)


def fail(text: str) -> None:
    say(text)
    sys.exit(255)


def ask(question: str) -> str | None:
    """What ``SSH_ASKPASS`` answers, as ``ssh`` reads it; ``None`` when the program fails."""
    done = subprocess.run(
        [os.environ["SSH_ASKPASS"], question],
        capture_output=True,
        check=False,
        env=os.environ,
    )
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8").rstrip("\r\n")


def option(arguments: list[str], name: str) -> str | None:
    prefix = f"{name}="
    values = [a[len(prefix) :] for a in arguments if a.startswith(prefix)]
    return values[-1] if values else None


def authenticate(user: str, host: str, flags: set[str]) -> None:
    if "hostkey" in flags and ask(HOST_KEY_QUESTION.format(host=host)) != "yes":
        fail("Host key verification failed.")
    if "hostkey" in flags:
        say(f"Warning: Permanently added '{host}' (ED25519) to the list of known hosts.")
    if not flags & {"password", "wrongpass"}:
        return
    for attempt in range(ATTEMPTS):
        if ask(f"{user}@{host}'s password: ") == RIGHT_PASSWORD and "wrongpass" not in flags:
            return
        if attempt < ATTEMPTS - 1:
            say("Permission denied, please try again.")
    fail(f"{user}@{host}: Permission denied (publickey,password).")


def shell(flags: set[str]) -> None:
    say("Welcome to the fake server.")
    if "bye" in flags:
        sys.exit(0)
    while True:
        try:
            line = input("fake$ ")
        except EOFError:
            sys.exit(0)
        words = line.split()
        if words[:1] == ["exit"]:
            say("logout")
            sys.exit(int(words[1]) if len(words) > 1 else 0)
        say(f"you said: {line}")


def main() -> None:
    arguments = sys.argv[1:]
    user, _, host = arguments[-1].rpartition("@")
    flags = set(host.split("."))
    if "refused" in flags:
        fail(f"ssh: connect to host {host} port 22: Connection refused")
    if "timeout" in flags:
        fail(f"ssh: connect to host {host} port 22: Connection timed out")
    if "changedkey" in flags:
        say(CHANGED_KEY)
        fail("Host key verification failed.")
    authenticate(user, host, flags)
    local_command = option(arguments, "LocalCommand")
    if local_command and "nosignal" not in flags:
        subprocess.run(local_command, shell=True, check=False, env=os.environ)  # as ssh does
    if "drop" in flags:
        fail("client_loop: send disconnect: Connection reset")
    shell(flags)


if __name__ == "__main__":
    main()
