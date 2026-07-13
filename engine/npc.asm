;----------------------------------------
; engine/npc.asm — Silnik przeciwników / NPC
;----------------------------------------

; Wskaźniki na klatki animacji i limity dla przeciwników
KIKIMORA_PTRS_TABLE
    dta a(KIKIMORA_PTRS)
    dta a(KIKIMORA_PTRS)
    dta a(KIKIMORA_PTRS)
    dta a(KIKIMORA_PTRS)

KIKIMORA_ANIM_LIMITS
    dta SPRITE_KIKIMORA_FRAMES, SPRITE_KIKIMORA_FRAMES, SPRITE_KIKIMORA_FRAMES, SPRITE_KIKIMORA_FRAMES

STRZYGA_PTRS_TABLE
    dta a(STRZYGA_PTRS)
    dta a(STRZYGA_PTRS)
    dta a(STRZYGA_PTRS)
    dta a(STRZYGA_PTRS)

STRZYGA_ANIM_LIMITS
    dta SPRITE_STRZYGA_FRAMES, SPRITE_STRZYGA_FRAMES, SPRITE_STRZYGA_FRAMES, SPRITE_STRZYGA_FRAMES

BAZYLISZEK_PTRS_TABLE
    dta a(BAZYLISZEK_PTRS)
    dta a(BAZYLISZEK_PTRS)
    dta a(BAZYLISZEK_PTRS)
    dta a(BAZYLISZEK_PTRS)

BAZYLISZEK_ANIM_LIMITS
    dta SPRITE_BAZYLISZEK_FRAMES, SPRITE_BAZYLISZEK_FRAMES, SPRITE_BAZYLISZEK_FRAMES, SPRITE_BAZYLISZEK_FRAMES

SUKKUB_PTRS_TABLE
    dta a(SUKKUB_RIGHT_PTRS)
    dta a(SUKKUB_LEFT_PTRS)
    dta a(SUKKUB_RIGHT_PTRS)
    dta a(SUKKUB_LEFT_PTRS)

SUKKUB_ANIM_LIMITS
    dta SPRITE_SUKKUB_RIGHT_FRAMES, SPRITE_SUKKUB_LEFT_FRAMES, SPRITE_SUKKUB_RIGHT_FRAMES, SPRITE_SUKKUB_LEFT_FRAMES

ENEMY_PTRS_TABLE_LO
    dta <KIKIMORA_PTRS_TABLE
    dta <STRZYGA_PTRS_TABLE
    dta <BAZYLISZEK_PTRS_TABLE
    dta <SUKKUB_PTRS_TABLE

ENEMY_PTRS_TABLE_HI
    dta >KIKIMORA_PTRS_TABLE
    dta >STRZYGA_PTRS_TABLE
    dta >BAZYLISZEK_PTRS_TABLE
    dta >SUKKUB_PTRS_TABLE

ENEMY_LIMITS_LO
    dta <KIKIMORA_ANIM_LIMITS
    dta <STRZYGA_ANIM_LIMITS
    dta <BAZYLISZEK_ANIM_LIMITS
    dta <SUKKUB_ANIM_LIMITS

ENEMY_LIMITS_HI
    dta >KIKIMORA_ANIM_LIMITS
    dta >STRZYGA_ANIM_LIMITS
    dta >BAZYLISZEK_ANIM_LIMITS
    dta >SUKKUB_ANIM_LIMITS

ENEMY_HEIGHTS
    dta SPRITE_KIKIMORA_HEIGHT
    dta SPRITE_STRZYGA_HEIGHT
    dta SPRITE_BAZYLISZEK_HEIGHT
    dta SPRITE_SUKKUB_RIGHT_HEIGHT

ENEMY_SPEED_MASK
    dta 3 ; slow (moves every 4th frame)
    dta 1 ; medium (moves every 2nd frame)
    dta 0 ; fast (moves every frame)

;=========================================================
; Load_Screen_Enemies — Ładuje przeciwników ze SCREEN_PTR
;=========================================================
.proc Load_Screen_Enemies
    ; Zwiększamy wskaźnik o 1, aby wskazywał na bajt liczby przeciwników (za obiektami)
    jsr npc_advance_screen_ptr
    
    ldy #0
    lda (SCREEN_PTR),y
    sta ENEMY_COUNT_TMP
    
    lda #1
    sta CURRENT_ACTOR

@loop_enemies
    lda ENEMY_COUNT_TMP
    bne @continue_load
    jmp @deactivate_remaining
@continue_load
    
    ; Wczytanie typu przeciwnika
    jsr npc_advance_screen_ptr
    ldy #0
    lda (SCREEN_PTR),y
    sta OBJ_CODE                ; Tymczasowo przechowujemy typ w OBJ_CODE
    
    ; Wczytanie X (piksele)
    jsr npc_advance_screen_ptr
    lda (SCREEN_PTR),y
    ldx CURRENT_ACTOR
    sta ACTOR_X,x
    sta ACTOR_INTENT_X,x
    
    ; Wczytanie Y (piksele)
    jsr npc_advance_screen_ptr
    lda (SCREEN_PTR),y
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_Y,x
    
    ; Wczytanie strategii
    jsr npc_advance_screen_ptr
    lda (SCREEN_PTR),y
    cmp #2                      ; random?
    bne @store_strat
    
    ; Losujemy oś ruchu: 0 (horiz) lub 1 (vert)
    lda $D20A
    and #$01
