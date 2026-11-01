from __future__ import annotations

import sys
import copy
from pathlib import Path
from typing import Optional, Union, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QScrollArea, QDialog,
    QLineEdit, QComboBox, QFormLayout, QDialogButtonBox, QLabel
)
from PySide6.QtGui import QAction, QKeySequence

from sprite_studio.models import Project, Sprite, Animation, Frame
from sprite_studio.io import load_project, save_project
from sprite_studio.validation import validate_project
from sprite_studio.history import HistoryManager, Command
from sprite_studio.widgets.sprite_list import SpriteListWidget
from sprite_studio.widgets.properties import PropertiesWidget
from sprite_studio.widgets.pixel_editor import PixelEditorWidget
from sprite_studio.widgets.timeline import TimelineWidget
from sprite_studio.widgets.preview import PreviewWidget
from sprite_studio.widgets.import_dialog import ImageImportDialog


class GenericCommand(Command):
    def __init__(self, description: str, do_action, undo_action):
        self.description = description
        self._do = do_action
        self._undo = undo_action

    def redo(self):
        self._do()

    def undo(self):
        self._undo()


class CombineSpritesDialog(QDialog):
    """Dialog allowing user to choose two 2-color sprites to combine into a 4-color sprite."""
    def __init__(self, sprites: List[Sprite], current_sprite: Optional[Sprite] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Combine Two Sprites into 4-Color Sprite")
        self.sprites = sprites
        self._setup_ui(current_sprite)

    def _setup_ui(self, current_sprite: Optional[Sprite]):
        layout = QFormLayout(self)

        self.combo_p0 = QComboBox()
        self.combo_p1 = QComboBox()

        for s in self.sprites:
            label = f"{s.id} ({s.description})" if s.description else str(s.id)
            self.combo_p0.addItem(label, s)
            self.combo_p1.addItem(label, s)

        # Preselect
        if current_sprite and current_sprite in self.sprites:
            idx = self.sprites.index(current_sprite)
            self.combo_p0.setCurrentIndex(idx)
            if len(self.sprites) > 1:
                self.combo_p1.setCurrentIndex((idx + 1) % len(self.sprites))

        layout.addRow("Layer 0 (Player A / P0):", self.combo_p0)
        layout.addRow("Layer 1 (Player B / P1):", self.combo_p1)

        default_id = f"{self.combo_p0.currentData().id}_4C" if self.combo_p0.currentData() else "COMBINED_4C"
        self.edit_id = QLineEdit(str(default_id))
        layout.addRow("New Sprite ID:", self.edit_id)

        self.lbl_info = QLabel("P0 and P1 will be merged into a 4-color PMG sprite using GTIA overlap mixing.")
        self.lbl_info.setStyleSheet("color: #888888; font-style: italic;")
        layout.addRow(self.lbl_info)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_selection(self):
        return self.combo_p0.currentData(), self.combo_p1.currentData(), self.edit_id.text().strip()


class MainWindow(QMainWindow):
    clipboard_frame_pixels = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Studio")
        self.project_path: Optional[Path] = None
        self.project = Project()
        self.history = HistoryManager()
        
        self.current_sprite: Optional[Sprite] = None
        self.current_frame_idx = -1
        self.clipboard_frame_pixels = None
        
        self._setup_ui()
        self._setup_menu()
        self._refresh_all()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left Panel (Sprite list)
        self.list_widget = SpriteListWidget()
        self.list_widget.sprite_selected.connect(self._on_sprite_selected)
        self.list_widget.add_requested.connect(self._on_add_sprite)
        self.list_widget.delete_requested.connect(self._on_delete_sprite)
        self.list_widget.copy_requested.connect(self._on_copy_sprite)
        main_layout.addWidget(self.list_widget, 1)
        
        # Center Panel (Editor + Timeline)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        self.pixel_editor = PixelEditorWidget()
        self.pixel_editor.pixel_changed.connect(self._on_pixel_changed)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.pixel_editor)
        center_layout.addWidget(scroll_area, 3)
        
        self.timeline = TimelineWidget()
        self.timeline.frame_selected.connect(self._on_frame_selected)
        self.timeline.add_requested.connect(self._on_add_frame)
        self.timeline.delete_requested.connect(self._on_delete_frame)
        self.timeline.duplicate_requested.connect(self._on_dup_frame)
        self.timeline.insert_requested.connect(self._on_insert_frame)
        self.timeline.reorder_requested.connect(self._on_reorder_frame)
        self.timeline.copy_requested.connect(self._on_copy_frame)
        self.timeline.paste_requested.connect(self._on_paste_frame)
        self.timeline.mirror_h_requested.connect(self._on_mirror_h_frame)
        self.timeline.mirror_v_requested.connect(self._on_mirror_v_frame)
        self.timeline.inverse_requested.connect(self._on_inverse_frame)
        self.timeline.clear_requested.connect(self._on_clear_frame)
        self.timeline.shift_requested.connect(self._on_shift_frame)
        center_layout.addWidget(self.timeline, 1)
        
        main_layout.addWidget(center_panel, 3)
        
        # Right Panel (Properties + Preview)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.props = PropertiesWidget()
        self.props.id_changed.connect(self._on_prop_id)
        self.props.description_changed.connect(self._on_prop_description)
        self.props.color_mode_changed.connect(self._on_prop_color_mode)
        self.props.height_changed.connect(self._on_prop_height)
        self.props.color_changed.connect(self._on_prop_color)
        self.props.color2_changed.connect(self._on_prop_color2)
        self.props.duration_changed.connect(self._on_prop_duration)
        self.props.loop_changed.connect(self._on_prop_loop)
        right_layout.addWidget(self.props)
        
        self.preview = PreviewWidget()
        right_layout.addWidget(self.preview)
        
        right_layout.addStretch()
        main_layout.addWidget(right_panel, 1)

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        act_new = QAction("New", self)
        act_new.triggered.connect(self.action_new)
        file_menu.addAction(act_new)
        
        act_open = QAction("Open...", self)
        act_open.triggered.connect(self.action_open)
        file_menu.addAction(act_open)
        
        act_save = QAction("Save", self)
        act_save.triggered.connect(self.action_save)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        file_menu.addAction(act_save)
        
        act_save_as = QAction("Save As...", self)
        act_save_as.triggered.connect(self.action_save_as)
        file_menu.addAction(act_save_as)
        
        file_menu.addSeparator()
        act_import = QAction("Import Image...", self)
        act_import.triggered.connect(self.action_import_image)
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        file_menu.addAction(act_import)
        
        edit_menu = menubar.addMenu("Edit")
        
        act_undo = QAction("Undo", self)
        act_undo.triggered.connect(self._undo)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(act_undo)
        
        act_redo = QAction("Redo", self)
        act_redo.triggered.connect(self._redo)
        act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        edit_menu.addAction(act_redo)
        
        edit_menu.addSeparator()
        act_copy = QAction("Copy Frame", self)
        act_copy.triggered.connect(lambda: self._on_copy_frame(self.current_frame_idx))
        act_copy.setShortcut(QKeySequence("Ctrl+C"))
        edit_menu.addAction(act_copy)
        
        act_paste = QAction("Paste Frame", self)
        act_paste.triggered.connect(lambda: self._on_paste_frame(self.current_frame_idx))
        act_paste.setShortcut(QKeySequence("Ctrl+V"))
        edit_menu.addAction(act_paste)
        
        edit_menu.addSeparator()
        act_inverse = QAction("Inverse Frame", self)
        act_inverse.triggered.connect(lambda: self._on_inverse_frame(self.current_frame_idx))
        edit_menu.addAction(act_inverse)
        
        act_clear = QAction("Clear Frame", self)
        act_clear.triggered.connect(lambda: self._on_clear_frame(self.current_frame_idx))
        edit_menu.addAction(act_clear)
        
        act_mirror_h = QAction("H Mirror Frame", self)
        act_mirror_h.triggered.connect(lambda: self._on_mirror_h_frame(self.current_frame_idx))
        edit_menu.addAction(act_mirror_h)

        act_mirror_v = QAction("V Mirror Frame", self)
        act_mirror_v.triggered.connect(lambda: self._on_mirror_v_frame(self.current_frame_idx))
        edit_menu.addAction(act_mirror_v)

        # Tools Menu (4-Color operations)
        tools_menu = menubar.addMenu("Tools")
        act_combine = QAction("Combine Two Sprites into 4-Color Sprite...", self)
        act_combine.triggered.connect(self.action_combine_sprites)
        tools_menu.addAction(act_combine)

        act_split = QAction("Split 4-Color Sprite into Two 2-Color Sprites", self)
        act_split.triggered.connect(self.action_split_sprite)
        tools_menu.addAction(act_split)

    # --- Commands Framework ---
    
    def _execute_cmd(self, desc, do_act, undo_act, refresh_fn=None):
        def _do():
            do_act()
            if refresh_fn: refresh_fn()
        def _undo():
            undo_act()
            if refresh_fn: refresh_fn()
        cmd = GenericCommand(desc, _do, _undo)
        self.history.execute(cmd)

    def _undo(self):
        self.history.undo()
    def _redo(self):
        self.history.redo()

    # --- Actions ---
    
    def action_new(self):
        self.project_path = None
        self.project = Project()
        self.history.clear()
        self._refresh_all()
        
    def action_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Sprite JSON (*.sprite.json);;All Files (*)")
        if path:
            try:
                new_proj = load_project(Path(path))
                errs = validate_project(new_proj)
                if errs:
                    QMessageBox.warning(self, "Validation Errors", "Loaded file has validation errors:\n" + "\n".join(errs))
                self.project_path = Path(path)
                self.project = new_proj
                self.history.clear()
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project:\n{e}")

    def action_save(self):
        if not self.project_path:
            self.action_save_as()
            return
        self._save_to(self.project_path)

    def action_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "project.sprite.json", "Sprite JSON (*.sprite.json);;All Files (*)")
        if path:
            self.project_path = Path(path)
            self._save_to(self.project_path)

    def action_import_image(self):
        if not self.current_sprite:
            QMessageBox.warning(self, "Import Image", "Please select or create a sprite first before importing an image.")
            return

        file_filter = (
            "Image Files (*.png *.jpg *.jpeg *.bmp);;"
            "PNG (*.png);;"
            "JPEG (*.jpg *.jpeg);;"
            "BMP (*.bmp);;"
            "All Files (*)"
        )
        path, _ = QFileDialog.getOpenFileName(self, "Import Raster Image", "", file_filter)
        if not path:
            return

        try:
            dialog = ImageImportDialog(
                image_path=path,
                target_height=self.current_sprite.height,
                sprite_color_mode=self.current_sprite.color_mode,
                color1=self.current_sprite.color,
                color2=self.current_sprite.color2,
                parent=self,
            )
            if dialog.exec() == QDialog.Accepted:
                new_frames = dialog.get_imported_frames()
                imported_mode = dialog.get_color_mode()
                if not new_frames:
                    QMessageBox.warning(self, "Import Image", "No frames were generated from the image.")
                    return

                spr = self.current_sprite
                old_frames = list(spr.frames)
                old_height = spr.height
                old_color_mode = spr.color_mode
                new_height = dialog.get_target_height()

                def do():
                    if imported_mode == 4 and spr.color_mode == 2:
                        spr.color_mode = 4
                    if new_height != old_height:
                        adjusted = []
                        for f in spr.frames:
                            nf = Frame(pixels=list(f.pixels))
                            if new_height > old_height:
                                nf.pixels.extend(["00000000"] * (new_height - old_height))
                            else:
                                nf.pixels = nf.pixels[:new_height]
                            adjusted.append(nf)
                        spr.frames = adjusted
                        spr.height = new_height
                    spr.frames.extend(new_frames)
                    self.list_widget.update_sprite_display(spr)
                    self.props.update_from_sprite(spr)

                def undo():
                    spr.height = old_height
                    spr.color_mode = old_color_mode
                    spr.frames = list(old_frames)
                    self.list_widget.update_sprite_display(spr)
                    self.props.update_from_sprite(spr)

                self._execute_cmd(f"Import {len(new_frames)} Frames", do, undo, self._refresh_sprite)
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Successfully imported {len(new_frames)} frame(s) to sprite {spr.id}.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import image:\n{e}")

    def action_combine_sprites(self):
        if len(self.project.sprites) < 2:
            QMessageBox.information(
                self, "Combine Sprites", "Project must contain at least two sprites to combine them."
            )
            return

        dialog = CombineSpritesDialog(self.project.sprites, self.current_sprite, self)
        if dialog.exec() == QDialog.Accepted:
            spr0, spr1, new_id = dialog.get_selection()
            if not spr0 or not spr1:
                return

            if not new_id:
                new_id = f"{spr0.id}_COMBINED_4C"

            combined_frames = Sprite.combine_layer_frames(spr0.frames, spr1.frames)
            height = max(spr0.height, spr1.height)

            new_sprite = Sprite(
                id=new_id,
                description=f"Combined {spr0.id} + {spr1.id}",
                width=8,
                height=height,
                color=spr0.color,
                color_mode=4,
                color2=spr1.color,
                animation=copy.deepcopy(spr0.animation),
                frames=combined_frames
            )

            def do():
                self.project.sprites.append(new_sprite)

            def undo():
                if new_sprite in self.project.sprites:
                    self.project.sprites.remove(new_sprite)

            self._execute_cmd(f"Combine Sprites into {new_id}", do, undo, self._refresh_all)
            self._on_sprite_selected(new_sprite)

    def action_split_sprite(self):
        if not self.current_sprite:
            QMessageBox.warning(self, "Split Sprite", "No sprite selected.")
            return

        if self.current_sprite.color_mode != 4:
            QMessageBox.information(
                self, "Split Sprite", "Only 4-color sprites can be split into separate P0 and P1 layers."
            )
            return

        spr = self.current_sprite
        id_str = str(spr.id)

        p0_frames = [
            Frame(pixels=spr.get_layer_pixels(i, layer=0))
            for i in range(len(spr.frames))
        ]
        p1_frames = [
            Frame(pixels=spr.get_layer_pixels(i, layer=1))
            for i in range(len(spr.frames))
        ]

        spr_p0 = Sprite(
            id=f"{id_str}_P0",
            description=f"{spr.description} (P0)"[:40],
            width=8,
            height=spr.height,
            color=spr.color,
            color_mode=2,
            color2=0,
            animation=copy.deepcopy(spr.animation),
            frames=p0_frames
        )
        spr_p1 = Sprite(
            id=f"{id_str}_P1",
            description=f"{spr.description} (P1)"[:40],
            width=8,
            height=spr.height,
            color=spr.color2,
            color_mode=2,
            color2=0,
            animation=copy.deepcopy(spr.animation),
            frames=p1_frames
        )

        def do():
            self.project.sprites.append(spr_p0)
            self.project.sprites.append(spr_p1)

        def undo():
            if spr_p0 in self.project.sprites:
                self.project.sprites.remove(spr_p0)
            if spr_p1 in self.project.sprites:
                self.project.sprites.remove(spr_p1)

        self._execute_cmd(f"Split Sprite {id_str}", do, undo, self._refresh_all)
        self._on_sprite_selected(spr_p0)

    def _save_to(self, path):
        errs = validate_project(self.project)
        if errs:
            QMessageBox.critical(self, "Validation Errors", "Cannot save due to validation errors:\n" + "\n".join(errs))
            return
            
        if save_project(path, self.project):
            QMessageBox.information(self, "Saved", "Project saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save project.")

    # --- Refreshing UI ---
    
    def _refresh_all(self):
        self.list_widget.set_project(self.project)
        self._refresh_sprite()

    def _refresh_sprite(self):
        if self.current_sprite and self.current_sprite not in self.project.sprites:
            self.current_sprite = None
            self.current_frame_idx = -1
            
        self.props.update_from_sprite(self.current_sprite)
        self.preview.set_sprite(self.current_sprite)
        
        if self.current_sprite:
            if self.current_frame_idx >= len(self.current_sprite.frames) or self.current_frame_idx < 0:
                self.current_frame_idx = 0 if self.current_sprite.frames else -1
            self.timeline.set_frames(len(self.current_sprite.frames), self.current_frame_idx)
        else:
            self.timeline.set_frames(0, -1)
            
        self._refresh_frame()

    def _refresh_frame(self):
        if not self.current_sprite or self.current_frame_idx < 0:
            self.pixel_editor.set_data(None, None, 2, 0, 0)
            return
            
        frame = self.current_sprite.frames[self.current_frame_idx]
        
        onion = None
        if self.current_frame_idx > 0:
            onion = self.current_sprite.frames[self.current_frame_idx - 1]
        elif self.current_sprite.animation.loop and len(self.current_sprite.frames) > 1:
            onion = self.current_sprite.frames[-1]
            
        self.pixel_editor.set_data(
            frame=frame,
            onion_frame=onion,
            color_mode=self.current_sprite.color_mode,
            color1=self.current_sprite.color,
            color2=self.current_sprite.color2
        )

    # --- Signals ---

    def _on_sprite_selected(self, sprite):
        self.current_sprite = sprite
        self._refresh_sprite()

    def _on_frame_selected(self, idx):
        if self.current_sprite and 0 <= idx < len(self.current_sprite.frames):
            self.current_frame_idx = idx
            self._refresh_frame()

    def _on_add_sprite(self):
        used_ids = {s.id for s in self.project.sprites if isinstance(s.id, int)}
        new_id = 1
        while new_id in used_ids and new_id < 255:
            new_id += 1
        new_spr = Sprite(id=new_id)
        new_spr.frames.append(Frame(pixels=["00000000"] * new_spr.height))
        
        def do(): self.project.sprites.append(new_spr)
        def undo(): self.project.sprites.remove(new_spr)
        self._execute_cmd("Add Sprite", do, undo, self._refresh_all)
        self._on_sprite_selected(new_spr)

    def _on_delete_sprite(self, spr):
        idx = self.project.sprites.index(spr)
        def do(): self.project.sprites.remove(spr)
        def undo(): self.project.sprites.insert(idx, spr)
        self._execute_cmd("Delete Sprite", do, undo, self._refresh_all)

    def _on_copy_sprite(self, spr):
        new_spr = copy.deepcopy(spr)
        if isinstance(new_spr.id, int):
            used_ids = {s.id for s in self.project.sprites if isinstance(s.id, int)}
            new_id = 1
            while new_id in used_ids and new_id < 255:
                new_id += 1
            new_spr.id = new_id
        else:
            new_spr.id = f"{new_spr.id}_COPY"
            
        if new_spr.description:
            new_spr.description = f"{new_spr.description[:33]} (Copy)"
        def do(): self.project.sprites.append(new_spr)
        def undo(): self.project.sprites.remove(new_spr)
        self._execute_cmd("Copy Sprite", do, undo, self._refresh_all)
        self._on_sprite_selected(new_spr)

    # ... frame timeline commands
    def _on_add_frame(self):
        if not self.current_sprite: return
        spr = self.current_sprite
        new_f = Frame(pixels=["00000000"] * spr.height)
        def do(): spr.frames.append(new_f)
        def undo(): spr.frames.remove(new_f)
        self._execute_cmd("Add Frame", do, undo, self._refresh_sprite)

    def _on_delete_frame(self, idx):
        if not self.current_sprite or len(self.current_sprite.frames) <= 1: return
        spr = self.current_sprite
        f = spr.frames[idx]
        def do(): spr.frames.pop(idx)
        def undo(): spr.frames.insert(idx, f)
        self._execute_cmd("Delete Frame", do, undo, self._refresh_sprite)

    def _on_dup_frame(self, idx):
        if not self.current_sprite: return
        spr = self.current_sprite
        f = copy.deepcopy(spr.frames[idx])
        def do(): spr.frames.append(f)
        def undo(): spr.frames.remove(f)
        self._execute_cmd("Duplicate Frame", do, undo, self._refresh_sprite)

    def _on_insert_frame(self, idx):
        if not self.current_sprite: return
        spr = self.current_sprite
        new_f = Frame(pixels=["00000000"] * spr.height)
        def do(): spr.frames.insert(idx, new_f)
        def undo(): spr.frames.pop(idx)
        self._execute_cmd("Insert Frame", do, undo, self._refresh_sprite)

    def _on_reorder_frame(self, from_idx, to_idx):
        if not self.current_sprite: return
        spr = self.current_sprite
        def do():
            f = spr.frames.pop(from_idx)
            spr.frames.insert(to_idx, f)
        def undo():
            f = spr.frames.pop(to_idx)
            spr.frames.insert(from_idx, f)
        self._execute_cmd("Reorder Frame", do, undo, self._refresh_sprite)

    def _on_copy_frame(self, idx=None):
        focus = self.focusWidget()
        if isinstance(focus, QLineEdit) and focus.hasSelectedText():
            focus.copy()
            return

        if not self.current_sprite:
            return
        if idx is None or idx < 0:
            idx = self.current_frame_idx
        if idx < 0 or idx >= len(self.current_sprite.frames):
            return

        f = self.current_sprite.frames[idx]
        MainWindow.clipboard_frame_pixels = list(f.pixels)
        self.clipboard_frame_pixels = MainWindow.clipboard_frame_pixels

    def _on_paste_frame(self, idx=None):
        focus = self.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.paste()
            return

        clip = MainWindow.clipboard_frame_pixels or self.clipboard_frame_pixels
        if not self.current_sprite or not clip:
            return
        if idx is None or idx < 0:
            idx = self.current_frame_idx
        if idx < 0 or idx >= len(self.current_sprite.frames):
            return

        spr = self.current_sprite
        if len(clip) != spr.height:
            QMessageBox.warning(
                self, "Paste Frame",
                f"Clipboard frame height ({len(clip)}) does not match sprite height ({spr.height})."
            )
            return

        f = spr.frames[idx]
        old_pixels = list(f.pixels)
        new_pixels = list(clip)

        # If sprite is 2-color but clipboard has 4-color values, clamp to '1'
        if spr.color_mode == 2:
            new_pixels = [
                "".join('1' if c in ('1', '2', '3') else '0' for c in row)
                for row in new_pixels
            ]

        def do(): f.pixels = list(new_pixels)
        def undo(): f.pixels = list(old_pixels)
        self._execute_cmd("Paste Frame", do, undo, self._refresh_frame)

    def _on_mirror_h_frame(self, idx):
        if not self.current_sprite or idx < 0 or idx >= len(self.current_sprite.frames): return
        spr = self.current_sprite
        f = spr.frames[idx]
        old_pixels = list(f.pixels)
        reversed_pixels = [row[::-1] for row in old_pixels]
        def do(): f.pixels = reversed_pixels
        def undo(): f.pixels = old_pixels
        self._execute_cmd("H Mirror Frame", do, undo, self._refresh_frame)

    def _on_mirror_v_frame(self, idx):
        if not self.current_sprite or idx < 0 or idx >= len(self.current_sprite.frames): return
        spr = self.current_sprite
        f = spr.frames[idx]
        old_pixels = list(f.pixels)
        reversed_pixels = list(reversed(old_pixels))
        def do(): f.pixels = reversed_pixels
        def undo(): f.pixels = old_pixels
        self._execute_cmd("V Mirror Frame", do, undo, self._refresh_frame)

    def _on_inverse_frame(self, idx):
        if not self.current_sprite or idx < 0 or idx >= len(self.current_sprite.frames): return
        spr = self.current_sprite
        f = spr.frames[idx]
        old_pixels = list(f.pixels)

        if spr.color_mode == 4:
            # 0 <-> 3, 1 <-> 2
            inv_map = {'0': '3', '1': '2', '2': '1', '3': '0'}
            inversed = ["".join(inv_map.get(c, '0') for c in row) for row in old_pixels]
        else:
            inversed = ["".join("0" if c == "1" else "1" for c in row) for row in old_pixels]

        def do(): f.pixels = inversed
        def undo(): f.pixels = old_pixels
        self._execute_cmd("Inverse Frame", do, undo, self._refresh_frame)

    def _on_clear_frame(self, idx):
        if not self.current_sprite or idx < 0 or idx >= len(self.current_sprite.frames): return
        spr = self.current_sprite
        f = spr.frames[idx]
        old_pixels = list(f.pixels)
        cleared = ["00000000"] * spr.height
        def do(): f.pixels = cleared
        def undo(): f.pixels = old_pixels
        self._execute_cmd("Clear Frame", do, undo, self._refresh_frame)

    def _on_shift_frame(self, direction):
        if not self.current_sprite or self.current_frame_idx < 0: return
        spr = self.current_sprite
        f = spr.frames[self.current_frame_idx]
        old_pixels = list(f.pixels)
        
        new_pixels = []
        if direction == "left":
            new_pixels = [row[1:] + "0" for row in old_pixels]
        elif direction == "right":
            new_pixels = ["0" + row[:-1] for row in old_pixels]
        elif direction == "up":
            new_pixels = old_pixels[1:] + ["00000000"]
        elif direction == "down":
            new_pixels = ["00000000"] + old_pixels[:-1]
            
        def do(): f.pixels = new_pixels
        def undo(): f.pixels = old_pixels
        self._execute_cmd(f"Shift {direction}", do, undo, self._refresh_frame)

    # ... pixel editing
    def _on_pixel_changed(self, x, y, val):
        if not self.current_sprite or self.current_frame_idx < 0: return
        f = self.current_sprite.frames[self.current_frame_idx]
        old_val = f.pixels[y][x]
        
        def do():
            row = list(f.pixels[y])
            row[x] = val
            f.pixels[y] = "".join(row)
        def undo():
            row = list(f.pixels[y])
            row[x] = old_val
            f.pixels[y] = "".join(row)
            
        self._execute_cmd("Edit Pixel", do, undo, self._refresh_frame)

    # ... properties
    def _on_prop_id(self, new_id: Union[int, str]):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_id = spr.id
        if old_id == new_id: return
        def do():
            spr.id = new_id
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
        def undo():
            spr.id = old_id
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
        self._execute_cmd("Change ID", do, undo)

    def _on_prop_description(self, new_desc: str):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_desc = spr.description
        if old_desc == new_desc: return
        def do():
            spr.description = new_desc
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
        def undo():
            spr.description = old_desc
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
        self._execute_cmd("Change Description", do, undo)

    def _on_prop_color_mode(self, new_mode: int):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_mode = spr.color_mode
        if old_mode == new_mode: return

        # If switching from 4-color to 2-color, check if we need to convert pixels
        has_multi = any(
            any(c in ('2', '3') for c in row)
            for f in spr.frames
            for row in f.pixels
        )

        old_frames = copy.deepcopy(spr.frames)

        if new_mode == 2 and has_multi:
            res = QMessageBox.question(
                self,
                "Convert to 2-color",
                "Converting to 2-color will merge Layer 1 pixels (colors 2 and 3) to color 1. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res != QMessageBox.Yes:
                self.props.update_from_sprite(spr)
                return

            new_frames = []
            for f in spr.frames:
                new_rows = ["".join('1' if c in ('1', '2', '3') else '0' for c in row) for row in f.pixels]
                new_frames.append(Frame(pixels=new_rows))
        else:
            new_frames = old_frames

        def do():
            spr.color_mode = new_mode
            spr.frames = new_frames
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
            self._refresh_sprite()

        def undo():
            spr.color_mode = old_mode
            spr.frames = old_frames
            self.list_widget.update_sprite_display(spr)
            self.props.update_from_sprite(spr)
            self._refresh_sprite()

        self._execute_cmd(f"Change Color Mode to {new_mode}C", do, undo)

    def _on_prop_height(self, new_h):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_h = spr.height
        if old_h == new_h: return
        
        old_frames = copy.deepcopy(spr.frames)
        new_frames = []
        for f in spr.frames:
            nf = Frame(pixels=list(f.pixels))
            if new_h > old_h:
                nf.pixels.extend(["00000000"] * (new_h - old_h))
            else:
                nf.pixels = nf.pixels[:new_h]
            new_frames.append(nf)
            
        def do():
            spr.height = new_h
            spr.frames = new_frames
        def undo():
            spr.height = old_h
            spr.frames = old_frames
            
        self._execute_cmd("Change Height", do, undo, self._refresh_sprite)

    def _on_prop_color(self, new_c: int):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_c = spr.color
        def do():
            spr.color = new_c
            self.props.update_from_sprite(spr)
        def undo():
            spr.color = old_c
            self.props.update_from_sprite(spr)
        self._execute_cmd("Change Color 1", do, undo, self._refresh_sprite)

    def _on_prop_color2(self, new_c2: int):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_c2 = spr.color2
        def do():
            spr.color2 = new_c2
            self.props.update_from_sprite(spr)
        def undo():
            spr.color2 = old_c2
            self.props.update_from_sprite(spr)
        self._execute_cmd("Change Color 2", do, undo, self._refresh_sprite)

    def _on_prop_duration(self, new_d):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_d = spr.animation.frame_duration
        def do(): spr.animation.frame_duration = new_d
        def undo(): spr.animation.frame_duration = old_d
        self._execute_cmd("Change Duration", do, undo, self._refresh_sprite)

    def _on_prop_loop(self, new_l):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_l = spr.animation.loop
        def do(): spr.animation.loop = new_l
        def undo(): spr.animation.loop = old_l
        self._execute_cmd("Change Loop", do, undo, self._refresh_sprite)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
