from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent
from PySide6.QtCore import Qt, Signal, QRect

from ..charset import Charset
from ..settings import DEFAULT_COLORS, CANVAS_WIDTH_TILES, CANVAS_HEIGHT_TILES

class CanvasWidget(QWidget):
    canvas_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.charset = None
        self.zoom = 8
        self.cols = CANVAS_WIDTH_TILES
        self.rows = CANVAS_HEIGHT_TILES
        
        self.setMinimumSize(self.cols * 4 * self.zoom, self.rows * 8 * self.zoom)
        self.colors = [QColor(*rgb) for rgb in DEFAULT_COLORS.values()]
        
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.active_brush = 0
        self.is_painting = False
        self.is_erasing = False

    def set_colors(self, color_dict):
        self.colors = [QColor(*rgb) for rgb in color_dict.values()]
        self.update()

    def set_charset(self, charset: Charset):
        self.charset = charset
        self.update()
        
    def set_brush(self, index: int):
        self.active_brush = index
        
    def get_grid(self):
        return self.grid
        
    def set_grid(self, tiles_list, w, h):
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        idx = 0
        for y in range(min(h, self.rows)):
            for x in range(min(w, self.cols)):
                if idx < len(tiles_list):
                    self.grid[y][x] = tiles_list[idx]
                idx += 1
        self.update()

    def clear(self):
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.update()
        self.canvas_changed.emit()

    def _paint_at(self, pos):
        tile_w = 4 * self.zoom
        tile_h = 8 * self.zoom
        
        col = int(pos.x() // tile_w)
        row = int(pos.y() // tile_h)
        
        if 0 <= col < self.cols and 0 <= row < self.rows:
            new_val = 0 if self.is_erasing else self.active_brush
            if self.grid[row][col] != new_val:
                self.grid[row][col] = new_val
                self.update()
                self.canvas_changed.emit()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_painting = True
            self.is_erasing = False
            self._paint_at(event.position())
        elif event.button() == Qt.MouseButton.RightButton:
            self.is_painting = True
            self.is_erasing = True
            self._paint_at(event.position())

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_painting:
            self._paint_at(event.position())

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.is_painting = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.colors[0]) # Tło
        
        tile_w_px = 4
        tile_h_px = 8
        
        # Rysuj kafelki
        for row in range(self.rows):
            for col in range(self.cols):
                tile_idx = self.grid[row][col]
                x_offset = col * tile_w_px * self.zoom
                y_offset = row * tile_h_px * self.zoom
                
                if tile_idx != 0 and self.charset:
                    pixels = self.charset.get_tile_pixels(tile_idx)
                    for py in range(8):
                        for px in range(4):
                            c_idx = pixels[py][px]
                            if c_idx > 0:
                                painter.fillRect(
                                    x_offset + px * self.zoom, 
                                    y_offset + py * self.zoom, 
                                    self.zoom, self.zoom, 
                                    self.colors[c_idx]
                                )
                
                # Rysuj siatkę
                rect = QRect(x_offset, y_offset, tile_w_px * self.zoom, tile_h_px * self.zoom)
                pen = QPen(QColor(50, 50, 50), 1)
                painter.setPen(pen)
                painter.drawRect(rect)
