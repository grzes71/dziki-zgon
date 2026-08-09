from pathlib import Path
import io
import sys
import yaml
from scripts.analyze_objects import print_world_stats, main

def test_print_world_stats_output(capsys):
    base_dir = Path(__file__).resolve().parent.parent / "world"
    objects_file = base_dir / "objects.yaml"
    
    with open(objects_file, 'r', encoding='utf-8') as f:
        objects_data = yaml.safe_load(f)
        
    print_world_stats(base_dir, objects_data)
    captured = capsys.readouterr()
    output = captured.out

    assert "=== STATYSTYKI ŚWIATA GRY (OGÓŁEM) ===" in output
    assert "Ilość przeciwników" in output
    assert "Ilość portal entry" in output
    assert "Ilość secret'ów" in output
    assert "Ilość obiektów" in output
    assert "Interaktywne:" in output
    assert "Kwatery:" in output
    assert "Portale:" in output
    assert "Ilość obiektów dla każdego tagu:" in output
    assert "=== STATYSTYKI W ROZBICIU NA POSZCZEGÓLNE REGIONY ===" in output
    assert "--- Region: WHITE_FIELD ---" in output

def test_analyze_objects_cli_stats(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["analyze_objects.py", "--stats", "-r", "WHITE_FIELD"])
    main()
    captured = capsys.readouterr()
    output = captured.out

    assert "=== STATYSTYKI ŚWIATA GRY (OGÓŁEM) [region: WHITE_FIELD] ===" in output
    assert "=== STATYSTYKI W ROZBICIU NA POSZCZEGÓLNE REGIONY [region: WHITE_FIELD] ===" in output
    assert "--- Region: WHITE_FIELD ---" in output
