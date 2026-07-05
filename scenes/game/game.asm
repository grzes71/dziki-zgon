;----------------------------------------
; scenes/game/game.asm — Gra właściwa (ANTIC 4, 40×24 znaków)
;----------------------------------------

;---- Adresy pamięci dla gry (współdzielone z main.asm przez .global) ----
GAME_SCREEN_A5 = SCREEN      ; mapa 40×10 (ANTIC 5) = 400 bajtów
GAME_SCREEN_A2 = SCREEN+400  ; mapa 40×4 (ANTIC 2) = 160 bajtów
GAME_CHARSET  = $A800       ; charset gry — kafelki terenu (1 KB, CHBASE=$A8)

;---- Zmienne lokalne sceny ----
game_fire_released
    dta $00
game_stage
    dta $00             ; Aktualny etap gry (0-4)

; Zmienne przechowujące aktywne kolory dla obu stref (nadpisywane co etap)
; Paleta kolorów sprzętowych dla planszy (ANTIC 5) od PCOLR0 ($D012) do COLBK ($D01A)
game_palette
    .ds 9

; Paleta kolorów sprzętowych dla panelu statusu (ANTIC 2) od PCOLR0 do COLBK
game_status_palette
    .ds 9

; Offsety do tablic palet (dla każdego etapu: 0, 9, 18, 27, 36)
stage_palette_offsets
    dta 0, 9, 18, 27, 36

; Definicje wszystkich kolorów dla 5 etapów (gra właściwa)
; Kolejność rejestrów (9 bajtów):
; PCOLR0, PCOLR1, PCOLR2, PCOLR3, COLPF0, COLPF1, COLPF2, COLPF3, COLBK
stage_palettes
    ; Etap 0 (startowy)
    dta $14, $18, $C2, $82, $14, $18, $C2, $82, $00
    ; Etap 1
    dta $0E, $0E, $0E, $0E, $C8, $16, $0E, $00, $84
    ; Etap 2
    dta $0E, $0E, $0E, $0E, $C8, $16, $0E, $00, $74
    ; Etap 3
    dta $0E, $0E, $0E, $0E, $C8, $16, $0E, $00, $64
    ; Etap 4
    dta $0E, $0E, $0E, $0E, $C8, $16, $0E, $00, $54

; Definicje wszystkich kolorów dla 5 etapów (panel statusu)
stage_status_palettes
    ; Etap 0
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00
    ; Etap 1
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00
    ; Etap 2
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00
    ; Etap 3
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00
    ; Etap 4
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00

;==============================================================
; update_stage_colors — kopiuje odpowiednie kolory w oparciu o game_stage
;==============================================================
.proc update_stage_colors
    ldx game_stage
    ldy stage_palette_offsets,x
    
    ldx #0
@loop
    lda stage_palettes,y
    sta game_palette,x
    lda stage_status_palettes,y
    sta game_status_palette,x
    iny
    inx
    cpx #9
    bne @loop

    rts
.endp

;==============================================================
; game_init — Konfiguracja ANTIC 4 + PMG
;==============================================================
.proc game_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta game_fire_released  ; zresetuj stan przycisku FIRE

    jsr pmg_clear_all
    
    ; --- Inicjalizacja kolorów wybranego etapu ---
    jsr update_stage_colors

    ; --- Display List gry (ANTIC 4) ---
    lda #<DLIST_GAME
    sta DLISTL
    lda #>DLIST_GAME
    sta DLISTH

    ; --- Wczytanie początkowego charsetu (górny panel gry, game.fnt) ---
    lda #$64
    sta CHBASE

    ; --- Kolory (początkowe, bezpieczne) ---
    lda #$00
    sta COLBK

    ; --- Inicjalizacja pierwszej mapy ---
    lda #START_SCREEN_ID
    sta GAME_SCREEN_ID

    ; --- Wypełnij mapę (ANTIC 5 i ANTIC 2) ---
    jsr clear_game_screens
    
    ; --- Zbuduj ekran gry bazując na World Builderze ---
    jsr build_screen

    ; --- PMG: rozmiar normalny, włącz PMG ---
    lda #$00
    sta SIZEP0
    sta SIZEM
    lda #PRIOR_5TH
    sta PRIOR
    lda #>PMBASE_ADDR
    sta PMBASE
    lda #GRACTL_PM
    sta GRACTL
    lda #$60
    sta HPOSP0

    ; --- Przygotuj przerwania DLI ---
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta DMACTL
    lda #$80             ; włącz DLI
    sta NMIEN

    rts
