;----------------------------------------
; engine/collision.asm
;----------------------------------------

.proc Collision_Update
    ldx #0
@actor_loop
    lda ACTOR_ACTIVE,x
    bne @do_actor
    jmp @next_actor
@do_actor

    ; Copy current actor's intent and height to ZP temp variables
    lda ACTOR_INTENT_X,x
    sta ACTOR_TMP_X
    lda ACTOR_INTENT_Y,x
    sta ACTOR_TMP_Y
    lda ACTOR_HEIGHT,x
    sta ACTOR_TMP_HEIGHT

    ; Limity dla osi X (SCREEN_LIMIT_LEFT - SCREEN_LIMIT_RIGHT)
    lda ACTOR_TMP_X
    cmp #SCREEN_LIMIT_LEFT
    bcc @hit_left
    cmp #SCREEN_LIMIT_RIGHT
    bcs @hit_right
    jmp @check_y

@hit_left
    cpx #0
    bne @clamp_left
    ; Player hit West edge
    lda GAME_SCREEN_ID
    asl
    asl
    tay
    lda EXITS_TABLE+2,y ; West exit
    cmp #$FF
    beq @clamp_left
    ; Valid exit
    sta NEW_SCREEN_ID
    lda #1
    sta REQ_SCREEN_TRANSITION
    lda #TRANSITION_SPAWN_RIGHT
    sta NEW_ACTOR_X
    lda ACTOR_TMP_Y
    sta NEW_ACTOR_Y
    jmp @next_actor

@clamp_left
    lda #SCREEN_LIMIT_LEFT
    sta ACTOR_TMP_X
    jmp @check_y

@hit_right
    cpx #0
    bne @clamp_right
    ; Player hit East edge
    lda GAME_SCREEN_ID
    asl
    asl
    tay
    lda EXITS_TABLE+3,y ; East exit
    cmp #$FF
    beq @clamp_right
    ; Valid exit
    sta NEW_SCREEN_ID
    lda #1
    sta REQ_SCREEN_TRANSITION
    lda #TRANSITION_SPAWN_LEFT
    sta NEW_ACTOR_X
    lda ACTOR_TMP_Y
    sta NEW_ACTOR_Y
    jmp @next_actor

@clamp_right
    lda #SCREEN_LIMIT_RIGHT
    sta ACTOR_TMP_X

@check_y
    ; Limity dla osi Y (SCREEN_LIMIT_TOP - SCREEN_LIMIT_BOTTOM) 
@apply_y
    lda ACTOR_TMP_Y
    cmp #SCREEN_LIMIT_TOP
    bcc @hit_top
    cmp #SCREEN_LIMIT_BOTTOM
    bcs @hit_bottom
    jmp @screen_ok

@hit_top
    cpx #0
    bne @clamp_top
    ; Player hit North edge
    lda GAME_SCREEN_ID
    asl
    asl
    tay
    lda EXITS_TABLE+0,y ; North exit
    cmp #$FF
    beq @clamp_top
    ; Valid exit
    sta NEW_SCREEN_ID
    lda #1
    sta REQ_SCREEN_TRANSITION
    lda ACTOR_TMP_X
    sta NEW_ACTOR_X
    lda #TRANSITION_SPAWN_BOTTOM
    sta NEW_ACTOR_Y
    jmp @next_actor

@clamp_top
    lda #SCREEN_LIMIT_TOP
    sta ACTOR_TMP_Y
    jmp @screen_ok

@hit_bottom
    cpx #0
    bne @clamp_bottom
    ; Player hit South edge
    lda GAME_SCREEN_ID
    asl
    asl
    tay
    lda EXITS_TABLE+1,y ; South exit
    cmp #$FF
    beq @clamp_bottom
    ; Valid exit
    sta NEW_SCREEN_ID
    lda #1
    sta REQ_SCREEN_TRANSITION
    lda ACTOR_TMP_X
    sta NEW_ACTOR_X
    lda #TRANSITION_SPAWN_TOP
    sta NEW_ACTOR_Y
    jmp @next_actor

@clamp_bottom
    lda #SCREEN_LIMIT_BOTTOM
    sta ACTOR_TMP_Y

