	OPT h+

;---------------------------------------
; Atari XL/XE
; ANTIC E (160x192, 4 kolory) + PMG
;---------------------------------------

; ---- GTIA ----
HPOSP0  = $D000
HPOSP1  = $D001
HPOSP2  = $D002
HPOSP3  = $D003
HPOSM0  = $D004
HPOSM1  = $D005
HPOSM2  = $D006
HPOSM3  = $D007
SIZEP0  = $D008
SIZEP1  = $D009
SIZEP2  = $D00A
SIZEP3  = $D00B
SIZEM   = $D00C
PCOLR0  = $D012
PCOLR1  = $D013
PCOLR2  = $D014
PCOLR3  = $D015
COLPF3  = $D019
PRIOR   = $D01B
GRACTL  = $D01D

; ---- ANTIC ----
DMACTL  = $D400
DLISTL  = $D402
DLISTH  = $D403
PMBASE  = $D407
WSYNC   = $D40A
NMIEN   = $D40E

; ---- POKEY ----
IRQEN   = $D20E

; ---- OS shadows ----
SDMCTL  = 559
VDSLST  = $0200

SCREEN      = $4000
PMBASE_ADDR = $8000          ; PMG memory (1K-aligned)

; =====================================================================
; TŁO — zmień "title-2" na inny prefix (3 miejsca poniżej):
;   icl "title-2_colors.asm"
;   icl "title-2_displaylist.asm"
;   ins "title-2.bin"
; =====================================================================

; PMG data offsets — single-line resolution
; $000-$2FF: unused (768 B wolnych na zmienne/DLI)
MISSILES    = PMBASE_ADDR+$300  ; 128 B — wszystkie 4 missile w 1 bajcie/linia
PLAYER0     = PMBASE_ADDR+$400  ; 128 B
PLAYER1     = PMBASE_ADDR+$500  ; 128 B
PLAYER2     = PMBASE_ADDR+$600  ; 128 B
PLAYER3     = PMBASE_ADDR+$700  ; 128 B

; Sprite dimensions — tytuł
SPRITE_ROWS = 37
TOP_MARGIN  = 50

; Sprite dimensions — księżyc (4 graczy, 32px)
MOON_ROWS   = 24
MOON_TOP    = 114           ; pozycja Y księżyca (linia PMG)
MOON_X      = $28          ; pozycja X lewego skraju księżyca

; Gwiazdy — na missile'ach M0–M3 (niezależne HPOS + kolor)
STAR0_X     = $50           ; HPOS (było $10 — za bardzo w lewo)
STAR1_X     = $48
STAR2_X     = $60
STAR3_X     = $70

STAR0_Y     = 108           ; linia PMG — tuż nad księżycem
STAR1_Y     = 116           ; w obszarze księżyca
STAR2_Y     = 126
STAR3_Y     = 121

; PMG DMA start offset (blank lines $70×3 = 24 lines counted by PMG counter)
KOREKTA     = 8            ; dostrojone doświadczalnie
DL_BLANKS   = 24
DLI_DELAY   = TOP_MARGIN - DL_BLANKS - KOREKTA ; 26 - KOREKTA

; PMG positions (color clocks — side by side, x2 = 16px apart)
TITLE_X     = $34          ; lewy skraj całego napisu — zmień, żeby przesunąć
HPOS_P0     = TITLE_X
HPOS_P1     = TITLE_X+$10
HPOS_P2     = TITLE_X+$20
HPOS_P3     = TITLE_X+$30
HPOS_M      = TITLE_X+$40   ; 5th player — M3 (lewy skraj)

        org $2000

start
;---------------------------------------
; Pełne wyłączenie systemu i DMA na czas konfiguracji
;---------------------------------------
        sei                 ; Blokada IRQ
        lda #0
        sta IRQEN            ; Wyłączenie przerwań POKEY
        sta SDMCTL
        sta DMACTL

;---------------------------------------
; Transpozycja sprite'ów → PMG
; Format źródłowy: [P0,P1,P2,P3,M5th] × 37 wierszy
; Format PMG:       per-player, ciągiem 128 B, offset TOP_MARGIN
;---------------------------------------

        ldx #SPRITE_ROWS-1  ; X = indeks wiersza (36..0)

@row_loop
        ; Oblicz offset źródłowy: X * 5
        txa
        sta SRC_TMP
        asl @               ; *2
        asl @               ; *4
        clc
        adc SRC_TMP          ; +1 → *5
        tay                  ; Y = offset w źródle

        ; Player 0 ← bajt 0 wiersza
        lda SpriteData,y
        sta PLAYER0+TOP_MARGIN,x

        ; Player 1 ← bajt 1
        iny
        lda SpriteData,y
        sta PLAYER1+TOP_MARGIN,x

        ; Player 2 ← bajt 2
        iny
        lda SpriteData,y
        sta PLAYER2+TOP_MARGIN,x

        ; Player 3 ← bajt 3
        iny
        lda SpriteData,y
        sta PLAYER3+TOP_MARGIN,x

        ; Missiles (5th player) ← bajt 4
        ; Bajt sprite'a ma identyczny układ bitów co bajt missile:
        ;   [7:6]=M3_lewy, [5:4]=M2, [3:2]=M1, [1:0]=M0_prawy
        ; → zapisujemy bezpośrednio do wspólnego bufora missile
        iny
        lda SpriteData,y
        sta MISSILES+TOP_MARGIN,x

        dex
        bpl @row_loop

