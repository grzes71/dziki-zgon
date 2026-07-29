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


def test_text_line_length_validation():
    """Verifies that all gameover and title text files in texts/ have lines of exactly 40 characters."""
    texts_dir = Path(__file__).parent.parent / "texts"
    target_files = list(texts_dir.glob("gameover*.txt")) + [texts_dir / "title.txt"]
    assert len(target_files) >= 3, "Expected at least 3 text files (gameover* and title.txt)"

    for file_path in target_files:
        assert file_path.exists(), f"Text file {file_path.name} does not exist"
        content = file_path.read_text(encoding="utf-8")
        lines = [l.rstrip("\r\n") for l in content.splitlines() if l.rstrip("\r\n")]
        assert len(lines) > 0, f"File {file_path.name} is empty"

        for line_idx, line in enumerate(lines, 1):
            assert len(line) == 40, (
                f"File {file_path.name} line {line_idx} has length {len(line)}, expected 40 characters: '{line}'"
            )


