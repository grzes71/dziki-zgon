#!/usr/bin/env python3
"""
Altirra Auto-Debugger Basic (v3)
Automated debugging of 6502 code within the Altirra emulator.
"""

import argparse
import atexit
import base64
import datetime
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import time

# --- Constants & Regex Patterns ---

# Example: (6502) PC=4000 A=00 X=FF Y=10 S=FD P=34 (NV-BDIZC: 00110100)  A9 FF       LDA #$FF
REGISTER_PATTERN = re.compile(
    r"PC=([0-9A-F]+)\s+A=([0-9A-F]+)\s+X=([0-9A-F]+)\s+Y=([0-9A-F]+)\s+S=([0-9A-F]+)\s+P=([0-9A-F]+)",
    re.IGNORECASE
)
FLAGS_PATTERN = re.compile(r"NV-BDIZC:\s*([01]{8})", re.IGNORECASE)
INSTRUCTION_PATTERN = re.compile(r"\)\s*(?:[0-9A-F]{2}\s*)+\s+(.+)$", re.IGNORECASE)

# Example: 4000: A9 FF 8D 00 D0 ...
HEXDUMP_PATTERN = re.compile(r"^([0-9A-F]{4}):((?:\s[0-9A-F]{2})+)", re.MULTILINE | re.IGNORECASE)

# Example output from `k`: lines of hex addresses
CALL_STACK_PATTERN = re.compile(r"^([0-9A-F]{4})", re.MULTILINE | re.IGNORECASE)

TEMP_FILES = []

# --- Cleanup ---

def cleanup():
    """Removes temporary files and ensures no zombie Altirra process remains."""
    for tf in TEMP_FILES:
        try:
            if os.path.exists(tf):
                os.remove(tf)
        except Exception:
            pass

atexit.register(cleanup)

# --- Helper Functions ---

def fatal_error(code: int, message: str, print_json: bool = True, output_json_path: str = None):
    """Exits the tool with the specified code and JSON error payload."""
    if print_json:
        payload = {
            "tool": "altirra-auto-debugger-basic",
            "version": "3.0",
            "status": "error",
            "error": message,
            "exit_code": code,
            "timestamp": datetime.datetime.now().isoformat()
        }
        json_str = json.dumps(payload, indent=4)
        print(json_str)
        if output_json_path:
            try:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            except Exception:
                pass
    else:
        print(f"Error: {message}", file=sys.stderr)
    
    sys.exit(code)

def log_verbose(msg: str, is_verbose: bool):
    if is_verbose:
        print(f"[INFO] {msg}", file=sys.stderr)

# --- Core Modules ---

def parse_args():
    parser = argparse.ArgumentParser(description="Altirra Auto-Debugger Basic")
    parser.add_argument("--rom", required=True, help="Path to compiled .xex or .atr file")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bp", help="Software breakpoint: hex address (e.g. $4000) or label name")
    group.add_argument("--bx", help="Hardware breakpoint: Altirra expression (e.g. write($D40E))")
    
    parser.add_argument("--mem-dump", action="append", default=[], help="Memory dump range(s). Format: $ADDR:L$LEN")
    parser.add_argument("--altirra", help="Path to Altirra64.exe")
    parser.add_argument("--timeout", type=int, default=15, help="Wall-clock timeout in seconds (default: 15)")
    parser.add_argument("--lab-file", help="Path to MADS .lab labels file")
    parser.add_argument("--output-json", help="Write JSON result to file in addition to stdout")
    parser.add_argument("--verbose", action="store_true", help="Print progress messages to stderr")
    parser.add_argument("--warp", action="store_true", help="Runs the emulator without frame limits (/warp)")
    
    return parser.parse_args()

