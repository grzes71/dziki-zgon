;----------------------------------------
; engine/render.asm — PMG Rendering Engine
; 4-Color Hero (P0+P1) & Enemies (P2, P3, 5th Player M0-M3)
;----------------------------------------

.proc Render_Prepare
    ;=========================================================
    ; 1. BOHATER (Actor 0) — 4-Kolorowy: Player 0 + Player 1
    ;=========================================================
    lda ACTOR_ACTIVE
    bne @hero_active
    lda #0
    sta HPOSP0
    sta HPOSP1
    jmp @render_enemies

@hero_active
    ; Czyścimy stary obszar w PLAYER0 i PLAYER1
    ldy ACTOR_HEIGHT
    dey
@clear_old_hero
    tya
    clc
    adc ACTOR_Y_OLD
    tax
    lda #0
    sta PLAYER0,x
    sta PLAYER1,x
    dey
    bpl @clear_old_hero

    ; Sprawdzenie limitu klatek Gerwalta
    ldy ACTOR_DIR
    lda ACTOR_ANIM_FRAME
    cmp GERWALT_ANIM_LIMITS,y
    bcc @hero_frame_ok
    lda #0
    sta ACTOR_ANIM_FRAME
@hero_frame_ok
    ; Wskaźnik na tablicę klatek dla bieżącego kierunku
    lda ACTOR_DIR
    asl
    tay
    lda GERWALT_P0_PTRS_TABLE,y
    sta SRC_TMP
    lda GERWALT_P0_PTRS_TABLE+1,y
    sta SRC_TMP+1

    lda GERWALT_P1_PTRS_TABLE,y
    sta PMG_PTR
    lda GERWALT_P1_PTRS_TABLE+1,y
    sta PMG_PTR+1

    ; Pobranie adresu klatki z wybranej tablicy kierunku
    lda ACTOR_ANIM_FRAME
    asl
    tay
    lda (SRC_TMP),y
    sta SRC_PTR
    iny
    lda (SRC_TMP),y
    sta SRC_PTR+1

    dey
    lda (PMG_PTR),y
    sta DST_PTR
    iny
    lda (PMG_PTR),y
    sta DST_PTR+1

    ; Kopiowanie klatki 4-kolorowej do PLAYER0 i PLAYER1
    ldy ACTOR_HEIGHT
    dey
@copy_hero
    tya
    clc
    adc ACTOR_Y
    tax
    lda (SRC_PTR),y
    sta PLAYER0,x
    lda (DST_PTR),y
    sta PLAYER1,x
    dey
    bpl @copy_hero

    ; Aktualizacja pozycji i rejestrów sprzętowych bohatera
    lda ACTOR_X
    sta HPOSP0
    sta HPOSP1
    lda ACTOR_Y
    sta ACTOR_Y_OLD

    ; Ustawienie kolorów sprzętowych (z obsługą błysku obrażeń)
    lda collision_active
    beq @hero_col_normal
    lda #HERO_COLOR_DAMAGE
    sta $02C0
    sta PCOLR0
    jmp @hero_col_done
@hero_col_normal
    lda #HERO_COLOR_0
    sta $02C0
    sta PCOLR0
@hero_col_done
    lda #HERO_COLOR_1
    sta $02C1
    sta PCOLR1

    ;=========================================================
    ; 2. PRZECIWNICY 1 i 2 (Aktorzy 1 i 2 -> Player 2 i 3)
    ;=========================================================
@render_enemies
    ldx #1
@enemy_loop
    lda ACTOR_ACTIVE,x
    bne @enemy_active
    lda #0
    sta HPOSP1,x
    jmp @next_enemy

@enemy_active
    ; PMG_PTR = PMBASE_ADDR + $0500 + (X * $100) -> X=1: $A600 (P2), X=2: $A700 (P3)
    lda #0
    sta PMG_PTR
    txa
    clc
    adc #>(PMBASE_ADDR + $0500)
    sta PMG_PTR+1

    ; Czyścimy starą pozycję
    ldy ACTOR_HEIGHT,x
    dey
@clear_old_enemy
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
    bpl @clear_old_enemy

    jsr get_actor_frame_ptr

    ; Kopiowanie nowej klatki
    ldy ACTOR_HEIGHT,x
    dey
