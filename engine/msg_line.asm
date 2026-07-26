;----------------------------------------
; engine/msg_line.asm — Obsługa drugiej linii statusowej (MESSAGE LINE)
;----------------------------------------

msg_ptr_lo  dta $00
msg_ptr_hi  dta $00
msg_timer   dta $00
msg_len     dta $00
msg_offset  dta $00

msg_buf     .ds 36

;==============================================================
; msg_show — Rozpoczyna wyświetlanie komunikatu
; In: A = wskaźnik LO do ciągu znaków, Y = wskaźnik HI
;==============================================================
.proc msg_show
    sta msg_ptr_lo
    sty msg_ptr_hi
    jsr msg_present_next_sentence
    rts
.endp

;==============================================================
; msg_present_next_sentence — Parsuje i wyświetla jedno zdanie
;==============================================================
.proc msg_present_next_sentence
    ; 1. Kopiuj msg_ptr do ZP SRC_TMP
    lda msg_ptr_lo
    sta SRC_TMP
    lda msg_ptr_hi
    sta SRC_TMP+1

    ; 2. Wyczyszczenie tymczasowego bufora msg_buf (36 bajtów)
    ldx #35
    lda #0
@clr_buf
    sta msg_buf,x
    dex
    bpl @clr_buf

    ; 3. Pętla czytania i konwersji znaków
    ldy #0              ; offset w bajtach źródłowych
    ldx #0              ; licznik znaków w msg_buf (0..36)

@parse_loop
    cpx #36
    bcs @parse_done     ; max 36 znaków

    lda (SRC_TMP),y
    beq @parse_done     ; $00 = koniec ciągu
    cmp #$26            ; ASCII '&'
    beq @parse_done
    cmp #$06            ; screencode '&'
    beq @parse_done

    cmp #$C3
    bcc @ascii
    cmp #$C7
    bcs @ascii

    ; Sekwencja UTF-8 ($C3..$C6)
    jsr decode_utf8
    bcs @parse_done     ; błąd/nieoczekiwany EOF
    jmp @store_char

@ascii
    jsr convert_ascii_to_screencode

@store_char
    sta msg_buf,x
    inx
    iny
    jmp @parse_loop

@parse_done
    ; Zaktualizuj msg_ptr o liczbę przeczytanych bajtów Y
    tya
    clc
    adc msg_ptr_lo
    sta msg_ptr_lo
    bcc @no_hi_carry
    inc msg_ptr_hi
@no_hi_carry

    stx msg_len

    ; Oblicz przesunięcie centrujące P = (36 - L) / 2
    lda #36
    sec
    sbc msg_len
    lsr
    sta msg_offset

    ; Wyczyszczenie 36 znaków wiadomości w VRAM
    jsr clear_msg_line_display

    ; Kopiuj msg_buf do VRAM (od GAME_SCREEN_A2 + 42 + P)
    lda msg_len
    beq @finish_present

    ldx #0
@copy_to_vram
    lda msg_buf,x
    ldy msg_offset
    sta GAME_SCREEN_A2 + 42,y
    inc msg_offset
    inx
    cpx msg_len
    bne @copy_to_vram

@finish_present
    lda #1
    sta MSG_STATE       ; 1 = wyświetlanie zdania
    lda #250
    sta msg_timer       ; 5 sekund (250 klatek przy 50 Hz)
    rts
.endp

;==============================================================
; decode_utf8 — Dekoduje 2-bajtową sekwencję UTF-8 polskich znaków
; In: A = bajt 1 ($C3..$C6), Y = indeks bajtu 1 w (SRC_TMP)
; Out: A = screencode, Y = zaktualizowany indeks (bajt 2), Carry = 0 (OK) / 1 (Err)
;==============================================================
.proc decode_utf8
    cmp #$C3
    bne @not_c3
    jmp @c3
@not_c3
    cmp #$C4
    bne @not_c4
    jmp @c4
@not_c4
    cmp #$C5
    bne @not_c5
    jmp @c5
@not_c5
    cmp #$C6
    bne @err
    jmp @c6

@err
    sec
    rts

@c3
    iny
    lda (SRC_TMP),y
    bne @c3_ok
    jmp @err
