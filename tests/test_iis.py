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

    # Position Gerwalt (Actor 0) below The Tavern (x=18, y=4, size w=12, h=2)
    # The Tavern grid Y is 4..5 (y1=4, y2=5).
    # Position Gerwalt at grid x=18, y=6 (pixel x = 18*4+48 = 120, pixel y = 6*16+32 = 128)
    # Facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 120
    mem[labels["ACTOR_Y"]] = 128
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    # Inventory starts empty, no Item 1 (Fałszywe pieniądze)
    assert mem[labels["INVENTORY_COUNT"]] == 0

    # Press Fire button (TRIG0 = 0 -> InputState_Trig = 0)
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0

    # Execute IIS_Update
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # Check results:
    # Inventory unchanged
    assert mem[labels["INVENTORY_COUNT"]] == 0
    assert mem[labels["GAME_RESULT_STATUS"]] == 0

    # MSG_STATE should be 1 (showing message)
    assert mem[labels["MSG_STATE"]] == 1

    # Request_SFX_Interact should be set to 1
    assert mem[labels["REQUEST_SFX_INTERACT"]] == 1


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
    assert mem[labels["INVENTORY_COUNT"]] == 1

    # Position Gerwalt below The Tavern facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 120
    mem[labels["ACTOR_Y"]] = 128
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    # Press Fire button
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0

    # Execute IIS_Update
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # Check results:
    # Item 1 should be removed, Item 5 ("Podarty rachunek") added
    assert mem[labels["INVENTORY_COUNT"]] == 1
    items_in_inv = [mem[labels["INVENTORY_ITEMS"] + i] for i in range(1)]
    assert 1 not in items_in_inv
    assert 5 in items_in_inv

    # Game status should be 1 (Success!) and stage advance requested
    assert mem[labels["GAME_RESULT_STATUS"]] == 1
    assert mem[labels["ENGINE_REQUESTSTAGEADVANCE"]] == 1

    # MSG_STATE should be 1 (showing message)
    assert mem[labels["MSG_STATE"]] == 1


def test_iis_complete_flag_initialization(game_binary) -> None:
    """Verifies that INTERACTIVE_OBJ_COMPLETE is initialized based on items_required."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    complete_base = labels["INTERACTIVE_OBJ_COMPLETE"]
    # TAVERN has required items -> complete flag 1
    assert mem[complete_base + labels["SCREEN_ID_TAVERN"]] == 1
    # FOREST_0_0 (portal, no req items) -> complete flag 0
    assert mem[complete_base + labels["SCREEN_ID_FOREST_0_0"]] == 0


def test_portal_interaction_shows_message_and_transitions(game_binary) -> None:
    """Verifies portal interaction: 1st press displays message_travel, 2nd press triggers screen transition."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    # Set active screen to FOREST_0_0
    mem[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_FOREST_0_0"]

    # In FOREST_0_0.yaml, PORT_2 is at grid x=26, y=0 (w=10, h=3).
    # Position Gerwalt below PORT_2 at grid x=28, y=3 (pixel x = 28*4+48 = 160, pixel y = 3*16+32 = 80)
    # Facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 160
    mem[labels["ACTOR_Y"]] = 80
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    mem[labels["REQ_SCREEN_TRANSITION"]] = 0
    mem[labels["MSG_STATE"]] = 0

    # 1st press: Fire button
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # 1st press result: message_travel shown (MSG_STATE=1), no transition yet
    assert mem[labels["MSG_STATE"]] == 1
    assert mem[labels["REQ_SCREEN_TRANSITION"]] == 0

    # Release Fire button
    mem[labels["INPUTSTATE_TRIG"]] = 1
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # 2nd press: Fire button while MSG_STATE is 1
    mem[labels["INPUTSTATE_TRIG"]] = 0
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # 2nd press result: REQ_SCREEN_TRANSITION=1, targeting HARBOUR (WHITE_FIELD portal entry)
    assert mem[labels["REQ_SCREEN_TRANSITION"]] == 1
    assert mem[labels["NEW_SCREEN_ID"]] == labels["SCREEN_ID_HARBOUR"]


def test_iis_persistent_item_not_removed(game_binary) -> None:
    """Verifies that non-consumable (persistent) items are NOT removed from inventory upon interaction."""
    xex_file, labels = game_binary
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    run_subroutine(cpu, labels["GAME_INIT"], max_steps=100000)

    # Set active screen to TAVERN
    mem[labels["GAME_SCREEN_ID"]] = labels["SCREEN_ID_TAVERN"]

    # Verify Item 2 (miecz na potwory) is persistent in ITEM_FLAGS
    assert mem[labels["ITEM_FLAGS"] + 2] == 0

    # Put Item 2 in scratch memory buffer and point TAVERN requirements to it
    req_buf_addr = 0x0500
    mem[req_buf_addr] = 2  # Requires Item 2 (persistent)
    tavern_id = labels["SCREEN_ID_TAVERN"]
    mem[labels["INTERACTIVE_OBJ_REQ_PTR_LO"] + tavern_id] = req_buf_addr & 0xFF
    mem[labels["INTERACTIVE_OBJ_REQ_PTR_HI"] + tavern_id] = (req_buf_addr >> 8) & 0xFF
    mem[labels["INTERACTIVE_OBJ_REQ_COUNT"] + tavern_id] = 1

    # Add Item 2 to inventory
    cpu.a = 2
    run_subroutine(cpu, labels["INVENTORY_ADD_ITEM"])
    assert mem[labels["INVENTORY_COUNT"]] == 1

    # Position Gerwalt below The Tavern facing UP (ACTOR_DIR = 2)
    mem[labels["ACTOR_X"]] = 120
    mem[labels["ACTOR_Y"]] = 128
    mem[labels["ACTOR_HEIGHT"]] = 16
    mem[labels["ACTOR_DIR"]] = 2

    # Press Fire button
    mem[labels["INPUTSTATE_TRIG"]] = 0
    mem[labels["IIS_FIRE_WAS_PRESSED"]] = 0

    # Execute IIS_Update
    run_subroutine(cpu, labels["IIS_UPDATE"])

    # Item 2 is persistent, so it must still be in inventory!
    # Item 5 ("Podarty rachunek") was also provided by Tavern.
    assert mem[labels["INVENTORY_COUNT"]] == 2
    items_in_inv = [mem[labels["INVENTORY_ITEMS"] + i] for i in range(2)]
    assert 2 in items_in_inv
    assert 5 in items_in_inv


