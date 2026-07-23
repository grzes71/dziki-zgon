;----------------------------------------
; engine/world.asm
;----------------------------------------

.proc World_Update
    lda REQ_SCREEN_TRANSITION
    beq @done

    ; Wyczyść flagę
    lda #0
    sta REQ_SCREEN_TRANSITION

    ; Ukryj duszka gracza (HPOSP0 = 0) oraz wyczyść PMG przed rysowaniem nowego ekranu,
    ; aby uniknąć fałszywych kolizji GTIA (P0PF) ze starymi współrzędnymi gracza
    sta HPOSP0
    jsr pmg_clear_all

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
    jsr check_active_charset_animations
    
    ; Zaktualizuj region i odśwież kolory oraz HUD
    ldx GAME_SCREEN_ID
    lda SCREEN_REGION,x
    sta game_stage
    jsr update_stage_colors
    jsr draw_region_name

    ; Wyczyść pamięć PMG oraz fałszywe kolizje sprzętowe GTIA powstałe podczas rysowania
    jsr pmg_clear_all
    lda #0
    sta HITCLR

@done
    rts
.endp
