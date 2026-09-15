"""
scout_desktop/ui/components.py — Shared Obsidian Executive UI Components for Scout Desktop v2.8.0.

Implements all core building blocks:
- ScoutShell: Window frame wrapper
- TopBar: Eye logo, v2.8.0 chip, pulsing active pill, signed-in user, installation ID, sign-out link
- UpdateBanner: Dismissible v2.9.0 signed release banner
- LeftRail: 7 navigation destinations with real-time badges & durable queue widget
- BottomStatusBar: Synced timestamp, uploaded records, queued count, error status, versions
- PageHead: Standardized screen headers with subtitle and action button
- Card: Dark Obsidian container with subtle highlight borders
- StateChip: Canonical, Hypothesis, Review, Rejected status chips
- ConfidenceMeter: Per-field / composite confidence bars (green 90+, amber 70+, red <70%)
"""

import sys
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy, QGraphicsDropShadowEffect, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, Property
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen, QBrush,
    QLinearGradient, QCursor
)

from .scout_data import SYSTEM_STATE, CANDIDATES, REVIEW_QUEUE_ITEMS, ACTIVITY_FEED


# ─────────────────────────────────────────────────────────────────────────────
# Styling Constants (Obsidian Palette — Exact Reference Alignment)
# ─────────────────────────────────────────────────────────────────────────────

COLOR_BG_BASE = "#0B0F19"       # Deep obsidian background (styles.css: --background)
COLOR_RAIL = "#080C14"          # Sidebar & top/bottom rails (styles.css: --rail)
COLOR_SURFACE_CARD = "#111624"  # Container card background (styles.css: --card)
COLOR_SURFACE = "#0E131F"       # Inner surface & inputs (styles.css: --surface)
COLOR_SURFACE_HOVER = "#182032" # Secondary highlight (styles.css: --secondary)
COLOR_SURFACE_BORDER = "#1B2234"# Card border (styles.css: --border)
COLOR_SURFACE_BORDER_LIGHT = "#243048"

COLOR_TEXT_PRIMARY = "#F8FAFC"
COLOR_TEXT_SECONDARY = "#94A3B8"
COLOR_TEXT_MUTED = "#64748B"

# Semantic Accents
COLOR_CANONICAL = "#10B981"      # Emerald Accent Green (styles.css: --accent)
COLOR_CANONICAL_BG = "rgba(16, 185, 129, 0.10)"
COLOR_CANONICAL_BORDER = "rgba(16, 185, 129, 0.25)"

COLOR_HYPOTHESIS = "#38BDF8"     # Sky Blue Primary (styles.css: --primary)
COLOR_HYPOTHESIS_BG = "rgba(56, 189, 248, 0.10)"
COLOR_HYPOTHESIS_BORDER = "rgba(56, 189, 248, 0.25)"

COLOR_REVIEW = "#F59E0B"         # Amber Signal (styles.css: --signal)
COLOR_REVIEW_BG = "rgba(245, 158, 11, 0.12)"
COLOR_REVIEW_BORDER = "rgba(245, 158, 11, 0.25)"

COLOR_REJECTED = "#EF4444"       # Rose Destructive (styles.css: --destructive)
COLOR_REJECTED_BG = "rgba(239, 68, 68, 0.12)"
COLOR_REJECTED_BORDER = "rgba(239, 68, 68, 0.25)"

COLOR_CYAN_ACCENT = "#38BDF8"
COLOR_PRIMARY = "#38BDF8"


# ─────────────────────────────────────────────────────────────────────────────
# 1. StateChip (Canonical / Hypothesis / Review / Rejected)
# ─────────────────────────────────────────────────────────────────────────────

