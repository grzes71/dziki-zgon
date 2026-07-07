from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtCore import Qt
from world_studio.widgets.render_utils import render_screen
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset

class PreviewDialog(QDialog):
    def __init__(self, region_id: str, start_screen_id: str, project: ProjectManager, charset: Charset, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview - {region_id}")
        self.project = project
        self.charset = charset
        self.region_id = region_id
        self.current_screen_id = start_screen_id
        
        self.setStyleSheet("background-color: black;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        
        screen_def = self.project.screens.get(self.region_id, {}).get(self.current_screen_id)
        if not screen_def:
            return
            
        img = render_screen(screen_def, self.project, self.charset, mark_start_pos=False)
        # We use FastTransformation because Atari graphics look best when scaled linearly (no blurring)
        scaled = img.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.FastTransformation)
        
        # Center image
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        
        # Draw some text
        painter.setPen(Qt.white)
        painter.drawText(10, 20, f"Screen: {self.current_screen_id}")
        painter.drawText(10, 40, "Use Arrows to navigate. ESC to exit.")
        
    def keyPressEvent(self, event):
        screen_def = self.project.screens.get(self.region_id, {}).get(self.current_screen_id)
        if not screen_def:
            super().keyPressEvent(event)
            return
            
        next_screen = None
        if event.key() == Qt.Key_Escape:
            self.accept()
            return
        elif event.key() == Qt.Key_Up:
            next_screen = screen_def.exits.north
        elif event.key() == Qt.Key_Down:
            next_screen = screen_def.exits.south
        elif event.key() == Qt.Key_Left:
            next_screen = screen_def.exits.west
        elif event.key() == Qt.Key_Right:
            next_screen = screen_def.exits.east
            
        if next_screen and next_screen in self.project.screens.get(self.region_id, {}):
            self.current_screen_id = next_screen
            self.update()
        else:
            super().keyPressEvent(event)
