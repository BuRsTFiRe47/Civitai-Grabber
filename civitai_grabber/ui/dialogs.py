"""Dialogs: paste links, assign/edit group, settings."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from civitai_grabber import APP_NAME, REPO_URL, __version__
from civitai_grabber.core.downloader import safe_filename
from civitai_grabber.core.models import Group
from civitai_grabber.core.storage import DEFAULT_UA, Settings
from civitai_grabber.i18n import t

NEW_GROUP = "__new__"


def pick_folder(parent: QWidget, title: str, start: str = "") -> str:
    return QFileDialog.getExistingDirectory(parent, title, start or str(Path.home()))


def _buttons(dlg: QDialog, ok_text: str | None = None) -> QDialogButtonBox:
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    box.button(QDialogButtonBox.Ok).setText(ok_text or t("btn.ok"))
    box.button(QDialogButtonBox.Cancel).setText(t("btn.cancel"))
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    return box


class _FolderRow(QWidget):
    def __init__(self, parent=None, title: str = ""):
        super().__init__(parent)
        self.title = title or t("dlg.pick_folder")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.btn = QPushButton(t("btn.browse"))
        self.btn.setAutoDefault(False)
        self.btn.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn)

    def _browse(self):
        p = pick_folder(self, self.title, self.edit.text())
        if p:
            self.edit.setText(p)

    def setEnabled(self, on: bool):  # noqa: N802
        self.edit.setEnabled(on)
        self.btn.setEnabled(on)


# --------------------------------------------------------------------------- paste links
class PasteLinksDialog(QDialog):
    def __init__(self, parent=None, prefill: str = ""):
        super().__init__(parent)
        self.setWindowTitle(t("dlg.paste_title"))
        self.resize(620, 380)
        lay = QVBoxLayout(self)
        lbl = QLabel(t("dlg.paste_hint"))
        lbl.setProperty("muted", True)
        lbl.setWordWrap(True)
        self.text = QPlainTextEdit()
        self.text.setPlainText(prefill)
        self.text.setPlaceholderText("https://civitai.com/models/12345/...")
        lay.addWidget(lbl)
        lay.addWidget(self.text, 1)
        lay.addWidget(_buttons(self, t("btn.add")))

    def value(self) -> str:
        return self.text.toPlainText()


# --------------------------------------------------------------------------- group
class GroupDialog(QDialog):
    """Create or edit one group (name + download folder)."""

    def __init__(self, parent=None, group: Optional[Group] = None, base_folder: str = ""):
        super().__init__(parent)
        self.setWindowTitle(t("dlg.group_edit") if group else t("dlg.group_new"))
        self.setMinimumWidth(520)
        self.base_folder = base_folder
        self._touched = bool(group and group.folder)
        form = QFormLayout(self)
        self.name = QLineEdit(group.name if group else "")
        self.folder = _FolderRow(title=t("dlg.pick_folder"))
        self.folder.edit.setText(group.folder if group else "")
        form.addRow(t("lbl.group_name"), self.name)
        form.addRow(t("lbl.folder"), self.folder)
        self.box = _buttons(self)
        form.addRow(self.box)
        self.name.textChanged.connect(self._name_changed)
        self.folder.edit.textEdited.connect(lambda _: setattr(self, "_touched", True))
        self._name_changed()

    def _name_changed(self):
        n = self.name.text().strip()
        self.box.button(QDialogButtonBox.Ok).setEnabled(bool(n))
        if not self._touched and self.base_folder and n:
            self.folder.edit.setText(str(Path(self.base_folder) / safe_filename(n)))

    def value(self) -> tuple[str, str]:
        return self.name.text().strip(), self.folder.edit.text().strip()


class AssignGroupDialog(QDialog):
    """Put the selected links into an existing group or a brand-new one."""

    def __init__(self, parent=None, groups: list[Group] | None = None, count: int = 0, base_folder: str = ""):
        super().__init__(parent)
        self.groups = groups or []
        self.base_folder = base_folder
        self._touched = False
        self._was_new = None
        self.setWindowTitle(t("dlg.assign_title", n=count))
        self.setMinimumWidth(540)
        form = QFormLayout(self)
        self.combo = QComboBox()
        for g in self.groups:
            self.combo.addItem(g.name, g.id)
        self.combo.addItem(t("dlg.new_group_item"), NEW_GROUP)
        self.name = QLineEdit()
        self.folder = _FolderRow(title=t("dlg.pick_folder"))
        form.addRow(t("lbl.group"), self.combo)
        form.addRow(t("lbl.group_name"), self.name)
        form.addRow(t("lbl.folder"), self.folder)
        self.box = _buttons(self, t("btn.move"))
        form.addRow(self.box)
        self.combo.currentIndexChanged.connect(self._sync)
        self.name.textChanged.connect(self._name_changed)
        self.folder.edit.textEdited.connect(lambda _: setattr(self, "_touched", True))
        if not self.groups:
            self.combo.setCurrentIndex(self.combo.count() - 1)
        self._sync()

    def _is_new(self) -> bool:
        return self.combo.currentData() == NEW_GROUP

    def _sync(self):
        new = self._is_new()
        self.name.setEnabled(new)
        self.folder.setEnabled(new)
        if new:
            if not self._was_new:  # coming from an existing group: start with empty fields
                self.name.clear()
                self.folder.edit.clear()
                self._touched = False
            self.name.setFocus()
            self._name_changed()
        else:
            g = next(x for x in self.groups if x.id == self.combo.currentData())
            self.name.setText(g.name)
            self.folder.edit.setText(g.folder)
            self.box.button(QDialogButtonBox.Ok).setEnabled(True)
        self._was_new = new

    def _name_changed(self):
        if not self._is_new():
            return
        n = self.name.text().strip()
        self.box.button(QDialogButtonBox.Ok).setEnabled(bool(n))
        if not self._touched and self.base_folder and n:
            self.folder.edit.setText(str(Path(self.base_folder) / safe_filename(n)))

    def result_group(self) -> tuple[Optional[str], str, str]:
        """(existing group id or None, name, folder)"""
        if self._is_new():
            return None, self.name.text().strip(), self.folder.edit.text().strip()
        return self.combo.currentData(), "", ""


# --------------------------------------------------------------------------- settings
class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None, config_path: str = ""):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle(t("dlg.settings_title"))
        self.resize(680, 500)
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        # --- general
        gen = QWidget()
        f = QFormLayout(gen)
        self.api = QLineEdit(settings.api_key)
        self.api.setEchoMode(QLineEdit.Password)
        self.api.setPlaceholderText(t("ph.api_key"))
        show = QCheckBox(t("lbl.show"))
        show.toggled.connect(lambda on: self.api.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.api, 1)
        rl.addWidget(show)
        f.addRow(t("lbl.api_key"), row)
        hint = QLabel(t("hint.api_key"))
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        f.addRow("", hint)
        self.default_folder = _FolderRow(title=t("dlg.pick_folder"))
        self.default_folder.edit.setText(settings.default_folder)
        f.addRow(t("lbl.default_folder"), self.default_folder)
        self.base_folder = _FolderRow(title=t("dlg.pick_folder"))
        self.base_folder.edit.setText(settings.base_folder)
        f.addRow(t("lbl.base_folder"), self.base_folder)
        bh = QLabel(t("hint.base_folder"))
        bh.setProperty("muted", True)
        bh.setWordWrap(True)
        f.addRow("", bh)
        self.lang = QComboBox()
        self.lang.addItem("Türkçe", "tr")
        self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(0 if settings.language == "tr" else 1)
        f.addRow(t("lbl.language"), self.lang)
        self.theme = QComboBox()
        self.theme.addItem(t("opt.dark"), "dark")
        self.theme.addItem(t("opt.light"), "light")
        self.theme.setCurrentIndex(0 if settings.theme == "dark" else 1)
        f.addRow(t("lbl.theme"), self.theme)
        self.monitor = QCheckBox(t("lbl.monitor"))
        self.monitor.setChecked(settings.monitor_clipboard)
        f.addRow("", self.monitor)
        tabs.addTab(gen, t("tab.general"))

        # --- downloads
        dl = QWidget()
        f2 = QFormLayout(dl)
        self.conc = QSpinBox()
        self.conc.setRange(1, 8)
        self.conc.setValue(settings.max_concurrent)
        f2.addRow(t("lbl.concurrent"), self.conc)
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 60)
        self.delay.setSingleStep(0.5)
        self.delay.setSuffix(" s")
        self.delay.setValue(settings.start_delay)
        f2.addRow(t("lbl.delay"), self.delay)
        self.retries = QSpinBox()
        self.retries.setRange(0, 10)
        self.retries.setValue(settings.retries)
        f2.addRow(t("lbl.retries"), self.retries)
        self.exts = QLineEdit(settings.file_extensions)
        self.exts.setPlaceholderText("safetensors, pt")
        f2.addRow(t("lbl.file_extensions"), self.exts)
        eh = QLabel(t("hint.file_extensions"))
        eh.setProperty("muted", True)
        eh.setWordWrap(True)
        f2.addRow("", eh)
        self.skip = QCheckBox(t("lbl.skip_existing"))
        self.skip.setChecked(settings.skip_existing)
        f2.addRow("", self.skip)
        self.stopcf = QCheckBox(t("lbl.stop_on_cf"))
        self.stopcf.setChecked(settings.stop_on_cloudflare)
        f2.addRow("", self.stopcf)
        sh = QLabel(t("hint.cf_queue"))
        sh.setProperty("muted", True)
        sh.setWordWrap(True)
        f2.addRow("", sh)
        self.verify = QCheckBox(t("lbl.verify"))
        self.verify.setChecked(settings.verify_sha256)
        f2.addRow("", self.verify)
        dh = QLabel(t("hint.delay"))
        dh.setProperty("muted", True)
        dh.setWordWrap(True)
        f2.addRow("", dh)
        tabs.addTab(dl, t("tab.downloads"))

        # --- advanced / cloudflare
        adv = QWidget()
        f3 = QFormLayout(adv)
        self.ua = QLineEdit(settings.user_agent)
        f3.addRow(t("lbl.user_agent"), self.ua)
        reset = QPushButton(t("btn.reset_ua"))
        reset.setAutoDefault(False)
        reset.clicked.connect(lambda: self.ua.setText(DEFAULT_UA))
        f3.addRow("", reset)
        self.cookie = QLineEdit(settings.cookie)
        self.cookie.setPlaceholderText("cf_clearance=...")
        f3.addRow(t("lbl.cookie"), self.cookie)
        ah = QLabel(t("hint.cloudflare"))
        ah.setProperty("muted", True)
        ah.setWordWrap(True)
        f3.addRow("", ah)
        tabs.addTab(adv, t("tab.advanced"))

        about = QLabel(f"{APP_NAME} v{__version__} — <a href='{REPO_URL}'>{REPO_URL.removeprefix('https://')}</a>")
        about.setOpenExternalLinks(True)
        about.setProperty("muted", True)
        about.setTextInteractionFlags(Qt.TextBrowserInteraction)
        lay.addWidget(about)
        if config_path:
            cp = QLabel(f"{t('lbl.config_dir')}: {config_path}")
            cp.setProperty("muted", True)
            cp.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(cp)
        lay.addWidget(_buttons(self))

    def value(self) -> Settings:
        return dataclasses.replace(
            self.s,
            api_key=self.api.text().strip(),
            default_folder=self.default_folder.edit.text().strip(),
            base_folder=self.base_folder.edit.text().strip(),
            language=self.lang.currentData(),
            theme=self.theme.currentData(),
            monitor_clipboard=self.monitor.isChecked(),
            max_concurrent=self.conc.value(),
            start_delay=self.delay.value(),
            retries=self.retries.value(),
            verify_sha256=self.verify.isChecked(),
            file_extensions=self.exts.text().strip(),
            skip_existing=self.skip.isChecked(),
            stop_on_cloudflare=self.stopcf.isChecked(),
            user_agent=self.ua.text().strip() or DEFAULT_UA,
            cookie=self.cookie.text().strip(),
        )


# --------------------------------------------------------------------------- power countdown
class PowerCountdownDialog(QDialog):
    """Shown when all downloads are done: counts down, then accepts (= run the action)."""

    def __init__(self, mode: str, seconds: int = 60, parent=None):
        super().__init__(parent)
        self.mode, self.left = mode, seconds
        self.setWindowTitle(t("pow.title"))
        self.setModal(True)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        self.lbl = QLabel()
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)
        row = QHBoxLayout()
        self.b_now = QPushButton(t("pow.now"))
        self.b_cancel = QPushButton(t("pow.cancel"))
        self.b_cancel.setDefault(True)   # Enter / Space cancels, never confirms
        self.b_now.setAutoDefault(False)
        row.addStretch(1)
        row.addWidget(self.b_now)
        row.addWidget(self.b_cancel)
        lay.addLayout(row)
        self.b_now.clicked.connect(self.accept)
        self.b_cancel.clicked.connect(self.reject)
        self.timer = QTimer(self, interval=1000)
        self.timer.timeout.connect(self.tick)
        self._render()
        self.timer.start()

    def _render(self):
        self.lbl.setText(t(f"pow.msg_{self.mode}", secs=max(self.left, 0)))

    def tick(self):
        self.left -= 1
        self._render()
        if self.left <= 0:
            self.timer.stop()
            self.accept()

    def done(self, r):
        self.timer.stop()
        super().done(r)
