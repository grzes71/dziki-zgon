;----------------------------------------
; engine/travel_screen.asm — Ekran Podróży (Interlude, ANTIC mode 2, statyczny tekst)
;----------------------------------------

; --- Zmienne lokalne ---
travel_frame_count
    dta $00
travel_regname_len
    dta $00
travel_screen_active
    dta $00

; Kody znakowe ekranu (Screen Codes) dla małych liter: "podróż do " (10 znaków)
; p=$70, o=$6F, d=$64, r=$72, ó=$5F, ż=$5C, space=$00, d=$64, o=$6F, space=$00
TravelPrefixText
    dta $70, $6F, $64, $72, $5F, $5C, $00, $64, $6F, $00

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

    ; 3. Czyszczenie bufora tekstu (320 B)
    ldx #0
    lda #0
@clr_footer
    sta FOOTER_ADDR,x
    sta FOOTER_ADDR+$100,x
    inx
    bne @clr_footer

    ; 4. Przygotowanie tekstu w FOOTER_ADDR ($5E10)
    ; Pobranie ID docelowego regionu dla NEW_SCREEN_ID
    ldx NEW_SCREEN_ID
    lda SCREEN_REGION,x
    tax                     ; X = RegionId

    ; Pobranie wskaźnika nazwy regionu
    lda REGION_NAMES_LO,x
    sta SRC_PTR
    lda REGION_NAMES_HI,x
    sta SRC_PTR+1

    ; Oblicz długość nazwy regionu L_name (skanuj wstecz od indeksu 19 w poszukiwaniu niezerowego bajtu)
    ldy #19
@find_end
    lda (SRC_PTR),y
    bne @found_end
    dey
    bpl @find_end
    ldy #0
    jmp @got_len
@found_end
    iny                     ; Y = L_name (ostatni niezerowy indeks + 1)
@got_len
    sty travel_regname_len

    ; Całkowita długość L_total = 10 + L_name
    tya
    clc
    adc #10

    ; start_offset = (40 - L_total) / 2
    eor #$FF
    sec
    adc #40
    lsr
    tax                     ; X = start_offset

    ; Kopiowanie "podróż do " (10 bajtów) od FOOTER_ADDR + start_offset
    ldy #0
@copy_prefix
    lda TravelPrefixText,y
    sta FOOTER_ADDR,x
    inx
    iny
    cpy #10
    bne @copy_prefix

    ; Kopiowanie L_name bajtów nazwy regionu od FOOTER_ADDR + start_offset + 10
    ldy #0
@copy_regname
    cpy travel_regname_len
    bcs @copy_done
    lda (SRC_PTR),y
    sta FOOTER_ADDR,x
    inx
    iny
    jmp @copy_regname
@copy_done

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
