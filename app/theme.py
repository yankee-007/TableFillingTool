"""Semantic desktop colors and consistent focus/control geometry."""
from string import Template

COLORS = {
    "canvas": "#F4F6F8", "surface": "#FFFFFF", "ink": "#202B33",
    "muted": "#586975", "line": "#DCE3E8", "input_border": "#83949E",
    "accent": "#176B5D", "accent_hover": "#125749", "accent_soft": "#E7F3EF",
    "accent_text": "#165B4D", "navy": "#273F4A", "hover": "#F0F4F5",
    "danger": "#A63232", "danger_soft": "#FFF1F0", "warning": "#8C5914",
    "warning_soft": "#FFF6E6", "disabled": "#85939D",
}

STYLE = Template("""
QWidget { font-size: 13px; color: $ink; }
QMainWindow, QDialog, QWidget#floating { background: $canvas; }
QWidget#sidebar { background: $surface; border-right: 1px solid $line; }
QWidget#tableSurface, QWidget#detailPanel { background: $surface; border: 1px solid $line; border-radius: 9px; }
QWidget#editorCard, QWidget#formFields, QWidget#tableEmpty { background: $surface; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#brand { font-size: 18px; font-weight: 600; }
QLabel#muted, QLabel#caption { color: $muted; }
QLabel#caption, QLabel#fieldLabel { font-size: 12px; }
QLabel#section { font-size: 13px; font-weight: 600; }
QLabel#recordName { font-size: 19px; font-weight: 600; }
QLabel#emptyTitle { font-size: 23px; font-weight: 600; }
QLabel#countBadge { font-size: 12px; color: $muted; background: $canvas; border-radius: 4px; padding: 3px 7px; }
QLabel#banner { color: $muted; background: $surface; border: 1px solid $line; border-radius: 6px; padding: 10px; font-size: 12px; }
QLabel#banner[tone="success"] { color: $accent_text; background: $accent_soft; border-color: $accent_soft; }
QLabel#banner[tone="warning"] { color: $warning; background: $warning_soft; border-color: $warning_soft; }
QLabel#banner[tone="error"] { color: $danger; background: $danger_soft; border-color: $danger_soft; }
QLabel#saveState { color: $muted; font-size: 12px; }
QLabel#saveState[tone="success"] { color: $accent_text; }
QLabel#saveState[tone="error"] { color: $danger; }
QLabel#errorText { color: $danger; font-size: 12px; }
QLabel#appStatus[tone="error"] { color: $danger; }
QPushButton { background: $surface; border: 2px solid transparent; border-radius: 6px; padding: 7px 11px; min-height: 19px; }
QPushButton:hover { background: $hover; }
QPushButton:pressed { background: $line; }
QPushButton:focus { border-color: $accent; }
QPushButton#secondary { border: 1px solid $input_border; padding: 8px 12px; }
QPushButton#secondary:focus { border: 2px solid $accent; padding: 7px 11px; }
QPushButton#primary { color: white; background: $accent; font-weight: 600; }
QPushButton#primary:hover { background: $accent_hover; }
QPushButton#primary:focus { border-color: $ink; }
QPushButton#contactAction { color: white; background: $navy; font-weight: 600; }
QPushButton#contactAction:hover { background: $ink; }
QPushButton#contactAction:focus { border-color: $accent; }
QPushButton#link { color: $accent; background: transparent; padding: 5px 8px; }
QPushButton#link:hover { background: $accent_soft; }
QPushButton[iconOnly="true"] { padding: 4px; min-width: 20px; min-height: 22px; }
QPushButton:disabled { color: $disabled; background: $canvas; border-color: transparent; }
QPushButton#primary:disabled, QPushButton#contactAction:disabled { color: $disabled; background: $canvas; border-color: $line; }
QLineEdit, QComboBox, QPlainTextEdit { background: $surface; border: 1px solid $input_border; border-radius: 6px; padding: 8px 10px; selection-background-color: $accent; selection-color: white; placeholder-text-color: $muted; }
QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover { border-color: $input_border; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border: 2px solid $accent; padding: 7px 9px; }
QLineEdit#search { background: $canvas; border: 2px solid transparent; padding: 7px 9px; }
QLineEdit#search:focus { background: $surface; border-color: $accent; padding: 7px 9px; }
QComboBox { min-height: 20px; padding-right: 22px; }
QComboBox:focus { padding: 7px 21px 7px 9px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border: none; }
QComboBox QAbstractItemView { background: $surface; color: $ink; border: 1px solid $line; selection-background-color: $accent_soft; selection-color: $ink; padding: 4px; }
QListWidget { border: none; outline: none; background: transparent; }
QListWidget::item { padding: 12px 10px; margin: 2px 0px; border-radius: 6px; border: 2px solid transparent; }
QListWidget::item:selected { background: $accent_soft; color: $accent_text; }
QListWidget::item:hover { background: $hover; }
QListWidget::item:focus { border-color: $accent; }
QTableView { background: $surface; alternate-background-color: #FBFCFD; border: none; gridline-color: $line; selection-background-color: $accent_soft; selection-color: $ink; }
QTableView::item { padding: 5px 9px; border-bottom: 1px solid #EDF0F2; }
QTableView::item:focus { border: 1px solid $accent; }
QTableView QLineEdit, QTableView QLineEdit:focus { border: 2px solid $accent; border-radius: 0px; padding: 4px; }
QHeaderView::section { background: #F8FAFB; color: $muted; padding: 11px 9px; border: none; border-bottom: 1px solid $line; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: #F8FAFB; border: none; border-bottom: 1px solid $line; }
QScrollArea { border: none; background: $surface; }
QScrollArea > QWidget > QWidget { background: $surface; }
QScrollBar:vertical { width: 10px; margin: 2px 0; background: transparent; }
QScrollBar:horizontal { height: 10px; margin: 0 2px; background: transparent; }
QScrollBar::handle:vertical { min-height: 28px; background: #BDCAD1; border-radius: 4px; }
QScrollBar::handle:horizontal { min-width: 28px; background: #BDCAD1; border-radius: 4px; }
QScrollBar::handle:hover { background: $input_border; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; border: none; background: transparent; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QCheckBox { spacing: 8px; min-height: 24px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QCheckBox:focus { outline: 1px solid $accent; }
QSplitter::handle { background: transparent; width: 14px; }
QSplitter::handle:hover { background: $line; }
QStatusBar { background: $surface; border-top: 1px solid $line; padding: 2px 10px; }
QStatusBar::item { border: none; }
QProgressBar { min-height: 5px; max-height: 5px; border: none; background: $line; border-radius: 2px; }
QProgressBar::chunk { background: $accent; border-radius: 2px; }
""").substitute(COLORS)


def set_tone(widget, tone):
    if widget.property("tone") != tone:
        widget.setProperty("tone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
