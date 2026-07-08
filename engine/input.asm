;----------------------------------------
; engine/input.asm
;----------------------------------------

.proc Input_Update
    ; Odczyt joysticka (PORT A, $D300)
    lda PORTA
    eor #$FF            ; neguj (0=neutral, 1=aktywny kierunek)
    sta InputState_Joy
    
    ; Odczyt przycisku FIRE
    lda TRIG0
    sta InputState_Trig
    
    rts
.endp
