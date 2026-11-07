"""Application entry point."""
from __future__ import annotations

import logging
import sys
import threading

from PySide6 import __version__ as pyside_version
from PySide6.QtWidgets import QApplication

from civitai_grabber import APP_NAME, __version__
from civitai_grabber.core.logsetup import setup_logging
from civitai_grabber.core.engine import Engine
from civitai_grabber.core.storage import LAST_MIGRATION, Storage
from civitai_grabber.i18n import set_language, t
from civitai_grabber.ui import theme
from civitai_grabber.ui.main_window import MainWindow


def _hook_exceptions(log: logging.Logger) -> None:
    """Send uncaught exceptions (GUI slots and worker threads) to the log file as well."""
    old = sys.excepthook

    def hook(exc_type, exc, tb):
        log.error("Uncaught exception", exc_info=(exc_type, exc, tb))
        old(exc_type, exc, tb)

    sys.excepthook = hook

    def thread_hook(args):
        log.error("Uncaught exception in thread %s", getattr(args.thread, "name", "?"),
                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = thread_hook


def _report_migration(log: logging.Logger) -> bool:
    """Write what config_dir() did (import from the old folder / fallback) to the log."""
    m = LAST_MIGRATION
    if m.get("fallback"):
        log.warning(t("log.config_fallback", target=m.get("target", ""), path=m["fallback"]))
    if m.get("error"):
        log.error(t("log.migrate_failed", err=m["error"], src=m.get("source", "")))
    if m.get("moved"):
        log.info(t("log.migrated", src=m["source"], dst=m["target"], moved=", ".join(m["moved"])))
        if m.get("left"):
            log.warning(t("log.migrated_left", left=", ".join(m["left"])))
        return not m.get("left")
    return False


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("BuRsTFiRe47")

    storage = Storage()
    log_buffer = setup_logging(storage.base / "logs")
    log = logging.getLogger("civgrab.app")
    log.info("%s %s | python %s | PySide6 %s | %s", APP_NAME, __version__, sys.version.split()[0], pyside_version, storage.base)
    _hook_exceptions(log)
    settings = storage.load_settings()
    set_language(settings.language)
    migrated = _report_migration(log)
    theme.apply_theme(app, settings.theme)  # dark unless the user changed it

    engine = Engine(storage, settings)
    win = MainWindow(engine, log_buffer)
    win.show()
    if migrated:
        win.statusBar().showMessage(t("msg.migrated"), 15000)
    engine.begin()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
