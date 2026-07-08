;----------------------------------------
; scenes/game/game.asm — Gra właściwa    
;----------------------------------------

;---- Adresy pamięci dla gry (współdzielone z main.asm przez .global) ----
GAME_SCREEN_A5 = SCREEN      ; mapa 40×10 (ANTIC 5) = 400 bajtów
GAME_SCREEN_A2 = SCREEN+400  ; mapa 40×4 (ANTIC 2) = 160 bajtów
GAME_CHARSET  = $A800       ; charset gry — kafelki terenu (1 KB, CHBASE=$A8)

;---- Zmienne lokalne sceny ----
game_fire_released
    dta $00
game_stage
    dta $00             ; Aktualny etap gry (0-4)
;==============================================================
; DANE STARTOWE (łatwe do edycji podczas testów mapy)
;==============================================================
DEBUG_START_SCREEN  dta SCREEN_ID_TAVERN

; Zmienne przechowujące aktywne kolory dla obu stref (nadpisywane co etap)
; Paleta kolorów sprzętowych dla planszy (ANTIC 5) od PCOLR0 ($D012) do COLBK ($D01A)
game_palette
    .ds 9

; Paleta kolorów sprzętowych dla panelu statusu (ANTIC 2) od PCOLR0 do COLBK
game_status_palette
    .ds 9

; Jedna wspólna paleta dla panelu statusu (ANTIC 2)
status_palette
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00

;==============================================================
; update_stage_colors — kopiuje odpowiednie kolory w oparciu o game_stage
;==============================================================
.proc update_stage_colors
    ldx game_stage
    ldy REGION_PALETTE_OFFSETS,x
    
    ldx #0
@loop
    lda REGION_PALETTES,y
    sta game_palette,x
    lda status_palette,x
    sta game_status_palette,x
    iny
    inx
    cpx #9
    bne @loop

    rts
.endp

;==============================================================
; game_init — Konfiguracja ANTIC 4 + PMG
;==============================================================
.proc game_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta game_fire_released  ; zresetuj stan przycisku FIRE
    
    ; Wyzeruj wszystkich aktorów
    ldx #MAX_ACTORS - 1
    lda #0
@clear_actors
    sta ACTOR_ACTIVE,x
    sta ACTOR_X,x
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_X,x
    sta ACTOR_INTENT_Y,x
    sta ACTOR_DIR,x
    sta ACTOR_ANIM_FRAME,x
    sta ACTOR_ANIM_TIMER,x
    sta ACTOR_ANIM_SPEED,x
    sta ACTOR_COLOR,x
    dex
    bpl @clear_actors

    ; Inicjalizacja głównego bohatera (Actor 0)
    ldx #0
    lda #1
    sta ACTOR_ACTIVE,x
    lda #6
    sta ACTOR_ANIM_SPEED,x
    lda #14
    sta ACTOR_HEIGHT,x
    lda #$0F
    sta ACTOR_COLOR,x
    
    ; Wskaźniki na klatki animacji i limity
    lda #<GERWALT_PTRS_TABLE
    sta ACTOR_PTRS_TABLE_LO,x
    lda #>GERWALT_PTRS_TABLE
    sta ACTOR_PTRS_TABLE_HI,x
    
    lda #<GERWALT_ANIM_LIMITS
    sta ACTOR_ANIM_LIMITS_LO,x
    lda #>GERWALT_ANIM_LIMITS
    sta ACTOR_ANIM_LIMITS_HI,x

    jsr pmg_clear_all
    
    ; Ustaw pozycję startową z World Buildera dla Aktora 0
    lda #START_POS_X
    asl
    asl
    clc
    adc #48
    sta ACTOR_X,x
    sta ACTOR_INTENT_X,x
    
    lda #START_POS_Y
    asl
    asl
    asl
    asl
    clc
    adc #32
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_Y,x

    ; --- Inicjalizacja kolorów wybranego etapu ---
    jsr update_stage_colors

    ; --- Display List gry (ANTIC 4) ---
    lda #<DLIST_GAME
    sta SDLSTL
    lda #>DLIST_GAME
    sta SDLSTH

    ; --- Wczytanie początkowego charsetu (górny panel gry, game.fnt) ---
    lda #$64
    sta CHBAS

    ; --- Kolory (początkowe, bezpieczne) ---
    lda #$00
    sta COLOR4

    ; --- Inicjalizacja pierwszej mapy ---
    lda #START_SCREEN_ID
    sta GAME_SCREEN_ID

    ; --- Wypełnij mapę (ANTIC 5 i ANTIC 2) ---
    jsr clear_game_screens
    
    ; --- Zbuduj ekran gry bazując na World Builderze ---
    jsr build_screen

    ; --- PMG: rozmiar normalny, włącz PMG ---
    lda #$00
    sta SIZEP0
    sta SIZEM
    lda #PRIOR_5TH
    sta GPRIOR
    lda #>PMBASE_ADDR
    sta PMBASE
    lda #GRACTL_PM
    sta GRACTL
    lda #$60
    sta HPOSP0

    jsr Render_Prepare

    ; --- Przygotuj przerwania DLI ---
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    ; --- VBLANK i DLI ON ---
    lda #<Engine_FrameHandler
    sta $0222
    lda #>Engine_FrameHandler
    sta $0223

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta SDMCTL
    lda #$C0             ; włącz DLI i VBLANK
    sta NMIEN

    rts
.endp

;==============================================================
; clear_game_screens — Zeruje pamięć ekranów (ANTIC 5 + ANTIC 2)
; Łącznie do wyzerowania 560 bajtów (400 + 160).
;==============================================================
.proc clear_game_screens
    lda #0
    tax
@loop
    sta GAME_SCREEN_A5,x
    sta GAME_SCREEN_A5+$0100,x
    cpx #$30                ; 512 + 48 = 560 bajtów
    bcs @skip
    sta GAME_SCREEN_A5+$0200,x
@skip
    inx
    bne @loop
    rts
.endp



;==============================================================
; Przerwania DLI
;==============================================================

.proc game_dli_1
    pha
    txa
    pha
    

    ; Ustawienie fontu dla górnej części ekranu (game.fnt pod $6400 -> CHBASE=$64)
    lda #$64
    sta CHBASE

    ; Ustawienie całej palety ze zdefiniowanej tablicy
    ldx #8
@set_colors
    lda game_palette,x
    sta PCOLR0,x         ; PCOLR0 to $D012, aż do COLBK $D01A
    dex
    bpl @set_colors

    ; Przygotuj wektor na drugie DLI
    lda #<game_dli_2
    sta VDSLST
    lda #>game_dli_2
    sta VDSLST+1

    pla
    tax
    pla
    rti
.endp

.proc game_dli_2
    pha
    txa
    pha


    ; Zmień font na font.fnt ($6000 -> CHBASE=$60)
    lda #$60
    sta CHBASE

    ; Ustawienie całej palety ze zdefiniowanej tablicy (status area)
    ldx #8
@set_status_colors
    lda game_status_palette,x
    sta PCOLR0,x         ; PCOLR0 to $D012, aż do COLBK $D01A
    dex
    bpl @set_status_colors

    ; Przywróć wektor na pierwsze DLI (na następną klatkę)
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    pla
    tax
    pla
    rti
.endp

