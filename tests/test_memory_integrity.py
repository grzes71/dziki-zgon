from pathlib import Path
from scripts.export_portal_data import PortalDataPipeline
from scripts.verify_memory_integrity import verify_memory_integrity


def test_memory_integrity_validation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = tmp_path / "portal"
    pipeline = PortalDataPipeline(root_dir=root, output_dir=out_dir)
    mem_data = pipeline.generate_memory_data()

    mem_json = out_dir / "memory.json"
    mem_json.write_text(mem_data.model_dump_json(indent=2), encoding="utf-8")

    zp_asm = root / "zeropage.asm"
    assert zp_asm.exists(), "zeropage.asm must exist"

    passed = verify_memory_integrity(mem_json, zp_asm, require_binary_match=False)
    assert passed is True, "Memory integrity validation failed"



