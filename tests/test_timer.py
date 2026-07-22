import pytest
from py65.devices.mpu6502 import MPU
from pathlib import Path
from test_state_transitions import load_xex, load_labels, run_subroutine, build_main_binary

@pytest.fixture(scope="module")
def game_binary() -> tuple[Path, dict[str, int]]:
    xex_path, lab_path = build_main_binary()
    labels = load_labels(lab_path)
    return xex_path, labels

def test_timer_decrement(game_binary) -> None:
    """Verifies that the timer decrements correctly frame-by-frame and second-by-second at normal speed (1 second per 50 frames)."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Initialize timer to 12:00 (timer_minutes=12, timer_seconds=0, timer_frames=50)
    mem[labels["TIMER_MINUTES"]] = 12
    mem[labels["TIMER_SECONDS"]] = 0
    mem[labels["TIMER_FRAMES"]] = 50
    mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] = 0

    # Ensure no active enemies to avoid collisions
    for i in range(1, 4):
        mem[labels["ACTOR_ACTIVE"] + i] = 0

    # Execute update_timer once (should decrement frame counter to 49)
    run_subroutine(cpu, labels["UPDATE_TIMER"])
    assert mem[labels["TIMER_FRAMES"]] == 49
    assert mem[labels["TIMER_SECONDS"]] == 0
    assert mem[labels["TIMER_MINUTES"]] == 12

    # Advance 49 more frames to reach 1 second tick (total 50 frames)
    for _ in range(49):
        run_subroutine(cpu, labels["UPDATE_TIMER"])
    
    # After 50 frames, it should tick down to 11:59 (frames reset to 50)
    assert mem[labels["TIMER_FRAMES"]] == 50
    assert mem[labels["TIMER_SECONDS"]] == 59
    assert mem[labels["TIMER_MINUTES"]] == 11

def test_timer_expiration_triggers_gameover(game_binary) -> None:
    """Verifies that reaching 00:00 triggers game over on the next second tick."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Ensure no active enemies
    for i in range(1, 4):
        mem[labels["ACTOR_ACTIVE"] + i] = 0

    # Initialize timer close to expiration: 00:01, 1 frame remaining in the current second
    mem[labels["TIMER_MINUTES"]] = 0
    mem[labels["TIMER_SECONDS"]] = 1
    mem[labels["TIMER_FRAMES"]] = 1
    mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] = 0

    # 1) Execute update_timer once. It should decrement the last frame of 00:01, resetting frames to 50,
    # decrementing seconds to 00. The timer should display 00:00, and no stage advance should be requested yet.
    run_subroutine(cpu, labels["UPDATE_TIMER"])
    assert mem[labels["TIMER_FRAMES"]] == 50
    assert mem[labels["TIMER_SECONDS"]] == 0
    assert mem[labels["TIMER_MINUTES"]] == 0
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 0

    # 2) Run 49 frames of the final 00:00 second (leaves 1 frame remaining).
    for _ in range(49):
        run_subroutine(cpu, labels["UPDATE_TIMER"])
    assert mem[labels["TIMER_FRAMES"]] == 1
    assert mem[labels["TIMER_SECONDS"]] == 0
    assert mem[labels["TIMER_MINUTES"]] == 0
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 0

    # 3) The 50th frame tick should trigger the game over request since the time has fully run out.
    run_subroutine(cpu, labels["UPDATE_TIMER"])
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 1

