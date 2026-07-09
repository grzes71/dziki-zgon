from dataclasses import dataclass, field
from typing import Optional, List
import yaml
from pathlib import Path
from .errors import ConfigError

@dataclass
class EmulatorConfig:
    executable: str

@dataclass
class GameConfig:
    executable: str

@dataclass
class OutputConfig:
    directory: str

@dataclass
class CaptureConfig:
    screenshot: bool
    state: bool
    memory_dump: bool = False

@dataclass
class WaitConfig:
    mode: str = "frame" # frame | timeout | manual
    frame: Optional[int] = None
    timeout_seconds: Optional[float] = None

@dataclass
class SymbolsConfig:
    file: Optional[str] = None
    include: Optional[List[str]] = None

@dataclass
class DeterministicConfig:
    seed: int = 0
    emulator_speed: str = "realtime" # full | realtime
    disable_random_inputs: bool = True

@dataclass
class DebugBridgeConfig:
    emulator: EmulatorConfig
    game: GameConfig
    output: OutputConfig
    capture: CaptureConfig
    wait: WaitConfig = field(default_factory=WaitConfig)
    symbols: SymbolsConfig = field(default_factory=SymbolsConfig)
    deterministic: DeterministicConfig = field(default_factory=DeterministicConfig)
    scenario: Optional[list] = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DebugBridgeConfig":
        path = Path(path)
        if not path.is_file():
            raise ConfigError(f"Config file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML parsing error: {e}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "DebugBridgeConfig":
        try:
            emulator_data = data.get("emulator", {})
            game_data = data.get("game", {})
            output_data = data.get("output", {})
            capture_data = data.get("capture", {})
            wait_data = data.get("wait", {})
            symbols_data = data.get("symbols", {})
            deterministic_data = data.get("deterministic", {})

            # Required
            if "executable" not in emulator_data:
                raise ConfigError("Missing required key: emulator.executable")
            if "executable" not in game_data:
                raise ConfigError("Missing required key: game.executable")
            if "directory" not in output_data:
                raise ConfigError("Missing required key: output.directory")
            if "screenshot" not in capture_data:
                raise ConfigError("Missing required key: capture.screenshot")
            if "state" not in capture_data:
                raise ConfigError("Missing required key: capture.state")

            config = cls(
                emulator=EmulatorConfig(executable=emulator_data["executable"]),
                game=GameConfig(executable=game_data["executable"]),
                output=OutputConfig(directory=output_data["directory"]),
                capture=CaptureConfig(
                    screenshot=bool(capture_data["screenshot"]),
                    state=bool(capture_data["state"]),
                    memory_dump=bool(capture_data.get("memory_dump", False)),
                ),
                wait=WaitConfig(
                    mode=wait_data.get("mode", "frame"),
                    frame=wait_data.get("frame"),
                    timeout_seconds=wait_data.get("timeout_seconds"),
                ),
                symbols=SymbolsConfig(
                    file=symbols_data.get("file"),
                    include=symbols_data.get("include"),
                ),
                deterministic=DeterministicConfig(
                    seed=deterministic_data.get("seed", 0),
                    emulator_speed=deterministic_data.get("emulator_speed", "realtime"),
                    disable_random_inputs=deterministic_data.get("disable_random_inputs", True),
                ),
                scenario=data.get("scenario")
            )

            config.validate()
            return config
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid configuration structure: {e}")

    def validate(self):
        if self.wait.mode not in ("frame", "timeout", "manual"):
            raise ConfigError(f"Invalid wait mode: {self.wait.mode}")
            
        if self.wait.mode == "frame" and (self.wait.frame is None or self.wait.frame <= 0):
            raise ConfigError("wait.frame must be > 0 when wait.mode is frame")
            
        if self.wait.mode == "timeout" and (self.wait.timeout_seconds is None or self.wait.timeout_seconds <= 0):
            raise ConfigError("wait.timeout_seconds must be > 0 when wait.mode is timeout")

        if self.symbols.include is not None and self.symbols.file is None:
            raise ConfigError("symbols.file must be provided if symbols.include is provided")

        if self.scenario is not None and self.wait.mode is not None:
            # Wait mode is default 'frame', so we just check if scenario is used
            # For MVP, scenario is not fully supported, but we validate the rule.
            if "wait" in self.__dict__ and self.scenario:
                 pass # For now, allow default wait mode if scenario is provided, but in strict scenario mode wait is ignored