; --- Zerowanie reszty pamięci PMG ---
@pmg_done
        lda #0
        ldx #TOP_MARGIN-1
@clr_top
        sta PLAYER0,x
        sta PLAYER1,x
        sta PLAYER2,x
        sta PLAYER3,x
        sta MISSILES,x
        dex
        bpl @clr_top

        ldx #239-MOON_TOP-MOON_ROWS
@clr_bottom
        sta PLAYER0+MOON_TOP+MOON_ROWS,x
        sta PLAYER1+MOON_TOP+MOON_ROWS,x
        sta PLAYER2+MOON_TOP+MOON_ROWS,x
        sta PLAYER3+MOON_TOP+MOON_ROWS,x
        sta MISSILES+MOON_TOP+MOON_ROWS,x
        dex
        bpl @clr_bottom

;---------------------------------------
; Transpozycja księżyca → PMG (P0–P3, 24 wiersze)
;---------------------------------------

        ldx #MOON_ROWS-1
@mclear  lda #0
        sta MISSILES+MOON_TOP,x
        dex
        bpl @mclear

        ldx #MOON_ROWS-1
@moon_loop
        txa
        asl @
        asl @               ; X * 4
        tay
        lda MoonData,y
        sta PLAYER0+MOON_TOP,x
        iny
        lda MoonData,y
        sta PLAYER1+MOON_TOP,x
        iny
        lda MoonData,y
        sta PLAYER2+MOON_TOP,x
        iny
        lda MoonData,y
        sta PLAYER3+MOON_TOP,x
        dex
        bpl @moon_loop

;---------------------------------------
; Gwiazdy — pojedyncze piksele na missile'ach
; W pobliżu księżyca (MOON_TOP=114)
;---------------------------------------

        ; Gwiazdy na missile'ach (M0–M3, pojedynczy piksel)
        ; Zapis PO moon_loop, żeby nadpisać @mclear
        lda #$01             ; M0: bit 0
        sta MISSILES+STAR0_Y
        lda #$04             ; M1: bit 2
        sta MISSILES+STAR1_Y
        lda #$10             ; M2: bit 4
        sta MISSILES+STAR2_Y
        lda #$40             ; M3: bit 6
        sta MISSILES+STAR3_Y

;---------------------------------------
; PMG — rejestry GTIA
;---------------------------------------

        ; Pozycje graczy (side-by-side od lewej)
        lda #HPOS_P0
        sta HPOSP0
        lda #HPOS_P1
        sta HPOSP1
        lda #HPOS_P2
        sta HPOSP2
        lda #HPOS_P3
        sta HPOSP3

        ; Pozycje missile'i — ODWROTNA KOLEJNOŚĆ!
        ; M3 (lewy skraj) → M2 → M1 → M0 (prawy skraj)
        ; SIZEM nie wpływa na odstępy — zawsze +2
        lda #HPOS_M+6
        sta HPOSM0
        lda #HPOS_M+4
        sta HPOSM1
        lda #HPOS_M+2
        sta HPOSM2
        lda #HPOS_M
        sta HPOSM3

        ; Rozmiar graczy — normalny (x2 tylko w DLI dla tytułu)
        lda #$00
        sta SIZEP0
        sta SIZEP1
        sta SIZEP2
        sta SIZEP3
        sta SIZEM

        ; Kolory graczy — wszystkie białe
        lda #$0E
        sta PCOLR0
        sta PCOLR1
        sta PCOLR2
        sta PCOLR3

        ; Kolor 5. gracza (missiles) — COLPF3
        lda #$0E
        sta COLPF3

        ; Adres bazowy PMG
        lda #>PMBASE_ADDR
        sta PMBASE

        ; Włącz graczy i missile w GTIA
        lda #$03
        sta GRACTL

        ; PRIOR — 5th player mode + players over playfield
        lda #$11
        sta PRIOR

;---------------------------------------
; Display List — bezpośrednio do sprzętu
;---------------------------------------
        lda #<DLIST
        sta DLISTL
        lda #>DLIST
        sta DLISTH

;---------------------------------------
; DMA ON (playfield + PMG single-line)
;---------------------------------------
        lda #$3E             ; %00111110 = playfield ON (normal) + PMG single-line
        sta DMACTL

;---------------------------------------
; Kolory (SCREEN_PREFIX)
;---------------------------------------
        icl "title_colors.asm"

