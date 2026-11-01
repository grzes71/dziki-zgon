from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSlider, QHBoxLayout, QLabel, QPushButton, QComboBox, QButtonGroup
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QKeyEvent
from PySide6.QtCore import Qt, Signal, QRect

from sprite_studio.models import Frame
from sprite_studio.palette import get_atari_rgb, mix_atari_colors


class PaletteBar(QWidget):
    """Color swatch bar showing active drawing pens (0..3) with Atari colors."""
    pen_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color_mode = 2
        self.color1 = 0
        self.color2 = 0
        self.color_mix = 0
        self.active_pen = "1"
        self._buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Pen:"))

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for val in ["0", "1", "2", "3"]:
            btn = QPushButton(val)
            btn.setCheckable(True)
            btn.setFixedWidth(54)
            btn.clicked.connect(lambda checked, v=val: self._on_btn_clicked(v))
            self.btn_group.addButton(btn)
            self._buttons.append(btn)
            layout.addWidget(btn)

        self._buttons[1].setChecked(True)
        layout.addStretch()

    def set_palette(self, color_mode: int, color1: int, color2: int):
        self.color_mode = color_mode
        self.color1 = color1
        self.color2 = color2
        self.color_mix = mix_atari_colors(color1, color2)

        # Swatch 0: Transparent
        self._buttons[0].setText("0: Tr")
        self._buttons[0].setStyleSheet("background-color: #222222; color: #aaaaaa; font-weight: bold;")

        # Swatch 1: Player 0
        rgb1 = get_atari_rgb(self.color1)
        text_color1 = "#000000" if rgb1.lightness() > 128 else "#ffffff"
        self._buttons[1].setText("1: P0")
        self._buttons[1].setStyleSheet(
            f"background-color: {rgb1.name()}; color: {text_color1}; font-weight: bold;"
        )

        # Swatches 2 and 3
        if self.color_mode == 4:
            rgb2 = get_atari_rgb(self.color2)
            text_color2 = "#000000" if rgb2.lightness() > 128 else "#ffffff"
            self._buttons[2].setText("2: P1")
            self._buttons[2].setStyleSheet(
                f"background-color: {rgb2.name()}; color: {text_color2}; font-weight: bold;"
            )
            self._buttons[2].setVisible(True)

            rgb3 = get_atari_rgb(self.color_mix)
            text_color3 = "#000000" if rgb3.lightness() > 128 else "#ffffff"
            self._buttons[3].setText("3: Mix")
            self._buttons[3].setStyleSheet(
                f"background-color: {rgb3.name()}; color: {text_color3}; font-weight: bold;"
            )
            self._buttons[3].setVisible(True)
        else:
            self._buttons[2].setVisible(False)
            self._buttons[3].setVisible(False)
            if self.active_pen in ("2", "3"):
                self.set_active_pen("1")

    def set_active_pen(self, pen_val: str):
        if pen_val not in ("0", "1", "2", "3"):
            return
        if self.color_mode == 2 and pen_val in ("2", "3"):
            pen_val = "1"
        self.active_pen = pen_val
        idx = int(pen_val)
        if 0 <= idx < len(self._buttons):
            self._buttons[idx].setChecked(True)
        self.pen_selected.emit(self.active_pen)

    def _on_btn_clicked(self, val: str):
        self.active_pen = val
        self.pen_selected.emit(val)


