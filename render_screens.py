import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from world_studio.project_manager import ProjectManager
from world_studio.charset import Charset
from world_studio.widgets.render_utils import render_screen

app = QApplication(sys.argv)
pm = ProjectManager()
pm.load_project(Path("world"))
charset = Charset(Path("font.fnt"))

crossroads_def = pm.screens["WHITE_FIELD"]["CROSSROADS"]
img_cross = render_screen(crossroads_def, pm, charset)
img_cross.save("crossroads.png")

church_def = pm.screens["WHITE_FIELD"]["CHURCH"]
img_church = render_screen(church_def, pm, charset)
img_church.save("church.png")

print("Saved crossroads.png and church.png")
