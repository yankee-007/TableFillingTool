from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QAction, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMessageBox

from app.data import Store
from app.fonts import configure_font
from app.service import Workspace
from app.theme import COLORS, STYLE
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

    def test_narrow_layout_keeps_primary_controls_inside_window(self):
        self.window.resize(980, 620)
        self.window.title.setText("这是一张具有很长名称的虚构联系人填写与反馈记录工作表")
        APP.processEvents()
        self.assertEqual((self.window.width(), self.window.height()), (980, 620))
        for control in (self.window.import_button, self.window.verify_button, self.window.export_button, self.window.follow_button,
                        self.window.search, self.window.add_row_button, self.window.add_field_button,
                        self.window.contact_settings_button, self.window.open_button):
            self.assertTrue(control.isVisible())
            top = control.mapTo(self.window, QPoint(0, 0))
            bottom = control.mapTo(self.window, control.rect().bottomRight())
            self.assertTrue(self.window.rect().contains(top), control.accessibleName())
            self.assertTrue(self.window.rect().contains(bottom), control.accessibleName())
        self.assertLess(self.window.title.width(), self.window.title.fontMetrics().horizontalAdvance(self.window.title.text()))
        self.assertEqual(self.window.title.toolTip(), self.window.title.text())
        import_pos = self.window.import_button.mapTo(self.window, QPoint(0, 0))
        verify_pos = self.window.verify_button.mapTo(self.window, QPoint(0, 0))
        export_pos = self.window.export_button.mapTo(self.window, QPoint(0, 0))
        self.assertEqual(import_pos.y(), verify_pos.y())
        self.assertGreaterEqual(verify_pos.x(), import_pos.x() + self.window.import_button.width())
        self.assertLess(verify_pos.x() + self.window.verify_button.width(), export_pos.x())

    def test_no_results_action_clears_filter_without_changing_data(self):
        self.window.search.setText("虚构无匹配关键词")
        APP.processEvents()
        self.assertTrue(self.window.table.empty_overlay.isVisible())
        self.assertEqual(self.window.table_empty_action.text(), "清除搜索")
        self.window.table_empty_action.click()
        APP.processEvents()
        self.assertEqual(self.window.search.text(), "")
        self.assertEqual(len(self.sheet.rows), 2)
        self.assertFalse(self.window.table.empty_overlay.isVisible())

    def test_empty_table_action_creates_first_record(self):
        empty = fixture("空表", names=())
        self.workspace.add_sheets([empty])
        self.window.sheet_list.setCurrentRow(1)
        APP.processEvents()
        self.assertTrue(self.window.table.empty_overlay.isVisible())
        self.assertEqual(self.window.table_empty_action.text(), "新增首行")
        self.window.table_empty_action.click()
        APP.processEvents()
        self.assertEqual(len(empty.rows), 1)
        self.assertEqual(self.window.form.key, (empty.id, empty.rows[0].id))
        self.assertFalse(self.window.table.empty_overlay.isVisible())

    def test_small_floating_error_has_readable_status_and_reachable_retry(self):
        floating = self.window.floating
        floating.form.bind(self.window.current_key)
        floating.follow.setChecked(False)
        floating.resize(290, 420)
        floating.show()
        floating.timer.stop()
        APP.processEvents()
        self.enter(floating.form, self.sheet.columns[2].id, "保留的草稿")
        with patch.object(self.store, "save_cells", side_effect=OSError("disk full")):
            self.assertFalse(floating.form.flush())
            APP.processEvents()
            self.assertEqual(floating.form.result.text(), "保存失败")
            self.assertEqual(floating.form.result.property("tone"), "error")
            self.assertTrue(floating.form.error_row.isVisible())
            retry_bottom = floating.form.retry.mapTo(floating, floating.form.retry.rect().bottomRight())
            self.assertTrue(floating.rect().contains(retry_bottom))
            self.assertEqual(floating.form.pending[self.sheet.columns[2].id], "保留的草稿")
        self.assertTrue(floating.form.flush())
        APP.processEvents()
        self.assertFalse(floating.form.error_row.isVisible())
        self.assertEqual(floating.form.result.property("tone"), "success")
        self.assertGreaterEqual(floating.form.result.width(),
                                floating.form.result.fontMetrics().horizontalAdvance(floating.form.result.text()))

    def test_keyboard_focus_reveals_field_below_fold_and_labels_have_buddies(self):
        from app.data import Column
        for index in range(8):
            self.workspace.add_column(self.sheet.id, Column(f"额外填写字段{index}"))
        self.window.resize(980, 620)
        APP.processEvents()
        labels = self.window.form.scroll.widget().findChildren(QLabel)
        self.assertEqual(sum(label.buddy() is not None for label in labels), len(self.sheet.columns))
        last = self.window.form.editors[self.sheet.columns[-1].id]
        self.window.activateWindow()
        last.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.qWait(20)
        center = last.mapTo(self.window.form.scroll.viewport(), last.rect().center())
        self.assertTrue(self.window.form.scroll.viewport().rect().contains(center))
        self.assertEqual(self.window.form.key, (self.sheet.id, self.sheet.rows[0].id))

    def test_status_colors_use_text_and_not_color_alone(self):
        floating = self.window.floating
        self.assertTrue(floating.match_title("py169张三"))
        self.assertEqual(floating.notice.property("tone"), "success")
        self.assertIn("已识别", floating.notice.text())
        self.assertFalse(floating.match_title("未知联系人"))
        self.assertEqual(floating.notice.property("tone"), "warning")
        self.assertIn("未匹配", floating.notice.text())
        floating.follow.setChecked(False)
        self.assertIn("暂停", floating.notice.text())
        self.assertEqual(floating.notice.property("tone"), "idle")

    def test_form_save_status_does_not_wrap_at_minimum_width(self):
        self.window.resize(980, 620)
        APP.processEvents()
        result = self.window.form.result
        self.assertFalse(result.wordWrap())
        self.assertGreaterEqual(result.width(), result.fontMetrics().horizontalAdvance(result.text()))


    def test_sheet_context_menu_targets_clicked_table_and_requires_confirmation(self):
        other = fixture("右键目标")
        self.workspace.add_sheets([other])
        APP.processEvents()
        position = self.window.sheet_list.visualItemRect(self.window.sheet_list.item(1)).center()
        action = QAction("删除此表格…", self.window)
        with patch("app.ui.QMenu") as factory, patch("app.ui.QMessageBox.question", return_value=QMessageBox.StandardButton.No) as confirm:
            factory.return_value.addAction.return_value = action
            factory.return_value.exec.side_effect = lambda point: action.triggered.emit()
            self.window.sheet_context_menu(position)
            self.assertIn("右键目标", confirm.call_args.args[2])
        self.assertEqual(len(self.workspace.sheets), 2)
        with patch("app.ui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.delete_sheet(other.id)
        self.assertEqual(self.workspace.sheets, [self.sheet])
        self.assertEqual(self.window.model.sheet_id, self.sheet.id)

    def test_delete_last_sheet_blocks_failed_save_then_clears_editors_and_cached_verifier(self):
        with patch("app.ui.VerificationDialog.exec", return_value=0):
            self.window.verify_contacts()
        self.window.floating.form.bind(self.window.current_key)
        cid = self.sheet.columns[2].id
        self.enter(self.window.form, cid, "保留输入")
        with patch.object(self.store, "save_cells", side_effect=OSError("disk full")), patch("app.ui.QMessageBox.question") as confirm:
            self.window.delete_sheet(self.sheet.id)
            confirm.assert_not_called()
        self.assertEqual(self.window.form.pending[cid], "保留输入")
        self.assertEqual(len(self.workspace.sheets), 1)
        with patch("app.ui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.delete_sheet(self.sheet.id)
        APP.processEvents()
        self.assertEqual(self.store.load(), [])
        self.assertIsNone(self.window.current_key)
        self.assertIsNone(self.window.form.key)
        self.assertIsNone(self.window.floating.form.key)
        self.assertIsNone(self.window.verifier_dialog)
        self.assertEqual(self.window.stack.currentWidget(), self.window.empty)
        self.assertFalse(self.window.verify_button.isVisible())

    def test_shift_wheel_scrolls_horizontal_for_angle_and_pixel_deltas(self):
        other = fixture("滚动示例", names=tuple(f"虚构{index}" for index in range(50)))
        self.workspace.add_sheets([other])
        self.window.sheet_list.setCurrentRow(1)
        table = self.window.table
        for i in range(table.model().columnCount()):
            table.setColumnWidth(i, 500)
        APP.processEvents()
        horizontal, vertical = table.horizontalScrollBar(), table.verticalScrollBar()
        self.assertGreater(horizontal.maximum(), 0)
        self.assertGreater(vertical.maximum(), 0)

        def wheel(angle, pixel=QPoint(), shift=True):
            event = QWheelEvent(QPointF(30, 30), QPointF(table.viewport().mapToGlobal(QPoint(30, 30))),
                                pixel, angle, Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(table.viewport(), event)

        wheel(QPoint(0, -120), shift=False)
        self.assertGreater(vertical.value(), 0)
        self.assertEqual(horizontal.value(), 0)
        before_vertical = vertical.value()
        wheel(QPoint(0, -120))
        self.assertGreater(horizontal.value(), 0)
        self.assertEqual(vertical.value(), before_vertical)
        before_horizontal = horizontal.value()
        wheel(QPoint(), QPoint(0, -35))
        self.assertEqual(horizontal.value(), before_horizontal + 35)
        wheel(QPoint(0, 120))
        self.assertLess(horizontal.value(), before_horizontal + 35)
        self.assertEqual(vertical.value(), before_vertical)


class ContrastTests(unittest.TestCase):
    def test_semantic_text_and_control_contrast(self):
        def luminance(color):
            rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in rgb]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        def contrast(one, two):
            low, high = sorted((luminance(COLORS[one]), luminance(COLORS[two])))
            return (high + 0.05) / (low + 0.05)

        for foreground, background in (("ink", "surface"), ("muted", "surface"), ("muted", "canvas"),
                                       ("surface", "accent"), ("surface", "navy"),
                                       ("accent_text", "accent_soft"), ("danger", "danger_soft"),
                                       ("warning", "warning_soft")):
            self.assertGreaterEqual(contrast(foreground, background), 4.5, (foreground, background))
        self.assertGreaterEqual(contrast("input_border", "surface"), 3)
        self.assertGreaterEqual(contrast("accent", "surface"), 3)


if __name__ == "__main__":
    unittest.main()
