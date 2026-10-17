"""Independent desktop workbench and chat-following editor."""
from __future__ import annotations

import copy
from pathlib import Path

import shiboken6
from PySide6.QtCore import QEvent, QMimeData, QModelIndex, QSignalBlocker, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemDelegate, QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSplitter,
    QStackedWidget, QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
)

from .data import Column, Record, Sheet, infer_settings
from .files import export_file, import_file
from .matching import candidates
from .models import TableFilter, TableModel
from .wecom import ContactSearch, NativeDesktop


def label(text, name="muted"):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback, *, primary=False, name=""):
    widget = QPushButton(text)
    widget.setObjectName("primary" if primary else name)
    widget.setAccessibleName(text)
    widget.clicked.connect(callback)
    return widget


class Job(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.succeeded.emit(self.operation())
        except Exception as exc:
            self.failed.emit(str(exc))


class CellDelegate(QStyledItemDelegate):
    """Do not discard a failed table edit on focus loss; bind to immutable row IDs."""
    def __init__(self, workspace, parent):
        super().__init__(parent)
        self.workspace, self.editor, self.key = workspace, None, None

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setMaxLength(32_000)
        source = index.model().mapToSource(index)
        sheet = index.model().sourceModel().sheet
        self.key = sheet.id, sheet.rows[source.row()].id, sheet.columns[source.column()].id
        self.editor = editor
        editor.setAccessibleName(sheet.columns[source.column()].label)
        return editor

    def flush(self):
        if self.editor is None or not shiboken6.isValid(self.editor):
            self.editor = None
            return True
        editor = self.editor
        sid, rid, cid = self.key
        if not self.workspace.save_values(sid, rid, {cid: editor.text()}):
            QTimer.singleShot(0, editor.setFocus)
            return False
        self.editor = None
        self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)
        return True

    def eventFilter(self, editor, event):
        if editor is self.editor:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                    self.flush()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.editor = None
                    self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.RevertModelCache)
                    return True
            if event.type() == QEvent.Type.FocusOut:
                self.flush()
                return True
        return super().eventFilter(editor, event)


