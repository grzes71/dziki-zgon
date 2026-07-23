import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "world_transition_test.asm"
    out_xex = tests_dir / "world_transition_test.xex"
    out_lab = tests_dir / "world_transition_test.lab"
    
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

def test_world_update_transition_resets_hposp0_and_hitclr(harness):
    xex, labels = harness
    cpu = MPU()
    load_xex(xex, cpu.memory)
    
    # Pre-set old state
    cpu.memory[labels["GAME_SCREEN_ID"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 200
    cpu.memory[labels["ACTOR_Y"]] = 100
    cpu.memory[labels["HPOSP0"]] = 200
    cpu.memory[labels["HITCLR"]] = 0xFF
    
    # Request transition to screen 3 at X=52, Y=120
    cpu.memory[labels["REQ_SCREEN_TRANSITION"]] = 1
    cpu.memory[labels["NEW_SCREEN_ID"]] = 3
    cpu.memory[labels["NEW_ACTOR_X"]] = 52
    cpu.memory[labels["NEW_ACTOR_Y"]] = 120
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_WORLD_UPDATE"]
    
    max_steps = 5000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00:  # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Infinite loop in World_Update!"
    
    # Assertions
    assert cpu.memory[labels["REQ_SCREEN_TRANSITION"]] == 0, "REQ_SCREEN_TRANSITION was not cleared"
    assert cpu.memory[labels["GAME_SCREEN_ID"]] == 3, "GAME_SCREEN_ID was not updated"
    assert cpu.memory[labels["ACTOR_X"]] == 52, "ACTOR_X was not updated to NEW_ACTOR_X"
    assert cpu.memory[labels["ACTOR_Y"]] == 120, "ACTOR_Y was not updated to NEW_ACTOR_Y"
    assert cpu.memory[labels["HPOSP0"]] == 0, "HPOSP0 was not hidden (set to 0) during transition"
    assert cpu.memory[labels["HITCLR"]] == 0, "HITCLR was not cleared at end of transition"

def test_world_update_no_transition(harness):
    xex, labels = harness
    cpu = MPU()
    load_xex(xex, cpu.memory)
    
    cpu.memory[labels["GAME_SCREEN_ID"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 100
    cpu.memory[labels["REQ_SCREEN_TRANSITION"]] = 0
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_WORLD_UPDATE"]
    
    max_steps = 500
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00:
            break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["GAME_SCREEN_ID"]] == 1
    assert cpu.memory[labels["ACTOR_X"]] == 100
