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
    ; Ustaw kolor gracza na pomarańczowy (żeby go widzieć)
    lda #$24
    sta ACTOR_COLOR,x

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
    
    ; Zmniejszenie prędkości poziomej o połowę (ruch co drugie wejście do funkcji)
    lda player_move_toggle
    eor #$01
    sta player_move_toggle
    beq @chk_right
    dec ACTOR_INTENT_X,x

@chk_right
    tya
    and #$08
    beq @anim
    lda #0
    sta ACTOR_DIR,x
    
    ; Zmniejszenie prędkości poziomej o połowę (ruch co drugie wejście do funkcji)
    ; Używamy tego samego toggle co wyżej, bo w danym wykonaniu naciskamy tylko 1 kierunek (left lub right)
    lda player_move_toggle
    eor #$01
    sta player_move_toggle
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

player_move_toggle
    dta 0

.endp

GERWALT_ANIM_LIMITS
    dta SPRITE_GERWALT_RIGHT_FRAMES
    dta SPRITE_GERWALT_LEFT_FRAMES
    dta SPRITE_GERWALT_UP_FRAMES
    dta SPRITE_GERWALT_DOWN_FRAMES
