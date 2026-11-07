"""'When all downloads are finished' actions: hibernate / shut down (best effort, per OS)."""
from __future__ import annotations

import subprocess
import sys
from typing import Optional

NONE = "none"
HIBERNATE = "hibernate"
SHUTDOWN = "shutdown"
MODES = (NONE, HIBERNATE, SHUTDOWN)


def command_for(mode: str, platform: Optional[str] = None) -> Optional[list[str]]:
    """The OS command for `mode`, or None (mode none / unsupported platform)."""
    platform = platform or sys.platform
    if mode not in (HIBERNATE, SHUTDOWN):
        return None
    if platform == "win32":
        # hibernate needs hibernation enabled (`powercfg /hibernate on`); no /f on shutdown so
        # unsaved work in other programs is not thrown away silently.
        return ["shutdown", "/h"] if mode == HIBERNATE else ["shutdown", "/s", "/t", "0"]
    if platform == "darwin":
        # macOS has no plain hibernate command: sleep is the closest
        if mode == HIBERNATE:
            return ["pmset", "sleepnow"]
        return ["osascript", "-e", 'tell application "System Events" to shut down']
    return ["systemctl", "hibernate"] if mode == HIBERNATE else ["systemctl", "poweroff"]


def run(mode: str) -> list[str]:
    """Execute the action. Returns the command; raises OSError/CalledProcessError on failure."""
    cmd = command_for(mode)
    if cmd is None:
        raise ValueError(f"no power command for mode {mode!r} on {sys.platform}")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    subprocess.run(cmd, check=True, capture_output=True, timeout=30, creationflags=flags)
    return cmd
