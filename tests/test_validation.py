import pytest
from pathlib import Path
from atari_smoke_test.validation import validate_emulator_path, validate_xex_path
from atari_smoke_test.exceptions import EmulatorNotFoundError, XexNotFoundError

def test_validate_emulator_path_success(tmp_path):
    mock_emulator = tmp_path / "Altirra64.exe"
    mock_emulator.touch()
    
    result = validate_emulator_path(mock_emulator)
    assert result == mock_emulator

def test_validate_emulator_path_missing(tmp_path):
    missing_emulator = tmp_path / "Missing.exe"
    
    with pytest.raises(EmulatorNotFoundError) as exc_info:
        validate_emulator_path(missing_emulator)
    
    assert "Altirra executable not found" in str(exc_info.value)
    assert exc_info.value.exit_code == 2

def test_validate_xex_path_success(tmp_path):
    mock_xex = tmp_path / "game.xex"
    mock_xex.touch()
    
    result = validate_xex_path(mock_xex)
    assert result == mock_xex

def test_validate_xex_path_missing(tmp_path):
    missing_xex = tmp_path / "missing.xex"
    
    with pytest.raises(XexNotFoundError) as exc_info:
        validate_xex_path(missing_xex)
    
    assert "XEX file not found" in str(exc_info.value)
    assert exc_info.value.exit_code == 3
