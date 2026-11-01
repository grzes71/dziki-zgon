import argparse
import json
import os
import sys

def generate_asm(json_data, filename):
    out = [f"; Wygenerowano automatycznie z {filename}\n"]
    
    sprites = json_data.get("sprites", [])
    
    for sprite in sprites:
        sid = sprite.get("id", "UNKNOWN")
        if isinstance(sid, int) or (isinstance(sid, str) and (sid.isdigit() or (sid and not sid[0].isalpha() and sid[0] != '_'))):
            desc = str(sprite.get("description", "")).strip()
            if desc and (desc[0].isalpha() or desc[0] == '_'):
                sid = desc
        height = sprite.get("height", 0)
        color = sprite.get("color", 0)
        color2 = sprite.get("color2", 0)
        color_mode = sprite.get("color_mode", 2)
        frames = sprite.get("frames", [])
        num_frames = len(frames)
        
        # Detect if any pixel is '2' or '3'
        has_multi_color = (color_mode == 4) or any(
            any(c in ('2', '3') for c in frame.get("pixels", []))
            for frame in frames
        )

        if has_multi_color:
            color_mix = (color | color2) & 0xFF
            out.append(f".def SPRITE_{sid}_HEIGHT = {height}")
            out.append(f".def SPRITE_{sid}_COLOR = {color}")
            out.append(f".def SPRITE_{sid}_COLOR0 = {color}")
            out.append(f".def SPRITE_{sid}_COLOR1 = {color2}")
            out.append(f".def SPRITE_{sid}_COLOR_MIX = {color_mix}")
            out.append(f".def SPRITE_{sid}_FRAMES = {num_frames}")
            out.append(f".def SPRITE_{sid}_IS_4COLOR = 1")
            out.append("")

            # Export Layer P0 frames (Player A)
            for f_idx, frame in enumerate(frames):
                out.append(f"{sid}_P0_FRAME_{f_idx}")
                pixels = frame.get("pixels", [])
                for row in pixels:
                    p0_row = "".join("1" if c in ('1', '3') else "0" for c in row)
                    out.append(f"    dta %{p0_row}")
                out.append("")

            # Export Layer P1 frames (Player B)
            for f_idx, frame in enumerate(frames):
                out.append(f"{sid}_P1_FRAME_{f_idx}")
                pixels = frame.get("pixels", [])
                for row in pixels:
                    p1_row = "".join("1" if c in ('2', '3') else "0" for c in row)
                    out.append(f"    dta %{p1_row}")
                out.append("")

            # Pointers tables
            out.append(f"{sid}_P0_PTRS")
            for f_idx in range(num_frames):
                out.append(f"    dta a({sid}_P0_FRAME_{f_idx})")
            out.append("")

            out.append(f"{sid}_P1_PTRS")
            for f_idx in range(num_frames):
                out.append(f"    dta a({sid}_P1_FRAME_{f_idx})")
            out.append("")

            # Default alias for P0
            out.append(f"{sid}_PTRS = {sid}_P0_PTRS")
            out.append("")
        else:
            out.append(f".def SPRITE_{sid}_HEIGHT = {height}")
            out.append(f".def SPRITE_{sid}_COLOR = {color}")
            out.append(f".def SPRITE_{sid}_FRAMES = {num_frames}")
            out.append(f".def SPRITE_{sid}_IS_4COLOR = 0")
            out.append("")
            
            for f_idx, frame in enumerate(frames):
                out.append(f"{sid}_FRAME_{f_idx}")
                pixels = frame.get("pixels", [])
                for row in pixels:
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
