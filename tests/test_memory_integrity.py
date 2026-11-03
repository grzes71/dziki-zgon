from pathlib import Path
from scripts.verify_memory_integrity import verify_memory_integrity


def test_memory_integrity_validation():
    root = Path(__file__).resolve().parent.parent
    mem_json = root / "reports" / "portal" / "memory.json"
    zp_asm = root / "zeropage.asm"
    xex_bin = root / "dziki_zgon.xex"

    assert mem_json.exists(), "reports/portal/memory.json must exist before testing"
    assert zp_asm.exists(), "zeropage.asm must exist"

    passed = verify_memory_integrity(mem_json, zp_asm, xex_bin if xex_bin.exists() else None)
    assert passed is True, "Memory integrity validation failed"

