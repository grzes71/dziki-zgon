;----------------------------------------
; scenes/gameover/gameover.asm — Ekran końca gry
; (TODO: zastąp placeholder prawdziwym ekranem)
;----------------------------------------

.proc gameover_init
    lda #0
    sta DMACTL

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
    lda #$00
    sta NMIEN

    rts
.endp

.proc gameover_run
    lda STRIG0
    bne @exit
    lda #STATE_TITLE     ; powrót do ekranu tytułowego
    sta GAME_STATE
@exit
    rts
.endp
