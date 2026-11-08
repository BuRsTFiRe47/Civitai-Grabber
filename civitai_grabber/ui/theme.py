"""Dark (default) and light themes, plus the app icon drawn in code."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox

# KDE Breeze-Dark inspired (slate background, coral accent); colours measured from the LoRA Librarian look.
PALETTES: dict[str, dict[str, str]] = {
    "dark": dict(
        bg="#181826", surface="#12121d", surface2="#2c2d40", border="#4a4c63", soft="#2f3045",
        ctrl="#202133", ctrl_hover="#2a2b40", text="#eff0f1", muted="#9a9db3", disabled="#626479",
        accent="#d94a4f", accent_hover="#e45a5e", accent_press="#c03d42", accent_dim="#7a3a48",
        accent_text="#ffffff", check_box="#6a6c85",
        ok="#4cc38a", err="#ef6a72", warn="#e5b567", sel="#4a2f40", hover="#2a2b40",
    ),
    "light": dict(
        bg="#eff0f1", surface="#fcfcfc", surface2="#cdd1d5", border="#bdc3c7", soft="#d3d7da",
        ctrl="#f7f8f9", ctrl_hover="#e4e7ea", text="#232629", muted="#5e6773", disabled="#9aa1a8",
        accent="#d94a4f", accent_hover="#e05a5e", accent_press="#c63f44", accent_dim="#efb0b3",
        accent_text="#ffffff", check_box="#8a9199",
        ok="#1f9d63", err="#da4453", warn="#b7791f", sel="#f6d5d7", hover="#e4e7ea",
    ),
}

_current = "dark"


def colors(name: str | None = None) -> dict[str, str]:
    return PALETTES[name or _current]


def build_qss(c: dict[str, str]) -> str:
    return f"""
