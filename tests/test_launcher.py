import pytest
from unittest.mock import Mock, patch
import subprocess
from pathlib import Path

from atari_smoke_test.launcher import SmokeTestLauncher
from atari_smoke_test.exceptions import EmulatorLaunchError, EmulatorCrashedError

@pytest.fixture
def mock_validation():
    with patch("atari_smoke_test.launcher.validate_emulator_path") as mock_emu_val, \
         patch("atari_smoke_test.launcher.validate_xex_path") as mock_xex_val:
        mock_emu_val.return_value = Path("mock_altirra.exe")
        mock_xex_val.return_value = Path("mock_game.xex")
        yield

@pytest.fixture
def mock_subprocess():
    with patch("atari_smoke_test.process.subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_popen.return_value = mock_process
        yield mock_process

def test_launcher_success(mock_validation, mock_subprocess):
    # Simulate a process that stays alive until timeout (wait raises TimeoutExpired)
    mock_subprocess.wait.side_effect = [subprocess.TimeoutExpired(cmd="altirra", timeout=5.0), None]
    mock_subprocess.poll.return_value = None  # Still running when terminate is called

    launcher = SmokeTestLauncher()
    # Should not raise any exception
    launcher.run("mock_altirra.exe", "mock_game.xex", timeout=5.0)

    mock_subprocess.terminate.assert_called_once()
    assert mock_subprocess.kill.call_count == 0

def test_launcher_emulator_crash(mock_validation, mock_subprocess):
    # Simulate a process that exits early with an error code
    mock_subprocess.wait.return_value = 1

    launcher = SmokeTestLauncher()
    with pytest.raises(EmulatorCrashedError) as exc_info:
        launcher.run("mock_altirra.exe", "mock_game.xex", timeout=5.0)

    assert exc_info.value.exit_code == 5
    # Terminate should not be called on the process if it already exited
    mock_subprocess.terminate.assert_not_called()

def test_launcher_kill_fallback(mock_validation, mock_subprocess):
    # Simulate a process that stays alive until timeout
    def wait_side_effect(*args, **kwargs):
        if kwargs.get('timeout') == 5.0:
            raise subprocess.TimeoutExpired(cmd="altirra", timeout=5.0)
        elif kwargs.get('timeout') == 2.0:
            # Simulate refusing to terminate
            raise subprocess.TimeoutExpired(cmd="altirra", timeout=2.0)
        return None
        
    mock_subprocess.wait.side_effect = wait_side_effect
    mock_subprocess.poll.return_value = None

    launcher = SmokeTestLauncher()
    launcher.run("mock_altirra.exe", "mock_game.xex", timeout=5.0)

    mock_subprocess.terminate.assert_called_once()
    mock_subprocess.kill.assert_called_once()
