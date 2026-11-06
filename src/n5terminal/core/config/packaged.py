"""Whether the application runs as the packaged executable or from the sources."""

import sys


def is_packaged() -> bool:
    """Is this the packaged application? (PyInstaller sets ``sys.frozen``; sources do not.)"""
    return bool(getattr(sys, "frozen", False))
