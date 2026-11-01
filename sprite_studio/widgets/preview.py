from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtCore import Qt, QTimer

from sprite_studio.models import Frame, Sprite
from sprite_studio.palette import get_atari_rgb, mix_atari_colors

class PreviewCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.frame: Optional[Frame] = None
        self.color_mode = 2
        self.color1 = 0
        self.color2 = 0
        self.color_mix = 0
        self.zoom = 4
        self.setMinimumSize(32, 100)

    def set_data(self, frame: Optional[Frame], color_mode: int, color1: int, color2: int, zoom: int):
        self.frame = frame
        self.color_mode = color_mode
        self.color1 = color1
        self.color2 = color2
        self.color_mix = mix_atari_colors(color1, color2)
        self.zoom = zoom
        h = len(frame.pixels) if frame else 0
        self.setMinimumSize(8 * zoom, h * zoom)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0)) # Atari background
        
        if not self.frame:
            return
            
        h = len(self.frame.pixels)
        painter.setPen(Qt.NoPen)
        rgb1 = get_atari_rgb(self.color1)
        rgb2 = get_atari_rgb(self.color2)
        rgb_mix = get_atari_rgb(self.color_mix)

        for y in range(h):
            row = self.frame.pixels[y]
            for x in range(8):
                c = row[x]
                if c == '1':
                    painter.fillRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom, rgb1)
                elif c == '2' and self.color_mode == 4:
                    painter.fillRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom, rgb2)
                elif c == '3' and self.color_mode == 4:
                    painter.fillRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom, rgb_mix)

class PreviewWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sprite: Optional[Sprite] = None
        self.current_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timeout)
        self.preview_fps = 50
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.canvas = PreviewCanvas(self)
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

    def set_sprite(self, sprite: Optional[Sprite]):
        self.sprite = sprite
        self.stop()
        
    def play(self):
        if not self.sprite or not self.sprite.frames:
            return
            
        if not self.timer.isActive():
            duration_ticks = self.sprite.animation.frame_duration
            ms = max(10, int((duration_ticks / self.preview_fps) * 1000))
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
        if not self.sprite or not self.sprite.frames:
            self.canvas.set_data(None, 2, 0, 0, self.slider_zoom.value())
            return
            
        idx = max(0, min(self.current_idx, len(self.sprite.frames) - 1))
        frame = self.sprite.frames[idx]
        self.canvas.set_data(
            frame=frame,
            color_mode=self.sprite.color_mode,
            color1=self.sprite.color,
            color2=self.sprite.color2,
            zoom=self.slider_zoom.value()
        )
