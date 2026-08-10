import pytest
from pathlib import Path
from py65.devices.mpu6502 import MPU

ROOT_DIR = Path(__file__).parent.parent


def parse_labels(lab_path: Path) -> dict[str, int]:
    labels = {}
    if not lab_path.exists():
        return labels
    for line in lab_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                name = parts[2].upper()
                val_str = parts[1].lstrip("$")
                labels[name] = int(val_str, 16)
            except ValueError:
                continue
    return labels


def test_travel_screen_symbols_exist():
    lab_path = ROOT_DIR / "gen" / "game.lab"
    if not lab_path.exists():
        pytest.skip("gen/game.lab does not exist yet")

    labels = parse_labels(lab_path)

    assert "TRAVEL_SCREEN_SHOW" in labels
    assert "DLIST_TRAVEL" in labels
    assert "IS_PORTAL_TRANSITION" in labels
    assert labels["IS_PORTAL_TRANSITION"] == 0x00A6



def test_travel_screen_footer_formatting():
    lab_path = ROOT_DIR / "gen" / "game.lab"
    xex_path = ROOT_DIR / "dziki_zgon.xex"
    if not lab_path.exists() or not xex_path.exists():
        pytest.skip("dziki_zgon.xex does not exist yet")

    labels = parse_labels(lab_path)
    cpu = MPU()

    # Load XEX into py65 memory
    data = xex_path.read_bytes()
    idx = 0
    while idx < len(data):
        if data[idx:idx+2] == b"\xFF\xFF":
            idx += 2
        if idx >= len(data):
            break
        seg_start = data[idx] | (data[idx+1] << 8)
        seg_end = data[idx+2] | (data[idx+3] << 8)
        idx += 4
        seg_len = seg_end - seg_start + 1
        cpu.memory[seg_start:seg_start+seg_len] = data[idx:idx+seg_len]
        idx += seg_len

    # Set NEW_SCREEN_ID to 1 (screen 1 -> region "białe pole")
    cpu.memory[labels["NEW_SCREEN_ID"]] = 1

    # Place a RTS at Engine_WaitFrame to stub out the 250 frame wait loop
    wait_frame_addr = labels["ENGINE_WAITFRAME"]
    cpu.memory[wait_frame_addr] = 0x60  # RTS

    # Call TRAVEL_SCREEN_SHOW
    show_addr = labels["TRAVEL_SCREEN_SHOW"]
    cpu.memory[0x01FE] = 0x00
    cpu.memory[0x01FF] = 0x00
    cpu.sp = 0xFD
    cpu.pc = show_addr

    steps = 0
    while cpu.pc != 0x0001 and steps < 10000:
        cpu.step()
        steps += 1

    # Inspect FOOTER_ADDR ($5E10)
    footer_bytes = bytes(cpu.memory[0x5E10:0x5E38])
    # Total string = "podróż do białe pole" (20 chars) -> offset (40-20)/2 = 10
    # Bytes 0..9 should be 0x00
    assert footer_bytes[:10] == b"\x00" * 10
    # Bytes 10..19: "podróż do " ($70, $6F, $64, $72, $5F, $5C, $00, $64, $6F, $00)
    assert footer_bytes[10:20] == bytes([0x70, 0x6F, 0x64, 0x72, 0x5F, 0x5C, 0x00, 0x64, 0x6F, 0x00])
    # Bytes 20..29: "białe pole" ($62, $69, $61, $7E, $65, $00, $70, $6F, $6C, $65)
    assert footer_bytes[20:30] == bytes([0x62, 0x69, 0x61, 0x7E, 0x65, 0x00, 0x70, 0x6F, 0x6C, 0x65])
    # Bytes 30..39 should be 0x00
    assert footer_bytes[30:40] == b"\x00" * 10




