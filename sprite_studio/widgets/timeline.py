from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                               QPushButton, QHBoxLayout, QAbstractItemView)
from PySide6.QtCore import Signal, Qt

class TimelineWidget(QWidget):
    frame_selected = Signal(int)
    add_requested = Signal()
    delete_requested = Signal(int)
    duplicate_requested = Signal(int)
    insert_requested = Signal(int)
    reorder_requested = Signal(int, int) # from_idx, to_idx
    mirror_requested = Signal(int)
    shift_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # We can use a horizontal list widget for frames
        self.list_widget = QListWidget()
        self.list_widget.setFlow(QListWidget.LeftToRight)
        self.list_widget.setWrapping(False)
        self.list_widget.setFixedHeight(80)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        
        self.list_widget.currentRowChanged.connect(self.frame_selected.emit)
        
        # Override dropEvent to intercept reordering
        self._original_dropEvent = self.list_widget.dropEvent
        self.list_widget.dropEvent = self._custom_dropEvent
        
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_requested.emit)
        
        self.btn_ins = QPushButton("Insert")
        self.btn_ins.clicked.connect(self._on_insert)
        
        self.btn_dup = QPushButton("Dup")
        self.btn_dup.clicked.connect(self._on_dup)
        
        self.btn_del = QPushButton("Del")
        self.btn_del.clicked.connect(self._on_del)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_ins)
        btn_layout.addWidget(self.btn_dup)
        btn_layout.addWidget(self.btn_del)
        layout.addLayout(btn_layout)
        
        transform_layout = QHBoxLayout()
        self.btn_mirror = QPushButton("Mirror")
        self.btn_mirror.clicked.connect(self._on_mirror)
        
        self.btn_sl = QPushButton("Shift L")
        self.btn_sl.clicked.connect(lambda: self._on_shift("left"))
        self.btn_sr = QPushButton("Shift R")
        self.btn_sr.clicked.connect(lambda: self._on_shift("right"))
        self.btn_su = QPushButton("Shift U")
        self.btn_su.clicked.connect(lambda: self._on_shift("up"))
        self.btn_sd = QPushButton("Shift Down")
        self.btn_sd.clicked.connect(lambda: self._on_shift("down"))
        
        transform_layout.addWidget(self.btn_mirror)
        transform_layout.addWidget(self.btn_sl)
        transform_layout.addWidget(self.btn_sr)
        transform_layout.addWidget(self.btn_su)
        transform_layout.addWidget(self.btn_sd)
        layout.addLayout(transform_layout)

    def _custom_dropEvent(self, event):
        source_row = self.list_widget.currentRow()
        self._original_dropEvent(event)
        target_row = self.list_widget.currentRow()
        if source_row != target_row and source_row >= 0 and target_row >= 0:
            self.reorder_requested.emit(source_row, target_row)

    def set_frames(self, frame_count, active_idx):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        for i in range(frame_count):
            item = QListWidgetItem(f"Frame {i}")
            self.list_widget.addItem(item)
            
        if 0 <= active_idx < frame_count:
            self.list_widget.setCurrentRow(active_idx)
            
        self.list_widget.blockSignals(False)

    def _on_insert(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.insert_requested.emit(idx)
            
    def _on_dup(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.duplicate_requested.emit(idx)
            
    def _on_del(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.delete_requested.emit(idx)
            
    def _on_mirror(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.mirror_requested.emit(idx)

    def _on_shift(self, direction):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            # We don't pass idx here, we assume active frame is shifted. But let's pass direction.
            # Actually, main.py knows current frame, but let's be safe.
            # The signal signature is Signal(str)
            self.shift_requested.emit(direction)
