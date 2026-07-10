;----------------------------------------
; tests/charset_anim_test.asm
; Test Harness dla procedury animate_charset
;----------------------------------------

; --- Mocki rejestrów Zero Page ---
SRC_PTR = $82

; --- Entry Point ---
    org $2000
start_test
    jsr animate_charset
    brk
    rts

; --- Pamięć dla bufora znaków ---
    org $A800
GAME_CHARSET
    .ds 1024  ; 1 KB na znaki

; --- Włączenie biblioteki docelowej ---
    org $3000
    icl "../engine/charset_anim.asm"
