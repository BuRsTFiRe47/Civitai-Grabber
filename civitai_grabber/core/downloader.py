"""Resumable single-file downloader (no Qt). Used from worker threads."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import unquote, urlparse

import requests

from civitai_grabber.core.api import (
    CivitaiError,
    CloudflareBlocked,
    HashMismatch,
    HttpError,
    LoginRequired,
    RetryableError,
    classify_error_response,
    looks_like_cloudflare,
    response_info,
)
from civitai_grabber.core.logsetup import one_line, redact
from civitai_grabber.i18n import t

log = logging.getLogger("civgrab.dl")

CHUNK = 256 * 1024
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class DownloadCancelled(Exception):
    pass


def safe_filename(name: str) -> str:
    name = _BAD_CHARS.sub("_", name or "").strip().strip(".")
    return name[:180]


def filename_from_headers(headers, url: str) -> str:
    cd = headers.get("content-disposition", "") or ""
    m = re.search(r"filename\*\s*=\s*[^']*'[^']*'([^;]+)", cd, re.IGNORECASE)
    if m:
        return safe_filename(unquote(m.group(1).strip().strip('"')))
    m = re.search(r'filename\s*=\s*"?([^";]+)"?', cd, re.IGNORECASE)
    if m:
        return safe_filename(m.group(1).strip())
    base = os.path.basename(urlparse(url).path)
    return safe_filename(unquote(base))


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    n = 1
    while True:
        cand = path.with_name(f"{stem} ({n}){suffix}")
        if not cand.exists():
            return cand
        n += 1


def sha256_file(path: Path, cancel: Optional[threading.Event] = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(4 * 1024 * 1024)
            if not b:
                break
            if cancel is not None and cancel.is_set():
                raise DownloadCancelled()
            h.update(b)
    return h.hexdigest()


def _parse_content_range(value: str) -> tuple[int, int]:
    """'bytes 100-199/200' -> (start, total); '*/200' -> (-1, 200)."""
    m = re.match(r"bytes\s+(?:(\d+)-\d+|\*)/(\d+|\*)", value or "")
    if not m:
        return -1, 0
    start = int(m.group(1)) if m.group(1) else -1
    total = int(m.group(2)) if m.group(2) and m.group(2) != "*" else 0
    return start, total


def _finalize(part: Path, final: Path, sha256: str, verify: bool, cancel) -> Path:
    if verify and sha256:
        if sha256_file(part, cancel).lower() != sha256.lower():
            try:
                part.unlink()
            except OSError:
                pass
            raise HashMismatch()
    if final.exists():
        try:
            same = final.stat().st_size == part.stat().st_size
        except OSError:
            same = False
        if same:  # we already have this exact file
            part.unlink(missing_ok=True)
            return final
        final = unique_path(final)
    os.replace(part, final)
    return final


def _attempt(session, url, dest_dir, hint, part, expected_size, sha256, verify, progress, cancel, timeout, tag="") -> Path:
    pos = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={pos}-"} if pos else {}
    log.debug("%s GET %s range=%s", tag, redact(url), headers.get("Range", "-"))
    try:
        r = session.get(url, headers=headers, stream=True, timeout=timeout, allow_redirects=True)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise RetryableError(type(e).__name__, f"{type(e).__name__}: {one_line(str(e), 200)}") from e

    with r:
        log.debug("%s -> %s", tag, response_info(r))
        name = hint or filename_from_headers(r.headers, r.url) or "download.bin"
        final = dest_dir / safe_filename(name)

        if r.status_code == 416:
            start, total = _parse_content_range(r.headers.get("content-range", ""))
            if total and pos == total:
                return _finalize(part, final, sha256, verify, cancel)
            part.unlink(missing_ok=True)
            raise RetryableError("416", response_info(r))
        if r.status_code >= 400:
            raise classify_error_response(r)

        ctype = (r.headers.get("content-type") or "").lower()
        if "text/html" in ctype:
            snippet = next(r.iter_content(4096), b"")
            if looks_like_cloudflare(r.status_code, r.headers, snippet):
                raise CloudflareBlocked(str(r.status_code), response_info(r, snippet))
            # Civitai redirects to its login page for models that need an account
            raise LoginRequired("html", response_info(r, snippet))

        if r.status_code == 206:
            _, total = _parse_content_range(r.headers.get("content-range", ""))
            mode = "ab"
            done = pos
        else:
            total = int(r.headers.get("content-length") or 0)
            mode = "wb"
            if pos:
                log.warning("%s %s", tag, t("log.range_ignored"))
            done = 0  # server ignored Range -> restart from scratch
        if not total:
            total = expected_size
        progress(done, total)

        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(part, mode) as f:
                for chunk in r.iter_content(CHUNK):
                    if cancel.is_set():
                        raise DownloadCancelled()
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    progress(done, total)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            raise RetryableError(type(e).__name__, f"{type(e).__name__}: {one_line(str(e), 200)}") from e

    if total and done < total:
        raise RetryableError("incomplete", f"got {done} of {total} bytes")
    progress(done, total or done)
    return _finalize(part, final, sha256, verify, cancel)


def download(
    session: requests.Session,
    url: str,
    dest_dir: Path,
    filename_hint: str = "",
    *,
    expected_size: int = 0,
    sha256: str = "",
    verify: bool = False,
    retries: int = 3,
    progress: Callable[[int, int], None] = lambda d, t: None,
    cancel: Optional[threading.Event] = None,
    timeout=(15, 60),
    backoff: float = 2.0,
    tag: str = "",
) -> Path:
    """Download `url` into `dest_dir`, resuming `<name>.part` if present.

    Raises DownloadCancelled (pause/stop, the .part file is kept) or a CivitaiError.
    """
    cancel = cancel or threading.Event()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    hint = safe_filename(filename_hint)
    part_base = hint or ("download_" + hashlib.sha1(url.encode()).hexdigest()[:10])
    part = dest_dir / (part_base + ".part")

    resume = part.stat().st_size if part.exists() else 0
    log.info("%s %s", tag, t("log.dl_start", file=hint or "?", folder=str(dest_dir), resume=resume))
    t0 = time.monotonic()
    attempt = 0
    while True:
        try:
            path = _attempt(session, url, dest_dir, hint, part, expected_size, sha256, verify, progress, cancel, timeout, tag)
            dt = max(time.monotonic() - t0, 0.001)
            size = path.stat().st_size if path.exists() else 0
            log.info("%s %s", tag, t("log.dl_done", path=str(path), size=size, secs=f"{dt:.1f}",
                                     speed=f"{size / dt / 1048576:.1f}"))
            return path
        except DownloadCancelled:
            log.info("%s %s", tag, t("log.dl_paused", bytes=part.stat().st_size if part.exists() else 0))
            raise
        except (CloudflareBlocked, LoginRequired, HashMismatch):
            raise
        except RetryableError as e:
            if attempt >= retries:
                raise
            attempt += 1
            wait = backoff * (2 ** (attempt - 1))
            log.warning("%s %s", tag, t("log.dl_retry", n=attempt, total=retries, err=e.as_text(),
                                        secs=f"{wait:.0f}", info=e.info))
            if cancel.wait(wait):
                raise DownloadCancelled() from e
        except HttpError:
            raise
        except requests.RequestException as e:  # (is an OSError subclass, so catch first)
            raise HttpError(type(e).__name__) from e
        except OSError as e:
            raise HttpError(f"disk:{e.strerror or e}") from e
        except CivitaiError:
            raise