@screen_ok
    ; Save actor index on stack before calling world collision
    txa
    pha

    ; Weryfikacja kolizji z obiektami świata
    jsr Check_Objects_Collision
    cmp #1
    beq @reject

    ; Pop actor index
    pla
    tax

@apply
    ; Aplikujemy zweryfikowaną intencję do rzeczywistej pozycji aktora
    lda ACTOR_TMP_X
    sta ACTOR_X,x
    lda ACTOR_TMP_Y
    sta ACTOR_Y,x
    jmp @next_actor
    
@reject
    pla
    tax
    
@next_actor
    inx
    cpx #MAX_ACTORS
    beq @done_loop
    jmp @actor_loop
@done_loop
    rts
.endp

.proc Check_Objects_Collision
    ; Zwraca: A = 1 (kolizja), A = 0 (brak kolizji)
    
    ; 1. Oblicz Y2 = Pixel_Y + Height - 1
    lda ACTOR_TMP_Y
    clc
    adc ACTOR_TMP_HEIGHT
    sec
    sbc #1
    sta col_tmp_y2
    
    ; Jeśli Y2 < 32 -> brak kolizji (gracz nad mapą)
    cmp #32
    bcs @y2_ok
    lda #0
    rts
@y2_ok
    ; Grid_Y2 = (Y2 - 32) / 16
    sec
    sbc #32
    lsr
    lsr
    lsr
    lsr
    sta col_grid_y2
    
    ; Oblicz Grid_Y1 = (Pixel_Y - 32) / 16
    lda ACTOR_TMP_Y
    cmp #32
    bcs @y1_ok
    lda #0
    sta col_grid_y1
    jmp @x_coords
@y1_ok
    sec
    sbc #32
    lsr
    lsr
    lsr
    lsr
    sta col_grid_y1
    
@x_coords
    ; Oblicz Grid_X1 = (Pixel_X - 48) / 4
    lda ACTOR_TMP_X
    sec
    sbc #48
    lsr
    lsr
    sta col_grid_x1
    
    ; Oblicz Grid_X2 = (Pixel_X - 48 + 7) / 4
    lda ACTOR_TMP_X
    sec
    sbc #48
    clc
    adc #7
    lsr
    lsr
    sta col_grid_x2
    
    ; Ogranicz współrzędne siatki (clamp)
    lda col_grid_y2
    cmp #12
    bcc @y2_clamp_ok
    lda #11
    sta col_grid_y2
@y2_clamp_ok

    lda col_grid_x2
    cmp #40
    bcc @x2_clamp_ok
    lda #39
    sta col_grid_x2
@x2_clamp_ok

    ; Szybka pętla po wierszach od Grid_Y1 do Grid_Y2
    ; i kolumnach od Grid_X1 do Grid_X2
    
    lda col_grid_y1
    sta col_curr_y
@row_loop
    lda col_grid_x1
    sta col_curr_x
@col_loop
    ; Sprawdź bit na (col_curr_x, col_curr_y)
    
    ; Index = col_curr_y * 5 + col_curr_x / 8
    lda col_curr_y
    asl
    asl
    clc
    adc col_curr_y ; Y * 5
    
    sta col_curr_idx
    lda col_curr_x
    lsr
    lsr
    lsr            ; X / 8
    clc
    adc col_curr_idx
    tay            ; index w COLLISION_GRID
    
    lda col_curr_x
    and #$07
    tax
    lda bit_masks,x ; maska bitu
    
    and COLLISION_GRID,y
    beq @no_col_cell
    
    ; Wykryto kolizję!
    lda #1
    rts
    
@no_col_cell
    inc col_curr_x
    lda col_curr_x
    cmp col_grid_x2
    beq @col_loop
    bcc @col_loop

    inc col_curr_y
    lda col_curr_y
    cmp col_grid_y2
    beq @row_loop
    bcc @row_loop

    lda #0
    rts
    
bit_masks
    dta $80, $40, $20, $10, $08, $04, $02, $01

col_tmp_y2     dta $00
col_grid_y1    dta $00
col_grid_y2    dta $00
col_grid_x1    dta $00
col_grid_x2    dta $00
col_curr_x     dta $00
col_curr_y     dta $00
col_curr_idx   dta $00
.endp
