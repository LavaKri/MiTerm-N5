from pathlib import Path

import pytest

from n5terminal.core.config.file_association import PROG_ID, FileAssociation, open_command
from n5terminal.core.errors import AssociationError

pytestmark = pytest.mark.unit

COMMAND = '"C:\\N5\\n5terminal.exe" "%1"'
COMMAND_KEY = f"{PROG_ID}\\shell\\open\\command"


class FakeRegistry:
    """The registry in a dictionary; deleting a key deletes the keys under it."""

    def __init__(self) -> None:
        self.keys: dict[str, str] = {}
        self.notified = 0
        self.fail = False

    def read(self, key: str) -> str | None:
        return self.keys.get(key)

    def write(self, key: str, value: str) -> None:
        if self.fail:
            raise PermissionError("denied")
        self.keys[key] = value

    def delete(self, key: str) -> None:
        if self.fail:
            raise PermissionError("denied")
        under = key + "\\"
        self.keys = {k: v for k, v in self.keys.items() if k != key and not k.startswith(under)}

    def changed(self) -> None:
        self.notified += 1


def test_nothing_is_associated_at_first() -> None:
    assert not FileAssociation(FakeRegistry(), COMMAND).is_associated()


def test_associate_writes_the_extension_the_type_and_the_command() -> None:
    registry = FakeRegistry()
    association = FileAssociation(registry, COMMAND)
    association.associate()
    assert registry.keys[".n5term"] == PROG_ID
    assert registry.keys[COMMAND_KEY] == COMMAND
    assert association.is_associated()
    assert registry.notified == 1


def test_dissociate_removes_all_that_was_written() -> None:
    registry = FakeRegistry()
    association = FileAssociation(registry, COMMAND)
    association.associate()
    association.dissociate()
    assert registry.keys == {}
    assert not association.is_associated()
    assert registry.notified == 2


def test_another_program_extension_entry_is_left_alone() -> None:
    registry = FakeRegistry()
    registry.keys[".n5term"] = "Other.Program"
    FileAssociation(registry, COMMAND).dissociate()
    assert registry.keys == {".n5term": "Other.Program"}


def test_a_moved_program_is_not_associated_any_more() -> None:
    registry = FakeRegistry()
    FileAssociation(registry, COMMAND).associate()
    assert not FileAssociation(registry, '"D:\\other\\n5terminal.exe" "%1"').is_associated()


@pytest.mark.parametrize("action", ["associate", "dissociate"])
def test_a_refusal_of_the_registry_is_an_association_error(action: str) -> None:
    registry = FakeRegistry()
    registry.fail = True
    association = FileAssociation(registry, COMMAND)
    with pytest.raises(AssociationError):
        getattr(association, action)()


def test_the_command_of_a_packaged_program_is_the_executable_and_the_file() -> None:
    assert open_command("C:\\N5\\n5terminal.exe", frozen=True) == COMMAND


def test_the_command_of_a_source_run_is_the_module_and_the_file(tmp_path: Path) -> None:
    (tmp_path / "pythonw.exe").write_text("", encoding="utf-8")
    command = open_command(str(tmp_path / "python.exe"), frozen=False)
    assert command == f'"{tmp_path / "pythonw.exe"}" -m n5terminal "%1"'
