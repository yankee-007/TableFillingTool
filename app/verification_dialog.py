"""GUI-owned batch sequencing: clipboard and database stay on the GUI thread."""
from collections import Counter
from PySide6.QtCore import QMimeData, QTimer, Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .theme import set_tone
from .verification import F11Hotkey, VerificationJob, prepare_tasks, save_confirmed
from .wecom import NativeDesktop
from .widgets import FieldComboBox


class VerificationDialog(QDialog):
    def __init__(self, workspace, sheet, scope, parent=None):
        super().__init__(parent)
        self.workspace, self.sheet, self.scope = workspace, sheet, scope
        self.tasks, self.cursor, self.job = [], 0, None
        self.active = self.paused = self.pause_requested = self.stopping = False
        self.desktop = None
        self.backup = None
        self.clipboard_query = ""
        self.hotkey = F11Hotkey(self.toggle_pause)
        self.setWindowTitle("验证联系人 · " + sheet.title)
        self.resize(800, 650)
        self.setMinimumSize(680, 560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        heading = QLabel("批量验证联系人")
        heading.setObjectName("title")
        layout.addWidget(heading)
        self.scope_label = QLabel()
        self.scope_label.setObjectName("caption")
        self.scope_label.setWordWrap(True)
        layout.addWidget(self.scope_label)
        self.settings_panel = QWidget()
        fields = QFormLayout(self.settings_panel)
        fields.setContentsMargins(0, 0, 0, 0)
        self.search_field = FieldComboBox()
        self.search_field.addItem("请选择搜索字段", "")
        self.result_field = FieldComboBox()
        self.result_field.addItem("不写回，仅查看验证结果", "")
        for col in sheet.columns:
            self.search_field.addItem(col.label, col.id)
            if col.kind != "date" and (col.kind != "choice" or "是" in col.options):
                self.result_field.addItem(col.label, col.id)
        self.search_field.setCurrentIndex(max(0, self.search_field.findData(sheet.settings.get("name_column", ""))))
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText("默认空，例如 py175")
        self.prefix.setMaxLength(256)
        self.mode = FieldComboBox()
        self.mode.addItem("包含匹配（默认）", "contains")
        self.mode.addItem("完整匹配", "exact")
        for title, widget in (("搜索字段", self.search_field), ("联系人前缀", self.prefix),
                              ("匹配方式", self.mode), ("成功写入“是”的字段", self.result_field)):
            widget.setAccessibleName(title)
            text = QLabel(title)
            text.setBuddy(widget)
            fields.addRow(text, widget)
        layout.addWidget(self.settings_panel)
        hint = QLabel("搜索词 = 前缀 + 字段值。只在确认匹配时写入“是”；其余保留原值。\n验证期间请勿操作鼠标键盘；F11 在当前联系人结束后暂停或继续。")
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.notice = QLabel("选择字段后开始验证")
        self.notice.setObjectName("banner")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.results = QTableWidget(0, 4)
        self.results.setHorizontalHeaderLabels(["搜索词", "结果", "企微联系人", "说明"])
        self.results.setAccessibleName("本轮联系人验证结果")
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setWordWrap(False)
        self.results.setAlternatingRowColors(True)
        self.results.verticalHeader().hide()
        self.results.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.results.setColumnWidth(0, 145)
        self.results.setColumnWidth(1, 80)
        self.results.setColumnWidth(2, 160)
        layout.addWidget(self.results, 1)
        actions = QHBoxLayout()
        self.start_button = QPushButton("开始验证")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start)
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button = QPushButton("结束本轮")
        self.stop_button.clicked.connect(self.stop)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        for btn in (self.start_button, self.pause_button, self.stop_button):
            actions.addWidget(btn)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)
        self.update_controls()
        self.refresh_scope()

    def refresh_scope(self):
        rows = self.scope()
        self.scope_label.setText(f"当前表 · 按当前搜索/筛选匹配范围，共 {len(rows)} 条；不含已不符合筛选的保留行。")
        return rows

    def update_controls(self):
        self.settings_panel.setEnabled(not self.active)
        self.start_button.setEnabled(not self.active)
        self.pause_button.setEnabled(self.active and not self.stopping)
        self.pause_button.setText("继续验证" if self.paused else "等待暂停…" if self.pause_requested else "暂停")
        self.stop_button.setEnabled(self.active and not self.stopping)

    def tell(self, text, tone="idle"):
        self.notice.setText(text)
        set_tone(self.notice, tone)

    def start(self):
        if self.active:
            return
        try:
            search = self.search_field.currentData()
            if not search:
                raise ValueError("请指定搜索字段")
            tasks = prepare_tasks(self.sheet, self.refresh_scope(), search,
                                  self.result_field.currentData(), self.prefix.text())
            if not tasks:
                raise ValueError("当前筛选没有匹配记录，未开始验证")
            # Validate only; no real input or clipboard mutation before this succeeds.
            desktop = NativeDesktop()
            desktop.main_window()
            self.hotkey.start()
        except Exception as exc:
            self.hotkey.close()
            self.tell(str(exc), "error")
            return
        self.desktop, self.tasks, self.cursor = desktop, tasks, 0
        self.search_cid, self.result_cid = search, self.result_field.currentData()
        self.match_mode = self.mode.currentData()
        self.active = True
        self.paused = self.pause_requested = self.stopping = False
        self.results.setRowCount(len(tasks))
        self.progress.setRange(0, len(tasks))
        self.progress.setValue(0)
        for i, task in enumerate(tasks):
            for j, text in enumerate((task.query, "待验证", "", "")):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self.results.setItem(i, j, item)
        self.update_controls()
        QTimer.singleShot(0, self.advance)

    def advance(self):
        if not self.active or self.job:
            return
        if self.stopping or self.cursor >= len(self.tasks):
            self.finish()
            return
        if self.pause_requested:
            self.paused = True
            self.tell("已暂停，可以操作电脑；F11 或「继续验证」恢复。", "warning")
            self.update_controls()
            return
        task = self.tasks[self.cursor]
        if task.review:
            self.checked("待确认", "", task.review)
            QTimer.singleShot(0, self.advance)
            return
        # Recheck identity immediately before sending any keys.
        try:
            if self.sheet.row(task.rid).cells.get(self.search_cid, "") != task.value:
                self.checked("已跳过", "", "搜索字段已变化，未操作企微")
                QTimer.singleShot(0, self.advance)
                return
        except StopIteration:
            self.checked("已跳过", "", "记录已删除，未操作企微")
            QTimer.singleShot(0, self.advance)
            return
        clipboard = QApplication.clipboard()
        self.backup = QMimeData()
        original = clipboard.mimeData()
        if original:
            for fmt in original.formats():
                self.backup.setData(fmt, original.data(fmt))
        self.clipboard_query = task.query
        clipboard.setText(task.query)
        self.tell(f"{self.cursor + 1}/{len(self.tasks)} · 正在验证：{task.query}；F11 可暂停")
        job = VerificationJob(self.desktop, task.query, self.match_mode, self)
        self.job = job
        job.checked.connect(self.checked)
        job.finished.connect(self.job_finished)
        job.finished.connect(job.deleteLater)
        job.start()

    def checked(self, state, observed, detail):
        task = self.tasks[self.cursor]
        if state == "已添加":
            state, detail = save_confirmed(self.workspace, self.sheet.id, task, self.search_cid, self.result_cid)
        for j, text in enumerate((task.query, state, observed, detail)):
            item = self.results.item(self.cursor, j)
            item.setText(text)
            item.setToolTip(text)
        self.results.scrollToItem(self.results.item(self.cursor, 0))
        self.cursor += 1
        self.progress.setValue(self.cursor)
        # Ambiguous title / focus or write failure requires an explicit resume.
        if (state == "失败" or (state == "待确认" and not task.review)) and self.cursor < len(self.tasks):
            self.pause_requested = True

    def job_finished(self):
        clipboard = QApplication.clipboard()
        if self.backup is not None and clipboard.text() == self.clipboard_query:
            clipboard.setMimeData(self.backup)
        self.backup = None
        self.job = None
        self.advance()

    def toggle_pause(self):
        if not self.active or self.stopping:
            return
        if self.paused:
            self.paused = self.pause_requested = False
            self.tell("继续验证，请勿操作鼠标键盘")
            self.advance()
        else:
            self.pause_requested = True
            self.tell("等待当前联系人结束后暂停", "warning")
            if not self.job:
                self.advance()
        self.update_controls()

    def stop(self):
        if self.active:
            self.stopping = True
            self.tell("当前联系人结束后停止；已保存结果保留。", "warning")
            self.update_controls()
            if not self.job:
                self.finish()

    def finish(self):
        self.hotkey.close()
        states = Counter(self.results.item(i, 1).text() for i in range(self.cursor))
        self.active = self.paused = self.pause_requested = self.stopping = False
        self.tell(f"已处理 {self.cursor}/{len(self.tasks)} 条 · 已添加 {states['已添加']} · 未找到 {states['未找到']} · 待确认 {states['待确认']} · 失败 {states['失败']} · 跳过 {states['已跳过']}" +
                  (f"；剩余 {len(self.tasks) - self.cursor} 条未验证" if self.cursor < len(self.tasks) else ""))
        self.start_button.setText("重新验证")
        self.update_controls()

    def reject(self):
        if self.active:
            self.stop()
            return
        super().reject()

    def closeEvent(self, event):
        if self.active:
            self.stop()
            event.ignore()
        else:
            super().closeEvent(event)
