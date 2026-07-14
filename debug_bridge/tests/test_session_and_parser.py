import pytest
from pathlib import Path
from debug_bridge.symbols import LabParser
from debug_bridge.session import parse_altirra_log, parse_mem_dumps

def test_lab_parser_table_format(tmp_path):
    lab_content = """
; MADS symbol table
00 2000 START_LABEL
01 3000 LOOP_LABEL
D000 HPOSP0
"""
    lab_file = tmp_path / "test_table.lab"
    lab_file.write_text(lab_content)
    
    parser = LabParser()
    symbols = parser.parse(lab_file)
    assert symbols["START_LABEL"] == 0x2000
    assert symbols["LOOP_LABEL"] == 0x3000
    assert symbols["HPOSP0"] == 0xD000

def test_parse_mem_dumps():
    dumps = ["$0600:L$40", "$A000:L$100"]
    commands = parse_mem_dumps(dumps)
    assert commands == ["d 0600 L40", "d A000 L100"]

def test_parse_altirra_log():
    log_data = """
Altirra> r
(6502) PC=4000 A=0A X=10 Y=20 S=FD P=34 (NV-BDIZC: 00110100)  A9 FF       LDA #$FF
Altirra> k
4000
3050
2010
Altirra> d 0600 10
0600: A9 FF 8D 00 D0 A9 10 8D  01 D0 A9 20 8D 02 D0 A9  |........... ...|
0610: 30 8D 03 D0 A9 40 8D 04  D0 A9 50 8D 05 D0 A9 60  |0...@..P...`....|
Altirra> .logclose
"""
    result = parse_altirra_log(
        log_content=log_data,
        is_software_bp=True,
        bp_label_or_addr="MY_LABEL",
        bx_cond=None,
        hw_regs=False,
        disasm_count=0
    )
    
    assert result["status"] == "ok"
    assert result["breakpoint"]["type"] == "software"
    assert result["breakpoint"]["label"] == "MY_LABEL"
    assert result["cpu"]["PC"] == 0x4000
    assert result["cpu"]["A"] == 0x0A
    assert result["cpu"]["X"] == 0x10
    assert result["cpu"]["Y"] == 0x20
    assert result["cpu"]["S"] == 0xFD
    assert result["cpu"]["flags"] == {
        "N": False, "V": False, "B": True, "D": False,
        "I": True, "Z": False, "C": False
    }
    assert result["cpu"]["current_instruction"] == "LDA #$FF"
    assert result["call_stack"] == ["$4000", "$3050", "$2010"]
    
    assert len(result["memory_dumps"]) == 1
    dump = result["memory_dumps"][0]
    assert dump["address"] == "$0600"
    assert dump["length"] == 32
    assert dump["hex"].startswith("A9 FF 8D")
