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
; DLI_Gameover — Obrazek + płynne migotanie tekstu (ANTIC mode 3)
; (1) pierwsza linia DL ($F0) — przywraca kolory obrazka
; (2) blank przed tekstem ($F0) — ustawia COLPF2 na kolor z tabeli
; Kolor zmienia się co klatkę (10 klatek = pełny cykl)
;==============================================================
RAINBOW_LEN = 10

.proc DLI_Gameover
    pha
    txa
    pha

    lda go_dli_toggle
    bne @blink

@restore
    ; --- Obrazek: przywróć COLPF0–2 z palety ---
    lda #GAMEOVER_COLPF0
    sta COLPF0
    lda #GAMEOVER_COLPF1
    sta COLPF1
    lda #GAMEOVER_COLPF2
    sta COLPF2
    lda #1
    sta go_dli_toggle
    jmp @done

@blink
    ; --- Migotanie: ustaw COLPF2 na bieżący kolor z tabeli ---
    lda #0
    sta COLPF0            ; nieużywane (standardowe znaki)
    sta COLPF2
    ldx go_pulse_idx
    lda GoRainbow,x
    sta COLPF1            ; kolor tekstu dla tej klatki

    ; Spowolnienie ×2: inkrementuj go_pulse_idx co 2 klatki
    inc go_subframe
    lda go_subframe
    cmp #2
    bne @reset_done
    lda #0
    sta go_subframe
    inc go_pulse_idx
    lda go_pulse_idx
    cmp #RAINBOW_LEN
    bne @reset_done
    lda #0
    sta go_pulse_idx      ; wrap do 0 po pełnym cyklu
@reset_done
    lda #0
    sta go_dli_toggle

@done
    pla
    tax
    pla
    rti
.endp

go_dli_toggle
    dta $00
go_pulse_idx
    dta $00
go_subframe
    dta $00

; Kolory migotania dla COLPF2 — 10 kolorów, zmiana co klatkę
GoRainbow
    dta $30     ; 0: ciemny pomarańcz
    dta $32     ; 1
    dta $34     ; 2
    dta $36     ; 3: czerwony
    dta $38     ; 4
    dta $3A     ; 5
    dta $3C     ; 6
    dta $3C     ; 7
    dta $3E     ; 8
    dta $3E     ; 9: jasny pomarańcz

.proc gameover_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta PRIOR               ; reset priorytetów
    sta gameover_fire_released ; zresetuj stan przycisku FIRE
    sta go_dli_toggle       ; DLI toggle: 0 = obrazek
    sta go_pulse_idx        ; indeks migotania: 0
    sta go_subframe         ; spowolnienie ×2: 0

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