class RecordForm(QWidget):
    """Stable editors with buffered input captured against one record identity."""
    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.key = None
        self.signature = None
        self.pending = {}
        self.editors = {}
        self.loading = False
        self.setObjectName("editorCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        self.heading = label("选择一条记录", "section")
        self.summary = label("在表格中选择联系人，在这里集中填写。")
        layout.addWidget(self.heading)
        layout.addWidget(self.summary)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll, 1)
        self.result = label("修改后自动保存到本机")
        self.result.setAccessibleName("填写保存状态")
        layout.addWidget(self.result)
        self.retry = button("重试保存", self.flush)
        self.retry.hide()
        layout.addWidget(self.retry)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(450)
        self.timer.timeout.connect(self.flush)
        self.workspace.cellsChanged.connect(self._external_change)

    def bind(self, key) -> bool:
        changed_key = key != self.key
        if changed_key:
            QApplication.inputMethod().commit()
            if not self.flush():
                return False
        sheet, row = None, None
        if key:
            try:
                sheet = self.workspace.sheet(key[0])
                row = sheet.row(key[1])
            except StopIteration:
                key = None
        signature = (sheet.id, tuple((col.id, col.label, col.kind, tuple(col.options)) for col in sheet.columns)) if key else None
        if signature != self.signature:
            if not self.flush():
                return False
            self.loading = True
            self.editors = {}
            content = QWidget()
            form = QVBoxLayout(content)
            form.setContentsMargins(0, 0, 8, 0)
            form.setSpacing(6)
            if sheet:
                for col in sheet.columns:
                    form.addWidget(label(col.label, "section"))
                    if col.kind == "multiline":
                        editor = QPlainTextEdit()
                        editor.setMaximumHeight(120)
                        editor.setMinimumHeight(80)
                        editor.textChanged.connect(lambda cid=col.id: self._queue(cid))
                    elif col.kind == "choice":
                        editor = QComboBox()
                        for option in col.options:
                            editor.addItem(option, option)
                        editor.addItem("未填写（清空）", "")
                        editor.currentTextChanged.connect(lambda _, cid=col.id: self._queue(cid))
                    else:
                        editor = QLineEdit()
                        editor.setMaxLength(32_000)
                        if col.kind == "date":
                            editor.setPlaceholderText("YYYY-MM-DD；留空可清除")
                        editor.textEdited.connect(lambda _, cid=col.id: self._queue(cid))
                        editor.returnPressed.connect(self.flush)
                    editor.setObjectName("field_" + col.id)
                    editor.setAccessibleName(col.label)
                    self.editors[col.id] = editor
                    form.addWidget(editor)
                    form.addSpacing(6)
            form.addStretch()
            old = self.scroll.takeWidget()
            self.scroll.setWidget(content)
            if old:
                old.deleteLater()
            self.signature = signature
            self.loading = False
        self.key = key
        if not key:
            self.heading.setText("等待选择联系人")
            self.summary.setText("选择一条记录后，填写字段会显示在这里。")
            return True
        self.heading.setText(sheet.name(row) or "未填写姓名")
        self.summary.setText(sheet.title + " · 当前记录")
        self._update_values(row, force=changed_key)
        return True

    def _get(self, editor):
        if isinstance(editor, QPlainTextEdit):
            return editor.toPlainText()
        if isinstance(editor, QComboBox):
            return editor.currentData() or ""
        return editor.text()

    def _update_values(self, row, force=False):
        self.loading = True
        for cid, editor in self.editors.items():
            if not force and (cid in self.pending or editor.hasFocus()):
                continue
            value = row.cells.get(cid, "")
            with QSignalBlocker(editor):
                if isinstance(editor, QPlainTextEdit):
                    if editor.toPlainText() != value:
                        editor.setPlainText(value)
                elif isinstance(editor, QComboBox):
                    if editor.findData(value) < 0:
                        editor.addItem(value, value)
                    editor.setCurrentIndex(editor.findData(value))
                else:
                    if editor.text() != value:
                        editor.setText(value)
        self.loading = False

    def _queue(self, cid):
        if self.loading or not self.key:
            return
        self.pending[cid] = self._get(self.editors[cid])
        self.result.setText("正在保存…")
        self.timer.start()

    def flush(self) -> bool:
        self.timer.stop()
        if not self.pending or not self.key:
            return True
        if self.workspace.save_values(*self.key, dict(self.pending)):
            self.pending.clear()
            self.result.setText("已自动保存到本机")
            self.result.setStyleSheet("color: #166534")
            self.retry.hide()
            self.bind(self.key)
            return True
        self.result.setText("保存失败，输入已保留；请重试后再切换。")
        self.result.setStyleSheet("color: #B91C1C")
        self.retry.show()
        return False

    def _external_change(self, sid, rid, changes):
        if self.key == (sid, rid):
            sheet = self.workspace.sheet(sid)
            self.heading.setText(sheet.name(sheet.row(rid)) or "未填写姓名")
            self._update_values(sheet.row(rid))


