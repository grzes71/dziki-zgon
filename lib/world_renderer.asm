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
    rts
.endp
