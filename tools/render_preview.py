"""Render only synthetic sample data for local layout review (no WeCom actions)."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.data import Store
from app.fonts import configure_font
from app.service import Workspace
from app.theme import STYLE
from app.ui import ContactDialog, FieldDialog, MainWindow
from app.filter_dialog import ColumnFilterDialog
from app.verification_dialog import VerificationDialog


def capture(widget, path, app):
    widget.show()
    app.processEvents()
    widget.grab().save(str(path))


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
        window.resize(980, 620)
        capture(window, output / "empty.png", app)
        window.sample()
        for width, height in ((1400, 850), (980, 620)):
            window.resize(width, height)
            capture(window, output / f"main-{width}.png", app)
            print(f"Requested {width}x{height}; actual {window.width()}x{window.height()}")
        sheet = workspace.sheets[0]
        original_title = sheet.title
        sheet.title = "虚构长表名：跨班期联系人登记与日常沟通反馈填写工作表"
        window.title.setText(sheet.title)
        capture(window, output / "long-title.png", app)
        sheet.title = original_title
        window.title.setText(sheet.title)
        window.search.setText("不存在的虚构关键词")
        capture(window, output / "no-results.png", app)
        window.search.clear()
        row = sheet.rows[0]
        window.floating.form.bind(window.current_key)
        window.floating.follow.setChecked(False)
        window.floating.notice.setText("手动填写中 · 虚构示例，无真实联系人")
        capture(window.floating, output / "floating.png", app)
        window.floating.timer.stop()
        window.floating.resize(290, 420)
        capture(window.floating, output / "floating-small.png", app)
        print(f"Small floating: {window.floating.width()}x{window.floating.height()}")
        # Exercise error presentation without changing real data or external apps.
        notes = next(col.id for col in sheet.columns if col.kind == "multiline")
        window.floating.form.pending[notes] = "待保存的虚构反馈"
        with patch.object(store, "save_cells", side_effect=OSError("模拟磁盘写入失败")):
            window.floating.form.flush()
            capture(window.floating, output / "save-error.png", app)
        window.floating.form.flush()
        window.floating.close()
        name_cid = sheet.settings["name_column"]
        column_filter = ColumnFilterDialog(sheet, name_cid, window.filter, window)
        capture(column_filter, output / "column-filter-values.png", app)
        column_filter.tabs.setCurrentIndex(1)
        capture(column_filter, output / "column-filter-condition.png", app)
        column_filter.close()
        verifier = VerificationDialog(workspace, sheet, window.filter.scope_rows, window)
        capture(verifier, output / "verification.png", app)
        verifier.resize(680, 560)
        capture(verifier, output / "verification-small.png", app)
        verifier.close()
        window.set_column_filter(name_cid, {"mode": "exact", "value": row.cells[name_cid]})
        workspace.save_values(sheet.id, row.id, {name_cid: "示例小周（已处理）"})
        window.resize(980, 620)
        capture(window, output / "filter-stale.png", app)
        window.clear_filters()
        for dialog, filename in ((ContactDialog(sheet, window), "contact-settings.png"),
                                 (FieldDialog(window), "add-field.png")):
            capture(dialog, output / filename, app)
            dialog.close()
        window.close()
        store.close()
    print(output)


if __name__ == "__main__":
    main()
