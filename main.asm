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

disable_basic_loader
    pha
    lda #$FF
    sta PORTB
    pla
    rts
    ini disable_basic_loader

    ; --- Biblioteki (procedury wielokrotnego użytku) ---
    icl "lib/pmg.asm"
    icl "lib/rle.asm"
    icl "lib/world_renderer.asm"
    
    ; --- Silnik gry ---
    icl "engine/engine.asm"

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
    sta $42                 ; Wyczyść flagę CRITIC, aby upewnić się, że OS VBLANK kopiuje cienie!
    sta IRQEN               ; wyłącz przerwania POKEY
    sta DMACTL              ; wyłącz DMA na czas konfiguracji
    sta SDMCTL              ; zresetuj też cień DMACTL
    sta NMIEN               ; wyłącz NMI (DLI + VBI) — kluczowe przy DEV_START_STAGE>0
    sta GRACTL              ; wyłącz PMG DMA

    ; --- Wyczyszczenie rejestrów GTIA (pozycje, rozmiary i grafika PMG) ---
    ldx #$11
@clr_gtia
    sta $D000,x
    dex
    bpl @clr_gtia

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
    jsr title_audio_stop          ; Stop the music on state exit
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
    jsr title_audio_stop          ; Stop the music on state exit
    jmp main_loop

@chk_game
    cmp #STATE_GAME
    bne @chk_over
    jsr system_init
    jsr game_init
    lda #0
    sta Engine_RequestStageAdvance
@gm 
    jsr Engine_WaitFrame
    jsr EngineScheduler

    ; Sprawdzenie, czy silnik poprosił o zmianę sceny
    lda Engine_RequestStageAdvance
    beq @skip_advance
    jsr advance_stage
@skip_advance

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
    jsr title_audio_stop          ; Stop the music on state exit
    jmp main_loop

; --- Dane tekstów (kopiowane do RAM w czasie wykonania) ---
StoryText_RAM = FOOTER_ADDR

StoryText_Data = text_story
GO_TEXT_Data = text_gameover
TitleFooterROM = text_title

    ; Wyrównaj dane tekstowe do granicy strony, aby uniknąć kar
    ; za przekraczanie stron w pętli dekodera RLE.
    .align $0100
    icl "gen/all_texts.asm"

SpriteData = DzikizgonData

    icl "gen/dziki-zgon.asm"
    icl "gen/moon.asm"
    icl "gen/gerwalt.sprite.asm"
    icl "gen/bazyliszek.sprite.asm"
    icl "gen/kikimora.sprite.asm"
    icl "gen/strzyga.sprite.asm"

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

; --- DL gra ---
DLIST_GAME
    dta $70,$70,$70        ; 24 puste linie
    dta $45,a(GAME_SCREEN_A5) ; ANTIC 5, 1 linia
    .rept 11               ; Kolejne 11 linii ANTIC 5 (razem 12)
    dta $05
    .endr
    dta $90                ; 1 pusta linia + DLI gdzie powinno być ustawienie charsetu dla statusu (font.fnt) oraz kolorów dla statusu!
    dta $42,a(GAME_SCREEN_A2) ; ANTIC 2, 1 linia
    dta $02                ; Kolejna 1 linia ANTIC 2 (razem 2)
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
; 7. Współdzielona Arena VRAM ($4000)
; ===================================================================
VRAM_ARENA = SCREEN
; Zamiast "ins" surowego obrazka, rozpakowujemy go z ROM_DATA w title_init.

; ===================================================================
; 8. Stopka tekstowa ($5E10) — współdzielona (tytuł/story/gameover)
; ===================================================================
    org FOOTER_ADDR
    .ds 320                 ; 8 linii × 40 znaków — zerowane na starcie

; ===================================================================
; 10. Czcionka ($6000, 1 KB aligned → CHBASE=$60)
; ===================================================================
    org $6000
    icl "gen/font.asm"

    org $6400
    icl "gen/game_font.asm"

; 11. Dane ekranu Game Over (w VRAM_ARENA)
; ===================================================================
GO_SCREEN = VRAM_ARENA
; Gameover grafika jest kompresowana i wypakowywana w gameover_init.

; ===================================================================
; 12. Dane skompresowane w darmowym RAM-ie ($8000)
; ===================================================================
    org $8000
TitleScreen_Data
    ins "gen/title.rle"
GameOverScreen_Data
    ins "gen/gameover.rle"

; Tekst "GAME OVER" pod ekranem (współdzielony FOOTER_ADDR $5E10)
GO_TEXT = FOOTER_ADDR

; ===================================================================
; 13. Dane świata i odtwarzacz muzyki (w bezpiecznym darmowym RAM-ie)
; ===================================================================
    org $6800

; --- Dane Świata (World Builder) ---
    icl "gen/world/world.inc"
    icl "gen/world/objects.asm"
    icl "gen/world/regions.asm"
    icl "gen/world/screens.asm"
    icl "gen/world/exits.asm"

; --- Muzyka i odtwarzacz ($8800) ---
    icl "music/title_audio.asm"

    run start