.endp

;==============================================================
; clear_game_screens — Zeruje pamięć ekranów (ANTIC 5 + ANTIC 2)
; Łącznie do wyzerowania 560 bajtów (400 + 160).
;==============================================================
.proc clear_game_screens
    lda #0
    tax
@loop
    sta GAME_SCREEN_A5,x
    sta GAME_SCREEN_A5+$0100,x
    cpx #$30                ; 512 + 48 = 560 bajtów
    bcs @skip
    sta GAME_SCREEN_A5+$0200,x
@skip
    inx
    bne @loop
    rts
.endp

;==============================================================
; Tablice offsetów wierszy dla ANTIC 5 (szerokość = 40)
; Używane do błyskawicznego obliczania adresów VRAM: Y * 40
;==============================================================
row_offsets_lo
    dta <(GAME_SCREEN_A5 + 0*40), <(GAME_SCREEN_A5 + 1*40), <(GAME_SCREEN_A5 + 2*40), <(GAME_SCREEN_A5 + 3*40)
    dta <(GAME_SCREEN_A5 + 4*40), <(GAME_SCREEN_A5 + 5*40), <(GAME_SCREEN_A5 + 6*40), <(GAME_SCREEN_A5 + 7*40)
    dta <(GAME_SCREEN_A5 + 8*40), <(GAME_SCREEN_A5 + 9*40)

row_offsets_hi
    dta >(GAME_SCREEN_A5 + 0*40), >(GAME_SCREEN_A5 + 1*40), >(GAME_SCREEN_A5 + 2*40), >(GAME_SCREEN_A5 + 3*40)
    dta >(GAME_SCREEN_A5 + 4*40), >(GAME_SCREEN_A5 + 5*40), >(GAME_SCREEN_A5 + 6*40), >(GAME_SCREEN_A5 + 7*40)
    dta >(GAME_SCREEN_A5 + 8*40), >(GAME_SCREEN_A5 + 9*40)

;==============================================================
; build_screen — buduje ekran z danych mapy dla GAME_SCREEN_ID
;==============================================================
.proc build_screen
    ldx GAME_SCREEN_ID
    lda SCREEN_POINTERS_LO,x
    sta SCREEN_PTR
    lda SCREEN_POINTERS_HI,x
    sta SCREEN_PTR+1

    ldy #0
    lda (SCREEN_PTR),y          ; Liczba obiektów
    beq @end                    ; Jeśli 0 -> koniec
    tax                         ; X = licznik obiektów

@object_loop
    iny
    lda (SCREEN_PTR),y
    sta OBJ_CODE
    
    iny
    lda (SCREEN_PTR),y
    sta OBJ_X

    iny
    lda (SCREEN_PTR),y
    sta OBJ_Y

    txa
    pha                         ; Zapisz licznik obiektów
    tya
    pha                         ; Zapisz offset SCREEN_PTR

    ; Wypakuj rozmiar
    ldx OBJ_CODE
    lda OBJ_SIZE,x
    
    ; Szerokość: górne 4 bity + 1
    pha
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1
    sta OBJ_W
    
    ; Wysokość: dolne 4 bity + 1
    pla
    and #$0F
    clc
    adc #1
    sta OBJ_H

    ; Pobierz wskaźnik kafelków
    lda OBJ_TILES_LO,x
    sta TILE_PTR
    lda OBJ_TILES_HI,x
    sta TILE_PTR+1

    ; Rysowanie
    lda #0
    sta TMP_Y
    ldx #0                      ; X = tile index

