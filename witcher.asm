	OPT h+

;---------------------------------------
; Atari XL/XE
; ANTIC E (160x192, 4 kolory) + PMG
;---------------------------------------

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
MOON_TOP    = 110           ; pozycja Y księżyca (linia PMG)
MOON_X      = 40            ; pozycja X lewego skraju księżyca

; PMG DMA start offset (blank lines $70×3 = 24 lines counted by PMG counter)
KOREKTA     = 8            ; dostrojone doświadczalnie
DL_BLANKS   = 24
DLI_DELAY   = TOP_MARGIN - DL_BLANKS - KOREKTA ; 26 - KOREKTA

; PMG positions (color clocks — side by side, x2 = 16px apart)
HPOS_P0     = $30
HPOS_P1     = $40
HPOS_P2     = $50
HPOS_P3     = $60
HPOS_M      = $70           ; 5th player — M3 (lewy skraj)

        org $2000

start
;---------------------------------------
; Wyłączenie DMA na czas konfiguracji
;---------------------------------------

        lda #0
        sta 559             ; SDMCTL = 0
        sta $D400           ; DMACTL = 0

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
; PMG — rejestry GTIA
;---------------------------------------

        ; Pozycje graczy (side-by-side od lewej)
        lda #HPOS_P0
        sta $D000            ; HPOSP0
        lda #HPOS_P1
        sta $D001            ; HPOSP1
        lda #HPOS_P2
        sta $D002            ; HPOSP2
        lda #HPOS_P3
        sta $D003            ; HPOSP3

        ; Pozycje missile'i — ODWROTNA KOLEJNOŚĆ!
        ; M3 (lewy skraj) → M2 → M1 → M0 (prawy skraj)
        ; SIZEM nie wpływa na odstępy — zawsze +2
        lda #HPOS_M+6        ; M0 = prawy skraj
        sta $D004            ; HPOSM0
        lda #HPOS_M+4        ; M1
        sta $D005            ; HPOSM1
        lda #HPOS_M+2        ; M2
        sta $D006            ; HPOSM2
        lda #HPOS_M          ; M3 = lewy skraj
        sta $D007            ; HPOSM3

        ; Rozmiar graczy — normalny (x2 tylko w DLI dla tytułu)
        lda #$00
        sta $D008            ; SIZEP0
        sta $D009            ; SIZEP1
        sta $D00A            ; SIZEP2
        sta $D00B            ; SIZEP3
        sta $D00C            ; SIZEM

        ; Kolory graczy — wszystkie białe
        lda #$0E
        sta $D012            ; PCOLR0
        sta $02C0            ;   shadow
        sta $D013            ; PCOLR1
        sta $02C1            ;   shadow
        sta $D014            ; PCOLR2
        sta $02C2            ;   shadow
        sta $D015            ; PCOLR3
        sta $02C3            ;   shadow

        ; Kolor 5. gracza (missiles) — COLPF3
        lda #$0E
        sta $D019            ; COLPF3
        sta $02C7            ;   shadow (COLOR3)

        ; Adres bazowy PMG
        lda #>PMBASE_ADDR
        sta $D407            ; PMBASE

        ; Włącz graczy i missile w GTIA
        lda #$03
        sta $D01D            ; GRACTL

        ; PRIOR — 5th player mode + players over playfield
        lda #$11
        sta $D01B            ; PRIOR
        sta $026F            ;   shadow (GPRIOR)

;---------------------------------------
; Display List
;---------------------------------------

        lda #<DLIST
        sta 560              ; SDLSTL
        lda #>DLIST
        sta 561              ; SDLSTH

;---------------------------------------
; DMA ON (playfield + PMG single-line)
;---------------------------------------

        lda #$3E             ; DL + single-line + players + missiles + normal width
        sta 559              ; SDMCTL
        sta $D400            ; DMACTL

;---------------------------------------
; Kolory (SCREEN_PREFIX)
;---------------------------------------
        icl "title-0a_colors.asm"