class StateChip(QFrame):
    """
    Color-coded pill badge:
    - CANONICAL: Emerald Green (#10B981)
    - HYPOTHESIS: Sky Blue (#38BDF8)
    - REVIEW: Amber (#F59E0B)
    - REJECTED: Rose Red (#EF4444)
    """
    def __init__(self, state_text: str = "CANONICAL", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state_text = state_text.strip().upper()
        self.setFixedHeight(22)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)
        
        self.lbl_text = QLabel(self.state_text.capitalize())
        self.lbl_text.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        layout.addWidget(self.lbl_text)
        
        self._apply_style()

    def set_state(self, state_text: str):
        self.state_text = state_text.strip().upper()
        self.lbl_text.setText(self.state_text.capitalize())
        self._apply_style()

    def _apply_style(self):
        st = self.state_text
        if st in ("CANONICAL", "HEALTHY", "SUCCESS", "APPROVED"):
            bg = COLOR_CANONICAL_BG
            fg = COLOR_CANONICAL
            border = COLOR_CANONICAL_BORDER
        elif st in ("HYPOTHESIS", "UPLOADING", "ACTIVE", "INFO"):
            bg = COLOR_HYPOTHESIS_BG
            fg = COLOR_HYPOTHESIS
            border = COLOR_HYPOTHESIS_BORDER
        elif st in ("REVIEW", "UPDATE", "RETRYING", "WARN", "WARNING"):
            bg = COLOR_REVIEW_BG
            fg = COLOR_REVIEW
            border = COLOR_REVIEW_BORDER
        elif st in ("REJECTED", "OFFLINE", "REQUIRED", "FAILED", "ERROR", "HELD"):
            bg = COLOR_REJECTED_BG
            fg = COLOR_REJECTED
            border = COLOR_REJECTED_BORDER
        else:
            bg = "#111827"
            fg = COLOR_TEXT_SECONDARY
            border = "#1F2937"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 11px;
            }}
            QLabel {{
                color: {fg};
                background: transparent;
                border: none;
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# 2. ConfidenceMeter (Confidence Bar: green 90+, amber 70+, red <70%)
# ─────────────────────────────────────────────────────────────────────────────

class ConfidenceMeter(QWidget):
    """
    Horizontal confidence bar with optional label and percentage.
    - Green for 90-100%
    - Amber for 70-89%
    - Red for <70%
    """
    def __init__(self, label: str = "", score_pct: int = 95, show_label: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.score_pct = max(0, min(100, int(score_pct)))
        self.label_text = label
        self.show_label = show_label
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 4)
        layout.setSpacing(3)
        
        if self.show_label:
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            
            self.lbl_title = QLabel(self.label_text)
            self.lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: transparent; border: none;")
            
            self.lbl_pct = QLabel(f"{self.score_pct}%")
            self.lbl_pct.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
            self.lbl_pct.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent; border: none;")
            
            header_layout.addWidget(self.lbl_title)
            header_layout.addStretch()
            header_layout.addWidget(self.lbl_pct)
            layout.addLayout(header_layout)
            
        self.bar_widget = _ConfidenceBarWidget(self.score_pct)
        layout.addWidget(self.bar_widget)

    def set_score(self, score_pct: int, label: Optional[str] = None):
        self.score_pct = max(0, min(100, int(score_pct)))
        if label is not None and self.show_label:
            self.label_text = label
            self.lbl_title.setText(label)
        if self.show_label:
            self.lbl_pct.setText(f"{self.score_pct}%")
        self.bar_widget.set_score(self.score_pct)


class _ConfidenceBarWidget(QWidget):
    def __init__(self, score_pct: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.score_pct = score_pct
        self.setFixedHeight(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_score(self, score_pct: int):
        self.score_pct = score_pct
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        r = h / 2.0
        
        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#162238"))
        painter.drawRoundedRect(0, 0, w, h, r, r)
        
        # Determine fill color
        if self.score_pct >= 90:
            fill_color = QColor(COLOR_CANONICAL)
        elif self.score_pct >= 70:
            fill_color = QColor(COLOR_REVIEW)
        else:
            fill_color = QColor(COLOR_REJECTED)
            
        fill_w = int((self.score_pct / 100.0) * w)
        if fill_w > 0:
            painter.setBrush(fill_color)
            painter.drawRoundedRect(0, 0, max(fill_w, int(h)), h, r, r)
        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Card Container
# ─────────────────────────────────────────────────────────────────────────────

class Card(QFrame):
    """
    Obsidian surface container with 1px border and optional hover effect.
    """
    def __init__(self, parent: Optional[QWidget] = None, clickable: bool = False):
        super().__init__(parent)
        self.clickable = clickable
        self.setObjectName("ScoutCard")
        hover_css = f"""
            QFrame#ScoutCard:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border-color: {COLOR_SURFACE_BORDER_LIGHT};
            }}
        """ if clickable else ""
        self.setStyleSheet(f"""
            QFrame#ScoutCard {{
                background-color: {COLOR_SURFACE_CARD};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 8px;
            }}
            QFrame#ScoutCard QLabel {{
                background: transparent;
                border: none;
            }}
            {hover_css}
        """)
        if clickable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


# ─────────────────────────────────────────────────────────────────────────────
# 4. PageHead (Header with Title, Subtitle, and Right Action)
# ─────────────────────────────────────────────────────────────────────────────

class PageHead(QWidget):
    """
    Standard page header block:
    - Title (white bold)
    - Subtitle (muted gray)
    - Right side optional action or badge container
    """
    def __init__(self, title: str, subtitle: str = "", action_widget: Optional[QWidget] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(12)
        
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        
        text_layout.addWidget(self.lbl_title)
        
        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
            self.lbl_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            self.lbl_subtitle.setWordWrap(True)
            text_layout.addWidget(self.lbl_subtitle)
            
        layout.addLayout(text_layout)
        layout.addStretch()
        
        if action_widget is not None:
            layout.addWidget(action_widget, alignment=Qt.AlignmentFlag.AlignVCenter)


# ─────────────────────────────────────────────────────────────────────────────
# 5. TopBar
# ─────────────────────────────────────────────────────────────────────────────

class TopBar(QFrame):
    """
    Top Bar:
    - Eye logo (32x32 container in secondary bg)
    - "TalentOps Scout" + version chip "v2.8.0"
    - Subtitle "Edge intelligence agent"
    - Center pill "Active · observing" with pulsing dot
    - Right side: signed-in user ("Prashant · TalentOps AI"), "Installation #483", and "Sign out" button
    """
    sign_out_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_RAIL};
                border-bottom: 1px solid {COLOR_SURFACE_BORDER};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        # Left Section: Eye Logo, Title, Version Chip, Subtitle
        left_layout = QHBoxLayout()
        left_layout.setSpacing(10)
        
        self.eye_logo = _EyeLogoWidget()
        left_layout.addWidget(self.eye_logo)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        
        self.lbl_title = QLabel("TalentOps Scout")
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
        title_row.addWidget(self.lbl_title)
        
        # Version Chip
        self.lbl_version_chip = QLabel("v2.8.0")
        self.lbl_version_chip.setFont(QFont("Consolas", 8, QFont.Weight.Medium))
        self.lbl_version_chip.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: {COLOR_TEXT_SECONDARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 4px;
            padding: 1px 5px;
        """)
        title_row.addWidget(self.lbl_version_chip)
        title_row.addStretch()
        title_box.addLayout(title_row)
        
        # Subtitle
        self.lbl_subtitle = QLabel("Edge intelligence agent")
        self.lbl_subtitle.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        self.lbl_subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
        title_box.addWidget(self.lbl_subtitle)
        
        left_layout.addLayout(title_box)
        layout.addLayout(left_layout)
        layout.addStretch()
        
        # Center Section: Pulsing Active Pill
        self.center_pill = _ActiveObservingPill()
        layout.addWidget(self.center_pill, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        # Right Section: Signed-in User, Installation #483, Sign Out Button
        right_layout = QHBoxLayout()
        right_layout.setSpacing(14)
        
        self.lbl_user = QLabel(SYSTEM_STATE["user"]["display"])
        self.lbl_user.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        self.lbl_user.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none; background: transparent;")
        right_layout.addWidget(self.lbl_user)
        
        self.lbl_inst = QLabel(SYSTEM_STATE["user"]["installation_id"])
        self.lbl_inst.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        self.lbl_inst.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
        right_layout.addWidget(self.lbl_inst)
        
        self.btn_signout = QPushButton("Sign out")
        self.btn_signout.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        self.btn_signout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_signout.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                color: {COLOR_TEXT_SECONDARY};
                padding: 3px 10px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.btn_signout.clicked.connect(self.sign_out_clicked.emit)
        right_layout.addWidget(self.btn_signout)
        
        layout.addLayout(right_layout)

    def set_status(self, text: str, is_active: bool = True):
        self.center_pill.set_status(text, is_active)


class _EyeLogoWidget(QWidget):
    """Vector rendered Eye Logo for TalentOps Scout inside a rounded box"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(30, 30)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Rounded background box (bg-secondary ring-1 ring-border)
        p.setPen(QPen(QColor(COLOR_SURFACE_BORDER), 1))
        p.setBrush(QColor(COLOR_SURFACE_HOVER))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)
        
        # Outer eye curve in primary cyan
        cx = w / 2.0
        cy = h / 2.0
        path = QPainterPath()
        path.moveTo(6, cy)
        path.quadTo(cx, cy - 6, w - 6, cy)
        path.quadTo(cx, cy + 6, 6, cy)
        
        pen = QPen(QColor(COLOR_CYAN_ACCENT), 1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        
        # Center pupil dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(COLOR_CYAN_ACCENT))
        p.drawEllipse(int(cx - 2.5), int(cy - 2.5), 5, 5)
        p.end()


class _ActiveObservingPill(QFrame):
    """Centre status pill 'Active · observing' with a pulsing emerald dot"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.is_active = True
        self.status_text = "Active · observing"
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 12, 0)
        layout.setSpacing(6)
        
        self.dot = _PulsingDotWidget()
        layout.addWidget(self.dot)
        
        self.lbl_status = QLabel(self.status_text)
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        layout.addWidget(self.lbl_status)
        
        self._apply_style()

    def set_status(self, text: str, is_active: bool = True):
        self.status_text = text
        self.is_active = is_active
        self.lbl_status.setText(text)
        self.dot.set_active(is_active)
        self._apply_style()

    def _apply_style(self):
        if self.is_active:
            bg = COLOR_SURFACE
            border = COLOR_SURFACE_BORDER
            fg = COLOR_CANONICAL
        else:
            bg = COLOR_SURFACE
            border = COLOR_SURFACE_BORDER
            fg = COLOR_TEXT_MUTED
            
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 13px;
            }}
            QLabel {{
                color: {fg};
                background: transparent;
                border: none;
            }}
        """)


class _PulsingDotWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self.is_active = True
        self._alpha = 255
        self._increasing = False
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(75)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def _animate(self):
        if not self.is_active:
            return
        if self._increasing:
            self._alpha += 20
            if self._alpha >= 255:
                self._alpha = 255
                self._increasing = False
        else:
            self._alpha -= 20
            if self._alpha <= 110:
                self._alpha = 110
                self._increasing = True
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.is_active:
            c = QColor(16, 185, 129, self._alpha)
        else:
            c = QColor(156, 163, 175, 200)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(0, 0, self.width(), self.height())
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# 6. UpdateBanner (Scout 2.9.0 available)
# ─────────────────────────────────────────────────────────────────────────────

class UpdateBanner(QFrame):
    """
    Dismissible update banner:
    'Scout 2.9.0 available — signed release, verified and ready. Installs on next restart.'
    with 'Restart now' (visual only) and 'X' dismiss button.
    """
    restart_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border-bottom: 1px solid {COLOR_SURFACE_BORDER};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)
        
        # Info icon
        self.lbl_icon = QLabel("ℹ")
        self.lbl_icon.setFont(QFont("Segoe UI", 9))
        self.lbl_icon.setStyleSheet(f"color: {COLOR_HYPOTHESIS}; border: none;")
        layout.addWidget(self.lbl_icon)
        
        # Message
        self.lbl_msg = QLabel("")
        self.lbl_msg.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        self.lbl_msg.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        layout.addWidget(self.lbl_msg)
        
        layout.addStretch()
        
        # Restart Now button
        self.btn_restart = QPushButton("Restart now")
        self.btn_restart.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.btn_restart.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_restart.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_HOVER};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 3px 10px;
            }}
            QPushButton:hover {{
                background-color: #243048;
            }}
        """)
        self.btn_restart.clicked.connect(self._on_restart_click)
        layout.addWidget(self.btn_restart)
        
        # Close 'X' button
        self.btn_close = QPushButton("✕")
        self.btn_close.setFont(QFont("Segoe UI", 8))
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_MUTED};
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.btn_close.clicked.connect(self.hide)
        layout.addWidget(self.btn_close)

        # Hidden by default until an update is actually detected or ready
        self.hide()

    def show_update_ready(self, version: str, message: Optional[str] = None):
        """Displays update banner when installer binary is verified and staged."""
        msg = message or f"Scout v{version} available — signed release, verified and ready. Installs on next restart."
        self.lbl_msg.setText(msg)
        self.btn_restart.setText("Restart now")
        self.btn_restart.setEnabled(True)
        self.show()

    def show_downloading(self, version: str):
        """Displays update banner while downloading in background."""
        self.lbl_msg.setText(f"Scout v{version} available — downloading verified package in background...")
        self.btn_restart.setText("Downloading...")
        self.btn_restart.setEnabled(False)
        self.show()

    def reset_state(self):
        """Resets the button state if restart was deferred or aborted."""
        self.btn_restart.setText("Restart now")
        self.btn_restart.setEnabled(True)

    def _on_restart_click(self):
        self.btn_restart.setText("Restarting...")
        self.btn_restart.setEnabled(False)
        self.restart_requested.emit()


# ─────────────────────────────────────────────────────────────────────────────
# 7. LeftRail (Desktop Navigation Sidebar)
# ─────────────────────────────────────────────────────────────────────────────

class LeftRail(QFrame):
    """
    Left rail:
    - Width: 224px (w-56)
    - 7 destinations:
      0: Scan
      1: Candidates
      2: Review Queue (badge 6)
      3: Cloud Sync
      4: Pipeline
      5: Activity (badge 4)
      6: Settings
    - Bottom widget: 'Local queue 14 · durable · retrying in 12s'
    """
    nav_changed = Signal(int)

    NAV_ITEMS = [
        ("Scan", "👁️", 0, None),
        ("Candidates", "👥", 1, None),
        ("Review Queue", "🛡️", 2, "review_queue"),
        ("Cloud Sync", "☁️", 3, None),
        ("Pipeline", "⚡", 4, None),
        ("Activity", "🔔", 5, "activity"),
        ("Settings", "⚙️", 6, None),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(224)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_RAIL};
                border-right: 1px solid {COLOR_SURFACE_BORDER};
            }}
        """)
        
        self.active_index = 0
        self.buttons: List[_NavButton] = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)
        
        # Navigation buttons
        for title, icon, idx, badge_key in self.NAV_ITEMS:
            btn = _NavButton(title, icon, idx, badge_key)
            btn.clicked.connect(lambda checked=False, i=idx: self.select_tab(i))
            self.buttons.append(btn)
            layout.addWidget(btn)
            
        layout.addStretch()
        
        # Bottom Local Queue durable card
        self.queue_widget = _LocalQueueWidget()
        layout.addWidget(self.queue_widget)
        
        self.select_tab(0)

    def select_tab(self, index: int):
        self.active_index = index
        for btn in self.buttons:
            btn.set_active(btn.index == index)
        self.nav_changed.emit(index)

    def update_badge(self, key: str, count: int):
        for btn in self.buttons:
            if btn.badge_key == key:
                btn.set_badge_count(count)
                break

    def update_queue_status(self, count: int, retry_sec: int):
        self.queue_widget.set_stats(count, retry_sec)


