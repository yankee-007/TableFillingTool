"""Qt's virtual table model. Display positions never act as persistent record keys."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt


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
