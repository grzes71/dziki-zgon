from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QFormLayout, QComboBox, 
    QDialogButtonBox, QMessageBox
)
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent
from PySide6.QtCore import Qt, Signal
from world_studio.models import ScreenDef, ObjectInstance, EnemyInstance
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
        self.grid_height = 12
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
            # 1. Check if there is an existing enemy at this coordinate to edit
            existing_enemy = next((e for e in self.screen_def.enemies if e.x == x and e.y == y), None)
            if existing_enemy:
                from world_studio.widgets.enemy_properties_dialog import EnemyPropertiesDialog
                dialog = EnemyPropertiesDialog(existing_enemy, self.project.enemy_defs, self.project.enemy_colors, self)
                if dialog.exec() == QDialog.Accepted:
                    self.screen_changed.emit()
                    self.update()
                return

            # 1.5 Check if there is an existing interactive or secret object at this coordinate to edit
            obj_dict = {o.id: o for o in self.project.objects}
            for inst in self.screen_def.objects:
                odef = obj_dict.get(inst.object)
                if not odef:
                    continue
                w = odef.size.width * inst.repeat_x
                h = odef.size.height * inst.repeat_y
                if inst.x <= x < inst.x + w and inst.y <= y < inst.y + h:
                    is_inter = odef.flags and getattr(odef.flags, 'interactive', False)
                    is_secret = odef.flags and getattr(odef.flags, 'secret', False)
                    if is_inter:
                        from world_studio.widgets.interactive_object_dialog import InteractiveObjectPropertiesDialog
                        inv_items = self.project.inventory_items if self.project else []
                        regs = self.project.regions if self.project else {}
                        dialog = InteractiveObjectPropertiesDialog(inst, inventory_items=inv_items, regions=regs, current_region_id=self.region_id, parent=self)
                        if dialog.exec() == QDialog.Accepted:
                            self.screen_changed.emit()
                            self.update()
                        return
                    elif is_secret:
                        from world_studio.widgets.secret_item_dialog import SecretItemSelectionDialog
                        inv_items = self.project.inventory_items if self.project else []
                        current_item_id = inst.items_provided[0] if (inst.items_provided and len(inst.items_provided) > 0) else None
                        dialog = SecretItemSelectionDialog(inv_items, initial_item_id=current_item_id, parent=self)
                        if dialog.exec() == QDialog.Accepted and dialog.selected_item_id is not None:
                            inst.items_provided = [dialog.selected_item_id]
                            self.screen_changed.emit()
                            self.update()
                        return

            # 2. Add new entity/object if clicking empty space
            if self.active_tool == "PLAYER_START":
                if self.project.world_config:
                    self.project.world_config.start_screen = self.screen_def.id
                    self.project.world_config.start_position.x = int(x)
                    self.project.world_config.start_position.y = int(y)
                    self.screen_changed.emit()
            elif self.active_tool and (self.active_tool == "ENEMY" or self.active_tool.startswith("ENEMY:")):
                if self.active_tool.startswith("ENEMY:"):
                    enemy_id = self.active_tool.split(":")[1]
                else:
                    enemy_id = self.project.enemy_defs[0].id if (self.project and self.project.enemy_defs) else "strzyga"
                if len(self.screen_def.enemies) < 3:
                    # Create temporary enemy instance with default properties
                    new_enemy = EnemyInstance(
                        enemy=enemy_id,
                        x=int(x),
                        y=int(y),
                        strategy="vertical",
                        speed="medium",
                        color="white"
                    )
                    from world_studio.widgets.enemy_properties_dialog import EnemyPropertiesDialog
                    dialog = EnemyPropertiesDialog(new_enemy, self.project.enemy_defs, self.project.enemy_colors, self)
                    if dialog.exec() == QDialog.Accepted:
                        self.screen_def.enemies.append(new_enemy)
                        self.screen_changed.emit()
            elif self.active_tool and self.active_tool.startswith("PORTAL_ENTRY"):
                region = self.project.regions.get(self.region_id) if (self.project and self.region_id) else None
                existing_from_regions = set(region.portal_entries.keys()) if (region and getattr(region, 'portal_entries', None)) else set()
                avail_regions = [r for r in self.project.regions.keys() if r != self.region_id and r not in existing_from_regions]
                if not avail_regions:
                    QMessageBox.warning(
                        self,
                        "Brak dostępnych regionów",
                        "Brak dostępnych regionów do wyboru.\nWszystkie inne regiony posiadają już Portal Entry w tym regionie lub brak innych regionów w projekcie."
                    )
                    return

                dialog = QDialog(self)
                dialog.setWindowTitle("Set Portal Entry")
                d_layout = QVBoxLayout(dialog)

                form = QFormLayout()
                combo_region = QComboBox()
                combo_region.addItems(sorted(avail_regions))
                form.addRow("Region źródłowy (From Region):", combo_region)
                d_layout.addLayout(form)

                btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                btns.accepted.connect(dialog.accept)
                btns.rejected.connect(dialog.reject)
                d_layout.addWidget(btns)

                if dialog.exec() == QDialog.Accepted:
                    selected_region = combo_region.currentText().strip()
                    if selected_region:
                        region = self.project.regions.get(self.region_id)
                        if region:
                            from world_studio.models import PortalEntry
                            region.portal_entries[selected_region] = PortalEntry(screen=self.screen_def.id, x=int(x), y=int(y))
                            self.screen_changed.emit()
                            self.update()
                return
            elif self.active_tool:
                active_obj_def = next((o for o in self.project.objects if o.id == self.active_tool), None)
                if not active_obj_def:
                    return
                    
                is_interactive = active_obj_def.flags and getattr(active_obj_def.flags, 'interactive', False)
                is_secret = active_obj_def.flags and getattr(active_obj_def.flags, 'secret', False)
                if is_interactive:
                    interactive_ids = self.project.get_interactive_object_ids()
                    existing_screen_interactive = [
                        inst for inst in self.screen_def.objects if inst.object in interactive_ids
                    ]
                    if existing_screen_interactive:
                        QMessageBox.warning(
                            self,
                            "Cannot Place Interactive Object",
                            f"Screen '{self.screen_def.id}' already contains an interactive object ('{existing_screen_interactive[0].object}').\n\nThere can be at most one interactive object per screen."
                        )
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
                    if is_interactive:
                        from world_studio.widgets.interactive_object_dialog import InteractiveObjectPropertiesDialog
                        inv_items = self.project.inventory_items if self.project else []
                        regs = self.project.regions if self.project else {}
                        dialog = InteractiveObjectPropertiesDialog(new_obj, inventory_items=inv_items, regions=regs, current_region_id=self.region_id, parent=self)
                        if dialog.exec() == QDialog.Accepted:
                            self.screen_def.objects.append(new_obj)
                            self.screen_changed.emit()
                            self.update()
                    elif is_secret:
                        from world_studio.widgets.secret_item_dialog import SecretItemSelectionDialog
                        inv_items = self.project.inventory_items if self.project else []
                        dialog = SecretItemSelectionDialog(inv_items, parent=self)
                        if dialog.exec() == QDialog.Accepted and dialog.selected_item_id is not None:
                            new_obj.items_provided = [dialog.selected_item_id]
                            self.screen_def.objects.append(new_obj)
                            self.screen_changed.emit()
                            self.update()
                    else:
                        self.screen_def.objects.append(new_obj)
                        self.screen_changed.emit()
                        self.update()
                
        elif event.button() == Qt.RightButton:
            # Delete portal entry at this pos if matching
            if self.region_id and self.project and self.region_id in self.project.regions:
                region = self.project.regions[self.region_id]
                portal_to_remove = None
                for from_reg, entry in region.portal_entries.items():
                    es = getattr(entry, 'screen', None) if not isinstance(entry, dict) else entry.get('screen')
                    ex = getattr(entry, 'x', None) if not isinstance(entry, dict) else entry.get('x')
                    ey = getattr(entry, 'y', None) if not isinstance(entry, dict) else entry.get('y')
                    if es == self.screen_def.id and ex == x and ey == y:
                        portal_to_remove = from_reg
                        break
                if portal_to_remove:
                    del region.portal_entries[portal_to_remove]
                    self.screen_changed.emit()
                    self.update()
                    return

            # Delete enemy at this pos
            enemy_to_remove = None
            for i, e in enumerate(self.screen_def.enemies):
                if e.x == x and e.y == y:
                    enemy_to_remove = i
                    break
                    
            if enemy_to_remove is not None:
                self.screen_def.enemies.pop(enemy_to_remove)
                self.screen_changed.emit()
                self.update()
                return

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
