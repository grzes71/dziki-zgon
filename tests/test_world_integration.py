import pytest
from pathlib import Path
import subprocess
from py65.devices.mpu6502 import MPU
import sys

# Dodaj główny katalog do PYTHONPATH aby zaimportować world_builder
sys.path.insert(0, str(Path(__file__).parent.parent))
from world_builder.parser import parse_world_dir

def build_harness():
    root_dir = Path(__file__).parent.parent
    tests_dir = Path(__file__).parent
    
    # Upewnij się, że dane świata są aktualne
    subprocess.run(["make", "world"], cwd=root_dir, check=True)
    
    asm_file = tests_dir / "world_integration_test.asm"
    out_xex = tests_dir / "world_integration_test.xex"
    out_lab = tests_dir / "world_integration_test.lab"
    
    mads_exe = "c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe"
    subprocess.run([mads_exe, str(asm_file), f"-o:{out_xex}", f"-t:{out_lab}"], cwd=tests_dir, check=True)
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

def compute_expected_vram(world_dir: Path, region_id: str, screen_id: str):
    world = parse_world_dir(world_dir)
    vram = [0] * 480
    
    # Przygotuj słownik obiektów do szybkiego dostępu (uwaga: szukamy w oryginalnym yaml lub modelu Pydantic)
    # world.objects to lista obiektów GameObject z pydantic.
    objects_dict = {obj.id: obj for obj in world.objects}
    
    # Znajdź ekran
    target_screen = None
    for region in world.regions:
        if region.id == region_id:
            for screen in region.screens:
                if screen.id == screen_id:
                    target_screen = screen
                    break
            if target_screen:
                break
                
    assert target_screen is not None, f"Nie znaleziono ekranu {screen_id} w regionie {region_id}"
    
    for obj_inst in target_screen.objects:
        obj_def = objects_dict.get(obj_inst.object)
        if not obj_def:
            continue
            
        w = obj_def.size.width
        h = obj_def.size.height
        tiles = obj_def.tiles
        base_x = obj_inst.x
        base_y = obj_inst.y
        
        for ty in range(h):
            for tx in range(w):
                idx = ty * w + tx
                if idx < len(tiles):
                    tile = tiles[idx]
                    
                    # Nanieś na vram (zabezpieczenie granic tak jak robi to kompilator)
                    screen_x = base_x + tx
                    screen_y = base_y + ty
                    
                    if screen_x < 40 and screen_y < 12:
                        vram[screen_y * 40 + screen_x] = tile
                        
    return vram

@pytest.fixture(scope="module")
def integration_harness():
    xex, lab = build_harness()
    labels = load_labels(lab)
    return xex, labels

def test_full_screen_rendering(integration_harness):
    xex_file, labels = integration_harness
    cpu = MPU()
    load_xex(xex_file, cpu.memory)
    
    # 1. Zbuduj VRAM oczekiwany w oparciu o parser Pythona (Screen SWAMP.yaml)
    world_dir = Path(__file__).parent.parent / "world"
    expected_vram = compute_expected_vram(world_dir, "WHITE_FIELD", "SWAMP")
    
    # 2. Skonfiguruj 6502
    GAME_SCREEN_A5 = labels["GAME_SCREEN_A5"]
    GAME_SCREEN_ID_Z = labels["GAME_SCREEN_ID"]
    
    # Wyczyść wirtualny VRAM przed testem (upewnij się że zaczynamy z czystą kartą)
    for i in range(480):
        cpu.memory[GAME_SCREEN_A5 + i] = 0
        
    # Ustaw ekran (MADS exportuje labele globalne)
    # Z world.inc mamy SCREEN_ID_SWAMP
    assert "SCREEN_ID_SWAMP" in labels, "Brak labela SCREEN_ID_SWAMP"
    cpu.memory[GAME_SCREEN_ID_Z] = labels["SCREEN_ID_SWAMP"]
    
    # Wywołanie procedury
    cpu.sp = 0xFF
    cpu.pc = labels["START_TEST"]
    
    max_steps = 100000 # Duża mapa = dużo kroków (kilkadziesiąt tysięcy instrukcji)
    steps = 0
    while steps < max_steps:
        if cpu.memory[cpu.pc] == 0x00: # BRK
            break
        cpu.step()
        steps += 1
        
    assert steps < max_steps, "Przekroczono limit kroków procesora (nieskończona pętla?)"
    
    # 3. Weryfikacja wynikowa 480 bajtów
    actual_vram = [cpu.memory[GAME_SCREEN_A5 + i] for i in range(480)]
    
    errors = []
    for i in range(480):
        if actual_vram[i] != expected_vram[i]:
            x = i % 40
            y = i // 40
            errors.append(f"Diff @({x},{y}) [idx {i}]: Oczekiwano {expected_vram[i]}, Otrzymano {actual_vram[i]}")
            
    assert not errors, "Błędy VRAM:\n" + "\n".join(errors[:10]) # pokaz pierwszych 10
