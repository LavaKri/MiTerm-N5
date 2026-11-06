import json
from pathlib import Path

import pytest

from n5terminal.core.config.connections import (
    MAX_NAME_LENGTH,
    Connection,
    ConnectionStore,
    TargetProblem,
    connection_name_problem,
    is_valid_port,
    target_problem,
)
from n5terminal.core.config.profiles import NameProblem
from n5terminal.core.errors import ConnectionFileError

pytestmark = pytest.mark.unit


def _full() -> Connection:
    return Connection("prod", target="admin@example.org", port=2222)


# Names -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "problem"),
    [
        ("prod", None),
        ("a" * MAX_NAME_LENGTH, None),
        ("a" * (MAX_NAME_LENGTH + 1), NameProblem.TOO_LONG),
        ("", NameProblem.EMPTY),
        ("a/b", NameProblem.FORBIDDEN_CHARACTER),
        ("CON", NameProblem.FORBIDDEN_CHARACTER),
    ],
)
def test_connection_name_problem(name: str, problem: NameProblem | None) -> None:
    assert connection_name_problem(name, taken=[]) is problem


def test_a_connection_name_may_be_longer_than_a_profile_name() -> None:
    assert connection_name_problem("serveur-prod-1", taken=[]) is None


def test_a_taken_name_is_refused_unless_it_is_the_one_being_edited() -> None:
    assert connection_name_problem("PROD", taken=["prod"]) is NameProblem.TAKEN
    assert connection_name_problem("prod", taken=["prod"], current="prod") is None


# Targets ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    ["prod", "admin@example.org", "admin@192.168.0.4", "admin@[::1]", "serveur_de_été", "a@b@c"],
)
def test_a_target_that_ssh_can_take_is_accepted(target: str) -> None:
    assert target_problem(target) is None


@pytest.mark.parametrize("target", ["", "   ", "admin@"])
def test_an_empty_target_is_refused(target: str) -> None:
    assert target_problem(target) is TargetProblem.EMPTY


@pytest.mark.parametrize(
    "target", ["-oProxyCommand=calc", "-v", "admin@-oProxyCommand=calc", "--", "a@-b"]
)
def test_a_target_that_ssh_would_take_for_an_option_is_refused(target: str) -> None:
    assert target_problem(target) is TargetProblem.OPTION_LIKE


@pytest.mark.parametrize(
    "target",
    ["a b", "a\tb", "a\nb", "a\x00b", "a\x7fb", "a\u00a0b", "a\u2003b", "admin@host name"],
)
def test_a_blank_or_control_character_is_refused(target: str) -> None:
    assert target_problem(target) is TargetProblem.FORBIDDEN_CHARACTER


@pytest.mark.parametrize("port", [1, 22, 65535])
def test_the_ports_of_the_range_are_valid(port: int) -> None:
    assert is_valid_port(port)


@pytest.mark.parametrize("port", [0, -1, 65536, True, False, "22", 22.0, None, [22]])
def test_anything_else_is_not_a_port(port: object) -> None:
    assert not is_valid_port(port)


# The data of a connection ----------------------------------------------------------------------


def test_a_connection_with_only_a_target_has_no_port() -> None:
    connection = Connection.from_data("prod", {"target": "prod"})
    assert connection == Connection("prod", target="prod")
    assert connection.port is None


def test_the_data_of_a_connection_holds_no_secret_and_no_profile() -> None:
    assert set(_full().to_data()) == {"target", "port"}


def test_a_profile_written_by_an_older_version_is_kept_but_means_nothing() -> None:
    connection = Connection.from_data("x", {"target": "x", "profile": "git"})
    assert not hasattr(connection, "profile")
    assert connection.extra == {"profile": "git"}
    assert connection.to_data()["profile"] == "git"  # an unknown key is written back


def test_values_of_the_wrong_kind_are_ignored() -> None:
    data = {"target": 3, "port": "2222"}
    assert Connection.from_data("x", data) == Connection("x")


@pytest.mark.parametrize("port", [0, 65536, True, 22.5])
def test_a_port_out_of_range_is_ignored_when_read(port: object) -> None:
    assert Connection.from_data("x", {"target": "x", "port": port}).port is None


def test_the_blanks_around_the_target_are_dropped_when_read() -> None:
    assert Connection.from_data("x", {"target": "  prod\n"}).target == "prod"


# The files -------------------------------------------------------------------------------------


def test_a_connection_survives_a_save(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path / "connections")
    store.save(_full())
    loaded = store.load_all()
    assert loaded.warnings == []
    assert loaded.connections == [_full()]


