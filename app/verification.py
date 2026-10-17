"""Batch verification decisions, stable identities and global pause hotkey.

Adapted from StudentManagement profile_wechat; never imports the source project.
"""
from collections import Counter
from dataclasses import dataclass
import ctypes
import os
import unicodedata

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QThread, Signal


def normalize(value):
    return "".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def contact_matches(query, observed, mode="contains"):
    # Only known application suffixes are removed; arbitrary remark text is retained.
    actual = str(observed or "").strip()
    for suffix in (" - 企业微信", " - WeCom", " - WXWork"):
        if actual.casefold().endswith(suffix.casefold()):
            actual = actual[:-len(suffix)].strip()
            break
    expected, actual = normalize(query), normalize(actual)
    if not expected or actual in ("企业微信", "wecom", "wxwork"):
        return False
    return expected == actual if mode == "exact" else expected in actual


@dataclass
class VerificationTask:
    rid: str
    value: str
    query: str
    original_result: str = ""
    review: str = ""


def prepare_tasks(sheet, rows, search_cid, result_cid="", prefix=""):
    sheet.column(search_cid)
    if result_cid:
        result = sheet.column(result_cid)
        if result_cid == search_cid or result.kind == "date" or (result.kind == "choice" and "是" not in result.options):
            raise ValueError("结果字段需与搜索字段不同，且能够写入“是”（文本或含“是”的选项）")
    if any(ch in prefix for ch in "\r\n\0"):
        raise ValueError("前缀不能包含换行或空字符")
    prefix = prefix.strip()
    counts = Counter(normalize(prefix + row.cells.get(search_cid, "").strip()) for row in sheet.rows)
    tasks = []
    for row in rows:
        value = row.cells.get(search_cid, "")
        query = prefix + value.strip()
        review = ""
        if not value.strip() or any(ch in query for ch in "\r\n\0"):
            review = "搜索字段为空或包含换行/空字符，保留原值"
        elif counts[normalize(query)] > 1:
            review = "当前表存在重复搜索词，无法唯一确认；保留原值"
        tasks.append(VerificationTask(row.id, value, query, row.cells.get(result_cid, ""), review))
    return tasks


def save_confirmed(workspace, sid, task, search_cid, result_cid):
    """Optimistic guards prevent a queued result overwriting edits or another row."""
    try:
        sheet = workspace.sheet(sid)
        current = sheet.row(task.rid)
        if current.cells.get(search_cid, "") != task.value:
            return "已跳过", "搜索字段已变化，未写入"
        if not result_cid:
            return "已添加", "已确认联系人；未设置写回字段"
        sheet.column(result_cid)
        if current.cells.get(result_cid, "") != task.original_result:
            return "已跳过", "结果字段已变化，未覆盖"
        if not workspace.save_values(sid, task.rid, {result_cid: "是"}):
            return "失败", "结果保存失败，原值保留"
        return "已添加", "已确认联系人；结果字段已写入“是”"
    except (StopIteration, ValueError):
        return "已跳过", "表格、记录或字段已变化，未写入"


class VerificationJob(QThread):
    checked = Signal(str, str, str)

    def __init__(self, desktop, query, mode, parent=None):
        super().__init__(parent)
        self.desktop, self.query, self.mode = desktop, query, mode

    def run(self):
        from .wecom import ContactSearch, ContactNotFoundError
        try:
            result = ContactSearch(self.desktop).verify(self.query, mode=self.mode)
        except ContactNotFoundError as exc:
            result = "未找到", "", str(exc) + "；保留原值"
        except Exception as exc:
            result = "失败", "", str(exc) + "；原值保留，已暂停"
        self.checked.emit(*result)


class F11Hotkey(QAbstractNativeEventFilter):
    # A different ID from StudentManagement; registration never replaces its hotkey.
    KEY_ID = 0x5B42

    def __init__(self, callback):
        super().__init__()
        self.callback, self.registered = callback, False

    def start(self):
        if os.name != "nt":
            raise RuntimeError("联系人验证仅支持 Windows")
        if not ctypes.windll.user32.RegisterHotKey(None, self.KEY_ID, 0x4000, 0x7A):
            raise RuntimeError("F11 已被占用，未开始验证；请先结束其他自动化任务")
        self.registered = True
        QCoreApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        from ctypes.wintypes import MSG
        msg = MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == self.KEY_ID:
            self.callback()
            return True, 0
        return False, 0

    def close(self):
        if self.registered:
            QCoreApplication.instance().removeNativeEventFilter(self)
            ctypes.windll.user32.UnregisterHotKey(None, self.KEY_ID)
            self.registered = False