* {{ font-size: 13px; font-family: "Noto Sans", "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif; }}
QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QLabel {{ background: transparent; }}
QLabel[muted="true"] {{ color: {c['muted']}; font-size: 12px; }}
QToolTip {{ background: {c['ctrl']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px 6px; }}

QToolBar {{ background: {c['bg']}; border: none; border-bottom: 1px solid {c['soft']}; padding: 6px; spacing: 4px; }}
QToolBar::separator {{ background: {c['soft']}; width: 1px; margin: 4px 6px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 6px 9px; }}
QToolBar QToolButton#qt_toolbar_ext_button {{ padding: 4px; }}
QToolButton:hover {{ background: {c['ctrl_hover']}; border: 1px solid {c['border']}; }}
QToolButton:pressed {{ background: {c['surface']}; }}
QToolButton:checked {{ background: {c['accent']}; border: 1px solid {c['accent']}; color: {c['accent_text']}; }}
QToolButton:disabled {{ color: {c['disabled']}; }}

QPushButton {{ background: {c['ctrl']}; border: 1px solid {c['border']}; border-radius: 4px; padding: 6px 14px; }}
QPushButton:hover {{ background: {c['ctrl_hover']}; border: 1px solid {c['muted']}; }}
QPushButton:pressed {{ background: {c['surface']}; }}
QPushButton:default {{ background: {c['accent']}; color: {c['accent_text']}; border: 1px solid {c['accent_press']}; font-weight: 700; }}
QPushButton:default:hover {{ background: {c['accent_hover']}; border: 1px solid {c['accent_hover']}; }}
QPushButton:default:pressed {{ background: {c['accent_press']}; }}
QPushButton:disabled {{ color: {c['disabled']}; background: {c['bg']}; border: 1px solid {c['soft']}; }}

QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 4px; padding: 5px 8px;
    selection-background-color: {c['accent']}; selection-color: white;
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border: 1px solid {c['muted']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {c['accent']}; }}
QLineEdit:disabled, QPlainTextEdit:disabled {{ color: {c['disabled']}; border: 1px solid {c['soft']}; }}
QPlainTextEdit {{ font-family: Consolas, Menlo, "DejaVu Sans Mono", monospace; font-size: 12px; }}

QComboBox {{ background: {c['ctrl']}; border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 28px 4px 10px; min-height: 20px; }}
QComboBox:hover {{ background: {c['ctrl_hover']}; }}
QComboBox:focus {{ border: 1px solid {c['accent']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{ background: {c['ctrl']}; border: 1px solid {c['border']}; selection-background-color: {c['accent']}; selection-color: white; outline: none; padding: 2px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}

QTableView, QListWidget {{
    background: {c['surface']}; alternate-background-color: {c['bg']}; border: 1px solid {c['soft']};
    border-radius: 4px; gridline-color: transparent; outline: 0;
    selection-background-color: {c['sel']}; selection-color: {c['text']};
}}
QTableView::item {{ padding: 4px 6px; border: none; }}
QTableView::item:selected, QListWidget::item:selected {{ background: {c['sel']}; color: {c['text']}; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 4px; margin: 1px 4px; }}
QListWidget::item:hover {{ background: {c['ctrl_hover']}; }}
QListWidget::item:selected {{ background: {c['accent']}; color: {c['accent_text']}; }}
QHeaderView::section {{ background: {c['ctrl']}; color: {c['muted']}; border: none; border-right: 1px solid {c['soft']}; padding: 6px 8px; font-weight: 600; }}
QTableCornerButton::section {{ background: {c['ctrl']}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 3px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: {c['bg']}; width: 6px; }}
QDockWidget::title {{ background: {c['bg']}; padding: 6px 10px; border-top: 1px solid {c['soft']}; }}
QStatusBar {{ background: {c['bg']}; border-top: 1px solid {c['soft']}; }}
QStatusBar QLabel {{ background: transparent; color: {c['muted']}; padding: 0 8px; }}
QMenu {{ background: {c['ctrl']}; border: 1px solid {c['border']}; border-radius: 4px; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {c['accent']}; color: {c['accent_text']}; }}
QMenu::item:disabled {{ color: {c['disabled']}; }}
QMenu::separator {{ height: 1px; background: {c['soft']}; margin: 4px 6px; }}
QMessageBox {{ background: {c['bg']}; }}
QTabWidget::pane {{ border: 1px solid {c['soft']}; border-radius: 4px; top: -1px; }}
QTabBar::tab {{ background: transparent; padding: 8px 16px; border: none; color: {c['muted']}; }}
QTabBar::tab:hover {{ color: {c['text']}; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {c['accent']}; }}
QGroupBox {{ border: 1px solid {c['soft']}; border-radius: 4px; margin-top: 12px; padding-top: 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {c['muted']}; }}
QProgressBar {{ background: {c['surface2']}; border: none; border-radius: 4px; }}
"""


class Check(QCheckBox):
    """Breeze-style checkbox: rounded square, accent border + tick."""
    BOX = 18

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(28)

    def sizeHint(self):
        return QSize(self.BOX + 10 + self.fontMetrics().horizontalAdvance(self.text()) + 4, 28)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = colors()
        y = (self.height() - self.BOX) / 2
        box = QRectF(1.5, y + 0.5, self.BOX - 1, self.BOX - 1)
        on = self.isChecked()
        hot = self.underMouse() and self.isEnabled()
        border = QColor(c["accent"]) if on else QColor(c["accent_hover"] if hot else c["check_box"])
        p.setPen(QPen(border, 1.4))
        p.setBrush(QColor(c["surface"]))
        p.drawRoundedRect(box, 3, 3)
        if on:
            tick = QPen(QColor(c["text"]), 2)
            tick.setCapStyle(Qt.RoundCap)
            tick.setJoinStyle(Qt.RoundJoin)
            p.setPen(tick)
            p.setBrush(Qt.NoBrush)
            x0, y0, w = box.left(), box.top(), box.width()
            p.drawPolyline(QPolygonF([QPointF(x0 + w * 0.24, y0 + w * 0.54),
                                      QPointF(x0 + w * 0.44, y0 + w * 0.74),
                                      QPointF(x0 + w * 0.78, y0 + w * 0.30)]))
        p.setPen(QColor(c["text"] if self.isEnabled() else c["disabled"]))
        p.drawText(QRectF(self.BOX + 10, 0, self.width() - self.BOX - 10, self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.text())


class Combo(QComboBox):
    """QComboBox with a thin chevron."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = colors()
        pen = QPen(QColor(c["text"] if self.isEnabled() else c["disabled"]), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        cx, cy, s = self.width() - 15, self.height() / 2, 4.5
        p.drawPolyline(QPolygonF([QPointF(cx - s, cy - s / 2), QPointF(cx, cy + s / 2), QPointF(cx + s, cy - s / 2)]))


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#202133")))
        p.drawRoundedRect(r, size * 0.22, size * 0.22)
        pen = QPen(QColor("#d94a4f"))
        pen.setWidthF(size * 0.09)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(QPointF(size * 0.5, size * 0.22))
        path.lineTo(QPointF(size * 0.5, size * 0.60))
        path.moveTo(QPointF(size * 0.33, size * 0.45))
        path.lineTo(QPointF(size * 0.5, size * 0.62))
        path.lineTo(QPointF(size * 0.67, size * 0.45))
        path.moveTo(QPointF(size * 0.28, size * 0.76))
        path.lineTo(QPointF(size * 0.72, size * 0.76))
        p.drawPath(path)
        p.end()
        icon.addPixmap(pm)
    return icon


def apply_theme(app: QApplication, name: str = "dark") -> None:
    global _current
    _current = name if name in PALETTES else "dark"
    c = PALETTES[_current]
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["bg"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["surface2"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.Link, QColor(c["accent"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(c["accent_text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["surface2"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["muted"]))
    app.setPalette(pal)
    app.setStyleSheet(build_qss(c))
