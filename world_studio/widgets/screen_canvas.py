from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent
from PySide6.QtCore import Qt, Signal
from world_studio.models import ScreenDef, ObjectInstance
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.render_utils import render_screen

class ScreenCanvasWidget(QWidget):
    screen_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.screen_def = None
        self.project = None
        self.charset = None
        self.region_id = None
        
        self.zoom = 4
        self.grid_width = 40
        self.grid_height = 10
        self.tile_w_px = 4
        self.tile_h_px = 8
        
        self.active_tool = None # object_id or "PLAYER_START"
        
        self.setMinimumSize(self.grid_width * self.tile_w_px * self.zoom, 
                            self.grid_height * self.tile_h_px * self.zoom)

    def set_data(self, screen_def: ScreenDef, project: ProjectManager, charset: Charset, region_id: str = None):
        self.screen_def = screen_def
        self.project = project
        self.charset = charset
        self.region_id = region_id
        self.update()

    def paintEvent(self, event):
        if not self.screen_def or not self.project:
            return
            
        painter = QPainter(self)
        img = render_screen(self.screen_def, self.project, self.charset, mark_start_pos=True, region_id=self.region_id)
        scaled_img = img.scaled(img.width() * self.zoom, img.height() * self.zoom, Qt.KeepAspectRatio, Qt.FastTransformation)
        painter.drawImage(0, 0, scaled_img)
        
        # Draw grid
        pen = QPen(QColor(255, 255, 255, 30))
        painter.setPen(pen)
        for x in range(self.grid_width + 1):
            px = x * self.tile_w_px * self.zoom
            painter.drawLine(px, 0, px, self.grid_height * self.tile_h_px * self.zoom)
        for y in range(self.grid_height + 1):
            py = y * self.tile_h_px * self.zoom
            painter.drawLine(0, py, self.grid_width * self.tile_w_px * self.zoom, py)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.screen_def or not self.project:
            return
            
        x = event.position().x() // (self.tile_w_px * self.zoom)
        y = event.position().y() // (self.tile_h_px * self.zoom)
        
        if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
            return
            
        if event.button() == Qt.LeftButton:
            if self.active_tool == "PLAYER_START":
                if self.project.world_config:
                    self.project.world_config.start_screen = self.screen_def.id
                    self.project.world_config.start_position.x = int(x)
                    self.project.world_config.start_position.y = int(y)
                    self.screen_changed.emit()
            elif self.active_tool:
                active_obj_def = next((o for o in self.project.objects if o.id == self.active_tool), None)
                if not active_obj_def:
                    return
                    
                new_w = active_obj_def.size.width
                new_h = active_obj_def.size.height
                
                overlap = False
                obj_dict = {o.id: o for o in self.project.objects}
                for inst in self.screen_def.objects:
                    odef = obj_dict.get(inst.object)
                    if not odef:
                        continue
                        
                    inst_w = odef.size.width * inst.repeat_x
                    inst_h = odef.size.height * inst.repeat_y
                    
                    if not (x >= inst.x + inst_w or inst.x >= x + new_w or y >= inst.y + inst_h or inst.y >= y + new_h):
                        overlap = True
                        break
                        
                if not overlap:
                    new_obj = ObjectInstance(object=self.active_tool, x=int(x), y=int(y), **{"repeat-x": 1, "repeat-y": 1})
                    self.screen_def.objects.append(new_obj)
                    self.screen_changed.emit()
                
        elif event.button() == Qt.RightButton:
            # Delete object at this pos
            # Simple heuristic: delete object if (x,y) is inside its bounds.
            obj_dict = {o.id: o for o in self.project.objects}
            to_remove = None
            # search backwards to remove top-most
            for i in range(len(self.screen_def.objects)-1, -1, -1):
                inst = self.screen_def.objects[i]
                odef = obj_dict.get(inst.object)
                if not odef:
                    continue
                w = odef.size.width
                h = odef.size.height
                rx = inst.repeat_x
                ry = inst.repeat_y
                
                if inst.x <= x < inst.x + w*rx and inst.y <= y < inst.y + h*ry:
                    # check if it really hits one of the repeated parts (grid matching)
                    dx = x - inst.x
                    dy = y - inst.y
                    if (dx % w) < w and (dy % h) < h: # always true
                        to_remove = i
                        break
                        
            if to_remove is not None:
                self.screen_def.objects.pop(to_remove)
                self.screen_changed.emit()
                
        self.update()
