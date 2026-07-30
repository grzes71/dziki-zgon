;----------------------------------------
; engine/travel_screen.asm — Ekran Podróży (Interlude)
; ANTIC 4 (40×23 znaków) + tekst "PODRÓŻ DO <REGION>" (ANTIC 2)
;----------------------------------------

; --- Zmienne lokalne ---
travel_dli_state
    dta $00
travel_frame_count
    dta $00
travel_regname_len
    dta $00


; Tablica kolorów tła/tekstu dla paska tęczy (10 linii skanowania)
TravelRainbow
    dta $74, $76, $78, $7A, $7C, $7A, $78, $76, $74, $00

; Kody znakowe ekranu (Screen Codes) dla małych liter: "podróż do " (10 znaków)
; p=$70, o=$6F, d=$64, r=$72, ó=$5F, ż=$5C, space=$00, d=$64, o=$6F, space=$00
TravelPrefixText
    dta $70, $6F, $64, $72, $5F, $5C, $00, $64, $6F, $00

;==============================================================
; DLI_Travel_Top / DLI_Travel_Bottom — 2-etapowa obsługa DLI
;==============================================================
DLI_Travel = DLI_Travel_Top

.proc DLI_Travel_Top
    pha
    lda #$90            ; DLI #1 (góra): wspólny charset Game Over / Travel ($9000)
    sta CHBASE


    ; --- Kolory obrazka (wpis bezpośrednio do rejestrów GTIA) ---
    lda #GO_COLBK
    sta COLBK
    lda #GO_COLPF0
    sta COLPF0
    lda #GO_COLPF1
    sta COLPF1
    lda #GO_COLPF2
    sta COLPF2
    lda #GO_COLPF3
    sta COLPF3

    lda #<DLI_Travel_Bottom
    sta VDSLST
    lda #>DLI_Travel_Bottom
    sta VDSLST+1

    pla
    rti
.endp

.proc DLI_Travel_Bottom
    pha
    lda #$60            ; DLI #2 (dół): czcionka systemowa ($6000) dla tekstu
    sta CHBASE

    ldy #0
    sty COLPF0    
    sty COLPF1
    sty COLBK

@rainbow_loop
    lda TravelRainbow,y
    sta WSYNC
    sta COLPF2
    iny
    cpy #10
    bne @rainbow_loop

    lda #<DLI_Travel_Top
    sta VDSLST
    lda #>DLI_Travel_Top
    sta VDSLST+1

    pla
    rti
.endp

;==============================================================
; travel_screen_show — Wyświetla 5-sekundowy ekran podróży
;==============================================================
.proc travel_screen_show
    ; 1. Wyłącz DMA i PMG na czas przygotowania ekranu
    lda #0
    sta DMACTL
    sta SDMCTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA w GTIA
    sta GPRIOR

    ; 2. Kopiuj obrazek TravelScreen_Data (920 B) do VRAM_ARENA ($4000)

    ldx #0
@loop_copy
    lda TravelScreen_Data,x
    sta VRAM_ARENA,x
    lda TravelScreen_Data+$100,x
    sta VRAM_ARENA+$100,x
    lda TravelScreen_Data+$200,x
    sta VRAM_ARENA+$200,x
    lda TravelScreen_Data+$300,x
    sta VRAM_ARENA+$300,x
    inx
    bne @loop_copy

    ; 3. Wyczyszczenie PMG
    jsr pmg_clear_all

    ; 4. Przygotowanie tekstu stopki w FOOTER_ADDR ($5E10)
    ; Czyszczenie 40 bajtów do $00 (spacja w font.asm)
    ldx #39
    lda #0
@clr_footer
    sta FOOTER_ADDR,x
    dex
    bpl @clr_footer

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

    ; 6. Ustaw charset i DLI
    lda #$90
    sta CHBAS
    sta CHBASE



    lda #<DLI_Travel_Top
    sta VDSLST
    lda #>DLI_Travel_Top
    sta VDSLST+1

    lda #$C0                ; DLI on, VBI on
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
    lda #<DLI_Travel_Top
    sta VDSLST
    lda #>DLI_Travel_Top
    sta VDSLST+1

    inc travel_frame_count
    lda travel_frame_count
    cmp #250
    bcc @wait_loop

    ; 9. Wyłącz DLI/VBI przed wyjściem
    lda #0
    sta NMIEN
    rts
.endp

