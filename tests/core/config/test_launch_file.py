from pathlib import Path

import pytest

from n5terminal.core.config.launch_file import read_launch_file
from n5terminal.core.errors import LaunchFileError
from n5terminal.i18n import install

pytestmark = pytest.mark.unit


def write(tmp_path: Path, text: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / "project.n5term"
    path.write_text(text, encoding=encoding)
    return path


def test_the_profile_the_variables_and_the_folder_are_read(tmp_path: Path) -> None:
    (tmp_path / "work").mkdir()
    path = write(
        tmp_path,
        "profile = git\nWorkingPath = work\nname = dev\nsource = C:\\a b\\c.txt\n",
    )
    launch = read_launch_file(path)
    assert launch.profile == "git"
    assert launch.variables == {"name": "dev", "source": "C:\\a b\\c.txt"}
    assert launch.folder == tmp_path.resolve() / "work"
    assert launch.warnings == []


def test_the_keys_ignore_case_and_braces(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "Profile=git\n{NAME} = dev\n{Value1}=1\n"))
    assert launch.profile == "git"
    assert launch.variables == {"name": "dev", "value1": "1"}


def test_the_values_may_hold_a_percent_sign_a_colon_and_an_equal_sign(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "profile = p\nname = 100%=C:\\x\n"))
    assert launch.variables == {"name": "100%=C:\\x"}


def test_comments_blank_lines_and_unknown_keys_are_ignored(tmp_path: Path) -> None:
    text = "; a comment\n# another\n\nprofile = git\ncolour = blue\n"
    launch = read_launch_file(write(tmp_path, text))
    assert (launch.profile, launch.variables) == ("git", {})


def test_a_section_header_is_accepted(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "[session]\nprofile = git\nname = dev\n"))
    assert (launch.profile, launch.variables) == ("git", {"name": "dev"})


def test_a_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "profile = été\n", encoding="utf-8-sig"))
    assert launch.profile == "été"


def test_empty_values_count_as_absent(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "profile =\nname =\n"))
    assert (launch.profile, launch.variables) == (None, {})
    assert launch.warnings == []


def test_variables_without_a_profile_are_ignored_with_a_warning(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "name = dev\n"))
    assert launch.variables == {}
    assert len(launch.warnings) == 1


def test_the_warnings_are_in_the_language_of_the_application(tmp_path: Path) -> None:
    install("fr")
    try:
        launch = read_launch_file(write(tmp_path, "name = dev\nWorkingPath = nowhere\n"))
    finally:
        install("en")
    assert launch.warnings[0] == (
        "project.n5term : les variables sont ignorées parce que le fichier n'a pas de profil."
    )
    assert launch.warnings[1].startswith("project.n5term : le dossier de travail ")


def test_only_the_english_key_names_the_profile(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "profil = git\nname = dev\n"))
    assert launch.profile is None
    assert launch.variables == {}
    assert len(launch.warnings) == 1


def test_without_a_working_path_the_folder_of_the_file_is_used(tmp_path: Path) -> None:
    assert read_launch_file(write(tmp_path, "profile = git\n")).folder == tmp_path.resolve()


def test_an_absolute_working_path_is_used_as_it_is(tmp_path: Path) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    launch = read_launch_file(write(tmp_path, f"WorkingPath = {other}\n"))
    assert launch.folder == other


def test_a_working_path_that_does_not_exist_gives_a_warning_and_no_folder(tmp_path: Path) -> None:
    launch = read_launch_file(write(tmp_path, "WorkingPath = nowhere\n"))
    assert launch.folder is None
    assert len(launch.warnings) == 1


def test_a_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(LaunchFileError):
        read_launch_file(tmp_path / "missing.n5term")


def test_a_file_that_is_not_text_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.n5term"
    path.write_bytes(b"profile = \xff\xfe\x00")
    with pytest.raises(LaunchFileError):
        read_launch_file(path)


def test_a_line_that_is_not_a_key_value_raises(tmp_path: Path) -> None:
    with pytest.raises(LaunchFileError):
        read_launch_file(write(tmp_path, "this is not a setting\n"))


def test_the_old_email_key_is_the_comment(tmp_path: Path) -> None:
    path = write(tmp_path, "profile = ssh-keygen\n{Email} = me@work\n")
    assert read_launch_file(path).variables == {"comment": "me@work"}
