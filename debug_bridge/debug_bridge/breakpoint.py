"""
Breakpoint debugger workflow logic.
"""

import sys
import os
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .symbols import LabParser
from .session import AltirraSession, parse_mem_dumps, parse_altirra_log
from .errors import TimeoutError, AutomationError

def run_breakpoint_mode(args) -> Dict[str, Any]:
    """Runs the breakpoint mode and returns the parsed JSON dict."""
    start_time = time.time()

    # 1. Resolve ROM path
    rom_path = Path(args.xex)
    if not rom_path.is_file():
        # Exit code 3 for ROM not found
        fatal_error(3, f"ROM file not found: {args.xex}", args.output_json)

    # 2. Resolve Altirra path
    altirra_path = args.altirra or os.environ.get("ALTIRRA_PATH", "Altirra64.exe")
    # If path contains slashes/backslashes, check existence
    if ("/" in altirra_path or "\\" in altirra_path) and not os.path.exists(altirra_path):
        fatal_error(3, f"Emulator not found at: {altirra_path}", args.output_json)

    # 3. Resolve breakpoint label if software bp
    resolved_addr = None
    if args.bp:
        try:
            resolved_addr = LabParser().resolve_label(args.lab, args.bp)
        except Exception as e:
            fatal_error(3, str(e), args.output_json)

    # 4. Initialize session
    try:
        session = AltirraSession(altirra_path, rom_path)
    except Exception as e:
        fatal_error(3, str(e), args.output_json)

    # 5. Build script lines
    lines = []
    if args.lab and os.path.exists(args.lab):
        safe_lab_path = session.safe_path(args.lab)
        lines.append(f'.loadsym "{safe_lab_path}"')

    # Resolve BX conditions
    bx_expr = args.bx
    if args.trap_wsync:
        bx_expr = "write($D40A)"
    elif args.trap_dli:
        bx_expr = "read($FFFA) && (b($D40F) & $80)"
    elif args.trap_vbi:
        bx_expr = "read($FFFA) && (b($D40F) & $40)"

    # Command chain executed when hit
    chain = ["r", "k"] + parse_mem_dumps(args.mem_dump)
    chain.append("d D014 L1")

    if args.hw_regs:
        chain.extend(["d D000 L100", "d D200 L100", "d D300 L10", "d D400 L100"])

    if args.disasm > 0:
        chain.append(f"u pc L{args.disasm}")

    chain.extend([".logclose", ".quit"])
    chain_str = " ".join(chain)

    if args.bp:
        addr = resolved_addr.replace('$', '')
        lines.append(f'bp {addr} "{chain_str}"')
    elif bx_expr:
        lines.append(f'bx {bx_expr} "{chain_str}"')

    lines.append("g")

    # 6. Execute session
    log_content = ""
    try:
        log_content = session.run_script(lines, timeout=args.timeout, warp=args.warp)
    except TimeoutError as e:
        fatal_error(1, str(e), args.output_json)
    except Exception as e:
        fatal_error(4, f"Emulator execution failed: {e}", args.output_json)
    finally:
        session.cleanup()

    # 7. Parse log content
    is_software_bp = bool(args.bp)
    bp_val = resolved_addr if is_software_bp else None
    if is_software_bp and not args.bp.startswith("$"):
        # Put back original label for output representation
        bp_val = args.bp

    try:
        json_obj = parse_altirra_log(
            log_content=log_content,
            is_software_bp=is_software_bp,
            bp_label_or_addr=bp_val,
            bx_cond=bx_expr,
            hw_regs=args.hw_regs,
            disasm_count=args.disasm
        )
    except Exception as e:
        fatal_error(5, f"Log parsing error: {e}", args.output_json)

    # 8. Enrich metadata
    json_obj["timestamp"] = datetime.datetime.now().isoformat()
    json_obj["duration_seconds"] = round(time.time() - start_time, 3)

    return json_obj

def fatal_error(code: int, message: str, output_json_path: Optional[str] = None):
    """Prints the JSON error payload and exits with the given code."""
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
            out_p = Path(output_json_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json_str, encoding="utf-8")
        except Exception:
            pass

    sys.exit(code)
