from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from typing import List, Optional
from world_studio.models import InventoryItemDef


class SecretItemSelectionDialog(QDialog):
    """Dialog for selecting an Inventory Item associated with a Secret Object."""

    def __init__(self, inventory_items: List[InventoryItemDef], initial_item_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.inventory_items = inventory_items
        self.selected_item_id: Optional[int] = None

        self.setWindowTitle("Wybierz przedmiot dla Secret Object")
        self.resize(380, 150)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        label_info = QLabel("Ten obiekt jest typu <b>Secret</b>. Wybierz przedmiot z ekwipunku, który Gerwalt znajdzie po podniesieniu:")
        label_info.setWordWrap(True)
        layout.addWidget(label_info)

        self.combo_items = QComboBox()
        if not self.inventory_items:
            self.combo_items.addItem("Brak przedmiotów w obiekcie items.yaml", None)
        else:
            for item in self.inventory_items:
                display_text = f"[{item.id}] {item.description} (pos: {item.charset_position})"
                self.combo_items.addItem(display_text, item.id)

        # Pre-select initial_item_id if provided
        if initial_item_id is not None:
            idx = self.combo_items.findData(initial_item_id)
            if idx >= 0:
                self.combo_items.setCurrentIndex(idx)

        form.addRow("Przedmiot:", self.combo_items)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        item_id = self.combo_items.currentData()
        if item_id is None:
            QMessageBox.warning(self, "Brak przedmiotu", "Należy wybrać prawidłowy przedmiot z listy.")
            return
        self.selected_item_id = item_id
        self.accept()