@row_loop
    lda #0
    sta TMP_X
    
    ; Oblicz DST_PTR używając tablic dla wiersza (OBJ_Y + TMP_Y)
    lda OBJ_Y
    clc
    adc TMP_Y
    tay                         ; Y = Screen Row Index
    
    lda row_offsets_lo,y
    clc
    adc OBJ_X
    sta DST_PTR
    lda row_offsets_hi,y
    adc #0
    sta DST_PTR+1

    ldy #0                      ; Y = offset w kolumnach na ekranie

@col_loop
    txa
    tay                         ; Y = indeks kafelka
    lda (TILE_PTR),y            ; Pobierz kafelek

    ldy TMP_X                   ; Y = kolumna (offset ekranu dla danego wiersza)
    sta (DST_PTR),y             ; Rysuj na ekran

    inx                         ; Następny kafelek
    
    inc TMP_X
    lda TMP_X
    cmp OBJ_W
    bne @col_loop

    inc TMP_Y
    lda TMP_Y
    cmp OBJ_H
    bne @row_loop

    ; Powrót do pętli głównej
    pla
    tay                         ; Przywróć Y offset w ekranie
    pla
    tax                         ; Przywróć X (licznik obiektów)

    dex
    beq @end
    jmp @object_loop

@end
    rts
.endp


;==============================================================
; Przerwania DLI
;==============================================================

.proc game_dli_1
    pha
    txa
    pha
    

    ; Ustawienie fontu dla górnej części ekranu (game.fnt pod $6400 -> CHBASE=$64)
    lda #$64
    sta CHBASE

    ; Ustawienie całej palety ze zdefiniowanej tablicy
    ldx #8
@set_colors
    lda game_palette,x
    sta PCOLR0,x         ; PCOLR0 to $D012, aż do COLBK $D01A
    dex
    bpl @set_colors

    ; Przygotuj wektor na drugie DLI
    lda #<game_dli_2
    sta VDSLST
    lda #>game_dli_2
    sta VDSLST+1

    pla
    tax
    pla
    rti
.endp

.proc game_dli_2
    pha
    txa
    pha


    ; Zmień font na font.fnt ($6000 -> CHBASE=$60)
    lda #$60
    sta CHBASE

    ; Ustawienie całej palety ze zdefiniowanej tablicy (status area)
    ldx #8
@set_status_colors
    lda game_status_palette,x
    sta PCOLR0,x         ; PCOLR0 to $D012, aż do COLBK $D01A
    dex
    bpl @set_status_colors

    ; Przywróć wektor na pierwsze DLI (na następną klatkę)
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    pla
    tax
    pla
    rti
.endp

;==============================================================
; game_run — Obsługa klatki (joystick + FIRE)
;==============================================================
.proc game_run
    lda game_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda TRIG0
    beq @move            ; wciąż trzyma — nie reaguj i idź do ruchu
    lda #1
    sta game_fire_released
    jmp @move

@check_press
    ; --- TEST: FIRE → następny etap ---
    lda TRIG0
    bne @move
    jsr advance_stage
    rts

@move
    ; --- Odczyt joysticka (PORT A, $D300) ---
    lda PORTA
    eor #$FF            ; neguj (0=neutral, 1=aktywny kierunek)

    ; GÓRA
    and #$01
    beq @chk_down
    dec HPOSP0

@chk_down
    lda PORTA
    eor #$FF
    and #$02
    beq @chk_left
    inc HPOSP0

@chk_left
    lda PORTA
    eor #$FF
    and #$04
    beq @chk_right
    dec HPOSP0

@chk_right
    lda PORTA
    eor #$FF
    and #$08
    beq @exit
    inc HPOSP0

@exit
    rts
.endp
