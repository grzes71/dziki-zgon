;----------------------------------------
; scenes/title/title.asm — Ekran tytułowy
; Tęcza na sprite'ach + księżyc + gwiazdy + stopka
;----------------------------------------

; --- Stałe kolorów tła (generowane z obrazka) ---
    icl "../../gen/title_colors.asm"

;---- Zmienne lokalne sceny ----
title_fire_released
    dta $00

;==============================================================
; title_init — Konfiguracja ekranu tytułowego
; Wywoływane RAZ przy wejściu w ten stan
;==============================================================
.proc title_init
    ; --- Wyłącz DMA na czas konfiguracji ---
    lda #0
    sta DMACTL
    sta title_fire_released

    ; --- Rozpakuj ekran tytułowy (RLE) do VRAM_ARENA ---
    mRLE_Depack TitleScreen_Data VRAM_ARENA

    ; --- Wyczyść całą pamięć PMG ---
    jsr pmg_clear_all

    ; --- Transpozycja sprite'ów tytułu → PMG ---
    ; Format źródłowy: [P0,P1,P2,P3,M5th] × 37 wierszy
    ; Format PMG:       per-player, ciągiem 128 B, offset TOP_MARGIN
    
    ; Rozpakuj SpriteData (logo) do bufora tymczasowego $3000
    mRLE_Depack SpriteData $3000

    ldx #SPRITE_ROWS-1

@row_loop
    ; Oblicz offset źródłowy: X * 5
    txa
    sta SRC_TMP
    asl @               ; *2
    asl @               ; *4
    clc
    adc SRC_TMP          ; +1 → *5
    tay                  ; Y = offset w źródle

    lda $3000,y
    sta PLAYER0+TOP_MARGIN,x
    iny
    lda $3000,y
    sta PLAYER1+TOP_MARGIN,x
    iny
    lda $3000,y
    sta PLAYER2+TOP_MARGIN,x
    iny
    lda $3000,y
    sta PLAYER3+TOP_MARGIN,x
    iny
    lda $3000,y
    sta MISSILES+TOP_MARGIN,x

    dex
    bpl @row_loop

    ; --- Transpozycja księżyca → PMG (P0–P3, 24 wiersze) ---
    ldx #MOON_ROWS-1
@mclear
    lda #0
    sta MISSILES+MOON_TOP,x
    dex
    bpl @mclear

    ; Rozpakuj MoonData (księżyc) do bufora tymczasowego $3000
    mRLE_Depack MoonData $3000

    ldx #MOON_ROWS-1
@moon_loop
    txa
    asl @
    asl @               ; X * 4
    tay
    lda $3000,y
    sta PLAYER0+MOON_TOP,x
    iny
    lda $3000,y
    sta PLAYER1+MOON_TOP,x
    iny
    lda $3000,y
    sta PLAYER2+MOON_TOP,x
    iny
    lda $3000,y
    sta PLAYER3+MOON_TOP,x
    pointer_dummy = *
    dex
    bpl @moon_loop

    ; --- Gwiazdy — pojedyncze piksele na missile'ach ---
    lda #$01             ; M0: bit 0 (prawy skraj)
    sta MISSILES+STAR0_Y
    lda #$04             ; M1: bit 2
    sta MISSILES+STAR1_Y
    lda #$10             ; M2: bit 4
    sta MISSILES+STAR2_Y
    lda #$40             ; M3: bit 6 (lewy skraj)
    sta MISSILES+STAR3_Y

    ; --- GTIA: pozycje graczy (side-by-side od lewej) ---
    lda #HPOS_P0
    sta HPOSP0
    lda #HPOS_P1
    sta HPOSP1
    lda #HPOS_P2
    sta HPOSP2
    lda #HPOS_P3
    sta HPOSP3

    ; Pozycje missile'i — ODWROTNA KOLEJNOŚĆ
    lda #HPOS_M+6
    sta HPOSM0
    lda #HPOS_M+4
    sta HPOSM1
    lda #HPOS_M+2
    sta HPOSM2
    lda #HPOS_M
    sta HPOSM3

    ; Rozmiar graczy — normalny
    lda #$00
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2
    sta SIZEP3
    sta SIZEM

    ; Kolory graczy — białe
    lda #$0E
    sta PCOLR0
    sta PCOLR1
    sta PCOLR2
    sta PCOLR3

    ; Kolor 5. gracza (missiles) — COLPF3
    lda #$0E
    sta COLPF3

    ; Adres bazowy PMG
    lda #>PMBASE_ADDR
    sta PMBASE

    ; Włącz graczy i missile
    lda #GRACTL_PM
    sta GRACTL

    ; PRIOR — 5th player + players over playfield
    lda #PRIOR_5TH
    sta GPRIOR

    ; --- Display List ---
    lda #<DLIST_TITLE
    sta DLISTL
    lda #>DLIST_TITLE
    sta DLISTH

    ; --- Kolory tła (generowane; plik w katalogu gen/) ---
    icl "../../gen/title_colors.asm"

    ; --- Przywróć tekst stopki (nadpisywany przez story/gameover) ---
    jsr copy_title_footer

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta DMACTL

    ; Charset — własna czcionka ($6000)
    lda #$60
    sta CHBASE

    ; --- DLI: wektor + włączenie na ostatniej pustej linii ---
    lda #<DLI_Handler
    sta VDSLST
    lda #>DLI_Handler
    sta VDSLST+1

    lda DLIST_TITLE+2
    ora #$80
    sta DLIST_TITLE+2

    lda #$C0             ; DLI on, VBI on (required for music)
    sta NMIEN

    jsr title_audio_init
    rts
