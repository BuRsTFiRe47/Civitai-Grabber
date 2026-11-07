"""Log panel: live view of the 'civgrab' logger with level + text filter."""
from __future__ import annotations

import html
import logging
import time
from collections import deque
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from civitai_grabber.core.logsetup import LOGGER_NAME, BufferHandler, redact
from civitai_grabber.i18n import t
from civitai_grabber.ui import theme

_LEVELS = (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
MAX_LINES = 5000


class _Bridge(QObject):
    line = Signal(float, int, str)  # created, levelno, text  (emitted from worker threads)


class _QtHandler(logging.Handler):
    def __init__(self, bridge: _Bridge):
        super().__init__(logging.DEBUG)
        self.bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.bridge.line.emit(record.created, record.levelno, redact(record.getMessage()))
        except Exception:  # noqa: BLE001 - never let logging break a worker thread
            pass


class LogPanel(QWidget):
    def __init__(self, buffer: Optional[BufferHandler] = None, log_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.log_dir = log_dir
        self._lines: deque[tuple[float, int, str]] = deque(buffer.records if buffer else (), maxlen=MAX_LINES)

        top = QHBoxLayout()
        self.level = QComboBox()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.b_clear, self.b_copy, self.b_folder = QPushButton(), QPushButton(), QPushButton()
        for b in (self.b_clear, self.b_copy, self.b_folder):
            b.setAutoDefault(False)
        top.addWidget(self.level)
        top.addWidget(self.search, 1)
        top.addWidget(self.b_clear)
        top.addWidget(self.b_copy)
        top.addWidget(self.b_folder)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.view.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.view.setMaximumBlockCount(MAX_LINES + 100)
        self.lbl_file = QLabel()
        self.lbl_file.setProperty("muted", True)
        self.lbl_file.setTextInteractionFlags(Qt.TextSelectableByMouse)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addLayout(top)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.lbl_file)

        self.level.currentIndexChanged.connect(self._render_all)
        self.search.textChanged.connect(self._render_all)
        self.b_clear.clicked.connect(self._clear)
        self.b_copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.view.toPlainText()))
        self.b_folder.clicked.connect(self._open_folder)

        # live records
        # no Qt parent: worker threads may still be emitting while the panel is being destroyed;
        # Qt drops the connection itself when the receiving panel dies
        self._bridge = _Bridge()
        self._bridge.line.connect(self._on_line)
        self._handler = _QtHandler(self._bridge)
        logging.getLogger(LOGGER_NAME).addHandler(self._handler)
        self.destroyed.connect(lambda *_: logging.getLogger(LOGGER_NAME).removeHandler(self._handler))

        self.retranslate()
        self.level.setCurrentIndex(1)  # Info by default
        self._render_all()

    # ------------------------------------------------------------------ public
    def retranslate(self):
        cur = self.level.currentIndex()
        self.level.blockSignals(True)
        self.level.clear()
        for k in ("debug", "info", "warn", "error"):
            self.level.addItem(t(f"logui.level_{k}"))
        self.level.setCurrentIndex(max(cur, 0))
        self.level.blockSignals(False)
        self.search.setPlaceholderText(t("logui.search"))
        self.b_clear.setText(t("logui.clear"))
        self.b_copy.setText(t("logui.copy"))
        self.b_folder.setText(t("logui.open_folder"))
        self.lbl_file.setText(t("logui.file", path=str(self.log_dir / "civitai-grabber.log")) if self.log_dir else "")

    def show_only(self, text: str, detailed: bool = True):
        """Filter to lines containing `text` (e.g. a row code like '#a1b2c3')."""
        self.level.blockSignals(True)
        self.level.setCurrentIndex(0 if detailed else 1)
        self.level.blockSignals(False)
        self.search.setText(text)  # triggers the re-render
        self._render_all()

    # ------------------------------------------------------------------ internals
    def _matches(self, level: int, text: str) -> bool:
        if level < _LEVELS[max(self.level.currentIndex(), 0)]:
            return False
        q = self.search.text().strip().lower()
        return not q or q in text.lower()

    def _fmt(self, created: float, level: int, text: str) -> str:
        c = theme.colors()
        color = {logging.ERROR: c["err"], logging.CRITICAL: c["err"], logging.WARNING: c["warn"],
                 logging.DEBUG: c["muted"]}.get(level, c["text"])
        stamp = time.strftime("%H:%M:%S", time.localtime(created))
        return f'<span style="color:{c["muted"]}">{stamp}</span> <span style="color:{color}">{html.escape(text)}</span>'

    def _on_line(self, created: float, level: int, text: str):
        self._lines.append((created, level, text))
        if self._matches(level, text):
            bar = self.view.verticalScrollBar()
            at_end = bar.value() >= bar.maximum() - 4
            self.view.appendHtml(self._fmt(created, level, text))
            if at_end:
                bar.setValue(bar.maximum())

    def _render_all(self, *_):
        self.view.setUpdatesEnabled(False)
        self.view.clear()
        chunks = [self._fmt(*rec) for rec in self._lines if self._matches(rec[1], rec[2])]
        if chunks:
            self.view.appendHtml("<br>".join(chunks))
        self.view.setUpdatesEnabled(True)
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _clear(self):
        self._lines.clear()
        self.view.clear()

    def _open_folder(self):
        if self.log_dir and self.log_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_dir)))
