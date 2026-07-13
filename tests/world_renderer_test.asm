;----------------------------------------
; tests/world_renderer_test.asm
; Test Harness dla procedury build_screen
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

; --- Entry Point ---
    org $2000
start_test
    jsr build_screen
    ; Ponieważ emulator jest uruchamiany do momentu RTS na stosie, a my
    ; chcemy, żeby zatrzymał się czysto na końcu, możemy po prostu wrócić
    ; do systemu albo zasymulować break:
    ; Ale bezpieczniej:
    brk
    rts

; --- Zmienne globalne i Mocki tablic World Buildera ---
    org $3000
SCREEN_POINTERS_LO .ds 256
SCREEN_POINTERS_HI .ds 256
OBJ_SIZE           .ds 256
OBJ_FLAGS          .ds 256
COLLISION_GRID     .ds 60
OBJ_TILES_LO       .ds 256
OBJ_TILES_HI       .ds 256

; --- Wirtualny VRAM (ANTIC 5 to 40x10) ---
    org $4000
GAME_SCREEN_A5     .ds 480

; --- Zrzut danych mapy zdefiniowany przez Pythona ---
    org $5000
SCREEN_DATA        .ds 1024  ; Miejsce, pod którym wgramy testowy układ "ekranu"

    org $6000
TILES_DATA         .ds 1024  ; Miejsce na zdefiniowane na brudno kafle obiektów

; --- Włączenie biblioteki docelowej ---
    org $7000
    icl "../lib/world_renderer.asm"

Load_Screen_Enemies
    rts
