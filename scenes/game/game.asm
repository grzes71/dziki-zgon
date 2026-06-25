;----------------------------------------
; scenes/game/game.asm — Gra właściwa (ANTIC 4, 40×24 znaków)
;----------------------------------------

;---- Adresy pamięci dla gry (współdzielone z main.asm przez .global) ----
GAME_SCREEN   = $4000       ; mapa 40×24 = 960 bajtów
GAME_CHARSET  = $A000       ; charset gry — kafelki terenu (1 KB, CHBASE=$A0)

;==============================================================
; game_init — Konfiguracja ANTIC 4 + PMG
;==============================================================
.proc game_init
    lda #0
    sta DMACTL
    sta NMIEN

    jsr pmg_clear_all

    ; --- Display List gry (ANTIC 4) ---
    lda #<DLIST_GAME
    sta DLISTL
    lda #>DLIST_GAME
    sta DLISTH

    ; --- Charset gry ($A000, używamy font.asm jako placeholder) ---
    lda #$A0
    sta CHBASE

    ; --- Kolory gry (4 kolory: trawa, woda, góry, chaty) ---
    lda #$94             ; ciemny niebieski — niebo/woda
    sta COLBK
    lda #$C8             ; zielony — trawa
    sta COLPF0
    lda #$16             ; brązowy — góry/ziemia
    sta COLPF1
    lda #$0E             ; biały/szary — budynki
    sta COLPF2
    lda #$00             ; czarny — obrysy/PMG 5th player
    sta COLPF3

    ; --- PMG: rozmiar normalny, kolor biały dla gracza ---
    lda #$00
    sta SIZEP0
    sta SIZEM
    lda #$0E
    sta PCOLR0
    lda #PRIOR_5TH
    sta PRIOR

    lda #>PMBASE_ADDR
    sta PMBASE
    lda #GRACTL_PM
    sta GRACTL

    ; --- Pozycja startowa gracza (na środku) ---
    lda #$60
    sta HPOSP0

    ; --- Wypełnij mapę testową (placeholder — potem dane z pliku) ---
    jsr fill_test_map

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta DMACTL
    lda #$00             ; bez DLI na razie
    sta NMIEN

    rts
.endp

;==============================================================
; fill_test_map — Wypełnia GAME_SCREEN wzorem testowym
;==============================================================
.proc fill_test_map
    ldx #0
@row
    ; 40 znaków na wiersz, 24 wiersze
    txa
    lsr @               ; X/4 → różne kafelki co 4 wiersze
    lsr @
    and #$03            ; 4 rodzaje terenu
    tay
    lda TestTiles,y     ; wybierz kafelek

    ldy #40
@col
    sta GAME_SCREEN,x
    inx
    dey
    bne @col

    cpx #<$03C0          ; 24 × 40 = 960 = $03C0
    bne @row

    rts

TestTiles
    dta $00,$28,$50,$78  ; 4 testowe kafelki (co 40 znaków w charset)
.endp

;==============================================================
; game_run — Obsługa klatki (joystick + FIRE)
;==============================================================
.proc game_run
    ; --- TEST: FIRE → gameover ---
    lda TRIG0
    bne @move
    lda #STATE_OVER
    sta GAME_STATE
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
