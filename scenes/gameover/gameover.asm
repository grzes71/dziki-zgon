;----------------------------------------
; scenes/gameover/gameover.asm — Ekran końca gry (ANTIC mode 2, statyczny tekst)
;----------------------------------------

;---- Zmienne lokalne sceny ----
gameover_fire_released
    dta $00

;==============================================================
; gameover_vbi — Obsługa Immediate VBI dla ekranu Game Over
; - Odtwarza muzykę RMT
;==============================================================
.proc gameover_vbi
    jsr RASTERMUSICTRACKER+3 ; Odtwórz 1 klatkę muzyki RMT
    jmp SYSVBV
.endp

;==============================================================
; gameover_init — Konfiguracja ekranu Game Over
;==============================================================
.proc gameover_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta GPRIOR              ; reset priorytetów
    sta gameover_fire_released ; zresetuj stan przycisku FIRE

    jsr pmg_clear_all
    jsr copy_gameover_text

    ; --- Display List (ANTIC mode 2) ---
    lda #<DLIST_GAMEOVER
    sta SDLSTL
    sta DLISTL
    lda #>DLIST_GAMEOVER
    sta SDLSTH
    sta DLISTH

    ; --- Charset systemowy ($6000 -> CHBASE=$60) ---
    lda #$60
    sta CHBAS
    sta CHBASE

    ; --- Kolory: biały tekst na czarnym tle ---
    lda #$00
    sta COLOR4
    sta COLBK            ; czarna ramka
    sta COLOR2
    sta COLPF2           ; czarne tło znaków
    sta COLOR3
    sta COLPF3           ; nieużywane
    sta COLOR0
    sta COLPF0           ; nieużywane
    lda #$0E
    sta COLOR1
    sta COLPF1           ; biały tekst (COLPF1 w ANTIC mode 2)

    ; --- DMA ON (normal playfield — 40 znaków, bez PMG) ---
    lda #$22
    sta SDMCTL
    sta DMACTL

    jsr title_audio_init

    ; --- Podepnij VBI handler dla muzyki RMT ---
    lda #0
    sta NMIEN
    lda #<gameover_vbi
    sta $0222
    lda #>gameover_vbi
    sta $0223
    lda #$40
    sta NMIEN
    rts
.endp

;==============================================================
; gameover_run — Czeka na puszczenie FIRE, potem na FIRE → GAME
;==============================================================
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
    lda #0
    sta NMIEN              ; wyłącz VBI przed zmianą stanu
    jsr advance_stage      ; powrót do pierwszego etapu z tablicy
@exit
    rts
.endp

;==============================================================
; copy_gameover_text — Kopiuje tekst GAME OVER (porażka/sukces) z ROM do RAM ($5E10)
;==============================================================
.proc copy_gameover_text
    ; Clear footer buffer (320 B)
    ldx #0
    lda #0
@clr
    sta FOOTER_ADDR,x
    cpx #64
    bcs @skip
    sta FOOTER_ADDR+256,x
@skip
    inx
    bne @clr

    lda GAME_RESULT_STATUS
    cmp #1                  ; 1 = Sukces
    beq @do_success

@do_fail
    jsr show_gameover_fail_header
    mRLE_Depack text_contents_gameover_fail FOOTER_ADDR
    rts

@do_success
    jsr show_gameover_success_header
    mRLE_Depack text_contents_gameover_success FOOTER_ADDR
    rts
.endp
