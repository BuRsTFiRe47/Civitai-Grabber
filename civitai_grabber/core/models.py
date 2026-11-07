"""Data classes shared by engine, storage and UI."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

# Item states
RESOLVING = "resolving"
READY = "ready"            # resolved, waiting for the user to start it
QUEUED = "queued"
DOWNLOADING = "downloading"
PAUSED = "paused"
DONE = "done"
ERROR = "error"

ACTIVE_STATES = {QUEUED, DOWNLOADING}
STARTABLE_STATES = {READY, PAUSED, ERROR}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Group:
    id: str = field(default_factory=new_id)
    name: str = ""
    folder: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Group":
        return cls(id=d.get("id") or new_id(), name=d.get("name", ""), folder=d.get("folder", ""))


@dataclass
class Item:
    url: str
    host: str = "civitai.com"
    id: str = field(default_factory=new_id)
    kind: str = "model"                 # model | version
    model_id: Optional[int] = None
    version_id: Optional[int] = None
    # filled by resolve
    name: str = ""
    version_name: str = ""
    creator: str = ""
    model_type: str = ""
    base_model: str = ""
    filename: str = ""
    download_url: str = ""
    size: int = 0                       # bytes (0 = unknown)
    sha256: str = ""
    # user
    group_id: str = ""
    # runtime / persisted state
    state: str = RESOLVING
    done_bytes: int = 0
    error: str = ""
    error_info: str = ""                # technical details of the last error (HTTP status, headers…)
    dest_path: str = ""
    # runtime only (not persisted)
    speed: float = 0.0
    autostart: bool = False

    PERSISTED = (
        "url", "host", "id", "kind", "model_id", "version_id", "name", "version_name",
        "creator", "model_type", "base_model", "filename", "download_url", "size",
        "sha256", "group_id", "state", "done_bytes", "error", "error_info", "dest_path",
    )

    @property
    def key(self) -> str:
        if self.version_id:
            return f"v{self.version_id}"
        return f"m{self.model_id}"

    @property
    def display_name(self) -> str:
        return self.name or self.filename or self.url

    @property
    def progress(self) -> float:
        if self.state == DONE:
            return 1.0
        if self.size > 0:
            return max(0.0, min(1.0, self.done_bytes / self.size))
        return 0.0

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.PERSISTED}

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        it = cls(url=d.get("url", ""))
        for k in cls.PERSISTED:
            if k in d:
                setattr(it, k, d[k])
        # nothing is running after a restart
        if it.state in (DOWNLOADING, QUEUED):
            it.state = PAUSED
        elif it.state == RESOLVING:
            it.state = RESOLVING  # re-resolved on load
        return it
