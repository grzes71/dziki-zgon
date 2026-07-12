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
GPRIOR  = $026F     ; shadow dla PRIOR
GRACTL  = $D01D     ; włączenie DMA PMG: bit 0=P/M, bit 1=missiles

; ---- PIA (Port Interface Adapter — PORTB, banki pamięci) ----
PORTB   = $D301     ; bit 0=OS ROM, bit 1=BASIC, bity 7-2=banki rozszerzonej pamięci

; ---- ANTIC (kontroler DMA, Display List) ----
DMACTL  = $D400     ; włączenie DMA: bit 5=playfield, bity 1-0=rozdzielczość PMG
DLISTL  = $D402     ; młodszy bajt adresu Display List
DLISTH  = $D403     ; starszy bajt adresu Display List
PMBASE  = $D407     ; adres bazowy pamięci PMG (musi być wyrównany do 1K)
CHBASE  = $D409     ; adres bazowy fontu (znaków) — górny bajt, dolny zawsze $00
WSYNC   = $D40A     ; Wait for Sync — zapis zatrzymuje CPU do początku następnej linii
VCOUNT  = $D40B     ; Odczyt licznika linii (w dół od 0 do 155 na PAL)
NMIST   = $D40F     ; rejestr statusu NMI: bit 7=DLI, bit 6=VBI (odczyt kasuje)
NMIEN   = $D40E     ; włączenie NMI: bit 7=DLI, bit 6=VBI

; ---- POKEY (dźwięk, klawiatura, timery) ----
IRQEN   = $D20E     ; włączenie przerwań IRQ z POKEY

; ---- OS shadows (cienie rejestrów w RAM) ----
; UWAGA: Jeśli NMIEN=$C0 (VBI włączone), OS przepisuje cienie do sprzętu w każdej klatce.
; Dlatego inicjalizacje scen muszą pisać do cieni. Zapis bezpośredni do hardware ma sens 
; tylko przy wyłączonym VBI (NMIEN=$00) lub wewnątrz DLI.
VDSLST  = $0200     ; wektor przerwania DLI
VVBLKD  = $0222     ; wektor przerwania VBI (Immediate VBLANK)
VVBLKI  = $0224     ; wektor przerwania VBI (Deferred VBLANK)
SDMCTL  = $022F     ; cień DMACTL
SDLSTL  = $0230     ; cień DLISTL
SDLSTH  = $0231     ; cień DLISTH
CHBAS   = $02F4     ; cień CHBASE
COLOR0  = $02C4     ; cień COLPF0
COLOR1  = $02C5     ; cień COLPF1
COLOR2  = $02C6     ; cień COLPF2
COLOR3  = $02C7     ; cień COLPF3
COLOR4  = $02C8     ; cień COLBK

; ---- Joystick ----
STRIG0  = $0284     ; cień przycisku FIRE (NIEAKTUALNY bez VBI — użyj TRIG0!)
TRIG0   = $D010     ; GTIA — przycisk FIRE joysticka 0 (bit 0=0 gdy wciśnięty)
PORTA   = $D300     ; PORT A PIA — joystick 0 (bity 0–3: góra/dół/lewo/prawo, 0=aktywny)

; ---- Mapa pamięci projektu ----
SCREEN      = $4000         ; bufor ekranu (ANTIC E, 160x192)
DLIST_ADDR  = $3E80         ; adres bazowy Display List
PMBASE_ADDR = $A000         ; pamięć PMG (1K-aligned, pod ROM BASIC)
FOOTER_ADDR = $5E10         ; stopka tekstowa (ANTIC mode 2, 40 znaków)

; ---- Offsety PMG (single-line resolution) ----
MISSILES    = PMBASE_ADDR+$300   ; 256 B — wszystkie 4 missile w 1 bajcie/linia
PLAYER0     = PMBASE_ADDR+$400   ; 256 B
PLAYER1     = PMBASE_ADDR+$500   ; 256 B
PLAYER2     = PMBASE_ADDR+$600   ; 256 B
PLAYER3     = PMBASE_ADDR+$700   ; 256 B

; ---- Wymiary sprite'ów — tytuł ----
SPRITE_ROWS = 37
TOP_MARGIN  = 38

; ---- Wymiary sprite'ów — księżyc (4 graczy, 32px) ----
MOON_ROWS   = 24
MOON_TOP    = 100            ; pozycja Y księżyca (linia PMG) — musi być > TOP_MARGIN+SPRITE_ROWS
MOON_X      = $30            ; pozycja X lewego skraju księżyca

; ---- Gwiazdy — na missile'ach M0–M3 (tylko PMG data placement, NIE DLI timing) ----
STAR0_X     = $50
STAR1_X     = $48
STAR2_X     = $60
STAR3_X     = $74

STAR0_Y     = 90            ; linia PMG — tuż nad księżycem
STAR1_Y     = 110            ; w obszarze księżyca
STAR2_Y     = 95
STAR3_Y     = 100

; ---- Timing DLI ----
KOREKTA     = 8              ; dostrojone doświadczalnie
DL_BLANKS   = 24
DLI_DELAY   = TOP_MARGIN - DL_BLANKS - KOREKTA

; ---- Pozycje PMG tytułu (color clocks, side by side, x1 = 8px apart) ----
TITLE_X     = $30            ; lewy skraj całego napisu
HPOS_P0     = TITLE_X
HPOS_P1     = TITLE_X+$08
HPOS_P2     = TITLE_X+$10
HPOS_P3     = TITLE_X+$18
HPOS_M      = TITLE_X+$20    ; 5th player — M3 (lewy skraj)

; ---- PMG DMA ----
DMA_PMG_ON  = $3E            ; %00111110 = playfield ON + PMG single-line
GRACTL_PM   = $03            ; włącz P/M + missiles
PRIOR_5TH   = $11            ; 5th player mode + players over playfield

; ---- Stany gry ----
STATE_TITLE = 0
STATE_STORY = 1
STATE_GAME  = 2
STATE_OVER  = 3

; ---- Development — indeks etapu startowego (0=title, 1=story, 2=game, 3=gameover) ----
DEV_START_STAGE = 2         ; zmień, by wystartować od innego etapu podczas developmentu

; ---- Limity i współrzędne spawnu przy przejściu między ekranami ----
SCREEN_LIMIT_LEFT   = 48   ; Lewa granica chodzenia. Ruch poniżej wyzwala transition na zachód.
SCREEN_LIMIT_RIGHT  = 200  ; Prawa granica chodzenia. Ruch równy lub powyżej wyzwala transition na wschód.
SCREEN_LIMIT_TOP    = 32   ; Górna granica chodzenia. Ruch poniżej wyzwala transition na północ.
SCREEN_LIMIT_BOTTOM = 210  ; Dolna granica chodzenia. Ruch równy lub powyżej wyzwala transition na południe.

TRANSITION_SPAWN_LEFT   = 48   ; Pozycja X po wejściu na ekran z lewej strony (wschodni transition)
TRANSITION_SPAWN_RIGHT  = 199  ; Pozycja X po wejściu na ekran z prawej strony (zachodni transition)
TRANSITION_SPAWN_TOP    = 32   ; Pozycja Y po wejściu na ekran od góry (południowy transition)
TRANSITION_SPAWN_BOTTOM = 209  ; Pozycja Y po wejściu na ekran od dołu (północny transition)

