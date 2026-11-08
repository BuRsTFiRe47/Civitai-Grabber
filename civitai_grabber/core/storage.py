"""Settings + state persistence (plain JSON, atomic writes)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from civitai_grabber.core.models import Group, Item


APP_DIR = "CivitaiGrabber"
_MIGRATE_FILES = ("settings.json", "state.json")

# Filled by config_dir(); the app reads it once to tell the user what happened.
# keys: source, target, moved (list), left (list), error, fallback
LAST_MIGRATION: dict = {}


def legacy_dir() -> Path:
    """Where versions before the portable mode kept their data (per-user app-data folder)."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "civitai-grabber"


def portable_dir() -> Path:
    """`config` folder next to the exe (frozen build) or next to main.py (running from source)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "config"


def _writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / f".write-test-{os.getpid()}"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def migrate_legacy(legacy: Path, target: Path) -> dict:
    """Move settings/state/logs from the old app-data folder into `target`, then clean up.

    Safe by construction: nothing is moved if `target` already has data; files are copied and
    verified first, the old ones are deleted only afterwards, and only files we know about are
    deleted (an unknown file keeps the old folder alive). On any error the old data stays intact
    and the partial copy is removed.
    """
    res: dict = {"source": str(legacy), "target": str(target), "moved": [], "left": [], "error": ""}
    try:
        if not legacy.is_dir() or legacy.resolve() == target.resolve():
            return {}
        if any((target / n).exists() for n in _MIGRATE_FILES):
            return {}
        names = [n for n in _MIGRATE_FILES if (legacy / n).is_file()]
        has_logs = (legacy / "logs").is_dir()
        if not names and not has_logs:
            return {}
    except OSError:
        return {}

    copied: list[Path] = []
    try:
        target.mkdir(parents=True, exist_ok=True)
        for n in names:
            shutil.copy2(legacy / n, target / n)
            copied.append(target / n)
            if (target / n).stat().st_size != (legacy / n).stat().st_size:
                raise OSError(f"size mismatch after copying {n}")
        if has_logs:
            shutil.copytree(legacy / "logs", target / "logs", dirs_exist_ok=True)
    except (OSError, shutil.Error) as e:
        for c in copied:  # undo: leave the old data as the single source of truth
            try:
                c.unlink()
            except OSError:
                pass
        res["error"] = str(e)
        return res

    # copies verified -> clean up the old location (known files only)
    for n in names:
        try:
            (legacy / n).unlink()
            res["moved"].append(n)
        except OSError:
            res["left"].append(n)
    if has_logs:
        shutil.rmtree(legacy / "logs", ignore_errors=True)
        res["moved"].append("logs")
        if (legacy / "logs").exists():
            res["left"].append("logs")
    try:
        legacy.rmdir()  # only succeeds when empty
    except OSError:
        res["left"] += [x.name for x in legacy.iterdir() if x.name not in res["left"]] if legacy.exists() else []
    return res


def config_dir() -> Path:
    """Portable `config` folder next to the exe; imports data from the old app-data folder once.

    CIVITAI_GRABBER_HOME overrides everything. If the exe folder is not writable
    (e.g. installed under Program Files) the old app-data folder keeps being used.
    """
    LAST_MIGRATION.clear()
    override = os.environ.get("CIVITAI_GRABBER_HOME")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    target = portable_dir()
    if not _writable(target):
        legacy = legacy_dir()
        legacy.mkdir(parents=True, exist_ok=True)
        LAST_MIGRATION.update(fallback=str(legacy), target=str(target))
        return legacy
    LAST_MIGRATION.update(migrate_legacy(legacy_dir(), target))
    return target


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


MAX_RECENT_FOLDERS = 8


@dataclass
class Settings:
    api_key: str = ""
    default_folder: str = ""          # for ungrouped items
    base_folder: str = ""             # parent of per-creator folders (auto-group)
    language: str = "tr"              # tr | en
    theme: str = "dark"               # dark | light
    monitor_clipboard: bool = True
    max_concurrent: int = 2
    start_delay: float = 3.0          # seconds between starting two downloads
    retries: int = 3
    verify_sha256: bool = False
    skip_existing: bool = True        # file already in the folder with the same size -> do not download
    stop_on_cloudflare: bool = False  # False: a Cloudflare block fails that file only and the queue goes on
    speed_limit_kbps: int = 0         # total download speed limit in KB/s, 0 = unlimited
    all_versions: bool = True         # a model link without ?modelVersionId adds every version of the model
    recent_folders: list = field(default_factory=list)   # recently used parent locations of group folders, newest first
    file_extensions: str = "safetensors, pt"   # allowed file types, in order of preference; empty = any
    user_agent: str = DEFAULT_UA
    cookie: str = ""                  # optional, e.g. "cf_clearance=...; ..."
    geometry: str = ""                # base64 window geometry

    def to_dict(self) -> dict:
        return asdict(self)

    def allowed_extensions(self) -> list[str]:
        """['safetensors', 'pt'] from 'safetensors, .pt' (order = preference)."""
        out: list[str] = []
        for part in str(self.file_extensions).replace(";", ",").replace(" ", ",").split(","):
            e = part.strip().lower().lstrip("*").lstrip(".")
            if e and e not in out:
                out.append(e)
        return out

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        names = {f.name for f in fields(cls)}
        s = cls(**{k: v for k, v in d.items() if k in names})
        s.max_concurrent = max(1, min(8, int(s.max_concurrent)))
        s.start_delay = max(0.0, float(s.start_delay))
        s.retries = max(0, min(10, int(s.retries)))
        s.recent_folders = [str(x) for x in (s.recent_folders or []) if x][:MAX_RECENT_FOLDERS]
        if s.language not in ("tr", "en"):
            s.language = "tr"
        if s.theme not in ("dark", "light"):
            s.theme = "dark"
        return s


def _atomic_write(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


class Storage:
    def __init__(self, base: Path | None = None):
        self.base = base or config_dir()
        self.base.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.base / "settings.json"
        self.state_path = self.base / "state.json"

    def load_settings(self) -> Settings:
        try:
            return Settings.from_dict(_read(self.settings_path))
        except (TypeError, ValueError):
            return Settings()

    def save_settings(self, s: Settings) -> None:
        _atomic_write(self.settings_path, s.to_dict())

    def load_state(self) -> tuple[list[Group], list[Item]]:
        d = _read(self.state_path)
        groups = [Group.from_dict(g) for g in d.get("groups", []) if isinstance(g, dict)]
        items = [Item.from_dict(i) for i in d.get("items", []) if isinstance(i, dict) and i.get("url")]
        return groups, items

    def save_state(self, groups: list[Group], items: list[Item]) -> None:
        _atomic_write(
            self.state_path,
            {"groups": [g.to_dict() for g in groups], "items": [i.to_dict() for i in items]},
        )
