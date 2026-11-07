"""Qt-side orchestration: item list, groups, resolve + download scheduling."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from civitai_grabber.core.api import CivitaiError, CloudflareBlocked, make_session, resolve
from civitai_grabber.core.downloader import DownloadCancelled, download, safe_filename
from civitai_grabber.core.links import ParsedLink
from civitai_grabber.core.logsetup import one_line, redact
from civitai_grabber.core.models import (
    DONE,
    DOWNLOADING,
    ERROR,
    PAUSED,
    QUEUED,
    READY,
    RESOLVING,
    STARTABLE_STATES,
    Group,
    Item,
)
from civitai_grabber.core.storage import Settings, Storage
from civitai_grabber.i18n import t

log = logging.getLogger("civgrab.engine")


def tag_of(it: Item) -> str:
    """Short per-item prefix for log lines; the 6-char id is what the log filter searches for."""
    return f"[#{it.id[:6]} {one_line(it.name or it.filename or it.url, 32)}]"


class Engine(QObject):
    itemsAdded = Signal(list)       # [item ids]
    itemChanged = Signal(str)
    itemRemoved = Signal(str)
    groupsChanged = Signal()
    message = Signal(str, str)      # (code, detail) -> translated by the UI

    # worker thread -> GUI thread
    _sig_resolved = Signal(str, object)
    _sig_progress = Signal(str, object, object)  # byte counts: `int` here is a C int32 -> OverflowError > 2 GiB
    _sig_finished = Signal(str, object)

    def __init__(self, storage: Storage, settings: Settings, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.groups: list[Group] = []
        self.items: dict[str, Item] = {}
        self.order: list[str] = []

        self._cancel: dict[str, threading.Event] = {}      # live download threads
        self._part_paths: dict[str, Path] = {}
        self._removed: set[str] = set()
        self._speed: dict[str, tuple[float, int]] = {}
        self._last_start = 0.0
        self._resolve_sem = threading.Semaphore(2)
        self._closing = False

        self._sig_resolved.connect(self._on_resolved)
        self._sig_progress.connect(self._on_progress)
        self._sig_finished.connect(self._on_finished)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1500)
        self._save_timer.timeout.connect(self.save_now)

        self._tick = QTimer(self)
        self._tick.setInterval(400)
        self._tick.timeout.connect(self._schedule)

        groups, items = storage.load_state()
        self.groups = groups
        for it in items:
            self.items[it.id] = it
            self.order.append(it.id)

    def begin(self) -> None:
        """Call once the UI is connected: resumes unfinished resolves, starts the scheduler."""
        for it in self.items.values():
            if it.state == RESOLVING:
                self._spawn_resolve(it)
        self._tick.start()

    # ------------------------------------------------------------------ settings
    def set_settings(self, s: Settings) -> None:
        self.settings = s
        self.storage.save_settings(s)

    # ------------------------------------------------------------------ groups
    def group(self, gid: str) -> Optional[Group]:
        for g in self.groups:
            if g.id == gid:
                return g
        return None

    def group_name(self, gid: str) -> str:
        g = self.group(gid)
        return g.name if g else ""

    def add_group(self, name: str, folder: str) -> Group:
        g = Group(name=name.strip(), folder=folder.strip())
        self.groups.append(g)
        self.groupsChanged.emit()
        self._dirty()
        return g

    def edit_group(self, gid: str, name: str, folder: str) -> None:
        g = self.group(gid)
        if g:
            g.name, g.folder = name.strip(), folder.strip()
            self.groupsChanged.emit()
            for it in self.items.values():
                if it.group_id == gid:
                    self.itemChanged.emit(it.id)
            self._dirty()

    def delete_group(self, gid: str) -> None:
        self.groups = [g for g in self.groups if g.id != gid]
        for it in self.items.values():
            if it.group_id == gid:
                it.group_id = ""
                self.itemChanged.emit(it.id)
        self.groupsChanged.emit()
        self._dirty()

    def set_group(self, ids: Iterable[str], gid: str) -> None:
        if gid and not self.group(gid):
            return
        for i in ids:
            it = self.items.get(i)
            if it and it.group_id != gid:
                it.group_id = gid
                self.itemChanged.emit(i)
        self.groupsChanged.emit()
        self._dirty()

    def auto_group_by_creator(self, ids: Iterable[str], base_folder: str) -> tuple[int, int]:
        """One group per creator (folder = base/creator). Returns (groups created, items assigned)."""
        created = assigned = 0
        for i in ids:
            it = self.items.get(i)
            if not it or not it.creator:
                continue
            g = next((x for x in self.groups if x.name.lower() == it.creator.lower()), None)
            if g is None:
                folder = str(Path(base_folder) / (safe_filename(it.creator) or "unknown")) if base_folder else ""
                g = Group(name=it.creator, folder=folder)
                self.groups.append(g)
                created += 1
            if it.group_id != g.id:
                it.group_id = g.id
                assigned += 1
                self.itemChanged.emit(i)
        self.groupsChanged.emit()
        self._dirty()
        return created, assigned

    def folder_for(self, it: Item) -> Optional[Path]:
        g = self.group(it.group_id)
        base = (g.folder if g and g.folder else "") or self.settings.default_folder
        return Path(base) if base else None

    # ------------------------------------------------------------------ adding links
    def add_links(self, links: Iterable[ParsedLink]) -> int:
        existing = {it.key for it in self.items.values()} | {it.url for it in self.items.values()}
        new_ids: list[str] = []
        for lk in links:
            if lk.key in existing or lk.url in existing:
                continue
            existing.add(lk.key)
            it = Item(url=lk.url, host=lk.host, kind=lk.kind, model_id=lk.model_id, version_id=lk.version_id)
            self.items[it.id] = it
            self.order.append(it.id)
            new_ids.append(it.id)
            log.info("[#%s] %s", it.id[:6], t("log.link_added", url=redact(lk.url)))
        if new_ids:
            self.itemsAdded.emit(new_ids)
            for i in new_ids:
                self._spawn_resolve(self.items[i])
            self.groupsChanged.emit()
            self._dirty()
        return len(new_ids)

    # ------------------------------------------------------------------ resolve
    def _spawn_resolve(self, it: Item) -> None:
        it.state = RESOLVING
        it.error = ""
        item_id, host, mid, vid = it.id, it.host, it.model_id, it.version_id
        settings = self.settings
        allowed = settings.allowed_extensions()
        tag = tag_of(it)
        log.info("%s %s", tag, t("log.resolving", allowed=",".join(allowed) or "*"))

        def work():
            with self._resolve_sem:
                try:
                    res = resolve(make_session(settings, host), host, mid, vid, allowed, tag)
                    time.sleep(0.25)  # be gentle with the API
                except CivitaiError as e:
                    res = e
                except Exception as e:  # noqa: BLE001
                    res = CivitaiError(type(e).__name__)
            if not self._closing:
                self._sig_resolved.emit(item_id, res)

        threading.Thread(target=work, daemon=True).start()
        self.itemChanged.emit(it.id)

    def _on_resolved(self, item_id: str, res) -> None:
        it = self.items.get(item_id)
        if it is None:
            return
        if isinstance(res, Exception):
            it.state = ERROR
            it.error = res.as_text() if isinstance(res, CivitaiError) else str(res)
            it.error_info = getattr(res, "info", "") or ""
            it.autostart = False
            log.warning("%s %s", tag_of(it), t("log.resolve_failed", err=it.error, info=it.error_info))
            self.itemChanged.emit(item_id)
            self._dirty()
            return
        it.model_id = res.model_id or it.model_id
        it.version_id = res.version_id or it.version_id
        it.name, it.version_name, it.creator = res.name, res.version_name, res.creator
        it.model_type, it.base_model = res.model_type, res.base_model
        it.filename, it.download_url, it.size, it.sha256 = res.filename, res.download_url, res.size, res.sha256
        for other in self.items.values():
            if other is not it and it.version_id and other.version_id == it.version_id:
                self.remove([item_id], _silent=True)
                self.message.emit("duplicate", it.display_name)
                return
        it.state, it.error, it.error_info = READY, "", ""
        log.info("%s %s", tag_of(it), t("log.resolved", creator=it.creator or "?", mtype=it.model_type or "?",
                                        file=it.filename or "?", size=it.size))
        if it.autostart:
            it.autostart = False
            self._queue(it)
        self.itemChanged.emit(item_id)
        self._dirty()

    def re_resolve(self, ids: Iterable[str]) -> None:
        for i in ids:
            it = self.items.get(i)
            if it and it.state in (ERROR, READY, PAUSED) and i not in self._cancel:
                self._spawn_resolve(it)

    # ------------------------------------------------------------------ start / pause / remove
    def _queue(self, it: Item) -> None:
        if self.folder_for(it) is None:
            it.state, it.error, it.error_info = ERROR, "nofolder", ""
            log.warning("%s %s", tag_of(it), t("log.no_folder"))
        else:
            it.state, it.error, it.error_info = QUEUED, "", ""
            log.info("%s %s", tag_of(it), t("log.queued", folder=str(self.folder_for(it))))

    def start(self, ids: Iterable[str]) -> None:
        for i in ids:
            it = self.items.get(i)
            if not it:
                continue
            if it.state == RESOLVING:
                it.autostart = True
            elif it.state in STARTABLE_STATES:
                if not it.download_url:
                    it.autostart = True
                    self._spawn_resolve(it)
                else:
                    self._queue(it)
            self.itemChanged.emit(i)
        self._dirty()

    def pause(self, ids: Iterable[str]) -> None:
        for i in ids:
            it = self.items.get(i)
            if not it:
                continue
            it.autostart = False
            if it.state in (QUEUED, DOWNLOADING):
                if i in self._cancel:
                    self._cancel[i].set()
                it.state, it.speed = PAUSED, 0.0
                self.itemChanged.emit(i)
        self._dirty()

    def pause_all(self) -> None:
        self.pause(list(self.items))

    def remove(self, ids: Iterable[str], _silent: bool = False) -> None:
        for i in list(ids):
            it = self.items.pop(i, None)
            if it is None:
                continue
            if i in self.order:
                self.order.remove(i)
            if i in self._cancel:
                self._cancel[i].set()
                self._removed.add(i)
            elif it.state != DONE:
                self._delete_part(self._part_for(it))
            self.itemRemoved.emit(i)
        self.groupsChanged.emit()
        self._dirty()

    def clear_finished(self) -> None:
        self.remove([i for i, it in self.items.items() if it.state == DONE])

    def _part_for(self, it: Item) -> Optional[Path]:
        folder = self.folder_for(it)
        name = safe_filename(it.filename)
        if not folder or not name:
            return None
        return folder / (name + ".part")

    @staticmethod
    def _delete_part(p: Optional[Path]) -> None:
        if p:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------ scheduler / workers
    def _schedule(self) -> None:
        if self._closing:
            return
        if len(self._cancel) >= self.settings.max_concurrent:
            return
        if time.monotonic() - self._last_start < self.settings.start_delay:
            return
        for i in self.order:
            it = self.items[i]
            if it.state == QUEUED and i not in self._cancel:
                self._spawn_download(it)
                self._last_start = time.monotonic()
                return

    def _spawn_download(self, it: Item) -> None:
        folder = self.folder_for(it)
        if folder is None:
            it.state, it.error = ERROR, "nofolder"
            self.itemChanged.emit(it.id)
            return
        it.state, it.error, it.speed = DOWNLOADING, "", 0.0
        cancel = threading.Event()
        self._cancel[it.id] = cancel
        self._speed[it.id] = (time.monotonic(), it.done_bytes)
        part = self._part_for(it)
        if part:
            self._part_paths[it.id] = part
        s = self.settings
        item_id, host, url = it.id, it.host, it.download_url
        filename, size, sha = it.filename, it.size, it.sha256
        tag = tag_of(it)

        def work():
            last = [0.0]

            def prog(done: int, total: int):
                now = time.monotonic()
                if now - last[0] >= 0.25 or (total and done >= total):
                    last[0] = now
                    self._sig_progress.emit(item_id, done, total)

            try:
                path = download(
                    make_session(s, host), url, folder, filename,
                    expected_size=size, sha256=sha, verify=s.verify_sha256,
                    retries=s.retries, progress=prog, cancel=cancel, tag=tag,
                )
                result = path
            except Exception as e:  # noqa: BLE001
                result = e
            if not self._closing:
                self._sig_finished.emit(item_id, result)

        threading.Thread(target=work, daemon=True).start()
        self.itemChanged.emit(it.id)

    def _on_progress(self, item_id: str, done: int, total: int) -> None:
        it = self.items.get(item_id)
        if it is None or it.state != DOWNLOADING:
            return
        now = time.monotonic()
        t0, d0 = self._speed.get(item_id, (now, done))
        if now - t0 >= 0.2:
            inst = max(0.0, (done - d0) / (now - t0))
            it.speed = inst if it.speed <= 0 else it.speed * 0.6 + inst * 0.4
            self._speed[item_id] = (now, done)
        it.done_bytes = done
        if total:
            it.size = total
        self.itemChanged.emit(item_id)

    def _on_finished(self, item_id: str, result) -> None:
        self._cancel.pop(item_id, None)
        self._speed.pop(item_id, None)
        part = self._part_paths.pop(item_id, None)
        if item_id in self._removed:
            self._removed.discard(item_id)
            self._delete_part(part)
            return
        it = self.items.get(item_id)
        if it is None:
            return
        it.speed = 0.0
        if isinstance(result, Path):
            it.state, it.error, it.error_info, it.dest_path = DONE, "", "", str(result)
            try:
                it.size = it.done_bytes = result.stat().st_size
            except OSError:
                pass
        elif isinstance(result, DownloadCancelled):
            if it.state == DOWNLOADING:  # stopped by shutdown etc.
                it.state = PAUSED
        elif isinstance(result, CivitaiError):
            it.state, it.error, it.error_info = ERROR, result.as_text(), result.info
            log.error("%s %s", tag_of(it), t("log.dl_failed", err=it.error, info=result.info))
            if isinstance(result, CloudflareBlocked):
                # don't keep hammering a blocked connection: park the rest of the queue
                for o in self.items.values():
                    if o.state == QUEUED and o.id not in self._cancel:
                        o.state = READY
                        self.itemChanged.emit(o.id)
                self.message.emit("queue_stopped_cf", "")
        else:
            it.state, it.error = ERROR, f"unknown:{type(result).__name__}: {result}"
            it.error_info = ""
            log.error("%s %s", tag_of(it), t("log.dl_failed", err=it.error, info=""), exc_info=result)
        self.itemChanged.emit(item_id)
        self._dirty()

    # ------------------------------------------------------------------ misc
    def page_url(self, it: Item) -> str:
        if it.model_id:
            q = f"?modelVersionId={it.version_id}" if it.version_id else ""
            return f"https://{it.host}/models/{it.model_id}{q}"
        return it.url

    def counts(self) -> dict:
        c = {"total": len(self.items), "downloading": 0, "queued": 0, "done": 0, "error": 0, "speed": 0.0}
        for it in self.items.values():
            if it.state == DOWNLOADING:
                c["downloading"] += 1
                c["speed"] += it.speed
            elif it.state == QUEUED:
                c["queued"] += 1
            elif it.state == DONE:
                c["done"] += 1
            elif it.state == ERROR:
                c["error"] += 1
        return c

    def _dirty(self) -> None:
        if not self._closing:
            self._save_timer.start()

    def save_now(self) -> None:
        try:
            self.storage.save_state(self.groups, [self.items[i] for i in self.order if i in self.items])
        except OSError:
            pass

    def shutdown(self) -> None:
        """Pause everything (keeps .part files) and write state."""
        for ev in self._cancel.values():
            ev.set()
        for it in self.items.values():
            if it.state in (QUEUED, DOWNLOADING):
                it.state, it.speed = PAUSED, 0.0
        self._tick.stop()
        self._save_timer.stop()
        self.save_now()
        self._closing = True
