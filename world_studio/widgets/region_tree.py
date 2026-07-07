from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from world_studio.project_manager import ProjectManager

class RegionTreeWidget(QTreeWidget):
    # Signals
    screen_double_clicked = Signal(str, str) # region_id, screen_id
    region_selected = Signal(str) # region_id
    request_add_region = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def populate(self, project: ProjectManager):
        self.clear()
        
        for region_id, region_def in project.regions.items():
            r_item = QTreeWidgetItem(self, [region_def.name])
            r_item.setData(0, 32, "REGION")
            r_item.setData(0, 33, region_id)
            
            screens = project.screens.get(region_id, {})
            # Sort screens by ID
            for screen_id in sorted(screens.keys()):
                s_item = QTreeWidgetItem(r_item, [screen_id])
                s_item.setData(0, 32, "SCREEN")
                s_item.setData(0, 33, region_id)
                s_item.setData(0, 34, screen_id)
                
            r_item.setExpanded(True)

    def _on_selection_changed(self):
        items = self.selectedItems()
        if not items:
            return
        item = items[0]
        item_type = item.data(0, 32)
        region_id = item.data(0, 33)
        if region_id:
            self.region_selected.emit(region_id)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        item_type = item.data(0, 32)
        if item_type == "SCREEN":
            region_id = item.data(0, 33)
            screen_id = item.data(0, 34)
            self.screen_double_clicked.emit(region_id, screen_id)

    def _on_context_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)

        act_add_region = QAction("Add Region", self)
        act_add_region.triggered.connect(lambda: self.request_add_region.emit())
        
        if not item:
            menu.addAction(act_add_region)
        else:
            item_type = item.data(0, 32)
            region_id = item.data(0, 33)
            
            if item_type == "REGION":
                menu.addAction(act_add_region)

        menu.exec_(self.viewport().mapToGlobal(pos))
