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

def test_patrol_enemy_init(harness):
    xex_file, labels = harness
    
    # We will test two different random choices from $D20A:
    # Choice 1: $D20A returns 0 -> direction should be 0
    # Choice 2: $D20A returns 3 -> direction should be 3
    for rand_val in [0, 3]:
        cpu = MPU()
        load_xex(xex_file, cpu.memory)
        
        # Write enemy data at a safe RAM address, e.g., $4500
        enemy_data_addr = 0x4500
        data = [1, 0, 50, 100, 4, 1, 15] # count=1, type=0, X=50, Y=100, strat=4 (patrol), speed=1, color=15
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
        
        enemy_idx = 1
        assert cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] == 1
        assert cpu.memory[labels["ACTOR_X"] + enemy_idx] == 50
        assert cpu.memory[labels["ACTOR_Y"] + enemy_idx] == 100
        assert cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] == 4
        assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == rand_val

def test_patrol_enemy_bounce(harness):
    xex_file, labels = harness
    
    # Test cases: (initial_dir, expected_new_dir)
    # Right (0) -> Down (3) -> Left (1) -> Up (2) -> Right (0)
    test_cases = [
        (0, 3),
        (3, 1),
        (1, 2),
        (2, 0),
    ]
    
    for initial_dir, expected_new_dir in test_cases:
        cpu = MPU()
        load_xex(xex_file, cpu.memory)
        
        enemy_idx = 1
        cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
        cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 4 # patrol
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

def test_pacing_enemy_init(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Write enemy data at a safe RAM address, e.g., $4500
    enemy_data_addr = 0x4500
    data = [1, 0, 50, 100, 5, 1, 15] # count=1, type=0, X=50, Y=100, strat=5 (pacing), speed=1, color=15
    for offset, val in enumerate(data):
        cpu.memory[enemy_data_addr + 1 + offset] = val
        
    # Point SCREEN_PTR to enemy_data_addr
    cpu.memory[labels["SCREEN_PTR"]] = enemy_data_addr & 0xFF
    cpu.memory[labels["SCREEN_PTR"] + 1] = (enemy_data_addr >> 8) & 0xFF
    
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
    
    enemy_idx = 1
    assert cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] == 1
    assert cpu.memory[labels["ACTOR_X"] + enemy_idx] == 50
    assert cpu.memory[labels["ACTOR_Y"] + enemy_idx] == 100
    assert cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] == 5
    assert cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] == 0

def test_pacing_enemy_movement(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    enemy_idx = 1
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 5 # pacing
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast (moves every frame)
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 0       # Right
    cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] = 0
    
    # 1. Simulate blocked: ACTOR_X (50) != ACTOR_INTENT_X (51)
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 51
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.memory[labels["FRAMECOUNTER"]] = 0
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    # Check that timer was set to 30
    assert cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] == 30
    
    # 2. Run update again when paused (e.g. at timer 30).
    # Since it is paused, it should decrement the timer to 29 and not change direction or move.
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] == 29
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 0 # still Right
    
    # 3. Simulate when timer is at 1. It should decrement to 0 and reverse direction to Left (1).
    cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] = 1
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_PAUSE_TIMER"] + enemy_idx] == 0
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 1 # reversed to Left (0 ^ 1 = 1)

def test_homing_enemy_init(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Write enemy data at a safe RAM address, e.g., $4500
    enemy_data_addr = 0x4500
    data = [1, 0, 50, 100, 7, 1, 15] # count=1, type=0, X=50, Y=100, strat=7 (homing), speed=1, color=15
    for offset, val in enumerate(data):
        cpu.memory[enemy_data_addr + 1 + offset] = val
        
    # Point SCREEN_PTR to enemy_data_addr
    cpu.memory[labels["SCREEN_PTR"]] = enemy_data_addr & 0xFF
    cpu.memory[labels["SCREEN_PTR"] + 1] = (enemy_data_addr >> 8) & 0xFF
    
    cpu.memory[0xD20A] = 3 # initial direction
    
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
    
    enemy_idx = 1
    assert cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] == 1
    assert cpu.memory[labels["ACTOR_X"] + enemy_idx] == 50
    assert cpu.memory[labels["ACTOR_Y"] + enemy_idx] == 100
    assert cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] == 7
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 3

