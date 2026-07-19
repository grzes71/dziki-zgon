;----------------------------------------
; engine/charset_anim.asm
;----------------------------------------

    icl "../gen/rotated_chars_global.asm"

anim_chars_active_mask
    dta 0

.proc animate_charset
    ; Zachowaj wskaźnik SRC_PTR na stosie
    lda SRC_PTR
    pha
    lda SRC_PTR+1
    pha

    ldx #ANIM_CHAR_COUNT-1
@loop
    ; Sprawdź czy znak jest aktywny na tym ekranie
    lda anim_chars_active_mask
    and anim_char_bit_masks,x
    beq @next_char

    ; Zmniejsz licznik dla danego znaku
    dec anim_char_counters,x
    bne @next_char

    ; Reset licznika do wartości prędkości
    lda anim_char_speeds,x
    sta anim_char_counters,x

    ; Oblicz adres znaku: GAME_CHARSET ($6400) + ID * 8
    lda #0
    sta SRC_PTR+1
    lda anim_char_ids,x
    asl
    rol SRC_PTR+1
    asl
    rol SRC_PTR+1
    asl
    rol SRC_PTR+1
    
    clc
    sta SRC_PTR
    lda SRC_PTR+1
    adc #$64            ; GAME_CHARSET ($6400) -> high byte is $64
    sta SRC_PTR+1

    ; Zroluj 8 bajtów znaku w lewo o 2 bity (ROL ROL)
    ldy #7
@roll_loop
    lda (SRC_PTR),y
    asl
    adc #0
    asl
    adc #0
    sta (SRC_PTR),y
    dey
    bpl @roll_loop

@next_char
    dex
    bpl @loop

    ; Przywróć SRC_PTR ze stosu
    pla
    sta SRC_PTR+1
    pla
    sta SRC_PTR
    rts

    icl "../gen/rotated_chars_proc.asm"
.endp

.proc update_animated_charset
    .if NUM_ANIM_CHARS > 0
    ; Zachowaj wskaźniki na stosie
    lda SRC_PTR
    pha
    lda SRC_PTR+1
    pha
    lda DST_PTR
    pha
    lda DST_PTR+1
    pha

    ldx #NUM_ANIM_CHARS-1
@loop
    ; Sprawdź czy znak jest aktywny na tym ekranie
    lda anim_chars_active_mask
    and animated_char_bit_masks,x
    bne @is_active
    jmp @next_char
@is_active

    ; Zmniejsz licznik dla danego znaku
    dec animated_char_timers,x
    beq @timer_triggered
    jmp @next_char
@timer_triggered

    ; Pobierz i zaktualizuj indeks klatki
    lda animated_char_cur_frame,x
    clc
    adc #1
    sta animated_char_cur_frame,x

    ; Ustaw wskaźnik SRC_PTR na adres tabeli liczby klatek segmentów dla znaku X
    lda animated_char_seg_num_frames_lo,x
    sta SRC_PTR
    lda animated_char_seg_num_frames_hi,x
    sta SRC_PTR+1

    ; Pobierz indeks obecnego segmentu do Y
    ldy animated_char_cur_segment,x
    
    ; Pobierz liczbę klatek w obecnym segmencie
    lda (SRC_PTR),y

    ; Porównaj z nowym relative_frame_idx
    cmp animated_char_cur_frame,x
    bne @store_frame_directly

    ; Jeśli relative_frame_idx == num_frames, to koniec segmentu.
    ; Sprawdź czy powtarzamy segment
    lda animated_char_repeat_counter,x
    beq @next_segment

    ; Powtarzamy segment:
    dec animated_char_repeat_counter,x
    lda #0
    sta animated_char_cur_frame,x
    jmp @get_frame_data

@next_segment
    ; Przechodzimy do kolejnego segmentu
    lda animated_char_cur_segment,x
    clc
    adc #1
    cmp animated_char_num_segments,x
    bcc @store_segment
    lda #0                  ; Zawiń do pierwszego segmentu
@store_segment
    sta animated_char_cur_segment,x
    tay                     ; Y = nowy segment index

    ; Zainicjalizuj licznik powtórzeń dla nowego segmentu:
    ; Ustaw SRC_PTR na char{idx}_segment_repeats
    lda animated_char_seg_repeats_lo,x
    sta SRC_PTR
    lda animated_char_seg_repeats_hi,x
    sta SRC_PTR+1
    lda (SRC_PTR),y
    sta animated_char_repeat_counter,x

    ; Zresetuj relative_frame_idx do 0
    lda #0
    sta animated_char_cur_frame,x

