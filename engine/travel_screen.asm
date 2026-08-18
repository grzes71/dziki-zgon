;----------------------------------------
; engine/travel_screen.asm — Ekran Podróży (Interlude, ANTIC mode 2, statyczny tekst)
;----------------------------------------

; --- Zmienne lokalne ---
travel_frame_count
    dta $00
travel_screen_active
    dta $00

; --- Tabele wskaźników do tekstów podróży (indeksowane przez RegionId) ---
TRAVEL_TEXTS_LO
    dta <text_contents_travel_JAR_WIECZNEJ_ZGAGI
    dta <text_contents_travel_LAS_PIJANEGO_ZAJACA
    dta <text_contents_travel_OLD_WYZIMA
    dta <text_contents_travel_SAMOTNIA_MISTRZA
    dta <text_contents_travel_WHITE_FIELD

TRAVEL_TEXTS_HI
    dta >text_contents_travel_JAR_WIECZNEJ_ZGAGI
    dta >text_contents_travel_LAS_PIJANEGO_ZAJACA
    dta >text_contents_travel_OLD_WYZIMA
    dta >text_contents_travel_SAMOTNIA_MISTRZA
    dta >text_contents_travel_WHITE_FIELD

;==============================================================
; travel_screen_show — Wyświetla 5-sekundowy statyczny ekran podróży (ANTIC mode 2)
;==============================================================
.proc travel_screen_show
    ; Ustaw flagę aktywności ekranu podróży i wyłącz wyliczanie animacji charsetu
    lda #1
    sta travel_screen_active
    lda #0
    sta anim_chars_active_mask

    ; 1. Wyłącz DMA i PMG na czas przygotowania ekranu
    sta DMACTL
    sta SDMCTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA w GTIA
    sta GPRIOR

    ; 2. Wyczyszczenie PMG
    jsr pmg_clear_all
    jsr show_travel_header

    ; 3. Czyszczenie bufora tekstu (320 B)
    ldx #0
    lda #0
@clr_footer
    sta FOOTER_ADDR,x
    cpx #64
    bcs @skip_upper
    sta FOOTER_ADDR+256,x
@skip_upper
    inx
    bne @clr_footer

    ; 4. Przygotowanie tekstu w FOOTER_ADDR ($5E10)
    ; Pobranie ID docelowego regionu dla NEW_SCREEN_ID
    ldx NEW_SCREEN_ID
    lda SCREEN_REGION,x
    tax                     ; X = RegionId

    ; Pobranie wskaźnika tekstu podróży dla docelowego regionu
    lda TRAVEL_TEXTS_LO,x
    sta SRC_PTR
    lda TRAVEL_TEXTS_HI,x
    sta SRC_PTR+1

    ; Rozpakuj wielowierszowy tekst podróży (8 linii × 40 znaków) do FOOTER_ADDR
    lda #<FOOTER_ADDR
    sta DST_PTR
    lda #>FOOTER_ADDR
    sta DST_PTR+1
    jsr RLE_Depack

    ; 5. Ustaw Display List dla Travel Screen
    lda #<DLIST_TRAVEL
    sta SDLSTL
    sta DLISTL
    lda #>DLIST_TRAVEL
    sta SDLSTH
    sta DLISTH

    ; 6. Ustaw charset i kolory (font.asm $6000)
    lda #$60
    sta CHBAS
    sta CHBASE

    lda #$00
    sta COLOR4
    sta COLBK            ; czarne tło
    sta COLOR2
    sta COLPF2
    lda #$0E
    sta COLOR1
    sta COLPF1           ; biały tekst

    lda #$40             ; VBI on dla muzyki
    sta NMIEN

    ; 7. DMA ON (normal playfield — 40 znaków, bez PMG)
    lda #$22
    sta SDMCTL
    sta DMACTL

    ; 8. Czekaj 250 klatek (5.0 s przy 50 Hz PAL)
    lda #0
    sta travel_frame_count

@wait_loop
    jsr Engine_WaitFrame

    inc travel_frame_count
    lda travel_frame_count
    cmp #250
    bcc @wait_loop

    ; 9. Zakończ ekran podróży
    lda #0
    sta travel_screen_active
    lda #$40
    sta NMIEN
    rts
.endp
