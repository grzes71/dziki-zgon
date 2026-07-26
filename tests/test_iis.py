import pytest
from py65.devices.mpu6502 import MPU
from pathlib import Path
from test_state_transitions import load_xex, load_labels, run_subroutine, build_main_binary

@pytest.fixture(scope="module")
def game_binary() -> tuple[Path, dict[str, int]]:
    xex_path, lab_path = build_main_binary()
    labels = load_labels(lab_path)
    return xex_path, labels

def test_iis_zero_page_initialization(game_binary) -> None:
    """Verifies that GAME_RESULT_STATUS ($A3) is initialized to 0 on game init."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    assert labels["GAME_RESULT_STATUS"] == 0xA3
    assert mem[labels["GAME_RESULT_STATUS"]] == 0

def test_timer_expiration_sets_game_result_status_2(game_binary) -> None:
    """Verifies that timer expiration sets GAME_RESULT_STATUS to 2."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Initialize timer close to expiration: 00:00, 1 frame remaining in current second
    mem[labels["TIMER_MINUTES"]] = 0
    mem[labels["TIMER_SECONDS"]] = 0
    mem[labels["TIMER_FRAMES"]] = 1
    mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] = 0
    mem[labels["GAME_RESULT_STATUS"]] = 0

    # Ensure no active enemies
    for i in range(1, 4):
        mem[labels["ACTOR_ACTIVE"] + i] = 0

    # Execute update_timer to expire timer
    run_subroutine(cpu, labels["UPDATE_TIMER"])


    assert mem[labels["TIMER_MINUTES"]] == 0
    assert mem[labels["TIMER_SECONDS"]] == 0
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 1
    assert mem[labels["GAME_RESULT_STATUS"]] == 2

def test_iis_interaction_unmet(game_binary) -> None:
    """Verifies that pressing Fire near interactive object without required items displays conditions_unmet text."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    # Set active screen to TAVERN (Screen 4 in default world)
    mem[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_TAVERN"]

    # Position Gerwalt (Actor 0) below The Tavern (x=18, y=5, size w=12, h=2)
    # The Tavern grid Y is 5..6 (y1=5, y2=6).
    # Position Gerwalt at grid x=18, y=7 (pixel x = 18*4+48 = 120, pixel y = 7*16+32 = 144)
    # Facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 120
    mem[labels["ACTOR_Y"]] = 144
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    # Inventory starts with Sznurek (ID 4), no Item 1 (Fałszywe pieniądze)
    assert mem[labels["INVENTORY_COUNT"]] == 1
    assert mem[labels["INVENTORY_ITEMS"]] == 4

    # Press Fire button (TRIG0 = 0 -> InputState_Trig = 0)
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0

    # Execute IIS_Update
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # Check results:
    # Inventory unchanged
    assert mem[labels["INVENTORY_COUNT"]] == 1
    assert mem[labels["INVENTORY_ITEMS"]] == 4
    assert mem[labels["GAME_RESULT_STATUS"]] == 0

    # MSG_STATE should be 1 (showing message)
    assert mem[labels["MSG_STATE"]] == 1

def test_iis_interaction_met_and_success(game_binary) -> None:
    """Verifies that pressing Fire near interactive object WITH required items swaps items, displays conditions_met, and sets GAME_RESULT_STATUS=1."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    # Set active screen to TAVERN
    mem[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_TAVERN"]

    # Add Item 1 (Fałszywe pieniądze) to inventory using inventory_add_item
    cpu.a = 1
    run_subroutine(cpu, labels["INVENTORY_ADD_ITEM"])
    assert mem[labels["INVENTORY_COUNT"]] == 2

    # Position Gerwalt below The Tavern facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 120
    mem[labels["ACTOR_Y"]] = 144
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    # Press Fire button
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0

    # Execute IIS_Update
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # Check results:
    # Item 1 should be removed, Item 5 ("Podarty rachunek") added
    assert mem[labels["INVENTORY_COUNT"]] == 2
    # Inventory items should contain 4 (Sznurek) and 5 (Podarty rachunek)
    items_in_inv = [mem[labels["INVENTORY_ITEMS"] + i] for i in range(2)]
    assert 1 not in items_in_inv
    assert 5 in items_in_inv

    # Game status should be 1 (Success!) and stage advance requested
    assert mem[labels["GAME_RESULT_STATUS"]] == 1
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 1

    # MSG_STATE should be 1 (showing message)
    assert mem[labels["MSG_STATE"]] == 1
