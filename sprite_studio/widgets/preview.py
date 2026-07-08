from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtCore import Qt, QTimer

class PreviewCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.sprite_color = QColor(255, 255, 255)
        self.zoom = 4
        self.setMinimumSize(32, 100)

    def set_data(self, frame, color_idx, zoom):
        self.frame = frame
        self.sprite_color = QColor(255, 255, 255) # Placeholder mapping
        self.zoom = zoom
        self.setMinimumSize(8 * zoom, (len(frame.pixels) if frame else 0) * zoom)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        if not self.frame:
            return
            
        h = len(self.frame.pixels)
        painter.setBrush(QBrush(self.sprite_color))
        painter.setPen(Qt.NoPen)
        for y in range(h):
            row = self.frame.pixels[y]
            for x in range(8):
                if row[x] == '1':
                    painter.drawRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.sprite = None
        self.current_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timeout)
        self.preview_fps = 50
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.canvas = PreviewCanvas()
        layout.addWidget(self.canvas)
        
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(1, 20)
        self.slider_zoom.setValue(4)
        self.slider_zoom.valueChanged.connect(self._update_canvas)
        zoom_layout.addWidget(self.slider_zoom)
        layout.addLayout(zoom_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.play)
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.pause)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop)
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

    def set_sprite(self, sprite):
        self.sprite = sprite
        self.stop()
        
    def play(self):
        if not self.sprite or not self.sprite.frames:
            return
            
        if not self.timer.isActive():
            duration_ticks = self.sprite.animation.frame_duration
            ms = int((duration_ticks / self.preview_fps) * 1000)
            self.timer.start(ms)

    def pause(self):
        self.timer.stop()

    def stop(self):
        self.timer.stop()
        self.current_idx = 0
        self._update_canvas()

    def _on_timeout(self):
        if not self.sprite or not self.sprite.frames:
            self.timer.stop()
            return
            
        self.current_idx += 1
        if self.current_idx >= len(self.sprite.frames):
            if self.sprite.animation.loop:
                self.current_idx = 0
            else:
                self.current_idx = len(self.sprite.frames) - 1
                self.timer.stop()
                
        self._update_canvas()

    def _update_canvas(self):
        if self.sprite and self.sprite.frames and 0 <= self.current_idx < len(self.sprite.frames):
            self.canvas.set_data(self.sprite.frames[self.current_idx], self.sprite.color, self.slider_zoom.value())
        else:
            self.canvas.set_data(None, 0, self.slider_zoom.value())
