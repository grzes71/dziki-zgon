import sys
import pytest
from unittest.mock import patch, MagicMock
from debug_bridge.cli import main_cli
from debug_bridge.errors import ExitCode

@patch("debug_bridge.cli.run_bridge")
@patch("debug_bridge.cli.DebugBridgeConfig")
@patch("platform.system", return_value="Windows")
def test_cli_run_command(mock_platform, mock_config, mock_run_bridge):
    mock_config_instance = MagicMock()
    mock_config.from_yaml.return_value = mock_config_instance

    test_args = ["debug-bridge", "run", "--config", "debug.yaml"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main_cli()
        assert excinfo.value.code == ExitCode.SUCCESS
        
    mock_config.from_yaml.assert_called_once_with("debug.yaml")
    mock_run_bridge.assert_called_once_with(mock_config_instance)

@patch("debug_bridge.cli.run_breakpoint_mode")
@patch("platform.system", return_value="Windows")
def test_cli_break_command(mock_platform, mock_run_breakpoint):
    mock_run_breakpoint.return_value = {"status": "ok"}

    test_args = ["debug-bridge", "break", "--xex", "game.xex", "--bp", "START"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main_cli()
        assert excinfo.value.code == ExitCode.SUCCESS
        
    mock_run_breakpoint.assert_called_once()
    # Check that bp argument was passed
    args, _ = mock_run_breakpoint.call_args
    assert args[0].bp == "START"
    assert args[0].xex == "game.xex"

@patch("platform.system", return_value="Linux")
def test_cli_unsupported_platform(mock_platform):
    test_args = ["debug-bridge", "run", "--config", "debug.yaml"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main_cli()
        assert excinfo.value.code == ExitCode.UNSUPPORTED_PLATFORM
