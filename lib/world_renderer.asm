;----------------------------------------
; lib/world_renderer.asm — Silnik renderujący świat (World Builder)
;----------------------------------------

;==============================================================
; Tablice offsetów wierszy dla ANTIC 5 (szerokość = 40)
; Używane do błyskawicznego obliczania adresów VRAM: Y * 40
;==============================================================
row_offsets_lo
    dta <(GAME_SCREEN_A5 + 0*40), <(GAME_SCREEN_A5 + 1*40), <(GAME_SCREEN_A5 + 2*40), <(GAME_SCREEN_A5 + 3*40)
    dta <(GAME_SCREEN_A5 + 4*40), <(GAME_SCREEN_A5 + 5*40), <(GAME_SCREEN_A5 + 6*40), <(GAME_SCREEN_A5 + 7*40)
    dta <(GAME_SCREEN_A5 + 8*40), <(GAME_SCREEN_A5 + 9*40), <(GAME_SCREEN_A5 + 10*40), <(GAME_SCREEN_A5 + 11*40)

row_offsets_hi
    dta >(GAME_SCREEN_A5 + 0*40), >(GAME_SCREEN_A5 + 1*40), >(GAME_SCREEN_A5 + 2*40), >(GAME_SCREEN_A5 + 3*40)
    dta >(GAME_SCREEN_A5 + 4*40), >(GAME_SCREEN_A5 + 5*40), >(GAME_SCREEN_A5 + 6*40), >(GAME_SCREEN_A5 + 7*40)
    dta >(GAME_SCREEN_A5 + 8*40), >(GAME_SCREEN_A5 + 9*40), >(GAME_SCREEN_A5 + 10*40), >(GAME_SCREEN_A5 + 11*40)

;==============================================================
; build_screen — buduje ekran z danych mapy dla GAME_SCREEN_ID
;==============================================================
.proc build_screen
    ; 1. Wyczyść COLLISION_GRID (60 bajtów)
    ldy #59
    lda #0
@clear_grid
    sta COLLISION_GRID,y
    dey
    bpl @clear_grid

    ldx GAME_SCREEN_ID
    lda SCREEN_POINTERS_LO,x
    sta SCREEN_PTR
    lda SCREEN_POINTERS_HI,x
    sta SCREEN_PTR+1

    ldy #0
    lda (SCREEN_PTR),y          ; Liczba obiektów
    bne @start_objects
    jmp @end                    ; Jeśli 0 -> koniec
@start_objects
    tax                         ; X = licznik obiektów

@object_loop
    ; Advance SCREEN_PTR by 1
    inc SCREEN_PTR
    bne @read_code
    inc SCREEN_PTR+1
@read_code
    ldy #0
    lda (SCREEN_PTR),y
    sta OBJ_CODE
    
    inc SCREEN_PTR
    bne @read_x
    inc SCREEN_PTR+1
@read_x
    lda (SCREEN_PTR),y
    sta OBJ_X

    inc SCREEN_PTR
    bne @read_y
    inc SCREEN_PTR+1
@read_y
    lda (SCREEN_PTR),y
    sta OBJ_Y

    txa
    pha                         ; Zapisz licznik obiektów

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

    ; --- Oznacz w siatce kolizji, jeśli obiekt jest blokujący ---
    ldx OBJ_CODE
    lda OBJ_FLAGS,x
    and #$80
    beq @skip_col_mark
    jsr mark_object_blocking
    ldx OBJ_CODE
@skip_col_mark

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
    tax                         ; Przywróć X (licznik obiektów)

    dex
    beq @end
    jmp @object_loop

@end
    jsr Load_Screen_Enemies
    rts
.endp

;==============================================================
; mark_object_blocking — oznacza obiekt w siatce COLLISION_GRID
; Wejście: OBJ_X, OBJ_Y, OBJ_W, OBJ_H
;==============================================================
.proc mark_object_blocking
    lda OBJ_Y
    sta TMP_Y_GRID
@row_loop
    lda OBJ_X
    sta TMP_X_GRID
@col_loop
    ; Oblicz Row * 5
    lda TMP_Y_GRID
    asl
    asl            ; Row * 4
    clc
    adc TMP_Y_GRID ; Row * 5
    sta TMP_GRID_INDEX

    ; Dodaj Col / 8
    lda TMP_X_GRID
    lsr
    lsr
    lsr            ; Col / 8
    clc
    adc TMP_GRID_INDEX
    tay            ; Y = index w COLLISION_GRID

    ; Oblicz bit mask (Col & 7)
    lda TMP_X_GRID
    and #$07
    tax            ; X = bit index (0..7)
    lda bit_masks,x

    ; Ustaw bit
    ora COLLISION_GRID,y
    sta COLLISION_GRID,y

    ; Kolumny loop
    inc TMP_X_GRID
    lda TMP_X_GRID
    sec
    sbc OBJ_X
    cmp OBJ_W
    bcc @col_loop

    ; Wiersze loop
    inc TMP_Y_GRID
    lda TMP_Y_GRID
    sec
    sbc OBJ_Y
    cmp OBJ_H
    bcc @row_loop

    rts

bit_masks
    dta $80, $40, $20, $10, $08, $04, $02, $01

TMP_X_GRID     dta $00
TMP_Y_GRID     dta $00
TMP_GRID_INDEX dta $00
.endp

