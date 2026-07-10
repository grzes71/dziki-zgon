;----------------------------------------
; engine/render.asm
;----------------------------------------

.proc Render_Prepare
    ldx #0
@actor_loop
    lda ACTOR_ACTIVE,x
    bne @process_actor
    jmp @next_actor

@process_actor
    ; PMG_PTR = PMBASE_ADDR + $0400 + (X * $100)
    lda #0
    sta PMG_PTR
    txa
    clc
    adc #>(PMBASE_ADDR + $0400)
    sta PMG_PTR+1

    ; Czyścimy starą pozycję aktora w buforze PMG
    ldy ACTOR_HEIGHT,x
    dey
@clear_old
    tya
    clc
    adc ACTOR_Y_OLD,x
    tay
    
    lda #0
    sta (PMG_PTR),y
    
    tya
    sec
    sbc ACTOR_Y_OLD,x
    tay
    
    dey
    bpl @clear_old
    
    ; Pobranie bazowego wskaźnika do tablicy wskaźników kierunku dla tego aktora
    lda ACTOR_PTRS_TABLE_LO,x
    sta DST_PTR
    lda ACTOR_PTRS_TABLE_HI,x
    sta DST_PTR+1
    
    ; Obliczenie przesunięcia dla kierunku
    lda ACTOR_DIR,x
    asl
    tay
    
    ; Pobranie wskaźnika na tablicę klatek dla tego kierunku
    lda (DST_PTR),y
    sta SRC_TMP
    iny
    lda (DST_PTR),y
    sta SRC_TMP+1
    
    ; Obliczenie przesunięcia klatki wewnątrz tej tablicy
    lda ACTOR_ANIM_FRAME,x
    asl
    tay
    
    ; Zapisanie ostatecznego wskaźnika na klatkę do SRC_PTR
    lda (SRC_TMP),y
    sta SRC_PTR
    iny
    lda (SRC_TMP),y
    sta SRC_PTR+1

    ; Kopiowanie nowej klatki do bufora PMG (wskazywanego przez PMG_PTR)
    ldy ACTOR_HEIGHT,x
    dey
@loop
    lda (SRC_PTR),y
    pha          ; PUSH pixel data
    
    tya
    clc
    adc ACTOR_Y,x
    tay          ; Y = absolute target Y
    
    pla          ; PULL pixel data
    sta (PMG_PTR),y
    
    tya
    sec
    sbc ACTOR_Y,x
    tay          ; RESTORE original Y
    
    dey
    bpl @loop

    ; Zapamiętaj nową pozycję jako starą
    lda ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    
    ; Ustaw X i kolor (rejestry sprzętowe)
    lda ACTOR_X,x
    sta HPOSP0,x
    lda ACTOR_COLOR,x
    sta $02C0,x            ; Używamy OS shadow dla PCOLR0, aby SYSVBV go nie nadpisał złym kolorem

@next_actor
    inx
    cpx #MAX_ACTORS
    beq @done
    jmp @actor_loop
    
@done
    rts
.endp

; Tabele pozostają tutaj (są przypinane w game_init do ACTOR_PTRS_TABLE)
GERWALT_PTRS_TABLE
    dta a(GERWALT_RIGHT_PTRS)
    dta a(GERWALT_LEFT_PTRS)
    dta a(GERWALT_UP_PTRS)
    dta a(GERWALT_DOWN_PTRS)
