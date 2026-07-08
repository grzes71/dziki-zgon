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
    tax

    ; GÓRA
    and #$01
    beq @chk_down
    dec Player_Intent_Y

@chk_down
    txa
    and #$02
    beq @chk_left
    inc Player_Intent_Y

@chk_left
    txa
    and #$04
    beq @chk_right
    dec Player_Intent_X

@chk_right
    txa
    and #$08
    beq @done
    inc Player_Intent_X

@done
    rts
.endp