def test_enemy_collision_timer_acceleration(game_binary) -> None:
    """Verifies that colliding with enemies subtracts their damage value dynamically read from the ENEMY_DAMAGE table."""
    xex_file, labels = game_binary
    
    # 1) Test Bazyliszek collision (damage dynamically loaded from type 2 index)
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory
    
    mem[labels["TIMER_MINUTES"]] = 12
    mem[labels["TIMER_SECONDS"]] = 0
    mem[labels["TIMER_FRAMES"]] = 50
    
    # Setup Player (Actor 0) at (100, 100)
    mem[labels["ACTOR_X"]] = 100
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_ACTIVE"]] = 1
    
    # Setup Bazyliszek (Actor 1) overlapping at (100, 100)
    mem[labels["ACTOR_X"] + 1] = 100
    mem[labels["ACTOR_Y"] + 1] = 100
    mem[labels["ACTOR_HEIGHT"] + 1] = 16
    mem[labels["ACTOR_TYPE"] + 1] = 2  # Bazyliszek type index
    mem[labels["ACTOR_ACTIVE"] + 1] = 1
    
    # Deactivate others
    mem[labels["ACTOR_ACTIVE"] + 2] = 0
    mem[labels["ACTOR_ACTIVE"] + 3] = 0
    
    # Read dynamic damage
    damage_bazyliszek = mem[labels["ENEMY_DAMAGE"] + 2]
    
    # Run update_timer once
    run_subroutine(cpu, labels["UPDATE_TIMER"])
    
    # Verify exact subtraction
    expected_total_seconds = 12 * 60 - damage_bazyliszek
    assert mem[labels["TIMER_MINUTES"]] == expected_total_seconds // 60
    assert mem[labels["TIMER_SECONDS"]] == expected_total_seconds % 60

    # 2) Test Strzyga collision (damage dynamically loaded from type 1 index)
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory
    
    mem[labels["TIMER_MINUTES"]] = 12
    mem[labels["TIMER_SECONDS"]] = 0
    mem[labels["TIMER_FRAMES"]] = 50
    
    # Setup Player at (100, 100)
    mem[labels["ACTOR_X"]] = 100
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_ACTIVE"]] = 1
    
    # Setup Strzyga (Actor 1) overlapping at (100, 100)
    mem[labels["ACTOR_X"] + 1] = 100
    mem[labels["ACTOR_Y"] + 1] = 100
    mem[labels["ACTOR_HEIGHT"] + 1] = 16
    mem[labels["ACTOR_TYPE"] + 1] = 1  # Strzyga type index
    mem[labels["ACTOR_ACTIVE"] + 1] = 1
    
    # Deactivate others
    mem[labels["ACTOR_ACTIVE"] + 2] = 0
    mem[labels["ACTOR_ACTIVE"] + 3] = 0
    
    # Read dynamic damage
    damage_strzyga = mem[labels["ENEMY_DAMAGE"] + 1]
    
    # Run update_timer once
    run_subroutine(cpu, labels["UPDATE_TIMER"])
    
    # Verify exact subtraction
    expected_total_seconds = 12 * 60 - damage_strzyga
    assert mem[labels["TIMER_MINUTES"]] == expected_total_seconds // 60
    assert mem[labels["TIMER_SECONDS"]] == expected_total_seconds % 60

