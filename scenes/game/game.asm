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
hero_x
    dta 100
hero_y
    dta 100

;==============================================================
; DANE STARTOWE (łatwe do edycji podczas testów mapy)
;==============================================================
DEBUG_START_SCREEN  dta SCREEN_ID_TAVERN
DEBUG_START_X       dta 5
DEBUG_START_Y       dta 5

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

    jsr pmg_clear_all
    
    ; --- Inicjalizacja kolorów wybranego etapu ---
    jsr update_stage_colors

    ; --- Display List gry (ANTIC 4) ---
    lda #<DLIST_GAME
    sta DLISTL
    lda #>DLIST_GAME
    sta DLISTH

    ; --- Wczytanie początkowego charsetu (górny panel gry, game.fnt) ---
    lda #$64
    sta CHBASE

    ; --- Kolory (początkowe, bezpieczne) ---
    lda #$00
    sta COLBK

    ; --- Inicjalizacja pierwszej mapy ---
    lda DEBUG_START_SCREEN
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
    sta PRIOR
    lda #>PMBASE_ADDR
    sta PMBASE
    lda #GRACTL_PM
    sta GRACTL
    lda #$60
    sta HPOSP0

    jsr draw_hero

    ; --- Przygotuj przerwania DLI ---
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta DMACTL
    lda #$80             ; włącz DLI
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
; draw_hero — Rysuje gracza w PMG
;==============================================================
.proc draw_hero
    jsr pmg_clear_all
    
    ; Kopiowanie klatki GERWALT_RIGHT_FRAME_0 do bufora PMG gracza 0
    ldx #SPRITE_GERWALT_RIGHT_HEIGHT - 1
@loop
    lda GERWALT_RIGHT_FRAME_0,x
    pha
    txa
    clc
    adc hero_y
    tay
    pla
    sta PLAYER0,y
    dex
    bpl @loop
    
    ; Ustaw X i kolor
    lda hero_x
    sta HPOSP0
    lda #$0F
    sta PCOLR0
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

;==============================================================
; wait_frame — Czeka na początek sprzętowego VBLANK
;==============================================================
.proc wait_frame
@wait1
    lda VCOUNT
    cmp #120
    beq @wait1      ; Czekaj aż przestanie być VBLANK (jeśli już w nim jesteśmy)
@wait2
    lda VCOUNT
    cmp #120
    bne @wait2      ; Czekaj aż zacznie się nowy VBLANK
    rts
.endp

;==============================================================
; game_run — Obsługa klatki (joystick + FIRE)
;==============================================================
.proc game_run
    jsr wait_frame      ; synchronizacja 50 FPS i redukcja migotania

    lda game_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda TRIG0
    beq @move            ; wciąż trzyma — nie reaguj i idź do ruchu
    lda #1
    sta game_fire_released
    jmp @move

@check_press
    ; --- TEST: FIRE → następny etap ---
    lda TRIG0
    bne @move
    jsr advance_stage
    rts

@move
    ; --- Odczyt joysticka (PORT A, $D300) ---
    lda PORTA
    eor #$FF            ; neguj (0=neutral, 1=aktywny kierunek)
    tax

    ; GÓRA
    and #$01
    beq @chk_down
    dec hero_y

@chk_down
    txa
    and #$02
    beq @chk_left
    inc hero_y

@chk_left
    txa
    and #$04
    beq @chk_right
    dec hero_x

@chk_right
    txa
    and #$08
    beq @draw
    inc hero_x

@draw
    txa
    beq @exit
    jsr draw_hero

@exit
    rts
.endp
