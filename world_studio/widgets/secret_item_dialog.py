from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from typing import List, Optional, Dict, Any
from world_studio.models import InventoryItemDef


class SecretItemSelectionDialog(QDialog):
    """Dialog for selecting an Inventory Item associated with a Secret Object."""

    def __init__(
        self,
        inventory_items: List[InventoryItemDef],
        initial_item_id: Optional[int] = None,
        placed_secrets: Optional[Dict[int, Dict[str, Any]]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.inventory_items = inventory_items
        self.initial_item_id = initial_item_id
        self.placed_secrets = placed_secrets or {}
        self.selected_item_id: Optional[int] = None

        self.setWindowTitle("Wybierz przedmiot dla Secret Object")
        self.resize(440, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        label_info = QLabel(
            "Ten obiekt jest typu <b>Secret</b>. Wybierz przedmiot z ekwipunku, który Gerwalt znajdzie po podniesieniu:<br>"
            "<small style='color: #888;'>Każdy unikalny przedmiot typu Secret może wystąpić w Świecie Gry tylko raz.</small>"
        )
        label_info.setWordWrap(True)
        layout.addWidget(label_info)

        self.combo_items = QComboBox()
        if not self.inventory_items:
            self.combo_items.addItem("Brak przedmiotów w pliku items.yaml", None)
        else:
            for item in self.inventory_items:
                is_taken = (item.id in self.placed_secrets) and (item.id != initial_item_id)
                if is_taken:
                    info = self.placed_secrets[item.id]
                    display_text = f"[{item.id}] {item.description} (Zajęty: {info['region_id']} / {info['screen_id']})"
                else:
                    display_text = f"[{item.id}] {item.description} (pos: {item.charset_position})"
                self.combo_items.addItem(display_text, item.id)

        # Pre-select initial_item_id if provided
        if initial_item_id is not None:
            idx = self.combo_items.findData(initial_item_id)
            if idx >= 0:
                self.combo_items.setCurrentIndex(idx)
        else:
            # If not provided, try to select first available (not taken) item
            for idx in range(self.combo_items.count()):
                item_id = self.combo_items.itemData(idx)
                if item_id is not None and item_id not in self.placed_secrets:
                    self.combo_items.setCurrentIndex(idx)
                    break

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
        if item_id in self.placed_secrets and item_id != self.initial_item_id:
            info = self.placed_secrets[item_id]
            item_obj = next((item for item in self.inventory_items if item.id == item_id), None)
            item_name = item_obj.description if item_obj else f"ID {item_id}"
            QMessageBox.warning(
                self,
                "Przedmiot Secret już istnieje",
                f"Obiekt Secret z przedmiotem '{item_name}' (ID: {item_id}) znajduje się już w Świecie Gry w regionie '{info['region_id']}' na ekranie '{info['screen_id']}'.\n\nDany obiekt typu Secret można dodać do Świata Gry tylko raz."
            )
            return
        self.selected_item_id = item_id
        self.accept()

