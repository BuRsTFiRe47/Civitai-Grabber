"""Logging: rotating file + in-memory ring buffer. Secrets are never logged."""
from __future__ import annotations

import logging
import re
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "civgrab"
LOG_FILE = "civitai-grabber.log"

log = logging.getLogger(LOGGER_NAME)
log.addHandler(logging.NullHandler())  # silent until setup_logging() / in tests

_SECRET_QS = re.compile(r"([?&](?:token|api_key|apikey|key|access_token)=)[^&\s#]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Hide API keys / tokens that may sit in URLs."""
    return _SECRET_QS.sub(r"\1***", text or "")


def one_line(text: str, limit: int = 160) -> str:
    s = re.sub(r"\s+", " ", text or "").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


class BufferHandler(logging.Handler):
    """Keeps the last N records so a log panel opened later can show them."""

    def __init__(self, capacity: int = 4000):
        super().__init__(level=logging.DEBUG)
        self.records: deque[tuple[float, int, str]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.records.append((record.created, record.levelno, redact(record.getMessage())))
        except Exception:  # noqa: BLE001 - logging must never break the app
            pass


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(log_dir: Path) -> BufferHandler:
    """(Re)configure the 'civgrab' logger. Returns the in-memory buffer."""
    for h in list(log.handlers):
        log.removeHandler(h)
        try:
            h.close()
        except Exception:  # noqa: BLE001
            pass
    log.setLevel(logging.DEBUG)
    log.propagate = False
    buf = BufferHandler()
    log.addHandler(buf)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_dir / LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(RedactingFormatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
        log.addHandler(fh)
    except OSError:
        pass  # no log file is not fatal; the panel still works
    return buf
