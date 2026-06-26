;----------------------------------------
; scenes/gameover/gameover.asm — Ekran końca gry
; (TODO: zastąp placeholder prawdziwym ekranem)
;----------------------------------------

;---- Zmienne lokalne sceny ----
gameover_fire_released
    dta $00

.proc gameover_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta PRIOR               ; reset priorytetów
    sta gameover_fire_released ; zresetuj stan przycisku FIRE

    jsr pmg_clear_all

    ; Tymczasowa DL
    lda #<DLIST_GAMEOVER
    sta DLISTL
    lda #>DLIST_GAMEOVER
    sta DLISTH

    ; Kolory placeholder
    lda #$00
    sta COLBK
    lda #$34
    sta COLPF0
    lda #$00
    sta COLPF1
    lda #$00
    sta COLPF2
    lda #$00
    sta COLPF3

    lda #$22
    sta DMACTL

    rts
.endp

.proc gameover_run
    lda gameover_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda TRIG0
    beq @exit            ; wciąż trzyma — nie reaguj
    lda #1
    sta gameover_fire_released
    jmp @exit

@check_press
    lda TRIG0
    bne @exit
    lda #STATE_TITLE     ; powrót do ekranu tytułowego
    sta GAME_STATE
@exit
    rts
.endp
