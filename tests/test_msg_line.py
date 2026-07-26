import pytest
from py65.devices.mpu6502 import MPU
from pathlib import Path
from test_state_transitions import load_xex, load_labels, run_subroutine, build_main_binary

POLISH_MAP = {
    'ą': 0x7B, 'Ą': 0x7B,
    'ć': 0x7C, 'Ć': 0x7C,
    'ę': 0x7D, 'Ę': 0x7D,
    'ł': 0x7E, 'Ł': 0x7E,
    'ń': 0x7F, 'Ń': 0x7F,
    'ó': 0x5F, 'Ó': 0x5F,
    'ś': 0x5E, 'Ś': 0x5E,
    'ź': 0x5D, 'Ź': 0x5D,
    'ż': 0x5C, 'Ż': 0x5C
}

def to_screencode(c: str) -> int:
    if c in POLISH_MAP:
        return POLISH_MAP[c]
    val = ord(c)
    if 32 <= val <= 95:
        return val - 32
    elif 96 <= val <= 127:
        return val
    elif 0 <= val <= 31:
        return val + 64
    return val

@pytest.fixture(scope="module")
def game_binary() -> tuple[Path, dict[str, int]]:
    xex_path, lab_path = build_main_binary()
    labels = load_labels(lab_path)
    return xex_path, labels

def show_message_helper(cpu: MPU, labels: dict[str, int], text: str, str_addr: int = 0x3900) -> None:
    """Writes text (UTF-8 bytes or ASCII) to memory at str_addr and invokes MSG_SHOW."""
    mem = cpu.memory
    encoded = text.encode("utf-8") + b"\x00"
    for i, b in enumerate(encoded):
        mem[str_addr + i] = b
    
    cpu.a = str_addr & 0xFF
    cpu.y = (str_addr >> 8) & 0xFF
    run_subroutine(cpu, labels["MSG_SHOW"])

def test_msg_initial_game_start(game_binary) -> None:
    """Verifies that entering game_init displays the initial MSG_START_GAME message centered with MSG_STATE=1."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    # MSG_STATE at ZP $A2 should be 1
    assert mem[labels["MSG_STATE"]] == 1

    # Read MSG_START_GAME string from memory dynamically
    msg_addr = labels["MSG_START_GAME"]
    msg_bytes = bytearray()
    curr = msg_addr
    while mem[curr] != 0:
        msg_bytes.append(mem[curr])
        curr += 1

    expected_text = msg_bytes.decode("utf-8", errors="ignore")
    expected_len = len(expected_text)
    expected_offset = (36 - expected_len) // 2

    vram_start = labels["GAME_SCREEN_A2"] + 42

    # Check padding before message
    for i in range(expected_offset):
        assert mem[vram_start + i] == 0

    # Check text screen codes
    for i, char in enumerate(expected_text):
        assert mem[vram_start + expected_offset + i] == to_screencode(char)


def test_msg_state_transitions(game_binary) -> None:
    """Verifies MSG_STATE transitions: 1 (0-4s) -> 2 (4-5s) -> 0 (5s, line cleared)."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    show_message_helper(cpu, labels, "Testowe zdanie")
    assert mem[labels["MSG_STATE"]] == 1

    # Advance 199 frames (still < 4s = 200 frames)
    for _ in range(199):
        run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 1

    # 200th frame (4 seconds elapsed, 1 second remaining) -> state 2
    run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 2

    # Advance 49 frames (total 249 frames, state remains 2)
    for _ in range(49):
        run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 2

    # 250th frame (5 seconds elapsed) -> state 0, line cleared to spaces
    run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 0

    # Verify line is cleared
    vram_start = labels["GAME_SCREEN_A2"] + 42
    for i in range(36):
        assert mem[vram_start + i] == 0

def test_msg_multi_sentence(game_binary) -> None:
    """Verifies multi-sentence messages split by & display sequentially for 5 seconds each with proper state transitions."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    show_message_helper(cpu, labels, "Pierwsze zdanie&Drugie zdanie")
    assert mem[labels["MSG_STATE"]] == 1

    # Verify sentence 1 "Pierwsze zdanie" is displayed
    vram_start = labels["GAME_SCREEN_A2"] + 42
    s1_text = "Pierwsze zdanie"
    s1_offset = (36 - len(s1_text)) // 2
    assert mem[vram_start + s1_offset] == to_screencode("P")

    # Run 250 frames for sentence 1
    for _ in range(249):
        run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 2

    # 250th frame transitions to sentence 2 "Drugie zdanie" (MSG_STATE = 1)
    run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 1

    # Verify sentence 2 "Drugie zdanie" is displayed
    s2_text = "Drugie zdanie"
    s2_offset = (36 - len(s2_text)) // 2
    assert mem[vram_start + s2_offset] == to_screencode("D")

    # Run 250 frames for sentence 2
    for _ in range(249):
        run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 2

    # Final frame -> clears sentence 2, MSG_STATE becomes 0
    run_subroutine(cpu, labels["MSG_UPDATE"])
    assert mem[labels["MSG_STATE"]] == 0

    for i in range(36):
        assert mem[vram_start + i] == 0

def test_msg_polish_characters(game_binary) -> None:
    """Verifies correct conversion of Polish characters to Atari font screen codes."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    polish_text = "Zażółć gęślą jaźń"
    show_message_helper(cpu, labels, polish_text)

    vram_start = labels["GAME_SCREEN_A2"] + 42
    offset = (36 - len(polish_text)) // 2

    for i, char in enumerate(polish_text):
        actual_code = mem[vram_start + offset + i]
        expected_code = to_screencode(char)
        assert actual_code == expected_code, f"Mismatch at index {i} ('{char}'): expected {expected_code:#x}, got {actual_code:#x}"
