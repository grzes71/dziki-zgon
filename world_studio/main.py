import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                              QVBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox,
                              QSplitter, QTabWidget, QScrollArea, QInputDialog, QDialog,
                              QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QComboBox)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.region_tree import RegionTreeWidget
from world_studio.widgets.object_palette import ObjectPaletteWidget
from world_studio.widgets.live_region_view import LiveRegionViewWidget
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.widgets.preview_dialog import PreviewDialog

class WorldStudioMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Studio")
        self.resize(1280, 800)
        
        self.project = ProjectManager()
        self.charset = Charset()
        
        self.current_region_id = None
        self.current_screen_id = None
        
        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel (Tree + Palette)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.region_tree = RegionTreeWidget()
        self.region_tree.region_selected.connect(self._on_region_selected)
        self.region_tree.screen_double_clicked.connect(self._on_screen_double_clicked)
        self.region_tree.request_add_region.connect(self._on_add_region)
        self.region_tree.request_add_region.connect(self._on_add_region)
        left_layout.addWidget(self.region_tree, 1)
        
        self.object_palette = ObjectPaletteWidget()
        self.object_palette.object_selected.connect(self._on_object_selected)
        left_layout.addWidget(self.object_palette, 2)
        
        splitter.addWidget(left_panel)
        
        # Central Panel (Tabs)
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        
        # Tab 1: Live Region
        self.scroll_live = QScrollArea()
        self.scroll_live.setWidgetResizable(True)
        self.live_view = LiveRegionViewWidget()
        self.live_view.screen_double_clicked.connect(self._on_screen_double_clicked)
        self.live_view.empty_cell_add_requested.connect(self._on_empty_cell_add_requested)
        self.live_view.screen_edit_requested.connect(self._on_screen_rename_requested)
        self.live_view.screen_delete_requested.connect(self._on_screen_delete_requested)
        self.live_view.screen_preview_requested.connect(self._on_screen_preview_requested)
        self.scroll_live.setWidget(self.live_view)
        self.tabs.addTab(self.scroll_live, "Live Region")
        
        # Tab 2: Screen Canvas
        self.scroll_canvas = QScrollArea()
        self.scroll_canvas.setWidgetResizable(True)
        self.scroll_canvas.setAlignment(Qt.AlignCenter)
        self.canvas_view = ScreenCanvasWidget()
        self.canvas_view.screen_changed.connect(self._on_screen_changed)
        self.scroll_canvas.setWidget(self.canvas_view)
        self.tabs.addTab(self.scroll_canvas, "Screen Canvas")
        
        splitter.setSizes([300, 980])

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        act_open = QAction("Open World Folder...", self)
        act_open.triggered.connect(self.action_open_world)
        file_menu.addAction(act_open)
        
        act_load_char = QAction("Load Charset...", self)
        act_load_char.triggered.connect(self.action_load_charset)
        file_menu.addAction(act_load_char)
        
        file_menu.addSeparator()
        
        act_save = QAction("Save Project", self)
        act_save.triggered.connect(self.action_save_project)
        file_menu.addAction(act_save)

    def action_open_world(self):
        folder = QFileDialog.getExistingDirectory(self, "Select world folder")
        if folder:
            if self.project.load_project(Path(folder)):
                self.region_tree.populate(self.project)
                self.object_palette.populate(self.project, self.charset)
                self.statusBar().showMessage(f"World loaded: {folder}")
            else:
                QMessageBox.warning(self, "Error", "Invalid world folder (missing world.yaml).")

    def action_load_charset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Charset", "", "Atari Font (*.fnt);;All Files (*)")
        if path:
            if self.charset.load(Path(path)):
                self.object_palette.populate(self.project, self.charset)
                self._refresh_views()
                self.statusBar().showMessage(f"Charset loaded: {path}")
            else:
                QMessageBox.warning(self, "Error", "Failed to load charset (must be 1024 bytes).")

    def action_save_project(self):
        if self.project.save_project():
            self.statusBar().showMessage("Project saved successfully.")
            QMessageBox.information(self, "Saved", "Project saved successfully.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save project.")

    def _on_region_selected(self, region_id):
        self.current_region_id = region_id
        self.live_view.set_data(region_id, self.project, self.charset)
        self.tabs.setCurrentIndex(0)

    def _on_screen_double_clicked(self, region_id, screen_id):
        self.current_region_id = region_id
        self.current_screen_id = screen_id
        
        screen_def = self.project.screens.get(region_id, {}).get(screen_id)
        if screen_def:
            self.canvas_view.set_data(screen_def, self.project, self.charset)
            self.tabs.setCurrentIndex(1)

    def _on_object_selected(self, object_id):
        self.canvas_view.active_tool = object_id

    def _on_add_region(self):
        if not self.project.world_dir:
            QMessageBox.warning(self, "Error", "No project loaded.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Region")
        layout = QFormLayout(dialog)
        
        edit_id = QLineEdit()
        edit_name = QLineEdit()
        spin_rows = QSpinBox()
        spin_rows.setRange(1, 100)
        spin_cols = QSpinBox()
        spin_cols.setRange(1, 100)
        
        layout.addRow("Region ID (e.g. DARK_FOREST):", edit_id)
        layout.addRow("Name:", edit_name)
        layout.addRow("Rows:", spin_rows)
        layout.addRow("Columns:", spin_cols)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)
        
        if dialog.exec() == QDialog.Accepted:
            r_id = edit_id.text().strip().upper()
            r_name = edit_name.text().strip()
            if not r_id:
                QMessageBox.warning(self, "Error", "Region ID cannot be empty.")
                return
            if self.project.add_region(r_id, r_name, spin_rows.value(), spin_cols.value()):
                self.region_tree.populate(self.project)
            else:
                QMessageBox.warning(self, "Error", f"Region {r_id} already exists.")

    def _on_empty_cell_add_requested(self, region_id, col, row):
        text, ok = QInputDialog.getText(self, f"Add Screen at {col},{row}", "Screen ID (e.g. START):")
        if ok and text:
            s_id = text.strip().upper()
            if not s_id:
                QMessageBox.warning(self, "Error", "Screen ID cannot be empty.")
                return
            if s_id in self.project.screens.get(region_id, {}):
                QMessageBox.warning(self, "Error", f"Screen {s_id} already exists.")
                return
            if self.project.add_screen(region_id, s_id, col, row):
                self.region_tree.populate(self.project)
                self.live_view.update()
            else:
                QMessageBox.warning(self, "Error", f"Failed to add screen {s_id}.")

    def _on_screen_delete_requested(self, region_id, screen_id):
        reply = QMessageBox.question(self, 'Remove Screen', f"Are you sure you want to remove {screen_id}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.project.remove_screen(region_id, screen_id)
            self.region_tree.populate(self.project)
            self.live_view.update()
            if self.current_screen_id == screen_id:
                self.current_screen_id = None
                self.canvas_view.set_data(None, None, None)

    def _on_screen_rename_requested(self, region_id, screen_id):
        text, ok = QInputDialog.getText(self, "Rename Screen", "New Screen ID:", text=screen_id)
        if ok and text:
            new_id = text.strip().upper()
            if new_id and new_id != screen_id:
                if new_id in self.project.screens.get(region_id, {}):
                    QMessageBox.warning(self, "Error", f"Screen {new_id} already exists.")
                    return
                sdef = self.project.screens[region_id].pop(screen_id)
                sdef.id = new_id
                self.project.screens[region_id][new_id] = sdef
                self.project.update_all_exits(region_id)
                self.region_tree.populate(self.project)
                self.live_view.update()
                if self.current_screen_id == screen_id:
                    self.current_screen_id = new_id
                    self.canvas_view.set_data(sdef, self.project, self.charset)

    def _on_screen_preview_requested(self, region_id, screen_id):
        dialog = PreviewDialog(region_id, screen_id, self.project, self.charset, self)
        dialog.showFullScreen()
        dialog.exec()

    def _on_screen_changed(self):
        self.live_view.update() # Refresh live region
        
    def _refresh_views(self):
        if self.current_region_id:
            self.live_view.set_data(self.current_region_id, self.project, self.charset)
        if self.current_region_id and self.current_screen_id:
            screen_def = self.project.screens.get(self.current_region_id, {}).get(self.current_screen_id)
            if screen_def:
                self.canvas_view.set_data(screen_def, self.project, self.charset)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            'Quit World Studio', 
            "Are you sure you want to quit? You might have unsaved changes.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WorldStudioMainWindow()
    window.show()
    sys.exit(app.exec())
