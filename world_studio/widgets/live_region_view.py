from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent, QPolygonF
from PySide6.QtCore import Qt, Signal, QRect, QPointF
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.render_utils import render_screen

class LiveRegionViewWidget(QWidget):
    screen_double_clicked = Signal(str, str) # region_id, screen_id
    empty_cell_add_requested = Signal(str, int, int) # region_id, col, row
    screen_edit_requested = Signal(str, str) # region_id, screen_id
    screen_delete_requested = Signal(str, str) # region_id, screen_id
    screen_preview_requested = Signal(str, str) # region_id, screen_id
    screen_exits_requested = Signal(str, str) # region_id, screen_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.charset = None
        self.region_id = None
        
        self.zoom = 2
        self.screen_w = 40 * 4
        self.screen_h = 12 * 8
        self.spacing = 20
        
        self.hovered_cell = None
        self.setMouseTracking(True)
        
    def set_data(self, region_id: str, project: ProjectManager, charset: Charset):
        self.region_id = region_id
        self.project = project
        self.charset = charset
        self._compute_layout()
        self.update()

    def _compute_layout(self):
        if not self.region_id or not self.project:
            return
            
        region = self.project.regions.get(self.region_id)
        if not region:
            return
            
        cols = region.layout.columns
        rows = region.layout.rows
            
        w = cols * (self.screen_w * self.zoom + self.spacing) + self.spacing
        h = rows * (self.screen_h * self.zoom + self.spacing) + self.spacing
        self.setMinimumSize(w, h)

    def paintEvent(self, event):
        if not self.region_id or not self.project:
            return
            
        painter = QPainter(self)
        region = self.project.regions.get(self.region_id)
        if not region:
            return
            
        cols = region.layout.columns
        rows = region.layout.rows
        screens = self.project.screens.get(self.region_id, {})
        
        for row in range(rows):
            for col in range(cols):
                px = col * (self.screen_w * self.zoom + self.spacing) + self.spacing // 2
                py = row * (self.screen_h * self.zoom + self.spacing) + self.spacing // 2
                sw = self.screen_w * self.zoom
                sh = self.screen_h * self.zoom
                
                screen_id = None
                for sid, sdef in screens.items():
                    if sdef.grid_x == col and sdef.grid_y == row:
                        screen_id = sid
                        break
                        
                is_hovered = (self.hovered_cell == (col, row))
                
                if screen_id:
                    screen_def = screens[screen_id]
                    img = render_screen(screen_def, self.project, self.charset, mark_start_pos=True, region_id=self.region_id)
                    scaled = img.scaled(sw, sh, Qt.KeepAspectRatio, Qt.FastTransformation)
                    painter.drawImage(px, py, scaled)
                    
                    if is_hovered:
                        painter.setPen(QPen(Qt.yellow, 2))
                    else:
                        painter.setPen(QPen(QColor(100, 100, 100), 1))
                    painter.drawRect(px, py, sw, sh)
                    
                    painter.setPen(Qt.white)
                    painter.drawText(px, py - 4, screen_id)
                    
                    # Draw red exit arrows in bottom-right corner of thumbnail
                    self._draw_exit_arrows(painter, px, py, sw, sh, getattr(screen_def, 'exits', None))
                else:
                    if is_hovered:
                        painter.setPen(QPen(Qt.yellow, 2, Qt.DashLine))
                    else:
                        painter.setPen(QPen(QColor(50, 50, 50), 1, Qt.DashLine))
                    painter.drawRect(px, py, sw, sh)

    def _draw_exit_arrows(self, painter: QPainter, px: int, py: int, sw: int, sh: int, exits):
        if not exits:
            return
            
        has_north = bool(exits.north and exits.north != "null")
        has_south = bool(exits.south and exits.south != "null")
        has_east = bool(exits.east and exits.east != "null")
        has_west = bool(exits.west and exits.west != "null")
        
        if not (has_north or has_south or has_east or has_west):
            return
            
        box_w, box_h = 24, 24
        margin = 3
        box_x = px + sw - box_w - margin
        box_y = py + sh - box_h - margin
        cx = box_x + box_w // 2
        cy = box_y + box_h // 2
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Semi-transparent dark background for contrast
        painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
        painter.setBrush(QColor(15, 15, 15, 200))
        painter.drawRoundedRect(box_x, box_y, box_w, box_h, 4, 4)
        
        red_brush = QColor(255, 40, 40)
        red_pen = QPen(QColor(180, 0, 0), 1)
        
        painter.setBrush(red_brush)
        painter.setPen(red_pen)
        
        # North Arrow (pointing UP)
        if has_north:
            arrow = QPolygonF([
                QPointF(cx, cy - 9),
                QPointF(cx - 3.5, cy - 2),
                QPointF(cx + 3.5, cy - 2)
            ])
            painter.drawPolygon(arrow)
            
        # South Arrow (pointing DOWN)
        if has_south:
            arrow = QPolygonF([
                QPointF(cx, cy + 9),
                QPointF(cx - 3.5, cy + 2),
                QPointF(cx + 3.5, cy + 2)
            ])
            painter.drawPolygon(arrow)
            
        # West Arrow (pointing LEFT)
        if has_west:
            arrow = QPolygonF([
                QPointF(cx - 9, cy),
                QPointF(cx - 2, cy - 3.5),
                QPointF(cx - 2, cy + 3.5)
            ])
            painter.drawPolygon(arrow)
            
        # East Arrow (pointing RIGHT)
        if has_east:
            arrow = QPolygonF([
                QPointF(cx + 9, cy),
                QPointF(cx + 2, cy - 3.5),
                QPointF(cx + 2, cy + 3.5)
            ])
            painter.drawPolygon(arrow)
            
        painter.restore()

            
    def mouseMoveEvent(self, event):
        self.hovered_cell = None
        if not self.region_id or not self.project:
            return
            
        region = self.project.regions.get(self.region_id)
        if not region:
            return
            
        x = event.position().x()
        y = event.position().y()
        
        cols = region.layout.columns
        rows = region.layout.rows
        
        for row in range(rows):
            for col in range(cols):
                px = col * (self.screen_w * self.zoom + self.spacing) + self.spacing // 2
                py = row * (self.screen_h * self.zoom + self.spacing) + self.spacing // 2
                rect = QRect(px, py, self.screen_w * self.zoom, self.screen_h * self.zoom)
                
                if rect.contains(int(x), int(y)):
                    self.hovered_cell = (col, row)
                    break
                    
        self.update()

    def mouseDoubleClickEvent(self, event):
        if not self.hovered_cell or not self.region_id:
            return
        col, row = self.hovered_cell
        screens = self.project.screens.get(self.region_id, {})
        for sid, sdef in screens.items():
            if sdef.grid_x == col and sdef.grid_y == row:
                self.screen_double_clicked.emit(self.region_id, sid)
                break

    def contextMenuEvent(self, event):
        if not self.hovered_cell or not self.region_id:
            return
            
        col, row = self.hovered_cell
        screens = self.project.screens.get(self.region_id, {})
        screen_id = None
        for sid, sdef in screens.items():
            if sdef.grid_x == col and sdef.grid_y == row:
                screen_id = sid
                break
                
        menu = QMenu(self)
        if screen_id:
            preview_action = menu.addAction("Preview Screen")
            edit_action = menu.addAction("Rename Screen...")
            exits_action = menu.addAction("Set Exits...")
            del_action = menu.addAction("Remove Screen")
            action = menu.exec(event.globalPos())
            if action == preview_action:
                self.screen_preview_requested.emit(self.region_id, screen_id)
            elif action == edit_action:
                self.screen_edit_requested.emit(self.region_id, screen_id)
            elif action == exits_action:
                self.screen_exits_requested.emit(self.region_id, screen_id)
            elif action == del_action:
                self.screen_delete_requested.emit(self.region_id, screen_id)
        else:
            add_action = menu.addAction("Add Screen Here...")
            action = menu.exec(event.globalPos())
            if action == add_action:
                self.empty_cell_add_requested.emit(self.region_id, col, row)
