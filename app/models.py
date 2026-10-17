"""Qt's virtual table model. Display positions never act as persistent record keys."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor

from .filtering import matches, natural_key
from .theme import COLORS
from .icons import icon


class TableModel(QAbstractTableModel):
    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.sheet_id = ""
        self.workspace.cellsChanged.connect(self._changed)
        self.workspace.structureChanged.connect(self._structure)

    @property
    def sheet(self):
        return self.workspace.sheet(self.sheet_id) if self.sheet_id else None

    def use_sheet(self, sid):
        self.beginResetModel()
        self.sheet_id = sid
        self.endResetModel()

    def _structure(self, sid):
        if sid == self.sheet_id:
            self.beginResetModel()
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.sheet.rows) if self.sheet and not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.sheet.columns) if self.sheet and not parent.isValid() else 0

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not self.sheet:
            return None
        row = self.sheet.rows[index.row()]
        column = self.sheet.columns[index.column()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.ToolTipRole):
            return row.cells.get(column.id, "")
        if role == Qt.ItemDataRole.UserRole:
            return row.id

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and self.sheet:
            return self.sheet.columns[section].label if orientation == Qt.Orientation.Horizontal else str(section + 1)

    def flags(self, index):
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or not self.sheet:
            return False
        row, column = self.sheet.rows[index.row()], self.sheet.columns[index.column()]
        return self.workspace.save_values(self.sheet.id, row.id, {column.id: str(value)})

    def _changed(self, sid, rid, changes):
        if sid != self.sheet_id:
            return
        row_index = next((i for i, row in enumerate(self.sheet.rows) if row.id == rid), None)
        if row_index is not None:
            self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.columnCount() - 1),
                                  [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])


class TableFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)
        # Editing a matched field must not make the active record disappear mid-entry.
        self.setDynamicSortFilter(False)
        self.search = ""
        self.rules = {}
        self.frozen = None

    @property
    def active(self):
        return bool(self.search.strip() or self.rules)

    def setFilterFixedString(self, text):
        self.search = text
        self.reapply()

    def reset_query(self):
        self.search, self.rules, self.frozen = "", {}, None
        self.invalidate()
        self._headers_changed()

    def reapply(self):
        sheet = self.sourceModel().sheet
        self.frozen = ({r.id for r in sheet.rows if self.matches_row(r)}
                       if sheet and self.active else None)
        self.invalidate()
        self._headers_changed()

    def _headers_changed(self):
        if self.columnCount():
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount() - 1)

    def matches_row(self, row):
        return matches(row.cells, self.search, self.rules)

    def filterAcceptsRow(self, source_row, parent):
        sheet = self.sourceModel().sheet
        if not sheet or source_row >= len(sheet.rows):
            return False
        row = sheet.rows[source_row]
        return row.id in self.frozen if self.frozen is not None else self.matches_row(row)

    def scope_rows(self):
        sheet = self.sourceModel().sheet
        if not sheet:
            return []
        visible = (sheet.rows[self.mapToSource(self.index(i, 0)).row()] for i in range(self.rowCount()))
        return [row for row in visible if self.matches_row(row)]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and self.active and role in (Qt.ItemDataRole.BackgroundRole,
                                                        Qt.ItemDataRole.ForegroundRole,
                                                        Qt.ItemDataRole.ToolTipRole):
            row = self.sourceModel().sheet.rows[self.mapToSource(index).row()]
            if not self.matches_row(row):
                if role == Qt.ItemDataRole.BackgroundRole:
                    return QColor(COLORS["warning_soft"])
                if role == Qt.ItemDataRole.ForegroundRole:
                    return QColor(COLORS["warning"])
                if role == Qt.ItemDataRole.ToolTipRole:
                    return str(super().data(index, role) or "") + "\n已不符合当前筛选；重新筛选后移除"
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        value = super().headerData(section, orientation, role)
        sheet = self.sourceModel().sheet
        if orientation == Qt.Orientation.Horizontal and sheet and section < len(sheet.columns):
            if role == Qt.ItemDataRole.DisplayRole:
                return str(value) + (" [筛选]" if sheet.columns[section].id in self.rules else "")
            if role == Qt.ItemDataRole.DecorationRole:
                return icon("filter", COLORS["accent"] if sheet.columns[section].id in self.rules else COLORS["muted"])
            if role == Qt.ItemDataRole.ToolTipRole:
                return "单击打开列筛选与排序；Ctrl+Shift+L 筛选当前列"
        return value

    def lessThan(self, left, right):
        return natural_key(str(left.data() or "")) < natural_key(str(right.data() or ""))
