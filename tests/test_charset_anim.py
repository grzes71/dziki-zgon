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

def run_cpu_until_brk(cpu, start_pc, max_steps=1000):
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

def test_update_animated_charset(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)

    num_anim_chars = labels.get("NUM_ANIM_CHARS", 0)
    if num_anim_chars == 0:
        pytest.skip("No animated characters defined in animated.json")

    cur_frame_addr = labels["ANIMATED_CHAR_CUR_FRAME"]
    timers_addr = labels["ANIMATED_CHAR_TIMERS"]
    start_test = labels["START_ANIMATED_TEST"]
    src_ptr_z = labels["SRC_PTR"]
    dst_ptr_z = labels["DST_PTR"]

    cpu.memory[src_ptr_z] = 0x12
    cpu.memory[src_ptr_z + 1] = 0x34
    cpu.memory[dst_ptr_z] = 0x56
    cpu.memory[dst_ptr_z + 1] = 0x78

    assert cpu.memory[cur_frame_addr] == 255
    assert cpu.memory[timers_addr] == 1

    run_cpu_until_brk(cpu, start_test)

    assert cpu.memory[cur_frame_addr] == 0
    assert cpu.memory[timers_addr] == 100

    char_addr = 0x6400 + 112 * 8
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
    
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[cur_frame_addr] == 0
    assert cpu.memory[timers_addr] == 99
    for i in range(8):
        assert cpu.memory[char_addr + i] == 0

    cpu.memory[timers_addr] = 1
    run_cpu_until_brk(cpu, start_test)
    assert cpu.memory[cur_frame_addr] == 1
    assert cpu.memory[timers_addr] == 5
    expected_frame1 = [0, 60, 195, 131, 195, 0, 60, 44]
    for i in range(8):
        assert cpu.memory[char_addr + i] == expected_frame1[i], \
            f"Byte {i} should be {expected_frame1[i]}, got {cpu.memory[char_addr + i]}"

