import argparse
import json
import os
import sys

def generate_asm(json_data, filename):
    out = [f"; Wygenerowano automatycznie z {filename}\n"]
    
    sprites = json_data.get("sprites", [])
    
    for sprite in sprites:
        sid = sprite.get("id", "UNKNOWN")
        height = sprite.get("height", 0)
        color = sprite.get("color", 0)
        frames = sprite.get("frames", [])
        num_frames = len(frames)
        
        out.append(f".def SPRITE_{sid}_HEIGHT = {height}")
        out.append(f".def SPRITE_{sid}_COLOR = {color}")
        out.append(f".def SPRITE_{sid}_FRAMES = {num_frames}")
        out.append("")
        
        for f_idx, frame in enumerate(frames):
            out.append(f"{sid}_FRAME_{f_idx}")
            pixels = frame.get("pixels", [])
            for row in pixels:
                # Replace '1' and '0' with actual MADS binary representation
                out.append(f"    dta %{row}")
            out.append("")
            
        out.append(f"{sid}_PTRS")
        for f_idx in range(num_frames):
            out.append(f"    dta a({sid}_FRAME_{f_idx})")
        out.append("")
        
    return "\n".join(out)

def main():
    parser = argparse.ArgumentParser(description="Convert .sprite.json to MADS .asm")
    parser.add_argument("-i", "--input", required=True, help="Input .sprite.json file")
    parser.add_argument("-o", "--output", required=True, help="Output .asm file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist.")
        sys.exit(1)
        
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        sys.exit(1)
        
    asm_content = generate_asm(data, os.path.basename(args.input))
    
    try:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(asm_content)
    except Exception as e:
        print(f"Error writing output: {e}")
        sys.exit(1)
        
    print(f"Generated {args.output}")

if __name__ == "__main__":
    main()
