"""
Exit Codes mapping and custom exceptions.
"""

from enum import IntEnum

class ExitCode(IntEnum):
    SUCCESS = 0
    CONFIG_ERROR = 2
    MISSING_INPUT = 3
    LAUNCH_ERROR = 4
    AUTOMATION_ERROR = 5
    SYMBOL_ERROR = 6
    CAPTURE_ERROR = 7
    EXPORT_ERROR = 8
    UNSUPPORTED_PLATFORM = 9

class DebugBridgeError(Exception):
    def __init__(self, message: str, exit_code: ExitCode):
        super().__init__(message)
        self.exit_code = exit_code

class ConfigError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.CONFIG_ERROR)

class MissingInputError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.MISSING_INPUT)

class EmulatorLaunchError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.LAUNCH_ERROR)

class AutomationError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.AUTOMATION_ERROR)

class SymbolError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.SYMBOL_ERROR)

class CaptureError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.CAPTURE_ERROR)

class ExportError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.EXPORT_ERROR)

class UnsupportedPlatformError(DebugBridgeError):
    def __init__(self, message: str):
        super().__init__(message, ExitCode.UNSUPPORTED_PLATFORM)
