"""Stable table/record/column identities and a transactional, independent local store."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex


@dataclass
class Column:
    label: str
    kind: str = "text"
    options: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)


@dataclass
class Record:
    cells: dict[str, str]
    id: str = field(default_factory=new_id)


@dataclass
class Sheet:
    title: str
    columns: list[Column]
    rows: list[Record] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    id: str = field(default_factory=new_id)

    def row(self, row_id: str) -> Record:
        return next(row for row in self.rows if row.id == row_id)

    def column(self, column_id: str) -> Column:
        return next(column for column in self.columns if column.id == column_id)

    def name(self, row: Record) -> str:
        return row.cells.get(self.settings.get("name_column", ""), "").strip()

    def contact(self, row: Record) -> str:
        remark = row.cells.get(self.settings.get("remark_column", ""), "").strip()
        if remark:
            return remark
        name = self.name(row)
        prefix = self.settings.get("prefix", "") if self.settings.get("use_prefix", True) else ""
        return prefix.strip() + name if name else ""


def infer_settings(columns: list[Column]) -> dict:
    def find(labels):
        return next((col.id for col in columns if col.label.strip().casefold() in labels), "")
    return {
        "name_column": find({"姓名", "学员姓名", "学员名称", "联系人", "name", "联系人姓名"}),
        "remark_column": find({"联系人备注", "企微备注", "微信备注", "备注名", "真实备注", "contact"}),
        "prefix": "", "use_prefix": True, "verify_contact": True, "keep_float": True,
    }


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=3000")
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sheets(
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, columns_json TEXT NOT NULL,
                    settings_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS records(
                    id TEXT PRIMARY KEY, sheet_id TEXT NOT NULL REFERENCES sheets(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL, cells_json TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS records_sheet ON records(sheet_id, position);
            """)
            version = self.connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if version and version[0] != "1":
                raise ValueError("本地数据版本不受支持，请使用匹配版本的工具；原文件已保留")
            self.connection.execute("INSERT OR IGNORE INTO metadata VALUES('schema_version', '1')")

    @staticmethod
    def encode(value) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def load(self) -> list[Sheet]:
        sheets = []
        for sid, title, columns, settings in self.connection.execute("SELECT * FROM sheets ORDER BY rowid"):
            sheet = Sheet(title, [Column(**item) for item in json.loads(columns)],
                          settings=json.loads(settings), id=sid)
            sheet.rows = [Record(json.loads(cells), id=rid) for rid, cells in self.connection.execute(
                "SELECT id,cells_json FROM records WHERE sheet_id=? ORDER BY position,rowid", (sid,))]
            sheets.append(sheet)
        return sheets

    def add_sheets(self, sheets: list[Sheet]):
        # All worksheets from one import are committed together, never half imported.
        with self.connection:
            for sheet in sheets:
                self.connection.execute("INSERT INTO sheets VALUES(?,?,?,?)", (
                    sheet.id, sheet.title, self.encode([asdict(col) for col in sheet.columns]),
                    self.encode(sheet.settings)))
                self.connection.executemany("INSERT INTO records VALUES(?,?,?,?)", (
                    (row.id, sheet.id, index, self.encode(row.cells)) for index, row in enumerate(sheet.rows)))

    def save_cells(self, sheet: Sheet, row: Record, changes: dict[str, str]):
        cells = dict(row.cells, **changes)
        with self.connection:
            cursor = self.connection.execute("UPDATE records SET cells_json=? WHERE id=? AND sheet_id=?",
                                             (self.encode(cells), row.id, sheet.id))
            if cursor.rowcount != 1:
                raise ValueError("记录已不存在，未保存")

    def save_definition(self, sheet: Sheet, *, columns=None, settings=None):
        with self.connection:
            cursor = self.connection.execute("UPDATE sheets SET columns_json=?,settings_json=? WHERE id=?", (
                self.encode([asdict(col) for col in (columns if columns is not None else sheet.columns)]),
                self.encode(settings if settings is not None else sheet.settings), sheet.id))
            if cursor.rowcount != 1:
                raise ValueError("表格已不存在，未保存")

    def add_row(self, sheet: Sheet, row: Record):
        with self.connection:
            self.connection.execute("INSERT INTO records VALUES(?,?,?,?)", (
                row.id, sheet.id, len(sheet.rows), self.encode(row.cells)))

    def delete_rows(self, sheet_id: str, ids: list[str]):
        with self.connection:
            self.connection.executemany("DELETE FROM records WHERE sheet_id=? AND id=?", (
                (sheet_id, rid) for rid in ids))

    def close(self):
        self.connection.close()

    def delete_sheet(self, sheet_id: str):
        with self.connection:
            cursor = self.connection.execute("DELETE FROM sheets WHERE id=?", (sheet_id,))
            if cursor.rowcount != 1:
                raise ValueError("表格已不存在，未删除")
