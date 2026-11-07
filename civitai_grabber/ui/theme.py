"""Dark (default) and light themes, plus the app icon drawn in code."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

PALETTES: dict[str, dict[str, str]] = {
    "dark": dict(
        bg="#14161a", surface="#1b1e24", surface2="#232730", border="#2d323d",
        text="#e6e8ec", muted="#8b93a1", accent="#5b9dff", accent_text="#0b1220",
        ok="#4cc38a", err="#ef6a6a", warn="#e5b567", sel="#243350", hover="#2a2f3a",
    ),
    "light": dict(
        bg="#f4f5f7", surface="#ffffff", surface2="#eceef2", border="#d5d9e0",
        text="#1c2027", muted="#6b7482", accent="#2f6fe0", accent_text="#ffffff",
        ok="#1f9d63", err="#d64545", warn="#b7791f", sel="#dce8fd", hover="#e3e7ee",
    ),
}

_current = "dark"


def colors(name: str | None = None) -> dict[str, str]:
    return PALETTES[name or _current]


def build_qss(c: dict[str, str]) -> str:
    return f"""
* {{ font-size: 13px; }}
QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QLabel {{ background: transparent; }}
QLabel[muted="true"] {{ color: {c['muted']}; }}
QToolTip {{ background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px; }}

QToolBar {{ background: {c['surface']}; border: none; border-bottom: 1px solid {c['border']}; padding: 6px; spacing: 4px; }}
QToolBar::separator {{ background: {c['border']}; width: 1px; margin: 4px 6px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 6px 8px; }}
QToolBar QToolButton#qt_toolbar_ext_button {{ padding: 4px; }}
QToolButton:hover {{ background: {c['hover']}; }}
QToolButton:pressed {{ background: {c['sel']}; }}
QToolButton:checked {{ background: {c['sel']}; border: 1px solid {c['accent']}; color: {c['accent']}; }}
QToolButton:disabled {{ color: {c['muted']}; }}

QPushButton {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {c['accent']}; }}
QPushButton:pressed {{ background: {c['sel']}; }}
QPushButton:default {{ background: {c['accent']}; color: {c['accent_text']}; border-color: {c['accent']}; }}
QPushButton:disabled {{ color: {c['muted']}; }}

QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 5px 8px;
    selection-background-color: {c['accent']}; selection-color: {c['accent_text']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']}; selection-background-color: {c['sel']}; selection-color: {c['text']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['border']}; border-radius: 4px; background: {c['surface']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}

QTableView, QListWidget {{
    background: {c['surface']}; alternate-background-color: {c['bg']}; border: 1px solid {c['border']};
    border-radius: 8px; gridline-color: transparent; outline: 0;
    selection-background-color: {c['sel']}; selection-color: {c['text']};
}}
QTableView::item {{ padding: 4px 6px; border: none; }}
QTableView::item:selected, QListWidget::item:selected {{ background: {c['sel']}; color: {c['text']}; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; margin: 1px 4px; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QHeaderView::section {{ background: {c['surface2']}; color: {c['muted']}; border: none; border-right: 1px solid {c['border']}; padding: 6px 8px; font-weight: 600; }}
QTableCornerButton::section {{ background: {c['surface2']}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 28px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 28px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: {c['bg']}; width: 6px; }}
QDockWidget::title {{ background: {c['surface']}; padding: 6px 10px; border-top: 1px solid {c['border']}; }}
QStatusBar {{ background: {c['surface']}; border-top: 1px solid {c['border']}; }}
QStatusBar QLabel {{ background: transparent; color: {c['muted']}; padding: 0 8px; }}
QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: {c['sel']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 6px; }}
QMessageBox {{ background: {c['bg']}; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{ background: transparent; padding: 8px 16px; border: none; color: {c['muted']}; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {c['accent']}; }}
QGroupBox {{ border: 1px solid {c['border']}; border-radius: 8px; margin-top: 12px; padding-top: 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {c['muted']}; }}
"""


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#1b2540")))
        p.drawRoundedRect(r, size * 0.22, size * 0.22)
        pen = QPen(QColor("#5b9dff"))
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