class _NavButton(QPushButton):
    def __init__(self, title: str, icon_str: str, index: int, badge_key: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.icon_str = icon_str
        self.index = index
        self.badge_key = badge_key
        self.is_active = False
        self.setFixedHeight(36)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.h_layout = QHBoxLayout(self)
        self.h_layout.setContentsMargins(12, 0, 12, 0)
        self.h_layout.setSpacing(10)
        
        self.lbl_icon = QLabel(self.icon_str)
        self.lbl_icon.setFont(QFont("Segoe UI", 10))
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.h_layout.addWidget(self.lbl_icon)
        
        self.lbl_title = QLabel(self.title)
        self.lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.lbl_title.setStyleSheet("background: transparent; border: none;")
        self.h_layout.addWidget(self.lbl_title)
        
        self.h_layout.addStretch()
        
        self.lbl_badge = QLabel("")
        self.lbl_badge.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setFixedHeight(18)
        self.lbl_badge.setMinimumWidth(18)
        self.lbl_badge.hide()
        self.h_layout.addWidget(self.lbl_badge)
        
        if self.badge_key and self.badge_key in SYSTEM_STATE["badges"]:
            self.set_badge_count(SYSTEM_STATE["badges"][self.badge_key])
            
        self._apply_style()

    def set_active(self, active: bool):
        self.is_active = active
        self._apply_style()

    def set_badge_count(self, count: int):
        if count > 0:
            self.lbl_badge.setText(str(count))
            self.lbl_badge.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.15);
                color: #F59E0B;
                border: none;
                border-radius: 9px;
                padding: 0 5px;
            """)
            self.lbl_badge.show()
        else:
            self.lbl_badge.hide()

    def _apply_style(self):
        if self.is_active:
            bg = COLOR_SURFACE_HOVER
            fg = COLOR_TEXT_PRIMARY
        else:
            bg = "transparent"
            fg = COLOR_TEXT_SECONDARY
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: none;
                border-radius: 6px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        self.lbl_icon.setStyleSheet(f"color: {fg}; background: transparent; border: none;")


class _LocalQueueWidget(QFrame):
    """Bottom Left Rail Widget: 'Local queue 14 · durable · retrying in 12s'"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        
        self.lbl_tag = QLabel("LOCAL QUEUE")
        self.lbl_tag.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.lbl_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent; letter-spacing: 1px;")
        layout.addWidget(self.lbl_tag)
        
        self.lbl_count = QLabel(str(SYSTEM_STATE["local_queue_summary"]["count"]))
        self.lbl_count.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.lbl_count.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
        layout.addWidget(self.lbl_count)
        
        self.lbl_sub = QLabel(f"durable · retrying in {SYSTEM_STATE['local_queue_summary']['retry_in_sec']}s")
        self.lbl_sub.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        self.lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
        layout.addWidget(self.lbl_sub)

    def set_stats(self, count: int, retry_sec: int):
        self.lbl_count.setText(str(count))
        self.lbl_sub.setText(f"durable · retrying in {retry_sec}s")


