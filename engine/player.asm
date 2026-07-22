;----------------------------------------
; engine/player.asm
;----------------------------------------

.proc Player_Update
    ; Aktor 0 to gracz
    ldx #0
    lda ACTOR_ACTIVE,x
    bne @process
    rts

@process
    inc player_frame_counter

    ; Resetuj intencję do aktualnej pozycji (brak ruchu = stoisz)
    lda ACTOR_X,x
    sta ACTOR_INTENT_X,x
    lda ACTOR_Y,x
    sta ACTOR_INTENT_Y,x

    ; Zakomentowaliśmy zmianę sceny pod przyciskiem Fire, żeby umożliwić testy ruchu
    ; Jeśli będzie potrzebna, dodamy to później w docelowym miejscu w grze.

@move
    lda InputState_Joy
    bne @is_moving

    ; Stoi w miejscu
    lda #0
    sta ACTOR_ANIM_TIMER,x
    sta ACTOR_ANIM_FRAME,x
    jmp @done

@is_moving
    ; W X jest indeks aktora. Stan joysticka mamy w A.
    ; Zapiszmy stan joysticka do Y, by móc łatwo do niego wracać.
    tay

    ; check if vertical movement should be skipped (during collision, skip even frames)
    lda collision_active
    beq @vertical_ok
    lda player_frame_counter
    and #$01
    beq @chk_left
@vertical_ok

    ; GÓRA (2)
    tya
    and #$01
    beq @chk_down
    dec ACTOR_INTENT_Y,x
    lda #2
    sta ACTOR_DIR,x

@chk_down
    tya
    and #$02
    beq @chk_left
    inc ACTOR_INTENT_Y,x
    lda #3
    sta ACTOR_DIR,x

@chk_left
    tya
    and #$04
    beq @chk_right
    lda #1
    sta ACTOR_DIR,x
    
    jsr check_horizontal_move
    beq @chk_right
    dec ACTOR_INTENT_X,x

@chk_right
    tya
    and #$08
    beq @anim
    lda #0
    sta ACTOR_DIR,x
    
    jsr check_horizontal_move
    beq @anim
    inc ACTOR_INTENT_X,x

@anim
    ; Aktualizacja animacji
    inc ACTOR_ANIM_TIMER,x
    lda ACTOR_ANIM_TIMER,x
    cmp ACTOR_ANIM_SPEED,x
    bne @done
    
    ; Reset timera
    lda #0
    sta ACTOR_ANIM_TIMER,x
    
    ; Pobierz limit klatek dla bieżącego kierunku
    lda ACTOR_ANIM_LIMITS_LO,x
    sta SRC_PTR
    lda ACTOR_ANIM_LIMITS_HI,x
    sta SRC_PTR+1
    
    ldy ACTOR_DIR,x
    lda (SRC_PTR),y
    
    ; Zmiana klatki
    inc ACTOR_ANIM_FRAME,x
    lda ACTOR_ANIM_FRAME,x
    cmp (SRC_PTR),y
    bcc @done
    ; Przekroczono limit, wracamy do klatki 0
    lda #0
    sta ACTOR_ANIM_FRAME,x

@done
    rts
.endp

;==============================================================
; check_horizontal_move — pomocnicza procedura do decydowania o ruchu w poziomie
; Zwraca A=1 (ruch dozwolony) lub A=0 (brak ruchu w tej klatce)
;==============================================================
.proc check_horizontal_move
    lda collision_active
    beq @normal
    
    ; Kolizja: ruch co 4 klatki (gdy licznik % 4 == 1)
    lda player_frame_counter
    and #$03
    cmp #$01
    beq @ok
    lda #0
    rts
    
@normal
    ; Normalnie: ruch co 2 klatki (gdy licznik % 2 == 1)
    lda player_frame_counter
    and #$01
    cmp #$01
    beq @ok
    lda #0
    rts
    
@ok
    lda #1
    rts
.endp

player_frame_counter
    dta 0

GERWALT_ANIM_LIMITS
    dta SPRITE_GERWALT_RIGHT_FRAMES
    dta SPRITE_GERWALT_LEFT_FRAMES
    dta SPRITE_GERWALT_UP_FRAMES
    dta SPRITE_GERWALT_DOWN_FRAMES
