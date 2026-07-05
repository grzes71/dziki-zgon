# scripts/check_memory.py
import sys
import re

def parse_lab(lab_file):
    symbols = {}
    with open(lab_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    symbols[parts[0]] = int(parts[-1], 16)
                except ValueError:
                    pass
    return symbols

def update_memory_usage(lab_file, md_file):
    symbols = parse_lab(lab_file)
    
    with open(md_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith('| **`$') and '`' in line:
            # Simple heuristic to identify rows to update based on known symbols
            # In a full implementation, you'd map table names to lab symbols.
            # Example: matching row by symbol name column.
            parts = line.split('|')
            if len(parts) > 3:
                name = parts[3].strip().strip('`')
                if name in symbols:
                    addr = symbols[name]
                    # Update start address hex (naive replacement for demo)
                    new_addr_str = f"| **`${addr:04X}`"
                    if not line.startswith(new_addr_str):
                        lines[i] = re.sub(r'\|\s*\*\*\`\$[0-9A-F]{4}\`', new_addr_str + '`', line)
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
