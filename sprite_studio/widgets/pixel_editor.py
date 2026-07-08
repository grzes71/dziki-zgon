from PySide6.QtWidgets import QWidget, QVBoxLayout, QSlider, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRect

class PixelCanvas(QWidget):
    # Emits (x, y, value)
    pixel_changed = Signal(int, int, str)
    
    def __init__(self):
        super().__init__()
        self.frame = None
        self.onion_frame = None
        self.sprite_color = QColor(255, 255, 255)
        self.zoom = 10
        self.setMouseTracking(True)
        self.last_pos = None
        self.drawing_val = None

    def set_data(self, frame, onion_frame, color_idx, zoom):
        self.frame = frame
        self.onion_frame = onion_frame
        # map color_idx to some visible QColor.
        self.sprite_color = QColor(255, 255, 255) # placeholder
        self.zoom = zoom
        self.setMinimumSize(8 * zoom, (len(frame.pixels) if frame else 0) * zoom)
        self.update()

    def paintEvent(self, event):
        if not self.frame:
            return
            
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0)) # Black background
        
        h = len(self.frame.pixels)
        
        # Draw onion skin first
        if self.onion_frame and len(self.onion_frame.pixels) == h:
            onion_color = QColor(self.sprite_color.red(), self.sprite_color.green(), self.sprite_color.blue(), 64)
            painter.setBrush(QBrush(onion_color))
            painter.setPen(Qt.NoPen)
            for y in range(h):
                row = self.onion_frame.pixels[y]
                for x in range(8):
                    if row[x] == '1':
                        painter.drawRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)

        # Draw active frame
        painter.setBrush(QBrush(self.sprite_color))
        painter.setPen(QPen(QColor(50, 50, 50))) # subtle grid
        for y in range(h):
            row = self.frame.pixels[y]
            for x in range(8):
                if row[x] == '1':
                    painter.setBrush(QBrush(self.sprite_color))
                else:
                    painter.setBrush(Qt.NoBrush)
                painter.drawRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)

    def mousePressEvent(self, event):
        self._handle_mouse(event.pos(), event.button())

    def mouseMoveEvent(self, event):
        if self.drawing_val is not None:
            self._handle_mouse(event.pos(), None)

    def mouseReleaseEvent(self, event):
        self.drawing_val = None
        self.last_pos = None

    def _handle_mouse(self, pos, button):
        if not self.frame:
            return
        
        x = pos.x() // self.zoom
        y = pos.y() // self.zoom
        
        h = len(self.frame.pixels)
        if 0 <= x < 8 and 0 <= y < h:
            if (x, y) != self.last_pos:
                if button == Qt.LeftButton:
                    self.drawing_val = '1'
                elif button == Qt.RightButton:
                    self.drawing_val = '0'
                    
                if self.drawing_val is not None:
                    # check if it actually changed
                    if self.frame.pixels[y][x] != self.drawing_val:
                        self.pixel_changed.emit(x, y, self.drawing_val)
                self.last_pos = (x, y)


class PixelEditorWidget(QWidget):
    pixel_changed = Signal(int, int, str)
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.canvas = PixelCanvas()
        self.canvas.pixel_changed.connect(self.pixel_changed.emit)
        
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(2, 40)
        self.slider_zoom.setValue(10)
        self.slider_zoom.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.slider_zoom)
        
        layout.addWidget(self.canvas)
        layout.addLayout(zoom_layout)
        layout.addStretch()

    def set_data(self, frame, onion_frame, color_idx):
        self.canvas.set_data(frame, onion_frame, color_idx, self.slider_zoom.value())

    def _on_zoom_changed(self, val):
        if self.canvas.frame:
            self.canvas.set_data(self.canvas.frame, self.canvas.onion_frame, self.canvas.sprite_color, val)
