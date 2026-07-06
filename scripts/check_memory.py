# scripts/check_memory.py
import sys
import re

def parse_lab(lab_file):
    symbols = {}
    with open(lab_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    symbols[parts[2]] = int(parts[1], 16)
                except ValueError:
                    pass
    return symbols

def update_memory_usage(lab_file, md_file):
    symbols = parse_lab(lab_file)
    
    with open(md_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    
    # Mapowanie przyjaznych nazw z kolumny tabeli na rzeczywiste etykiety w .lab
    symbol_map = {
        'start (jump)': 'START',
        'disable_basic_loader': 'DISABLE_BASIC_LOADER',
        'pmg.asm': 'PMG_CLEAR_ALL',
        'rle.asm': 'RLE_DEPACK',
        'title.asm': 'ROW_OFFSETS_LO',
        'fire_released_flag': 'FIRE_RELEASED_FLAG',
        'story.asm': 'STORY_INIT',
        'game_fire_released': 'GAME_FIRE_RELEASED',
        'game.asm': 'GAME_STAGE',
        'gameover_fire_released': 'GAMEOVER_FIRE_RELEASED',
        'gameover.asm': 'DLI_GAMEOVER',
        'main.asm': 'SYSTEM_INIT',
        'GO_TEXT_Data': 'GO_TEXT_DATA',
        'StoryText_Data': 'STORYTEXT_DATA',
        'TitleFooterROM': 'TITLEFOOTERROM',
        'DzikizgonData': 'DZIKIZGONDATA',
        'MoonData': 'MOONDATA',
        'VRAM_ARENA': 'VRAM_ARENA',
        'FOOTER_ADDR': 'FOOTER_ADDR',
        'font.asm': 'FONT_DATA',
        'game_font.asm': 'GAME_FONT_DATA',
        'ROM_DATA': 'ROM_DATA',
        'title_audio.asm': 'TITLE_AUDIO',
        'MISSILES': 'MISSILES',
        'PLAYER0': 'PLAYER0',
        'PLAYER1': 'PLAYER1',
        'PLAYER2': 'PLAYER2',
        'PLAYER3': 'PLAYER3',
        'GAME_CHARSET': 'GAME_CHARSET',
        'rmtplayr.asm': 'RMT_PLAYER',
        'title_music.asm': 'TITLE_MUSIC',
    }

    for i, line in enumerate(lines):
        if line.startswith('| **`$') and '`' in line:
            parts = line.split('|')
            if len(parts) > 3:
                name = parts[3].strip().strip('`')
                
                symbol_to_check = symbol_map.get(name, name)
                
                if symbol_to_check in symbols:
                    addr = symbols[symbol_to_check]
                    # Update start address hex (naive replacement for demo)
                    new_addr_str = f"| **`${addr:04X}`"
                    if not line.startswith(new_addr_str):
                        lines[i] = re.sub(r'\|\s*\*\*\`\$[0-9A-F]{4}\`', new_addr_str, line)
                        updated = True

    if updated:
        with open(md_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("MEMORY_USAGE.md updated.")
    else:
        print("MEMORY_USAGE.md is up-to-date.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_memory.py <game.lab> <MEMORY_USAGE.md>")
        sys.exit(1)
    update_memory_usage(sys.argv[1], sys.argv[2])
