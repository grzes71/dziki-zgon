"""
CLI entry point.
"""

import argparse
import sys
from pathlib import Path

from .config import DebugBridgeConfig
from .errors import DebugBridgeError, ExitCode
from .main import run_bridge

def main_cli():
    parser = argparse.ArgumentParser(description="Debug Bridge for Altirra")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("--config", required=True, help="Path to debug.yaml")
    parser.add_argument("--xex", help="Override path to XEX")
    parser.add_argument("--lab", help="Override path to LAB file")
    parser.add_argument("--out", help="Override output directory")
    parser.add_argument("--wait-frame", type=int, help="Override wait frame")
    parser.add_argument("--wait-timeout", type=float, help="Override wait timeout in seconds")

    args = parser.parse_args()

    try:
        # 1. validate config
        config = DebugBridgeConfig.from_yaml(args.config)
        
        # apply overrides
        if args.xex:
            config.game.executable = args.xex
        if args.lab:
            config.symbols.file = args.lab
        if args.out:
            config.output.directory = args.out
        if args.wait_frame is not None:
            config.wait.mode = "frame"
            config.wait.frame = args.wait_frame
        if args.wait_timeout is not None:
            config.wait.mode = "timeout"
            config.wait.timeout_seconds = args.wait_timeout
            
        config.validate()

        run_bridge(config)
        sys.exit(ExitCode.SUCCESS)

    except DebugBridgeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main_cli()
