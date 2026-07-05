;----------------------------------------
; scenes/game/game.asm — Gra właściwa (ANTIC 4, 40×24 znaków)
;----------------------------------------

;---- Adresy pamięci dla gry (współdzielone z main.asm przez .global) ----
GAME_SCREEN_A5 = SCREEN      ; mapa 40×10 (ANTIC 5) = 400 bajtów
GAME_SCREEN_A2 = SCREEN+400  ; mapa 40×4 (ANTIC 2) = 160 bajtów
GAME_CHARSET  = $A800       ; charset gry — kafelki terenu (1 KB, CHBASE=$A8)

;---- Zmienne lokalne sceny ----
game_fire_released
    dta $00

; Paleta kolorów sprzętowych od PCOLR0 ($D012) do COLBK ($D01A)
game_palette
    dta $0E             ; PCOLR0
    dta $0E             ; PCOLR1
    dta $0E             ; PCOLR2
    dta $0E             ; PCOLR3
    dta $C8             ; COLPF0
    dta $16             ; COLPF1
    dta $0E             ; COLPF2
    dta $00             ; COLPF3
    dta $94             ; COLBK

;==============================================================
; game_init — Konfiguracja ANTIC 4 + PMG
;==============================================================
.proc game_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta game_fire_released  ; zresetuj stan przycisku FIRE

    jsr pmg_clear_all

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

    ; --- Wypełnij mapę (ANTIC 5 i ANTIC 2) ---
    jsr clear_game_screens

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
; Przerwania DLI
;==============================================================

.proc game_dli_1
    pha
    txa
    pha

    ; Ustawienie całej palety ze zdefiniowanej tablicy
    ldx #8
@set_colors
    lda game_palette,x
    sta PCOLR0,x         ; PCOLR0 to $D012, aż do COLBK $D01A
    dex
    bpl @set_colors

    ; Ustawienie fontu dla górnej części ekranu (game.fnt pod $6400 -> CHBASE=$64)
    lda #$64
    sta CHBASE

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

    sta WSYNC            ; stabilizacja
    lda #$00             ; czarne tło (lub inny kolor wg uznania)
    sta COLPF2           ; kolor tła w ANTIC 2
    lda #$0F             ; biały tekst
    sta COLPF1           ; kolor znaków w ANTIC 2

    ; Zmień font na font.fnt ($6000 -> CHBASE=$60)
    lda #$60
    sta CHBASE

    ; Przywróć wektor na pierwsze DLI (na następną klatkę)
    lda #<game_dli_1
    sta VDSLST
    lda #>game_dli_1
    sta VDSLST+1

    pla
    rti
.endp

;==============================================================
; game_run — Obsługa klatki (joystick + FIRE)
;==============================================================
.proc game_run
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

    ; GÓRA
    and #$01
    beq @chk_down
    dec HPOSP0

@chk_down
    lda PORTA
    eor #$FF
    and #$02
    beq @chk_left
    inc HPOSP0

@chk_left
    lda PORTA
    eor #$FF
    and #$04
    beq @chk_right
    dec HPOSP0

@chk_right
    lda PORTA
    eor #$FF
    and #$08
    beq @exit
    inc HPOSP0

@exit
    rts
.endp
