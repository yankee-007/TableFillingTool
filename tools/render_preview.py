"""Render only synthetic sample data for local layout review (no WeCom actions)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.data import Store
from app.fonts import configure_font
from app.service import Workspace
from app.theme import STYLE
from app.ui import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    print("Font:", configure_font(app))
    app.setStyleSheet(STYLE)
    output = Path(__file__).resolve().parents[1] / "artifacts" / "preview"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "tables.sqlite3")
        workspace = Workspace(store)
        window = MainWindow(workspace)
        window.sample()
        window.show()
        app.processEvents()
        for width, height in ((1400, 850), (980, 620)):
            window.resize(width, height)
            app.processEvents()
            window.grab().save(str(output / f"main-{width}.png"))
            print(f"Requested {width}x{height}; actual {window.width()}x{window.height()}")
        window.floating.form.bind(window.current_key)
        window.floating.follow.setChecked(False)
        window.floating.notice.setText("手动填写中 · 虚构示例，无真实联系人")
        window.floating.show()
        window.floating.timer.stop()
        app.processEvents()
        window.floating.grab().save(str(output / "floating.png"))
        window.close()
        store.close()
    print(output)


if __name__ == "__main__":
    main()
