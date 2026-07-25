from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QLineEdit, QSpinBox, QCheckBox, QListWidget, QListWidgetItem,
                               QDialogButtonBox, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from typing import Optional, List
from world_studio.models import ObjectInstance, InventoryItemDef

class InteractiveObjectPropertiesDialog(QDialog):
    TYPE_KWATERA = "kwatera"
    TYPE_PORTAL = "portal"

    def __init__(self, obj_instance: ObjectInstance, inventory_items: Optional[List[InventoryItemDef]] = None, parent=None):
        super().__init__(parent)
        self.obj_instance = obj_instance
        self.inventory_items = inventory_items or []
        
        self.setWindowTitle(f"Interactive Object Properties - {obj_instance.object}")
        self.resize(480, 420)
        
        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        
        # Position Info
        self.form.addRow("Position:", QLabel(f"X: {obj_instance.x}, Y: {obj_instance.y}"))
        
        # Interactive Type Selector
        self.combo_type = QComboBox()
        self.combo_type.addItems([self.TYPE_KWATERA, self.TYPE_PORTAL])
        if obj_instance.type in [self.TYPE_KWATERA, self.TYPE_PORTAL]:
            self.combo_type.setCurrentText(obj_instance.type)
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        self.form.addRow("Object Type:", self.combo_type)

        # Fields
        # 1. conditions_met
        self.edit_conditions_met = QLineEdit()
        if obj_instance.conditions_met:
            self.edit_conditions_met.setText(obj_instance.conditions_met)
        self.form.addRow("Wymagania spełnione:", self.edit_conditions_met)

        # 2. conditions_unmet
        self.edit_conditions_unmet = QLineEdit()
        if obj_instance.conditions_unmet:
            self.edit_conditions_unmet.setText(obj_instance.conditions_unmet)
        self.form.addRow("Wymagania niespełnione:", self.edit_conditions_unmet)

        # 3. items_required (checkbox list from inventory_items)
        self.list_items_required = self._create_item_selector(obj_instance.items_required)
        self.form.addRow("Przedmioty wymagane:", self.list_items_required)

        # 4. items_provided (kwatera, checkbox list from inventory_items)
        self.list_items_provided = self._create_item_selector(obj_instance.items_provided)
        self.label_items_provided = QLabel("Przedmioty otrzymane:")
        self.form.addRow(self.label_items_provided, self.list_items_provided)

        # 5. game_over (kwatera)
        self.check_game_over = QCheckBox()
        if obj_instance.game_over is True:
            self.check_game_over.setChecked(True)
        self.label_game_over = QLabel("Koniec Gry:")
        self.form.addRow(self.label_game_over, self.check_game_over)

        # 6. cost_of_travel (portal)
        self.spin_cost_of_travel = QSpinBox()
        self.spin_cost_of_travel.setRange(0, 999999)
        if obj_instance.cost_of_travel is not None:
            self.spin_cost_of_travel.setValue(obj_instance.cost_of_travel)
        else:
            self.spin_cost_of_travel.setValue(10)
        self.label_cost_of_travel = QLabel("Koszt podróży:")
        self.form.addRow(self.label_cost_of_travel, self.spin_cost_of_travel)

        layout.addLayout(self.form)
        
        # Dialog buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._update_field_visibility()

    def _create_item_selector(self, selected_ids: Optional[List[int]]) -> QListWidget:
        list_widget = QListWidget()
        list_widget.setMaximumHeight(90)
        selected_ids_set = set(selected_ids or [])
        
        avail_items = {item.id: item for item in self.inventory_items}
        all_ids = sorted(set(avail_items.keys()) | selected_ids_set)
        
        if not all_ids:
            placeholder = QListWidgetItem("(Brak zdefiniowanych przedmiotów ekwipunku)")
            placeholder.setFlags(Qt.NoItemFlags)
            list_widget.addItem(placeholder)
            return list_widget

        for item_id in all_ids:
            if item_id in avail_items:
                item = avail_items[item_id]
                label = f"#{item.id}: {item.description} (char: {item.charset_position})"
            else:
                label = f"#{item_id}: (Niezdefiniowany przedmiot)"
                
            widget_item = QListWidgetItem(label)
            widget_item.setFlags(widget_item.flags() | Qt.ItemIsUserCheckable)
            widget_item.setCheckState(Qt.Checked if item_id in selected_ids_set else Qt.Unchecked)
            widget_item.setData(Qt.UserRole, item_id)
            list_widget.addItem(widget_item)
            
        return list_widget

    def _get_selected_item_ids(self, list_widget: QListWidget) -> Optional[List[int]]:
        result = []
        for i in range(list_widget.count()):
            widget_item = list_widget.item(i)
            if widget_item.checkState() == Qt.Checked:
                item_id = widget_item.data(Qt.UserRole)
                if item_id is not None:
                    result.append(item_id)
        return result if result else None

    def _on_type_changed(self, text):
        self._update_field_visibility()

    def _update_field_visibility(self):
        obj_type = self.combo_type.currentText()
        if obj_type == self.TYPE_KWATERA:
            self.label_items_provided.show()
            self.list_items_provided.show()
            self.label_game_over.show()
            self.check_game_over.show()
            self.label_cost_of_travel.hide()
            self.spin_cost_of_travel.hide()
        elif obj_type == self.TYPE_PORTAL:
            self.label_items_provided.hide()
            self.list_items_provided.hide()
            self.label_game_over.hide()
            self.check_game_over.hide()
            self.label_cost_of_travel.show()
            self.spin_cost_of_travel.show()

    def _on_accept(self):
        obj_type = self.combo_type.currentText()

        cond_met = self.edit_conditions_met.text().strip()
        if not cond_met:
            QMessageBox.warning(self, "Błąd walidacji", "Pole 'Wymagania spełnione' jest wymagane.")
            self.edit_conditions_met.setFocus()
            return

        cond_unmet = self.edit_conditions_unmet.text().strip()
        if not cond_unmet:
            QMessageBox.warning(self, "Błąd walidacji", "Pole 'Wymagania niespełnione' jest wymagane.")
            self.edit_conditions_unmet.setFocus()
            return

        items_req = self._get_selected_item_ids(self.list_items_required)

        if obj_type == self.TYPE_KWATERA:
            items_prov = self._get_selected_item_ids(self.list_items_provided)
            self.obj_instance.type = self.TYPE_KWATERA
            self.obj_instance.conditions_met = cond_met
            self.obj_instance.conditions_unmet = cond_unmet
            self.obj_instance.items_required = items_req
            self.obj_instance.items_provided = items_prov
            self.obj_instance.game_over = self.check_game_over.isChecked()
            self.obj_instance.cost_of_travel = None

        elif obj_type == self.TYPE_PORTAL:
            cost = self.spin_cost_of_travel.value()
            self.obj_instance.type = self.TYPE_PORTAL
            self.obj_instance.conditions_met = cond_met
            self.obj_instance.conditions_unmet = cond_unmet
            self.obj_instance.items_required = items_req
            self.obj_instance.items_provided = None
            self.obj_instance.game_over = None
            self.obj_instance.cost_of_travel = cost

        self.accept()
