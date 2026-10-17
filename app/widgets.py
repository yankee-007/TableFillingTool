"""Small presentation components used by the native desktop UI."""
from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QAbstractItemView, QApplication, QComboBox, QLabel, QTableView, QVBoxLayout, QWidget

from .theme import COLORS


class FieldComboBox(QComboBox):
    """Keep a visible dropdown affordance when styling native Fusion controls."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(COLORS["muted"]), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x, y = self.width() - 15, self.height() / 2
        painter.drawPolyline(QPolygonF([QPointF(x - 4, y - 2), QPointF(x, y + 2), QPointF(x + 4, y - 2)]))


class ElidedLabel(QLabel):
    """Keep a full accessible caption while drawing an ellipsis at narrow widths."""
    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(min(360, hint.width()), hint.height())

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.contentsRect().width())
        painter.drawText(self.contentsRect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)


class WorkbenchTable(QTableView):
    def __init__(self):
        super().__init__()
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.empty_overlay = QWidget(self.viewport())
        self.empty_overlay.setObjectName("tableEmpty")
        self.empty_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.empty_layout = QVBoxLayout(self.empty_overlay)
        self.empty_layout.setContentsMargins(16, 20, 16, 20)
        self.empty_layout.setSpacing(10)
        self.empty_overlay.hide()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            bar = self.horizontalScrollBar()
            pixels, angles = event.pixelDelta(), event.angleDelta()
            delta = pixels.x() or pixels.y()
            if not delta:
                delta = ((angles.x() or angles.y()) / 120 * QApplication.styleHints().wheelScrollLines()
                         * self.fontMetrics().height())
            bar.setValue(round(bar.value() - delta))
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_empty()

    def position_empty(self):
        size = self.viewport().size()
        width = min(360, max(160, size.width() - 24))
        height = min(220, max(120, size.height() - 24))
        self.empty_overlay.setGeometry((size.width() - width) // 2, (size.height() - height) // 2, width, height)
