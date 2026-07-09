import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "actor_test.asm"
    out_xex = tests_dir / "actor_test.xex"
    out_lab = tests_dir / "actor_test.lab"
    
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

def test_player_update(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Init Player
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 50
    cpu.memory[labels["ACTOR_Y"]] = 100
    
    # Simulate Joystick Right
    cpu.memory[labels["INPUTSTATE_JOY"]] = 8
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_PLAYER"]
    
    max_steps = 1000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Infinite loop in Player_Update!"
    
    # Since joystick is RIGHT (8), intention should be X+1, Dir 0
    assert cpu.memory[labels["ACTOR_DIR"]] == 0
    assert cpu.memory[labels["ACTOR_INTENT_X"]] == 51

def test_collision_update(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_INTENT_X"]] = 50
    cpu.memory[labels["ACTOR_INTENT_Y"]] = 50
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_COLLISION"]
    
    max_steps = 2000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Infinite loop in Collision_Update!"
    
    # Since there are no colliders mapped, it should accept the move
    assert cpu.memory[labels["ACTOR_X"]] == 50
    assert cpu.memory[labels["ACTOR_Y"]] == 50

def test_render_prepare(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 50
    cpu.memory[labels["ACTOR_Y"]] = 100
    cpu.memory[labels["ACTOR_Y_OLD"]] = 100
    cpu.memory[labels["ACTOR_HEIGHT"]] = 14
    cpu.memory[labels["ACTOR_DIR"]] = 0
    cpu.memory[labels["ACTOR_ANIM_FRAME"]] = 0
    
    cpu.memory[labels["ACTOR_PTRS_TABLE_LO"]] = labels["GERWALT_RIGHT_PTRS"] & 0xFF
    cpu.memory[labels["ACTOR_PTRS_TABLE_HI"]] = (labels["GERWALT_RIGHT_PTRS"] >> 8) & 0xFF
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_RENDER"]
    
    max_steps = 4000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Infinite loop in Render_Prepare!"
    
    assert cpu.memory[labels["HPOSP0"]] == 50
