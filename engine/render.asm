;----------------------------------------
; engine/render.asm
;----------------------------------------

.proc Render_Prepare
    ; Przygotowanie danych rysowania i sprzętu przed VBLANK
    
    jsr pmg_clear_all
    
    ; Pobranie bazowego wskaźnika do tablicy wskaźników kierunku
    lda Player_Dir
    asl
    tax
    lda GERWALT_PTRS_TABLE,x
    sta DST_PTR
    lda GERWALT_PTRS_TABLE+1,x
    sta DST_PTR+1
    
    ; Obliczenie przesunięcia klatki wewnątrz tej tablicy
    lda Player_AnimFrame
    asl
    tay
    
    ; Zapisanie ostatecznego wskaźnika na klatkę do SRC_PTR
    lda (DST_PTR),y
    sta SRC_PTR
    iny
    lda (DST_PTR),y
    sta SRC_PTR+1

    ; Kopiowanie do bufora PMG gracza 0
    ldy #SPRITE_GERWALT_RIGHT_HEIGHT - 1
@loop
    lda (SRC_PTR),y
    pha
    tya
    clc
    adc hero_y
    tax
    pla
    sta PLAYER0,x
    dey
    bpl @loop
    
    ; Ustaw X i kolor
    lda hero_x
    sta HPOSP0
    lda #$0F
    sta PCOLR0
    
    rts

GERWALT_PTRS_TABLE
    dta a(GERWALT_RIGHT_PTRS)
    dta a(GERWALT_LEFT_PTRS)
    dta a(GERWALT_UP_PTRS)
    dta a(GERWALT_DOWN_PTRS)
.endp
