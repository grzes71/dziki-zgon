"""
Common Altirra automation foundation, process runner, script builder, and log parser.
"""

import os
import re
import sys
import time
import base64
import datetime
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from .errors import EmulatorLaunchError, AutomationError, TimeoutError

# --- Constants & Regex Patterns ---
REGISTER_PATTERN = re.compile(
    r"PC=([0-9A-F]+)\s+A=([0-9A-F]+)\s+X=([0-9A-F]+)\s+Y=([0-9A-F]+)\s+S=([0-9A-F]+)\s+P=([0-9A-F]+)",
    re.IGNORECASE
)
FLAGS_PATTERN = re.compile(r"NV-BDIZC:\s*([01]{8})", re.IGNORECASE)
INSTRUCTION_PATTERN = re.compile(r"\)\s*(?:[0-9A-F]{2}\s*)+\s+(.+)$", re.MULTILINE | re.IGNORECASE)

HEXDUMP_PATTERN = re.compile(r"^([0-9A-F]{4}):((?:\s+[0-9A-F]{2})+)\s+\|.*\|[\r\n]", re.MULTILINE | re.IGNORECASE)

DISASM_PATTERN = re.compile(r"^([0-9A-F]{4}):\s*([0-9A-F]{2}(?:\s+[0-9A-F]{2}){0,2})\s+(.+)$", re.IGNORECASE)
CALL_STACK_PATTERN = re.compile(r"^([0-9A-F]{4})", re.MULTILINE | re.IGNORECASE)


def parse_mem_dumps(mem_dumps: List[str]) -> List[str]:
    """Parses '$ADDR:L$LEN' into Altirra command format 'd ADDR LLEN'."""
    commands = []
    for md in mem_dumps:
        md = md.replace('$', '')  # Remove all $
        parts = md.split(':')
        if len(parts) == 2:
            commands.append(f"d {parts[0]} {parts[1]}")
    return commands


def parse_altirra_log(log_content: str, is_software_bp: bool, bp_label_or_addr: Optional[str], bx_cond: Optional[str], hw_regs: bool = False, disasm_count: int = 0) -> Dict[str, Any]:
    """Parses Altirra log file content into a structured dict payload."""
    if not log_content.strip():
        raise AutomationError("Log file is empty. Breakpoint might not have hit or crashed.")

    result: Dict[str, Any] = {
        "tool": "altirra-auto-debugger-basic",
        "version": "3.0",
        "status": "ok",
        "breakpoint": {},
        "cpu": {},
        "call_stack": [],
        "memory_dumps": [],
    }

    if is_software_bp:
        result["breakpoint"]["type"] = "software"
        result["breakpoint"]["address"] = bp_label_or_addr
        if bp_label_or_addr and not bp_label_or_addr.startswith("$"):
            result["breakpoint"]["label"] = bp_label_or_addr
    else:
        result["breakpoint"]["type"] = "hardware"
        result["breakpoint"]["condition"] = bx_cond

    # 1. Parse CPU Registers
    reg_match = REGISTER_PATTERN.search(log_content)
    if reg_match:
        result["cpu"]["PC"] = int(reg_match.group(1), 16)
        result["cpu"]["A"] = int(reg_match.group(2), 16)
        result["cpu"]["X"] = int(reg_match.group(3), 16)
        result["cpu"]["Y"] = int(reg_match.group(4), 16)
        result["cpu"]["S"] = int(reg_match.group(5), 16)
    else:
        raise AutomationError("Could not find CPU registers in log.")

    # 2. Parse Flags
    flags_match = FLAGS_PATTERN.search(log_content)
    if flags_match:
        bits = flags_match.group(1)
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

    # 4. Parse Call Stack & Disassembly
    lines = log_content.splitlines()
    parsing_k = False
    parsing_u = False
    if disasm_count > 0:
        result["cpu"]["disassembly"] = []

    for line in lines:
        if line.startswith("Altirra>") and " k" in line:
            parsing_k = True
            parsing_u = False
            continue
        elif line.startswith("Altirra>") and " u " in line:
            parsing_u = True
            parsing_k = False
            continue
        elif line.startswith("Altirra>"):
            parsing_k = False
            parsing_u = False

        if parsing_k:
            stack_match = CALL_STACK_PATTERN.match(line)
            if stack_match:
                result["call_stack"].append("$" + stack_match.group(1).upper())
        elif parsing_u and disasm_count > 0:
            d_match = DISASM_PATTERN.match(line)
            if d_match:
                result["cpu"]["disassembly"].append({
                    "address": f"${d_match.group(1).upper()}",
                    "bytes": d_match.group(2).strip(),
                    "instruction": d_match.group(3).strip()
                })

    # 5. Parse Hexdumps
    matches = list(HEXDUMP_PATTERN.finditer(log_content + "\n"))
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
            dump_obj = {
                "address": f"${b['start_addr']:04X}",
                "length": len(b["bytes"]),
                "hex": hx,
                "raw_base64": base64.b64encode(b["bytes"]).decode('ascii')
            }
            if b['start_addr'] == 0xD014 and len(b["bytes"]) == 1:
                result["tv_system"] = "NTSC" if (b["bytes"][0] & 0x0E) == 0x0E else "PAL"
            elif hw_regs and b['start_addr'] == 0xD000 and len(b["bytes"]) == 256:
                result.setdefault("hardware_registers", {})["GTIA"] = dump_obj
            elif hw_regs and b['start_addr'] == 0xD200 and len(b["bytes"]) == 256:
                result.setdefault("hardware_registers", {})["POKEY"] = dump_obj
            elif hw_regs and b['start_addr'] == 0xD300 and len(b["bytes"]) == 16:
                result.setdefault("hardware_registers", {})["PIA"] = dump_obj
            elif hw_regs and b['start_addr'] == 0xD400 and len(b["bytes"]) == 256:
                result.setdefault("hardware_registers", {})["ANTIC"] = dump_obj
            else:
                result["memory_dumps"].append(dump_obj)

    return result


