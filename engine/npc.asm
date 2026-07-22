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
    bne @not_random
    
    ; Losujemy oś ruchu: 0 (horiz) lub 1 (vert)
    lda $D20A
    and #$01
    jmp @store_strat
@not_random
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
    sta ACTOR_PAUSE_TIMER,x
    lda #6                      ; Standardowa prędkość animacji
    sta ACTOR_ANIM_SPEED,x
    
    ldy OBJ_CODE
    lda ENEMY_HEIGHTS,y
    sta ACTOR_HEIGHT,x
    
    tya
    sta ACTOR_TYPE,x
    
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
    cmp #3                      ; >= 3 (chaotic/patrol/pacing/snake)?
    bcc @not_chaotic_init
    
    ; Dla strategii >= 3 losujemy dowolny kierunek 0..3 (Right, Left, Up, Down)
    lda $D20A
    and #$03
    sta ACTOR_DIR,x
    jmp @next_iteration

@not_chaotic_init
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
    ; Sprawdzenie timera pauzy (dla strategii pacing)
    lda ACTOR_PAUSE_TIMER,x
    beq @not_paused
    
    dec ACTOR_PAUSE_TIMER,x
    
    ; Pozostawiamy aktualną pozycję
    lda ACTOR_X,x
    sta ACTOR_INTENT_X,x
    lda ACTOR_Y,x
    sta ACTOR_INTENT_Y,x
    
    ; Jeśli timer właśnie osiągnął 0, zmieniamy zwrot na przeciwny dla kolejnej klatki
    lda ACTOR_PAUSE_TIMER,x
    bne @skip_reverse
    
    lda ACTOR_DIR,x
    eor #$01
    sta ACTOR_DIR,x
@skip_reverse
    jmp @next_npc

@not_paused
    ; Sprawdzenie, czy ruch w poprzedniej klatce się powiódł
    lda ACTOR_X,x
    cmp ACTOR_INTENT_X,x
    bne @blocked
    lda ACTOR_Y,x
    cmp ACTOR_INTENT_Y,x
    beq @not_blocked_snake_check
    
@blocked
    ; Nastąpiło zablokowanie o ścianę/przeszkodę -> zmiana kierunku lub chaotic/patrol/pacing losowanie
    lda ACTOR_STRATEGY,x
    cmp #5                      ; pacing?
    bne @not_pacing
    
    ; Strategia pacing:
    ; Ustawiamy timer pauzy na 30 klatek (~0.5 sekundy) i stoimy w miejscu w tej klatce
    lda #30
    sta ACTOR_PAUSE_TIMER,x
    jmp @not_blocked

@not_pacing
    cmp #4                      ; patrol?
    bne @chk_chaotic
    
    ; Patrol bounce:
    ; Obrót w prawo (clockwise) na podstawie ROTATION_TABLE
    ldy ACTOR_DIR,x
    lda ROTATION_TABLE,y
    sta ACTOR_DIR,x
    jmp @not_blocked

@chk_chaotic
    cmp #3                      ; chaotic?
    bne @standard_bounce
    
    ; Chaotic bounce:
    ; Losujemy nową oś: 0 (poziom) lub 1 (pion)
    lda $D20A
    and #$01
    tay                         ; Y = nowa oś (0 lub 1)
    
    lda ACTOR_DIR,x             ; A = aktualny kierunek
    lsr                         ; A = aktualna oś (0 lub 1)
    
    sty SRC_TMP                 ; SRC_TMP = nowa oś
    cmp SRC_TMP
    beq @same_axis              ; Jeśli nowa oś == aktualna oś, zmieniamy tylko zwrot (reverse)
    
    ; Nowa oś jest inna. Losujemy kierunek na nowej osi (0 lub 1).
    lda $D20A
    and #$01                    ; A = 0 lub 1
    cpy #0                      ; czy nowa oś to poziom?
    beq @store_dir
    clc
    adc #2                      ; dla pionu dodajemy 2 -> 2 lub 3
    bne @store_dir              ; skok bezwarunkowy (ponieważ A != 0)
    
@same_axis
    lda ACTOR_DIR,x
    eor #$01                    ; Odwrócenie kierunku na tej samej osi
@store_dir
    sta ACTOR_DIR,x
    jmp @not_blocked
    
@standard_bounce
    lda ACTOR_DIR,x
    eor #$01
    sta ACTOR_DIR,x
    
@not_blocked_snake_check
    lda ACTOR_STRATEGY,x
    cmp #6                      ; snake?
    bne @chk_homing
    
    ; Snake strategy switch check:
    txa
    clc
    adc FrameCounter
    and #$3F                    ; co 64 klatki
    bne @not_blocked
    
    ; Losujemy nowy kierunek 0..3
    lda $D20A
    and #$03
    sta ACTOR_DIR,x
    jmp @not_blocked

@chk_homing
    cmp #7                      ; homing?
    bne @not_blocked
    
    ; Homing strategy recalculate check:
    txa
    clc
    adc FrameCounter
    and #$0F                    ; co 16 klatek
    bne @not_blocked
    
    ; Obliczanie odległości w osiach X i Y (do gracza na indeksie 0)
    ; 1. dx = abs(ACTOR_X - ACTOR_X,x)
    lda ACTOR_X
    sec
    sbc ACTOR_X,x
    bcs @dx_pos
    eor #$FF
    clc
    adc #1
@dx_pos
    sta SRC_TMP
    
    ; 2. dy = abs(ACTOR_Y - ACTOR_Y,x)
    lda ACTOR_Y
    sec
    sbc ACTOR_Y,x
    bcs @dy_pos
    eor #$FF
    clc
    adc #1
@dy_pos
    sta SRC_TMP+1
    
    ; 3. Porównanie dx i dy
    lda SRC_TMP
    cmp SRC_TMP+1
    bcc @move_vert
    
    ; Ruch w poziomie: porównanie współrzędnych X gracza i przeciwnika
    lda ACTOR_X
    cmp ACTOR_X,x
    bcs @go_right
    lda #1                      ; Left
    sta ACTOR_DIR,x
    jmp @not_blocked
@go_right
    lda #0                      ; Right
    sta ACTOR_DIR,x
    jmp @not_blocked
    
@move_vert
    ; Ruch w pionie: porównanie współrzędnych Y gracza i przeciwnika
    lda ACTOR_Y
    cmp ACTOR_Y,x
    bcs @go_down
    lda #2                      ; Up
    sta ACTOR_DIR,x
    jmp @not_blocked
@go_down
    lda #3                      ; Down
    sta ACTOR_DIR,x
    jmp @not_blocked

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

ROTATION_TABLE
    dta 3, 2, 0, 1
.endp
