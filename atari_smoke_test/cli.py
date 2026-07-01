import argparse
import logging
import sys

from .exceptions import SmokeTestError, InvalidCommandLineError, InternalError
from .launcher import SmokeTestLauncher

def setup_logging() -> None:
    # Set up simple logging without timestamps for the clean CLI output requested
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated smoke testing for Atari 8-bit games using Altirra."
    )
    parser.add_argument(
        "--emulator",
        type=str,
        default=r"C:\Apps\Altirra-4.40\Altirra64.exe",
        help="Path to the Altirra emulator executable."
    )
    parser.add_argument(
        "--xex",
        type=str,
        required=True,
        help="Path to the Atari executable (.xex) to test."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds to wait for the emulator before declaring success."
    )
    parser.add_argument(
        "--screenshot",
        type=str,
        default=None,
        help="Path to save a screenshot of the desktop before termination."
    )
    
    try:
        return parser.parse_args(args)
    except SystemExit as e:
        # argparse calls sys.exit() on error or help.
        # We catch it to map invalid command line usage to exit code 1
        if e.code != 0:
            raise InvalidCommandLineError("Invalid command line arguments.") from e
        raise

def main(args: list[str] | None = None) -> int:
    setup_logging()
    
    try:
        parsed_args = parse_args(args)
        launcher = SmokeTestLauncher()
        launcher.run(
            emulator_path=parsed_args.emulator,
            xex_path=parsed_args.xex,
            timeout=parsed_args.timeout,
            screenshot_path=parsed_args.screenshot
        )
        return 0
    except SmokeTestError as e:
        print(f"\nERROR:\n{e}\n", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        print(f"\nERROR:\nUnexpected internal error: {e}\n", file=sys.stderr)
        return InternalError().exit_code
