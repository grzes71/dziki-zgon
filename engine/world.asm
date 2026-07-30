;----------------------------------------
; engine/world.asm
;----------------------------------------

.proc World_Update
    lda REQ_SCREEN_TRANSITION
    bne @do_update
    rts

@do_update
    ; Wyczyść flagę
    lda #0
    sta REQ_SCREEN_TRANSITION

    ; Wyłącz DMA (wygaś ekran do czerni), aby zniwelować rwanie i miganie palety/VRAM podczas przerysowywania
    sta SDMCTL
    sta DMACTL

    ; Jeśli to przejście przez portal, wyświetl 5-sekundowy ekran podróży
    lda IS_PORTAL_TRANSITION
    beq @skip_travel
    lda #0
    sta IS_PORTAL_TRANSITION
    jsr travel_screen_show

@skip_travel
    ; Ukryj duszka gracza (HPOSP0 = 0) oraz wyczyść PMG przed rysowaniem nowego ekranu,
    ; aby uniknąć fałszywych kolizji GTIA (P0PF) ze starymi współrzędnymi gracza
    lda #0
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
    jsr redraw_status_bar

    ; Wyczyść pamięć PMG oraz fałszywe kolizje sprzętowe GTIA powstałe podczas rysowania
    jsr pmg_clear_all
    jsr init_game_missiles
    lda #0
    sta HITCLR

    ; Przywróć Display List, charset i rejestry dla trybu gry
    lda #<DLIST_GAME
    sta SDLSTL
    sta DLISTL
    lda #>DLIST_GAME
    sta SDLSTH
    sta DLISTH

    lda #$64
    sta CHBAS
    sta CHBASE

    lda #<game_dli
    sta VDSLST
    lda #>game_dli
    sta VDSLST+1

    lda #$C0                ; DLI ON, VBI ON
    sta NMIEN

    ; Poczekaj na VBLANK przed włączeniem DMA, aby nowy ekran rozpoczął się czysto od góry
    jsr Engine_WaitFrame

    lda #DMA_PMG_ON         ; $2E (normal playfield + PMG DMA)
    sta SDMCTL
    sta DMACTL

    lda #3
    sta GRACTL              ; włącz PMG w GTIA


    lda #$C0                ; DLI ON, VBI ON
    sta NMIEN


@done
    rts
.endp
