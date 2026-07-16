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
    cpu.memory[labels["ACTOR_INTENT_X"]] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"]] = 100
    
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
    assert cpu.memory[labels["ACTOR_X"]] == 100
    assert cpu.memory[labels["ACTOR_Y"]] == 100

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

def test_chaotic_enemy_init(harness):
    xex_file, labels = harness
    
    # We will test two different random choices from $D20A:
    # Choice 1: $D20A returns 0 -> direction should be 0
    # Choice 2: $D20A returns 3 -> direction should be 3
    for rand_val in [0, 3]:
        cpu = MPU()
        load_xex(xex_file, cpu.memory)
        
        # Write enemy data at a safe RAM address, e.g., $4500
        enemy_data_addr = 0x4500
        data = [1, 0, 50, 100, 3, 1, 15] # count=1, type=0, X=50, Y=100, strat=3 (chaotic), speed=1, color=15
        for offset, val in enumerate(data):
            cpu.memory[enemy_data_addr + 1 + offset] = val
            
        # Point SCREEN_PTR to enemy_data_addr
        cpu.memory[labels["SCREEN_PTR"]] = enemy_data_addr & 0xFF
        cpu.memory[labels["SCREEN_PTR"] + 1] = (enemy_data_addr >> 8) & 0xFF
        
        # Set up $D20A random register mock value
        cpu.memory[0xD20A] = rand_val
        
        cpu.sp = 0xFF
        cpu.pc = labels["START_TEST_LOAD_ENEMIES"]
        
        max_steps = 2000
        steps = 0
        while steps < max_steps:
            if cpu.memory[cpu.pc] == 0x00: # BRK
                break
            cpu.step()
            steps += 1
            
        assert steps < max_steps, "Infinite loop in Load_Screen_Enemies!"
        
        # Verify first enemy properties (index 1 in SoA: index 0 is player)
        enemy_idx = 1
        assert cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] == 1
        assert cpu.memory[labels["ACTOR_X"] + enemy_idx] == 50
        assert cpu.memory[labels["ACTOR_Y"] + enemy_idx] == 100
        assert cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] == 3
        assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == rand_val

def test_chaotic_enemy_bounce(harness):
    xex_file, labels = harness
    
    # Test cases: (initial_dir, random_reg_val, expected_new_dir)
    test_cases = [
        (0, 0, 1), # Case A: current=horizontal, axis_choice=horizontal -> reverse -> Left (1)
        (0, 3, 3), # Case B: current=horizontal, axis_choice=vertical, dir_choice=1 -> Down (3)
        (2, 0, 0), # Case C: current=vertical, axis_choice=horizontal, dir_choice=0 -> Right (0)
        (2, 3, 3), # Case D: current=vertical, axis_choice=vertical -> reverse -> Down (3)
    ]
    
    for initial_dir, rand_val, expected_new_dir in test_cases:
        cpu = MPU()
        load_xex(xex_file, cpu.memory)
        
        enemy_idx = 1
        cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
        cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 3 # chaotic
        cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast (moves every frame)
        cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = initial_dir
        
        # Set up coordinates to simulate a blocked state.
        cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
        cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 51
        cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
        cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
        
        # Animation guard
        cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
        cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
        
        cpu.memory[0xD20A] = rand_val
        cpu.memory[labels["FRAMECOUNTER"]] = 0
        
        cpu.sp = 0xFF
        cpu.pc = labels["START_TEST_NPC_UPDATE"]
        
        max_steps = 2000
        steps = 0
        while steps < max_steps:
            if cpu.memory[cpu.pc] == 0x00: # BRK
                break
            cpu.step()
            steps += 1
            
        assert steps < max_steps, "Infinite loop in NPC_Update!"
        
        # Check that the new direction is correct
        assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == expected_new_dir
