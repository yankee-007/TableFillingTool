"""Profile-style value/condition filter, operating on a copy until Apply."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QTabWidget, QVBoxLayout, QWidget)

from .filtering import options
from .widgets import FieldComboBox


class ColumnFilterDialog(QDialog):
    def __init__(self, sheet, cid, proxy, parent=None):
        super().__init__(parent)
        self.setWindowTitle("筛选 · " + sheet.column(cid).label)
        self.resize(410, 560)
        self.setMinimumSize(370, 470)
        self.rule = None
        self.sort_order = None
        current = proxy.rules.get(cid, {})
        values = options(sheet, proxy.search, proxy.rules, cid)
        self.selected = set(current.get("values", [value for value, _ in values]))
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        sorting = QHBoxLayout()
        for title, order in (("↑ 升序", Qt.SortOrder.AscendingOrder), ("↓ 降序", Qt.SortOrder.DescendingOrder)):
            btn = QPushButton(title)
            btn.clicked.connect(lambda checked=False, order=order: self.choose_sort(order))
            sorting.addWidget(btn)
        layout.addLayout(sorting)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        value_page = QWidget()
        value_layout = QVBoxLayout(value_page)
        self.option_search = QLineEdit()
        self.option_search.setPlaceholderText("搜索选项，空格分隔多个关键词")
        self.option_search.setAccessibleName("搜索筛选选项")
        self.option_search.setClearButtonEnabled(True)
        value_layout.addWidget(self.option_search)
        self.select_visible = QCheckBox("全部搜索结果")
        value_layout.addWidget(self.select_visible)
        self.values = QListWidget()
        self.values.setAccessibleName("筛选值，可多选")
        for value, count in values:
            item = QListWidgetItem(f"{value or '(空白单元格)'}（{count}）")
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setToolTip(value or "(空白单元格)")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if value in self.selected else Qt.CheckState.Unchecked)
            self.values.addItem(item)
        value_layout.addWidget(self.values, 1)
        self.tabs.addTab(value_page, "按选项")
        condition_page = QWidget()
        condition_layout = QVBoxLayout(condition_page)
        self.condition = FieldComboBox()
        for title, mode in (("包含", "contains"), ("等于", "exact"), ("为空", "empty"), ("不为空", "notempty")):
            self.condition.addItem(title, mode)
        self.condition.setAccessibleName("筛选条件")
        self.condition.setCurrentIndex(max(0, self.condition.findData(current.get("mode", "contains"))))
        condition_layout.addWidget(QLabel("条件"))
        condition_layout.addWidget(self.condition)
        self.condition_value = QLineEdit(current.get("value", ""))
        self.condition_value.setPlaceholderText("条件内容")
        self.condition_value.setAccessibleName("筛选条件内容")
        condition_layout.addWidget(self.condition_value)
        condition_layout.addStretch()
        self.tabs.addTab(condition_page, "按条件")
        self.tabs.setCurrentIndex(0 if current.get("mode", "values") == "values" else 1)
        hint = QLabel("多列条件同时生效；编辑后保留当前列表，点击重新筛选更新。")
        hint.setWordWrap(True)
        hint.setObjectName("caption")
        layout.addWidget(hint)
        actions = QHBoxLayout()
        apply = QPushButton("确定")
        apply.setObjectName("primary")
        apply.clicked.connect(self.apply)
        reset = QPushButton("重置此列")
        reset.clicked.connect(self.clear)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        for btn in (apply, reset, cancel):
            actions.addWidget(btn)
        layout.addLayout(actions)
        self.option_search.textChanged.connect(self.search_options)
        self.select_visible.clicked.connect(self.toggle_visible)
        self.values.itemChanged.connect(self.item_changed)
        self.condition.currentIndexChanged.connect(self.update_condition)
        self.update_condition()
        self.search_options()

    def update_condition(self):
        self.condition_value.setVisible(self.condition.currentData() in ("contains", "exact"))

    def search_options(self):
        tokens = self.option_search.text().strip().casefold().split()
        for i in range(self.values.count()):
            item = self.values.item(i)
            text = (item.data(Qt.ItemDataRole.UserRole) or "(空白单元格)").casefold()
            item.setHidden(bool(tokens) and not any(token in text for token in tokens))
        self.update_select_visible()

    def update_select_visible(self):
        visible = [self.values.item(i) for i in range(self.values.count()) if not self.values.item(i).isHidden()]
        self.select_visible.setText(f"全部搜索结果（{len(visible)} 项）")
        self.select_visible.setChecked(bool(visible) and all(item.checkState() == Qt.CheckState.Checked for item in visible))

    def toggle_visible(self, checked):
        for i in range(self.values.count()):
            item = self.values.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def item_changed(self, item):
        value = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.selected.add(value)
        else:
            self.selected.discard(value)
        self.update_select_visible()

    def choose_sort(self, order):
        self.sort_order = order
        self.accept()

    def apply(self):
        self.rule = ({"mode": "values", "values": sorted(self.selected)} if self.tabs.currentIndex() == 0 else
                     {"mode": self.condition.currentData(), "value": self.condition_value.text()})
        self.accept()

    def clear(self):
        self.rule = {"mode": "clear"}
        self.accept()
