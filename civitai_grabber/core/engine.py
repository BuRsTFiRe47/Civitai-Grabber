"""Qt-side orchestration: item list, groups, resolve + download scheduling."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from civitai_grabber.core.api import BuzzRequired, CivitaiError, LoginRequired, CloudflareBlocked, list_version_ids, make_session, resolve
from civitai_grabber.core import power
from civitai_grabber.core.downloader import DownloadCancelled, download, part_path, safe_filename
from civitai_grabber.core.links import ParsedLink
from civitai_grabber.core.logsetup import one_line, redact
from civitai_grabber.core.ratelimit import RateLimiter
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
from civitai_grabber.core.storage import MAX_RECENT_FOLDERS, Settings, Storage
from civitai_grabber.i18n import t

log = logging.getLogger("civgrab.engine")


def tag_of(it: Item) -> str:
    """Short per-item prefix for log lines; the 6-char id is what the log filter searches for."""
    return f"[#{it.id[:6]} {one_line(it.name or it.filename or it.url, 32)}]"


class Expanded:
    """Result of looking up a whole model: all its version ids."""

    def __init__(self, version_ids: list[int]):
        self.version_ids = version_ids


class Engine(QObject):
    itemsAdded = Signal(list)       # [item ids]
    itemChanged = Signal(str)
    itemRemoved = Signal(str)
    groupsChanged = Signal()
    orderChanged = Signal()
    powerModeChanged = Signal(str)
    allFinished = Signal(str)       # power mode to execute
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
        self._cooldown_until = 0.0
        self.cf_cooldown = 15.0          # seconds the queue waits after a Cloudflare block
        self.power_mode = power.NONE     # never persisted: no surprise shutdown after a restart
        self._power_activity = False
        self._resolve_sem = threading.Semaphore(2)
        self._closing = False
        self._stop_evt = threading.Event()
        self._skipped: set[str] = set()
        self.limiter = RateLimiter(settings.speed_limit_kbps * 1024)
        self._threads: list[threading.Thread] = []

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

    def _start_thread(self, fn) -> None:
        self._threads = [x for x in self._threads if x.is_alive()]
        th = threading.Thread(target=fn, daemon=True)
        self._threads.append(th)
        th.start()

    def _emit_safe(self, sig, *args) -> None:
        """Emit from a worker thread; never crash if the engine is already being torn down."""
        if self._closing:
            return
        try:
            sig.emit(*args)
        except RuntimeError:  # underlying C++ object already deleted
            pass

    def begin(self) -> None:
        """Call once the UI is connected: resumes unfinished resolves, starts the scheduler."""
        for it in self.items.values():
            if it.state == RESOLVING:
                self._spawn_resolve(it)
        self._tick.start()

    # ------------------------------------------------------------------ settings
    def set_settings(self, s: Settings) -> None:
        self.settings = s
        self.limiter.set_rate(max(0, int(s.speed_limit_kbps)) * 1024)
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

    # -- folder memory: dialogs start where the user last was
    def remember_location(self, path: str) -> None:
        path = (path or "").strip()
        if not path:
            return
        recent = [path] + [p for p in self.settings.recent_folders if p != path]
        recent = recent[:MAX_RECENT_FOLDERS]
        if recent != self.settings.recent_folders:
            self.settings.recent_folders = recent
            self.storage.save_settings(self.settings)

    def suggest_base(self) -> str:
        """Where new group folders go by default: the base folder, else the location used last."""
        return self.settings.base_folder or (self.settings.recent_folders[0] if self.settings.recent_folders else "")

    def add_group(self, name: str, folder: str) -> Group:
        g = Group(name=name.strip(), folder=folder.strip())
        if g.folder:
            self.remember_location(str(Path(g.folder).parent))
        self.groups.append(g)
        self.groupsChanged.emit()
        self._dirty()
        return g

    def edit_group(self, gid: str, name: str, folder: str) -> None:
        g = self.group(gid)
        if g:
            g.name, g.folder = name.strip(), folder.strip()
            if g.folder:
                self.remember_location(str(Path(g.folder).parent))
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

        expand = it.kind == "model" and not vid and settings.all_versions and bool(mid)

        def work():
            with self._resolve_sem:
                try:
                    if expand:
                        res = Expanded(list_version_ids(make_session(settings, host), host, mid, tag))
                    else:
                        res = resolve(make_session(settings, host), host, mid, vid, allowed, tag)
                    self._stop_evt.wait(0.25)  # be gentle with the API
                except CivitaiError as e:
                    res = e
                except Exception as e:  # noqa: BLE001
                    res = CivitaiError(type(e).__name__)
            self._emit_safe(self._sig_resolved, item_id, res)

        self._start_thread(work)
        self.itemChanged.emit(it.id)

    def _on_resolved(self, item_id: str, res) -> None:
        it = self.items.get(item_id)
        if it is None:
            return
        if isinstance(res, Expanded):
            self._expand(it, res.version_ids)
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
        it.early_access = res.early_access
        it.filename, it.download_url, it.size, it.sha256 = res.filename, res.download_url, res.size, res.sha256
        for other in self.items.values():
            if other is not it and it.version_id and other.version_id == it.version_id:
                self.remove([item_id], _silent=True)
                self.message.emit("duplicate", it.display_name)
                return
        it.state, it.error, it.error_info = READY, "", ""
        if it.early_access:
            log.warning("%s %s", tag_of(it), t("log.early_access", date=it.early_access))
        log.info("%s %s", tag_of(it), t("log.resolved", creator=it.creator or "?", mtype=it.model_type or "?",
                                        file=it.filename or "?", size=it.size))
        if it.autostart:
            it.autostart = False
            self._queue(it)
        self.itemChanged.emit(item_id)
        self._dirty()

    def _expand(self, it: Item, version_ids: list[int]) -> None:
        """A model link without a version: this row becomes the newest version, every other version gets a row."""
        base = it.url.split("?", 1)[0]
        have = {x.version_id for x in self.items.values() if x.version_id}
        first = next((v for v in version_ids if v not in have), None)
        log.info("%s %s", tag_of(it), t("log.versions_found", n=len(version_ids)))
        pos = self.order.index(it.id) + 1 if it.id in self.order else len(self.order)
        new_items: list[Item] = []
        for vid in version_ids:
            if vid == first or vid in have:
                continue
            n = Item(url=f"{base}?modelVersionId={vid}", host=it.host, kind="version", model_id=it.model_id,
                     version_id=vid, group_id=it.group_id)
            n.autostart = it.autostart
            new_items.append(n)
        if first is None:  # every version is already in the list
            self.remove([it.id], _silent=True)
            self.message.emit("duplicate", it.display_name or base)
            return
        it.kind, it.version_id = "version", first
        it.url = f"{base}?modelVersionId={first}"
        for n in new_items:
            self.items[n.id] = n
            self.order.insert(pos, n.id)
            pos += 1
        if new_items:
            self.orderChanged.emit()
        self.groupsChanged.emit()
        self.message.emit("expanded", str(len(new_items) + 1))
        self._spawn_resolve(it)
        for n in new_items:
            self._spawn_resolve(n)
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
        if not folder or not safe_filename(it.filename):
            return None
        return part_path(folder, it.filename, str(it.version_id or ""))

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
        now = time.monotonic()
        if now - self._last_start < self.settings.start_delay or now < self._cooldown_until:
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
        suffix = str(it.version_id or "")
        it.skipped = False
        self._skipped.discard(item_id)
        tag = tag_of(it)
        if self.power_mode != power.NONE:
            self._power_activity = True

        def work():
            last = [0.0]

            def prog(done: int, total: int):
                now = time.monotonic()
                if now - last[0] >= 0.25 or (total and done >= total):
                    last[0] = now
                    self._emit_safe(self._sig_progress, item_id, done, total)

            try:
                path = download(
                    make_session(s, host), url, folder, filename,
                    expected_size=size, sha256=sha, verify=s.verify_sha256,
                    retries=s.retries, progress=prog, cancel=cancel, tag=tag,
                    part_suffix=suffix, skip_existing=s.skip_existing, limiter=self.limiter,
                    on_skip=lambda: self._skipped.add(item_id),
                )
                result = path
            except Exception as e:  # noqa: BLE001
                result = e
            self._emit_safe(self._sig_finished, item_id, result)

        self._start_thread(work)
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
            it.skipped = item_id in self._skipped
            self._skipped.discard(item_id)
            try:
                it.size = it.done_bytes = result.stat().st_size
            except OSError:
                pass
        elif isinstance(result, DownloadCancelled):
            if it.state == DOWNLOADING:  # stopped by shutdown etc.
                it.state = PAUSED
        elif isinstance(result, CivitaiError):
            if isinstance(result, LoginRequired) and it.early_access:
                # an early-access version that was refused: Buzz, not a bad API key and not Cloudflare
                result = BuzzRequired(it.early_access if it.early_access != "yes" else "", result.info)
            it.state, it.error, it.error_info = ERROR, result.as_text(), result.info
            log.error("%s %s", tag_of(it), t("log.dl_failed", err=it.error, info=result.info))
            if isinstance(result, CloudflareBlocked):
                if self.settings.stop_on_cloudflare:
                    # park the rest of the queue instead of hammering a blocked connection
                    for o in self.items.values():
                        if o.state == QUEUED and o.id not in self._cancel:
                            o.state = READY
                            self.itemChanged.emit(o.id)
                    self.message.emit("queue_stopped_cf", "")
                else:
                    # only this file fails; the queue goes on after a short breather
                    self._cooldown_until = time.monotonic() + self.cf_cooldown
                    log.warning("%s %s", tag_of(it), t("log.cf_cooldown", secs=f"{self.cf_cooldown:.0f}"))
        else:
            it.state, it.error = ERROR, f"unknown:{type(result).__name__}: {result}"
            it.error_info = ""
            log.error("%s %s", tag_of(it), t("log.dl_failed", err=it.error, info=""), exc_info=result)
        self.itemChanged.emit(item_id)
        self._dirty()
        if not isinstance(result, DownloadCancelled):
            self._maybe_all_finished()

    # ------------------------------------------------------------------ ordering
    def move_to(self, ids: Iterable[str], target_id: Optional[str], after: bool = False) -> bool:
        """Drag & drop: put `ids` (keeping their relative order) before/after `target_id`; None = at the end."""
        sels = set(ids) & set(self.items)
        if not sels or (target_id is not None and (target_id in sels or target_id not in self.items)):
            return False
        block = [x for x in self.order if x in sels]
        rest = [x for x in self.order if x not in sels]
        if target_id is None:
            at = len(rest)
        else:
            at = rest.index(target_id) + (1 if after else 0)
        order = rest[:at] + block + rest[at:]
        if order == self.order:
            return False
        self.order = order
        self.orderChanged.emit()
        self._dirty()
        return True

    def move(self, ids: Iterable[str], how: str, visible: Optional[Iterable[str]] = None) -> bool:
        """Re-order the queue. how: up | down | top | bottom.

        `visible` = ids currently shown (a group filter): "up" jumps over the previous *visible*
        row, "top"/"bottom" go to the edge of the visible rows. Scheduling follows this order.
        """
        sels = set(ids) & set(self.items)
        if not sels:
            return False
        vis = set(visible) & set(self.items) if visible is not None else set(self.items)
        vis |= sels
        order = list(self.order)

        def vis_now() -> list[str]:
            return [x for x in order if x in vis]

        if how in ("up", "down"):
            seq = [x for x in order if x in sels]
            if how == "down":
                seq.reverse()
            for i in seq:
                v = vis_now()
                p = v.index(i)
                q = p - 1 if how == "up" else p + 1
                if not 0 <= q < len(v) or v[q] in sels:
                    continue  # already at the edge, or sits behind another selected row
                nb = v[q]
                order.remove(i)
                order.insert(order.index(nb) + (0 if how == "up" else 1), i)
        elif how in ("top", "bottom"):
            block = [x for x in order if x in sels]
            rest = [x for x in vis_now() if x not in sels]
            first_pos = order.index(block[0])
            for x in block:
                order.remove(x)
            if not rest:
                order[first_pos:first_pos] = block
            elif how == "top":
                order[order.index(rest[0]):order.index(rest[0])] = block
            else:
                at = order.index(rest[-1]) + 1
                order[at:at] = block
        else:
            return False

        if order == self.order:
            return False
        self.order = order
        self.orderChanged.emit()
        self._dirty()
        return True

    # ------------------------------------------------------------------ power (after all downloads)
    def set_power_mode(self, mode: str) -> None:
        mode = mode if mode in power.MODES else power.NONE
        if mode == self.power_mode:
            return
        self.power_mode = mode
        # armed while downloads are already running/queued -> they count as the activity to wait for
        self._power_activity = mode != power.NONE and (
            bool(self._cancel) or any(it.state in (QUEUED, DOWNLOADING) for it in self.items.values())
        )
        log.info(t("log.power_armed", mode=t(f"pow.{mode}")))
        self.powerModeChanged.emit(mode)

    def _maybe_all_finished(self) -> None:
        """Fire `allFinished` once the queue ran dry after real download activity."""
        if self.power_mode == power.NONE or not self._power_activity or self._cancel:
            return
        busy = any(
            it.state in (QUEUED, DOWNLOADING, PAUSED) or (it.state == RESOLVING and it.autostart)
            for it in self.items.values()
        )
        if busy:
            return
        mode, self.power_mode, self._power_activity = self.power_mode, power.NONE, False
        self.powerModeChanged.emit(power.NONE)
        self.allFinished.emit(mode)

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
        self._closing = True   # first: worker threads stop emitting into a dying engine
        self._stop_evt.set()
        for ev in self._cancel.values():
            ev.set()
        for it in self.items.values():
            if it.state in (QUEUED, DOWNLOADING):
                it.state, it.speed = PAUSED, 0.0
        self._tick.stop()
        self._save_timer.stop()
        self.save_now()
        # let workers finish so none of them drops the last reference to this QObject
        deadline = time.monotonic() + 3.0
        for th in list(self._threads):
            th.join(max(0.0, deadline - time.monotonic()))