def test_a_missing_folder_means_no_connection(tmp_path: Path) -> None:
    loaded = ConnectionStore(tmp_path / "none").load_all()
    assert (loaded.connections, loaded.warnings) == ([], [])


def test_the_file_is_named_after_the_connection_and_holds_the_data(tmp_path: Path) -> None:
    ConnectionStore(tmp_path).save(_full())
    written = json.loads((tmp_path / "prod.json").read_text(encoding="utf-8"))
    assert written == {"target": "admin@example.org", "port": 2222}


def test_the_connections_are_sorted_by_name_whatever_the_case(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    for name in ("nas", "Box", "dev"):
        store.save(Connection(name, target=name))
    assert [c.name for c in store.load_all().connections] == ["Box", "dev", "nas"]


def test_unknown_keys_are_kept_when_the_connection_is_written_again(tmp_path: Path) -> None:
    text = json.dumps({"target": "prod", "fingerprint": "SHA256:abc"})
    (tmp_path / "x.json").write_text(text, encoding="utf-8")
    store = ConnectionStore(tmp_path)
    store.save(store.load_all().connections[0])
    written = json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))
    assert written["fingerprint"] == "SHA256:abc"


def test_a_damaged_file_is_reported_and_the_others_are_still_listed(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    store.save(Connection("good", target="good"))
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    loaded = store.load_all()
    assert [c.name for c in loaded.connections] == ["good"]
    assert len(loaded.warnings) == 1
    assert (tmp_path / "bad.json.corrupt").exists()


def test_a_damaged_file_gives_its_backup(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    store.save(Connection("prod", target="old"))
    store.save(Connection("prod", target="new"))  # makes a .bak with the old target
    (tmp_path / "prod.json").write_text("{not json", encoding="utf-8")
    loaded = store.load_all()
    assert [c.target for c in loaded.connections] == ["old"]
    assert len(loaded.warnings) == 1


def test_a_file_that_is_not_a_json_object_is_set_aside(tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    loaded = ConnectionStore(tmp_path).load_all()
    assert loaded.connections == []
    assert len(loaded.warnings) == 1
    assert (tmp_path / "list.json.corrupt").exists()


@pytest.mark.parametrize("target", ["-oProxyCommand=calc", "a b", ""])
def test_a_target_that_cannot_be_used_is_listed_and_reported(tmp_path: Path, target: str) -> None:
    (tmp_path / "bad.json").write_text(json.dumps({"target": target}), encoding="utf-8")
    loaded = ConnectionStore(tmp_path).load_all()
    assert [c.name for c in loaded.connections] == ["bad"]  # listed: the user can correct it
    assert len(loaded.warnings) == 1
    assert "bad" in loaded.warnings[0]


def test_a_file_without_a_target_is_reported(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    loaded = ConnectionStore(tmp_path).load_all()
    assert loaded.connections == [Connection("x")]
    assert len(loaded.warnings) == 1


def test_renaming_removes_the_old_file(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    store.save(Connection("old", target="a"))
    store.save(Connection("new", target="a"), replaces="old")
    assert [c.name for c in store.load_all().connections] == ["new"]
    assert not (tmp_path / "old.json").exists()


def test_changing_only_the_case_of_a_name_keeps_the_file(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    store.save(Connection("prod", target="a"))
    store.save(Connection("Prod", target="a"), replaces="prod")
    assert len(store.load_all().connections) == 1


def test_delete_removes_the_file_and_its_backup(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path)
    store.save(Connection("prod", target="a"))
    store.save(Connection("prod", target="b"))  # makes a .bak
    assert (tmp_path / "prod.json.bak").exists()
    store.delete("prod")
    assert list(tmp_path.iterdir()) == []


def test_deleting_a_connection_that_is_gone_is_not_an_error(tmp_path: Path) -> None:
    ConnectionStore(tmp_path).delete("nothing")


def test_an_unwritable_folder_raises_a_connection_file_error(tmp_path: Path) -> None:
    blocker = tmp_path / "connections"
    blocker.write_text("a file, not a folder", encoding="utf-8")
    with pytest.raises(ConnectionFileError):
        ConnectionStore(blocker).save(Connection("prod", target="a"))


def test_a_strict_connection_name_holds_only_the_characters_of_a_profile_name() -> None:
    assert connection_name_problem("serveur-prod (1)", taken=[], strict=True) is None
    assert connection_name_problem("a&b", taken=[], strict=True) is NameProblem.NOT_ALLOWED
    assert connection_name_problem("a&b", taken=[]) is None  # an old name is not checked
