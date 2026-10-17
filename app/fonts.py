"""Choose a readable system font; offscreen Qt on Windows needs explicit loading."""
import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def configure_font(app):
    available = set(QFontDatabase.families())
    if not available and os.name == "nt":
        directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for filename in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf"):
            path = directory / filename
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))
        available = set(QFontDatabase.families())
    family = next((name for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI")
                   if name in available), "Sans Serif")
    font = QFont(family, 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setStyleStrategy(QFont.StyleStrategy.PreferOutline)
    app.setFont(font)
    return family