class AltirraSession:
    def __init__(self, altirra_path: str | Path, rom_path: str | Path):
        self.altirra_path = Path(altirra_path)
        self.rom_path = Path(rom_path)
        self.temp_files: List[Path] = []

        if not self.altirra_path.is_file():
            raise EmulatorLaunchError(f"Emulator executable not found: {self.altirra_path}")
        if not self.rom_path.is_file():
            raise EmulatorLaunchError(f"ROM file not found: {self.rom_path}")

    def make_temp_file(self, suffix: str) -> Path:
        fd, path_str = tempfile.mkstemp(suffix=suffix, text=True)
        os.close(fd)
        path = Path(path_str)
        self.temp_files.append(path)
        return path

    def safe_path(self, path: str | Path) -> str:
        return str(Path(path).absolute()).replace('\\', '/')

    def run_script(self, script_lines: List[str], timeout: float, warp: bool = False, wait_for_file: Optional[Path] = None) -> str:
        script_path = self.make_temp_file(".atdbg")
        log_path = self.make_temp_file(".log")

        safe_log_path = self.safe_path(log_path)
        full_script = [
            f'.logopen "{safe_log_path}"',
            *script_lines
        ]

        script_path.write_text("\n".join(full_script) + "\n", encoding="utf-8")
        safe_script_path = self.safe_path(script_path)

        cmd = [
            str(self.altirra_path),
            "/debug",
            "/debugcmd",
            f".source \"{safe_script_path}\""
        ]
        if warp:
            cmd.append("/warp")
        cmd.append(str(self.rom_path))

        proc = None
        try:
            if wait_for_file:
                # Polling wait mode (used for snapshot mode)
                proc = subprocess.Popen(cmd)
                start_time = time.time()
                while True:
                    if wait_for_file.is_file():
                        # Give file handles a tiny moment to flush
                        time.sleep(0.5)
                        proc.terminate()
                        break
                    if time.time() - start_time > timeout:
                        proc.terminate()
                        raise TimeoutError("Timeout waiting for emulator to generate artifacts.")
                    if proc.poll() is not None:
                        # Process exited on its own
                        break
                    time.sleep(0.1)
                
                if log_path.is_file():
                    return log_path.read_text(encoding="utf-8")
                return ""
            else:
                # Synchronous wait mode (used for breakpoint mode)
                # Ensure we run using subprocess.run under a timeout
                result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
                if result.returncode != 0:
                    raise AutomationError(f"Altirra exited with code {result.returncode}.")
                
                if log_path.is_file():
                    return log_path.read_text(encoding="utf-8")
                return ""
        except subprocess.TimeoutExpired:
            if proc:
                proc.terminate()
            raise TimeoutError("Timeout - breakpoint not reached")
        except Exception as e:
            if proc and proc.poll() is None:
                proc.terminate()
            raise e

    def cleanup(self):
        for tf in self.temp_files:
            try:
                if tf.is_file():
                    tf.unlink()
            except Exception:
                pass
        self.temp_files.clear()

    def __del__(self):
        self.cleanup()
