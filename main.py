from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from app.data import Store
from app.fonts import configure_font
from app.service import Workspace
from app.theme import STYLE
from app.ui import MainWindow


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="独立表格填写与企业微信聊天跟随工具")
    parser.add_argument("--data-dir", type=Path, help="独立数据目录（默认使用本工具的 Qt 本地应用目录）")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("TableFillingTool")
    app.setOrganizationName("LocalTools")
    app.setStyle("Fusion")
    configure_font(app)
    app.setStyleSheet(STYLE)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LocalTools.TableFillingTool")
    directory = args.data_dir or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(directory / "workspace.lock"))
    if not lock.tryLock(0):
        QMessageBox.warning(None, "工具已打开", "此数据目录正由另一个实例使用，请切回已打开的工具。")
        return 1
    try:
        store = Store(directory / "tables.sqlite3")
        workspace = Workspace(store)
    except Exception as exc:
        QMessageBox.critical(None, "无法读取本地数据", "原数据文件已保留，请检查目录权限或备份后恢复：\n" + str(exc))
        return 1
    window = MainWindow(workspace)
    screen = app.primaryScreen()
    if screen:
        available = screen.availableGeometry()
        window.resize(min(1400, int(available.width() * 0.92)), min(900, int(available.height() * 0.9)))
        window.move(available.center() - window.rect().center())
    window.show()
    try:
        return app.exec()
    finally:
        store.close()
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