def test_enemy_collision_color_change(game_binary) -> None:
    """Verifies that colliding with an enemy changes the player's color to red (54), and reverts to the default palette color when collision ends."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Setup Player (Actor 0) at (100, 100)
    mem[labels["ACTOR_X"]] = 100
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_ACTIVE"]] = 1

    # Get default color from game_palette
    default_color = mem[labels["GAME_PALETTE"]]
    mem[labels["ACTOR_COLOR"]] = default_color

    # Ensure no active enemies initially
    for i in range(1, 4):
        mem[labels["ACTOR_ACTIVE"] + i] = 0

    # 1) Run get_collision_damage without collision
    run_subroutine(cpu, labels["GET_COLLISION_DAMAGE"])
    # Color should remain default
    assert mem[labels["ACTOR_COLOR"]] == default_color

    # 2) Spawn overlapping Kikimora (Actor 1) at (100, 100)
    mem[labels["ACTOR_X"] + 1] = 100
    mem[labels["ACTOR_Y"] + 1] = 100
    mem[labels["ACTOR_HEIGHT"] + 1] = 16
    mem[labels["ACTOR_TYPE"] + 1] = 0  # Kikimora type index
    mem[labels["ACTOR_ACTIVE"] + 1] = 1

    # Run get_collision_damage with collision
    run_subroutine(cpu, labels["GET_COLLISION_DAMAGE"])
    # Color should be red (54)
    assert mem[labels["ACTOR_COLOR"]] == 54

    # 3) Deactivate the enemy
    mem[labels["ACTOR_ACTIVE"] + 1] = 0

    # Run get_collision_damage again
    run_subroutine(cpu, labels["GET_COLLISION_DAMAGE"])
    # Color should revert to default
    assert mem[labels["ACTOR_COLOR"]] == default_color

def test_enemy_collision_player_slowdown(game_binary) -> None:
    """Verifies that player movement speed is halved during collisions (both vertically and horizontally)."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Initialize Player
    mem[labels["ACTOR_ACTIVE"]] = 1
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["PLAYER_FRAME_COUNTER"]] = 0

    # 1) Test Normal (No Collision) Horizontal Speed:
    # Joy Right = 8
    # Frame 1 (counter=1): check_horizontal_move returns 1 -> INTENT_X = X + 1
    # Frame 2 (counter=2): check_horizontal_move returns 0 -> no change
    mem[labels["COLLISION_ACTIVE"]] = 0
    
    # Run frame 1
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 51

    # Run frame 2
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 50

    # 2) Test Normal (No Collision) Vertical Speed:
    # Joy Down = 2
    # Frame 3: INTENT_Y = Y + 1
    mem[labels["INPUTSTATE_JOY"]] = 2
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_INTENT_Y"]] = 100
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_Y"]] == 101

    # 3) Test Colliding Horizontal Speed:
    # Should move only every 4th frame (when counter % 4 == 1, i.e. counter=1, 5, etc.)
    # Reset counter to 0
    mem[labels["PLAYER_FRAME_COUNTER"]] = 0
    mem[labels["COLLISION_ACTIVE"]] = 1

    # Frame 1 (counter=1): check_horizontal_move returns 1
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 51

    # Frame 2 (counter=2): check_horizontal_move returns 0
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 50

    # Frame 3 (counter=3): check_horizontal_move returns 0
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 50

    # Frame 4 (counter=4): check_horizontal_move returns 0
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 50

    # Frame 5 (counter=5): check_horizontal_move returns 1
    mem[labels["INPUTSTATE_JOY"]] = 8
    mem[labels["ACTOR_X"]] = 50
    mem[labels["ACTOR_INTENT_X"]] = 50
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_X"]] == 51

    # 4) Test Colliding Vertical Speed:
    # Should move only every 2nd frame (when counter % 2 == 1, i.e. counter=5, 7, etc.)
    # Reset counter to 4
    mem[labels["PLAYER_FRAME_COUNTER"]] = 4

    # Frame 5 (counter=5): odd -> processes vertical movement
    mem[labels["INPUTSTATE_JOY"]] = 2
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_INTENT_Y"]] = 100
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_Y"]] == 101

    # Frame 6 (counter=6): even -> skips vertical movement
    mem[labels["INPUTSTATE_JOY"]] = 2
    mem[labels["ACTOR_Y"]] = 100
    mem[labels["ACTOR_INTENT_Y"]] = 100
    run_subroutine(cpu, labels["PLAYER_UPDATE"])
    assert mem[labels["ACTOR_INTENT_Y"]] == 100

def test_pf3_collision_timer_acceleration(game_binary) -> None:
    """Verifies that colliding with PF3 playfield color subtracts the region damage value in full seconds per frame."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    mem[labels["TIMER_MINUTES"]] = 12
    mem[labels["TIMER_SECONDS"]] = 0
    mem[labels["TIMER_FRAMES"]] = 50
    mem[labels["GAME_STAGE"]] = 0  # Region WHITE_FIELD (damage is 10)

    # Setup Player (Actor 0)
    mem[labels["ACTOR_ACTIVE"]] = 1
    mem[labels["ACTOR_COLOR"]] = 0x0E

    # Ensure no active enemies to isolate PF3 collision
    for i in range(1, 4):
        mem[labels["ACTOR_ACTIVE"] + i] = 0

    # Simulate PF3 collision by setting P0PF register to 8 (bit 3)
    mem[labels["P0PF"]] = 8

    # Read dynamic region damage for region 0
    damage_region = mem[labels["REGION_DAMAGE"] + 0]
    assert damage_region == 10

    # Run update_timer once
    run_subroutine(cpu, labels["UPDATE_TIMER"])

    # Verify exact subtraction: 12:00 - 10 seconds = 11:50
    expected_total_seconds = 12 * 60 - damage_region
    assert mem[labels["TIMER_MINUTES"]] == expected_total_seconds // 60
    assert mem[labels["TIMER_SECONDS"]] == expected_total_seconds % 60

    # Verify color became red (54) and collision_active is 1
    assert mem[labels["ACTOR_COLOR"]] == 54
    assert mem[labels["COLLISION_ACTIVE"]] == 1

    # Verify that HITCLR was written to (cleared) by get_collision_damage
    # In hardware it would clear P0PF. In Py65 it wrote 0 to HITCLR.
    assert mem[labels["HITCLR"]] == 0




