"""Small local vector icon family; no remote assets or emoji controls."""
from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .theme import COLORS

PATHS = {
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 10v10"/>',
    "import": '<path d="M12 3v11m-4-4 4 4 4-4M4 15v5h16v-5"/>',
    "export": '<path d="M12 15V4m-4 4 4-4 4 4M4 15v5h16v-5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "fields": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16M3 10h18"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "refresh": '<path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 2M18 18A8 8 0 0 1 5 16"/>',
    "chat": '<path d="M21 15a3 3 0 0 1-3 3H9l-6 4V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z"/><path d="M7 8h10M7 12h6"/>',
    "contact": '<circle cx="9" cy="7" r="3"/><path d="M3 20v-2a6 6 0 0 1 10-4M15 11h6v7h-6zM17 14h2"/>',
    "settings": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="white"/><circle cx="15" cy="17" r="3" fill="white"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
    "edit": '<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14z"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
}


@lru_cache(maxsize=80)
def icon(name, color=None):
    color = color or COLORS["muted"]
    if name == "brand":
        body = f'<rect x="1" y="1" width="22" height="22" rx="6" fill="{COLORS["accent"]}" stroke="none"/><path d="M6 7h12v8h-5l-4 3v-3H6zM6 10h12M10 7v8" stroke="white" stroke-width="1.4"/>'
    else:
        body = PATHS[name]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    result = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 96):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        result.addPixmap(pixmap)
    return result
