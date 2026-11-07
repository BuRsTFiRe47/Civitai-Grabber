"""Item table model, filter proxy and progress-bar delegate."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QRectF,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from civitai_grabber.core.engine import Engine
from civitai_grabber.core.models import DONE, DOWNLOADING, ERROR, PAUSED, RESOLVING, Item
from civitai_grabber.i18n import error_text, t
from civitai_grabber.ui import theme

COLS = ["name", "version", "creator", "type", "size", "group", "status", "progress", "speed"]
COL_PROGRESS = COLS.index("progress")
MIME = "application/x-civitai-grabber-ids"

IdRole = Qt.UserRole + 1
SortRole = Qt.UserRole + 2
ProgressRole = Qt.UserRole + 3
StateRole = Qt.UserRole + 4


def format_size(n: float) -> str:
    if n <= 0:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.0f} {units[i]}" if i == 0 else f"{n:.1f} {units[i]}"


class ItemModel(QAbstractTableModel):
    def __init__(self, engine: Engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._ids: list[str] = list(engine.order)
        engine.itemsAdded.connect(self._added)
        engine.itemRemoved.connect(self._removed)
        engine.itemChanged.connect(self._changed)
        engine.orderChanged.connect(self._reordered)

    # -- engine signals
    def _added(self, ids: list):
        first = len(self._ids)
        self.beginInsertRows(QModelIndex(), first, first + len(ids) - 1)
        self._ids.extend(ids)
        self.endInsertRows()

    def _removed(self, item_id: str):
        if item_id in self._ids:
            row = self._ids.index(item_id)
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._ids[row]
            self.endRemoveRows()

    def _reordered(self):
        self.beginResetModel()
        self._ids = list(self.engine.order)
        self.endResetModel()

    def _changed(self, item_id: str):
        if item_id in self._ids:
            row = self._ids.index(item_id)
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLS) - 1))

    def retranslate(self):
        self.headerDataChanged.emit(Qt.Horizontal, 0, len(COLS) - 1)
        if self._ids:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._ids) - 1, len(COLS) - 1))

    # -- model API
    def item_at(self, row: int) -> Optional[Item]:
        if 0 <= row < len(self._ids):
            return self.engine.items.get(self._ids[row])
        return None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._ids)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return t(f"col.{COLS[section]}")
        return None

    def flags(self, index):
        f = super().flags(index)
        return f | Qt.ItemIsDragEnabled if index.isValid() else f

    def mimeTypes(self):
        return [MIME]

    def mimeData(self, indexes):
        ids: list[str] = []
        for ix in indexes:
            it = self.item_at(ix.row())
            if it and it.id not in ids:
                ids.append(it.id)
        md = QMimeData()
        md.setData(MIME, "\n".join(ids).encode())
        return md

    def status_text(self, it: Item) -> str:
        if it.state == ERROR:
            return error_text(it.error)
        return t(f"state.{it.state}")

    def data(self, index, role=Qt.DisplayRole):
        it = self.item_at(index.row())
        if it is None:
            return None
        col = COLS[index.column()]
        if role == IdRole:
            return it.id
        if role == StateRole:
            return it.state
        if role == ProgressRole:
            return it.progress
        if role == Qt.DisplayRole:
            return self._text(it, col)
        if role == SortRole:
            return {
                "size": it.size,
                "progress": it.progress,
                "speed": it.speed,
                "group": self.engine.group_name(it.group_id).lower(),
                "name": it.display_name.lower(),
                "creator": it.creator.lower(),
                "status": it.state,
            }.get(col, self._text(it, col).lower())
        if role == Qt.ToolTipRole:
            if col == "status" and it.state == ERROR:
                tip = error_text(it.error, long=True)
                detail = it.error.partition(":")[2] if it.error.startswith("nofile") else ""
                if detail:
                    tip += f"\n{detail}"
                return tip + (f"\n\n{it.error_info}" if it.error_info else "")
            if col == "name":
                return f"{it.display_name}\n{it.filename}\n{it.url}"
            return None
        if role == Qt.ForegroundRole:
            c = theme.colors()
            if col == "status":
                return QColor({ERROR: c["err"], DONE: c["ok"], PAUSED: c["warn"]}.get(it.state, c["text"]))
            if col in ("creator", "type", "version", "speed", "size") or (col == "group" and not it.group_id):
                return QColor(c["muted"])
        if role == Qt.TextAlignmentRole and col in ("size", "speed"):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def _text(self, it: Item, col: str) -> str:
        if col == "name":
            return it.display_name if it.state != RESOLVING or it.name else it.url
        if col == "version":
            return it.version_name or "—"
        if col == "creator":
            return it.creator or "—"
        if col == "type":
            return it.model_type or "—"
        if col == "size":
            return format_size(it.size)
        if col == "group":
            return self.engine.group_name(it.group_id) or "—"
        if col == "status":
            return self.status_text(it)
        if col == "progress":
            return ""
        if col == "speed":
            return f"{format_size(it.speed)}/s" if it.state == DOWNLOADING and it.speed > 0 else ""
        return ""


class FilterProxy(QSortFilterProxyModel):
    """group filter: None = everything, "" = ungrouped, otherwise a group id."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.group_filter: Optional[str] = None
        self.setSortRole(SortRole)
        self.setDynamicSortFilter(True)

    def set_group_filter(self, value: Optional[str]):
        if hasattr(self, "beginFilterChange"):  # Qt >= 6.9 (invalidateFilter is deprecated there)
            self.beginFilterChange()
            self.group_filter = value
            self.endFilterChange()
        else:
            self.group_filter = value
            self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if self.group_filter is None:
            return True
        it = self.sourceModel().item_at(row)
        return bool(it) and it.group_id == self.group_filter


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        if index.column() != COL_PROGRESS:
            return super().paint(painter, option, index)
        c = theme.colors()
        state = index.data(StateRole)
        frac = float(index.data(ProgressRole) or 0.0)
        # selection background
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(c["sel"]))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        r = QRectF(option.rect).adjusted(6, 8, -6, -8)
        track = QPainterPath()
        track.addRoundedRect(r, 4, 4)
        painter.fillPath(track, QColor(c["surface2"]))
        color = {DOWNLOADING: c["accent"], DONE: c["ok"], ERROR: c["err"], PAUSED: c["warn"]}.get(state, c["muted"])
        if frac > 0:
            fill = QRectF(r.x(), r.y(), r.width() * frac, r.height())
            clip = QPainterPath()
            clip.addRoundedRect(fill, 4, 4)
            painter.fillPath(clip, QColor(color))
        if frac > 0 or state == DOWNLOADING:
            painter.setPen(QColor(c["text"]))
            f = painter.font()
            f.setPointSizeF(max(7.0, f.pointSizeF() - 1))
            painter.setFont(f)
            painter.drawText(r, Qt.AlignCenter, f"{frac * 100:.0f}%")
        painter.restore()
