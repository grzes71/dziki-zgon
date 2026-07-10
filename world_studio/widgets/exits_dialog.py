from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QDialogButtonBox, QLabel)
from PySide6.QtCore import Qt

class SetExitsDialog(QDialog):
    def __init__(self, region_id: str, screen_id: str, project, parent=None):
        super().__init__(parent)
        self.region_id = region_id
        self.screen_id = screen_id
        self.project = project
        self.screen_def = self.project.screens.get(region_id, {}).get(screen_id)
        
        self.setWindowTitle(f"Set Exits - {screen_id}")
        self.resize(300, 200)
        
        self.combo_north = QComboBox()
        self.combo_south = QComboBox()
        self.combo_east = QComboBox()
        self.combo_west = QComboBox()
        
        self._populate_combos()
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        form.addRow("North Exit:", self.combo_north)
        form.addRow("South Exit:", self.combo_south)
        form.addRow("East Exit:", self.combo_east)
        form.addRow("West Exit:", self.combo_west)
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _populate_combos(self):
        screens = list(self.project.screens.get(self.region_id, {}).keys())
        screens.sort()
        
        options = ["null"] + screens
        
        for combo in (self.combo_north, self.combo_south, self.combo_east, self.combo_west):
            combo.addItems(options)
            
        if self.screen_def:
            self._set_combo_current(self.combo_north, self.screen_def.exits.north)
            self._set_combo_current(self.combo_south, self.screen_def.exits.south)
            self._set_combo_current(self.combo_east, self.screen_def.exits.east)
            self._set_combo_current(self.combo_west, self.screen_def.exits.west)
            
    def _set_combo_current(self, combo: QComboBox, value: str):
        if not value:
            combo.setCurrentText("null")
        else:
            idx = combo.findText(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText("null")
                
    def accept(self):
        if self.screen_def:
            def get_val(combo):
                t = combo.currentText()
                return None if t == "null" else t
                
            self.screen_def.exits.north = get_val(self.combo_north)
            self.screen_def.exits.south = get_val(self.combo_south)
            self.screen_def.exits.east = get_val(self.combo_east)
            self.screen_def.exits.west = get_val(self.combo_west)
        super().accept()