@copy_enemy
    lda (SRC_PTR),y
    pha
    tya
    clc
    adc ACTOR_Y,x
    tay
    pla
    sta (PMG_PTR),y
    tya
    sec
    sbc ACTOR_Y,x
    tay
    dey
    bpl @copy_enemy

    lda ACTOR_X,x
    sta HPOSP1,x
    lda ACTOR_COLOR,x
    sta $02C1,x
    sta PCOLR1,x
    lda ACTOR_Y,x
    sta ACTOR_Y_OLD,x

@next_enemy
    inx
    cpx #3
    bne @enemy_loop

    ;=========================================================
    ; 3. PRZECIWNIK 3 (Actor 3) — 5. Gracz (4x Missiles M0-M3)
    ;=========================================================
    lda ACTOR_ACTIVE+3
    bne @a3_active
    lda #0
    sta HPOSM0
    sta HPOSM1
    sta HPOSM2
    sta HPOSM3
    jmp @render_done

@a3_active
    ldy ACTOR_HEIGHT+3
    dey
@clear_old_a3
    tya
    clc
    adc ACTOR_Y_OLD+3
    tax
    lda #0
    sta MISSILES,x
    dey
    bpl @clear_old_a3

    ldx #3
    jsr get_actor_frame_ptr

    ldy ACTOR_HEIGHT+3
    dey
@copy_a3
    tya
    clc
    adc ACTOR_Y+3
    tax
    lda (SRC_PTR),y
    sta MISSILES,x
    dey
    bpl @copy_a3

    ; 4 pociski (po 2 bity każdy, szerokość standardowa 2 clocks) obok siebie tworzą 8px sprite:
    ; M3: piksele 0..1 (bity 7..6) na pozycji X
    ; M2: piksele 2..3 (bity 5..4) na pozycji X+2
    ; M1: piksele 4..5 (bity 3..2) na pozycji X+4
    ; M0: piksele 6..7 (bity 1..0) na pozycji X+6
    lda ACTOR_X+3
    sta HPOSM3
    clc
    adc #2
    sta HPOSM2
    adc #2
    sta HPOSM1
    adc #2
    sta HPOSM0

    lda ACTOR_Y+3
    sta ACTOR_Y_OLD+3

@render_done
    rts
.endp

;==============================================================
; get_actor_frame_ptr — pobiera adres klatki animacji dla Aktora X (1..3)
; Wyjście: SRC_PTR wskazuje na dane klatki
;==============================================================
.proc get_actor_frame_ptr
    lda ACTOR_PTRS_TABLE_LO,x
    sta DST_PTR
    lda ACTOR_PTRS_TABLE_HI,x
    sta DST_PTR+1

    ; Offset kierunku = DIR * 2
    lda ACTOR_DIR,x
    asl
    tay
    lda (DST_PTR),y
    sta SRC_TMP
    iny
    lda (DST_PTR),y
    sta SRC_TMP+1

    ; Sprawdzenie limitu klatek
    lda ACTOR_ANIM_LIMITS_LO,x
    sta DST_PTR
    lda ACTOR_ANIM_LIMITS_HI,x
    sta DST_PTR+1
    ldy ACTOR_DIR,x
    lda ACTOR_ANIM_FRAME,x
    cmp (DST_PTR),y
    bcc @frame_valid
    lda #0
    sta ACTOR_ANIM_FRAME,x
@frame_valid
    ; Offset klatki = FRAME * 2
    lda ACTOR_ANIM_FRAME,x
    asl
    tay
    lda (SRC_TMP),y
    sta SRC_PTR
    iny
    lda (SRC_TMP),y
    sta SRC_PTR+1
    rts
.endp

;==============================================================
; Tabele wskaźników animacji Gerwalta (4-kolorowy: P0 i P1)
;==============================================================
GERWALT_P0_PTRS_TABLE
    dta a(GERWALT_RIGHT_P0_PTRS)
    dta a(GERWALT_LEFT_P0_PTRS)
    dta a(GERWALT_UP_P0_PTRS)
    dta a(GERWALT_DOWN_P0_PTRS)

GERWALT_P1_PTRS_TABLE
    dta a(GERWALT_RIGHT_P1_PTRS)
    dta a(GERWALT_LEFT_P1_PTRS)
    dta a(GERWALT_UP_P1_PTRS)
    dta a(GERWALT_DOWN_P1_PTRS)

; Alias dla kompatybilności wstecznej i testów
GERWALT_PTRS_TABLE = GERWALT_P0_PTRS_TABLE