;---------------------------------------
; DLI — rainbow na sprite'ach
;---------------------------------------

        ; Ustaw wektor DLI
        lda #<DLI_Handler
        sta $0200            ; VDSLST low
        lda #>DLI_Handler
        sta $0201            ; VDSLST high

        ; Włącz DLI na OSTATNIEJ linii pustej (DLIST+2),
        ; nie na pierwszej trybu E. Puste linie nie mają DMA,
        ; więc CPU dostaje przerwanie natychmiast — WSYNC trafia idealnie.
        lda DLIST+2
        ora #$80
        sta DLIST+2

        ; Włącz DLI + VBI
        lda #$C0
        sta $D40E            ; NMIEN

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
        sta $D008            ; SIZEP0  x2
        sta $D009            ; SIZEP1  x2
        sta $D00A            ; SIZEP2  x2
        sta $D00B            ; SIZEP3  x2
        lda #HPOS_P0
        sta $D000            ; HPOSP0
        lda #HPOS_P1
        sta $D001            ; HPOSP1
        lda #HPOS_P2
        sta $D002            ; HPOSP2
        lda #HPOS_P3
        sta $D003            ; HPOSP3
        lda #HPOS_M+6
        sta $D004            ; HPOSM0
        lda #HPOS_M+4
        sta $D005            ; HPOSM1
        lda #HPOS_M+2
        sta $D006            ; HPOSM2
        lda #HPOS_M
        sta $D007            ; HPOSM3

        ; Czekaj do początku sprite'ów
        ldx #DLI_DELAY
@delay
        sta $D40A            ; WSYNC
        dex
        bne @delay

        ; Pierwsza linia tytułu — kolor od razu
        ldx #0
        lda RainbowColors,x
        sta $D012            ; PCOLR0
        sta $D013            ; PCOLR1
        sta $D014            ; PCOLR2
        sta $D015            ; PCOLR3
        sta $D019            ; COLPF3 (5th player)
        inx

        ; Pozostałe linie
        ldy #SPRITE_ROWS-2
@rainbow
        sta $D40A            ; WSYNC — czekaj na następną linię
        lda RainbowColors,x
        sta $D012            ; PCOLR0
        sta $D013            ; PCOLR1
        sta $D014            ; PCOLR2
        sta $D015            ; PCOLR3
        sta $D019            ; COLPF3 (5th player)
        inx
        dey
        bpl @rainbow

        ; Przywróć kolor księżyca + 1x + ciasne HPOS
        sta $D40A            ; WSYNC
        ; --- Księżyc: kolor $40, 1x, stykające się (8cc odstęp), 5th player ukryty ---
        lda #$40
        sta $D012            ; PCOLR0   kolor księżyca
        sta $D013            ; PCOLR1
        sta $D014            ; PCOLR2
        sta $D015            ; PCOLR3
        lda #$0E             ; 5th player biały (niewidoczny — HPOSM=0)
        sta $D019            ; COLPF3

        lda #$00             ; normalna szerokość (1x = 8cc na gracza)
        sta $D008            ; SIZEP0
        sta $D009            ; SIZEP1
        sta $D00A            ; SIZEP2
        sta $D00B            ; SIZEP3

        lda #MOON_X          ; P0 — lewy skraj księżyca
        sta $D000            ; HPOSP0
        lda #MOON_X+8        ; P1 — +8cc
        sta $D001            ; HPOSP1
        lda #MOON_X+16       ; P2 — +16cc
        sta $D002            ; HPOSP2
        lda #MOON_X+24       ; P3 — +24cc
        sta $D003            ; HPOSP3

        lda #0               ; ukryj 5. gracza poza ekranem
        sta $D004            ; HPOSM0
        sta $D005            ; HPOSM1
        sta $D006            ; HPOSM2
        sta $D007            ; HPOSM3

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

Title0aData = SCREEN

        icl "title-0a_displaylist.asm"

;---------------------------------------
; Obraz (SCREEN_PREFIX)
;---------------------------------------

        org SCREEN

        ins "title-0a.bin"

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