"""Desktop tokens: compact data view, comfortable forms, visible keyboard focus."""
STYLE = """
QWidget { font-size: 13px; color: #1E293B; }
QMainWindow, QDialog, QWidget#floating { background: #F8FAFC; }
QWidget#sidebar { background: #EFF3F9; border-right: 1px solid #D7DFEB; }
QWidget#editorCard { background: white; border-radius: 8px; }
QLabel#title { font-size: 22px; font-weight: 700; }
QLabel#brand { font-size: 18px; font-weight: 700; color: #1D4ED8; }
QLabel#muted { color: #475569; }
QLabel#section { font-size: 14px; font-weight: 600; }
QLabel#banner { color: #1E40AF; background: #EAF1FF; padding: 10px; border-radius: 6px; }
QPushButton { background: white; border: 1px solid #94A3B8; border-radius: 6px; padding: 8px 12px; }
QPushButton:hover { border-color: #2563EB; background: #EFF6FF; }
QPushButton:pressed { background: #DBEAFE; }
QPushButton#primary { color: white; background: #2563EB; border-color: #2563EB; font-weight: 600; }
QPushButton#primary:hover { background: #1D4ED8; }
QPushButton:disabled { color: #94A3B8; background: #F1F5F9; border-color: #CBD5E1; }
QPushButton:focus, QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border: 2px solid #2563EB; }
QLineEdit, QComboBox, QPlainTextEdit { border: 1px solid #94A3B8; border-radius: 5px; padding: 7px; background: white; selection-background-color: #2563EB; }
QComboBox { min-height: 20px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #DBEAFE; selection-color: #1E293B; }
QListWidget { border: none; outline: none; background: transparent; }
QListWidget::item { padding: 12px 10px; margin: 2px 6px; border-radius: 6px; }
QListWidget::item:selected { background: #DBEAFE; color: #1E40AF; }
QListWidget::item:hover { background: #E2E8F0; }
QTableView { background: white; alternate-background-color: #F8FAFC; border: 1px solid #CBD5E1; gridline-color: #E2E8F0; selection-background-color: #DBEAFE; selection-color: #1E3A8A; }
QTableView::item { padding: 5px; }
QTableView::item:focus { border: 1px solid #2563EB; }
QHeaderView::section { background: #EFF3F9; color: #334155; padding: 10px 7px; border: none; border-bottom: 1px solid #CBD5E1; border-right: 1px solid #E2E8F0; font-weight: 600; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: white; }
QCheckBox { spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QSplitter::handle { background: #E2E8F0; width: 1px; }
QStatusBar { background: white; border-top: 1px solid #E2E8F0; }
"""
