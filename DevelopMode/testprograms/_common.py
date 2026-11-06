"""What every test program shares: how it starts.

A file whose name starts with an underscore is not a test program: the Develop menu does not list
it. Every program starts with its name as a level 1 Markdown title, then a line that says the mode
it detected: a CLI (the input and output are pipes) or a TUI (they are a console).
"""

import ctypes
import sys

ENABLE_VIRTUAL_TERMINAL = 0x0004
STDOUT_HANDLE = -11


def enable_escape_sequences() -> None:
    """Ask the console to understand the escape sequences (Windows leaves them off by default)."""
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.GetStdHandle(STDOUT_HANDLE)
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL)


def is_terminal() -> bool:
    """Does the program run in a console (TUI) rather than with pipes (CLI)?"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def say(text: str) -> None:
    print(text, flush=True)


def start(name: str) -> bool:
    """Write the title and the mode line; whether the program runs in a console."""
    sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    terminal = is_terminal()
    say(f"# {name}")
    say("Mode : TUI (console)" if terminal else "Mode : CLI (tubes)")
    return terminal
