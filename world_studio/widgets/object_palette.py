from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QRadioButton
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtCore import Qt, Signal, QSize
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset

def render_object_pixmap(obj_def, charset: Charset, colors_dict: dict, zoom=2) -> QPixmap:
    w_tiles = obj_def.size.width
    h_tiles = obj_def.size.height
    
    px_w = w_tiles * 4
    px_h = h_tiles * 8
    
    img = QImage(px_w, px_h, QImage.Format_RGB32)
    img.fill(QColor(*colors_dict.get("BACKGROUND", (0,0,0))))
    
    colors = [
        QColor(*colors_dict.get("BACKGROUND", (0,0,0))),
        QColor(*colors_dict.get("PF0", (0,0,0))),
        QColor(*colors_dict.get("PF1", (0,0,0))),
        QColor(*colors_dict.get("PF2", (0,0,0))),
        QColor(*colors_dict.get("PF3_INV", (0,0,0))),
    ]
    
    if not charset:
        return QPixmap.fromImage(img)
        
    idx = 0
    for ty in range(h_tiles):
        for tx in range(w_tiles):
            if idx < len(obj_def.tiles):
                tile_idx = obj_def.tiles[idx]
                pixels = charset.get_tile_pixels(tile_idx)
                for py in range(8):
                    for px in range(4):
                        c_idx = pixels[py][px]
                        if c_idx > 0:
                            img.setPixelColor(tx * 4 + px, ty * 8 + py, colors[c_idx])
            idx += 1
            
    return QPixmap.fromImage(img).scaled(px_w * zoom, px_h * zoom, Qt.KeepAspectRatio, Qt.FastTransformation)

class ObjectPaletteWidget(QWidget):
    object_selected = Signal(str) # object_id or "PLAYER_START"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_player_start = QRadioButton("Set Player Start")
        self.btn_player_start.toggled.connect(self._on_player_start_toggled)
        layout.addWidget(self.btn_player_start)
        
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setSpacing(4)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

    def populate(self, project: ProjectManager, charset: Charset, region_id: str = None):
        self.list_widget.clear()
        if not project:
            return
            
        colors_dict = project.region_colors.get(region_id, project.colors) if region_id else project.colors
        if not colors_dict and project.region_colors:
            colors_dict = list(project.region_colors.values())[0]
            
        for obj in project.objects:
            pixmap = render_object_pixmap(obj, charset, colors_dict, zoom=3)
            item = QListWidgetItem(obj.id)
            item.setIcon(pixmap)
            item.setData(Qt.UserRole, obj.id)
            self.list_widget.addItem(item)
            
    def _on_player_start_toggled(self, checked):
        if checked:
            self.list_widget.clearSelection()
            self.object_selected.emit("PLAYER_START")
            
    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if items:
            self.btn_player_start.setChecked(False)
            obj_id = items[0].data(Qt.UserRole)
            self.object_selected.emit(obj_id)
