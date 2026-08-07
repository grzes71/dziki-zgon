from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QMenu, QComboBox, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from ..models import Project, ObjectDefinition

ALL_TAGS_OPTION = "(Wszystkie tagi)"

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
        self.filtered_objects = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Filtr tagów
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtr:"))
        self.combo_tag_filter = QComboBox()
        self.combo_tag_filter.addItem(ALL_TAGS_OPTION)
        self.combo_tag_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.combo_tag_filter, 1)
        layout.addLayout(filter_layout)
        
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
        self.update_tag_filter_options()
        self.refresh_list()

    def update_tag_filter_options(self):
        current_text = self.combo_tag_filter.currentText()
        self.combo_tag_filter.blockSignals(True)
        self.combo_tag_filter.clear()
        self.combo_tag_filter.addItem(ALL_TAGS_OPTION)

        if self.project:
            for tag in self.project.available_tags:
                self.combo_tag_filter.addItem(tag)

        idx = self.combo_tag_filter.findText(current_text)
        if idx >= 0:
            self.combo_tag_filter.setCurrentIndex(idx)
        else:
            self.combo_tag_filter.setCurrentIndex(0)
        self.combo_tag_filter.blockSignals(False)

    def _on_filter_changed(self, text):
        self.refresh_list(select_obj=self.current_object)
        
    def refresh_list(self, select_obj=None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.filtered_objects = []

        if not self.project:
            self.list_widget.blockSignals(False)
            return
            
        # Sortowanie ułatwi widok
        self.project.objects.sort(key=lambda x: x.code)

        selected_tag = self.combo_tag_filter.currentText()
        
        for obj in self.project.objects:
            if selected_tag != ALL_TAGS_OPTION and selected_tag:
                if selected_tag not in obj.tags:
                    continue
            self.filtered_objects.append(obj)
            tag_str = f" [{', '.join(obj.tags)}]" if obj.tags else ""
            self.list_widget.addItem(f"[{obj.code}] {obj.id}{tag_str}")
            
        self.list_widget.blockSignals(False)

        target_obj = select_obj or self.current_object
        if target_obj and target_obj in self.filtered_objects:
            self.current_object = target_obj
            idx = self.filtered_objects.index(self.current_object)
            self.list_widget.setCurrentRow(idx)
        elif self.filtered_objects:
            self.list_widget.setCurrentRow(0)
            self._on_selection_changed()
        else:
            self.current_object = None
            self.object_selected.emit(None)

    def _on_selection_changed(self):
        if not self.project:
            return
            
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_objects):
            self.current_object = self.filtered_objects[row]
            self.object_selected.emit(self.current_object)
        else:
            self.current_object = None
            self.object_selected.emit(None)

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
