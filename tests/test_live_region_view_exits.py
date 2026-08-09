import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QImage
from world_studio.models import ScreenExits
from world_studio.widgets.live_region_view import LiveRegionViewWidget

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_draw_exit_arrows(qapp):
    widget = LiveRegionViewWidget()
    img = QImage(300, 200, QImage.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)

    # Test empty exits (should not draw arrows or throw error)
    exits_none = ScreenExits()
    widget._draw_exit_arrows(painter, 10, 10, 160, 96, exits_none)

    # Test exits with all directions set
    exits_all = ScreenExits(north="SCREEN_N", south="SCREEN_S", east="SCREEN_E", west="SCREEN_W")
    widget._draw_exit_arrows(painter, 10, 10, 160, 96, exits_all)

    # Test exits with partial directions set
    exits_partial = ScreenExits(north="SCREEN_N", east="null")
    widget._draw_exit_arrows(painter, 10, 10, 160, 96, exits_partial)

    painter.end()