class PixelCanvas(QWidget):
    # Emits (x, y, value)
    pixel_changed = Signal(int, int, str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.frame: Optional[Frame] = None
        self.onion_frame: Optional[Frame] = None
        self.color_mode = 2
        self.color1 = 0
        self.color2 = 0
        self.color_mix = 0
        self.active_pen = "1"
        self.layer_view = 0  # 0 = All/Combined, 1 = Layer P0 only, 2 = Layer P1 only
        self.zoom = 10
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.last_pos = None
        self.drawing_val: Optional[str] = None

    def set_data(
        self,
        frame: Optional[Frame],
        onion_frame: Optional[Frame],
        color_mode: int,
        color1: int,
        color2: int,
        zoom: int,
        active_pen: str = "1",
        layer_view: int = 0
    ):
        self.frame = frame
        self.onion_frame = onion_frame
        self.color_mode = color_mode
        self.color1 = color1
        self.color2 = color2
        self.color_mix = mix_atari_colors(color1, color2)
        self.active_pen = active_pen
        self.layer_view = layer_view
        self.zoom = zoom

        h = len(frame.pixels) if frame else 0
        self.setMinimumSize(8 * zoom, h * zoom)
        self.update()

    def get_color_for_pixel(self, val: str) -> Optional[QColor]:
        if val == "1":
            return get_atari_rgb(self.color1)
        elif val == "2":
            return get_atari_rgb(self.color2)
        elif val == "3":
            return get_atari_rgb(self.color_mix)
        return None

    def paintEvent(self, event):
        if not self.frame:
            return
            
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(16, 16, 20)) # Dark background
        
        h = len(self.frame.pixels)
        
        # Subtle grid background
        grid_pen = QPen(QColor(35, 35, 42))
        painter.setPen(grid_pen)
        for y in range(h):
            for x in range(8):
                painter.drawRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)

        # Draw onion skin first (dimmed)
        if self.onion_frame and len(self.onion_frame.pixels) == h:
            for y in range(h):
                row = self.onion_frame.pixels[y]
                for x in range(8):
                    char = row[x]
                    col = self.get_color_for_pixel(char)
                    if col:
                        onion_col = QColor(col.red(), col.green(), col.blue(), 50)
                        painter.fillRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom, onion_col)

        # Draw active frame pixels
        for y in range(h):
            row = self.frame.pixels[y]
            for x in range(8):
                char = row[x]
                col = self.get_color_for_pixel(char)
                if col:
                    # Layer view filter
                    if self.layer_view == 1:
                        # Layer 0 (P0) only: chars '1' and '3'
                        if char not in ('1', '3'):
                            col = QColor(col.red() // 4, col.green() // 4, col.blue() // 4)
                    elif self.layer_view == 2:
                        # Layer 1 (P1) only: chars '2' and '3'
                        if char not in ('2', '3'):
                            col = QColor(col.red() // 4, col.green() // 4, col.blue() // 4)

                    painter.fillRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom, col)
                    painter.setPen(QPen(QColor(60, 60, 70), 1))
                    painter.drawRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)

    def mousePressEvent(self, event):
        self._handle_mouse(event.pos(), event.button())

    def mouseMoveEvent(self, event):
        if self.drawing_val is not None:
            self._handle_mouse(event.pos(), None)

    def mouseReleaseEvent(self, event):
        self.drawing_val = None
        self.last_pos = None

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_0:
            self.active_pen = "0"
            self.parent().palette_bar.set_active_pen("0")
        elif key == Qt.Key_1:
            self.active_pen = "1"
            self.parent().palette_bar.set_active_pen("1")
        elif key == Qt.Key_2 and self.color_mode == 4:
            self.active_pen = "2"
            self.parent().palette_bar.set_active_pen("2")
        elif key == Qt.Key_3 and self.color_mode == 4:
            self.active_pen = "3"
            self.parent().palette_bar.set_active_pen("3")
        else:
            super().keyPressEvent(event)

    def _handle_mouse(self, pos, button):
        if not self.frame:
            return
        
        x = pos.x() // self.zoom
        y = pos.y() // self.zoom
        
        h = len(self.frame.pixels)
        if 0 <= x < 8 and 0 <= y < h:
            if (x, y) != self.last_pos:
                if button == Qt.LeftButton:
                    self.drawing_val = self.active_pen
                elif button == Qt.RightButton:
                    self.drawing_val = "0"
                    
                if self.drawing_val is not None:
                    if self.frame.pixels[y][x] != self.drawing_val:
                        self.pixel_changed.emit(x, y, self.drawing_val)
                self.last_pos = (x, y)


class PixelEditorWidget(QWidget):
    pixel_changed = Signal(int, int, str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color_mode = 2
        self.color1 = 0
        self.color2 = 0
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top toolbar: Palette Bar + Layer View
        top_bar = QHBoxLayout()
        self.palette_bar = PaletteBar(self)
        self.palette_bar.pen_selected.connect(self._on_pen_selected)
        top_bar.addWidget(self.palette_bar)

        top_bar.addSpacing(15)
        top_bar.addWidget(QLabel("View:"))
        self.combo_layer_view = QComboBox()
        self.combo_layer_view.addItems(["Combined (All)", "Layer P0 (Player A)", "Layer P1 (Player B)"])
        self.combo_layer_view.currentIndexChanged.connect(self._on_layer_view_changed)
        top_bar.addWidget(self.combo_layer_view)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Canvas
        self.canvas = PixelCanvas(self)
        self.canvas.pixel_changed.connect(self.pixel_changed.emit)
        layout.addWidget(self.canvas)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(2, 40)
        self.slider_zoom.setValue(10)
        self.slider_zoom.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.slider_zoom)
        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)
        
        layout.addStretch()

    def set_data(
        self,
        frame: Optional[Frame],
        onion_frame: Optional[Frame],
        color_mode: int = 2,
        color1: int = 0,
        color2: int = 0
    ):
        self.color_mode = color_mode
        self.color1 = color1
        self.color2 = color2

        self.palette_bar.set_palette(color_mode, color1, color2)
        self.combo_layer_view.setEnabled(color_mode == 4)

        self.canvas.set_data(
            frame=frame,
            onion_frame=onion_frame,
            color_mode=color_mode,
            color1=color1,
            color2=color2,
            zoom=self.slider_zoom.value(),
            active_pen=self.palette_bar.active_pen,
            layer_view=self.combo_layer_view.currentIndex()
        )

    def _on_pen_selected(self, pen_val: str):
        self.canvas.active_pen = pen_val

    def _on_layer_view_changed(self, idx: int):
        self.canvas.layer_view = idx
        self.canvas.update()

    def _on_zoom_changed(self, val: int):
        if self.canvas.frame:
            self.canvas.set_data(
                frame=self.canvas.frame,
                onion_frame=self.canvas.onion_frame,
                color_mode=self.color_mode,
                color1=self.color1,
                color2=self.color2,
                zoom=val,
                active_pen=self.palette_bar.active_pen,
                layer_view=self.combo_layer_view.currentIndex()
            )
