from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent
from PySide6.QtCore import Qt, Signal, QRect

from ..charset import Charset
from ..settings import DEFAULT_COLORS

class PaletteWidget(QWidget):
    tile_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.charset = None
        self.selected_index = 0
        self.zoom = 3
        self.cols = 32
        self.rows = 8
        
        self.setMinimumSize(self.cols * 4 * self.zoom, self.rows * 8 * self.zoom)
        self.colors = [QColor(*rgb) for rgb in DEFAULT_COLORS.values()]

    def set_charset(self, charset: Charset):
        self.charset = charset
        self.update()
        
    def set_colors(self, color_dict):
        self.colors = [QColor(*rgb) for rgb in color_dict.values()]
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if not self.charset:
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            y = event.position().y()
            
            tile_w = 4 * self.zoom
            tile_h = 8 * self.zoom
            
            col = int(x // tile_w)
            row = int(y // tile_h)
            
            if 0 <= col < self.cols and 0 <= row < self.rows:
                self.selected_index = row * self.cols + col
                self.tile_selected.emit(self.selected_index)
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.colors[0]) # Tło
        
        if not self.charset:
            return
            
        tile_w_px = 4
        tile_h_px = 8
        
        for idx in range(256):
            row = idx // self.cols
            col = idx % self.cols
            
            x_offset = col * tile_w_px * self.zoom
            y_offset = row * tile_h_px * self.zoom
            
            pixels = self.charset.get_tile_pixels(idx)
            for py in range(8):
                for px in range(4):
                    c_idx = pixels[py][px]
                    if c_idx > 0: # 0 to tło
                        painter.fillRect(
                            x_offset + px * self.zoom, 
                            y_offset + py * self.zoom, 
                            self.zoom, self.zoom, 
                            self.colors[c_idx]
                        )
                        
        # Obrys zaznaczonego elementu
        sel_row = self.selected_index // self.cols
        sel_col = self.selected_index % self.cols
        rect = QRect(sel_col * tile_w_px * self.zoom, sel_row * tile_h_px * self.zoom, 
                     tile_w_px * self.zoom, tile_h_px * self.zoom)
        pen = QPen(Qt.GlobalColor.white, 2)
        painter.setPen(pen)
        painter.drawRect(rect)
