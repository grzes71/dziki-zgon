import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU
import sys

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "real_collision_test.asm"
    out_xex = tests_dir / "real_collision_test.xex"
    out_lab = tests_dir / "real_collision_test.lab"
    
    mads_exe = "c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe"
    subprocess.run([mads_exe, str(asm_file), f"-o:{out_xex}", f"-t:{out_lab}"], check=True)
    return out_xex, out_lab

def test_full_movement():
    compile_harness()
    tests_dir = Path(__file__).parent
    xex = tests_dir / "real_collision_test.xex"
    lab = tests_dir / "real_collision_test.lab"
    
    # Load labels
    labels = {}
    with open(lab, "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    addr = int(parts[1], 16)
                    name = parts[2]
                    labels[name.upper()] = addr
                except ValueError:
                    pass
                    
    cpu = MPU()
    
    # Load XEX
    with open(xex, "rb") as f:
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
        chunk = data[i:i+length]
        for j, byte in enumerate(chunk):
            cpu.memory[start + j] = byte
        i += length
    
    # Setup state
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 128
    cpu.memory[labels["ACTOR_Y"]] = 192
    cpu.memory[labels["ACTOR_HEIGHT"]] = 14
    cpu.memory[labels["ACTOR_DIR"]] = 3 # Facing down
    cpu.memory[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_SWAMP"]
    cpu.memory[labels["FRAMECOUNTER"]] = 0 # Even frame, allows movement!
    
    # Press LEFT
    cpu.memory[labels["INPUTSTATE_JOY"]] = 4
    
    # 1. Run Player_Update
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_PLAYER"]
    steps = 0
    while steps < 10000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    print(f"After Player_Update, INTENT_X = {cpu.memory[labels['ACTOR_INTENT_X']]}")
    
    # 2. Run Collision_Update
    cpu.pc = labels["START_TEST_COLLISION"]
    steps = 0
    while steps < 10000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    print(f"After Collision_Update, ACTOR_X = {cpu.memory[labels['ACTOR_X']]}")

if __name__ == '__main__':
    test_full_movement()
