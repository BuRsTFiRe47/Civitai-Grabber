"""Global download speed limit shared by all running downloads (no Qt)."""
from __future__ import annotations

import threading
import time
from typing import Optional


class RateLimiter:
    """Paces reads so that, summed over all threads, throughput stays near `rate` bytes/s.

    rate <= 0 means unlimited. The limit can be changed at any time, also mid-download.
    """

    BURST = 0.25  # seconds of data that may go out ahead of the schedule

    def __init__(self, rate: float = 0.0):
        self._lock = threading.Lock()
        self._next = 0.0
        self.rate = float(rate)

    def set_rate(self, bytes_per_sec: float) -> None:
        with self._lock:
            self.rate = max(0.0, float(bytes_per_sec))
            self._next = 0.0

    def chunk_size(self, default: int) -> int:
        """Read size for the next attempt: small when the limit is low, so pausing stays responsive."""
        r = self.rate
        if r <= 0:
            return default
        return int(max(2048, min(default, r / 8)))

    def throttle(self, nbytes: int, cancel: Optional[threading.Event] = None) -> None:
        """Account for `nbytes` just received; sleeps (in short slices) when ahead of the limit."""
        r = self.rate
        if r <= 0 or nbytes <= 0:
            return
        with self._lock:
            now = time.monotonic()
            self._next = max(self._next, now) + nbytes / r
            wait = self._next - now - self.BURST
        while wait > 0:
            step = min(wait, 0.25)
            if cancel is not None:
                if cancel.wait(step):
                    return
            else:
                time.sleep(step)
            wait -= step
            if self.rate <= 0:  # limit switched off meanwhile
                return
