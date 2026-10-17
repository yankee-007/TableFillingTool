"""Synthetic profile-query and batch lifecycle regression; no real desktop input."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, Signal, Qt, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from app.data import Column, Record, Sheet, Store, infer_settings
from app.filter_dialog import ColumnFilterDialog
from app.filtering import matches, next_record, options
from app.service import Workspace
from app.ui import MainWindow
from app.verification import contact_matches, prepare_tasks, save_confirmed
from app.verification_dialog import VerificationDialog
from app.wecom import ContactSearch, ContactNotFoundError, Window
from test_core import FakeDesktop, fixture

APP = QApplication.instance() or QApplication([])


class DecisionTests(unittest.TestCase):
    def test_contact_modes_prefix_unicode_and_known_suffix(self):
        self.assertTrue(contact_matches("张三", "py175张三/家长"))
        self.assertFalse(contact_matches("张三", "py175张三", "exact"))
        self.assertTrue(contact_matches("py175张三", "ｐｙ１７５ 张三 - 企业微信", "exact"))
        self.assertFalse(contact_matches("py175张三", "张三/py176", "contains"))
        self.assertFalse(contact_matches("", "张三"))
        self.assertFalse(contact_matches("WeCom", "WeCom"))

    def test_rules_combine_and_blank_multiselect_is_not_no_filter(self):
        rules = {"a": {"mode": "values", "values": [""]}, "b": {"mode": "contains", "value": " ok "}}
        self.assertTrue(matches({"a": "", "b": "OKAY"}, "", rules))
        self.assertFalse(matches({"a": "yes", "b": "OKAY"}, "", rules))
        self.assertFalse(matches({"a": ""}, "", {"a": {"mode": "values", "values": []}}))
        for mode, good, bad in (("empty", "  ", "x"), ("notempty", "x", "  "), ("exact", " OK ", "OKAY")):
            rule = {"a": {"mode": mode, "value": "ok"}}
            self.assertTrue(matches({"a": good}, "", rule))
            self.assertFalse(matches({"a": bad}, "", rule))

    def test_options_respect_other_columns_but_skip_current_column(self):
        a, b = Column("姓名"), Column("结果")
        sheet = Sheet("示例", [a, b], [Record({a.id: "张三", b.id: ""}), Record({a.id: "李四", b.id: "是"})], {})
        rules = {a.id: {"mode": "exact", "value": "张三"}, b.id: {"mode": "notempty"}}
        self.assertEqual(options(sheet, "", rules, a.id), [("李四", 1)])
        self.assertEqual(options(sheet, "", rules, b.id), [("", 1)])

    def test_reapply_chooses_next_then_previous(self):
        self.assertEqual(next_record(["1", "3", "4"], "2", ["1", "2", "3", "4"]), "3")
        self.assertEqual(next_record(["1"], "2", ["1", "2", "3"]), "1")
        self.assertEqual(next_record([], "2", ["1", "2"]), None)

    def test_tasks_check_duplicates_outside_filter_and_keep_empty(self):
        sheet = fixture(names=("张三", "张三", ""))
        cid = sheet.settings["name_column"]
        tasks = prepare_tasks(sheet, [sheet.rows[0], sheet.rows[2]], cid, prefix="py175")
        self.assertIn("重复", tasks[0].review)
        self.assertIn("为空", tasks[1].review)
        self.assertEqual(tasks[0].query, "py175张三")
        self.assertEqual(prepare_tasks(sheet, [], cid), [])

    def test_result_field_is_validated_before_any_desktop_action(self):
        sheet = fixture()
        cid = sheet.settings["name_column"]
        with self.assertRaisesRegex(ValueError, "不同"):
            prepare_tasks(sheet, sheet.rows, cid, cid)
        for col in (Column("日期", "date"), Column("状态", "choice", ["未验证", "否"])):
            sheet.columns.append(col)
            with self.assertRaises(ValueError):
                prepare_tasks(sheet, sheet.rows, cid, col.id)
        with self.assertRaises(ValueError):
            prepare_tasks(sheet, sheet.rows, cid, prefix="a\nb")

    def test_desktop_verification_closes_only_confirmed_chat(self):
        desktop = FakeDesktop("py169张三 - 企业微信")
        search = ContactSearch(desktop, wait=0, sleep=lambda _: None)
        self.assertEqual(search.verify("py169张三", mode="exact")[0], "已添加")
        self.assertEqual(desktop.events[-1], ("ctrl", "w"))
        desktop = FakeDesktop("py169张三/家长")
        search = ContactSearch(desktop, wait=0, sleep=lambda _: None)
        state, observed, detail = search.verify("py169张三", mode="exact")
        self.assertEqual(state, "待确认")
        self.assertEqual(observed, "py169张三/家长")
        self.assertNotIn(("ctrl", "w"), desktop.events)

    def test_search_timeout_and_focus_loss_are_distinct(self):
        desktop = FakeDesktop()
        desktop.keys = lambda *keys: desktop.events.append(keys)  # no float opens
        ticks = iter([0, 0, 1])
        search = ContactSearch(desktop, wait=0, timeout=.5, sleep=lambda _: None, clock=lambda: next(ticks))
        with self.assertRaises(ContactNotFoundError):
            search.verify("py169张三")
        desktop.after_search = Window(99, 8, "other", "other.exe")
        desktop.keys = FakeDesktop.keys.__get__(desktop)
        with self.assertRaisesRegex(RuntimeError, "焦点"):
            ContactSearch(desktop, wait=0, sleep=lambda _: None).verify("py169张三")


class ControlledJob(QObject):
    checked = Signal(str, str, str)
    finished = Signal()

    def __init__(self, desktop, query, mode, parent):
        super().__init__(parent)
        self.query, self.mode = query, mode

    def start(self):
        pass

    def complete(self, state="已添加", observed="虚构联系人", detail="模拟结果"):
        self.checked.emit(state, observed, detail)
        self.finished.emit()


class QueryAndBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "tables.sqlite3")
        self.workspace = Workspace(self.store)
        self.sheet = fixture(names=("张三", "李四", "王五"))
        self.result = Column("微信", "choice", ["是", "否"])
        self.sheet.columns.append(self.result)
        self.workspace.add_sheets([self.sheet])
        self.window = MainWindow(self.workspace)
        self.window.show()
        APP.processEvents()
        self.search_cid = self.sheet.settings["name_column"]
        self.dialog = VerificationDialog(self.workspace, self.sheet, self.window.filter.scope_rows, self.window)
        self.dialog.result_field.setCurrentIndex(self.dialog.result_field.findData(self.result.id))
        self.patches = [patch("app.verification_dialog.NativeDesktop", return_value=FakeDesktop()),
                        patch("app.verification_dialog.VerificationJob", ControlledJob),
                        patch.object(self.dialog.hotkey, "start"), patch.object(self.dialog.hotkey, "close")]
        for item in self.patches:
            item.start()

    def tearDown(self):
        if self.dialog.active:
            self.dialog.stop()
            if self.dialog.job:
                self.dialog.job.complete("失败")
        self.dialog.close()
        self.window.close()
        APP.clipboard().clear()
        self.dialog.deleteLater()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        APP.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.store.close()
        self.temp.cleanup()

    def start(self):
        self.dialog.start()
        APP.processEvents()

    def test_defaults_and_batch_writes_by_identity_in_sorted_view(self):
        self.assertEqual(self.dialog.prefix.text(), "")
        self.assertEqual(self.dialog.mode.currentData(), "contains")
        self.window.filter.sort(0, Qt.SortOrder.DescendingOrder)
        ids = [r.id for r in self.window.filter.scope_rows()]
        self.start()
        while self.dialog.job:
            self.dialog.job.complete()
        self.assertEqual([t.rid for t in self.dialog.tasks], ids)
        self.assertEqual([r.cells[self.result.id] for r in self.sheet.rows], ["是"] * 3)
        self.assertEqual([r.cells[self.result.id] for r in self.store.load()[0].rows], ["是"] * 3)
        self.assertFalse(self.dialog.active)

    def test_frozen_rows_are_marked_and_excluded_from_batch_scope(self):
        rule = {"mode": "empty"}
        self.window.set_column_filter(self.result.id, rule)
        self.workspace.save_values(self.sheet.id, self.sheet.rows[0].id, {self.result.id: "是"})
        self.assertEqual(self.window.filter.rowCount(), 3)
        self.assertEqual(len(self.window.filter.scope_rows()), 2)
        self.assertIn("1 条已不符合", self.window.summary.text())
        index = self.window.filter.mapFromSource(self.window.model.index(0, 0))
        self.assertIsNotNone(index.data(Qt.ItemDataRole.BackgroundRole))
        self.assertIn("重新筛选", index.data(Qt.ItemDataRole.ToolTipRole))
        self.start()
        self.assertEqual(len(self.dialog.tasks), 2)
        self.assertNotIn(self.sheet.rows[0].id, [t.rid for t in self.dialog.tasks])

    def test_reapply_keeps_cursor_continuity_and_sort_does_not_refresh(self):
        self.window.set_column_filter(self.result.id, {"mode": "empty"})
        self.window.select_record(self.sheet.rows[1].id)
        self.workspace.save_values(self.sheet.id, self.sheet.rows[1].id, {self.result.id: "是"})
        self.window.filter.sort(0, Qt.SortOrder.AscendingOrder)
        self.assertEqual(self.window.filter.rowCount(), 3)
        self.window.filter.sort(-1)
        self.window.reapply_filter()
        self.assertEqual(self.window.current_key[1], self.sheet.rows[2].id)
        self.assertEqual(self.window.filter.rowCount(), 2)

    def test_zero_filter_never_verifies_entire_table(self):
        self.window.set_column_filter(self.result.id, {"mode": "values", "values": []})
        self.start()
        self.assertFalse(self.dialog.active)
        self.assertIsNone(self.dialog.job)
        self.assertIn("没有匹配记录", self.dialog.notice.text())

    def test_no_writeback_keeps_cells_and_hotkey_conflict_starts_nothing(self):
        self.dialog.result_field.setCurrentIndex(0)
        APP.clipboard().setText("原始内容")
        with patch.object(self.dialog.hotkey, "start", side_effect=RuntimeError("F11 已被占用")):
            self.start()
        self.assertFalse(self.dialog.active)
        self.assertEqual(APP.clipboard().text(), "原始内容")
        self.start()
        self.dialog.stop()
        self.dialog.job.complete()
        self.assertEqual(self.dialog.results.item(0, 1).text(), "已添加")
        self.assertNotIn(self.result.id, self.sheet.rows[0].cells)

    def test_pause_and_stop_finish_current_contact_preserve_pending(self):
        self.start()
        self.dialog.toggle_pause()
        self.assertIsNotNone(self.dialog.job)
        self.dialog.job.complete()
        self.assertTrue(self.dialog.paused)
        self.assertIsNone(self.dialog.job)
        self.dialog.toggle_pause()
        self.assertEqual(self.dialog.job.query, "李四")
        self.dialog.stop()
        self.dialog.job.complete()
        self.assertFalse(self.dialog.active)
        self.assertEqual(self.dialog.results.item(2, 1).text(), "待验证")
        self.assertEqual(self.sheet.rows[0].cells[self.result.id], "是")
        self.assertNotIn(self.result.id, self.sheet.rows[2].cells)

    def test_unconfirmed_missing_and_failed_contacts_continue_without_any_write(self):
        self.sheet.rows[0].cells[self.result.id] = "否"
        original = [dict(row.cells) for row in self.sheet.rows]
        self.start()
        with patch.object(self.workspace, "save_values", wraps=self.workspace.save_values) as save:
            for i, state in enumerate(("待确认", "未找到", "失败")):
                self.assertEqual(self.dialog.job.query, self.sheet.rows[i].cells[self.search_cid])
                self.dialog.job.complete(state, "其他联系人" if i == 0 else "", "未通过")
                self.assertFalse(self.dialog.paused)
                self.assertFalse(self.dialog.pause_requested)
                self.assertEqual(self.dialog.results.item(i, 1).text(), state)
                if i < 2:
                    self.assertIsNotNone(self.dialog.job)
            save.assert_not_called()
        self.assertFalse(self.dialog.active)
        self.assertEqual([row.cells for row in self.sheet.rows], original)

    def test_explicit_pause_still_applies_after_failed_contact(self):
        self.start()
        self.dialog.toggle_pause()
        self.dialog.job.complete("失败", "", "焦点变化")
        self.assertTrue(self.dialog.paused)
        self.assertIsNone(self.dialog.job)
        self.dialog.toggle_pause()
        self.assertEqual(self.dialog.job.query, "李四")

    def test_result_or_identity_changes_while_running_are_not_overwritten(self):
        self.start()
        self.workspace.save_values(self.sheet.id, self.sheet.rows[0].id, {self.result.id: "人工记录"})
        self.dialog.job.complete()
        self.assertEqual(self.dialog.results.item(0, 1).text(), "已跳过")
        self.assertEqual(self.sheet.rows[0].cells[self.result.id], "人工记录")
        self.workspace.save_values(self.sheet.id, self.sheet.rows[1].id, {self.search_cid: "新名字"})
        self.dialog.job.complete()
        self.assertEqual(self.dialog.results.item(1, 1).text(), "已跳过")

    def test_failed_disk_write_reports_failure_and_preserves_memory(self):
        self.start()
        with patch.object(self.store, "save_cells", side_effect=OSError("disk full")):
            self.dialog.job.complete()
        self.assertEqual(self.dialog.results.item(0, 1).text(), "失败")
        self.assertNotIn(self.result.id, self.sheet.rows[0].cells)
        self.assertFalse(self.dialog.paused)
        self.assertFalse(self.dialog.pause_requested)
        self.assertEqual(self.dialog.job.query, "李四")

    def test_clipboard_restored_but_intervening_user_copy_is_preserved(self):
        APP.clipboard().setText("原始剪贴板")
        self.start()
        self.dialog.toggle_pause()
        self.dialog.job.complete()
        self.assertEqual(APP.clipboard().text(), "原始剪贴板")
        self.dialog.toggle_pause()
        APP.clipboard().setText("用户新复制的内容")
        self.dialog.stop()
        self.dialog.job.complete("失败")
        self.assertEqual(APP.clipboard().text(), "用户新复制的内容")

    def test_value_dialog_search_selects_only_visible_options_and_cancel_is_local(self):
        dialog = ColumnFilterDialog(self.sheet, self.search_cid, self.window.filter, self.window)
        dialog.option_search.setText("张三 王五")
        dialog.toggle_visible(False)
        self.assertEqual(dialog.selected, {"李四"})
        dialog.reject()
        self.assertEqual(self.window.filter.rules, {})

    def test_clear_filters_and_schema_change_recompute_but_new_row_stays_out(self):
        self.window.set_column_filter(self.result.id, {"mode": "empty"})
        self.workspace.add_row(self.sheet.id)
        self.assertEqual(self.window.filter.rowCount(), 3)
        self.workspace.add_column(self.sheet.id, Column("新字段"))
        self.assertEqual(self.window.filter.rowCount(), 4)
        self.window.clear_filters()
        self.assertFalse(self.window.filter.active)


if __name__ == "__main__":
    unittest.main()