@c3_ok
    cmp #$B3            ; 'ó'
    beq @is_o
    cmp #$93            ; 'Ó'
    beq @is_o
    lda #$5F
    clc
    rts
@is_o
    lda #$5F
    clc
    rts

@c4
    iny
    lda (SRC_TMP),y
    bne @c4_ok
    jmp @err
@c4_ok
    cmp #$85            ; 'ą'
    beq @is_a
    cmp #$84            ; 'Ą'
    beq @is_a
    cmp #$87            ; 'ć'
    beq @is_c
    cmp #$99            ; 'ę'
    beq @is_e
    cmp #$98            ; 'Ę'
    beq @is_e
    lda #$7B
    clc
    rts
@is_a
    lda #$7B
    clc
    rts
@is_c
    lda #$7C
    clc
    rts
@is_e
    lda #$7D
    clc
    rts

@c5
    iny
    lda (SRC_TMP),y
    bne @c5_ok
    jmp @err
@c5_ok
    cmp #$82            ; 'ł'
    beq @is_l
    cmp #$81            ; 'Ł'
    beq @is_l
    cmp #$84            ; 'ń'
    beq @is_n
    cmp #$83            ; 'Ń'
    beq @is_n
    cmp #$9B            ; 'ś'
    beq @is_s
    cmp #$9A            ; 'Ś'
    beq @is_s
    cmp #$BA            ; 'ź'
    beq @is_zi
    cmp #$B9            ; 'Ź'
    beq @is_zi
    cmp #$BC            ; 'ż'
    beq @is_z
    cmp #$BB            ; 'Ż'
    beq @is_z
    lda #$7E
    clc
    rts
@is_l
    lda #$7E
    clc
    rts
@is_n
    lda #$7F
    clc
    rts
@is_s
    lda #$5E
    clc
    rts
@is_zi
    lda #$5D
    clc
    rts
@is_z
    lda #$5C
    clc
    rts

@c6
    iny
    lda (SRC_TMP),y
    bne @c6_ok
    jmp @err
@c6_ok
    lda #$7C            ; 'Ć'
    clc
    rts
.endp

;==============================================================
; convert_ascii_to_screencode — Konwertuje pojedynczy znak ASCII/screencode
;==============================================================
.proc convert_ascii_to_screencode
    cmp #32
    bcc @screencode     ; < 32 -> już screencode (0..31)
    cmp #96
    bcc @ascii_upper    ; 32..95 -> odejmij 32 (32=' '->0, 65='A'->33, itd.)
    cmp #128
    bcc @done           ; 96..127 -> lowercase / pozostaw
@done
    rts
@ascii_upper
    sec
    sbc #32
    rts
@screencode
    rts
.endp

;==============================================================
; clear_msg_line_display — Czyszczenie 36 znaków linii wiadomości
;==============================================================
.proc clear_msg_line_display
    ldx #35
    lda #0
@clear
    sta GAME_SCREEN_A2 + 42,x
    dex
    bpl @clear
    rts
.endp

;==============================================================
; msg_update — Wywoływana z VBLANK co klatkę (50 Hz)
;==============================================================
.proc msg_update
    lda MSG_STATE
    beq @done           ; 0 = brak wiadomości

    dec msg_timer
    lda msg_timer
    cmp #50
    bne @chk_zero
    ; Pozostała 1 sekunda -> stan 2
    lda #2
    sta MSG_STATE
    rts

@chk_zero
    lda msg_timer
    beq @timer_zero
    rts

@timer_zero
    ; Koniec 5 sekund -> czyść i stan 0
    jsr clear_msg_line_display
    lda #0
    sta MSG_STATE

    ; Czy po separatorze '&' znajduje się kolejne zdanie?
    lda msg_ptr_lo
    sta SRC_TMP
    lda msg_ptr_hi
    sta SRC_TMP+1
    ldy #0
    lda (SRC_TMP),y
    cmp #$26            ; ASCII '&'
    beq @next_sentence
    cmp #$06            ; screencode '&'
    beq @next_sentence
    rts

@next_sentence
    inc msg_ptr_lo
    bne @no_hi
    inc msg_ptr_hi
@no_hi
    jsr msg_present_next_sentence

@done
    rts
.endp