;---------------------------------------
; DLI — rainbow na sprite'ach
;---------------------------------------

        ; Ustaw wektor DLI
        lda #<DLI_Handler
        sta VDSLST
        lda #>DLI_Handler
        sta VDSLST+1

        ; Włącz DLI na OSTATNIEJ linii pustej (DLIST+2),
        ; nie na pierwszej trybu E. Puste linie nie mają DMA,
        ; więc CPU dostaje przerwanie natychmiast — WSYNC trafia idealnie.
        lda DLIST+2
        ora #$80
        sta DLIST+2

        ; Włącz DLI (bez VBI — nie chcemy ingerencji OS)
        lda #$80
        sta NMIEN

Forever
        jmp Forever

;---------------------------------------
; DLI Handler — tęcza na sprite'ach
;---------------------------------------
DLI_Handler
        pha
        txa
        pha

        ; Setup HPOS + SIZEP dla tytułu (x2, szerokie)
        ; Robimy to od razu — pusta linia ma pełne CPU
        lda #$01
        sta SIZEP0
        sta SIZEP1
        sta SIZEP2
        sta SIZEP3
        lda #HPOS_P0
        sta HPOSP0
        lda #HPOS_P1
        sta HPOSP1
        lda #HPOS_P2
        sta HPOSP2
        lda #HPOS_P3
        sta HPOSP3
        lda #HPOS_M+6
        sta HPOSM0
        lda #HPOS_M+4
        sta HPOSM1
        lda #HPOS_M+2
        sta HPOSM2
        lda #HPOS_M
        sta HPOSM3

        ; Czekaj do początku sprite'ów
        ldx #DLI_DELAY
@delay
        sta WSYNC
        dex
        bne @delay

        ; Pierwsza linia tytułu — kolor od razu
        ldx #0
        lda RainbowColors,x
        sta PCOLR0
        sta PCOLR1
        sta PCOLR2
        sta PCOLR3
        sta COLPF3
        inx

        ; Pozostałe linie
        ldy #SPRITE_ROWS-2
@rainbow
        sta WSYNC
        lda RainbowColors,x
        sta PCOLR0
        sta PCOLR1
        sta PCOLR2
        sta PCOLR3
        sta COLPF3
        inx
        dey
        bpl @rainbow

        ; --- Po tęczy: PRIOR=$01, PCOLR=$40, SIZEP=1x (wspólne dla gwiazd i księżyca) ---
        sta WSYNC

        lda #$01
        sta PRIOR
        lda #$40
        sta PCOLR0
        sta PCOLR1
        sta PCOLR2
        sta PCOLR3
        lda #$00
        sta SIZEP0
        sta SIZEP1
        sta SIZEP2
        sta SIZEP3
        sta SIZEM

        ; --- Gwiazdy: HPOSM ---
        ldx #STAR0_Y - (TOP_MARGIN+SPRITE_ROWS) - 1  ; (108-87)-1 = 20 WSYNC
@sw     sta WSYNC
        dex
        bne @sw               ; → HBLANK 107→108

        lda #STAR0_X
        sta HPOSM0
        lda #STAR1_X
        sta HPOSM1
        lda #STAR2_X
        sta HPOSM2
        lda #STAR3_X
        sta HPOSM3

        ; --- Księżyc: HPOSP + HPOSM ---
        ldx #MOON_TOP-STAR0_Y-2  ; 4 WSYNC → HPOSP na PMG 113, efekt od 114
@sm     sta WSYNC
        dex
        bne @sm

        ; PMG 113: HPOSP księżyca + HPOSM gwiazd (PRIOR i PCOLR już ustawione)
        lda #MOON_X
        sta HPOSP0
        lda #MOON_X+8
        sta HPOSP1
        lda #MOON_X+16
        sta HPOSP2
        lda #MOON_X+24
        sta HPOSP3
        lda #STAR0_X
        sta HPOSM0
        lda #STAR1_X
        sta HPOSM1
        lda #STAR2_X
        sta HPOSM2
        lda #STAR3_X
        sta HPOSM3

        pla
        tax
        pla
        rti

;---------------------------------------
; Tabela kolorów tęczy (40 pozycji)
;---------------------------------------
RainbowColors
        dta $34,$36,$38,$3A,$3C 
        dta $3E,$3E,$3F,$3E,$3E
        dta $3C,$3A,$38,$36,$34
        dta $00,$00,$00,$00,$00
        dta $00,$14,$16,$18,$C8     
        dta $CA,$CC,$CE,$CE,$CF
        dta $CF,$CE,$CE,$CC,$CA
        dta $C8,$18,$16,$14,$00
;---------------------------------------
; Zmienne page zero
;---------------------------------------

SRC_TMP     equ $80

;---------------------------------------
; Display List (SCREEN_PREFIX)
;---------------------------------------

        org $3000

TitleData = SCREEN

        icl "title_displaylist.asm"

;---------------------------------------
; Obraz (SCREEN_PREFIX)
;---------------------------------------

        org SCREEN

        ins "title.bin"

;---------------------------------------
; Dane sprite'ów
;---------------------------------------

SpriteData = DzikizgonData

        icl "dziki-zgon.asm"

;---------------------------------------
; Dane sprite'ów — księżyc
;---------------------------------------

        icl "moon.asm"

        run start