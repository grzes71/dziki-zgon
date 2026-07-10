;----------------------------------------
; engine/world.asm
;----------------------------------------

.proc World_Update
    lda REQ_SCREEN_TRANSITION
    beq @done

    ; Wyczyść flagę
    lda #0
    sta REQ_SCREEN_TRANSITION

    ; Zaktualizuj ID ekranu
    lda NEW_SCREEN_ID
    sta GAME_SCREEN_ID

    ; Zaktualizuj pozycję gracza
    ldx #0
    lda NEW_ACTOR_X
    sta ACTOR_X,x
    sta ACTOR_INTENT_X,x
    lda NEW_ACTOR_Y
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_Y,x

    ; Przebuduj ekran
    jsr clear_game_screens
    jsr build_screen
    
    ; Wyczyść pamięć PMG, aby usunąć stare duszki pozycje
    jsr pmg_clear_all

@done
    rts
.endp
