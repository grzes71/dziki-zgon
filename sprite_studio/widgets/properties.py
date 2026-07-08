from PySide6.QtWidgets import (QWidget, QFormLayout, QLineEdit, QSpinBox, 
                               QCheckBox, QPushButton, QColorDialog)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor

class PropertiesWidget(QWidget):
    # Signals emitted when user changes something in the UI. 
    # Main window handles these to create commands.
    id_changed = Signal(str)
    height_changed = Signal(int)
    color_changed = Signal(int)
    duration_changed = Signal(int)
    loop_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.block_updates = False
        self.current_color_rgb = (255, 255, 255)

    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.edit_id = QLineEdit()
        self.edit_id.textEdited.connect(self._on_id_edited)
        layout.addRow("ID:", self.edit_id)
        
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 256)
        # using editingFinished so it doesn't trigger on every single keystroke, 
        # or valueChanged if we want immediate. Let's use valueChanged but carefully.
        self.spin_height.valueChanged.connect(self._on_height_changed)
        layout.addRow("Height:", self.spin_height)
        
        self.btn_color = QPushButton("Set Color")
        self.btn_color.clicked.connect(self._on_color_clicked)
        layout.addRow("Color:", self.btn_color)
        
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(1, 255)
        self.spin_duration.valueChanged.connect(self._on_duration_changed)
        layout.addRow("Frame Duration:", self.spin_duration)
        
        self.chk_loop = QCheckBox()
        self.chk_loop.stateChanged.connect(self._on_loop_changed)
        layout.addRow("Loop:", self.chk_loop)
        
        self.setEnabled(False)

    def update_from_sprite(self, sprite):
        if not sprite:
            self.setEnabled(False)
            self.block_updates = True
            self.edit_id.clear()
            self.spin_height.setValue(1)
            self.spin_duration.setValue(4)
            self.chk_loop.setChecked(True)
            self.block_updates = False
            return
            
        self.setEnabled(True)
        self.block_updates = True
        
        self.edit_id.setText(sprite.id)
        self.spin_height.setValue(sprite.height)
        self.spin_duration.setValue(sprite.animation.frame_duration)
        self.chk_loop.setChecked(sprite.animation.loop)
        
        # In a real Atari palette, we'd map color 0..255 to RGB. 
        # For simplicity in UI, we just show the raw index, but the spec says "Color picker".
        # We will keep a basic mapping or just let them pick RGB and we store an approximated int.
        # For now, let's just emit color index.
        self.btn_color.setText(f"Color: {sprite.color}")
        
        self.block_updates = False

    def _on_id_edited(self, text):
        if not self.block_updates:
            self.id_changed.emit(text)
            
    def _on_height_changed(self, value):
        if not self.block_updates:
            self.height_changed.emit(value)
            
    def _on_color_clicked(self):
        # We should show a QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            # In real Atari app, convert QColor to nearest Atari 0..255 index.
            # Here we just use lightness or something as a placeholder 
            # (assuming main.py or a palette handles exact mapping).
            # Let's just emit the 8-bit color representation or an index.
            # Since the user requested a color picker, we can store RGB in sprite_studio if needed, 
            # but JSON contract says "color" is int 0..255. 
            # We'll emit an integer (e.g. grasycale or a simple mapped value) for now.
            # A simple hash or just setting the text to RGB is an option.
            # We will assume Atari palette is managed elsewhere, so we just emit an int.
            idx = (color.red() + color.green() + color.blue()) // 3
            self.color_changed.emit(idx)

    def _on_duration_changed(self, value):
        if not self.block_updates:
            self.duration_changed.emit(value)
            
    def _on_loop_changed(self, state):
        if not self.block_updates:
            self.loop_changed.emit(bool(state))
