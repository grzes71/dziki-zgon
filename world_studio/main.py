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
        self.region_tree.request_add_screen.connect(self._on_add_screen)
        self.region_tree.request_edit_screen.connect(self._on_edit_screen)
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

    def _on_add_screen(self, region_id):
        if not self.project.world_dir:
            return
            
        region_def = self.project.regions.get(region_id)
        if region_def:
            current_screens = len(self.project.screens.get(region_id, {}))
            max_screens = region_def.layout.rows * region_def.layout.columns
            if current_screens >= max_screens:
                QMessageBox.warning(self, "Error", f"Cannot add more screens.\nRegion {region_id} layout is {region_def.layout.rows}x{region_def.layout.columns} (max {max_screens} screens).")
                return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Add Screen to {region_id}")
        layout = QFormLayout(dialog)
        
        edit_id = QLineEdit()
        layout.addRow("Screen ID (e.g. START):", edit_id)
        
        existing_screens = ["None"] + sorted(list(self.project.screens.get(region_id, {}).keys()))
        
        combo_north = QComboBox()
        combo_north.addItems(existing_screens)
        layout.addRow("North Exit:", combo_north)
        
        combo_south = QComboBox()
        combo_south.addItems(existing_screens)
        layout.addRow("South Exit:", combo_south)
        
        combo_east = QComboBox()
        combo_east.addItems(existing_screens)
        layout.addRow("East Exit:", combo_east)
        
        combo_west = QComboBox()
        combo_west.addItems(existing_screens)
        layout.addRow("West Exit:", combo_west)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)
        
        while True:
            if dialog.exec() == QDialog.Accepted:
                s_id = edit_id.text().strip().upper()
                if not s_id:
                    QMessageBox.warning(self, "Error", "Screen ID cannot be empty.")
                    continue
                    
                if s_id in self.project.screens.get(region_id, {}):
                    QMessageBox.warning(self, "Error", f"Screen {s_id} already exists in {region_id}.")
                    continue
                    
                exits = {}
                if combo_north.currentText() != "None": exits["north"] = combo_north.currentText()
                if combo_south.currentText() != "None": exits["south"] = combo_south.currentText()
                if combo_east.currentText() != "None": exits["east"] = combo_east.currentText()
                if combo_west.currentText() != "None": exits["west"] = combo_west.currentText()
                
                ok, msg = self.project.validate_screen_exits(region_id, s_id, exits)
                if not ok:
                    QMessageBox.warning(self, "Validation Error", msg)
                    continue
                
                if self.project.add_screen(region_id, s_id, exits):
                    self.region_tree.populate(self.project)
                    break
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add screen {s_id}.")
                    continue
            else:
                break

    def _on_edit_screen(self, region_id, screen_id):
        if not self.project.world_dir:
            return
            
        screen_def = self.project.screens.get(region_id, {}).get(screen_id)
        if not screen_def:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Screen {screen_id} ({region_id})")
        layout = QFormLayout(dialog)
        
        existing_screens = ["None"] + sorted(list(self.project.screens.get(region_id, {}).keys()))
        
        combo_north = QComboBox()
        combo_north.addItems(existing_screens)
        if screen_def.exits.north: combo_north.setCurrentText(screen_def.exits.north)
        layout.addRow("North Exit:", combo_north)
        
        combo_south = QComboBox()
        combo_south.addItems(existing_screens)
        if screen_def.exits.south: combo_south.setCurrentText(screen_def.exits.south)
        layout.addRow("South Exit:", combo_south)
        
        combo_east = QComboBox()
        combo_east.addItems(existing_screens)
        if screen_def.exits.east: combo_east.setCurrentText(screen_def.exits.east)
        layout.addRow("East Exit:", combo_east)
        
        combo_west = QComboBox()
        combo_west.addItems(existing_screens)
        if screen_def.exits.west: combo_west.setCurrentText(screen_def.exits.west)
        layout.addRow("West Exit:", combo_west)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)
        
        while True:
            if dialog.exec() == QDialog.Accepted:
                exits = {}
                if combo_north.currentText() != "None": exits["north"] = combo_north.currentText()
                if combo_south.currentText() != "None": exits["south"] = combo_south.currentText()
                if combo_east.currentText() != "None": exits["east"] = combo_east.currentText()
                if combo_west.currentText() != "None": exits["west"] = combo_west.currentText()
                
                ok, msg = self.project.validate_screen_exits(region_id, screen_id, exits)
                if not ok:
                    QMessageBox.warning(self, "Validation Error", msg)
                    continue
                
                self.project.update_screen_exits(region_id, screen_id, exits)
                
                # Odśwież canvas jeśli ten ekran jest aktualnie otwarty
                if self.current_region_id == region_id and self.current_screen_id == screen_id:
                    self.canvas_view.set_data(screen_def, self.project, self.charset)
                self.live_view.update()
                break
            else:
                break

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
