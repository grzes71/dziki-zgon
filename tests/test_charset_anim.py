import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "charset_anim_test.asm"
    out_xex = tests_dir / "charset_anim_test.xex"
    out_lab = tests_dir / "charset_anim_test.lab"
    
    mads_exe = "c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe"
    subprocess.run([mads_exe, str(asm_file), f"-o:{out_xex}", f"-t:{out_lab}"], check=True)
    return out_xex, out_lab

def load_xex(filename, memory):
    with open(filename, "rb") as f:
        data = f.read()
    
    i = 0
    while i < len(data):
        if data[i] == 0xFF and data[i+1] == 0xFF:
            i += 2
            if i >= len(data): break
        
        if i + 3 >= len(data): break
        start = data[i] | (data[i+1] << 8)
        i += 2
        end = data[i] | (data[i+1] << 8)
        i += 2
        
        length = end - start + 1
        if i + length > len(data): break
        chunk = data[i:i+length]
        
        for j, byte in enumerate(chunk):
            memory[start + j] = byte
            
        i += length

def load_labels(lab_file):
    labels = {}
    with open(lab_file, "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    addr = int(parts[1], 16)
                    name = parts[2]
                    labels[name.upper()] = addr
                except ValueError:
                    pass
    return labels

@pytest.fixture(scope="module")
def harness():
    xex, lab = compile_harness()
    labels = load_labels(lab)
    return xex, labels

def run_cpu_until_brk(cpu, start_pc, max_steps=30000):
    cpu.sp = 0xFF
    cpu.pc = start_pc
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00:  # BRK
            break
        cpu.step()
        steps += 1
    assert steps < max_steps, "Infinite loop detected!"

def test_charset_anim_counters_decrement(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Adresy z etykietami
    ids_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_IDS"]
    speeds_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_SPEEDS"]
    counters_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_COUNTERS"]
    game_charset = labels["GAME_CHARSET"]
    start_test = labels["START_TEST"]
    src_ptr_z = labels["SRC_PTR"]
    char_count = labels["ANIM_CHAR_COUNT"]
    cpu.memory[labels["ANIM_CHARS_ACTIVE_MASK"]] = 0xFF
    
    # 1. Setup mock data
    # Ustaw początkowe liczniki na 5 dla wszystkich animowanych znaków
    for i in range(char_count):
        cpu.memory[counters_addr + i] = 5
        cpu.memory[speeds_addr + i] = 10
        
    # Ustaw dane pierwszego znaku na znane wartości (np. 0xAA)
    first_char_id = cpu.memory[ids_addr]
    char_addr = game_charset + first_char_id * 8
    for i in range(8):
        cpu.memory[char_addr + i] = 0xAA  # %10101010
        
    # Mock ZP src_ptr
    cpu.memory[src_ptr_z] = 0x12
    cpu.memory[src_ptr_z + 1] = 0x34
    
    # 2. Uruchom kod
    run_cpu_until_brk(cpu, start_test)
    
    # 3. Weryfikacja: liczniki powinny zmaleć o 1 (do 4), a dane znaków nie powinny ulec zmianie
    for i in range(char_count):
        assert cpu.memory[counters_addr + i] == 4, \
            f"Counter {i} should be 4, got {cpu.memory[counters_addr + i]}"
        
    for i in range(8):
        assert cpu.memory[char_addr + i] == 0xAA, \
            f"Char byte {i} should be 0xAA, got {cpu.memory[char_addr + i]:#04x}"
        
    # Wskaźnik ZP powinien pozostać nietknięty
    assert cpu.memory[src_ptr_z] == 0x12
    assert cpu.memory[src_ptr_z + 1] == 0x34

def test_charset_anim_rotate_and_reset(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    ids_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_IDS"]
    speeds_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_SPEEDS"]
    counters_addr = labels["ANIMATE_CHARSET.ANIM_CHAR_COUNTERS"]
    game_charset = labels["GAME_CHARSET"]
    start_test = labels["START_TEST"]
    src_ptr_z = labels["SRC_PTR"]
    char_count = labels["ANIM_CHAR_COUNT"]
    cpu.memory[labels["ANIM_CHARS_ACTIVE_MASK"]] = 0xFF
    
    # 1. Setup mock data
    # Ustaw licznik pierwszego znaku na 1 (powinien się zrolować), a resztę na 5
    cpu.memory[counters_addr + 0] = 1
    cpu.memory[speeds_addr + 0] = 12
    for i in range(1, char_count):
        cpu.memory[counters_addr + i] = 5
        cpu.memory[speeds_addr + i] = 10
        
    # Ustaw dane pierwszego znaku na %10100101 ($A5)
    first_char_id = cpu.memory[ids_addr]
    char_addr = game_charset + first_char_id * 8
    for i in range(8):
        cpu.memory[char_addr + i] = 0xA5
        
    # Mock ZP src_ptr
    cpu.memory[src_ptr_z] = 0x55
    cpu.memory[src_ptr_z + 1] = 0xAA
    
    # 2. Uruchom kod
    run_cpu_until_brk(cpu, start_test)
    
    # 3. Weryfikacja:
    # - Licznik pierwszego znaku zresetowany do 12
    assert cpu.memory[counters_addr + 0] == 12
    # - Inne liczniki zmalały do 4
    for i in range(1, char_count):
        assert cpu.memory[counters_addr + i] == 4, \
            f"Counter {i} should be 4, got {cpu.memory[counters_addr + i]}"
        
    # - Dane pierwszego znaku zrolowane w lewo o 2 bity (circular shift):
    #   %10100101 -> %10010110 ($96)
    for i in range(8):
        assert cpu.memory[char_addr + i] == 0x96, \
            f"Char byte {i} should be 0x96, got {cpu.memory[char_addr + i]:#04x}"
        
    # - Wskaźnik ZP nienaruszony
    assert cpu.memory[src_ptr_z] == 0x55
    assert cpu.memory[src_ptr_z + 1] == 0xAA

def get_expected_mask(cpu, labels, char_id):
    ids_addr = labels["ANIMATED_CHAR_IDS"]
    bit_masks_addr = labels["ANIMATED_CHAR_BIT_MASKS"]
    num_anim = labels.get("NUM_ANIM_CHARS", 0)
    
    for y in range(num_anim - 1, -1, -1):
        if cpu.memory[ids_addr + y] == char_id:
            return cpu.memory[bit_masks_addr + y]
            
    rot_ids_addr = labels.get("ANIMATE_CHARSET.ANIM_CHAR_IDS")
    rot_masks_addr = labels.get("ANIMATE_CHARSET.ANIM_CHAR_BIT_MASKS")
    rot_count = labels.get("ANIM_CHAR_COUNT", 0)
    if rot_ids_addr and rot_masks_addr:
        for y in range(rot_count - 1, -1, -1):
            if cpu.memory[rot_ids_addr + y] == char_id:
                return cpu.memory[rot_masks_addr + y]
    return 0

def test_update_animated_charset(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    num_anim_chars = labels.get("NUM_ANIM_CHARS", 0)
    if num_anim_chars == 0:
        pytest.skip("No animated characters defined in animated.json")

    cur_segment_addr = labels["ANIMATED_CHAR_CUR_SEGMENT"]
    cur_frame_addr = labels["ANIMATED_CHAR_CUR_FRAME"]
    timers_addr = labels["ANIMATED_CHAR_TIMERS"]
    start_test = labels["START_ANIMATED_TEST"]
    src_ptr_z = labels["SRC_PTR"]
    dst_ptr_z = labels["DST_PTR"]
    ids_addr = labels["ANIMATED_CHAR_IDS"]
    bit_masks_addr = labels["ANIMATED_CHAR_BIT_MASKS"]

    cpu.memory[src_ptr_z] = 0x12
    cpu.memory[src_ptr_z + 1] = 0x34
    cpu.memory[dst_ptr_z] = 0x56
    cpu.memory[dst_ptr_z + 1] = 0x78
    
    # Isolate testing to entry 0
    mask_0 = cpu.memory[bit_masks_addr + 0]
    cpu.memory[labels["ANIM_CHARS_ACTIVE_MASK"]] = mask_0

    assert cpu.memory[cur_segment_addr] == 0
    assert cpu.memory[cur_frame_addr] == 255
    assert cpu.memory[timers_addr] == 1

    # First update: wrap frame from 255 to 0, start Segment 0
    run_cpu_until_brk(cpu, start_test)

    assert cpu.memory[cur_segment_addr] == 0
    assert cpu.memory[cur_frame_addr] == 0
    assert cpu.memory[timers_addr] == 100

    char_id_0 = cpu.memory[ids_addr + 0]
    char_addr = 0x6400 + char_id_0 * 8
    expected_frame0 = [0, 0, 0, 0, 0, 0, 0, 0]
    for i in range(8):
        assert cpu.memory[char_addr + i] == expected_frame0[i], \
            f"Byte {i} should be {expected_frame0[i]}, got {cpu.memory[char_addr + i]}"

    assert cpu.memory[src_ptr_z] == 0x12
    assert cpu.memory[src_ptr_z + 1] == 0x34
    assert cpu.memory[dst_ptr_z] == 0x56
    assert cpu.memory[dst_ptr_z + 1] == 0x78

    for i in range(8):
        cpu.memory[char_addr + i] = 0
    
    # Tick down timer (100 -> 99)
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[cur_segment_addr] == 0
    assert cpu.memory[cur_frame_addr] == 0
    assert cpu.memory[timers_addr] == 99
    for i in range(8):
        assert cpu.memory[char_addr + i] == 0

    # Force tick trigger (timers_addr = 1 -> becomes 0 -> advances)
    cpu.memory[timers_addr] = 1
    run_cpu_until_brk(cpu, start_test)
    
    # Segment 0 has 1 frame, so we end Segment 0 and move to Segment 1
    # Segment 1 starts at relative frame 0
    assert cpu.memory[cur_segment_addr] == 1
    assert cpu.memory[cur_frame_addr] == 0
    assert cpu.memory[timers_addr] == 5
    expected_frame1 = [0, 60, 195, 131, 195, 0, 60, 44]
    for i in range(8):
        assert cpu.memory[char_addr + i] == expected_frame1[i], \
            f"Byte {i} should be {expected_frame1[i]}, got {cpu.memory[char_addr + i]}"

def test_charset_anim_segment_repeats(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    num_anim_chars = labels.get("NUM_ANIM_CHARS", 0)
    if num_anim_chars == 0:
        pytest.skip("Test requires animated characters")

    ids_addr = labels["ANIMATED_CHAR_IDS"]
    bit_masks_addr = labels["ANIMATED_CHAR_BIT_MASKS"]
    
    # Find the first entry that has an initial repeat_counter > 0
    target_idx = None
    for i in range(num_anim_chars):
        if cpu.memory[labels["ANIMATED_CHAR_REPEAT_COUNTER"] + i] > 0:
            target_idx = i
            break
            
    if target_idx is None:
        pytest.skip("No animated character found with segment repeats")

    cur_segment_addr = labels["ANIMATED_CHAR_CUR_SEGMENT"] + target_idx
    repeat_counter_addr = labels["ANIMATED_CHAR_REPEAT_COUNTER"] + target_idx
    cur_frame_addr = labels["ANIMATED_CHAR_CUR_FRAME"] + target_idx
    timers_addr = labels["ANIMATED_CHAR_TIMERS"] + target_idx
    start_test = labels["START_ANIMATED_TEST"]
    
    # Isolate testing to target_idx
    mask = cpu.memory[bit_masks_addr + target_idx]
    cpu.memory[labels["ANIM_CHARS_ACTIVE_MASK"]] = mask

    char_id = cpu.memory[ids_addr + target_idx]
    char_addr = 0x6400 + char_id * 8

    initial_repeats = cpu.memory[repeat_counter_addr]

    # Initial state
    assert cpu.memory[cur_segment_addr] == 0
    assert cpu.memory[repeat_counter_addr] == initial_repeats
    assert cpu.memory[cur_frame_addr] == 255
    assert cpu.memory[timers_addr] == 1

    # Step 1: Start Segment 0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[cur_segment_addr] == 0
    assert cpu.memory[repeat_counter_addr] == initial_repeats
    assert cpu.memory[cur_frame_addr] == 0

    # Step 2: Loop through Segment 0 repeats (count goes from initial_repeats down to 0)
    for rep in range(initial_repeats, -1, -1):
        assert cpu.memory[cur_segment_addr] == 0
        assert cpu.memory[repeat_counter_addr] == rep
        cpu.memory[timers_addr] = 1
        run_cpu_until_brk(cpu, start_test)

    # Step 3: Verify transition to Segment 1
    assert cpu.memory[cur_segment_addr] == 1
    assert cpu.memory[cur_frame_addr] == 0

def test_check_active_charset_animations(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    start_test = labels["START_CHECK_ANIMATIONS_TEST"]
    active_mask_addr = labels["ANIM_CHARS_ACTIVE_MASK"]
    screen_addr = labels["GAME_SCREEN_A5"]
    ids_addr = labels["ANIMATED_CHAR_IDS"]

    # Clear screen and mask
    for i in range(480):
        cpu.memory[screen_addr + i] = 0
    cpu.memory[active_mask_addr] = 0

    # 1. Run check with empty screen -> mask should remain 0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[active_mask_addr] == 0

    char_id_0 = cpu.memory[ids_addr + 0]
    expected_mask_0 = get_expected_mask(cpu, labels, char_id_0)

    char_id_1 = cpu.memory[ids_addr + 1] if labels.get("NUM_ANIM_CHARS", 0) > 1 else char_id_0
    expected_mask_1 = get_expected_mask(cpu, labels, char_id_1)

    char_id_2 = cpu.memory[ids_addr + 2] if labels.get("NUM_ANIM_CHARS", 0) > 2 else char_id_0
    expected_mask_2 = get_expected_mask(cpu, labels, char_id_2)

    # 2. Put character 0 on screen -> mask should equal expected_mask_0
    cpu.memory[screen_addr + 100] = char_id_0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[active_mask_addr] == expected_mask_0

    # 3. Clear screen, put character 1 on screen -> mask should equal expected_mask_1
    cpu.memory[screen_addr + 100] = 0
    cpu.memory[screen_addr + 300] = char_id_1
    cpu.memory[active_mask_addr] = 0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[active_mask_addr] == expected_mask_1

    # 4. Put character 2 on screen -> mask should equal (expected_mask_1 | expected_mask_2)
    cpu.memory[screen_addr + 400] = char_id_2
    cpu.memory[active_mask_addr] = 0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[active_mask_addr] == (expected_mask_1 | expected_mask_2)

    # 5. Put character 0 with bit 7 set (inversion) on screen -> mask should equal expected_mask_0
    cpu.memory[screen_addr + 300] = 0
    cpu.memory[screen_addr + 400] = 0
    cpu.memory[screen_addr + 100] = char_id_0 | 0x80
    cpu.memory[active_mask_addr] = 0
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[active_mask_addr] == expected_mask_0

