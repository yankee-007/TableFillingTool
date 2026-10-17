"""One write path shared by the table and both independent record editors."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QObject, Signal

from .data import Column, Record, Sheet, Store


class Workspace(QObject):
    sheetsChanged = Signal()
    structureChanged = Signal(str)
    cellsChanged = Signal(str, str, object)
    notice = Signal(str, bool)

    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.sheets = store.load()

    def sheet(self, sid: str) -> Sheet:
        return next(sheet for sheet in self.sheets if sheet.id == sid)

    def save_values(self, sid: str, rid: str, changes: dict[str, str]) -> bool:
        try:
            sheet = self.sheet(sid)
            row = sheet.row(rid)
            clean = {}
            for cid, value in changes.items():
                column = sheet.column(cid)
                if not isinstance(value, str) or "\0" in value or len(value) > 32_000:
                    raise ValueError("单元格需要为不含空字符、最多 32,000 字的文本")
                if column.kind == "date" and value:
                    date.fromisoformat(value)
                if row.cells.get(cid, "") != value:
                    clean[cid] = value
            if not clean:
                return True
            self.store.save_cells(sheet, row, clean)
            row.cells.update(clean)
            self.cellsChanged.emit(sid, rid, clean)
            self.notice.emit("已自动保存到本机", False)
            return True
        except Exception as exc:
            self.notice.emit("保存失败，输入已保留：" + str(exc), True)
            return False

    def add_sheets(self, sheets: list[Sheet]) -> bool:
        try:
            used = {sheet.title for sheet in self.sheets}
            for sheet in sheets:
                base, suffix = sheet.title, 2
                while sheet.title in used:
                    sheet.title = f"{base} ({suffix})"
                    suffix += 1
                used.add(sheet.title)
            self.store.add_sheets(sheets)
            self.sheets.extend(sheets)
            self.sheetsChanged.emit()
            return True
        except Exception as exc:
            self.notice.emit("导入/新建失败，原有表格未改动：" + str(exc), True)
            return False

    def configure(self, sid: str, settings: dict) -> bool:
        try:
            sheet = self.sheet(sid)
            for key in ("name_column", "remark_column"):
                if settings.get(key):
                    sheet.column(settings[key])
            if any(ch in settings.get("prefix", "") for ch in "\r\n\0"):
                raise ValueError("前缀不能包含换行或空字符")
            self.store.save_definition(sheet, settings=settings)
            sheet.settings = dict(settings)
            self.structureChanged.emit(sid)
            return True
        except Exception as exc:
            self.notice.emit("配置未保存：" + str(exc), True)
            return False

    def add_column(self, sid: str, column: Column) -> bool:
        try:
            sheet = self.sheet(sid)
            if not column.label.strip() or any(col.label == column.label for col in sheet.columns):
                raise ValueError("字段名不能为空或重复")
            if len(sheet.columns) >= 200:
                raise ValueError("最多支持 200 列")
            columns = sheet.columns + [column]
            self.store.save_definition(sheet, columns=columns)
            sheet.columns = columns
            self.structureChanged.emit(sid)
            return True
        except Exception as exc:
            self.notice.emit("添加字段失败：" + str(exc), True)
            return False

    def add_row(self, sid: str) -> str:
        try:
            sheet = self.sheet(sid)
            if len(sheet.rows) >= 50_000:
                raise ValueError("每张表最多支持 50,000 条记录")
            row = Record({})
            self.store.add_row(sheet, row)
            sheet.rows.append(row)
            self.structureChanged.emit(sid)
            return row.id
        except Exception as exc:
            self.notice.emit("新增记录失败：" + str(exc), True)
            return ""

    def delete_rows(self, sid: str, ids: list[str]) -> bool:
        try:
            sheet = self.sheet(sid)
            self.store.delete_rows(sid, ids)
            sheet.rows = [row for row in sheet.rows if row.id not in ids]
            self.structureChanged.emit(sid)
            return True
        except Exception as exc:
            self.notice.emit("删除失败：" + str(exc), True)
            return False

    def delete_sheet(self, sid: str) -> bool:
        try:
            self.sheet(sid)
            self.store.delete_sheet(sid)
            self.sheets = [sheet for sheet in self.sheets if sheet.id != sid]
            self.sheetsChanged.emit()
            self.notice.emit("已删除本工具中的表格副本", False)
            return True
        except Exception as exc:
            self.notice.emit("表格删除失败，原有内容已保留：" + str(exc), True)
            return False
