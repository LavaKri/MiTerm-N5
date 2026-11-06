import subprocess

import pytest

from n5terminal.core.transport.command_line import split_command_line

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("", ()),
        ("   ", ()),
        ("prog a b", ("prog", "a", "b")),
        ("  prog \t a  ", ("prog", "a")),
        ('prog "a b" c', ("prog", "a b", "c")),
        (r'"C:\Program Files\x.exe" -v', (r"C:\Program Files\x.exe", "-v")),
        (r"prog a\\b c\d", ("prog", r"a\\b", r"c\d")),
        (r"prog \"x", ("prog", '"x')),
        (r'prog "a\\" b', ("prog", "a\\", "b")),
        (r"prog a\\\"b", ("prog", r"a\"b")),
        ('prog ""', ("prog", "")),
        ('prog "say ""hi"""', ("prog", 'say "hi"')),
        ('prog "unfinished', ("prog", "unfinished")),
        ('prog a"b c"d', ("prog", "ab cd")),
        ("prog trailing\\", ("prog", "trailing\\")),
    ],
)
def test_split(line: str, expected: tuple[str, ...]) -> None:
    assert split_command_line(line) == expected


@pytest.mark.parametrize(
    "arguments",
    [
        ("prog", "a b", "", 'quote "in" it', "back\\slash", "end\\", 'both\\"'),
        ("C:\\Program Files\\x.exe", "\t", "a\\\\b"),
    ],
)
def test_split_reads_back_what_subprocess_writes(arguments: tuple[str, ...]) -> None:
    assert split_command_line(subprocess.list2cmdline(arguments)) == arguments