.endp

;==============================================================
; title_run — Obsługa klatki (czeka na FIRE)
; Zwraca: GAME_STATE = STATE_STORY gdy FIRE wciśnięty
;==============================================================
.proc title_run
    lda title_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda TRIG0
    beq @exit            ; wciąż trzyma — nie reaguj
    lda #1
    sta title_fire_released
    jmp @exit

@check_press
    lda TRIG0
    bne @exit            ; FIRE nie wciśnięty — zostań w title
    ; Wyłącz DLI przed zmianą stanu — przekieruj na pusty RTI
    ; (zapobiega nadpisaniu kolorów/PRIOR przez pending DLI)
    lda #<DLI_Nop
    sta VDSLST
    lda #>DLI_Nop
    sta VDSLST+1
    lda #0
    sta NMIEN
    jsr advance_stage
@exit
    rts
.endp

;==============================================================
; DLI_Handler — Tęcza na sprite'ach tytułu
;==============================================================
DLI_Handler
    pha
    txa
    pha

    ; --- Ustaw kolory obrazka tytułowego (z title_colors.asm) ---
    lda #TITLE_COLBK
    sta COLBK            ; tło
    lda #TITLE_COLPF0
    sta COLPF0           ; playfield 0
    lda #TITLE_COLPF1
    sta COLPF1           ; playfield 1
    lda #TITLE_COLPF2
    sta COLPF2           ; playfield 2
    lda #$00
    sta COLPF3           ; playfield 3 — czarny

    ; Setup HPOS + SIZEP dla tytułu (x1, normalny)
    lda #$00
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2
    sta SIZEP3
    lda #HPOS_P0
    sta HPOSP0
    lda #HPOS_P1
    sta HPOSP1
    lda #HPOS_P2
    sta HPOSP2
    lda #HPOS_P3
    sta HPOSP3
    lda #HPOS_M+6
    sta HPOSM0
    lda #HPOS_M+4
    sta HPOSM1
    lda #HPOS_M+2
    sta HPOSM2
    lda #HPOS_M
    sta HPOSM3

    ; Czekaj do początku sprite'ów
    ldx #DLI_DELAY
@delay
    sta WSYNC
    dex
    bne @delay

    ; Pierwsza linia tytułu — kolor od razu
    ldx #0
    lda RainbowColors,x
    sta PCOLR0
    sta PCOLR1
    sta PCOLR2
    sta PCOLR3
    sta COLPF3
    inx

    ; Pozostałe linie
    ldy #SPRITE_ROWS-2