def test_homing_enemy_movement(harness):
    xex_file, labels = harness
    
    # Scenario 1: Player is at X=60, Y=100. Enemy is at X=50, Y=100.
    # Recalculation frame: FrameCounter = 15 (15 + 1 (X) = 16 & 0x0F == 0).
    # Since dx (10) > dy (0), it should choose Right (0).
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Gerwalt (player at index 0)
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 60
    cpu.memory[labels["ACTOR_Y"]] = 100
    
    # Enemy
    enemy_idx = 1
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 7 # homing
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 1       # starts at Left (1)
    
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
    cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
    
    cpu.memory[labels["FRAMECOUNTER"]] = 15 # 15 + 1 = 16 & 0x0F == 0 -> should recalculate!
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 0 # Right
    
    # Scenario 2: Player is at X=50, Y=110. Enemy is at X=50, Y=100.
    # Recalculation frame: FrameCounter = 15.
    # Since dx (0) < dy (10), it should choose Down (3).
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Gerwalt
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 50
    cpu.memory[labels["ACTOR_Y"]] = 110
    
    # Enemy
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 7 # homing
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 2       # starts at Up (2)
    
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
    cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
    
    cpu.memory[labels["FRAMECOUNTER"]] = 15 # 15 + 1 = 16 & 0x0F == 0 -> should recalculate!
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 3 # Down
    
    # Scenario 3: FrameCounter = 0. 0 + 1 = 1 & 0x0F != 0.
    # It should NOT recalculate (stays at Left/1).
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Gerwalt is at X=60, Y=100
    cpu.memory[labels["ACTOR_ACTIVE"]] = 1
    cpu.memory[labels["ACTOR_X"]] = 60
    cpu.memory[labels["ACTOR_Y"]] = 100
    
    # Enemy
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 7 # homing
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 1       # starts at Left (1)
    
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
    cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
    
    cpu.memory[labels["FRAMECOUNTER"]] = 0 # should not recalculate!
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 1 # still Left

def test_snake_enemy_init(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Write enemy data at a safe RAM address, e.g., $4500
    enemy_data_addr = 0x4500
    data = [1, 0, 50, 100, 6, 1, 15] # count=1, type=0, X=50, Y=100, strat=6 (snake), speed=1, color=15
    for offset, val in enumerate(data):
        cpu.memory[enemy_data_addr + 1 + offset] = val
        
    # Point SCREEN_PTR to enemy_data_addr
    cpu.memory[labels["SCREEN_PTR"]] = enemy_data_addr & 0xFF
    cpu.memory[labels["SCREEN_PTR"] + 1] = (enemy_data_addr >> 8) & 0xFF
    
    cpu.memory[0xD20A] = 2 # initial direction
    
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
    
    enemy_idx = 1
    assert cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] == 1
    assert cpu.memory[labels["ACTOR_X"] + enemy_idx] == 50
    assert cpu.memory[labels["ACTOR_Y"] + enemy_idx] == 100
    assert cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] == 6
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 2

def test_snake_enemy_movement(harness):
    xex_file, labels = harness
    
    # Scenario 1: FrameCounter + X (1) = 63 + 1 = 64. 64 & 0x3F == 0.
    # It should switch direction to $D20A = 2 (Up).
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    enemy_idx = 1
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 6 # snake
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 0       # starts at 0 (Right)
    
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    # Animation guard
    cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
    cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
    
    cpu.memory[labels["FRAMECOUNTER"]] = 63 # 63 + 1 (X) = 64 & 0x3F == 0 -> should switch!
    cpu.memory[0xD20A] = 2                  # new direction is 2 (Up)
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 2
    
    # Scenario 2: FrameCounter = 0. 0 + 1 (X) = 1 & 0x3F == 1 != 0.
    # It should NOT switch direction (stays at 2).
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    cpu.memory[labels["ACTOR_ACTIVE"] + enemy_idx] = 1
    cpu.memory[labels["ACTOR_STRATEGY"] + enemy_idx] = 6 # snake
    cpu.memory[labels["ACTOR_SPEED"] + enemy_idx] = 2    # fast
    cpu.memory[labels["ACTOR_DIR"] + enemy_idx] = 2       # starts at 2 (Up)
    
    cpu.memory[labels["ACTOR_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_INTENT_X"] + enemy_idx] = 50
    cpu.memory[labels["ACTOR_Y"] + enemy_idx] = 100
    cpu.memory[labels["ACTOR_INTENT_Y"] + enemy_idx] = 100
    
    cpu.memory[labels["ACTOR_ANIM_SPEED"] + enemy_idx] = 6
    cpu.memory[labels["ACTOR_ANIM_TIMER"] + enemy_idx] = 0
    
    cpu.memory[labels["FRAMECOUNTER"]] = 0 # 0 + 1 (X) = 1 & 0x3F != 0 -> should not switch!
    cpu.memory[0xD20A] = 0                 # would be 0 if it switched
    
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST_NPC_UPDATE"]
    steps = 0
    while steps < 2000:
        if cpu.memory[cpu.pc] == 0x00: break
        cpu.step()
        steps += 1
        
    assert cpu.memory[labels["ACTOR_DIR"] + enemy_idx] == 2 # still 2
