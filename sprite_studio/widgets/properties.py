from __future__ import annotations

from typing import Optional, Union
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QPushButton, QComboBox, QLabel, QHBoxLayout
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor

from sprite_studio.models import Sprite
from sprite_studio.palette import AtariColorDialog, get_atari_rgb, mix_atari_colors

class PropertiesWidget(QWidget):
    id_changed = Signal(object)
    description_changed = Signal(str)
    color_mode_changed = Signal(int)
    height_changed = Signal(int)
    color_changed = Signal(int)
    color2_changed = Signal(int)
    duration_changed = Signal(int)
    loop_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.block_updates = False
        self.current_sprite: Optional[Sprite] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.edit_id = QLineEdit()
        self.edit_id.setMaxLength(64)
        self.edit_id.setPlaceholderText("Sprite ID (e.g. 1 or GERWALT_RIGHT)")
        self.edit_id.editingFinished.connect(self._on_id_edited)
        layout.addRow("ID:", self.edit_id)

        self.edit_description = QLineEdit()
        self.edit_description.setMaxLength(40)
        self.edit_description.setPlaceholderText("Description (max 40 chars)")
        self.edit_description.textEdited.connect(self._on_description_edited)
        layout.addRow("Description:", self.edit_description)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("2 colors (1 Player)", 2)
        self.combo_mode.addItem("4 colors (2 Players Overlap)", 4)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        layout.addRow("Color Mode:", self.combo_mode)
        
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 256)
        self.spin_height.valueChanged.connect(self._on_height_changed)
        layout.addRow("Height:", self.spin_height)
        
        # Color 1
        self.btn_color1 = QPushButton("Color 1: $00")
        self.btn_color1.clicked.connect(self._on_color1_clicked)
        layout.addRow("Color 1 (P0):", self.btn_color1)

        # Color 2 (for 4-color mode)
        self.btn_color2 = QPushButton("Color 2: $00")
        self.btn_color2.clicked.connect(self._on_color2_clicked)
        self.lbl_color2_title = QLabel("Color 2 (P1):")
        layout.addRow(self.lbl_color2_title, self.btn_color2)

        # Mix color preview (for 4-color mode)
        self.lbl_color_mix = QLabel("Mix: $00")
        self.lbl_color_mix.setStyleSheet("font-weight: bold; padding: 4px; border: 1px solid #444;")
        self.lbl_color_mix_title = QLabel("Overlap Mix:")
        layout.addRow(self.lbl_color_mix_title, self.lbl_color_mix)
        
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(1, 255)
        self.spin_duration.valueChanged.connect(self._on_duration_changed)
        layout.addRow("Frame Duration:", self.spin_duration)
        
        self.chk_loop = QCheckBox()
        self.chk_loop.stateChanged.connect(self._on_loop_changed)
        layout.addRow("Loop:", self.chk_loop)
        
        self.setEnabled(False)

    def _style_button_color(self, btn: QPushButton, color_idx: int, prefix: str):
        rgb = get_atari_rgb(color_idx)
        text_color = "#000000" if rgb.lightness() > 128 else "#ffffff"
        btn.setText(f"{prefix}: ${color_idx:02X} ({color_idx})")
        btn.setStyleSheet(f"background-color: {rgb.name()}; color: {text_color}; font-weight: bold;")

    def update_from_sprite(self, sprite: Optional[Sprite]):
        self.current_sprite = sprite
        if not sprite:
            self.setEnabled(False)
            self.block_updates = True
            self.edit_id.clear()
            self.edit_description.clear()
            self.combo_mode.setCurrentIndex(0)
            self.spin_height.setValue(1)
            self.spin_duration.setValue(4)
            self.chk_loop.setChecked(True)
            self.block_updates = False
            return
            
        self.setEnabled(True)
        self.block_updates = True
        
        if not self.edit_id.hasFocus() or self.edit_id.text() != str(sprite.id):
            self.edit_id.setText(str(sprite.id))
        if not self.edit_description.hasFocus() or self.edit_description.text() != sprite.description:
            self.edit_description.setText(sprite.description)

        mode_idx = 1 if sprite.color_mode == 4 else 0
        self.combo_mode.setCurrentIndex(mode_idx)

        self.spin_height.setValue(sprite.height)
        self.spin_duration.setValue(sprite.animation.frame_duration)
        self.chk_loop.setChecked(sprite.animation.loop)
        
        # Style colors
        self._style_button_color(self.btn_color1, sprite.color, "Color 1")

        is_4c = sprite.color_mode == 4
        self.btn_color2.setVisible(is_4c)
        self.lbl_color2_title.setVisible(is_4c)
        self.lbl_color_mix.setVisible(is_4c)
        self.lbl_color_mix_title.setVisible(is_4c)

        if is_4c:
            self._style_button_color(self.btn_color2, sprite.color2, "Color 2")
            mix = mix_atari_colors(sprite.color, sprite.color2)
            rgb_mix = get_atari_rgb(mix)
            text_col = "#000000" if rgb_mix.lightness() > 128 else "#ffffff"
            self.lbl_color_mix.setText(f"Mix (OR): ${mix:02X} ({mix})")
            self.lbl_color_mix.setStyleSheet(
                f"background-color: {rgb_mix.name()}; color: {text_col}; font-weight: bold; padding: 4px;"
            )

        self.block_updates = False

    def _on_id_edited(self):
        if not self.block_updates:
            raw = self.edit_id.text().strip()
            # If numeric, emit int, else string
            if raw.isdigit():
                val: Union[int, str] = int(raw)
            else:
                val = raw
            self.id_changed.emit(val)

    def _on_description_edited(self, text: str):
        if not self.block_updates:
            self.description_changed.emit(text)

    def _on_mode_changed(self, idx: int):
        if not self.block_updates:
            mode = self.combo_mode.currentData()
            self.color_mode_changed.emit(mode)
            
    def _on_height_changed(self, value: int):
        if not self.block_updates:
            self.height_changed.emit(value)
            
    def _on_color1_clicked(self):
        if not self.current_sprite:
            return
        new_color, ok = AtariColorDialog.get_color(
            initial_color=self.current_sprite.color,
            parent=self,
            title="Select Color 1 (Player A)"
        )
        if ok and not self.block_updates:
            self.color_changed.emit(new_color)

    def _on_color2_clicked(self):
        if not self.current_sprite:
            return
        new_color, ok = AtariColorDialog.get_color(
            initial_color=self.current_sprite.color2,
            parent=self,
            title="Select Color 2 (Player B)"
        )
        if ok and not self.block_updates:
            self.color2_changed.emit(new_color)

    def _on_duration_changed(self, value: int):
        if not self.block_updates:
            self.duration_changed.emit(value)
            
    def _on_loop_changed(self, state: int):
        if not self.block_updates:
            self.loop_changed.emit(bool(state))
