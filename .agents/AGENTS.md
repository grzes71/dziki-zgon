# Project Rules — Wiedźmin: Dziki Zgon (Atari 800 XL / XE)

## Memory Management Rules & Guidelines

1. **OS ROM Boundary (`$C000`+)**:
   - OS ROM is enabled in this project (`PORTB` bit 0 = 1).
   - Address ranges `$C000`–`$CFFF` (OS Kernel) and `$D000`–`$DFFF` (Hardware Registers) **MUST NEVER** be used as RAM.
   - All code, graphics, RLE data, and world tables **MUST end at or below `$BFFF`**.

2. **RMT Audio Player Memory Isolation (`$A9E0`–`$B610`)**:
   - Memory range `$A9E0`–`$B610` is reserved exclusively for the RMT tracker player code and tables.
   - Do NOT place any sprites, images, or game routines inside `$A9E0`–`$B610`.

3. **Sequential Assembly (`main.asm`)**:
   - `org` directives in `main.asm` must be kept in strictly ascending memory order without location counter backtracking to prevent XEX segment overwrites during boot loading.

4. **Temporary Decompression Scratchpads**:
   - Never use arbitrary code addresses (e.g. `$3000`) as temporary depacking buffers in `mRLE_Depack`. Always use designated RAM buffers (e.g., `FOOTER_ADDR` = `$5E10`).
