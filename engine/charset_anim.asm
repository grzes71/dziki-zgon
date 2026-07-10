;----------------------------------------
; engine/charset_anim.asm
;----------------------------------------

ANIM_CHAR_COUNT = 5

.proc animate_charset
    ; Zachowaj wskaźnik SRC_PTR na stosie
    lda SRC_PTR
    pha
    lda SRC_PTR+1
    pha

    ldx #ANIM_CHAR_COUNT-1
@loop
    ; Zmniejsz licznik dla danego znaku
    dec anim_char_counters,x
    bne @next_char

    ; Reset licznika do wartości prędkości
    lda anim_char_speeds,x
    sta anim_char_counters,x

    ; Oblicz adres znaku: GAME_CHARSET + ID * 8
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
    adc #$A8            ; GAME_CHARSET ($A800) -> high byte is $A8
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

anim_char_ids
    dta $05, $20, $40, $65, $66

anim_char_speeds
    dta 10, 10, 10, 10, 10

anim_char_counters
    dta 10, 10, 10, 10, 10
.endp
