from typing import List, Optional
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtCore import Qt, Signal, QSize
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset

ALL_TAGS_OPTION = "(Wszystkie tagi)"

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
    object_selected = Signal(str) # object_id, "PLAYER_START", "ENEMY", or "PORTAL_ENTRY"

    ACTION_ADD_ENEMY = "Add Enemy"
    ACTION_ADD_OBJECT = "Add Object"
    ACTION_SET_PLAYER_START = "Set Player Start"
    ACTION_SET_PORTAL_ENTRY = "Set Portal Entry"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[ProjectManager] = None
        self.charset: Optional[Charset] = None
        self.region_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Action:"))
        
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            self.ACTION_ADD_ENEMY,
            self.ACTION_ADD_OBJECT,
            self.ACTION_SET_PLAYER_START,
            self.ACTION_SET_PORTAL_ENTRY
        ])
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("Tag:"))
        
        self.tag_combo = QComboBox()
        self.tag_combo.addItem(ALL_TAGS_OPTION)
        self.tag_combo.currentTextChanged.connect(self._on_tag_filter_changed)
        tag_layout.addWidget(self.tag_combo)
        layout.addLayout(tag_layout)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setSpacing(4)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        self.action_combo.currentTextChanged.connect(self._on_action_changed)

    def set_available_regions(self, regions: List[str], current_region_id: str = None):
        pass

    def populate(self, project: ProjectManager, charset: Charset, region_id: str = None):
        self.project = project
        self.charset = charset
        self.region_id = region_id

        self.update_tag_combo()
        self._refresh_object_list()

    def update_tag_combo(self):
        current_tag = self.tag_combo.currentText()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem(ALL_TAGS_OPTION)

        if self.project and getattr(self.project, 'available_tags', None):
            for tag in self.project.available_tags:
                self.tag_combo.addItem(tag)

        idx = self.tag_combo.findText(current_tag)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        else:
            self.tag_combo.setCurrentIndex(0)
        self.tag_combo.blockSignals(False)

    def _refresh_object_list(self):
        self.list_widget.blockSignals(True)
        
        selected_obj_id = None
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            selected_obj_id = selected_items[0].data(Qt.UserRole)
            
        self.list_widget.clear()

        if not self.project:
            self.list_widget.blockSignals(False)
            return

        colors_dict = self.project.get_region_colors(self.region_id) if self.project else {}
        selected_tag = self.tag_combo.currentText()

        matched_item = None
        for obj in self.project.objects:
            if selected_tag != ALL_TAGS_OPTION and selected_tag:
                if selected_tag not in getattr(obj, 'tags', []):
                    continue
            
            pixmap = render_object_pixmap(obj, self.charset, colors_dict, zoom=3)
            item = QListWidgetItem(obj.id)
            item.setIcon(pixmap)
            item.setData(Qt.UserRole, obj.id)
            self.list_widget.addItem(item)
            
            if selected_obj_id and obj.id == selected_obj_id:
                matched_item = item

        if matched_item:
            self.list_widget.setCurrentItem(matched_item)
            
        self.list_widget.blockSignals(False)
        self._update_action_state()

    def _on_tag_filter_changed(self, text):
        self._refresh_object_list()

    def _on_action_changed(self, text):
        self._update_action_state()

    def _update_action_state(self):
        action = self.action_combo.currentText()
        is_add_object = (action == self.ACTION_ADD_OBJECT)
        self.tag_combo.setEnabled(is_add_object)

        if action == self.ACTION_ADD_ENEMY:
            self.list_widget.blockSignals(True)
            self.list_widget.clearSelection()
            self.list_widget.blockSignals(False)
            self.object_selected.emit("ENEMY")
        elif action == self.ACTION_SET_PLAYER_START:
            self.list_widget.blockSignals(True)
            self.list_widget.clearSelection()
            self.list_widget.blockSignals(False)
            self.object_selected.emit("PLAYER_START")
        elif action == self.ACTION_SET_PORTAL_ENTRY:
            self.list_widget.blockSignals(True)
            self.list_widget.clearSelection()
            self.list_widget.blockSignals(False)
            self.object_selected.emit("PORTAL_ENTRY")
        elif is_add_object:
            items = self.list_widget.selectedItems()
            if items:
                obj_id = items[0].data(Qt.UserRole)
                self.object_selected.emit(obj_id)
            elif self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)

    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if items:
            if self.action_combo.currentText() != self.ACTION_ADD_OBJECT:
                self.action_combo.blockSignals(True)
                self.action_combo.setCurrentText(self.ACTION_ADD_OBJECT)
                self.tag_combo.setEnabled(True)
                self.action_combo.blockSignals(False)
            obj_id = items[0].data(Qt.UserRole)
            self.object_selected.emit(obj_id)
