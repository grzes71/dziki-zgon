from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                               QPushButton, QHBoxLayout, QMessageBox)
from PySide6.QtCore import Signal
from sprite_studio.models import Sprite, Project

class SpriteListWidget(QWidget):
    sprite_selected = Signal(object) # emits Sprite
    add_requested = Signal()
    delete_requested = Signal(object) # emits Sprite
    copy_requested = Signal(object) # emits Sprite

    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_requested.emit)
        
        self.btn_del = QPushButton("Del")
        self.btn_del.clicked.connect(self._on_delete_clicked)
        
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_del)
        layout.addLayout(btn_layout)

    def set_project(self, project: Project):
        self.project = project
        self.refresh_list()

    def refresh_list(self, select_obj=None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        if self.project:
            for sprite in self.project.sprites:
                item = QListWidgetItem(sprite.id)
                item.setData(100, sprite)
                self.list_widget.addItem(item)
                
                if select_obj and select_obj == sprite:
                    self.list_widget.setCurrentItem(item)
                    
        self.list_widget.blockSignals(False)
        if select_obj:
            self.sprite_selected.emit(select_obj)
        else:
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                self.sprite_selected.emit(self.list_widget.currentItem().data(100))
            else:
                self.sprite_selected.emit(None)

    def _on_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            self.sprite_selected.emit(current.data(100))
        else:
            self.sprite_selected.emit(None)

    def _on_delete_clicked(self):
        item = self.list_widget.currentItem()
        if item:
            self.delete_requested.emit(item.data(100))

    def _on_copy_clicked(self):
        item = self.list_widget.currentItem()
        if item:
            self.copy_requested.emit(item.data(100))
