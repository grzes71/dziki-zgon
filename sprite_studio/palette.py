from __future__ import annotations

import math
from typing import Tuple, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QWidget
)
from PySide6.QtGui import QColor, QPainter, QPen, QMouseEvent
from PySide6.QtCore import Qt, Signal

# Generate standard 256 Atari 8-bit GTIA colors (16 hues x 16 luminances)
def _generate_atari_palette() -> List[Tuple[int, int, int]]:
    palette: List[Tuple[int, int, int]] = []
    # 16 hues, each with 16 luminance levels
    for hue in range(16):
        for lum in range(16):
            l_val = lum / 15.0
            if hue == 0:
                # Grayscale
                gray = int(l_val * 255)
                palette.append((gray, gray, gray))
            else:
                # Atari color wheel approximation
                # Hue 1 starts around gold/yellow-orange (~45 deg), moves clockwise
                angle = (hue - 1) * (2.0 * math.pi / 15.0) + 0.65
                sat = 0.55 if lum > 0 else 0.0
                brightness = 0.15 + 0.85 * l_val if lum > 0 else 0.0

                r_raw = brightness * (1.0 + sat * math.cos(angle))
                g_raw = brightness * (1.0 + sat * math.cos(angle - 2.0 * math.pi / 3.0))
                b_raw = brightness * (1.0 + sat * math.cos(angle + 2.0 * math.pi / 3.0))

                r = max(0, min(255, int(r_raw * 255)))
                g = max(0, min(255, int(g_raw * 255)))
                b = max(0, min(255, int(b_raw * 255)))
                palette.append((r, g, b))
    return palette

ATARI_PALETTE_RGB: List[Tuple[int, int, int]] = _generate_atari_palette()

def get_atari_rgb(color_idx: int) -> QColor:
    """Return QColor for Atari 8-bit color index (0..255)."""
    idx = max(0, min(255, int(color_idx)))
    r, g, b = ATARI_PALETTE_RGB[idx]
    return QColor(r, g, b)

def mix_atari_colors(color1: int, color2: int) -> int:
    """
    Simulate Atari GTIA hardware OR-color mixing (PRIOR bit 5).
    In GTIA hardware, overlapping players perform bitwise OR on the color registers:
    Hue nibble (7-4) and luminance nibble (3-0, effectively 3-1).
    """
    c1 = max(0, min(255, int(color1)))
    c2 = max(0, min(255, int(color2)))
    # Bitwise OR in GTIA register
    mixed = c1 | c2
    return mixed


class AtariColorGridWidget(QWidget):
    color_selected = Signal(int)

    def __init__(self, selected_color: int = 0, parent: QWidget | None = None):
        super().__init__(parent)
        self.selected_color = selected_color
        self.cell_size = 18
        self.setFixedSize(16 * self.cell_size, 16 * self.cell_size)
        self.setMouseTracking(True)

    def set_selected_color(self, color_idx: int) -> None:
        self.selected_color = max(0, min(255, int(color_idx)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        for hue in range(16):
            for lum in range(16):
                idx = (hue << 4) | lum
                color = get_atari_rgb(idx)
                x = lum * self.cell_size
                y = hue * self.cell_size

                painter.fillRect(x, y, self.cell_size, self.cell_size, color)

                # Draw selection border
                if idx == self.selected_color:
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    painter.drawRect(x + 1, y + 1, self.cell_size - 2, self.cell_size - 2)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            col = event.position().x() // self.cell_size
            row = event.position().y() // self.cell_size
            if 0 <= col < 16 and 0 <= row < 16:
                idx = (int(row) << 4) | int(col)
                self.selected_color = idx
                self.color_selected.emit(idx)
                self.update()


class AtariColorDialog(QDialog):
    """Dialog allowing user to choose from the 256 Atari GTIA colors."""

    def __init__(self, initial_color: int = 0, parent: QWidget | None = None, title: str = "Select Atari Color"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_color = initial_color
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.info_label = QLabel(f"Selected: ${self.selected_color:02X} ({self.selected_color})")
        layout.addWidget(self.info_label)

        self.grid = AtariColorGridWidget(self.selected_color, self)
        self.grid.color_selected.connect(self._on_color_clicked)
        layout.addWidget(self.grid)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_color_clicked(self, color_idx: int) -> None:
        self.selected_color = color_idx
        self.info_label.setText(f"Selected: ${color_idx:02X} ({color_idx})")

    @classmethod
    def get_color(cls, initial_color: int = 0, parent: QWidget | None = None, title: str = "Select Atari Color") -> Tuple[int, bool]:
        dialog = cls(initial_color=initial_color, parent=parent, title=title)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_color, True
        return initial_color, False

