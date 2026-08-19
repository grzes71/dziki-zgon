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


def test_gameover_init_sets_shadow_registers(game_binary) -> None:
    """Verifies that GAMEOVER_INIT sets OS shadow registers (SDLSTL, SDLSTH, SDMCTL, CHBAS) so Engine_FrameHandler renders DLIST_GAMEOVER correctly."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Call GAMEOVER_INIT
    run_subroutine(cpu, labels["GAMEOVER_INIT"], max_steps=100000)

    # Check shadow registers
    dlist_gameover = labels["DLIST_GAMEOVER"]
    dlist_lo = dlist_gameover & 0xFF
    dlist_hi = (dlist_gameover >> 8) & 0xFF

    assert mem[labels["SDLSTL"]] == dlist_lo
    assert mem[labels["SDLSTH"]] == dlist_hi
    assert mem[labels["SDMCTL"]] == 0x22
    assert mem[labels["CHBAS"]] == 0x60


def test_gameover_text_selection_by_result_status(game_binary) -> None:
    """Verifies that GAMEOVER_INIT depacks failure text when status=0 and success text when status=1."""
    xex_file, labels = game_binary

    # 1. Test Failure text (status = 0)
    cpu1 = MPU()
    load_xex(xex_file, cpu1.memory)
    cpu1.memory[labels["GAME_RESULT_STATUS"]] = 0
    run_subroutine(cpu1, labels["GAMEOVER_INIT"], max_steps=100000)
    footer_addr = labels["FOOTER_ADDR"]
    fail_bytes = bytes(cpu1.memory[footer_addr : footer_addr + 40])

    # 2. Test Success text (status = 1)
    cpu2 = MPU()
    load_xex(xex_file, cpu2.memory)
    cpu2.memory[labels["GAME_RESULT_STATUS"]] = 1
    run_subroutine(cpu2, labels["GAMEOVER_INIT"], max_steps=100000)
    success_bytes = bytes(cpu2.memory[footer_addr : footer_addr + 40])

    assert fail_bytes != success_bytes
    assert any(b != 0 for b in fail_bytes)
    assert any(b != 0 for b in success_bytes)


def test_gameover_vbi_static_rendering(game_binary) -> None:
    """Verifies that GAMEOVER_VBI executes cleanly for static text display."""
    xex_file, labels = game_binary

    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Stub OS SYSVBV vector to RTS so JMP SYSVBV returns to test harness
    mem[0xE45F] = 0x60  # RTS

    # Init gameover scene for status=1 (success)
    mem[labels["GAME_RESULT_STATUS"]] = 1
    run_subroutine(cpu, labels["GAMEOVER_INIT"], max_steps=100000)

    # Run VBI multiple frames to verify no crash or memory corruption
    for _ in range(50):
        run_subroutine(cpu, labels["GAMEOVER_VBI"], max_steps=1000)


def test_title_vbi_multi_line_cycling(game_binary) -> None:
    """Verifies that TITLE_VBI cycles through title footer text lines every 250 VBI frames."""
    xex_file, labels = game_binary

    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Stub OS SYSVBV vector to RTS so JMP SYSVBV returns to test harness
    mem[0xE45F] = 0x60  # RTS

    # Init title scene
    run_subroutine(cpu, labels["TITLE_INIT"], max_steps=100000)

    lms_addr = labels["TITLE_TEXT_LMS"] + 1
    max_lines = mem[labels["TITLE_TEXT_MAX_LINES"]]
    assert max_lines >= 2

    # Line 0 starts at $5E10
    initial_lms = mem[lms_addr] | (mem[lms_addr + 1] << 8)
    assert initial_lms == 0x5E10, f"Expected initial LMS $5E10, got ${initial_lms:04X}"

    # Cycle through lines 1 .. max_lines - 1
    for line_idx in range(1, max_lines):
        for _ in range(249):
            run_subroutine(cpu, labels["TITLE_VBI"], max_steps=1000)
        # 250th frame -> switches to next line
        run_subroutine(cpu, labels["TITLE_VBI"], max_steps=1000)
        expected_lms = 0x5E10 + line_idx * 40
        current_lms = mem[lms_addr] | (mem[lms_addr + 1] << 8)
        assert current_lms == expected_lms, f"Expected LMS ${expected_lms:04X} for line {line_idx}, got ${current_lms:04X}"

    # Next 250 frames wrap back to line 0 ($5E10)
    for _ in range(249):
        run_subroutine(cpu, labels["TITLE_VBI"], max_steps=1000)
    run_subroutine(cpu, labels["TITLE_VBI"], max_steps=1000)
    wrapped_lms = mem[lms_addr] | (mem[lms_addr + 1] << 8)
    assert wrapped_lms == 0x5E10, f"Expected LMS $5E10 on wrap-around, got ${wrapped_lms:04X}"




