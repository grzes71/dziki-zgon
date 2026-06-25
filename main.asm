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
    sta SDMCTL
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

; --- DL placeholder — story / opis ---
DLIST_STORY
    dta $70,$70,$70        ; 3 puste linie
    dta $4E,a(SCREEN)      ; LMS na SCREEN (pusta pamięć)
    .rept 191
    dta $0E                ; ANTIC E
    .endr
    dta $41,a(DLIST_STORY) ; JVB

; --- DL placeholder — gra ---
DLIST_GAME
    dta $70,$70,$70
    dta $4E,a(SCREEN)
    .rept 191
    dta $0E
    .endr
    dta $41,a(DLIST_GAME)

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
; 9. Czcionka ($6000, 1 KB aligned → CHBASE=$60)
; ===================================================================
    org $6000
    icl "fonts/font.asm"
