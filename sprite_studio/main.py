import sys
import copy
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox, QScrollArea)
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

# Basic command class wrapper
class GenericCommand(Command):
    def __init__(self, description, do_action, undo_action):
        self.description = description
        self._do = do_action
        self._undo = undo_action

    def redo(self):
        self._do()

    def undo(self):
        self._undo()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Studio")
        self.project_path = None
        self.project = Project()
        self.history = HistoryManager()
        
        self.current_sprite = None
        self.current_frame_idx = -1
        
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
        self.timeline.mirror_requested.connect(self._on_mirror_frame)
        self.timeline.shift_requested.connect(self._on_shift_frame)
        center_layout.addWidget(self.timeline, 1)
        
        main_layout.addWidget(center_panel, 3)
        
        # Right Panel (Properties + Preview)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.props = PropertiesWidget()
        self.props.id_changed.connect(self._on_prop_id)
        self.props.height_changed.connect(self._on_prop_height)
        self.props.color_changed.connect(self._on_prop_color)
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
        
        edit_menu = menubar.addMenu("Edit")
        
        act_undo = QAction("Undo", self)
        act_undo.triggered.connect(self._undo)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(act_undo)
        
        act_redo = QAction("Redo", self)
        act_redo.triggered.connect(self._redo)
        act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        edit_menu.addAction(act_redo)

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
            self.pixel_editor.set_data(None, None, 0)
            return
            
        frame = self.current_sprite.frames[self.current_frame_idx]
        
        onion = None
        if self.current_frame_idx > 0:
            onion = self.current_sprite.frames[self.current_frame_idx - 1]
        elif self.current_sprite.animation.loop and len(self.current_sprite.frames) > 1:
            onion = self.current_sprite.frames[-1]
            
        self.pixel_editor.set_data(frame, onion, self.current_sprite.color)

    # --- Signals ---

    def _on_sprite_selected(self, sprite):
        self.current_sprite = sprite
        self._refresh_sprite()

    def _on_frame_selected(self, idx):
        if self.current_sprite and 0 <= idx < len(self.current_sprite.frames):
            self.current_frame_idx = idx
            self._refresh_frame()

    def _on_add_sprite(self):
        new_spr = Sprite(id=f"SPRITE_{len(self.project.sprites)}")
        new_spr.frames.append(Frame(pixels=["00000000"] * new_spr.height))
        
        def do(): self.project.sprites.append(new_spr)
        def undo(): self.project.sprites.remove(new_spr)
        self._execute_cmd("Add Sprite", do, undo, self._refresh_all)

    def _on_delete_sprite(self, spr):
        idx = self.project.sprites.index(spr)
        def do(): self.project.sprites.remove(spr)
        def undo(): self.project.sprites.insert(idx, spr)
        self._execute_cmd("Delete Sprite", do, undo, self._refresh_all)

    def _on_copy_sprite(self, spr):
        new_spr = copy.deepcopy(spr)
        new_spr.id = new_spr.id + "_COPY"
        def do(): self.project.sprites.append(new_spr)
        def undo(): self.project.sprites.remove(new_spr)
        self._execute_cmd("Copy Sprite", do, undo, self._refresh_all)

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

    def _on_mirror_frame(self, idx):
        if not self.current_sprite: return
        spr = self.current_sprite
        f = spr.frames[idx]
        old_pixels = list(f.pixels)
        mirrored = [row[::-1] for row in old_pixels]
        def do():
            f.pixels = mirrored
        def undo():
            f.pixels = old_pixels
        self._execute_cmd("Mirror Frame", do, undo, self._refresh_frame)

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
            
        def do():
            f.pixels = new_pixels
        def undo():
            f.pixels = old_pixels
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
    def _on_prop_id(self, new_id):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_id = spr.id
        def do(): spr.id = new_id
        def undo(): spr.id = old_id
        self._execute_cmd("Change ID", do, undo, lambda: self.list_widget.refresh_list(spr))

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

    def _on_prop_color(self, new_c):
        if not self.current_sprite: return
        spr = self.current_sprite
        old_c = spr.color
        def do(): spr.color = new_c
        def undo(): spr.color = old_c
        self._execute_cmd("Change Color", do, undo, self._refresh_sprite)

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
