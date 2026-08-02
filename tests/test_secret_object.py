import pytest
from pathlib import Path
from py65.devices.mpu6502 import MPU
import test_state_transitions as tst


@pytest.fixture(scope="module")
def game_binary():
    xex_path, lab_path = tst.build_main_binary()
    labels = tst.load_labels(lab_path)
    return xex_path, labels


def test_secret_object_init_resets_flags(game_binary):
    xex_file, labels = game_binary
    cpu = MPU()
    tst.load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Set some flags in SECRET_COLLECTED_FLAGS
    flag_addr = labels["SECRET_COLLECTED_FLAGS"]
    for i in range(10):
        mem[flag_addr + i] = 1

    # Call Secret_Init
    tst.run_subroutine(cpu, labels["SECRET_INIT"])

    # Verify all flags are 0
    for i in range(10):
        assert mem[flag_addr + i] == 0


def test_secret_object_pickup_capacity(game_binary):
    xex_file, labels = game_binary
    cpu = MPU()
    tst.load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    # Setup screen 0 with a secret object present
    screen_id = 0
    mem[labels["GAME_SCREEN_ID"]] = screen_id
    mem[labels["SECRET_OBJ_PRESENT"] + screen_id] = 1
    mem[labels["SECRET_OBJ_X"] + screen_id] = 10
    mem[labels["SECRET_OBJ_Y"] + screen_id] = 5
    mem[labels["SECRET_OBJ_W"] + screen_id] = 2
    mem[labels["SECRET_OBJ_H"] + screen_id] = 2
    mem[labels["SECRET_OBJ_ITEM"] + screen_id] = 7
    mem[labels["SECRET_COLLECTED_FLAGS"] + screen_id] = 0

    # Fill inventory to 8 items
    mem[labels["INVENTORY_COUNT"]] = 8

    # Place Gerwalt on the secret object position (X=10 -> px=10*4+48=88, Y=5 -> py=5*16+32=112)
    mem[labels["ACTOR_X"]] = 88
    mem[labels["ACTOR_Y"]] = 112
    mem[labels["ACTOR_HEIGHT"]] = 16

    # Call Secret_Check_Pickup
    tst.run_subroutine(cpu, labels["SECRET_CHECK_PICKUP"])

    # Should NOT be collected because inventory is full
    assert mem[labels["SECRET_COLLECTED_FLAGS"] + screen_id] == 0
    assert mem[labels["INVENTORY_COUNT"]] == 8


def test_secret_object_pickup_success(game_binary):
    xex_file, labels = game_binary
    cpu = MPU()
    tst.load_xex(xex_file, cpu.memory)
    mem = cpu.memory

    screen_id = 0
    mem[labels["GAME_SCREEN_ID"]] = screen_id
    mem[labels["SECRET_OBJ_PRESENT"] + screen_id] = 1
    mem[labels["SECRET_OBJ_X"] + screen_id] = 10
    mem[labels["SECRET_OBJ_Y"] + screen_id] = 5
    mem[labels["SECRET_OBJ_W"] + screen_id] = 2
    mem[labels["SECRET_OBJ_H"] + screen_id] = 2
    mem[labels["SECRET_OBJ_ITEM"] + screen_id] = 7
    mem[labels["SECRET_COLLECTED_FLAGS"] + screen_id] = 0

    # Inventory has 1 item
    mem[labels["INVENTORY_COUNT"]] = 1

    # Place Gerwalt on the secret object position
    mem[labels["ACTOR_X"]] = 88
    mem[labels["ACTOR_Y"]] = 112
    mem[labels["ACTOR_HEIGHT"]] = 16

    # Call Secret_Check_Pickup
    tst.run_subroutine(cpu, labels["SECRET_CHECK_PICKUP"], max_steps=50000)

    # Item 7 should be added to inventory and flag set to 1
    assert mem[labels["SECRET_COLLECTED_FLAGS"] + screen_id] == 1
    assert mem[labels["INVENTORY_COUNT"]] == 2
    assert mem[labels["INVENTORY_ITEMS"] + 1] == 7