def resolve_label(lab_path: str, label: str) -> str:
    """Resolves a label name to a hex address using a MADS .lab file."""
    if label.startswith("$"):
        return label
    
    if not lab_path or not os.path.exists(lab_path):
        raise FileNotFoundError(f"Label '{label}' provided, but lab file '{lab_path}' is missing or invalid.")
    
    with open(lab_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        # Assignment format: LABEL = $ADDR
        if "=" in line:
            parts = line.split("=")
            if len(parts) == 2 and parts[0].strip() == label:
                return parts[1].strip()
        else:
            # Table format: usually ADDR \t LABEL \t ...
            parts = line.split()
            if len(parts) >= 2 and parts[1] == label:
                return "$" + parts[0]
                
    raise ValueError(f"Label '{label}' not found in '{lab_path}'.")

def parse_mem_dumps(mem_dumps: list) -> list:
    """Parses '$ADDR:L$LEN' into Altirra command format 'd ADDR LLEN'."""
    commands = []
    for md in mem_dumps:
        md = md.replace('$', '') # Remove all $
        parts = md.split(':')
        if len(parts) == 2:
            commands.append(f"d {parts[0]} {parts[1]}")
    return commands

def generate_atdbg(args, resolved_addr: str) -> tuple[str, str]:
    """Generates the .atdbg script and returns paths to (script, log)."""
    fd_script, script_path = tempfile.mkstemp(suffix=".atdbg", text=True)
    fd_log, log_path = tempfile.mkstemp(suffix=".log", text=True)
    os.close(fd_script)
    os.close(fd_log)
    
    TEMP_FILES.extend([script_path, log_path])
    
    # Escape paths for Altirra string literals
    safe_log_path = log_path.replace("\\", "/")
    
    lines = []
    lines.append(f'.logopen "{safe_log_path}"')
    
    if args.lab_file and os.path.exists(args.lab_file):
        safe_lab_path = args.lab_file.replace("\\", "/")
        lines.append(f'.loadsym "{safe_lab_path}"')
        
    # Command chain
    chain = ["r", "k"] + parse_mem_dumps(args.mem_dump) + [".logclose", ".quit"]
    chain_str = " ".join(chain)
    
    if args.bp:
        addr = resolved_addr.replace('$', '')
        lines.append(f'bp {addr} "{chain_str}"')
    elif args.bx:
        lines.append(f'bx {args.bx} "{chain_str}"')
        
    lines.append("g")
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
        
    return script_path, log_path

def run_altirra(altirra_path: str, rom_path: str, atdbg_path: str, timeout: int, warp: bool):
    """Executes Altirra in a subprocess."""
    cmd = [altirra_path, "/debug", "/debugcmd", f".source {atdbg_path}"]
    if warp:
        cmd.append("/warp")
    cmd.append(rom_path)
    
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise TimeoutError("Timeout - breakpoint not reached")

def parse_log(log_path: str, args, resolved_addr: str) -> dict:
    """Parses the generated Altirra log file into the JSON contract."""
    with open(log_path, 'r', encoding='utf-8') as f:
        log_content = f.read()
        
    if not log_content.strip():
        raise ValueError("Log file is empty. Breakpoint might not have hit or crashed.")
        
    result = {
        "tool": "altirra-auto-debugger-basic",
        "version": "3.0",
        "status": "ok",
        "breakpoint": {},
        "cpu": {},
        "call_stack": [],
        "memory_dumps": [],
    }
    
    if args.bp:
        result["breakpoint"]["type"] = "software"
        result["breakpoint"]["address"] = resolved_addr
        if not args.bp.startswith("$"):
            result["breakpoint"]["label"] = args.bp
    else:
        result["breakpoint"]["type"] = "hardware"
        result["breakpoint"]["condition"] = args.bx
        
    # 1. Parse CPU Registers
    reg_match = REGISTER_PATTERN.search(log_content)
    if reg_match:
        result["cpu"]["PC"] = int(reg_match.group(1), 16)
        result["cpu"]["A"] = int(reg_match.group(2), 16)
        result["cpu"]["X"] = int(reg_match.group(3), 16)
        result["cpu"]["Y"] = int(reg_match.group(4), 16)
        result["cpu"]["S"] = int(reg_match.group(5), 16)
        # P is available as hex, but we parse the explicit flags bitmask below
    else:
        raise ValueError("Could not find CPU registers in log.")
        
    # 2. Parse Flags
    flags_match = FLAGS_PATTERN.search(log_content)
    if flags_match:
        bits = flags_match.group(1) # e.g. 00110100 for NV-BDIZC
        if len(bits) == 8:
            result["cpu"]["flags"] = {
                "N": bits[0] == '1',
                "V": bits[1] == '1',
                "B": bits[3] == '1',
                "D": bits[4] == '1',
                "I": bits[5] == '1',
                "Z": bits[6] == '1',
                "C": bits[7] == '1'
            }
            
    # 3. Parse Instruction
    inst_match = INSTRUCTION_PATTERN.search(log_content)
    if inst_match:
        result["cpu"]["current_instruction"] = inst_match.group(1).strip()
        
    # 4. Parse Call Stack
    lines = log_content.splitlines()
    parsing_k = False
    for line in lines:
        if line.startswith("Altirra>") and " k" in line:
            parsing_k = True
            continue
        elif line.startswith("Altirra>"):
            parsing_k = False
            
        if parsing_k:
            stack_match = re.match(r"^([0-9A-F]{4})", line, re.IGNORECASE)
            if stack_match:
                result["call_stack"].append("$" + stack_match.group(1).upper())
                
    # 5. Parse Hexdumps
    matches = list(HEXDUMP_PATTERN.finditer(log_content))
    if matches:
        blocks = []
        current_block = {"start_addr": None, "bytes": bytearray()}
        last_addr = -1
        
        for m in matches:
            addr = int(m.group(1), 16)
            hex_str = m.group(2).replace(" ", "")
            row_bytes = bytes.fromhex(hex_str)
            
            if current_block["start_addr"] is None:
                current_block["start_addr"] = addr
                current_block["bytes"].extend(row_bytes)
                last_addr = addr + len(row_bytes)
            elif addr == last_addr:
                current_block["bytes"].extend(row_bytes)
                last_addr += len(row_bytes)
            else:
                blocks.append(current_block)
                current_block = {"start_addr": addr, "bytes": bytearray(row_bytes)}
                last_addr = addr + len(row_bytes)
                
        if current_block["start_addr"] is not None:
            blocks.append(current_block)
            
        for b in blocks:
            hx = b["bytes"].hex(" ").upper()
            result["memory_dumps"].append({
                "address": f"${b['start_addr']:04X}",
                "length": len(b["bytes"]),
                "hex": hx,
                "raw_base64": base64.b64encode(b["bytes"]).decode('ascii')
            })

    return result

# --- Main ---

def main():
    if platform.system() != "Windows":
        fatal_error(9, "Unsupported platform: This tool requires Windows.", print_json=False)

    args = parse_args()
    
    start_time = time.time()
    log_verbose("Starting altirra-auto-debugger-basic...", args.verbose)
    
    if not os.path.exists(args.rom):
        fatal_error(3, f"ROM file not found: {args.rom}", output_json_path=args.output_json)
        
    altirra_path = args.altirra or os.environ.get("ALTIRRA_PATH", "Altirra64.exe")
    if ("/" in altirra_path or "\\" in altirra_path) and not os.path.exists(altirra_path):
        fatal_error(3, f"Emulator not found at: {altirra_path}", output_json_path=args.output_json)
        
    resolved_addr = None
    if args.bp:
        try:
            resolved_addr = resolve_label(args.lab_file, args.bp)
            log_verbose(f"Resolved breakpoint: {args.bp} -> {resolved_addr}", args.verbose)
        except Exception as e:
            fatal_error(3, str(e), output_json_path=args.output_json)

    log_verbose("Generating .atdbg script...", args.verbose)
    try:
        script_path, log_path = generate_atdbg(args, resolved_addr)
    except Exception as e:
        fatal_error(5, f"Failed to generate script: {e}", output_json_path=args.output_json)
        
    log_verbose(f"Running Altirra (timeout: {args.timeout}s)...", args.verbose)
    try:
        rc, stdout, stderr = run_altirra(altirra_path, args.rom, script_path, args.timeout, args.warp)
        if rc != 0:
            fatal_error(4, f"Altirra exited with code {rc}.", output_json_path=args.output_json)
    except TimeoutError as e:
        fatal_error(1, str(e), output_json_path=args.output_json)
    except Exception as e:
        fatal_error(4, f"Emulator execution failed: {e}", output_json_path=args.output_json)
        
    log_verbose("Parsing output log...", args.verbose)
    try:
        json_obj = parse_log(log_path, args, resolved_addr)
    except Exception as e:
        fatal_error(5, f"Log parsing error: {e}", output_json_path=args.output_json)
        
    json_obj["timestamp"] = datetime.datetime.now().isoformat()
    json_obj["duration_seconds"] = round(time.time() - start_time, 3)
    
    json_str = json.dumps(json_obj, indent=4)
    print(json_str)
    
    if args.output_json:
        try:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                f.write(json_str)
        except Exception as e:
            log_verbose(f"Warning: Failed to write output JSON file: {e}", args.verbose)
            
    log_verbose("Done.", args.verbose)
    sys.exit(0)

if __name__ == "__main__":
    main()