@rainbow
    sta WSYNC
    lda RainbowColors,x
    sta PCOLR0
    sta PCOLR1
    sta PCOLR2
    sta PCOLR3
    sta COLPF3
    inx
    dey
    bpl @rainbow

    ; --- Po tęczy: PRIOR=$01, PCOLR=$40, SIZEP=1x ---
    sta WSYNC
    lda #$01
    sta GPRIOR             ; wyłącz 5th-player
    lda #$40
    sta PCOLR0
    sta PCOLR1
    sta PCOLR2
    sta PCOLR3
    lda #$00
    sta COLPF3            ; przywróć playfield 3 (czarny)
    sta SIZEP0
    sta SIZEP1
    sta SIZEP2
    sta SIZEP3
    sta SIZEM

    ; --- Gwiazdy: HPOSM poniżej tęczy (stałe do końca klatki) ---
    lda #STAR0_X
    sta HPOSM0
    lda #STAR1_X
    sta HPOSM1
    lda #STAR2_X
    sta HPOSM2
    lda #STAR3_X
    sta HPOSM3

    ; --- Czekaj do księżyca ---
    ldx #MOON_TOP - TOP_MARGIN - SPRITE_ROWS - 2
@sm
    sta WSYNC
    dex
    bne @sm

    ; --- Księżyc: HPOSP ---
    lda #MOON_X
    sta HPOSP0
    lda #MOON_X+8
    sta HPOSP1
    lda #MOON_X+16
    sta HPOSP2
    lda #MOON_X+24
    sta HPOSP3

    ; Swap na text-DLI
    lda #<TEXT_DLI
    sta VDSLST
    lda #>TEXT_DLI
    sta VDSLST+1

    pla
    tax
    pla
    rti

;==============================================================
; Tabela kolorów tęczy (40 pozycji)
;==============================================================
RainbowColors
    dta $34,$36,$38,$3A,$3C
    dta $3E,$3E,$3F,$3E,$3E
    dta $3C,$3A,$38,$36,$34
    dta $00,$00,$00,$00,$00
    dta $00,$14,$16,$18,$C8
    dta $CA,$CC,$CE,$CE,$CF
    dta $CF,$CE,$CE,$CC,$CA
    dta $C8,$18,$16,$14,$00

;==============================================================
; TEXT_DLI — Tęcza na stopce (ANTIC mode 2)
;==============================================================
TEXT_DLI
    pha
    txa
    pha

    lda #$00
    sta GRACTL

    ldx #$9E
    sta WSYNC
    stx COLPF2
    sta COLPF0
    sta COLPF1
    sta COLBK

    ; Efekt tęczy (8 linii skanowania znaku)
    ldy #7
@tloop
    lda TextColors,y
    sta WSYNC
    sta COLPF2
    dey
    bpl @tloop
    lda TextColors,y
    sta COLPF2

    ; Przywrócenie stanu (kolory z title_colors.asm)
    lda #GRACTL_PM
    sta GRACTL
    lda #TITLE_COLBK
    sta COLBK
    lda #TITLE_COLPF0
    sta COLPF0
    lda #TITLE_COLPF1
    sta COLPF1
    lda #TITLE_COLPF2
    sta COLPF2
    lda #$00
    sta COLPF3

    ; Przywróć wektor DLI
    lda #<DLI_Handler
    sta VDSLST
    lda #>DLI_Handler
    sta VDSLST+1

    pla
    tax
    pla
    rti

;==============================================================
; Tabela kolorów tęczy — stopka tekstowa (8 pozycji)
;==============================================================
TextColors
    dta $90,$92,$94,$96,$98,$9A,$9C,$9E

;==============================================================
; DLI_Nop — Pusty handler DLI (używany przy przejściach między stanami)
;==============================================================
DLI_Nop
    rti

;==============================================================
; copy_title_footer — Przywraca tekst stopki tytułu ($5E10)
; Kopiuje 320 bajtów z TitleFooterROM → FOOTER_ADDR
; Niszczy: A, X, Y
;==============================================================
.proc copy_title_footer
    mRLE_Depack TitleFooterROM FOOTER_ADDR
    rts
.endp
