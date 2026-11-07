"""Civitai link detection / parsing (no Qt, no network)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

_HOSTS = r"(?:www\.)?civitai\.(?:com|red|green)"
_URL_RE = re.compile(
    r"https?://" + _HOSTS + r"/[^\s<>\"'\]\)]+",
    re.IGNORECASE,
)
_TRAILING = ".,;:!?)]}>'\""


@dataclass(frozen=True)
class ParsedLink:
    """A recognised Civitai link.

    kind:
      "model"    -> https://civitai.com/models/<id>[/slug][?modelVersionId=<vid>]
      "version"  -> https://civitai.com/api/download/models/<vid>
                    https://civitai.com/model-versions/<vid>
    """

    url: str
    host: str
    kind: str
    model_id: Optional[int] = None
    version_id: Optional[int] = None

    @property
    def key(self) -> str:
        """Stable key used to de-duplicate links before they are resolved."""
        if self.version_id:
            return f"v{self.version_id}"
        return f"m{self.model_id}"


def parse_link(url: str) -> Optional[ParsedLink]:
    url = url.strip().rstrip(_TRAILING)
    try:
        u = urlparse(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower()
    if not re.fullmatch(_HOSTS, host):
        return None
    host = host.removeprefix("www.")
    path = u.path
    qs = parse_qs(u.query)

    m = re.fullmatch(r"/api/download/models/(\d+)/?", path)
    if m:
        return ParsedLink(url, host, "version", version_id=int(m.group(1)))

    m = re.fullmatch(r"/model-versions/(\d+)/?", path)
    if m:
        return ParsedLink(url, host, "version", version_id=int(m.group(1)))

    m = re.match(r"/models/(\d+)(?:/.*)?$", path)
    if m:
        vid = None
        for k in ("modelVersionId", "modelversionid"):
            if k in qs and qs[k] and qs[k][0].isdigit():
                vid = int(qs[k][0])
                break
        return ParsedLink(url, host, "model", model_id=int(m.group(1)), version_id=vid)
    return None


def extract_links(text: str) -> list[ParsedLink]:
    """Find every Civitai model / download link in arbitrary text (clipboard)."""
    out: list[ParsedLink] = []
    seen: set[str] = set()
    for raw in _URL_RE.findall(text or ""):
        p = parse_link(raw)
        if p and p.url not in seen:
            seen.add(p.url)
            out.append(p)
    return out
