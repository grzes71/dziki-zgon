from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from typing import Optional, List
from world_studio.models import ObjectInstance

class InteractiveObjectPropertiesDialog(QDialog):
    TYPE_KWATERA = "kwatera"
    TYPE_PORTAL = "portal"

    def __init__(self, obj_instance: ObjectInstance, parent=None):
        super().__init__(parent)
        self.obj_instance = obj_instance
        
        self.setWindowTitle(f"Interactive Object Properties - {obj_instance.object}")
        self.resize(450, 300)
        
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

        # 3. items_required
        self.edit_items_required = QLineEdit()
        if obj_instance.items_required:
            self.edit_items_required.setText(", ".join(str(i) for i in obj_instance.items_required))
        self.edit_items_required.setPlaceholderText("np. 1, 2, 5 (opcjonalne)")
        self.form.addRow("Przedmioty wymagane:", self.edit_items_required)

        # 4. items_provided (kwatera)
        self.edit_items_provided = QLineEdit()
        if obj_instance.items_provided:
            self.edit_items_provided.setText(", ".join(str(i) for i in obj_instance.items_provided))
        self.edit_items_provided.setPlaceholderText("np. 3, 4 (opcjonalne)")
        self.label_items_provided = QLabel("Przedmioty otrzymane:")
        self.form.addRow(self.label_items_provided, self.edit_items_provided)

        # 5. cost_of_travel (portal)
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

    def _on_type_changed(self, text):
        self._update_field_visibility()

    def _update_field_visibility(self):
        obj_type = self.combo_type.currentText()
        if obj_type == self.TYPE_KWATERA:
            self.label_items_provided.show()
            self.edit_items_provided.show()
            self.label_cost_of_travel.hide()
            self.spin_cost_of_travel.hide()
        elif obj_type == self.TYPE_PORTAL:
            self.label_items_provided.hide()
            self.edit_items_provided.hide()
            self.label_cost_of_travel.show()
            self.spin_cost_of_travel.show()

    def _parse_int_list(self, text: str) -> Optional[List[int]]:
        text = text.strip()
        if not text:
            return None
        parts = [p.strip() for p in text.split(",") if p.strip()]
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                raise ValueError(f"Wartość '{p}' nie jest liczbą całkowitą.")
        return result if result else None

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

        try:
            items_req = self._parse_int_list(self.edit_items_required.text())
        except ValueError as e:
            QMessageBox.warning(self, "Błąd walidacji", f"Błąd w polu 'Przedmioty wymagane': {e}")
            self.edit_items_required.setFocus()
            return

        if obj_type == self.TYPE_KWATERA:
            try:
                items_prov = self._parse_int_list(self.edit_items_provided.text())
            except ValueError as e:
                QMessageBox.warning(self, "Błąd walidacji", f"Błąd w polu 'Przedmioty otrzymane': {e}")
                self.edit_items_provided.setFocus()
                return

            self.obj_instance.type = self.TYPE_KWATERA
            self.obj_instance.conditions_met = cond_met
            self.obj_instance.conditions_unmet = cond_unmet
            self.obj_instance.items_required = items_req
            self.obj_instance.items_provided = items_prov
            self.obj_instance.cost_of_travel = None

        elif obj_type == self.TYPE_PORTAL:
            cost = self.spin_cost_of_travel.value()
            self.obj_instance.type = self.TYPE_PORTAL
            self.obj_instance.conditions_met = cond_met
            self.obj_instance.conditions_unmet = cond_unmet
            self.obj_instance.items_required = items_req
            self.obj_instance.items_provided = None
            self.obj_instance.cost_of_travel = cost

        self.accept()
