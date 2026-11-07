"""Settings + state persistence (plain JSON, atomic writes)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from civitai_grabber.core.models import Group, Item


def config_dir() -> Path:
    override = os.environ.get("CIVITAI_GRABBER_HOME")
    if override:
        p = Path(override)
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "CivitaiGrabber"
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "CivitaiGrabber"
    else:
        p = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "civitai-grabber"
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


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
