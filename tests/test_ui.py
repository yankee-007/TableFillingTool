from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.data import Store
from app.fonts import configure_font
from app.service import Workspace
from app.theme import STYLE
from app.ui import MainWindow
from test_core import fixture

APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
configure_font(APP)
APP.setStyleSheet(STYLE)


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "tables.sqlite3")
        self.workspace = Workspace(self.store)
        self.sheet = fixture()
        self.workspace.add_sheets([self.sheet])
        self.window = MainWindow(self.workspace)
        self.window.show()
        APP.processEvents()
        self.window.select_record(self.sheet.rows[0].id)
        APP.processEvents()

    def tearDown(self):
        self.window.form.pending.clear()
        self.window.floating.form.pending.clear()
        self.window.close()
        APP.processEvents()
        self.store.close()
        self.temp.cleanup()

    def enter(self, form, cid, value):
        editor = form.editors[cid]
        editor.setFocus()
        if isinstance(editor, QLineEdit):
            editor.setText(value)
            editor.textEdited.emit(value)
        else:
            editor.setPlainText(value)
        APP.processEvents()

    def test_main_edit_saves_before_row_switch_and_focus_values_refresh(self):
        cid = self.sheet.columns[2].id
        first, second = self.sheet.rows
        self.enter(self.window.form, cid, "first record draft")
        self.window.select_record(second.id)
        APP.processEvents()
        self.assertEqual(first.cells[cid], "first record draft")
        self.assertEqual(self.window.form.key, (self.sheet.id, second.id))
        self.assertEqual(self.window.form.editors[cid].toPlainText(), "")
        self.enter(self.window.form, cid, "second record")
        self.assertTrue(self.window.flush_all())
        self.assertEqual(second.cells[cid], "second record")
        self.assertEqual(first.cells[cid], "first record draft")

    def test_follow_switch_flushes_old_id_and_ignores_main_selection(self):
        floating = self.window.floating
        floating.timer.stop()
        cid = self.sheet.columns[2].id
        first, second = self.sheet.rows
        self.assertTrue(floating.match_title("py169张三"))
        self.enter(floating.form, cid, "浮窗第一人")
        self.assertTrue(floating.match_title("py169李四"))
        self.assertEqual(first.cells[cid], "浮窗第一人")
        self.assertEqual(second.cells[cid], "")
        self.window.select_record(first.id)
        self.assertEqual(floating.form.key, (self.sheet.id, second.id))
        self.enter(floating.form, cid, "浮窗第二人")
        self.assertTrue(floating.form.flush())
        self.assertEqual(second.cells[cid], "浮窗第二人")

    def test_save_failure_preserves_draft_blocks_switch_and_close_then_retry(self):
        floating = self.window.floating
        cid = self.sheet.columns[2].id
        first = self.sheet.rows[0]
        floating.match_title("py169张三")
        self.enter(floating.form, cid, "不可丢失的输入")
        with patch.object(self.store, "save_cells", side_effect=OSError("disk full")):
            self.assertFalse(floating.match_title("py169李四"))
            self.assertEqual(floating.form.key, (self.sheet.id, first.id))
            self.assertEqual(floating.form.pending[cid], "不可丢失的输入")
            self.assertFalse(self.window.flush_all())
            self.assertIn("保存失败", floating.form.result.text())
        self.assertTrue(floating.form.flush())
        self.assertEqual(first.cells[cid], "不可丢失的输入")
        self.assertTrue(floating.match_title("py169李四"))

    def test_ambiguous_chat_clears_editor_without_writing(self):
        another = fixture("二班", ("张三",), "py170")
        self.workspace.add_sheets([another])
        floating = self.window.floating
        self.assertFalse(floating.match_title("张三"))
        self.assertIsNone(floating.form.key)
        self.assertIn("多条", floating.notice.text())
        floating.scope.setCurrentIndex(floating.scope.findData(self.sheet.id))
        self.assertTrue(floating.match_title("张三"))

    def test_sorting_preserves_record_identity_for_table_and_form(self):
        self.window.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        APP.processEvents()
        self.window.select_record(self.sheet.rows[0].id)
        cid = self.sheet.columns[2].id
        self.enter(self.window.form, cid, "stable identity")
        self.window.flush_all()
        self.assertEqual(self.sheet.rows[0].cells[cid], "stable identity")
        self.assertEqual(self.sheet.rows[1].cells[cid], "")

    def test_cell_editor_failed_save_retains_text_and_retries(self):
        index = self.window.filter.mapFromSource(self.window.model.index(0, 0))
        self.window.table.setCurrentIndex(index)
        self.window.table.edit(index)
        APP.processEvents()
        editor = self.window.delegate.editor
        self.assertIsNotNone(editor)
        editor.setText("changed name")
        with patch.object(self.store, "save_cells", side_effect=OSError("locked")):
            QTest.keyClick(editor, Qt.Key.Key_Return)
            APP.processEvents()
            self.assertIs(self.window.delegate.editor, editor)
            self.assertEqual(editor.text(), "changed name")
            self.assertEqual(self.sheet.name(self.sheet.rows[0]), "张三")
        self.assertTrue(self.window.delegate.flush())
        self.assertEqual(self.sheet.name(self.sheet.rows[0]), "changed name")

    def test_same_record_external_update_does_not_rebuild_editors(self):
        cid = self.sheet.columns[2].id
        original = self.window.form.editors[cid]
        self.workspace.save_values(self.sheet.id, self.sheet.rows[0].id, {cid: "external"})
        self.assertIs(self.window.form.editors[cid], original)
        self.assertEqual(original.toPlainText(), "external")

    def test_filtered_edit_stays_visible_until_explicit_reapply(self):
        cid = self.sheet.columns[0].id
        self.window.search.setText("张三")
        self.assertEqual(self.window.filter.rowCount(), 1)
        self.workspace.save_values(self.sheet.id, self.sheet.rows[0].id, {cid: "王五"})
        self.assertEqual(self.window.filter.rowCount(), 1)
        self.window.reapply_filter()
        self.assertEqual(self.window.filter.rowCount(), 0)
        self.assertIsNone(self.window.current_key)

    def test_adding_column_retains_existing_values_and_record_binding(self):
        from app.data import Column
        cid = self.sheet.columns[2].id
        self.enter(self.window.form, cid, "before structure change")
        self.assertTrue(self.window.flush_all())
        original_id = self.window.form.key
        new_column = Column("新增字段")
        self.assertTrue(self.workspace.add_column(self.sheet.id, new_column))
        APP.processEvents()
        self.assertEqual(self.window.form.key, original_id)
        self.assertIn(new_column.id, self.window.form.editors)
        self.assertEqual(self.window.form.editors[cid].toPlainText(), "before structure change")

    def test_choice_clear_saves_empty_value_instead_of_display_label(self):
        from app.data import Column
        column = Column("状态", "choice", ["待联系", "已完成"])
        self.workspace.add_column(self.sheet.id, column)
        editor = self.window.form.editors[column.id]
        self.assertEqual(editor.currentData(), "")
        editor.setCurrentIndex(editor.findData("已完成"))
        self.assertTrue(self.window.form.flush())
        self.assertEqual(self.sheet.rows[0].cells[column.id], "已完成")
        editor.setCurrentIndex(editor.findData(""))
        self.assertTrue(self.window.form.flush())
        self.assertEqual(self.sheet.rows[0].cells[column.id], "")

    def test_background_import_returns_to_gui_thread_and_flushes_old_record(self):
        cid = self.sheet.columns[2].id
        self.enter(self.window.form, cid, "pending before import")
        imported = fixture("导入班")
        self.window._file_task(lambda: [imported], self.window._imported)
        for _ in range(100):
            QTest.qWait(10)
            if self.window.file_job is None:
                break
        self.assertIsNone(self.window.file_job)
        self.assertEqual(len(self.workspace.sheets), 2)
        self.assertEqual(len(self.store.load()), 2)
        self.assertEqual(self.sheet.rows[0].cells[cid], "pending before import")
        self.assertEqual(self.window.model.sheet_id, imported.id)

    def test_background_file_failure_restores_controls_and_preserves_tables(self):
        def fail():
            raise ValueError("invalid workbook")
        self.window._file_task(fail, self.window._imported)
        for _ in range(100):
            QTest.qWait(10)
            if self.window.file_job is None:
                break
        self.assertIsNone(self.window.file_job)
        self.assertTrue(self.window.import_button.isEnabled())
        self.assertTrue(self.window.export_button.isEnabled())
        self.assertEqual(len(self.workspace.sheets), 1)
        self.assertIn("invalid workbook", self.window.status.text())


if __name__ == "__main__":
    unittest.main()
