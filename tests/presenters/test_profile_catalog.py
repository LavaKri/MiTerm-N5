from pathlib import Path

import pytest

from n5terminal.core.config.profiles import Profile, ProfileStore
from n5terminal.presenters.profile_catalog import ProfileCatalog

pytestmark = pytest.mark.unit


@pytest.fixture
def store(tmp_path: Path) -> ProfileStore:
    store = ProfileStore(tmp_path / "profiles")
    store.save(Profile("npm"))
    store.save(Profile("Git"))
    return store


def test_the_names_are_sorted_without_regard_to_the_case(store: ProfileStore) -> None:
    assert ProfileCatalog(store).names() == ["Git", "npm"]


def test_a_profile_is_found_by_its_exact_name_or_whatever_the_case(store: ProfileStore) -> None:
    catalog = ProfileCatalog(store)
    assert catalog.get("Git") is not None
    assert catalog.get("git") is None
    found = catalog.find("GIT")
    assert found is not None
    assert found.name == "Git"
    assert catalog.find("missing") is None


def test_the_names_read_the_files_again(store: ProfileStore) -> None:
    catalog = ProfileCatalog(store)
    store.save(Profile("late"))
    assert catalog.get("late") is None  # as of the last reading
    assert "late" in catalog.names()
    assert catalog.get("late") is not None


def test_a_file_that_cannot_be_read_is_a_warning_and_not_a_profile(tmp_path: Path) -> None:
    folder = tmp_path / "profiles"
    folder.mkdir()
    (folder / "broken.json").write_text("{not json", encoding="utf-8")
    catalog = ProfileCatalog(ProfileStore(folder))
    assert catalog.warnings
    assert catalog.names() == []


def test_a_profile_is_saved_renamed_and_deleted(store: ProfileStore) -> None:
    catalog = ProfileCatalog(store)
    catalog.save(Profile("npm2"), "npm")
    assert catalog.names() == ["Git", "npm2"]
    catalog.delete("npm2")
    assert catalog.names() == ["Git"]


def test_without_a_store_there_is_nothing_and_nothing_is_written() -> None:
    catalog = ProfileCatalog(None)
    assert not catalog.writable
    assert catalog.names() == []
    assert catalog.warnings == []
    catalog.save(Profile("x"), None)
    catalog.delete("x")
    assert catalog.names() == []
