from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent
from PySide6.QtCore import Qt, Signal, QRect
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.render_utils import render_screen

class LiveRegionViewWidget(QWidget):
    screen_double_clicked = Signal(str, str) # region_id, screen_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.charset = None
        self.region_id = None
        
        self.zoom = 2
        self.screen_w = 40 * 4
        self.screen_h = 10 * 8
        self.spacing = 20
        
        self.screen_positions = {}
        self.hovered_screen = None
        self.setMouseTracking(True)
        
    def set_data(self, region_id: str, project: ProjectManager, charset: Charset):
        self.region_id = region_id
        self.project = project
        self.charset = charset
        self._compute_layout()
        self.update()

    def _compute_layout(self):
        self.screen_positions.clear()
        if not self.region_id or not self.project:
            return
            
        region = self.project.regions.get(self.region_id)
        screens = self.project.screens.get(self.region_id, {})
        if not region or not screens:
            return
            
        start_id = region.start_screen
        if start_id not in screens:
            start_id = list(screens.keys())[0] if screens else None
            
        if not start_id:
            return
            
        queue = [(start_id, 0, 0)]
        self.screen_positions[start_id] = (0, 0)
        
        while queue:
            curr_id, cx, cy = queue.pop(0)
            s_def = screens.get(curr_id)
            if not s_def:
                continue
                
            exits = s_def.exits
            directions = [
                (exits.north, cx, cy - 1),
                (exits.south, cx, cy + 1),
                (exits.west, cx - 1, cy),
                (exits.east, cx + 1, cy)
            ]
            
            for next_id, nx, ny in directions:
                if next_id and next_id in screens and next_id not in self.screen_positions:
                    self.screen_positions[next_id] = (nx, ny)
                    queue.append((next_id, nx, ny))
                    
        if self.screen_positions:
            min_x = min(x for x,y in self.screen_positions.values())
            min_y = min(y for x,y in self.screen_positions.values())
            for sid, (x, y) in self.screen_positions.items():
                self.screen_positions[sid] = (x - min_x, y - min_y + 1) # +1 for label
                
            max_x = max(x for x,y in self.screen_positions.values())
            max_y = max(y for x,y in self.screen_positions.values())
            
            w = (max_x + 1) * (self.screen_w * self.zoom + self.spacing) + self.spacing
            h = (max_y + 2) * (self.screen_h * self.zoom + self.spacing) + self.spacing
            self.setMinimumSize(w, h)

    def paintEvent(self, event):
        if not self.region_id or not self.project:
            return
            
        painter = QPainter(self)
        screens = self.project.screens.get(self.region_id, {})
        
        for screen_id, (col, row) in self.screen_positions.items():
            screen_def = screens.get(screen_id)
            if not screen_def:
                continue
                
            px = col * (self.screen_w * self.zoom + self.spacing) + self.spacing // 2
            py = row * (self.screen_h * self.zoom + self.spacing) + self.spacing // 2
            
            img = render_screen(screen_def, self.project, self.charset, mark_start_pos=True)
            scaled = img.scaled(self.screen_w * self.zoom, self.screen_h * self.zoom, Qt.KeepAspectRatio, Qt.FastTransformation)
            
            painter.drawImage(px, py, scaled)
            
            if screen_id == self.hovered_screen:
                painter.setPen(QPen(Qt.yellow, 2))
                painter.drawRect(px, py, scaled.width(), scaled.height())
            else:
                painter.setPen(QPen(QColor(100, 100, 100), 1))
                painter.drawRect(px, py, scaled.width(), scaled.height())
            
            painter.setPen(Qt.white)
            painter.drawText(px, py - 4, screen_id)
            
    def mouseMoveEvent(self, event):
        self.hovered_screen = None
        if not self.screen_positions:
            return
            
        x = event.position().x()
        y = event.position().y()
        
        for screen_id, (col, row) in self.screen_positions.items():
            px = col * (self.screen_w * self.zoom + self.spacing) + self.spacing // 2
            py = row * (self.screen_h * self.zoom + self.spacing) + self.spacing // 2
            rect = QRect(px, py, self.screen_w * self.zoom, self.screen_h * self.zoom)
            
            if rect.contains(int(x), int(y)):
                self.hovered_screen = screen_id
                break
                
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.hovered_screen:
            self.screen_double_clicked.emit(self.region_id, self.hovered_screen)
