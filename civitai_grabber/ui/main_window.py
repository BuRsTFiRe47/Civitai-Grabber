"""Main window: group list on the left, link table on the right (JDownloader-style)."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QModelIndex, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from civitai_grabber import APP_NAME
from civitai_grabber.core.engine import Engine
from civitai_grabber.core.links import extract_links
from civitai_grabber.core.models import ERROR, PAUSED, READY, RESOLVING
from civitai_grabber.i18n import set_language, t
from civitai_grabber.core.logsetup import BufferHandler
from civitai_grabber.ui import theme
from civitai_grabber.ui.log_panel import LogPanel
from civitai_grabber.ui.dialogs import (
    AssignGroupDialog,
    GroupDialog,
    PasteLinksDialog,
    SettingsDialog,
    pick_folder,
)
from civitai_grabber.ui.table_model import (
    COL_PROGRESS,
    COLS,
    MIME,
    FilterProxy,
    IdRole,
    ItemModel,
    ProgressDelegate,
    format_size,
)

ALL = "__all__"
NONE = "__none__"


class GroupList(QListWidget):
    """Group list that accepts rows dragged from the link table."""

    itemsDropped = Signal(list, str)  # ids, group token

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDropIndicatorShown(False)

    def _target(self, event) -> Optional[QListWidgetItem]:
        it = self.itemAt(event.position().toPoint())
        return it if it is not None and it.data(Qt.UserRole) != ALL else None

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME) and self._target(e) is not None:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        it = self._target(e)
        if it is None or not e.mimeData().hasFormat(MIME):
            e.ignore()
            return
        ids = bytes(e.mimeData().data(MIME)).decode().split("\n")
        self.itemsDropped.emit([i for i in ids if i], it.data(Qt.UserRole))
        e.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine, log_buffer: Optional[BufferHandler] = None):
        super().__init__()
        self.engine = engine
        self._log_buffer = log_buffer
        self.setWindowIcon(theme.app_icon())
        self.resize(1440, 780)
        self.setAcceptDrops(True)

        self.model = ItemModel(engine, self)
        self.proxy = FilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self._build_actions()
        self._build_ui()
        self._apply_texts()

        engine.groupsChanged.connect(self._refresh_groups_soon)
        engine.message.connect(self._on_message)
        engine.itemChanged.connect(lambda _id: self._update_selection_actions())
        self.model.rowsInserted.connect(self._update_empty)
        self.model.rowsRemoved.connect(self._update_empty)

        self._groups_timer = QTimer(self, singleShot=True, interval=0)
        self._groups_timer.timeout.connect(self._refresh_groups)
        self._status_timer = QTimer(self, interval=1000)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start()

        self._refresh_groups()
        self._update_empty()
        self._update_status()

        self._clip = QGuiApplication.clipboard()
        self._clip.dataChanged.connect(self._on_clipboard)

        geo = engine.settings.geometry
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))

    # ------------------------------------------------------------------ build
    def _build_actions(self):
        mk = lambda: QAction(self)  # noqa: E731
        self.a_add, self.a_monitor = mk(), mk()
        self.a_monitor.setCheckable(True)
        self.a_monitor.setChecked(self.engine.settings.monitor_clipboard)
        self.a_monitor.toggled.connect(self._toggle_monitor)
        self.a_add.triggered.connect(self._add_dialog)
        self.a_start_sel, self.a_start_view, self.a_pause = mk(), mk(), mk()
        self.a_start_sel.triggered.connect(lambda: self._start(self._selected_ids()))
        self.a_start_view.triggered.connect(lambda: self._start(self._view_ids()))
        self.a_pause.triggered.connect(self._pause)
        self.a_group, self.a_autogroup = mk(), mk()
        self.a_group.setShortcut(QKeySequence("Ctrl+G"))
        self.a_group.triggered.connect(self._group_selected)
        self.a_autogroup.triggered.connect(self._autogroup)
        self.a_remove, self.a_clear, self.a_settings = mk(), mk(), mk()
        self.a_log = mk()
        self.a_log.setCheckable(True)
        self.a_log.toggled.connect(lambda on: self.log_dock.setVisible(on))
        self.a_remove.setShortcut(QKeySequence.Delete)
        self.a_remove.triggered.connect(self._remove_selected)
        self.a_clear.triggered.connect(self.engine.clear_finished)
        self.a_settings.triggered.connect(self._open_settings)
        self.a_paste = mk()
        self.a_paste.setShortcut(QKeySequence.Paste)
        self.a_paste.triggered.connect(lambda: self._grab_text(self._clip.text(), notify=True))
        self.addAction(self.a_paste)
        self.addAction(self.a_remove)
        self.addAction(self.a_group)

    def _build_ui(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)
        self.toolbar = tb
        for a in (self.a_add, self.a_monitor):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.a_start_sel, self.a_start_view, self.a_pause):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.a_group, self.a_autogroup):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.a_remove, self.a_clear):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.a_log)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        tb.addWidget(spacer)
        tb.addAction(self.a_settings)

        # left: groups
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 0, 10)
        self.lbl_groups = QLabel()
        self.lbl_groups.setProperty("muted", True)
        self.group_list = GroupList()
        self.group_list.currentItemChanged.connect(self._group_selected_in_list)
        self.group_list.itemsDropped.connect(self._on_drop)
        self.group_list.itemDoubleClicked.connect(lambda *_: self._edit_group())
        self.group_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_list.customContextMenuRequested.connect(self._group_menu)
        gb = QHBoxLayout()
        self.b_new = QPushButton()
        self.b_edit = QPushButton()
        self.b_del = QPushButton()
        for b in (self.b_new, self.b_edit, self.b_del):
            b.setAutoDefault(False)
            gb.addWidget(b)
        self.b_new.clicked.connect(self._new_group)
        self.b_edit.clicked.connect(self._edit_group)
        self.b_del.clicked.connect(self._delete_group)
        ll.addWidget(self.lbl_groups)
        ll.addWidget(self.group_list, 1)
        ll.addLayout(gb)
        left.setMinimumWidth(220)
        left.setMaximumWidth(380)

        # right: table (or empty hint)
        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(-1, Qt.AscendingOrder)  # keep insertion order until a header is clicked
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setDragEnabled(True)
        self.view.setDragDropMode(QAbstractItemView.DragOnly)
        self.view.setShowGrid(False)
        self.view.setWordWrap(False)
        self.view.setTextElideMode(Qt.ElideRight)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(34)
        self.view.setItemDelegateForColumn(COL_PROGRESS, ProgressDelegate(self.view))
        h = self.view.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setStretchLastSection(False)
        h.setMinimumSectionSize(60)
        h.setSectionResizeMode(COLS.index("name"), QHeaderView.Stretch)
        for name, w in (("version", 75), ("creator", 115), ("type", 90), ("size", 90), ("group", 115),
                        ("status", 165), ("progress", 110), ("speed", 85)):
            self.view.setColumnWidth(COLS.index(name), w)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._table_menu)
        self.view.doubleClicked.connect(self._open_item)
        self.view.selectionModel().selectionChanged.connect(lambda *_: self._update_selection_actions())

        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setProperty("muted", True)
        self.empty.setWordWrap(True)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.view)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 10, 10, 10)
        rl.addWidget(self.stack)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([240, 1200])
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)

        sb = self.statusBar()
        self.lbl_key = QLabel()
        self.lbl_counts = QLabel()
        self.lbl_speed = QLabel()
        sb.addPermanentWidget(self.lbl_key)
        sb.addPermanentWidget(self.lbl_counts)
        sb.addPermanentWidget(self.lbl_speed)

        # log dock (hidden until the Log button is pressed)
        self.log_panel = LogPanel(self._log_buffer, self.engine.storage.base / "logs")
        self.log_dock = QDockWidget(self)
        self.log_dock.setWidget(self.log_panel)
        self.log_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.resize(self.log_dock.width(), 240)
        self.log_dock.hide()
        self.log_dock.visibilityChanged.connect(self._sync_log_action)

    def _apply_texts(self):
        self.setWindowTitle(APP_NAME)
        self.a_add.setText(t("act.add"))
        self.a_add.setToolTip(t("tip.add"))
        self.a_monitor.setText(t("act.monitor"))
        self.a_monitor.setToolTip(t("tip.monitor"))
        self.a_start_sel.setText(t("act.start_sel"))
        self.a_start_sel.setToolTip(t("tip.start_sel"))
        self.a_start_view.setText(t("act.start_view"))
        self.a_start_view.setToolTip(t("tip.start_view"))
        self.a_pause.setText(t("act.pause"))
        self.a_group.setText(t("act.group"))
        self.a_group.setToolTip(t("tip.group"))
        self.a_autogroup.setText(t("act.autogroup"))
        self.a_autogroup.setToolTip(t("tip.autogroup"))
        self.a_remove.setText(t("act.remove"))
        self.a_clear.setText(t("act.clear"))
        self.a_settings.setText(t("act.settings"))
        self.a_log.setText(t("act.log"))
        self.a_log.setToolTip(t("tip.log"))
        self.log_dock.setWindowTitle(t("logui.title"))
        self.log_panel.retranslate()
        self.lbl_groups.setText(t("lbl.groups"))
        self.b_new.setText(t("btn.group_new"))
        self.b_edit.setText(t("btn.group_edit"))
        self.b_del.setText(t("btn.group_delete"))
        self.empty.setText(t("empty.hint"))
        self.model.retranslate()
        self._refresh_groups()
        self._update_status()
        self._update_selection_actions()

    # ------------------------------------------------------------------ selection helpers
    def _selected_ids(self) -> list[str]:
        rows = self.view.selectionModel().selectedRows()
        ids = [ix.data(IdRole) for ix in sorted(rows, key=lambda x: x.row())]
        return [i for i in ids if i]

    def _view_ids(self) -> list[str]:
        out = []
        for r in range(self.proxy.rowCount()):
            i = self.proxy.index(r, 0).data(IdRole)
            if i:
                out.append(i)
        return out

    def _update_selection_actions(self):
        n = len(self._selected_ids())
        for a in (self.a_start_sel, self.a_group, self.a_remove):
            a.setEnabled(n > 0)

    def _update_empty(self, *_):
        self.stack.setCurrentIndex(1 if self.model.rowCount() else 0)

    # ------------------------------------------------------------------ groups panel
    def _refresh_groups_soon(self):
        self._groups_timer.start()

    def _current_token(self) -> str:
        it = self.group_list.currentItem()
        return it.data(Qt.UserRole) if it else ALL

    def _refresh_groups(self):
        keep = self._current_token()
        counts: dict[str, int] = {}
        for it in self.engine.items.values():
            counts[it.group_id] = counts.get(it.group_id, 0) + 1
        self.group_list.blockSignals(True)
        self.group_list.clear()

        def add(text, token, tip=""):
            li = QListWidgetItem(text)
            li.setData(Qt.UserRole, token)
            if tip:
                li.setToolTip(tip)
            self.group_list.addItem(li)
            return li

        add(f"{t('grp.all')}   ({len(self.engine.items)})", ALL)
        add(f"{t('grp.none')}   ({counts.get('', 0)})", NONE)
        for g in self.engine.groups:
            add(f"{g.name}   ({counts.get(g.id, 0)})", g.id, g.folder or t("grp.no_folder"))
        target = 0
        for r in range(self.group_list.count()):
            if self.group_list.item(r).data(Qt.UserRole) == keep:
                target = r
        self.group_list.setCurrentRow(target)
        self.group_list.blockSignals(False)
        self._apply_filter()
        self._update_group_buttons()

    def _apply_filter(self):
        tok = self._current_token()
        self.proxy.set_group_filter(None if tok == ALL else ("" if tok == NONE else tok))

    def _group_selected_in_list(self, *_):
        self._apply_filter()
        self._update_group_buttons()

    def _update_group_buttons(self):
        real = self._current_token() not in (ALL, NONE)
        self.b_edit.setEnabled(real)
        self.b_del.setEnabled(real)

    def _new_group(self):
        dlg = GroupDialog(self, base_folder=self.engine.settings.base_folder)
        if dlg.exec():
            name, folder = dlg.value()
            self.engine.add_group(name, folder)

    def _edit_group(self):
        gid = self._current_token()
        g = self.engine.group(gid)
        if not g:
            return
        dlg = GroupDialog(self, g)
        if dlg.exec():
            name, folder = dlg.value()
            self.engine.edit_group(gid, name, folder)

    def _delete_group(self):
        gid = self._current_token()
        g = self.engine.group(gid)
        if g and QMessageBox.question(self, APP_NAME, t("msg.confirm_group_delete", name=g.name)) == QMessageBox.Yes:
            self.engine.delete_group(gid)

    def _group_menu(self, pos):
        m = QMenu(self)
        m.addAction(t("btn.group_new"), self._new_group)
        if self._current_token() not in (ALL, NONE):
            m.addAction(t("btn.group_edit"), self._edit_group)
            m.addAction(t("menu.open_folder"), self._open_group_folder)
            m.addAction(t("act.start_view"), lambda: self._start(self._view_ids()))
            m.addSeparator()
            m.addAction(t("btn.group_delete"), self._delete_group)
        m.exec(self.group_list.mapToGlobal(pos))

    def _open_group_folder(self):
        g = self.engine.group(self._current_token())
        if g and g.folder:
            self._open_path(Path(g.folder))

    def _on_drop(self, ids: list, token: str):
        self.engine.set_group(ids, "" if token == NONE else token)
        self.statusBar().showMessage(t("msg.moved", n=len(ids)), 4000)

    # ------------------------------------------------------------------ adding links
    def _toggle_monitor(self, on: bool):
        self.engine.set_settings(dataclasses.replace(self.engine.settings, monitor_clipboard=on))
        self.statusBar().showMessage(t("msg.monitor_on") if on else t("msg.monitor_off"), 3000)

    def _on_clipboard(self):
        if self.engine.settings.monitor_clipboard:
            QTimer.singleShot(60, lambda: self._grab_text(self._clip.text(), notify=True))

    def _grab_text(self, text: str, notify: bool = False) -> int:
        n = self.engine.add_links(extract_links(text))
        if n and notify:
            self.statusBar().showMessage(t("msg.added", n=n), 5000)
            if not self.isActiveWindow():
                QApplication.alert(self, 2500)
        return n

    def _add_dialog(self):
        pre = self._clip.text() if extract_links(self._clip.text()) else ""
        dlg = PasteLinksDialog(self, pre)
        if dlg.exec():
            n = self._grab_text(dlg.value())
            self.statusBar().showMessage(t("msg.added", n=n) if n else t("msg.nothing_added"), 5000)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText() or e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        text = md.text() or "\n".join(u.toString() for u in md.urls())
        if self._grab_text(text, notify=True):
            e.acceptProposedAction()

    # ------------------------------------------------------------------ start / pause / remove
    def _start(self, ids: list[str]):
        eng = self.engine
        ids = [i for i in ids if i in eng.items and eng.items[i].state in (READY, PAUSED, ERROR, RESOLVING)]
        if not ids:
            self.statusBar().showMessage(t("msg.nothing_to_start"), 4000)
            return
        missing = [i for i in ids if eng.folder_for(eng.items[i]) is None]
        if missing:
            folder = pick_folder(self, t("dlg.default_folder_title", n=len(missing)))
            if folder:
                eng.set_settings(dataclasses.replace(eng.settings, default_folder=folder))
            else:
                ids = [i for i in ids if i not in missing]
        eng.start(ids)
        if ids:
            self.statusBar().showMessage(t("msg.started", n=len(ids)), 4000)

    def _pause(self):
        ids = self._selected_ids() or self._view_ids()
        self.engine.pause(ids)

    def _remove_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        if len(ids) >= 5 and QMessageBox.question(self, APP_NAME, t("msg.confirm_remove", n=len(ids))) != QMessageBox.Yes:
            return
        self.engine.remove(ids)

    # ------------------------------------------------------------------ grouping actions
    def _group_selected(self):
        ids = self._selected_ids()
        if not ids:
            self.statusBar().showMessage(t("msg.select_first"), 4000)
            return
        dlg = AssignGroupDialog(self, self.engine.groups, len(ids), self.engine.settings.base_folder)
        if not dlg.exec():
            return
        gid, name, folder = dlg.result_group()
        if gid is None:
            gid = self.engine.add_group(name, folder).id
        self.engine.set_group(ids, gid)
        self.statusBar().showMessage(t("msg.moved", n=len(ids)), 4000)

    def _autogroup(self):
        eng = self.engine
        ids = self._selected_ids() or [i for i, it in eng.items.items() if not it.group_id]
        if not ids:
            self.statusBar().showMessage(t("msg.nothing_to_group"), 4000)
            return
        base = eng.settings.base_folder
        if not base:
            base = pick_folder(self, t("dlg.base_folder_title"))
            if not base:
                return
            eng.set_settings(dataclasses.replace(eng.settings, base_folder=base))
        unresolved = sum(1 for i in ids if not eng.items[i].creator)
        created, assigned = eng.auto_group_by_creator(ids, base)
        msg = t("msg.autogrouped", groups=created, n=assigned)
        if unresolved:
            msg += "  " + t("msg.unresolved_skipped", n=unresolved)
        self.statusBar().showMessage(msg, 7000)

    # ------------------------------------------------------------------ log
    def _sync_log_action(self, visible: bool):
        self.a_log.blockSignals(True)
        self.a_log.setChecked(visible)
        self.a_log.blockSignals(False)

    def show_log_for(self, item_id: str):
        self.log_dock.show()
        self.log_panel.show_only(f"#{item_id[:6]}")

    # ------------------------------------------------------------------ context menu / open
    def _table_menu(self, pos):
        ids = self._selected_ids()
        if not ids:
            ix = self.view.indexAt(pos)
            if not ix.isValid():
                return
            self.view.selectRow(ix.row())
            ids = self._selected_ids()
        eng = self.engine
        m = QMenu(self)
        m.addAction(t("act.start_sel"), lambda: self._start(ids))
        m.addAction(t("act.pause"), lambda: eng.pause(ids))
        m.addSeparator()
        sub = m.addMenu(t("menu.move_to"))
        for g in eng.groups:
            sub.addAction(g.name, lambda gid=g.id: eng.set_group(ids, gid))
        if eng.groups:
            sub.addSeparator()
        sub.addAction(t("grp.none"), lambda: eng.set_group(ids, ""))
        sub.addAction(t("dlg.new_group_item"), self._group_selected)
        m.addAction(t("act.autogroup"), self._autogroup)
        m.addSeparator()
        first = eng.items.get(ids[0])
        if first:
            m.addAction(t("menu.open_page"), lambda: QDesktopServices.openUrl(QUrl(eng.page_url(first))))
            m.addAction(t("menu.copy_link"), lambda: QGuiApplication.clipboard().setText("\n".join(
                eng.items[i].url for i in ids if i in eng.items)))
            m.addAction(t("menu.open_folder"), lambda: self._open_item_folder(first))
            m.addAction(t("menu.re_resolve"), lambda: eng.re_resolve(ids))
            m.addAction(t("menu.show_log"), lambda: self.show_log_for(first.id))
        m.addSeparator()
        m.addAction(t("act.remove"), self._remove_selected)
        m.exec(self.view.viewport().mapToGlobal(pos))

    def _open_path(self, p: Path):
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        else:
            self.statusBar().showMessage(t("msg.folder_missing", path=str(p)), 5000)

    def _open_item_folder(self, it):
        if it.dest_path:
            self._open_path(Path(it.dest_path).parent)
            return
        f = self.engine.folder_for(it)
        if f:
            self._open_path(f)

    def _open_item(self, proxy_index: QModelIndex):
        it = self.engine.items.get(proxy_index.data(IdRole))
        if it:
            self._open_item_folder(it)

    # ------------------------------------------------------------------ settings / status
    def _open_settings(self):
        old = self.engine.settings
        dlg = SettingsDialog(old, self, str(self.engine.storage.base))
        if not dlg.exec():
            return
        new = dlg.value()
        self.engine.set_settings(new)
        self.a_monitor.blockSignals(True)
        self.a_monitor.setChecked(new.monitor_clipboard)
        self.a_monitor.blockSignals(False)
        if new.theme != old.theme:
            theme.apply_theme(QApplication.instance(), new.theme)
        if new.language != old.language:
            set_language(new.language)
        self._apply_texts()

    def _on_message(self, code: str, detail: str):
        self.statusBar().showMessage(t(f"msg.{code}", detail=detail), 8000)

    def _update_status(self):
        c = self.engine.counts()
        self.lbl_counts.setText(t("status.counts", total=c["total"], active=c["downloading"],
                                  queued=c["queued"], done=c["done"], err=c["error"]))
        self.lbl_speed.setText(f"↓ {format_size(c['speed'])}/s" if c["speed"] > 0 else "")
        if self.engine.settings.api_key:
            self.lbl_key.setText("")
        else:
            self.lbl_key.setText(t("status.no_key"))
            self.lbl_key.setStyleSheet(f"color: {theme.colors()['warn']};")

    # ------------------------------------------------------------------ closing
    def closeEvent(self, e):
        s = dataclasses.replace(self.engine.settings, geometry=bytes(self.saveGeometry().toBase64()).decode())
        self.engine.set_settings(s)
        self.engine.shutdown()
        e.accept()
