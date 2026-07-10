import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "real_collision_test.asm"
    out_xex = tests_dir / "real_collision_test.xex"
    out_lab = tests_dir / "real_collision_test.lab"
    
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

def test_swamp_left_movement():
    xex, lab = compile_harness()
    labels = load_labels(lab)
    
    cpu = MPU()
    load_xex(xex, cpu.memory)
    
    # 20 * 4 + 48 = 128
    # 10 * 16 + 32 = 192
    
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 128
    cpu.memory[labels["ACTOR_Y"]] = 192
    cpu.memory[labels["ACTOR_HEIGHT"]] = 14
    
    # Intend to move LEFT
    cpu.memory[labels["ACTOR_INTENT_X"]] = 127
    cpu.memory[labels["ACTOR_INTENT_Y"]] = 192
    
    cpu.memory[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_SWAMP"]
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_COLLISION"]
    
    max_steps = 10000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Infinite loop in Collision_Update!"
    
    # Should successfully update ACTOR_X to 127
    assert cpu.memory[labels["ACTOR_X"]] == 127, f"Blocked! X is {cpu.memory[labels['ACTOR_X']]}"

if __name__ == '__main__':
    test_swamp_left_movement()
    print("SUCCESS! Movement left allowed!")