@store_strat
    sta ACTOR_STRATEGY,x
    
    ; Wczytanie prędkości
    jsr npc_advance_screen_ptr
    lda (SCREEN_PTR),y
    sta ACTOR_SPEED,x
    
    ; Wczytanie koloru
    jsr npc_advance_screen_ptr
    lda (SCREEN_PTR),y
    sta ACTOR_COLOR,x
    
    ; Ustawienie domyślnych flag aktora
    lda #1
    sta ACTOR_ACTIVE,x
    
    lda #0
    sta ACTOR_ANIM_FRAME,x
    sta ACTOR_ANIM_TIMER,x
    lda #6                      ; Standardowa prędkość animacji
    sta ACTOR_ANIM_SPEED,x
    
    ; Ładowanie wskaźników i limitów na podstawie typu
    ldy OBJ_CODE
    lda ENEMY_HEIGHTS,y
    sta ACTOR_HEIGHT,x
    
    lda ENEMY_PTRS_TABLE_LO,y
    sta ACTOR_PTRS_TABLE_LO,x
    lda ENEMY_PTRS_TABLE_HI,y
    sta ACTOR_PTRS_TABLE_HI,x
    
    lda ENEMY_LIMITS_LO,y
    sta ACTOR_ANIM_LIMITS_LO,x
    lda ENEMY_LIMITS_HI,y
    sta ACTOR_ANIM_LIMITS_HI,x
    
    ; Wybór początkowego kierunku ruchu na podstawie strategii
    lda ACTOR_STRATEGY,x
    cmp #0
    bne @dir_vert
    
    ; Strategia pozioma: kierunek 0 (Right) lub 1 (Left)
    lda $D20A
    and #$01
    sta ACTOR_DIR,x
    jmp @next_iteration
    
@dir_vert
    ; Strategia pionowa: kierunek 2 (Up) lub 3 (Down)
    lda $D20A
    and #$01
    clc
    adc #2
    sta ACTOR_DIR,x
    
@next_iteration
    dec ENEMY_COUNT_TMP
    inc CURRENT_ACTOR
    jmp @loop_enemies

@deactivate_remaining
    ldx CURRENT_ACTOR
    cpx #MAX_ACTORS
    bcs @done
    lda #0
    sta ACTOR_ACTIVE,x
    inc CURRENT_ACTOR
    jmp @deactivate_remaining

@done
    rts
.endp

.proc npc_advance_screen_ptr
    inc SCREEN_PTR
    bne @ok
    inc SCREEN_PTR+1
@ok
    rts
.endp

;=========================================================
; NPC_Update — Porusza aktywnymi przeciwnikami
;=========================================================
.proc NPC_Update
    ldx #1                      ; Gracz to 0, przeciwnicy to 1..3
@npc_loop
    lda ACTOR_ACTIVE,x
    bne @active
    jmp @next_npc
@active
    
    ; Sprawdzenie prędkości ruchu dla tego przeciwnika
    ldy ACTOR_SPEED,x
    lda ENEMY_SPEED_MASK,y
    beq @move_now
    and FrameCounter
    beq @move_now
    jmp @next_npc               ; Pomiń ruch, jeśli to nie jest klatka ruchu
    
@move_now
    ; Sprawdzenie, czy ruch w poprzedniej klatce się powiódł
    lda ACTOR_X,x
    cmp ACTOR_INTENT_X,x
    bne @blocked
    lda ACTOR_Y,x
    cmp ACTOR_INTENT_Y,x
    beq @not_blocked
    
@blocked
    ; Nastąpiło zablokowanie o ścianę/przeszkodę -> zmiana kierunku
    lda ACTOR_DIR,x
    eor #$01
    sta ACTOR_DIR,x
    
@not_blocked
    ; Klonujemy aktualną pozycję do intencji
    lda ACTOR_X,x
    sta ACTOR_INTENT_X,x
    lda ACTOR_Y,x
    sta ACTOR_INTENT_Y,x
    
    ; Obliczenie nowej intencji pozycji
    lda ACTOR_DIR,x
    ; 0 = Right, 1 = Left, 2 = Up, 3 = Down
    cmp #0
    bne @chk_left
    inc ACTOR_INTENT_X,x
    jmp @animate
    
@chk_left
    cmp #1
    bne @chk_up
    dec ACTOR_INTENT_X,x
    jmp @animate
    
@chk_up
    cmp #2
    bne @chk_down
    dec ACTOR_INTENT_Y,x
    jmp @animate
    
@chk_down
    inc ACTOR_INTENT_Y,x
    
@animate
    ; Aktualizacja animacji klatki
    inc ACTOR_ANIM_TIMER,x
    lda ACTOR_ANIM_TIMER,x
    cmp ACTOR_ANIM_SPEED,x
    bne @next_npc
    
    lda #0
    sta ACTOR_ANIM_TIMER,x
    
    lda ACTOR_ANIM_LIMITS_LO,x
    sta SRC_PTR
    lda ACTOR_ANIM_LIMITS_HI,x
    sta SRC_PTR+1
    
    ldy ACTOR_DIR,x
    
    inc ACTOR_ANIM_FRAME,x
    lda ACTOR_ANIM_FRAME,x
    cmp (SRC_PTR),y
    bcc @next_npc
    
    lda #0
    sta ACTOR_ANIM_FRAME,x

@next_npc
    inx
    cpx #MAX_ACTORS
    bcs @done_npc
    jmp @npc_loop
@done_npc
    rts
.endp
