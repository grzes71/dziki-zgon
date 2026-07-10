from PySide6.QtGui import QImage, QPainter, QColor, QPixmap
from PySide6.QtCore import Qt
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.models import ScreenDef

def render_screen(screen_def: ScreenDef, project: ProjectManager, charset: Charset, mark_start_pos=False, region_id: str=None) -> QImage:
    w_tiles = 40
    h_tiles = 12
    
    px_w = w_tiles * 4
    px_h = h_tiles * 8
    
    img = QImage(px_w, px_h, QImage.Format_RGB32)
    colors_dict = project.region_colors.get(region_id, project.colors) if region_id else project.colors
    img.fill(QColor(*colors_dict.get("BACKGROUND", (0,0,0))))
    
    if not charset:
        return img
        
    colors = [
        QColor(*colors_dict.get("BACKGROUND", (0,0,0))),
        QColor(*colors_dict.get("PF0", (0,0,0))),
        QColor(*colors_dict.get("PF1", (0,0,0))),
        QColor(*colors_dict.get("PF2", (0,0,0))),
        QColor(*colors_dict.get("PF3_INV", (0,0,0))),
    ]
    
    # create object dictionary
    obj_dict = {o.id: o for o in project.objects}
    
    for obj_inst in screen_def.objects:
        obj_def = obj_dict.get(obj_inst.object)
        if not obj_def:
            continue
            
        base_x = obj_inst.x
        base_y = obj_inst.y
        rx = obj_inst.repeat_x
        ry = obj_inst.repeat_y
        
        w = obj_def.size.width
        h = obj_def.size.height
        
        for rep_y in range(ry):
            for rep_x in range(rx):
                curr_x = base_x + rep_x * w
                curr_y = base_y + rep_y * h
                
                # Check bounding box
                if curr_x >= w_tiles or curr_y >= h_tiles:
                    continue
                    
                # render this instance
                idx = 0
                for ty in range(h):
                    for tx in range(w):
                        screen_tx = curr_x + tx
                        screen_ty = curr_y + ty
                        
                        if screen_tx < w_tiles and screen_ty < h_tiles and idx < len(obj_def.tiles):
                            tile_idx = obj_def.tiles[idx]
                            pixels = charset.get_tile_pixels(tile_idx)
                            for py in range(8):
                                for px in range(4):
                                    c_idx = pixels[py][px]
                                    if c_idx > 0:
                                        img.setPixelColor(screen_tx * 4 + px, screen_ty * 8 + py, colors[c_idx])
                        idx += 1
                        
    if mark_start_pos and project.world_config and project.world_config.start_screen == screen_def.id:
        sx = project.world_config.start_position.x
        sy = project.world_config.start_position.y
        
        # draw a simple red square to denote player
        p = QPainter(img)
        p.setPen(Qt.red)
        p.setBrush(QColor(255, 0, 0, 128))
        p.drawRect(sx * 4, sy * 8, 4, 8)
        p.end()
        
    if screen_def.enemies:
        p = QPainter(img)
        p.setPen(Qt.magenta)
        p.setBrush(QColor(255, 0, 255, 128))
        for enemy in screen_def.enemies:
            p.drawRect(enemy.x * 4, enemy.y * 8, 4, 8)
        p.end()
        
    return img
