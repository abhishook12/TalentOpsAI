"""
ui/edge_handle.py — Persistent Edge Dock Handle (Level 2 Companion)

Implements the compact screen-edge dock handle / tab specified in UI/UX rework
and shown in media_1788544064790.png:
- Anchored flush against the screen edge (right edge by default).
- Draggable vertically along the screen edge with snap boundaries.
- Clean tab styling with beveled inner border, cyan/blue chevron (<), and active status dot.
- Single-click toggles / summons the Level 3 Main Window.
- Uses WS_EX_NOACTIVATE and Qt.WA_ShowWithoutActivating so clicking/hovering
  never steals foreground focus from the user's active browser.
- Always remains visible when Level 3 Main Window is minimized or closed.
"""

import ctypes
from ctypes import wintypes
import logging
from typing import Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath

logger = logging.getLogger("scout.edge_handle")

# Win32 Constants for Non-Activating Window
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


class EdgeHandleWidget(QWidget):
    """
    Level 2: Compact Persistent Edge Handle.
    Sits right against the screen border.
    Clicking it toggles the Scout Main Application Window.
    """
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._width = 30
        self._height = 84
        self.resize(self._width, self._height)

        self._dragging = False
        self._drag_start_y = 0
        self._mouse_moved = False
        self._is_hovered = False
        self._status_state = "ACTIVE"  # ACTIVE | IDLE | OFFLINE

        self._init_position()

    def _init_position(self):
        """Positions handle on the right edge of primary screen, centered vertically."""
        screen = self.screen() or self.window().screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self._width + 1
            y = geo.top() + int(geo.height() * 0.45)
            self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_no_activate()

    def _apply_no_activate(self):
        """Ensures the window never steals keyboard/foreground focus."""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        except Exception as e:
            logger.debug("Failed to set WS_EX_NOACTIVATE on edge handle: %s", e)

    def set_status_state(self, state: str):
        self._status_state = state.upper()
        self.update()

    @property
    def state(self) -> str:
        return getattr(self, "_status_state", "OFFLINE")

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._mouse_moved = False
            self._drag_start_y = event.globalPosition().toPoint().y() - self.y()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            new_y = event.globalPosition().toPoint().y() - self._drag_start_y
            # Clamp to screen geometry
            screen = self.screen()
            if screen:
                geo = screen.availableGeometry()
                new_y = max(geo.top(), min(new_y, geo.bottom() - self._height))
                x = geo.right() - self._width + 1
                self.move(x, new_y)
            self._mouse_moved = True
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            if not self._mouse_moved:
                # User clicked without dragging -> trigger toggle
                self.clicked.emit()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Path matching media_1788544064790.png:
        # Flat on right edge, beveled cut/round on top-left and bottom-left
        path = QPainterPath()
        r = 6.0  # bevel radius

        # Start top-right
        path.moveTo(w, 0)
        # Top edge moving left
        path.lineTo(r, 0)
        # Top-left beveled corner
        path.quadTo(0, 0, 0, r)
        # Left edge moving down
        path.lineTo(0, h - r)
        # Bottom-left beveled corner
        path.quadTo(0, h, r, h)
        # Bottom edge moving right
        path.lineTo(w, h)
        path.closeSubpath()

        # Background color
        if self._is_hovered:
            bg_color = QColor(255, 255, 255, 250)
            border_color = QColor(56, 189, 248, 220)  # cyan glow
        else:
            bg_color = QColor(241, 245, 249, 235)  # clean slate white (#f1f5f9)
            border_color = QColor(203, 213, 225, 200)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawPath(path)

        # Draw left chevron `<` (matching media_1788544064790.png exactly)
        chevron_color = QColor(14, 165, 233) if not self._is_hovered else QColor(2, 132, 199)
        chevron_pen = QPen(chevron_color, 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(chevron_pen)

        mid_y = h / 2.0
        # Draw chevron <
        painter.drawLine(QPointF(19.0, mid_y - 9.0), QPointF(9.0, mid_y))
        painter.drawLine(QPointF(9.0, mid_y), QPointF(19.0, mid_y + 9.0))

        # Mini status pulse dot at top — 5 distinct states
        state = self._status_state.upper() if self._status_state else ""
        if "ACTIVE" in state:
            dot_color = QColor(16, 185, 129)    # emerald green — actively capturing
        elif "IDLE" in state:
            dot_color = QColor(245, 158, 11)    # amber yellow — idle watch mode
        elif "PAUSED" in state:
            dot_color = QColor(59, 130, 246)    # blue — manually paused by user
        elif "OFFLINE" in state or "DISCONNECTED" in state:
            dot_color = QColor(100, 116, 139)   # slate gray — no connection
        elif "ERROR" in state or "CAPTURE_ERROR" in state:
            dot_color = QColor(239, 68, 68)     # red — error state
        else:
            dot_color = QColor(100, 116, 139)   # slate gray — unknown defaults to offline

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(13.0, 12.0), 3.0, 3.0)
