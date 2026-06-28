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
    icl "lib/rle.asm"

    ; --- Sceny (każda eksportuje _init i _run) ---
    icl "scenes/title/title.asm"
    icl "scenes/story/story.asm"
    icl "scenes/game/game.asm"
    icl "scenes/gameover/gameover.asm"

; ===================================================================
; Tablica kolejności etapów (development: zmień DEV_START_STAGE w hardware.asm)
; ===================================================================
stage_order
    dta STATE_TITLE     ; 0
    dta STATE_STORY     ; 1
    dta STATE_GAME      ; 2
    dta STATE_OVER      ; 3
STAGE_COUNT = * - stage_order

; ===================================================================
; advance_stage — Przechodzi do następnego etapu wg tablicy stage_order
; Szuka bieżącego GAME_STATE w tablicy, bierze następny element
; (lub pierwszy, jeśli to był ostatni — wrap-around)
; Niszczy: A, X
; ===================================================================
.proc advance_stage
    ldx #0
@find
    lda stage_order,x
    cmp GAME_STATE
    beq @found
    inx
    cpx #STAGE_COUNT
    bne @find
    ; Nie znaleziono — fallback: idź do pierwszego etapu
    ldx #STAGE_COUNT-1    ; ostatni indeks — poniżej zrobi +1 → wrap na 0

@found
    inx
    cpx #STAGE_COUNT
    bne @store
    ldx #0               ; wrap-around: po ostatnim wróć do pierwszego

@store
    lda stage_order,x
    sta GAME_STATE
    rts
.endp

; ===================================================================
; system_init — Wspólna inicjalizacja sprzętu dla wszystkich etapów
; Wywoływana przed każdym scene_init (i w start)
; Niszczy: A
; ===================================================================
.proc system_init
    cld                     ; clear decimal mode (po resecie D może być nieznany!)
    sei                     ; blokada IRQ
    lda #0
    sta IRQEN               ; wyłącz przerwania POKEY
    sta DMACTL              ; wyłącz DMA na czas konfiguracji
    sta NMIEN               ; wyłącz NMI (DLI + VBI) — kluczowe przy DEV_START_STAGE>0
    sta GRACTL              ; wyłącz PMG DMA
    lda #$FF                ; %11111111: bit 0=1 (OS ROM ON), bit 1=1 (BASIC OFF)
    sta PORTB               ; odsłoń RAM spod BASIC ROM ($A000–$BFFF)
    rts
.endp

; ===================================================================
; 3. Punkt startowy — inicjalizacja systemu
; ===================================================================
start
    jsr system_init

    ; Ustaw stan początkowy z tablicy stage_order (wg DEV_START_STAGE)
    ldx #DEV_START_STAGE
    cpx #STAGE_COUNT
    bcc @ok
    ldx #0                  ; fallback: title
@ok
    lda stage_order,x
    sta GAME_STATE

; ===================================================================
; 4. Pętla główna — maszyna stanów
; ===================================================================
main_loop
    lda GAME_STATE
    cmp #STATE_TITLE
    bne @chk_story
    jsr system_init
    jsr title_init
@tl jsr title_run
    lda GAME_STATE
    cmp #STATE_TITLE
    beq @tl
    jmp main_loop

@chk_story
    cmp #STATE_STORY
    bne @chk_game
    jsr system_init
    jsr story_init
@st jsr story_run
    lda GAME_STATE
    cmp #STATE_STORY
    beq @st
    jmp main_loop

@chk_game
    cmp #STATE_GAME
    bne @chk_over
    jsr system_init
    jsr game_init
@gm jsr game_run
    lda GAME_STATE
    cmp #STATE_GAME
    beq @gm
    jmp main_loop

@chk_over
    ; Ostatni stan — gameover (domyślnie)
    jsr system_init
    jsr gameover_init
@go jsr gameover_run
    lda GAME_STATE
    cmp #STATE_OVER
    beq @go
    jmp main_loop

; --- Dane tekstów (kopiowane do RAM w czasie wykonania) ---
StoryText_RAM = FOOTER_ADDR

StoryText_Data
    icl "gen/story_text.asm"

GO_TEXT_Data
    icl "gen/gameover_text.asm"

SpriteData = DzikizgonData

    icl "gen/dziki-zgon.asm"
    icl "gen/moon.asm"

; ===================================================================
; 6. Display Listy ($3000)
; ===================================================================
    org DLIST_ADDR

; --- DL tytułu (pełna, z LMS i stopką) ---
TitleData = SCREEN
    icl "gen/title_displaylist.asm"    ; definiuje DLIST_TITLE

; --- DL story — ANTIC mode 2, tekst 8 linii wyśrodkowany ---
DLIST_STORY
    dta $70,$70,$70        ; 3 blank
    dta $70,$70            ; 2 blank (razem 5 blank na gorze)
    dta $42,a(StoryText_RAM) ; LMS + ANTIC mode 2 -> adres StoryText_RAM ($5E10)
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

; --- DL game over (ANTIC D, narrow, 128×96, 4 kolory) ---
GameoverData = GO_SCREEN
    icl "gen/gameover_displaylist.asm"    ; definiuje DLIST_GAMEOVER

JVB_OFFSET = * - DLIST_GAMEOVER - 3

    ; DLI na pierwszej pustej linii — przywraca kolory obrazka (COLPF1)
    org DLIST_GAMEOVER
    dta $F0                     ; blank + DLI (było $70)

    ; Nadpisz JVB: blank + DLI + ANTIC 3 (tekst "GAME OVER", tęcza co klatkę)
    org DLIST_GAMEOVER + JVB_OFFSET
    dta $F0                     ; 1 pusta linia + DLI (przełącza COLPF1 na tęczę)
    dta $43,a(GO_TEXT)          ; LMS + ANTIC mode 3 (8×10 znaków, narrow: 32 znaki)
    dta $41,a(DLIST_GAMEOVER)   ; JVB — powrót na początek DL

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
; 10. Czcionka ($6000, 1 KB aligned → CHBASE=$60)
; ===================================================================
    org $6000
    icl "fonts/font.asm"

; ===================================================================
; 11. Dane ekranu Game Over ($7000, ANTIC D, 160×96)
; ===================================================================
GO_SCREEN = $7000
    org GO_SCREEN
    ins "gen/gameover.bin"

; Tekst "GAME OVER" pod ekranem (współdzielony FOOTER_ADDR $5E10)
GO_TEXT = FOOTER_ADDR
