;----------------------------------------
; main.asm — DZIKI ZGON
; Punkt startowy + maszyna stanów gry
; Atari XL/XE, ANTIC E (160x192, 4 kolory) + PMG
;----------------------------------------
    OPT h+

; ===================================================================
; 1. Definicje sprzętu i zmiennych (wspólne dla wszystkich modułów)
; ===================================================================
    icl "hardware.asm"
    icl "zeropage.asm"

; ===================================================================
; 2. Kod programu ($2000)
; ===================================================================
    org $2000

    jmp start              ; jawny skok do inicjalizacji

    ; --- Biblioteki (procedury wielokrotnego użytku) ---
    icl "lib/pmg.asm"

    ; --- Sceny (każda eksportuje _init i _run) ---
    icl "scenes/title/title.asm"
    icl "scenes/story/story.asm"
    icl "scenes/game/game.asm"
    icl "scenes/gameover/gameover.asm"

; ===================================================================
; 3. Punkt startowy — inicjalizacja systemu
; ===================================================================
start
    sei                     ; blokada IRQ
    lda #0
    sta IRQEN               ; wyłącz przerwania POKEY
    sta DMACTL              ; wyłącz DMA na czas konfiguracji

    ; Odsłoń RAM spod BASIC ROM ($A000–$BFFF, 8 KB)
    lda #$FD                ; %11111101: bit 0=1 (OS ROM ON), bit 1=0 (BASIC OFF)
    sta PORTB

    ; Ustaw stan początkowy
    lda #STATE_TITLE
    sta GAME_STATE

; ===================================================================
; 4. Pętla główna — maszyna stanów
; ===================================================================
main_loop
    lda GAME_STATE
    cmp #STATE_TITLE
    bne @chk_story
    jsr title_init
@tl jsr title_run
    lda GAME_STATE
    cmp #STATE_TITLE
    beq @tl
    jmp main_loop

@chk_story
    cmp #STATE_STORY
    bne @chk_game
    jsr story_init
@st jsr story_run
    lda GAME_STATE
    cmp #STATE_STORY
    beq @st
    jmp main_loop

@chk_game
    cmp #STATE_GAME
    bne @chk_over
    jsr game_init
@gm jsr game_run
    lda GAME_STATE
    cmp #STATE_GAME
    beq @gm
    jmp main_loop

@chk_over
    ; Ostatni stan — gameover (domyślnie)
    jsr gameover_init
@go jsr gameover_run
    lda GAME_STATE
    cmp #STATE_OVER
    beq @go
    jmp main_loop

; ===================================================================
; 5. Dane sprite'ów (przed $3000, w luce po kodzie)
; ===================================================================
SpriteData = DzikizgonData

    icl "gen/dziki-zgon.asm"
    icl "gen/moon.asm"

; ===================================================================
; 6. Display Listy ($3000)
; ===================================================================
    org DLIST_ADDR

; --- DL tytułu (pełna, z LMS i stopką) ---
TitleData = SCREEN
    icl "gen/title_displaylist.asm"
DLIST_TITLE = DLIST        ; alias dla czytelności

; --- DL story — ANTIC mode 2, tekst 8 linii wyśrodkowany ---
DLIST_STORY
    dta $70,$70,$70        ; 3 blank
    dta $70,$70            ; 2 blank (razem 5 blank na gorze)
    dta $42,$00,$64        ; LMS + ANTIC mode 2 -> adres $6400 (Line 1 - Text)
    dta $70                ; Blank line 1
    dta $02                ; ANTIC mode 2 (Line 2 - Text)
    dta $70                ; Blank line 2
    dta $02                ; ANTIC mode 2 (Line 3 - Text)
    dta $70                ; Blank line 3
    dta $02                ; ANTIC mode 2 (Line 4 - Text)
    dta $70                ; Blank line 4
    dta $02                ; ANTIC mode 2 (Line 5 - Text)
    dta $70                ; Blank line 5
    dta $02                ; ANTIC mode 2 (Line 6 - Text)
    dta $70                ; Blank line 6
    dta $02                ; ANTIC mode 2 (Line 7 - Text)
    dta $70                ; Blank line 7
    dta $02                ; ANTIC mode 2 (Line 8 - Text)
    dta $70,$70,$70        ; 3 blank
    dta $70                ; 1 blank (razem 4 blank na dole)
    dta $41,a(DLIST_STORY) ; JVB

; --- DL gra — ANTIC 4, 40×24 znaków ---
DLIST_GAME
    dta $70,$70,$70        ; 3 puste linie
    dta $44,a(GAME_SCREEN) ; LMS + ANTIC 4
    .rept 22
    dta $04                ; ANTIC 4 (kolejne linie)
    .endr
    dta $04                ; ostatnia linia (razem 24)
    dta $41,a(DLIST_GAME)  ; JVB

; --- DL placeholder — koniec gry ---
DLIST_GAMEOVER
    dta $70,$70,$70
    dta $4E,a(SCREEN)
    .rept 191
    dta $0E
    .endr
    dta $41,a(DLIST_GAMEOVER)

; ===================================================================
; 7. Dane ekranu ($4000)
; ===================================================================
    org SCREEN

    ins "gen/title.bin"

; ===================================================================
; 8. Stopka tekstowa ($5E10) — tylko tytuł
; ===================================================================
    org FOOTER_ADDR

    .rept 8
    dta d"     WCISNIJ FIRE BY ROZPOCZAC GRE      "
    .endr

; ===================================================================
; 9. Tekst story ($6400, 8×40 = 320 B)
; ===================================================================
    org $6400
StoryText
    dta d"  Po wielodniowej imprezie w karczmie   "
    dta d" 'Pod Trzema Kuflami' Wiedzmin Gerwant  "
    dta d" budzi sie z poteznym kacem. Nie pamieta"
    dta d"gdzie jest Plotka, gdzie sa miecze, ani "
    dta d"skad wzial sie rachunek na 18000 orenow."
    dta d"   Wyrusza w podroz przez 5 regionow,   "
    dta d" by odzyskac swoj dobytek, wspomnienia i"
    dta d"           resztki godnosci.            "

; ===================================================================
; 10. Czcionka ($6000, 1 KB aligned → CHBASE=$60)
; ===================================================================
    org $6000
    icl "fonts/font.asm"