class ContactDialog(QDialog):
    def __init__(self, sheet, parent):
        super().__init__(parent)
        self.setWindowTitle("联系人设置 · " + sheet.title)
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.addWidget(label("指定用于打开和识别聊天的字段", "section"))
        layout.addWidget(label("联系人备注优先；为空时使用「前缀 + 姓名」。每张表独立保存配置。"))
        form = QFormLayout()
        self.name = QComboBox()
        self.remark = QComboBox()
        for widget in (self.name, self.remark):
            widget.addItem("不使用", "")
            for column in sheet.columns:
                widget.addItem(column.label, column.id)
        self.name.setCurrentIndex(max(0, self.name.findData(sheet.settings.get("name_column", ""))))
        self.remark.setCurrentIndex(max(0, self.remark.findData(sheet.settings.get("remark_column", ""))))
        self.prefix = QLineEdit(sheet.settings.get("prefix", ""))
        self.prefix.setPlaceholderText("例如 py169（直接与姓名拼接）")
        self.use_prefix = QCheckBox("使用姓名前缀")
        self.use_prefix.setChecked(sheet.settings.get("use_prefix", True))
        self.verify = QCheckBox("用独立聊天窗口验证联系人")
        self.verify.setChecked(sheet.settings.get("verify_contact", True))
        self.keep = QCheckBox("保留企业微信独立聊天窗口")
        self.keep.setChecked(sheet.settings.get("keep_float", True))
        self.keep.setEnabled(self.verify.isChecked())
        self.verify.toggled.connect(self.keep.setEnabled)
        form.addRow("姓名列", self.name)
        form.addRow("联系人备注列", self.remark)
        form.addRow("姓名前缀", self.prefix)
        form.addRow("", self.use_prefix)
        form.addRow("", self.verify)
        form.addRow("", self.keep)
        layout.addLayout(form)
        layout.addWidget(label("只搜索和打开联系人，不发送消息、不修改备注。关闭验证后需自行核对搜索结果，且无法保证浮窗自动识别。"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for widget, text in ((self.name, "姓名列"), (self.remark, "联系人备注列"), (self.prefix, "姓名前缀")):
            widget.setAccessibleName(text)

    def settings(self):
        return {"name_column": self.name.currentData(), "remark_column": self.remark.currentData(),
                "prefix": self.prefix.text().strip(), "use_prefix": self.use_prefix.isChecked(),
                "verify_contact": self.verify.isChecked(), "keep_float": self.keep.isChecked()}


class FieldDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("添加字段")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.kind = QComboBox()
        for title, key in (("单行文本", "text"), ("多行文本", "multiline"), ("下拉选项", "choice"), ("日期", "date")):
            self.kind.addItem(title, key)
        self.options = QPlainTextEdit()
        self.options.setPlaceholderText("每行一个选项（仅下拉字段使用）")
        self.options.setMaximumHeight(120)
        self.options.setEnabled(False)
        self.kind.currentIndexChanged.connect(lambda: self.options.setEnabled(self.kind.currentData() == "choice"))
        layout.addRow("字段名称", self.name)
        layout.addRow("填写方式", self.kind)
        layout.addRow("选项", self.options)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("添加")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def column(self):
        return Column(self.name.text().strip(), self.kind.currentData(),
                      list(dict.fromkeys(line.strip() for line in self.options.toPlainText().splitlines() if line.strip())))


class FloatingWindow(QWidget):
    def __init__(self, workspace, owner, probe=None):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.workspace, self.owner = workspace, owner
        self.setObjectName("floating")
        self.setWindowTitle("随聊填写 · TableFillingTool")
        self.resize(350, 670)
        self.setMinimumSize(290, 380)
        self.probe = probe
        self.last_title = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        header.addWidget(label("随聊填写", "section"), 1)
        self.pin = QCheckBox("置顶")
        self.pin.setChecked(True)
        self.pin.toggled.connect(self._pin)
        header.addWidget(self.pin)
        layout.addLayout(header)
        self.scope = QComboBox()
        self.scope.setAccessibleName("浮窗识别范围")
        self.scope.currentIndexChanged.connect(self._scope_changed)
        layout.addWidget(self.scope)
        self.follow = QCheckBox("自动跟随企业微信独立聊天窗口")
        self.follow.setChecked(True)
        layout.addWidget(self.follow)
        self.notice = label("激活企业微信独立聊天窗口以识别联系人。", "banner")
        self.notice.setAccessibleName("聊天识别状态")
        layout.addWidget(self.notice)
        self.form = RecordForm(workspace)
        layout.addWidget(self.form, 1)
        layout.addWidget(button("使用主表所选记录（手动填写）", self.use_current))
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.poll)
        self.workspace.sheetsChanged.connect(self._scopes)
        self.workspace.structureChanged.connect(self._structure)
        self._scope_id = ""
        self._scopes()

    def _pin(self, checked):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _scopes(self):
        scope = self.scope.currentData() or ""
        with QSignalBlocker(self.scope):
            self.scope.clear()
            self.scope.addItem("自动识别 · 所有表格", "")
            for sheet in self.workspace.sheets:
                self.scope.addItem(sheet.title, sheet.id)
            self.scope.setCurrentIndex(max(0, self.scope.findData(scope)))

    def _scope_changed(self):
        scope = self.scope.currentData() or ""
        if not self.form.flush():
            with QSignalBlocker(self.scope):
                self.scope.setCurrentIndex(max(0, self.scope.findData(self._scope_id)))
            return
        self._scope_id = scope
        if self.last_title:
            self.match_title(self.last_title)

    def _structure(self, sid):
        if self.form.key and self.form.key[0] == sid:
            self.form.bind(self.form.key)

    def use_current(self):
        if self.owner.current_key and self.form.bind(self.owner.current_key):
            self.follow.setChecked(False)
            self.notice.setText("手动填写中 · 勾选自动跟随可恢复聊天识别。")

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start()

    def closeEvent(self, event):
        QApplication.inputMethod().commit()
        if not self.form.flush():
            event.ignore()
            return
        self.timer.stop()
        event.accept()

    def poll(self):
        if not self.follow.isChecked() or self.owner.contact_busy:
            return
        try:
            if self.probe is None:
                self.probe = NativeDesktop()
            window = self.probe.foreground()
        except Exception as exc:
            self.notice.setText(str(exc))
            return
        if window and window.is_wecom and window.title not in ("企业微信", "WeCom"):
            self.last_title = window.title
            self.match_title(window.title)

    def match_title(self, title):
        matches = candidates(self.workspace.sheets, title, self.scope.currentData() or "")
        key = matches[0] if len(matches) == 1 else None
        if not self.form.bind(key):
            self.notice.setText("保存失败，已暂停切换；请先重试保存当前输入。")
            return False
        if len(matches) > 1:
            self.notice.setText("匹配到多条记录。请限定表格，或填写唯一的联系人备注；不会自动选择。")
        elif not matches:
            self.notice.setText("当前聊天未匹配。请检查姓名列、备注和前缀设置。")
        else:
            self.notice.setText("已跟随当前聊天 · 修改后自动保存")
        return len(matches) == 1


class MainWindow(QMainWindow):
    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.current_key = None
        self._filter_text = ""
        self._selecting = False
        self.file_job = None
        self.contact_job = None
        self._clipboard_backup = None
        self.setWindowTitle("TableFillingTool · 随聊填表")
        self.resize(1320, 820)
        self.setMinimumSize(980, 620)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(208)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 24, 12, 16)
        side.setSpacing(12)
        side.addWidget(label("随聊填表", "brand"))
        side.addWidget(label("TableFillingTool"))
        side.addSpacing(20)
        side.addWidget(label("我的表格", "section"))
        self.sheet_list = QListWidget()
        self.sheet_list.setAccessibleName("我的表格")
        self.sheet_list.currentRowChanged.connect(self._select_sheet)
        side.addWidget(self.sheet_list, 1)
        side.addWidget(button("新建表格", self.new_sheet))
        side.addWidget(label("本机保存 · 无需平台账号\n只打开联系人，不发送消息"))
        outer.addWidget(sidebar)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 22, 24, 16)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        title_stack = QVBoxLayout()
        self.title = label("把表格和聊天放在一起", "title")
        self.subtitle = label("导入名单，打开联系人，在浮窗中完成填写。")
        title_stack.addWidget(self.title)
        title_stack.addWidget(self.subtitle)
        heading.addLayout(title_stack, 1)
        self.import_button = button("导入表格", self.import_dialog, primary=True)
        self.export_button = button("导出当前表", self.export_dialog)
        heading.addWidget(self.import_button)
        heading.addWidget(self.export_button)
        layout.addLayout(heading)
        self.stack = QStackedWidget()
        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.addStretch()
        empty_title = label("从一张表开始", "title")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        empty_description = label("支持 Excel（.xlsx）与 CSV\n第一行作为字段名，每行作为一位联系人。\n原文件保持不变，填写内容自动保存在本机。")
        empty_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_description)
        empty_actions = QHBoxLayout()
        empty_actions.addStretch()
        empty_actions.addWidget(button("导入我的表格", self.import_dialog, primary=True))
        empty_actions.addWidget(button("创建空白表格", self.new_sheet))
        empty_actions.addWidget(button("体验虚构示例", self.sample))
        empty_actions.addStretch()
        empty_layout.addLayout(empty_actions)
        empty_layout.addStretch()
        self.stack.addWidget(self.empty)
        self.workbench = QWidget()
        work = QVBoxLayout(self.workbench)
        work.setContentsMargins(0, 0, 0, 0)
        work.setSpacing(12)
        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索当前表格…")
        self.search.setAccessibleName("搜索当前表格")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(320)
        tools.addWidget(self.search, 1)
        tools.addWidget(button("重新筛选", self.reapply_filter))
        tools.addWidget(button("新增行", self.add_row))
        tools.addWidget(button("添加字段", self.add_column))
        tools.addStretch()
        tools.addWidget(button("联系人设置", self.configure))
        tools.addWidget(button("聊天跟随浮窗", self.show_floating, primary=True))
        work.addLayout(tools)
        self.summary = label("双击单元格编辑；也可在右侧集中填写。")
        work.addWidget(self.summary)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableView()
        self.table.setAccessibleName("联系人表格")
        self.model = TableModel(workspace)
        self.filter = TableFilter()
        self.filter.setSourceModel(self.model)
        self.table.setModel(self.filter)
        self.delegate = CellDelegate(workspace, self.table)
        self.table.setItemDelegate(self.delegate)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setDefaultSectionSize(155)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.selectionModel().currentChanged.connect(self._selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        delete = QAction("删除选中的行…", self.table)
        delete.triggered.connect(self.delete_rows)
        self.table.addAction(delete)
        splitter.addWidget(self.table)
        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 0, 0, 0)
        self.open_button = button("打开企微联系人   F8", self.open_contact, primary=True)
        editor_layout.addWidget(self.open_button)
        self.form = RecordForm(workspace)
        editor_layout.addWidget(self.form, 1)
        editor.setMinimumWidth(260)
        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([760, 300])
        work.addWidget(splitter, 1)
        self.stack.addWidget(self.workbench)
        layout.addWidget(self.stack, 1)
        outer.addWidget(body, 1)
        self.status = label("已就绪 · 数据仅保存在本机")
        self.statusBar().addWidget(self.status, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(140)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.floating = FloatingWindow(workspace, self)
        self.search.textChanged.connect(self._filter_changed)
        self.workspace.sheetsChanged.connect(self._refresh_sheets)
        self.workspace.structureChanged.connect(self._structure)
        self.workspace.notice.connect(self.show_notice)
        self._shortcuts()
        self._refresh_sheets()

    @property
    def contact_busy(self):
        return self.contact_job is not None

    def show_notice(self, text, error=False):
        self.status.setText(text)
        self.status.setStyleSheet("color: #B91C1C" if error else "color: #475569")

    def _shortcuts(self):
        for key, callback in (("Ctrl+O", self.import_dialog), ("Ctrl+N", self.new_sheet),
                              ("Ctrl+Shift+S", self.export_dialog), ("Ctrl+S", self.flush_all),
                              ("Ctrl+Shift+F", self.show_floating), ("F8", self.open_contact)):
            action = QAction(self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(callback)
            self.addAction(action)

    def flush_all(self):
        QApplication.inputMethod().commit()
        return self.delegate.flush() and self.form.flush() and self.floating.form.flush()

    def _refresh_sheets(self):
        current = self.model.sheet_id
        with QSignalBlocker(self.sheet_list):
            self.sheet_list.clear()
            for sheet in self.workspace.sheets:
                item = QListWidgetItem(f"{sheet.title}\n{len(sheet.rows)} 条记录")
                item.setData(Qt.ItemDataRole.UserRole, sheet.id)
                item.setToolTip(sheet.title)
                self.sheet_list.addItem(item)
            target = next((i for i, sheet in enumerate(self.workspace.sheets) if sheet.id == current), 0)
            self.sheet_list.setCurrentRow(target if self.workspace.sheets else -1)
        self._select_sheet(self.sheet_list.currentRow())

    def _select_sheet(self, index):
        if self._selecting:
            return
        sid = self.workspace.sheets[index].id if 0 <= index < len(self.workspace.sheets) else ""
        if sid == self.model.sheet_id and sid:
            return
        if not self.flush_all():
            with QSignalBlocker(self.sheet_list):
                previous = next((i for i, s in enumerate(self.workspace.sheets) if s.id == self.model.sheet_id), -1)
                self.sheet_list.setCurrentRow(previous)
            return
        self._selecting = True
        self.current_key = None
        self.form.bind(None)
        self.model.use_sheet(sid)
        with QSignalBlocker(self.search):
            self.search.clear()
        self.filter.setFilterFixedString("")
        self._filter_text = ""
        self._selecting = False
        self.stack.setCurrentWidget(self.workbench if sid else self.empty)
        self.export_button.setEnabled(bool(sid))
        self.open_button.setEnabled(False)
        if sid:
            sheet = self.workspace.sheet(sid)
            self.title.setText(sheet.title)
            self.subtitle.setText("选择联系人 → 打开企微 → 随聊填写")
            self._counts()
            if self.filter.rowCount():
                self.table.setCurrentIndex(self.filter.index(0, 0))

    def _selection_changed(self, current, previous):
        if self._selecting:
            return
        if not current.isValid():
            return
        source = self.filter.mapToSource(current)
        key = (self.model.sheet_id, self.model.sheet.rows[source.row()].id)
        if not self.delegate.flush() or not self.form.bind(key):
            self._selecting = True
            if previous.isValid():
                self.table.setCurrentIndex(previous)
            self._selecting = False
            return
        self.current_key = key
        self.open_button.setEnabled(not self.contact_busy)

    def _structure(self, sid):
        if sid == self.model.sheet_id:
            previous = self.current_key
            if previous:
                try:
                    self.model.sheet.row(previous[1])
                    self.form.bind(previous)
                    self.select_record(previous[1])
                except StopIteration:
                    self.current_key = None
                    self.form.bind(None)
                    self.open_button.setEnabled(False)
            self._counts()
        for i, sheet in enumerate(self.workspace.sheets):
            item = self.sheet_list.item(i)
            if item:
                item.setText(f"{sheet.title}\n{len(sheet.rows)} 条记录")

    def _counts(self):
        if self.model.sheet:
            self.summary.setText(f"{self.filter.rowCount()} / {len(self.model.sheet.rows)} 条记录 · 双击单元格编辑，修改自动保存 · 导出包含当前表全部行")

    def select_record(self, rid):
        if not self.model.sheet:
            return
        index = next((i for i, row in enumerate(self.model.sheet.rows) if row.id == rid), None)
        if index is not None:
            proxy = self.filter.mapFromSource(self.model.index(index, 0))
            if proxy.isValid():
                self.table.setCurrentIndex(proxy)
                self.table.scrollTo(proxy)

    def _filter_changed(self, text):
        if not self.flush_all():
            with QSignalBlocker(self.search):
                self.search.setText(self._filter_text)
            return
        self.filter.setFilterFixedString(text)
        self.filter.invalidate()
        self._filter_text = text
        self._counts()
        if self.filter.rowCount():
            self.table.setCurrentIndex(self.filter.index(0, 0))
        else:
            self.current_key = None
            self.form.bind(None)
            self.open_button.setEnabled(False)

    def reapply_filter(self):
        self._filter_changed(self.search.text())

    def new_sheet(self):
        if not self.flush_all():
            return
        title, ok = QInputDialog.getText(self, "新建表格", "表格名称", text="联系人填写表")
        if not ok or not title.strip():
            return
        columns = [Column("姓名"), Column("联系人备注"), Column("班期"),
                   Column("跟进状态", "choice", ["待联系", "已联系", "待跟进", "已完成"]),
                   Column("反馈记录", "multiline")]
        sheet = Sheet(title.strip(), columns, settings=infer_settings(columns))
        if self.workspace.add_sheets([sheet]):
            self.sheet_list.setCurrentRow(len(self.workspace.sheets) - 1)

    def sample(self):
        if not self.flush_all():
            return
        cols = [Column("姓名"), Column("联系人备注"), Column("班期"),
                Column("跟进状态", "choice", ["待联系", "已联系", "待跟进", "已完成"]),
                Column("反馈记录", "multiline"), Column("下次联系日期", "date")]
        rows = [["示例小林", "demo示例小林", "体验班", "待联系", "此表仅含虚构数据，可自由体验填写。", ""],
                ["示例小陈", "demo示例小陈", "体验班", "待跟进", "约定下周继续沟通。", ""],
                ["示例小周", "demo示例小周", "体验班", "已完成", "已完成本次登记。", ""]]
        sheet = Sheet("虚构示例 · 联系人登记", cols,
                      [Record({col.id: value for col, value in zip(cols, values)}) for values in rows],
                      infer_settings(cols))
        sheet.settings["prefix"] = "demo"
        if self.workspace.add_sheets([sheet]):
            self.sheet_list.setCurrentRow(len(self.workspace.sheets) - 1)

    def add_row(self):
        if self.model.sheet and self.flush_all():
            with QSignalBlocker(self.search):
                self.search.clear()
            self.filter.setFilterFixedString("")
            rid = self.workspace.add_row(self.model.sheet_id)
            if rid:
                self.select_record(rid)
                next(iter(self.form.editors.values())).setFocus()

    def add_column(self):
        if not self.model.sheet or not self.flush_all():
            return
        dialog = FieldDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.workspace.add_column(self.model.sheet_id, dialog.column())

    def delete_rows(self):
        if not self.model.sheet or not self.flush_all():
            return
        ids = [self.model.sheet.rows[self.filter.mapToSource(index).row()].id
               for index in self.table.selectionModel().selectedRows()]
        if not ids:
            return
        answer = QMessageBox.question(self, "删除记录", f"删除所选 {len(ids)} 行？本操作不可撤销，导入的原文件保持不变。",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.workspace.delete_rows(self.model.sheet_id, ids)

    def configure(self):
        if not self.model.sheet or not self.flush_all():
            return
        dialog = ContactDialog(self.model.sheet, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.workspace.configure(self.model.sheet_id, dialog.settings())

    def show_floating(self):
        if not self.flush_all():
            return
        self.floating.show()
        self.floating.raise_()
        self.floating.activateWindow()

    def _file_task(self, operation, success):
        if self.file_job:
            self.show_notice("文件操作进行中，请稍候。")
            return
        self.import_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress.show()
        job = Job(operation, self)
        self.file_job = job
        job.succeeded.connect(success)
        job.failed.connect(lambda error: self.show_notice("文件操作失败，原文件已保留：" + error, True))
        job.finished.connect(self._file_finished)
        job.finished.connect(job.deleteLater)
        job.start()

    def _file_finished(self):
        self.file_job = None
        self.import_button.setEnabled(True)
        self.export_button.setEnabled(bool(self.model.sheet))
        self.progress.hide()

    def import_dialog(self):
        if self.file_job or not self.flush_all():
            return
        path, _ = QFileDialog.getOpenFileName(self, "导入表格 · 第一行为表头", "", "表格文件 (*.xlsx *.csv)")
        if path:
            self.show_notice("正在读取表格，原文件不会被修改…")
            self._file_task(lambda: import_file(Path(path)), self._imported)

    def _imported(self, sheets):
        if self.workspace.add_sheets(sheets):
            self.sheet_list.setCurrentRow(len(self.workspace.sheets) - len(sheets))
            self.show_notice(f"已导入 {len(sheets)} 张表；请在「联系人设置」核对姓名列和前缀。")

    def export_dialog(self):
        if self.file_job or not self.model.sheet or not self.flush_all():
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "导出当前表 · 全部行", str(Path.home() / "Documents" / (self.model.sheet.title + "-已填写.xlsx")),
            "Excel 表格 (*.xlsx);;CSV UTF-8 (*.csv)")
        if path:
            if not Path(path).suffix:
                path += ".csv" if "CSV" in selected else ".xlsx"
            snapshot = copy.deepcopy(self.model.sheet)
            self.show_notice("正在导出当前表的全部记录…")
            self._file_task(lambda: export_file(Path(path), [snapshot]),
                            lambda _: self.show_notice("导出成功：" + path))

    def open_contact(self):
        if self.contact_busy or not self.current_key or not self.flush_all():
            return
        sheet = self.workspace.sheet(self.current_key[0])
        row = sheet.row(self.current_key[1])
        query = sheet.contact(row)
        if not query:
            self.show_notice("姓名/备注为空，请先填写，或在联系人设置中指定姓名列。", True)
            return
        # Search is ambiguous if another imported record would use the same query.
        conflicts = [(s.id, r.id) for s in self.workspace.sheets for r in s.rows
                     if s.contact(r) == query]
        if len(conflicts) != 1:
            self.show_notice("多条记录使用相同联系人名称，请补充唯一备注或前缀后再打开。", True)
            return
        if any(ch in query for ch in "\r\n\0"):
            self.show_notice("联系人名称不能包含换行或空字符。", True)
            return
        try:
            desktop = NativeDesktop()
            # Validate the process before touching the clipboard.
            desktop.main_window()
        except Exception as exc:
            self.show_notice(str(exc), True)
            return
        clipboard = QApplication.clipboard()
        self._clipboard_backup = QMimeData()
        original = clipboard.mimeData()
        if original:
            for fmt in original.formats():
                self._clipboard_backup.setData(fmt, original.data(fmt))
        clipboard.setText(query)
        self._clipboard_query = query
        options = dict(sheet.settings)
        job = Job(lambda: ContactSearch(desktop, cancelled=job.isInterruptionRequested).open(
            query, verify=options.get("verify_contact", True), keep_float=options.get("keep_float", True)), self)
        self.contact_job = job
        self.open_button.setEnabled(False)
        self.show_notice("正在打开：" + query + "；请暂时不要操作鼠标键盘。")
        job.succeeded.connect(lambda message: self.show_notice(message))
        job.failed.connect(lambda error: self.show_notice("打开联系人失败：" + error, True))
        job.finished.connect(self._contact_finished)
        job.finished.connect(job.deleteLater)
        job.start()

    def _contact_finished(self):
        clipboard = QApplication.clipboard()
        # Do not overwrite clipboard changes made by the user or another app mid-search.
        if clipboard.text() == self._clipboard_query and self._clipboard_backup:
            clipboard.setMimeData(self._clipboard_backup)
        self._clipboard_backup = None
        self.contact_job = None
        self.open_button.setEnabled(bool(self.current_key))

    def closeEvent(self, event):
        if self.contact_job or self.file_job:
            self.show_notice("请等待当前文件/联系人操作结束后再关闭。", True)
            event.ignore()
            return
        if not self.flush_all():
            event.ignore()
            return
        self.floating.close()
        event.accept()
