from pathlib import Path
import sys
import yaml
from scripts.renumber_objects import renumber_objects, main

def test_renumber_objects_dry_run():
    base_dir = Path(__file__).resolve().parent.parent / "world"
    result = renumber_objects(base_dir, apply_changes=False)

    assert result["total"] > 0
    assert result["used_count"] > 0
    assert result["unused_count"] >= 0
    assert result["total"] == result["used_count"] + result["unused_count"]
    assert result["applied"] is False

    # Check ascending new_code order
    for idx, change in enumerate(result["changes"], start=1):
        assert change["new_code"] == idx

    # Check that counts are non-increasing (most used first)
    counts = [c["count"] for c in result["changes"]]
    for i in range(len(counts) - 1):
        assert counts[i] >= counts[i + 1]


def test_renumber_objects_cli(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["renumber_objects.py"])
    main()
    captured = capsys.readouterr()
    output = captured.out

    assert "RAPORT PRZENUMEROWANIA OBIEKTÓW" in output
    assert "Liczba wszystkich obiektów:" in output
    assert "Używane na planszach:" in output
    assert "Nieużywane w grze:" in output
