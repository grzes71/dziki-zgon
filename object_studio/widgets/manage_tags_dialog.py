from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QLineEdit, QPushButton, QMessageBox, QLabel)
from PySide6.QtCore import Signal
from ..models import Project

class ManageTagsDialog(QDialog):
    tags_changed = Signal()

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zarządzaj tagami")
        self.resize(320, 360)
        self.project = project

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Lista dostępnych tagów w projekcie:"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Sekcja dodawania
        add_layout = QHBoxLayout()
        self.edit_new_tag = QLineEdit()
        self.edit_new_tag.setPlaceholderText("Nazwa nowego tagu...")
        self.edit_new_tag.returnPressed.connect(self._on_add_tag)
        add_layout.addWidget(self.edit_new_tag)

        btn_add = QPushButton("+ Dodaj")
        btn_add.clicked.connect(self._on_add_tag)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        # Sekcja usuwania
        btn_del = QPushButton("- Usuń zaznaczony tag")
        btn_del.clicked.connect(self._on_delete_tag)
        layout.addWidget(btn_del)

        # Przycisk Zamknij
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _refresh_list(self):
        self.list_widget.clear()
        for tag in self.project.available_tags:
            self.list_widget.addItem(tag)

    def _on_add_tag(self):
        tag_text = self.edit_new_tag.text().strip()
        if not tag_text:
            return
        
        if tag_text in self.project.available_tags:
            QMessageBox.information(self, "Tag istnieje", f"Tag '{tag_text}' już istnieje.")
            return

        self.project.available_tags.append(tag_text)
        self.edit_new_tag.clear()
        self._refresh_list()
        self.tags_changed.emit()

    def _on_delete_tag(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        
        tag_to_remove = item.text()
        reply = QMessageBox.question(
            self,
            "Usuwanie tagu",
            f"Czy na pewno chcesz usunąć tag '{tag_to_remove}'?\nZostanie on wycofany ze wszystkich obiektów.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if tag_to_remove in self.project.available_tags:
            self.project.available_tags.remove(tag_to_remove)

        # Usuń tag z obiektów
        for obj in self.project.objects:
            if tag_to_remove in obj.tags:
                obj.tags.remove(tag_to_remove)

        self._refresh_list()
        self.tags_changed.emit()
