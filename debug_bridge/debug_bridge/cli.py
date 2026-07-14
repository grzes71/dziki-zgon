import argparse
import sys
import platform
from pathlib import Path

from .config import DebugBridgeConfig
from .errors import DebugBridgeError, ExitCode, UnsupportedPlatformError
from .main import run_bridge
from .breakpoint import run_breakpoint_mode


def main_cli():
    parser = argparse.ArgumentParser(description="Debug Bridge for Altirra")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. run command (legacy snapshot alias)
    run_parser = subparsers.add_parser("run", help="Run snapshot mode (legacy alias)")
    run_parser.add_argument("--config", required=True, help="Path to debug.yaml")
    run_parser.add_argument("--xex", help="Override path to XEX")
    run_parser.add_argument("--lab", help="Override path to LAB file")
    run_parser.add_argument("--out", help="Override output directory")
    run_parser.add_argument("--wait-frame", type=int, help="Override wait frame")
    run_parser.add_argument("--wait-timeout", type=float, help="Override wait timeout in seconds")

    # 2. snapshot command (new official name)
    snapshot_parser = subparsers.add_parser("snapshot", help="Run snapshot mode")
    snapshot_parser.add_argument("--config", required=True, help="Path to debug.yaml")
    snapshot_parser.add_argument("--xex", help="Override path to XEX")
    snapshot_parser.add_argument("--lab", help="Override path to LAB file")
    snapshot_parser.add_argument("--out", help="Override output directory")
    snapshot_parser.add_argument("--wait-frame", type=int, help="Override wait frame")
    snapshot_parser.add_argument("--wait-timeout", type=float, help="Override wait timeout in seconds")

    # 3. break command (breakpoint mode)
    break_parser = subparsers.add_parser("break", help="Run breakpoint mode")
    break_parser.add_argument("--xex", required=True, help="Path to compiled .xex or .atr file")
    
    bp_group = break_parser.add_mutually_exclusive_group(required=True)
    bp_group.add_argument("--bp", help="Software breakpoint: hex address (e.g. $4000) or label name")
    bp_group.add_argument("--bx", help="Hardware breakpoint: Altirra expression")
    bp_group.add_argument("--trap-wsync", action="store_true", help="Hardware breakpoint on WSYNC ($D40A) write")
    bp_group.add_argument("--trap-dli", action="store_true", help="Hardware breakpoint on DLI")
    bp_group.add_argument("--trap-vbi", action="store_true", help="Hardware breakpoint on VBI")

    break_parser.add_argument("--hw-regs", action="store_true", help="Dump hardware registers")
    break_parser.add_argument("--disasm", type=int, default=0, help="Disassemble N instructions")
    break_parser.add_argument("--mem-dump", action="append", default=[], help="Memory dump range(s). Format: $ADDR:L$LEN")
    break_parser.add_argument("--altirra", help="Path to Altirra64.exe")
    break_parser.add_argument("--timeout", type=int, default=15, help="Wall-clock timeout in seconds")
    break_parser.add_argument("--lab", help="Path to MADS .lab labels file")
    break_parser.add_argument("--output-json", help="Write JSON result to file in addition to stdout")
    break_parser.add_argument("--verbose", action="store_true", help="Print progress messages to stderr")
    break_parser.add_argument("--warp", action="store_true", help="Runs the emulator without frame limits (/warp)")

    args = parser.parse_args()

    # Platform check
    if platform.system() != "Windows":
        if args.command == "break":
            # breakpoint mode prints standard error and exits with 9
            print(f"Error: Unsupported platform: This tool requires Windows.", file=sys.stderr)
            sys.exit(ExitCode.UNSUPPORTED_PLATFORM)
        else:
            print(f"Error: Altirra runs only on Windows.", file=sys.stderr)
            sys.exit(ExitCode.UNSUPPORTED_PLATFORM)

    try:
        if args.command in ("run", "snapshot"):
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

        elif args.command == "break":
            json_obj = run_breakpoint_mode(args)
            import json
            print(json.dumps(json_obj, indent=4))
            sys.exit(ExitCode.SUCCESS)


    except DebugBridgeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main_cli()
