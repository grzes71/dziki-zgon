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



@pytest.mark.parametrize("screen_id,expected_region_id", [
    (1, "WHITE_FIELD"),
    (3, "LAS_PIJANEGO_ZAJACA"),
    (10, "JAR_WIECZNEJ_ZGAGI"),
    (2, "OLD_WYZIMA"),
    (21, "SAMOTNIA_MISTRZA"),
])
def test_travel_screen_footer_formatting(screen_id, expected_region_id):
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

    # Set NEW_SCREEN_ID
    cpu.memory[labels["NEW_SCREEN_ID"]] = screen_id

    # Stub Engine_WaitFrame to simulate FIRE release then press
    wait_frame_addr = labels["ENGINE_WAITFRAME"]
    trig0_addr = labels.get("TRIG0", 0xD010)
    cpu.memory[trig0_addr] = 1  # Start with released FIRE
    # Stub: lda #0; sta trig0; rts
    stub_code = [0xA9, 0x00, 0x8D, trig0_addr & 0xFF, (trig0_addr >> 8) & 0xFF, 0x60]
    for offset, b in enumerate(stub_code):
        cpu.memory[wait_frame_addr + offset] = b

    # Call TRAVEL_SCREEN_SHOW
    show_addr = labels["TRAVEL_SCREEN_SHOW"]
    cpu.memory[0x01FE] = 0x00
    cpu.memory[0x01FF] = 0x00
    cpu.sp = 0xFD
    cpu.pc = show_addr

    steps = 0
    while cpu.pc != 0x0001 and steps < 50000:
        cpu.step()
        steps += 1

    # Inspect FOOTER_ADDR ($5E10) - should contain 320 bytes of region travel text
    from scripts.rle_compress_text import to_atari_screencode
    expected_file = ROOT_DIR / "texts" / f"contents-travel-{expected_region_id}.txt"
    expected_lines = expected_file.read_text(encoding="utf-8").splitlines()
    expected_bytes = bytearray()
    for line in expected_lines[:8]:
        line = line.rstrip("\r\n").ljust(40)[:40]
        for c in line:
            expected_bytes.append(to_atari_screencode(c))
    while len(expected_bytes) < 320:
        expected_bytes.append(0)

    footer_bytes = bytes(cpu.memory[0x5E10:0x5E10 + 320])
    assert footer_bytes == bytes(expected_bytes)

    # Inspect ICON_ADDR+50 (middle of line 2 of icon header) - should contain 20 bytes of padded region name
    import yaml
    region_yaml = ROOT_DIR / "world" / expected_region_id / "region.yaml"
    region_data = yaml.safe_load(region_yaml.read_text(encoding="utf-8"))
    region_name = region_data["name"]
    expected_header = bytearray()
    for c in region_name.ljust(20)[:20]:
        expected_header.append(to_atari_screencode(c))
    
    icon_addr = labels.get("ICON_ADDR", 0x5F74)
    header_bytes = bytes(cpu.memory[icon_addr + 50 : icon_addr + 50 + 20])
    assert header_bytes == bytes(expected_header)