@store_frame_directly
    ; relative_frame_idx jest poprawny

@get_frame_data
    ; Y = current segment index
    ldy animated_char_cur_segment,x

    ; Oblicz flat frame index = segment_frame_starts[Y] + relative_frame_idx
    ; Ustaw SRC_PTR na char{idx}_segment_frame_starts
    lda animated_char_seg_frame_starts_lo,x
    sta SRC_PTR
    lda animated_char_seg_frame_starts_hi,x
    sta SRC_PTR+1
    lda (SRC_PTR),y         ; A = segment_frame_starts[Y]
    clc
    adc animated_char_cur_frame,x
    tay                     ; Y = flat_frame_idx (global frame index)

    ; Ustaw wskaźnik SRC_PTR na adres tabeli czasów trwania (durations) dla znaku X
    lda animated_char_durations_lo,x
    sta SRC_PTR
    lda animated_char_durations_hi,x
    sta SRC_PTR+1
    
    ; Odczytaj czas trwania i zapisz go
    lda (SRC_PTR),y
    sta animated_char_timers,x

    ; Oblicz adres danych klatki: BaseAddress + FlatFrameIndex * 8
    lda animated_char_data_lo,x
    sta SRC_PTR
    lda animated_char_data_hi,x
    sta SRC_PTR+1

    ; Pomnóż Y (flat_frame_idx) przez 8 i dodaj do SRC_PTR bez niszczenia rejestru X
    tya                     ; A = flat_frame_idx
    asl                     ; * 2, carry w C
    ldy #0
    bcc @no_carry1
    ldy #1
@no_carry1
    asl                     ; * 4, carry w C
    bcc @no_carry2
    iny
@no_carry2
    asl                     ; * 8, carry w C
    bcc @no_carry3
    iny
@no_carry3
    ; A = low byte of offset, Y = high byte of offset
    clc
    adc SRC_PTR
    sta SRC_PTR
    tya                     ; A = high byte offset
    adc SRC_PTR+1
    sta SRC_PTR+1

    ; Ustaw DST_PTR na docelowy adres znaku w charset
    lda animated_char_dest_lo,x
    sta DST_PTR
    lda animated_char_dest_hi,x
    sta DST_PTR+1

    ; Kopiuj 8 bajtów z SRC_PTR do DST_PTR
    ldy #7
@copy_loop
    lda (SRC_PTR),y
    sta (DST_PTR),y
    dey
    bpl @copy_loop

@next_char
    dex
    bmi @done_loop
    jmp @loop
@done_loop

    ; Przywróć wskaźniki ze stosu
    pla
    sta DST_PTR+1
    pla
    sta DST_PTR
    pla
    sta SRC_PTR+1
    pla
    sta SRC_PTR
    .endif
    rts
.endp

.proc check_active_charset_animations
    ; Wyzeruj maskę aktywności znaków
    lda #0
    sta anim_chars_active_mask

    ldx #0
@loop
    lda GAME_SCREEN_A5,x
    jsr @check_char
    lda GAME_SCREEN_A5+240,x
    jsr @check_char
    inx
    cpx #240
    bne @loop
    rts

@check_char
    and #$7F                ; Ignoruj bit 7 (inwersja / kolor w ANTIC 4/5)
    pha                     ; Zachowaj A na stosie (kod znaku)

    ; Przeszukaj znaki rolowane
    ldy #ANIM_CHAR_COUNT-1
@rolled_loop
    cmp animate_charset.anim_char_ids,y
    bne @next_rolled
    ; Znaleziono - ustaw bit w masce
    lda anim_chars_active_mask
    ora anim_char_bit_masks,y
    sta anim_chars_active_mask
    pla                     ; Przywróć A
    rts
@next_rolled
    dey
    bpl @rolled_loop

    ; Przeszukaj znaki klatkowe
    .if NUM_ANIM_CHARS > 0
    ldy #NUM_ANIM_CHARS-1
@anim_loop
    cmp animated_char_ids,y
    bne @next_anim
    ; Znaleziono - ustaw bit w masce
    lda anim_chars_active_mask
    ora animated_char_bit_masks,y
    sta anim_chars_active_mask
    pla                     ; Przywróć A
    rts
@next_anim
    dey
    bpl @anim_loop
    .endif

    pla                     ; Przywróć A
    rts
.endp

    icl "../gen/animated_chars.asm"
