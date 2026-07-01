class SmokeTestError(Exception):
    """Base exception for all smoke test errors."""
    
    @property
    def exit_code(self) -> int:
        return 6  # Default internal error code

class InvalidCommandLineError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 1

class EmulatorNotFoundError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 2

class XexNotFoundError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 3

class EmulatorLaunchError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 4

class EmulatorCrashedError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 5

class InternalError(SmokeTestError):
    @property
    def exit_code(self) -> int:
        return 6
