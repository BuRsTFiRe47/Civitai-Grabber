"""Regenerates assets/icon.ico (and icon.png) from the in-app icon drawing. Needs PySide6 + Pillow."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from civitai_grabber.ui.theme import icon_pixmap  # noqa: E402

app = QGuiApplication([])
out = ROOT / "assets"
out.mkdir(exist_ok=True)
icon_pixmap(256).save(str(out / "icon.png"))
Image.open(out / "icon.png").save(out / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
print("wrote", out / "icon.ico")
