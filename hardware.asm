;----------------------------------------
; hardware.asm — Rejestry sprzętowe i stałe projektowe
; Współdzielone przez wszystkie moduły gry
; Atari XL/XE, ANTIC E (160x192, 4 kolory) + PMG
;----------------------------------------

; ---- GTIA (CTIA/GTIA — generowanie obrazu, kolory, PMG) ----
HPOSP0  = $D000     ; pozycja X gracza P0 (0..255 color clocks)
HPOSP1  = $D001     ; pozycja X gracza P1
HPOSP2  = $D002     ; pozycja X gracza P2
HPOSP3  = $D003     ; pozycja X gracza P3
HPOSM0  = $D004     ; pozycja X pocisku M0
HPOSM1  = $D005     ; pozycja X pocisku M1
HPOSM2  = $D006     ; pozycja X pocisku M2
HPOSM3  = $D007     ; pozycja X pocisku M3
SIZEP0  = $D008     ; szerokość gracza P0 (00=normal, 01=x2, 11=x4)
SIZEP1  = $D009     ; szerokość gracza P1
SIZEP2  = $D00A     ; szerokość gracza P2
SIZEP3  = $D00B     ; szerokość gracza P3
SIZEM   = $D00C     ; szerokość wszystkich pocisków (te same bity co SIZEP)
PCOLR0  = $D012     ; kolor gracza P0 + pocisku M0
PCOLR1  = $D013     ; kolor gracza P1 + pocisku M1
PCOLR2  = $D014     ; kolor gracza P2 + pocisku M2
PCOLR3  = $D015     ; kolor gracza P3 + pocisku M3
COLPF0  = $D016     ; kolor playfield 0 (indeks 1 w palecie ANTIC E)
COLPF1  = $D017     ; kolor playfield 1 (indeks 2)
COLPF2  = $D018     ; kolor playfield 2 (indeks 3)
COLPF3  = $D019     ; kolor playfield 3 / 5. gracza (missiles) gdy PRIOR bit 4=1
COLBK   = $D01A     ; kolor tła (COLBAK) — wspólny dla playfield i PMG
PRIOR   = $D01B     ; priorytety: bit 4=5th player, bity 1-0=tryb priorytetu
GRACTL  = $D01D     ; włączenie DMA PMG: bit 0=P/M, bit 1=missiles

; ---- ANTIC (kontroler DMA, Display List) ----
DMACTL  = $D400     ; włączenie DMA: bit 5=playfield, bity 1-0=rozdzielczość PMG
DLISTL  = $D402     ; młodszy bajt adresu Display List
DLISTH  = $D403     ; starszy bajt adresu Display List
PMBASE  = $D407     ; adres bazowy pamięci PMG (musi być wyrównany do 1K)
CHBASE  = $D409     ; adres bazowy fontu (znaków) — górny bajt, dolny zawsze $00
WSYNC   = $D40A     ; Wait for Sync — zapis zatrzymuje CPU do początku następnej linii
NMIEN   = $D40E     ; włączenie NMI: bit 7=DLI, bit 6=VBI

; ---- POKEY (dźwięk, klawiatura, timery) ----
IRQEN   = $D20E     ; włączenie przerwań IRQ z POKEY

; ---- OS shadows (cienie rejestrów w RAM) ----
SDMCTL  = 559       ; cień DMACTL ($22F) — bezpieczny zapis przez OS
VDSLST  = $0200     ; wektor DLI (2 bajty: lo, hi)

; ---- Joystick ----
STRIG0  = $0284     ; przycisk FIRE joysticka 0 (0=wciśnięty)

; ---- Mapa pamięci projektu ----
SCREEN      = $4000         ; bufor ekranu (ANTIC E, 160x192)
DLIST_ADDR  = $3000         ; adres bazowy Display List
PMBASE_ADDR = $8000         ; pamięć PMG (1K-aligned)
FOOTER_ADDR = $5E10         ; stopka tekstowa (ANTIC mode 2, 40 znaków)

; ---- Offsety PMG (single-line resolution) ----
MISSILES    = PMBASE_ADDR+$300   ; 128 B — wszystkie 4 missile w 1 bajcie/linia
PLAYER0     = PMBASE_ADDR+$400   ; 128 B
PLAYER1     = PMBASE_ADDR+$500   ; 128 B
PLAYER2     = PMBASE_ADDR+$600   ; 128 B
PLAYER3     = PMBASE_ADDR+$700   ; 128 B

; ---- Wymiary sprite'ów — tytuł ----
SPRITE_ROWS = 37
TOP_MARGIN  = 50

; ---- Wymiary sprite'ów — księżyc (4 graczy, 32px) ----
MOON_ROWS   = 24
MOON_TOP    = 114            ; pozycja Y księżyca (linia PMG)
MOON_X      = $28            ; pozycja X lewego skraju księżyca

; ---- Gwiazdy — na missile'ach M0–M3 ----
STAR0_X     = $50
STAR1_X     = $48
STAR2_X     = $60
STAR3_X     = $70

STAR0_Y     = 108            ; linia PMG — tuż nad księżycem
STAR1_Y     = 116            ; w obszarze księżyca
STAR2_Y     = 126
STAR3_Y     = 121

; ---- Timing DLI ----
KOREKTA     = 8              ; dostrojone doświadczalnie
DL_BLANKS   = 24
DLI_DELAY   = TOP_MARGIN - DL_BLANKS - KOREKTA

; ---- Pozycje PMG tytułu (color clocks, side by side, x2 = 16px apart) ----
TITLE_X     = $34            ; lewy skraj całego napisu
HPOS_P0     = TITLE_X
HPOS_P1     = TITLE_X+$10
HPOS_P2     = TITLE_X+$20
HPOS_P3     = TITLE_X+$30
HPOS_M      = TITLE_X+$40    ; 5th player — M3 (lewy skraj)

; ---- PMG DMA ----
DMA_PMG_ON  = $3E            ; %00111110 = playfield ON + PMG single-line
GRACTL_PM   = $03            ; włącz P/M + missiles
PRIOR_5TH   = $11            ; 5th player mode + players over playfield

; ---- Stany gry ----
STATE_TITLE = 0
STATE_STORY = 1
STATE_GAME  = 2
STATE_OVER  = 3
