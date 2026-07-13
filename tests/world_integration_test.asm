;----------------------------------------
; tests/world_integration_test.asm
; Test Harness Integracyjny dla build_screen (rzeczywiste dane)
;----------------------------------------

; --- Mocki adresów Zero Page ---
SCREEN_PTR  equ $86
TILE_PTR    equ $88
GAME_SCREEN_ID equ $8A
OBJ_X       equ $8B
OBJ_Y       equ $8C
OBJ_W       equ $8D
OBJ_H       equ $8E
OBJ_CODE    equ $8F
TMP_X       equ $90
TMP_Y       equ $91
DST_PTR     equ $84

; --- Wirtualny VRAM ---
    org $4000
GAME_SCREEN_A5     .ds 480
COLLISION_GRID     .ds 60

; --- Zmienne wygenerowane z World Builder ---
    org $5000
    icl "../gen/world/world.inc"
    icl "../gen/world/objects.asm"
    icl "../gen/world/regions.asm"
    icl "../gen/world/screens.asm"
    icl "../gen/world/exits.asm"

; --- Entry Point ---
    org $7000
start_test
    jsr build_screen
    brk
    rts

; --- Włączenie biblioteki docelowej ---
    org $8000
    icl "../lib/world_renderer.asm"

Load_Screen_Enemies
    rts
