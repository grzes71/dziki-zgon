;----------------------------------------
; scenes/story/story.asm — Ekran opisu / wprowadzenia
; (TODO: zastąp placeholder prawdziwym ekranem)
;----------------------------------------

.proc story_init
    ; Wyłącz DMA
    lda #0
    sta DMACTL

    ; Wyczyść PMG (brak sprite'ów na ekranie story)
    jsr pmg_clear_all

    ; --- Tymczasowo: prosta DL z jedną pustą linią i pętlą ---
    lda #<DLIST_STORY
    sta DLISTL
    lda #>DLIST_STORY
    sta DLISTH

    ; Kolory placeholder
    lda #$00
    sta COLBK
    lda #$0E
    sta COLPF0
    lda #$00
    sta COLPF1
    lda #$00
    sta COLPF2
    lda #$00
    sta COLPF3

    ; Wyłącz PMG DMA (na razie nie używamy)
    lda #$22             ; playfield ON, PMG OFF
    sta DMACTL

    ; Wyłącz DLI
    lda #$00
    sta NMIEN

    rts
.endp

.proc story_run
    lda STRIG0
    bne @exit
    lda #STATE_GAME
    sta GAME_STATE
@exit
    rts
.endp
