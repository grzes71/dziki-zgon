import pytest
from debug_bridge.config import DebugBridgeConfig
from debug_bridge.errors import ConfigError

def test_valid_config():
    data = {
        "emulator": {"executable": "altirra.exe"},
        "game": {"executable": "game.xex"},
        "output": {"directory": "out"},
        "capture": {"screenshot": True, "state": True},
        "wait": {"mode": "frame", "frame": 100}
    }
    config = DebugBridgeConfig.from_dict(data)
    assert config.emulator.executable == "altirra.exe"
    assert config.wait.mode == "frame"
    assert config.wait.frame == 100

def test_missing_required_key():
    data = {
        "game": {"executable": "game.xex"},
        "output": {"directory": "out"},
        "capture": {"screenshot": True, "state": True}
    }
    with pytest.raises(ConfigError, match="Missing required key: emulator.executable"):
        DebugBridgeConfig.from_dict(data)

def test_invalid_wait_mode():
    data = {
        "emulator": {"executable": "altirra.exe"},
        "game": {"executable": "game.xex"},
        "output": {"directory": "out"},
        "capture": {"screenshot": True, "state": True},
        "wait": {"mode": "unknown"}
    }
    with pytest.raises(ConfigError, match="Invalid wait mode: unknown"):
        DebugBridgeConfig.from_dict(data)
