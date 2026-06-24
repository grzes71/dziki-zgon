;----------------------------------------
; scenes/game/game.asm — Gra właściwa
; (TODO: zastąp placeholder prawdziwą rozgrywką)
;----------------------------------------

.proc game_init
    lda #0
    sta DMACTL

    jsr pmg_clear_all

    ; Tymczasowa DL
    lda #<DLIST_GAME
    sta DLISTL
    lda #>DLIST_GAME
    sta DLISTH

    ; Kolory placeholder
    lda #$00
    sta COLBK
    lda #$36
    sta COLPF0
    lda #$00
    sta COLPF1
    lda #$00
    sta COLPF2
    lda #$00
    sta COLPF3

    lda #$22             ; playfield ON, PMG OFF
    sta DMACTL
    lda #$00
    sta NMIEN

    rts
.endp

.proc game_run
    lda STRIG0
    bne @exit
    lda #STATE_OVER
    sta GAME_STATE
@exit
    rts
.endp
