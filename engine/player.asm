;----------------------------------------
; engine/player.asm
;----------------------------------------

.proc Player_Update
    ; Pobierz aktualną pozycję jako domyślną intencję
    lda hero_x
    sta Player_Intent_X
    lda hero_y
    sta Player_Intent_Y

    ; Jeśli trigger był wciśnięty, zażądaj zmiany sceny
    lda game_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda InputState_Trig
    beq @move            ; wciąż trzyma
    lda #1
    sta game_fire_released
    jmp @move

@check_press
    lda InputState_Trig
    bne @move
    ; Poproś o zmianę sceny (flaga obsłużona w pętli głównej)
    lda #1
    sta Engine_RequestStageAdvance

@move
    lda InputState_Joy
    bne @is_moving

    ; Stoi w miejscu
    lda #0
    sta Player_AnimTimer
    sta Player_AnimFrame
    jmp @done

@is_moving
    tax

    ; GÓRA (2)
    and #$01
    beq @chk_down
    dec Player_Intent_Y
    lda #2
    sta Player_Dir

@chk_down
    txa
    and #$02
    beq @chk_left
    inc Player_Intent_Y
    lda #3
    sta Player_Dir

@chk_left
    txa
    and #$04
    beq @chk_right
    lda #1
    sta Player_Dir
    ; Zmniejszenie prędkości poziomej o połowę (ruch co drugą klatkę)
    lda FrameCounter
    and #$01
    bne @chk_right
    dec Player_Intent_X

@chk_right
    txa
    and #$08
    beq @anim
    lda #0
    sta Player_Dir
    ; Zmniejszenie prędkości poziomej o połowę (ruch co drugą klatkę)
    lda FrameCounter
    and #$01
    bne @anim
    inc Player_Intent_X

@anim
    ; Aktualizacja animacji
    inc Player_AnimTimer
    lda Player_AnimTimer
    cmp Player_AnimSpeed
    bne @done
    
    ; Reset timera
    lda #0
    sta Player_AnimTimer
    
    ; Zmiana klatki z uwzględnieniem limitu dla danego kierunku
    inc Player_AnimFrame
    ldx Player_Dir
    lda Player_AnimFrame
    cmp GERWALT_ANIM_LIMITS,x
    bcc @done
    ; Przekroczono limit, wracamy do klatki 0
    lda #0
    sta Player_AnimFrame

@done
    rts

GERWALT_ANIM_LIMITS
    dta SPRITE_GERWALT_RIGHT_FRAMES
    dta SPRITE_GERWALT_LEFT_FRAMES
    dta SPRITE_GERWALT_UP_FRAMES
    dta SPRITE_GERWALT_DOWN_FRAMES
.endp
