"""Portable config folder + one-time import from the old app-data folder."""
import json
import shutil

import pytest

from civitai_grabber.core import storage
from civitai_grabber.core.storage import Settings, Storage, config_dir, migrate_legacy


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    legacy, portable = tmp_path / "AppData" / "CivitaiGrabber", tmp_path / "app" / "config"
    monkeypatch.setattr(storage, "legacy_dir", lambda: legacy)
    monkeypatch.setattr(storage, "portable_dir", lambda: portable)
    monkeypatch.delenv("CIVITAI_GRABBER_HOME", raising=False)
    return legacy, portable


def make_legacy(legacy, extra=None):
    (legacy / "logs").mkdir(parents=True)
    (legacy / "settings.json").write_text(json.dumps({"api_key": "OLDKEY", "language": "en"}), encoding="utf-8")
    (legacy / "state.json").write_text(json.dumps({"groups": [{"id": "g1", "name": "Old", "folder": "D:/x"}], "items": []}), encoding="utf-8")
    (legacy / "logs" / "civitai-grabber.log").write_text("old log line\n", encoding="utf-8")
    for name in extra or []:
        (legacy / name).write_text("?", encoding="utf-8")


def test_new_install_uses_folder_next_to_exe(dirs):
    legacy, portable = dirs
    assert config_dir() == portable and portable.is_dir()
    assert storage.LAST_MIGRATION == {}


def test_old_data_is_moved_and_old_folder_removed(dirs):
    legacy, portable = dirs
    make_legacy(legacy)
    assert config_dir() == portable
    assert not legacy.exists()                                     # cleaned up
    st = Storage(portable)
    assert st.load_settings().api_key == "OLDKEY" and st.load_settings().language == "en"
    groups, _ = st.load_state()
    assert [g.name for g in groups] == ["Old"]
    assert (portable / "logs" / "civitai-grabber.log").read_text(encoding="utf-8") == "old log line\n"
    assert set(storage.LAST_MIGRATION["moved"]) == {"settings.json", "state.json", "logs"}
    assert storage.LAST_MIGRATION["left"] == [] and not storage.LAST_MIGRATION["error"]


def test_migration_runs_only_once(dirs):
    legacy, portable = dirs
    make_legacy(legacy)
    config_dir()
    # a second start must not import anything (and must not resurrect a recreated old folder)
    legacy.mkdir(parents=True)
    (legacy / "settings.json").write_text(json.dumps({"api_key": "OTHER"}), encoding="utf-8")
    config_dir()
    assert Storage(portable).load_settings().api_key == "OLDKEY"
    assert (legacy / "settings.json").exists() and storage.LAST_MIGRATION == {}


def test_existing_portable_data_is_never_overwritten(dirs):
    legacy, portable = dirs
    make_legacy(legacy)
    portable.mkdir(parents=True)
    (portable / "settings.json").write_text(json.dumps({"api_key": "NEWKEY"}), encoding="utf-8")
    config_dir()
    assert Storage(portable).load_settings().api_key == "NEWKEY"
    assert (legacy / "settings.json").exists()                     # old data untouched


def test_unknown_files_keep_the_old_folder(dirs):
    legacy, portable = dirs
    make_legacy(legacy, extra=["my-notes.txt"])
    config_dir()
    assert (legacy / "my-notes.txt").exists() and not (legacy / "settings.json").exists()
    assert "my-notes.txt" in storage.LAST_MIGRATION["left"]
    assert Storage(portable).load_settings().api_key == "OLDKEY"


def test_failed_copy_leaves_old_data_intact_and_target_clean(dirs, monkeypatch):
    legacy, portable = dirs
    make_legacy(legacy)
    real = shutil.copy2
    calls = {"n": 0}

    def flaky(src, dst, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        return real(src, dst, *a, **k)

    monkeypatch.setattr(storage.shutil, "copy2", flaky)
    assert config_dir() == portable
    assert "disk full" in storage.LAST_MIGRATION["error"]
    assert (legacy / "settings.json").exists() and (legacy / "state.json").exists()   # nothing lost
    assert not (portable / "settings.json").exists()               # partial copy removed -> retried next start


def test_unwritable_exe_folder_falls_back_to_old_location(dirs, monkeypatch):
    legacy, portable = dirs
    make_legacy(legacy)
    monkeypatch.setattr(storage, "_writable", lambda p: False)
    assert config_dir() == legacy
    assert storage.LAST_MIGRATION["fallback"] == str(legacy)
    assert (legacy / "settings.json").exists()


def test_env_override_wins_and_skips_migration(dirs, tmp_path, monkeypatch):
    legacy, portable = dirs
    make_legacy(legacy)
    custom = tmp_path / "custom"
    monkeypatch.setenv("CIVITAI_GRABBER_HOME", str(custom))
    assert config_dir() == custom and custom.is_dir()
    assert (legacy / "settings.json").exists() and not portable.exists()


def test_migrate_legacy_noop_cases(tmp_path):
    assert migrate_legacy(tmp_path / "missing", tmp_path / "t") == {}
    empty = tmp_path / "empty"
    empty.mkdir()
    assert migrate_legacy(empty, tmp_path / "t") == {}
    assert migrate_legacy(empty, empty) == {}


def test_settings_defaults_unchanged_by_migration():
    assert Settings().theme == "dark"  # dark stays the default
