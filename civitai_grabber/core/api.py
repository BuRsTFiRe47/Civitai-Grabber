"""Civitai REST helpers: HTTP session, error classification, link resolving."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import PurePosixPath
from typing import Optional, Sequence

import requests

from civitai_grabber.core.logsetup import one_line, redact
from civitai_grabber.core.storage import Settings
from civitai_grabber.i18n import t

TIMEOUT = (15, 60)  # connect, read
SCHEME = "https"    # tests point this at a local http server

log = logging.getLogger("civgrab.api")


# --------------------------------------------------------------------------- errors
class CivitaiError(Exception):
    """Base error. `code` is translated by the UI; `detail` is short extra text;
    `info` carries technical details (HTTP status, headers) for the log / tooltip."""

    code = "unknown"

    def __init__(self, detail: str = "", info: str = ""):
        super().__init__(detail or self.code)
        self.detail = detail
        self.info = info

    def as_text(self) -> str:
        return f"{self.code}:{self.detail}" if self.detail else self.code


class CloudflareBlocked(CivitaiError):
    code = "cloudflare"


class LoginRequired(CivitaiError):
    code = "login"


class NotFound(CivitaiError):
    code = "notfound"


class HttpError(CivitaiError):
    code = "http"


class RetryableError(CivitaiError):
    code = "network"


class HashMismatch(CivitaiError):
    code = "hash"


class NoMatchingFile(CivitaiError):
    """The version has no file with an allowed extension. `detail` lists what it does have."""

    code = "nofile"


# --------------------------------------------------------------------------- session
def make_session(settings: Settings, host: str = "civitai.com") -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = settings.user_agent or "Mozilla/5.0"
    s.headers["Accept"] = "*/*"
    if settings.api_key.strip():
        # requests drops Authorization on a redirect to another host (storage CDN)
        s.headers["Authorization"] = f"Bearer {settings.api_key.strip()}"
    if settings.cookie.strip():
        jar = SimpleCookie()
        try:
            jar.load(settings.cookie.strip())
        except Exception:
            jar = SimpleCookie()
        for name, morsel in jar.items():
            # scoped to the Civitai host so it is never sent to the CDN
            s.cookies.set(name, morsel.value, domain=host, path="/")
    return s


def looks_like_cloudflare(status: int, headers, body: bytes = b"") -> bool:
    h = {k.lower(): str(v) for k, v in dict(headers).items()}
    if h.get("cf-mitigated", "").lower() == "challenge":
        return True
    if status in (403, 429, 503) and "cloudflare" in h.get("server", "").lower():
        snip = (body or b"")[:4096].lower()
        return any(
            m in snip
            for m in (b"just a moment", b"cf-chl", b"attention required", b"challenge-platform", b"cloudflare")
        )
    return False


_INFO_HEADERS = ("server", "content-type", "content-length", "cf-mitigated", "cf-ray", "retry-after", "location")


def response_info(resp: requests.Response, snippet: bytes = b"") -> str:
    """One-line technical summary of a response, safe to show/log (no cookies, no secrets)."""
    parts = [f"HTTP {resp.status_code}"]
    for k in _INFO_HEADERS:
        v = resp.headers.get(k)
        if v:
            parts.append(f"{k}={one_line(v, 80)}")
    parts.append(f"url={redact(resp.url)}")
    if snippet:
        text = snippet.decode("utf-8", "replace")
        if "<title>" in text.lower():  # prefer the page title of HTML error pages
            i = text.lower().index("<title>") + 7
            text = text[i:text.lower().find("</title>", i)]
        parts.append(f"body='{one_line(text, 100)}'")
    return " · ".join(parts)


def classify_error_response(resp: requests.Response) -> CivitaiError:
    """Turn a bad HTTP response into one of our errors (reads a tiny body snippet)."""
    try:
        snippet = next(resp.iter_content(4096), b"")
    except Exception:
        snippet = b""
    info = response_info(resp, snippet)
    if looks_like_cloudflare(resp.status_code, resp.headers, snippet):
        return CloudflareBlocked(str(resp.status_code), info)
    code = resp.status_code
    if code in (401, 403):
        return LoginRequired(str(code), info)
    if code == 404:
        return NotFound("", info)
    if code == 429 or code >= 500:
        return RetryableError(str(code), info)
    return HttpError(str(code), info)


# --------------------------------------------------------------------------- API
def _api_get(session: requests.Session, host: str, path: str, tag: str = "") -> dict:
    url = f"{SCHEME}://{host}/api/v1/{path}"
    log.debug("%s GET %s", tag, url)
    try:
        r = session.get(url, timeout=TIMEOUT)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise RetryableError(type(e).__name__, f"{type(e).__name__}: {one_line(str(e), 200)}") from e
    with r:
        if r.status_code >= 400:
            raise classify_error_response(r)
        log.debug("%s -> %s", tag, response_info(r))
        try:
            return r.json()
        except ValueError:
            if looks_like_cloudflare(r.status_code, r.headers, r.content[:4096]):
                raise CloudflareBlocked(str(r.status_code), response_info(r, r.content[:4096]))
            raise HttpError("bad-json", response_info(r, r.content[:200]))


def _ext(f: dict) -> str:
    return PurePosixPath(str(f.get("name") or "")).suffix.lower().lstrip(".")


def pick_file(files: list[dict], allowed: Sequence[str] = ()) -> Optional[dict]:
    """Choose which file of a version to download.

    With `allowed` (e.g. ['safetensors', 'pt']) only those extensions qualify; the order of
    `allowed` is the preference, then Civitai's "primary" flag. Raises NoMatchingFile if the
    version has files but none qualifies. Without `allowed`: primary / first "Model" / first.
    """
    if not files:
        return None
    allowed = [a.lower().lstrip(".") for a in allowed if a and a.strip()]
    if allowed:
        cands = [f for f in files if _ext(f) in allowed and f.get("type") != "Training Data"]
        if not cands:
            names = ", ".join(str(f.get("name") or "?") for f in files)
            raise NoMatchingFile(one_line(names, 120), f"allowed={','.join(allowed)} files={names}")
        cands.sort(key=lambda f: (allowed.index(_ext(f)), not f.get("primary")))
        return cands[0]
    for f in files:
        if f.get("primary"):
            return f
    for f in files:
        if f.get("type") == "Model":
            return f
    return files[0]


@dataclass
class Resolved:
    model_id: Optional[int]
    version_id: Optional[int]
    name: str
    version_name: str
    creator: str
    model_type: str
    base_model: str
    filename: str
    download_url: str
    size: int
    sha256: str


def resolve(
    session: requests.Session,
    host: str,
    model_id: Optional[int],
    version_id: Optional[int],
    allowed_exts: Sequence[str] = (),
    tag: str = "",
) -> Resolved:
    """Look up model/version metadata. Needs either a model id or a version id."""
    if version_id:
        v = _api_get(session, host, f"model-versions/{version_id}", tag)
        model = v.get("model") or {}
        model_id = v.get("modelId") or model_id
        name = model.get("name") or ""
        mtype = model.get("type") or ""
        creator = ((v.get("creator") or {}).get("username")) or ""
        if not creator and model_id:
            try:  # creator is not always part of the version payload
                m = _api_get(session, host, f"models/{model_id}", tag)
                creator = ((m.get("creator") or {}).get("username")) or ""
                name = name or m.get("name") or ""
                mtype = mtype or m.get("type") or ""
            except NotFound:
                pass
    elif model_id:
        m = _api_get(session, host, f"models/{model_id}", tag)
        versions = m.get("modelVersions") or []
        if not versions:
            raise NotFound("no-versions")
        v = versions[0]  # newest first
        version_id = v.get("id")
        name = m.get("name") or ""
        mtype = m.get("type") or ""
        creator = ((m.get("creator") or {}).get("username")) or ""
    else:
        raise NotFound("no-id")

    files = v.get("files") or []
    try:
        f = pick_file(files, allowed_exts)
    except NoMatchingFile:
        log.warning("%s %s", tag, t("log.no_matching_file", allowed=",".join(allowed_exts),
                                    files=", ".join(str(x.get("name")) for x in files)))
        raise
    if f and len(files) > 1:
        skipped = [str(x.get("name")) for x in files if x is not f]
        log.info("%s %s", tag, t("log.file_chosen", file=f.get("name"), others=", ".join(skipped)))
    dl = (f or {}).get("downloadUrl") or v.get("downloadUrl") or f"{SCHEME}://{host}/api/download/models/{version_id}"
    hashes = (f or {}).get("hashes") or {}
    return Resolved(
        model_id=model_id,
        version_id=version_id,
        name=name,
        version_name=v.get("name") or "",
        creator=creator,
        model_type=mtype,
        base_model=v.get("baseModel") or "",
        filename=(f or {}).get("name") or "",
        download_url=dl,
        size=int(float((f or {}).get("sizeKB") or 0) * 1024),
        sha256=str(hashes.get("SHA256") or "").lower(),
    )
