from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QDialogButtonBox, QLabel)
from PySide6.QtCore import Qt
from world_studio.models import EnemyInstance

class EnemyPropertiesDialog(QDialog):
    def __init__(self, enemy_instance: EnemyInstance, enemy_defs: list, enemy_colors: list = None, parent=None):
        super().__init__(parent)
        self.enemy_instance = enemy_instance
        self.enemy_defs = enemy_defs
        
        self.setWindowTitle("Enemy Properties")
        self.resize(350, 220)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Position info
        form.addRow("Position:", QLabel(f"X: {enemy_instance.x}, Y: {enemy_instance.y}"))
        
        # Enemy Type (from enemies.yaml definitions list)
        self.combo_type = QComboBox()
        for edef in enemy_defs:
            self.combo_type.addItem(edef.name, edef.id)
            
        # Select current type
        idx = self.combo_type.findData(enemy_instance.enemy)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        form.addRow("Enemy Type:", self.combo_type)
        
        # Strategy (vertical/horizontal/random/chaotic)
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(["vertical", "horizontal", "random", "chaotic"])
        self.combo_strategy.setCurrentText(enemy_instance.strategy)
        form.addRow("Movement Strategy:", self.combo_strategy)
        
        # Speed (slow/medium/fast)
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["slow", "medium", "fast"])
        self.combo_speed.setCurrentText(enemy_instance.speed)
        form.addRow("Movement Speed:", self.combo_speed)
        
        # Color (English name, editable combo box)
        self.combo_color = QComboBox()
        self.combo_color.setEditable(True)
        colors = enemy_colors if enemy_colors else [
            "white", "red", "green", "blue", "yellow", 
            "magenta", "cyan", "orange", "purple", "brown", 
            "gray", "black"
        ]
        self.combo_color.addItems(colors)
        self.combo_color.setCurrentText(enemy_instance.color)
        form.addRow("Color (English):", self.combo_color)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def accept(self):
        self.enemy_instance.enemy = self.combo_type.currentData()
        self.enemy_instance.strategy = self.combo_strategy.currentText()
        self.enemy_instance.speed = self.combo_speed.currentText()
        self.enemy_instance.color = self.combo_color.currentText().strip().lower()
        super().accept()
