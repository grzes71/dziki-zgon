---
trigger: always_on
---

# AltirraSDL Emulation & Verification Rules

## 1. Emulator Execution Policy
- **Proactive Verification:** Whenever building, modifying, or testing the game binary (`call_of_the_wintermon.xex`), verify execution using **AltirraSDL** whenever possible.
- **AltirraSDL Binary Path:**
  `C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe`

## 2. Interactive Run (Visual Verification)
- To launch the emulator for visual/manual testing of the current binary:
  ```powershell
  Start-Process -FilePath "C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe" -ArgumentList "call_of_the_wintermon.xex"
  ```
  *(Always use asynchronous / non-blocking execution so the shell is not blocked).*

## 3. Automated / E2E Testing (AltirraBridge)
- For programmatic verification, headless tests, or capturing screenshots:
  - Launch AltirraSDL with `--bridge`:
    ```powershell
    Start-Process -FilePath "C:\Users\grzes\Documents\Projects\AltirraSDL\build\windows-sdl-release\src\AltirraSDL\Release\AltirraSDL.exe" -ArgumentList "--bridge"
    ```
  - Read token file from `$env:LOCALAPPDATA\Temp\altirra-bridge-*.token`.
  - Use Python SDK (`from altirra_bridge import AltirraBridge`):
    - Boot binary: `atari.boot("call_of_the_wintermon.xex")`
    - Advance deterministic frames: `atari.frame(120)`
    - Check registers or RAM: `atari.regs()`, `atari.peek(addr, length)`
    - Capture framebuffer: `atari.screenshot()`
    - Inject joystick/key actions: `atari.joy(0, "right", fire=True)`, `atari.key("SPACE")`

