from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image
from PySide6.QtCore import Qt, Signal, QRect, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QSlider,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QGroupBox,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QCheckBox,
)

from sprite_studio.models import Frame
from sprite_studio.palette import get_atari_rgb, mix_atari_colors
from sprite_studio.image_import import (
    load_image,
    slice_image,
    compute_slice_ranges,
    detect_image_color_mode,
    convert_frame_to_pixels,
    ImageImportError,
)


def pil_to_qimage(pil_img: Image.Image) -> QImage:
    rgba = pil_img.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888)
    return qimg.copy()


class SourceImageCanvas(QWidget):
    """
    Renders the loaded source image with aspect ratio preserved,
    overlaying slice division lines and highlighting the selected frame.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.image: Optional[Image.Image] = None
        self._qimage: Optional[QImage] = None
        self.direction: str = "horizontal"
        self.frame_count: int = 1
        self.selected_index: int = 0
        self.setMinimumSize(220, 200)

    def set_image(self, img: Image.Image):
        self.image = img
        self._qimage = pil_to_qimage(img)
        self.update()

    def set_slicing(self, direction: str, count: int, selected_idx: int):
        self.direction = direction
        self.frame_count = count
        self.selected_index = selected_idx
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(25, 25, 25))

        if not self._qimage or not self.image:
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded")
            return

        w_img = self.image.width
        h_img = self.image.height
        w_avail = self.width() - 20
        h_avail = self.height() - 20

        scale = min(w_avail / w_img, h_avail / h_img)
        draw_w = w_img * scale
        draw_h = h_img * scale
        offset_x = (self.width() - draw_w) / 2.0
        offset_y = (self.height() - draw_h) / 2.0

        target_rect = QRectF(offset_x, offset_y, draw_w, draw_h)
        painter.drawImage(target_rect, self._qimage)

        # Draw frame divisions and selected frame highlight
        try:
            ranges = compute_slice_ranges(w_img if self.direction == "horizontal" else h_img, self.frame_count)
        except Exception:
            return

        for idx, (start, end) in enumerate(ranges):
            if self.direction == "horizontal":
                fx0 = offset_x + start * scale
                fx1 = offset_x + end * scale
                frame_rect = QRectF(fx0, offset_y, fx1 - fx0, draw_h)
            else:
                fy0 = offset_y + start * scale
                fy1 = offset_y + end * scale
                frame_rect = QRectF(offset_x, fy0, draw_w, fy1 - fy0)

            if idx == self.selected_index:
                # Highlight active frame
                painter.fillRect(frame_rect, QColor(0, 160, 255, 60))
                pen_sel = QPen(QColor(0, 180, 255), 2)
                painter.setPen(pen_sel)
                painter.drawRect(frame_rect)

            # Division line
            if idx > 0:
                pen_div = QPen(QColor(255, 60, 60, 200), 1, Qt.DashLine)
                painter.setPen(pen_div)
                if self.direction == "horizontal":
                    painter.drawLine(QPointF(fx0, offset_y), QPointF(fx0, offset_y + draw_h))
                else:
                    painter.drawLine(QPointF(offset_x, fy0), QPointF(offset_x + draw_w, fy0))


class FramePreviewCanvas(QWidget):
    """
    Renders the converted 8 x H sprite frame with pixel grid and high zoom.
    Supports both 2-color and 4-color display modes.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.frame_pixels: List[str] = []
        self.zoom: int = 14
        self.color_mode: int = 2
        self.color1: int = 0
        self.color2: int = 0
        self.setMinimumSize(8 * self.zoom + 20, 100)

    def set_palette(self, color_mode: int, color1: int, color2: int):
        self.color_mode = color_mode
        self.color1 = color1
        self.color2 = color2
        self.update()

    def set_pixels(self, pixels: List[str]):
        self.frame_pixels = pixels
        h = len(pixels)
        self.setMinimumSize(8 * self.zoom + 20, h * self.zoom + 20)
        self.update()

    def _get_pixel_color(self, char: str) -> QColor:
        if char == "1":
            if self.color1 > 0:
                return get_atari_rgb(self.color1)
            return QColor(80, 140, 255) if self.color_mode == 4 else QColor(255, 255, 255)
        elif char == "2":
            if self.color2 > 0:
                return get_atari_rgb(self.color2)
            return QColor(245, 180, 45)
        elif char == "3":
            if self.color1 > 0 or self.color2 > 0:
                return get_atari_rgb(mix_atari_colors(self.color1, self.color2))
            return QColor(255, 255, 255)
        return QColor(15, 15, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        if not self.frame_pixels:
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No frame")
            return

        h = len(self.frame_pixels)
        grid_w = 8 * self.zoom
        grid_h = h * self.zoom
        offset_x = (self.width() - grid_w) // 2
        offset_y = (self.height() - grid_h) // 2

        grid_pen = QPen(QColor(50, 50, 60), 1)
        painter.setPen(grid_pen)

        for y in range(h):
            row_str = self.frame_pixels[y]
            for x in range(8):
                c = row_str[x] if x < len(row_str) else "0"
                col = self._get_pixel_color(c)
                painter.setBrush(QBrush(col))
                painter.drawRect(offset_x + x * self.zoom, offset_y + y * self.zoom, self.zoom, self.zoom)


# Compatibility alias
BinaryFrameCanvas = FramePreviewCanvas


class ImageImportDialog(QDialog):
    """
    Dialog for configuring image slicing, thresholding, and previewing
    resulting sprite frames before importing (supports 2-color and 4-color modes).
    """

    def __init__(
        self,
        image_path: Path | str,
        target_height: int,
        sprite_color_mode: int = 2,
        color1: int = 0,
        color2: int = 0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Import Raster Image")
        self.resize(780, 620)

        self.image_path = Path(image_path)
        self.target_height = target_height
        self.sprite_color_mode = sprite_color_mode
        self.color1 = color1
        self.color2 = color2

        self.source_image: Image.Image = load_image(self.image_path)
        self.detected_mode, self.detected_desc = detect_image_color_mode(self.source_image)

        self.slices: List[Image.Image] = []
        self.binary_frames: List[Frame] = []
        self.current_frame_idx: int = 0

        self._setup_ui()
        self._recompute_import()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)

        # Upper area: Source preview on left, Converted preview on right
        splitter = QSplitter(Qt.Horizontal)

        # Source box
        source_group = QGroupBox("Source Image & Slice Partition")
        source_layout = QVBoxLayout(source_group)
        self.source_canvas = SourceImageCanvas()
        self.source_canvas.set_image(self.source_image)
        source_layout.addWidget(self.source_canvas)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("color: #aaa; font-size: 11px;")
        source_layout.addWidget(self.lbl_info)
        splitter.addWidget(source_group)

        # Converted frame preview box
        converted_group = QGroupBox("Sprite Frame Preview (8 × H)")
        converted_layout = QVBoxLayout(converted_group)
        self.binary_canvas = FramePreviewCanvas()
        self.binary_canvas.set_palette(self.detected_mode, self.color1, self.color2)
        converted_layout.addWidget(self.binary_canvas, 1)

        # Frame navigation controls
        nav_layout = QHBoxLayout()
        self.btn_prev_frame = QPushButton("◀ Prev")
        self.btn_prev_frame.clicked.connect(self._on_prev_frame)
        self.lbl_frame_info = QLabel("Frame 1 of 1")
        self.lbl_frame_info.setAlignment(Qt.AlignCenter)
        self.btn_next_frame = QPushButton("Next ▶")
        self.btn_next_frame.clicked.connect(self._on_next_frame)
        nav_layout.addWidget(self.btn_prev_frame)
        nav_layout.addWidget(self.lbl_frame_info, 1)
        nav_layout.addWidget(self.btn_next_frame)
        converted_layout.addLayout(nav_layout)

        splitter.addWidget(converted_group)
        splitter.setSizes([450, 320])
        root_layout.addWidget(splitter, 1)

        # Parameters Box
        params_group = QGroupBox("Import & Conversion Parameters")
        params_layout = QVBoxLayout(params_group)

        # Row 1: Direction and Frame Count
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("Slice Direction:"))
        self.combo_dir = QComboBox()
        self.combo_dir.addItem("Horizontal (left to right)", "horizontal")
        self.combo_dir.addItem("Vertical (top to bottom)", "vertical")
        self.combo_dir.currentIndexChanged.connect(self._on_params_changed)
        row1_layout.addWidget(self.combo_dir, 1)

        row1_layout.addWidget(QLabel("Frame Count (N):"))
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, max(1, self.source_image.width))
        self.spin_count.setValue(1)
        self.spin_count.valueChanged.connect(self._on_params_changed)
        row1_layout.addWidget(self.spin_count, 1)
        params_layout.addLayout(row1_layout)

        # Row 2: Color Mode + Detection badge
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("Color Mode:"))
        self.combo_color_mode = QComboBox()
        self.combo_color_mode.addItem("2 colors (1-bit PMG)", 2)
        self.combo_color_mode.addItem("4 colors (2-bit PMG Overlap)", 4)
        
        # Preselect auto-detected mode
        init_idx = 1 if self.detected_mode == 4 else 0
        self.combo_color_mode.setCurrentIndex(init_idx)
        self.combo_color_mode.currentIndexChanged.connect(self._on_color_mode_changed)
        row2_layout.addWidget(self.combo_color_mode, 1)

        self.lbl_detected = QLabel(f"Detected: {self.detected_desc} (auto-selected)")
        self.lbl_detected.setStyleSheet("color: #4da6ff; font-weight: bold; font-size: 11px;")
        row2_layout.addWidget(self.lbl_detected, 2)
        params_layout.addLayout(row2_layout)

        # Row 3: Target Height (H), Auto Height button, Fit Mode
        row3_layout = QHBoxLayout()
        row3_layout.addWidget(QLabel("Target Height (H):"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 255)
        self.spin_height.setValue(self.target_height)
        self.spin_height.valueChanged.connect(self._on_height_changed)
        row3_layout.addWidget(self.spin_height)

        self.btn_auto_height = QPushButton("Auto Height")
        self.btn_auto_height.setToolTip("Set height proportional to slice aspect ratio")
        self.btn_auto_height.clicked.connect(self._on_auto_height)
        row3_layout.addWidget(self.btn_auto_height)

        row3_layout.addWidget(QLabel("Fit Mode:"))
        self.combo_fit = QComboBox()
        self.combo_fit.addItem("Fit (Letterbox / Keep ratio)", "fit")
        self.combo_fit.addItem("Stretch to fill (8 × H)", "stretch")
        self.combo_fit.addItem("Crop to fill (8 × H)", "crop")
        self.combo_fit.currentIndexChanged.connect(self._recompute_binarization)
        row3_layout.addWidget(self.combo_fit, 1)
        params_layout.addLayout(row3_layout)

        # Row 4: Threshold Slider, SpinBox, and Inverse CheckBox
        row4_layout = QHBoxLayout()
        self.lbl_th_name = QLabel("Threshold:")
        row4_layout.addWidget(self.lbl_th_name)
        self.slider_th = QSlider(Qt.Horizontal)
        self.slider_th.setRange(0, 100)
        self.slider_th.setValue(50)
        self.slider_th.valueChanged.connect(self._on_slider_th_changed)
        row4_layout.addWidget(self.slider_th, 2)

        self.spin_th = QSpinBox()
        self.spin_th.setRange(0, 100)
        self.spin_th.setValue(50)
        self.spin_th.setSuffix("%")
        self.spin_th.valueChanged.connect(self._on_spin_th_changed)
        row4_layout.addWidget(self.spin_th, 0)

        self.chk_inverse = QCheckBox("Inverse (Invert colors)")
        self.chk_inverse.toggled.connect(self._recompute_binarization)
        row4_layout.addWidget(self.chk_inverse)
        params_layout.addLayout(row4_layout)

        root_layout.addWidget(params_group)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Import Frames")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)

    def _on_color_mode_changed(self, idx: int):
        mode = self.combo_color_mode.currentData()
        self.binary_canvas.set_palette(mode, self.color1, self.color2)
        if mode == 4:
            self.lbl_th_name.setText("Threshold (4-level):")
            self.lbl_th_name.setToolTip("Sensitivity slider distributing luminance into 4 color levels (0, 1, 2, 3)")
        else:
            self.lbl_th_name.setText("Brightness Threshold:")
            self.lbl_th_name.setToolTip("Luminance cutoff threshold (0 or 1)")
        self._recompute_binarization()

    def _on_height_changed(self, val: int):
        self.target_height = val
        self._recompute_binarization()

    def _get_proportional_height(self) -> int:
        count = max(1, self.spin_count.value())
        direction = self.combo_dir.currentData()
        if direction == "horizontal":
            slice_w = max(1, self.source_image.width // count)
            slice_h = self.source_image.height
        else:
            slice_w = self.source_image.width
            slice_h = max(1, self.source_image.height // count)
        return max(1, min(255, int(round(slice_h * 8.0 / slice_w))))

    def _on_auto_height(self):
        prop_h = self._get_proportional_height()
        self.spin_height.setValue(prop_h)

    def get_target_height(self) -> int:
        return self.target_height

    def get_color_mode(self) -> int:
        return self.combo_color_mode.currentData()

    def _on_params_changed(self):
        direction = self.combo_dir.currentData()
        max_frames = self.source_image.width if direction == "horizontal" else self.source_image.height
        self.spin_count.setMaximum(max(1, max_frames))
        self._recompute_import()

    def _on_slider_th_changed(self, val: int):
        if self.spin_th.value() != val:
            self.spin_th.setValue(val)
        self._recompute_binarization()

    def _on_spin_th_changed(self, val: int):
        if self.slider_th.value() != val:
            self.slider_th.setValue(val)
        self._recompute_binarization()

    def _on_prev_frame(self):
        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self._update_current_frame_preview()

    def _on_next_frame(self):
        if self.current_frame_idx < len(self.binary_frames) - 1:
            self.current_frame_idx += 1
            self._update_current_frame_preview()

    def _recompute_import(self):
        direction = self.combo_dir.currentData()
        count = self.spin_count.value()

        try:
            self.slices = slice_image(self.source_image, count, direction)
        except Exception as e:
            QMessageBox.critical(self, "Slicing Error", str(e))
            return

        prop_h = self._get_proportional_height()
        if hasattr(self, "btn_auto_height"):
            self.btn_auto_height.setText(f"Auto ({prop_h} px)")
            self.btn_auto_height.setToolTip(f"Set proportional height based on slice aspect ratio: {prop_h} px")

        if self.current_frame_idx >= len(self.slices):
            self.current_frame_idx = 0

        self._recompute_binarization()

    def _recompute_binarization(self):
        threshold = float(self.slider_th.value())
        is_inverse = self.chk_inverse.isChecked()
        fit_mode = self.combo_fit.currentData() if hasattr(self, "combo_fit") else "fit"
        direction = self.combo_dir.currentData()
        count = self.spin_count.value()
        color_mode = self.combo_color_mode.currentData()

        frames: List[Frame] = []
        for s_img in self.slices:
            pixels = convert_frame_to_pixels(
                frame_image=s_img,
                target_width=8,
                target_height=self.target_height,
                color_mode=color_mode,
                threshold=threshold,
                inverse=is_inverse,
                fit_mode=fit_mode,
            )
            frames.append(Frame(pixels=pixels))

        self.binary_frames = frames

        if self.current_frame_idx >= len(self.binary_frames):
            self.current_frame_idx = max(0, len(self.binary_frames) - 1)

        mode_str = f"Mode: {color_mode}-color ({'2-bit Overlap' if color_mode == 4 else '1-bit'})"
        inv_str = " | Inverse: On" if is_inverse else ""
        fit_str = f" | Fit: {fit_mode.capitalize()}" if fit_mode else ""
        self.lbl_info.setText(
            f"File: {self.image_path.name} ({self.source_image.width} × {self.source_image.height} px)\n"
            f"{mode_str} | Direction: {direction.capitalize()} | Frames: {count} | Target: 8 × {self.target_height} px{fit_str}{inv_str}"
        )

        self.source_canvas.set_slicing(direction, count, self.current_frame_idx)
        self._update_current_frame_preview()

    def _update_current_frame_preview(self):
        total = len(self.binary_frames)
        if total == 0:
            self.lbl_frame_info.setText("No frames")
            self.binary_canvas.set_pixels([])
            self.btn_prev_frame.setEnabled(False)
            self.btn_next_frame.setEnabled(False)
            return

        self.btn_prev_frame.setEnabled(self.current_frame_idx > 0)
        self.btn_next_frame.setEnabled(self.current_frame_idx < total - 1)
        self.lbl_frame_info.setText(f"Frame {self.current_frame_idx + 1} of {total}")

        self.binary_canvas.set_pixels(self.binary_frames[self.current_frame_idx].pixels)
        direction = self.combo_dir.currentData()
        self.source_canvas.set_slicing(direction, len(self.slices), self.current_frame_idx)

    def get_imported_frames(self) -> List[Frame]:
        return self.binary_frames
