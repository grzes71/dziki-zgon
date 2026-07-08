;----------------------------------------
; engine/render.asm
;----------------------------------------

.proc Render_Prepare
    ; Przygotowanie danych rysowania i sprzętu przed VBLANK
    
    jsr pmg_clear_all
    
    ; Pobranie właściwego wskaźnika
    lda Player_Dir
    asl
    asl
    sta SRC_TMP     ; Dir * 4
    
    lda Player_AnimFrame
    asl             ; Frame * 2
    clc
    adc SRC_TMP
    tax
    
    lda GERWALT_ALL_FRAMES,x
    sta SRC_PTR
    lda GERWALT_ALL_FRAMES+1,x
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

GERWALT_ALL_FRAMES
    ; Right (0)
    dta a(GERWALT_RIGHT_FRAME_0)
    dta a(GERWALT_RIGHT_FRAME_1)
    ; Left (1)
    dta a(GERWALT_LEFT_FRAME_0)
    dta a(GERWALT_LEFT_FRAME_1)
    ; Up (2)
    dta a(GERWALT_UP_FRAME_0)
    dta a(GERWALT_UP_FRAME_1)
    ; Down (3)
    dta a(GERWALT_DOWN_FRAME_0)
    dta a(GERWALT_DOWN_FRAME_1)
.endp
