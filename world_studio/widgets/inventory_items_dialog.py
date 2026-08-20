from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                               QPushButton, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QMessageBox,
                               QHeaderView, QDialogButtonBox)
from PySide6.QtCore import Qt
from typing import List, Optional
from world_studio.models import InventoryItemDef
from world_studio.project_manager import ProjectManager


class InventoryItemEditDialog(QDialog):
    def __init__(self, item: Optional[InventoryItemDef] = None, existing_ids: List[int] = None, parent=None):
        super().__init__(parent)
        self.item = item
        self.existing_ids = existing_ids or []
        self.result_item: Optional[InventoryItemDef] = None
        
        if item:
            self.setWindowTitle("Edit Inventory Item")
        else:
            self.setWindowTitle("Add Inventory Item")
            
        self.resize(350, 200)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # ID field (1..255)
        self.spin_id = QSpinBox()
        self.spin_id.setRange(1, 255)
        if item:
            self.spin_id.setValue(item.id)
            self.spin_id.setEnabled(False)
        else:
            next_id = 1
            while next_id in self.existing_ids:
                next_id += 1
            self.spin_id.setValue(min(next_id, 255))
        form.addRow("ID (Index):", self.spin_id)

        # Description field (required)
        self.edit_description = QLineEdit()
        if item:
            self.edit_description.setText(item.description)
        self.edit_description.setPlaceholderText("opis przedmiotu (wymagany)")
        form.addRow("Opis:", self.edit_description)

        # Charset Position field (0..255)
        self.spin_charset_pos = QSpinBox()
        self.spin_charset_pos.setRange(0, 255)
        if item:
            self.spin_charset_pos.setValue(item.charset_position)
        else:
            self.spin_charset_pos.setValue(14)
        form.addRow("Pozycja w charset:", self.spin_charset_pos)

        # Consumable checkbox
        self.check_consumable = QCheckBox("Tak (usuwany przy użyciu)")
        if item:
            self.check_consumable.setChecked(item.consumable)
        else:
            self.check_consumable.setChecked(True)
        form.addRow("Zużywalny:", self.check_consumable)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        item_id = self.spin_id.value()
        desc = self.edit_description.text().strip()
        charset_pos = self.spin_charset_pos.value()
        consumable = self.check_consumable.isChecked()

        if not desc:
            QMessageBox.warning(self, "Błąd walidacji", "Pole 'Opis' jest wymagane.")
            self.edit_description.setFocus()
            return

        if not self.item and item_id in self.existing_ids:
            QMessageBox.warning(self, "Błąd walidacji", f"Przedmiot o ID {item_id} już istnieje.")
            self.spin_id.setFocus()
            return

        self.result_item = InventoryItemDef(
            id=item_id,
            description=desc,
            charset_position=charset_pos,
            consumable=consumable
        )
        self.accept()


class InventoryItemsDialog(QDialog):
    def __init__(self, project: ProjectManager, parent=None):
        super().__init__(parent)
        self.project = project
        self.items = [item.model_copy() for item in project.inventory_items]
        
        self.setWindowTitle("Inventory Items")
        self.resize(550, 350)
        
        layout = QVBoxLayout(self)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Opis", "Pozycja w charset", "Zużywalny"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._on_edit_item)
        layout.addWidget(self.table)
        
        # Buttons layout
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("Add Item")
        btn_add.clicked.connect(self._on_add_item)
        btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton("Edit Item")
        btn_edit.clicked.connect(self._on_edit_item)
        btn_layout.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete Item")
        btn_delete.clicked.connect(self._on_delete_item)
        btn_layout.addWidget(btn_delete)
        
        layout.addLayout(btn_layout)
        
        # Bottom OK / Cancel
        dialog_btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_btns.accepted.connect(self._on_accept)
        dialog_btns.rejected.connect(self.reject)
        layout.addWidget(dialog_btns)
        
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        self.items.sort(key=lambda x: x.id)
        for row, item in enumerate(self.items):
            self.table.insertRow(row)
            item_id = QTableWidgetItem(str(item.id))
            item_id.setTextAlignment(Qt.AlignCenter)
            
            item_desc = QTableWidgetItem(item.description)
            
            item_pos = QTableWidgetItem(str(item.charset_position))
            item_pos.setTextAlignment(Qt.AlignCenter)
            
            item_consumable = QTableWidgetItem("Tak" if item.consumable else "Nie")
            item_consumable.setTextAlignment(Qt.AlignCenter)
            
            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_desc)
            self.table.setItem(row, 2, item_pos)
            self.table.setItem(row, 3, item_consumable)

    def _on_add_item(self):
        existing_ids = [it.id for it in self.items]
        dialog = InventoryItemEditDialog(item=None, existing_ids=existing_ids, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.result_item:
            self.items.append(dialog.result_item)
            self._populate_table()

    def _on_edit_item(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.items):
            return
        current_item = self.items[row]
        dialog = InventoryItemEditDialog(item=current_item, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.result_item:
            self.items[row] = dialog.result_item
            self._populate_table()

    def _on_delete_item(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.items):
            return
        item_to_delete = self.items[row]
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete item #{item_to_delete.id} ('{item_to_delete.description}')?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.items.pop(row)
            self._populate_table()

    def _on_accept(self):
        self.project.inventory_items = self.items
        self.accept()
