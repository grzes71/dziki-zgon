;----------------------------------------
; engine/render.asm
;----------------------------------------

.proc Render_Prepare
    ; Przygotowanie danych rysowania i sprzętu przed VBLANK
    
    jsr pmg_clear_all
    
    ; Kopiowanie klatki GERWALT_RIGHT_FRAME_0 do bufora PMG gracza 0
    ldx #SPRITE_GERWALT_RIGHT_HEIGHT - 1
@loop
    lda GERWALT_RIGHT_FRAME_0,x
    pha
    txa
    clc
    adc hero_y
    tay
    pla
    sta PLAYER0,y
    dex
    bpl @loop
    
    ; Ustaw X i kolor
    lda hero_x
    sta HPOSP0
    lda #$0F
    sta PCOLR0
    
    rts
.endp
