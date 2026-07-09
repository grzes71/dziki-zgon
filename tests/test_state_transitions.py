import subprocess
from pathlib import Path

import pytest
from py65.devices.mpu6502 import MPU


ROOT_DIR = Path(__file__).parent.parent
MADS_EXE = "c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe"


def build_main_binary() -> tuple[Path, Path]:
    """Builds the full game binary and label table for transition tests."""
    xex_path = ROOT_DIR / "dziki_zgon.xex"
    lab_path = ROOT_DIR / "gen" / "game.lab"

    subprocess.run(
        [
            MADS_EXE,
            "main.asm",
            f"-o:{xex_path}",
            f"-t:{lab_path}",
        ],
        cwd=ROOT_DIR,
        check=True,
    )

    return xex_path, lab_path


def load_xex(filename: Path, memory) -> None:
    data = filename.read_bytes()

    i = 0
    while i < len(data):
        if data[i] == 0xFF and data[i + 1] == 0xFF:
            i += 2
            if i >= len(data):
                break

        if i + 3 >= len(data):
            break

        start = data[i] | (data[i + 1] << 8)
        i += 2
        end = data[i] | (data[i + 1] << 8)
        i += 2

        length = end - start + 1
        if i + length > len(data):
            break

        chunk = data[i : i + length]
        for j, byte in enumerate(chunk):
            memory[start + j] = byte

        i += length


def load_labels(lab_file: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line in lab_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                addr = int(parts[1], 16)
                name = parts[2]
                labels[name.upper()] = addr
            except ValueError:
                continue

    return labels


def run_subroutine(cpu: MPU, sub_addr: int, stub_addr: int = 0x0600, max_steps: int = 20000) -> None:
    """Executes JSR sub_addr; BRK and stops when subroutine returns to the stub."""
    mem = cpu.memory

    mem[stub_addr] = 0x20  # JSR abs
    mem[stub_addr + 1] = sub_addr & 0xFF
    mem[stub_addr + 2] = (sub_addr >> 8) & 0xFF
    mem[stub_addr + 3] = 0x00  # BRK

    cpu.sp = 0xFF
    cpu.pc = stub_addr

    for _ in range(max_steps):
        if cpu.pc == stub_addr + 3:
            return
        cpu.step()

    raise AssertionError(f"Subroutine at ${sub_addr:04X} did not return within {max_steps} steps")


@pytest.fixture(scope="module")
def game_binary() -> tuple[Path, dict[str, int]]:
    xex_path, lab_path = build_main_binary()
    labels = load_labels(lab_path)
    return xex_path, labels


def test_title_story_game_transition_flow(game_binary) -> None:
    """Verifies required FIRE sequence triggers title -> story -> game transition."""
    xex_file, labels = game_binary

    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    mem = cpu.memory

    game_state = labels["GAME_STATE"]
    trig0 = labels["TRIG0"]

    state_title = labels["STATE_TITLE"]
    state_story = labels["STATE_STORY"]
    state_game = labels["STATE_GAME"]

    mem[game_state] = state_title
    mem[labels["TITLE_FIRE_RELEASED"]] = 0
    mem[labels["FIRE_RELEASED_FLAG"]] = 0

    # TITLE: release FIRE first (still TITLE)
    mem[trig0] = 1
    run_subroutine(cpu, labels["TITLE_RUN"])
    assert mem[game_state] == state_title

    # TITLE: press FIRE (go to STORY)
    mem[trig0] = 0
    run_subroutine(cpu, labels["TITLE_RUN"])
    assert mem[game_state] == state_story

    # STORY: release FIRE first (still STORY)
    mem[trig0] = 1
    run_subroutine(cpu, labels["STORY_RUN"])
    assert mem[game_state] == state_story

    # STORY: press FIRE (go to GAME)
    mem[trig0] = 0
    run_subroutine(cpu, labels["STORY_RUN"])
    assert mem[game_state] == state_game


def test_story_does_not_advance_without_second_fire_press(game_binary) -> None:
    """Verifies STORY stays active when FIRE is only released but not pressed again."""
    xex_file, labels = game_binary

    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    mem = cpu.memory

    game_state = labels["GAME_STATE"]
    trig0 = labels["TRIG0"]

    state_story = labels["STATE_STORY"]
    state_game = labels["STATE_GAME"]

    # We start directly in STORY and clear story input latch.
    mem[game_state] = state_story
    mem[labels["FIRE_RELEASED_FLAG"]] = 0

    # 1) Release FIRE once.
    mem[trig0] = 1
    run_subroutine(cpu, labels["STORY_RUN"])
    assert mem[game_state] == state_story

    # 2) Keep FIRE released for multiple frames (still no press).
    for _ in range(5):
        mem[trig0] = 1
        run_subroutine(cpu, labels["STORY_RUN"])
        assert mem[game_state] == state_story

    assert mem[game_state] != state_game


def test_story_does_not_advance_when_fire_is_held(game_binary) -> None:
    """Verifies STORY does not advance when FIRE remains pressed from previous screen."""
    xex_file, labels = game_binary

    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    mem = cpu.memory

    game_state = labels["GAME_STATE"]
    trig0 = labels["TRIG0"]

    state_story = labels["STATE_STORY"]
    state_game = labels["STATE_GAME"]

    # Start directly in STORY with latch cleared.
    mem[game_state] = state_story
    mem[labels["FIRE_RELEASED_FLAG"]] = 0

    # FIRE held down for many frames (TRIG0=0) should not advance.
    for _ in range(6):
        mem[trig0] = 0
        run_subroutine(cpu, labels["STORY_RUN"])
        assert mem[game_state] == state_story

    assert mem[game_state] != state_game
