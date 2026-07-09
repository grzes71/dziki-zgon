import pytest
from pathlib import Path
from debug_bridge.symbols import LabParser
from debug_bridge.errors import SymbolError

def test_lab_parser(tmp_path):
    lab_content = """
; MADS log file
TEST_SYMBOL = $A000
OTHER_SYMBOL = $B000 (BANK=1)
"""
    lab_file = tmp_path / "test.lab"
    lab_file.write_text(lab_content)
    
    parser = LabParser()
    symbols = parser.parse(lab_file)
    assert symbols["TEST_SYMBOL"] == 0xA000
    assert symbols["OTHER_SYMBOL"] == 0xB000

def test_lab_parser_with_include(tmp_path):
    lab_content = """
A = $1000
B = $2000
C = $3000
"""
    lab_file = tmp_path / "test.lab"
    lab_file.write_text(lab_content)
    
    parser = LabParser(include_list=["A", "C"])
    symbols = parser.parse(lab_file)
    assert "A" in symbols
    assert "C" in symbols
    assert "B" not in symbols
