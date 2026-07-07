from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from ..models import Project, ObjectDefinition

class ObjectListWidget(QWidget):
    object_selected = Signal(ObjectDefinition)
    add_requested = Signal()
    delete_requested = Signal(ObjectDefinition)
    copy_requested = Signal(ObjectDefinition)
    shift_requested = Signal(ObjectDefinition, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.current_object = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("+ Dodaj")
        self.btn_add.clicked.connect(self.add_requested.emit)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_copy = QPushButton("Kopiuj")
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        btn_layout.addWidget(self.btn_copy)
        
        self.btn_del = QPushButton("- Usuń")
        self.btn_del.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.btn_del)
        
        layout.addLayout(btn_layout)
        
    def set_project(self, project: Project):
        self.project = project
        self.current_object = None
        self.refresh_list()
        
    def refresh_list(self, select_obj=None):
        self.list_widget.clear()
        if not self.project:
            return
            
        # Sortowanie ułatwi widok
        self.project.objects.sort(key=lambda x: x.code)
            
        for obj in self.project.objects:
            self.list_widget.addItem(f"[{obj.code}] {obj.id}")
            
        if select_obj and select_obj in self.project.objects:
            self.current_object = select_obj
            idx = self.project.objects.index(self.current_object)
            self.list_widget.setCurrentRow(idx)
        elif self.current_object in self.project.objects:
            idx = self.project.objects.index(self.current_object)
            self.list_widget.setCurrentRow(idx)

    def _on_selection_changed(self):
        if not self.project:
            return
            
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.project.objects):
            self.current_object = self.project.objects[row]
            self.object_selected.emit(self.current_object)
        else:
            self.current_object = None

    def _on_delete_clicked(self):
        if self.current_object:
            self.delete_requested.emit(self.current_object)

    def _on_copy_clicked(self):
        if self.current_object:
            self.copy_requested.emit(self.current_object)

    def _on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item or not self.current_object:
            return
            
        menu = QMenu(self)
        
        act_up = menu.addAction("Shift Up")
        act_up.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'up'))
        
        act_down = menu.addAction("Shift Down")
        act_down.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'down'))
        
        act_left = menu.addAction("Shift Left")
        act_left.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'left'))
        
        act_right = menu.addAction("Shift Right")
        act_right.triggered.connect(lambda: self.shift_requested.emit(self.current_object, 'right'))
        
        menu.exec(self.list_widget.mapToGlobal(pos))