# ─────────────────────────────────────────────────────────────────────────────
# 8. BottomStatusBar
# ─────────────────────────────────────────────────────────────────────────────

class BottomStatusBar(QFrame):
    """
    Bottom persistent status bar:
    'Synced 00:41:49', 49 records uploaded, 14 queued, No errors, Extractor 4.5.0, Scout 2.8.0, Windows 11
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_RAIL};
                border-top: 1px solid {COLOR_SURFACE_BORDER};
            }}
            QLabel {{
                color: {COLOR_TEXT_MUTED};
                font-family: 'Segoe UI';
                font-size: 8pt;
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        
        # Left status group
        self.lbl_synced = QLabel(f"● Synced {SYSTEM_STATE['status_bar']['synced_time']}")
        self.lbl_synced.setStyleSheet(f"color: {COLOR_CANONICAL}; font-size: 8pt;")
        self.lbl_uploaded = QLabel(f"{SYSTEM_STATE['status_bar']['records_uploaded']} records uploaded")
        self.lbl_queued = QLabel(f"{SYSTEM_STATE['status_bar']['queued']} queued")
        self.lbl_errors = QLabel(SYSTEM_STATE['status_bar']['errors'])
        
        layout.addWidget(self.lbl_synced)
        layout.addWidget(self.lbl_uploaded)
        layout.addWidget(self.lbl_queued)
        layout.addWidget(self.lbl_errors)
        
        layout.addStretch()
        
        # Right metadata group
        self.lbl_extractor = QLabel(SYSTEM_STATE['status_bar']['extractor_version'])
        self.lbl_scout = QLabel(SYSTEM_STATE['status_bar']['scout_version'])
        self.lbl_os = QLabel(SYSTEM_STATE['status_bar']['os_name'])
        
        layout.addWidget(self.lbl_extractor)
        layout.addWidget(self.lbl_scout)
        layout.addWidget(self.lbl_os)

    def update_metrics(self, synced_time: str, uploaded: int, queued: int, errors: str = "No errors"):
        self.lbl_synced.setText(f"● Synced {synced_time}")
        self.lbl_uploaded.setText(f"{uploaded} records uploaded")
        self.lbl_queued.setText(f"{queued} queued")
        self.lbl_errors.setText(errors)


# ─────────────────────────────────────────────────────────────────────────────
# 9. ToggleSwitch
# ─────────────────────────────────────────────────────────────────────────────

class ToggleSwitch(QWidget):
    """
    Modern Obsidian pill toggle switch:
    - Checked: Emerald Green (#10B981) background, knob on right
    - Unchecked: Slate dark (#1E293B) background, knob on left
    """
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(38, 20)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = h / 2.0

        if self._checked:
            bg_color = QColor("#10B981")
            border_color = QColor("#059669")
            knob_x = w - h + 2
        else:
            bg_color = QColor("#1E293B")
            border_color = QColor("#334155")
            knob_x = 2

        # Draw track
        p.setPen(QPen(border_color, 1))
        p.setBrush(bg_color)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Draw white knob
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        knob_size = h - 4
        p.drawEllipse(int(knob_x), 2, int(knob_size), int(knob_size))
        p.end()

