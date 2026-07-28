import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                              QVBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox,
                              QSplitter, QTabWidget, QScrollArea, QInputDialog, QDialog,
                              QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QComboBox,
                              QPushButton, QLabel, QGroupBox, QColorDialog)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt

from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.region_tree import RegionTreeWidget
from world_studio.widgets.object_palette import ObjectPaletteWidget
from world_studio.widgets.live_region_view import LiveRegionViewWidget
from world_studio.widgets.screen_canvas import ScreenCanvasWidget
from world_studio.widgets.preview_dialog import PreviewDialog
from world_studio.widgets.exits_dialog import SetExitsDialog

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
        self.region_tree.request_edit_region_colors.connect(self._on_edit_region_colors)
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
        self.live_view.screen_exits_requested.connect(self._on_screen_exits_requested)
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

        tools_menu = menubar.addMenu("Tools")
        act_items = QAction("Inventory Items...", self)
        act_items.triggered.connect(self.action_edit_inventory_items)
        tools_menu.addAction(act_items)

    def action_edit_inventory_items(self):
        if not self.project.world_dir:
            QMessageBox.warning(self, "Error", "No project loaded.")
            return
        from world_studio.widgets.inventory_items_dialog import InventoryItemsDialog
        dialog = InventoryItemsDialog(self.project, self)
        if dialog.exec() == QDialog.Accepted:
            self.statusBar().showMessage("Inventory items updated.")

    def action_open_world(self):
        folder = QFileDialog.getExistingDirectory(self, "Select world folder")
        if folder:
            if self.project.load_project(Path(folder)):
                self.region_tree.populate(self.project)
                self.object_palette.populate(self.project, self.charset, self.current_region_id)
                self.statusBar().showMessage(f"World loaded: {folder}")
            else:
                load_err = getattr(self.project, 'load_error', None)
                if load_err:
                    QMessageBox.warning(self, "Error Reading World", f"Could not load world due to validation error:\n\n{load_err}")
                else:
                    QMessageBox.warning(self, "Error", "Invalid world folder (missing world.yaml).")

    def action_load_charset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Charset", "", "Atari Font (*.fnt);;All Files (*)")
        if path:
            if self.charset.load(Path(path)):
                self.object_palette.populate(self.project, self.charset, self.current_region_id)
                self._refresh_views()
                self.statusBar().showMessage(f"Charset loaded: {path}")
            else:
                QMessageBox.warning(self, "Error", "Failed to load charset (must be 1024 bytes).")

    def action_save_project(self):
        errors = self.project.validate_interactive_objects()
        if errors:
            err_msg = "Cannot save project. Interactive object validation failed:\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Validation Error", err_msg)
            return

        if self.project.save_project():
            self.statusBar().showMessage("Project saved successfully.")
            QMessageBox.information(self, "Saved", "Project saved successfully.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save project.")

    def _on_region_selected(self, region_id):
        self.current_region_id = region_id
        self.live_view.set_data(region_id, self.project, self.charset)
        self.object_palette.populate(self.project, self.charset, region_id)
        self.tabs.setCurrentIndex(0)

    def _on_screen_double_clicked(self, region_id, screen_id):
        self.current_region_id = region_id
        self.current_screen_id = screen_id
        self.object_palette.set_available_regions(list(self.project.regions.keys()), region_id)
        
        screen_def = self.project.screens.get(region_id, {}).get(screen_id)
        if screen_def:
            self.canvas_view.set_data(screen_def, self.project, self.charset, region_id)
            self.tabs.setCurrentIndex(1)

    def _on_object_selected(self, object_id):
        self.canvas_view.active_tool = object_id

    def _create_color_config_box(self, initial_colors: dict, dialog: QDialog):
        group = QGroupBox("Region Playfield Colors")
        layout = QVBoxLayout(group)
        
        form = QFormLayout()
        combo_preset = QComboBox()
        combo_preset.addItem("Default (Atari)")
        for r_id in sorted(self.project.regions.keys()):
            combo_preset.addItem(f"Copy from {r_id}", r_id)
        form.addRow("Preset:", combo_preset)
        
        color_keys = ["PF0", "PF1", "PF2", "PF3_INV", "BACKGROUND"]
        colors_dict = dict(initial_colors)
        buttons = {}
        
        def update_btn(key):
            rgb = colors_dict[key]
            lum = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
            text_color = "black" if lum > 128 else "white"
            buttons[key].setStyleSheet(f"background-color: rgb({rgb[0]},{rgb[1]},{rgb[2]}); color: {text_color}; font-weight: bold; border: 1px solid gray;")
            buttons[key].setText(f"RGB{list(rgb)}")
            
        for k in color_keys:
            btn = QPushButton()
            buttons[k] = btn
            update_btn(k)
            
            def make_click_handler(key):
                def handler():
                    c = QColorDialog.getColor(QColor(*colors_dict[key]), dialog, f"Select Color for {key}")
                    if c.isValid():
                        colors_dict[key] = (c.red(), c.green(), c.blue())
                        update_btn(key)
                return handler
                
            btn.clicked.connect(make_click_handler(k))
            form.addRow(f"{k}:", btn)
            
        def on_preset_changed(idx):
            data = combo_preset.itemData(idx)
            if data and data in self.project.regions:
                preset_colors = self.project.get_region_colors(data)
            else:
                from world_studio.project_manager import DEFAULT_REGION_COLORS
                preset_colors = DEFAULT_REGION_COLORS
                
            for k in color_keys:
                if k in preset_colors:
                    colors_dict[k] = preset_colors[k]
                    update_btn(k)
                    
        combo_preset.currentIndexChanged.connect(on_preset_changed)
        layout.addLayout(form)
        return group, colors_dict

    def _on_add_region(self):
        if not self.project.world_dir:
            QMessageBox.warning(self, "Error", "No project loaded.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Region")
        main_layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        edit_id = QLineEdit()
        edit_name = QLineEdit()
        spin_damage = QSpinBox()
        spin_damage.setRange(0, 255)
        spin_damage.setValue(10)
        spin_rows = QSpinBox()
        spin_rows.setRange(1, 100)
        spin_rows.setValue(3)
        spin_cols = QSpinBox()
        spin_cols.setRange(1, 100)
        spin_cols.setValue(3)
        
        form_layout.addRow("Region ID (e.g. DARK_FOREST):", edit_id)
        form_layout.addRow("Name:", edit_name)
        form_layout.addRow("Damage (PF3 per sec):", spin_damage)
        form_layout.addRow("Rows:", spin_rows)
        form_layout.addRow("Columns:", spin_cols)
        main_layout.addLayout(form_layout)
        
        initial_cols = self.project.get_region_colors(None)
        color_box, colors_dict = self._create_color_config_box(initial_cols, dialog)
        main_layout.addWidget(color_box)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        main_layout.addWidget(btns)
        
        if dialog.exec() == QDialog.Accepted:
            r_id = edit_id.text().strip().upper()
            r_name = edit_name.text().strip()
            if not r_id:
                QMessageBox.warning(self, "Error", "Region ID cannot be empty.")
                return
            if self.project.add_region(r_id, r_name, spin_rows.value(), spin_cols.value(), spin_damage.value(), colors=colors_dict):
                self.region_tree.populate(self.project)
                self._on_region_selected(r_id)
            else:
                QMessageBox.warning(self, "Error", f"Region {r_id} already exists.")

    def _on_edit_region_colors(self, region_id: str):
        if not self.project or region_id not in self.project.regions:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Region Colors - {region_id}")
        main_layout = QVBoxLayout(dialog)
        
        current_cols = self.project.get_region_colors(region_id)
        color_box, colors_dict = self._create_color_config_box(current_cols, dialog)
        main_layout.addWidget(color_box)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        main_layout.addWidget(btns)
        
        if dialog.exec() == QDialog.Accepted:
            self.project.set_region_colors(region_id, colors_dict)
            self._refresh_views()
            self.statusBar().showMessage(f"Updated colors for region {region_id}")

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
                self.canvas_view.set_data(None, None, None, None)

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
                self.project.update_all_exits(region_id, old_id=screen_id, new_id=new_id)
                self.region_tree.populate(self.project)
                self.live_view.update()
                if self.current_screen_id == screen_id:
                    self.current_screen_id = new_id
                    self.canvas_view.set_data(sdef, self.project, self.charset, region_id)

    def _on_screen_preview_requested(self, region_id, screen_id):
        dialog = PreviewDialog(region_id, screen_id, self.project, self.charset, self)
        dialog.showFullScreen()
        dialog.exec()

    def _on_screen_exits_requested(self, region_id, screen_id):
        dialog = SetExitsDialog(region_id, screen_id, self.project, self)
        if dialog.exec() == QDialog.Accepted:
            self.project.save_project()
            self.live_view.update()
            if self.current_screen_id == screen_id:
                # Optionally refresh canvas if exits are visualized, but they are not.
                pass

    def _on_screen_changed(self):
        self.live_view.update() # Refresh live region
        
    def _refresh_views(self):
        if self.current_region_id:
            self.live_view.set_data(self.current_region_id, self.project, self.charset)
        if self.current_region_id and self.current_screen_id:
            screen_def = self.project.screens.get(self.current_region_id, {}).get(self.current_screen_id)
            if screen_def:
                self.canvas_view.set_data(screen_def, self.project, self.charset, self.current_region_id)

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
