---
trigger: always_on
---

# Domain: 6502 Assembly (MADS)

## 1. Instruction Set & Limitations
- **Strictly MOS 6502:** Use ONLY official 6502 instructions. NO CMOS (PHX, PLY, BRA) or 65816 opcodes.
- **Processor Flags:** `INC` and `DEC` modify `Z` and `N`, but **NEVER `C` (Carry)**. 
- **Arithmetic:** `ADC` and `SBC` must ALWAYS be preceded by an explicit `CLC` or `SEC`.
- **Syntax:** Enforce MADS syntax (`$` for hex, `%` for binary).

## 2. Hardware & Memory Boundaries
- **Zero Page:** Registers `$00-$7F` are reserved by the OS. Use ONLY `$80-$FF` for user variables and pointers.
- **ANTIC 1KB Rule:** Display Lists (DLIST) must NEVER cross a 1 KB boundary without an explicit `JVB` or `LMS` instruction.
- **No Magic Numbers:** Never hardcode hardware addresses. Always use official equates (e.g., `WSYNC`, `PORTB`) assumed to be in `hardware.asm`.
- **Interrupts:** DLI routines modifying CPU registers must push/pull them to/from the stack (`PHA/PLA`, `TXA/TAX`, etc.).

## 3. Formatting
- **Cycle Counts:** Time-critical routines must include cycle counts in comments per instruction, with running totals.
- **Format:** `[Label]  [Mnemonic] [Operand]  ; [Comment + cycles]`
