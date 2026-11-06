from pathlib import Path

import pytest

from n5terminal.core.config.profiles import ProfileStore
from n5terminal.core.config.starter_profiles import (
    STARTER_FOLDER,
    offer_starter_profiles,
    starter_folder,
)
from n5terminal.core.errors import ProfileError

pytestmark = pytest.mark.unit

REPOSITORY = Path(__file__).resolve().parents[3]


def application(tmp_path: Path, **profiles: str) -> Path:
    folder = tmp_path / "app"
    (folder / STARTER_FOLDER).mkdir(parents=True)
    for name, text in profiles.items():
        (folder / STARTER_FOLDER / f"{name}.json").write_text(text, encoding="utf-8")
    return folder


def test_a_starter_profile_is_copied_the_first_time(tmp_path: Path) -> None:
    app, target = application(tmp_path, git='{"commands": ["git status"]}'), tmp_path / "profiles"
    assert offer_starter_profiles(app, target) == ["git"]
    assert [p.name for p in ProfileStore(target).load_all().profiles] == ["git"]


def test_a_profile_the_user_deleted_does_not_come_back(tmp_path: Path) -> None:
    app, target = application(tmp_path, git="{}"), tmp_path / "profiles"
    offer_starter_profiles(app, target)
    ProfileStore(target).delete("git")
    assert offer_starter_profiles(app, target) == []
    assert ProfileStore(target).load_all().profiles == []


def test_a_profile_the_user_changed_is_never_overwritten(tmp_path: Path) -> None:
    app, target = application(tmp_path, git='{"commands": ["git status"]}'), tmp_path / "profiles"
    offer_starter_profiles(app, target)
    (target / "git.json").write_text('{"commands": ["mine"]}', encoding="utf-8")
    offer_starter_profiles(app, target)
    assert ProfileStore(target).load_all().profiles[0].commands == ["mine"]


def test_a_profile_the_user_already_has_is_kept_and_counted_as_offered(tmp_path: Path) -> None:
    app, target = application(tmp_path, git="{}"), tmp_path / "profiles"
    target.mkdir()
    (target / "git.json").write_text('{"commands": ["mine"]}', encoding="utf-8")
    assert offer_starter_profiles(app, target) == []
    ProfileStore(target).delete("git")
    assert offer_starter_profiles(app, target) == []


def test_a_new_starter_profile_is_offered_later(tmp_path: Path) -> None:
    app, target = application(tmp_path, git="{}"), tmp_path / "profiles"
    offer_starter_profiles(app, target)
    (app / STARTER_FOLDER / "npm.json").write_text("{}", encoding="utf-8")
    assert offer_starter_profiles(app, target) == ["npm"]


def test_without_a_starter_folder_nothing_happens(tmp_path: Path) -> None:
    target = tmp_path / "profiles"
    assert offer_starter_profiles(tmp_path, target) == []
    assert not target.exists()


def test_a_folder_that_cannot_be_written_is_a_profile_error(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file", encoding="utf-8")
    with pytest.raises(ProfileError):
        offer_starter_profiles(application(tmp_path, git="{}"), blocker / "profiles")


def test_the_git_profile_of_the_application_is_valid() -> None:
    profiles = ProfileStore(REPOSITORY / STARTER_FOLDER).load_all()
    assert profiles.warnings == []
    git = next(p for p in profiles.profiles if p.name == "git")
    assert git.variables == ["source", "message"]
    assert git.program == "git"
    assert "status" in git.commands
    assert git.commands == sorted(git.commands, key=str.casefold)
    assert 'commit -m "{message}"' in git.commands


def test_the_packaged_application_looks_in_internal_start_profil(tmp_path: Path) -> None:
    app = tmp_path / "app"
    packaged = app / "_internal" / "StartProfil"
    packaged.mkdir(parents=True)
    (packaged / "git.json").write_text("{}", encoding="utf-8")
    target = tmp_path / "profiles"
    assert starter_folder(app, packaged=True) == packaged
    assert offer_starter_profiles(app, target, packaged=True) == ["git"]
    assert starter_folder(app, packaged=False) == app / STARTER_FOLDER
    assert offer_starter_profiles(app, tmp_path / "other", packaged=False) == []
