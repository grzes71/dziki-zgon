;----------------------------------------
; scenes/gameover/gameover.asm — Ekran końca gry
; ANTIC D (128×96, 4 kolory, narrow playfield) + tekst GAME OVER
;----------------------------------------

; --- Kolory (generowane z obrazka) ---
    icl "../../gen/gameover_colors.asm"

;---- Zmienne lokalne sceny ----
gameover_fire_released
    dta $00

;==============================================================
; DLI_Gameover — Obrazek + tęcza na tekście (ANTIC mode 3, 10 scanlines)
; Wzorowane na TEXT_DLI z title.asm — per-scanline WSYNC + COLPF1
; (1) pierwsza linia DL ($F0) — przywraca kolory obrazka
; (2) blank przed tekstem ($F0) — tęcza na każdej linii znaku
;==============================================================
RAINBOW_LEN = 10

.proc DLI_Gameover
    pha
    txa
    pha

@rainbow
    ; --- Tęcza per-scanline (ANTIC mode 3 = 10 linii znaku) ---
    ldy #0
    sty COLPF0            ; nieużywane (standardowe znaki, bit 7=0)
    sty COLPF1            ; nieużywane

@rloop
    lda GoRainbow,y       ; pobierz kolor dla tej linii
    sta WSYNC             ; czekaj na początek następnej linii skanowania
    sta COLPF2            ; ustaw kolor tekstu
    iny
    cpy #RAINBOW_LEN
    bne @rloop

    lda #GAMEOVER_COLPF0
    sta COLPF0
    lda #GAMEOVER_COLPF1
    sta COLPF1
    lda #GAMEOVER_COLPF2
    sta COLPF2

@done
    pla
    tax
    pla
    rti
.endp

go_dli_toggle
    dta $00

; Kolory tęczy dla COLPF1 — 10 kolorów (ANTIC mode 3 = 10 scanlines)
GoRainbow
    dta $30  
    dta $32    
    dta $34   
    dta $36  
    dta $38    
    dta $3A   
    dta $3C    
    dta $3C   
    dta $3E    
    dta $3E 

.proc gameover_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta PRIOR               ; reset priorytetów
    sta gameover_fire_released ; zresetuj stan przycisku FIRE
    sta go_dli_toggle       ; DLI toggle: 0 = obrazek

    jsr pmg_clear_all
    jsr copy_gameover_text

    ; --- Display List (ANTIC D + tekst) ---
    lda #<DLIST_GAMEOVER
    sta DLISTL
    lda #>DLIST_GAMEOVER
    sta DLISTH

    ; --- Charset (własny font $6000) ---
    lda #$60
    sta CHBASE

    ; --- Kolory z wygenerowanego pliku ---
    lda #GAMEOVER_COLBK
    sta COLBK
    lda #GAMEOVER_COLPF0
    sta COLPF0
    lda #GAMEOVER_COLPF1
    sta COLPF1
    lda #GAMEOVER_COLPF2
    sta COLPF2
    lda #$00
    sta COLPF3            ; 5th player — nieużywany

    ; --- DLI: wektor + enable ---
    lda #<DLI_Gameover
    sta VDSLST
    lda #>DLI_Gameover
    sta VDSLST+1
    lda #$80              ; DLI on, VBI off
    sta NMIEN

    ; --- DMA ON (narrow playfield — 128 pikseli, bez PMG) ---
    lda #$21
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
    lda #0
    sta NMIEN              ; wyłącz DLI przed zmianą stanu
    jsr advance_stage      ; powrót do pierwszego etapu z tablicy
@exit
    rts
.endp

;==============================================================
; copy_gameover_text — Kopiuje tekst GAME OVER (32 B) z ROM do RAM ($5E10)
;==============================================================
.proc copy_gameover_text
    lda #<GO_TEXT_Data
    sta SRC_PTR
    lda #>GO_TEXT_Data
    sta SRC_PTR+1
    lda #<FOOTER_ADDR
    sta DST_PTR
    lda #>FOOTER_ADDR
    sta DST_PTR+1
    jsr RLE_Depack
    rts
.endp
