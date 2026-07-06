import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU

def compile_harness():
    tests_dir = Path(__file__).parent
    asm_file = tests_dir / "world_renderer_test.asm"
    out_xex = tests_dir / "world_renderer_test.xex"
    out_lab = tests_dir / "world_renderer_test.lab"
    
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

def test_build_screen_single_tile(harness):
    xex_file, labels = harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # Adresy
    SCREEN_PTR_Z = labels["SCREEN_PTR"]
    GAME_SCREEN_ID_Z = labels["GAME_SCREEN_ID"]
    SCREEN_POINTERS_LO = labels["SCREEN_POINTERS_LO"]
    SCREEN_POINTERS_HI = labels["SCREEN_POINTERS_HI"]
    OBJ_SIZE = labels["OBJ_SIZE"]
    OBJ_TILES_LO = labels["OBJ_TILES_LO"]
    OBJ_TILES_HI = labels["OBJ_TILES_HI"]
    GAME_SCREEN_A5 = labels["GAME_SCREEN_A5"]
    SCREEN_DATA = labels["SCREEN_DATA"]
    TILES_DATA = labels["TILES_DATA"]
    
    # Wyczyść VRAM (400 bajtów dla ANTIC 5)
    for i in range(400):
        cpu.memory[GAME_SCREEN_A5 + i] = 0
        
    # GAME_SCREEN_ID = 0
    cpu.memory[GAME_SCREEN_ID_Z] = 0
    
    # Setup SCREEN_POINTERS dla mapy 0 na adres SCREEN_DATA
    cpu.memory[SCREEN_POINTERS_LO] = SCREEN_DATA & 0xFF
    cpu.memory[SCREEN_POINTERS_HI] = (SCREEN_DATA >> 8) & 0xFF
    
    # Setup SCREEN_DATA: 1 obiekt (kod=1, x=2, y=1)
    cpu.memory[SCREEN_DATA] = 1     # Liczba obiektów
    cpu.memory[SCREEN_DATA+1] = 1   # Kod obiektu
    cpu.memory[SCREEN_DATA+2] = 2   # X
    cpu.memory[SCREEN_DATA+3] = 1   # Y
    
    # Setup OBJ_SIZE: (W-1)<<4 | (H-1) -> 0x00 dla rozmiaru 1x1
    cpu.memory[OBJ_SIZE + 1] = 0x00
    
    # Setup OBJ_TILES wskaźnik kafelków dla kodu 1
    cpu.memory[OBJ_TILES_LO + 1] = TILES_DATA & 0xFF
    cpu.memory[OBJ_TILES_HI + 1] = (TILES_DATA >> 8) & 0xFF
    
    # Setup TILES_DATA: kafelek = 42
    cpu.memory[TILES_DATA] = 42
    
    # Wywołanie (sp reset na dół stosu by zapobiec błędom)
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST"]
    
    max_steps = 1000
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK (koniec harnessu)
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Nieskończona pętla w 6502!"
    
    # Asercja wirtualnego VRAMu (Szerokość 40. Y=1, X=2 -> indeks 42)
    assert cpu.memory[GAME_SCREEN_A5 + 42] == 42, "Brak kafelka na właściwej pozycji VRAM"
    # Sprawdzenie czy dookoła nic nie ma
    assert cpu.memory[GAME_SCREEN_A5 + 41] == 0
    assert cpu.memory[GAME_SCREEN_A5 + 43] == 0
