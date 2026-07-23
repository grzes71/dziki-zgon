;----------------------------------------
; scenes/game/game.asm — Gra właściwa    
;----------------------------------------

;---- Adresy pamięci dla gry (współdzielone z main.asm przez .global) ----
GAME_SCREEN_A5 = SCREEN      ; mapa 40×12 (ANTIC 5) = 480 bajtów
GAME_SCREEN_A2 = SCREEN+480  ; mapa 40×2 (ANTIC 2) = 80 bajtów
GAME_CHARSET  = $A800       ; charset gry — kafelki terenu (1 KB, CHBASE=$A8)

;---- Zmienne lokalne sceny ----
game_fire_released
    dta $00
game_stage
    dta $00             ; Aktualny etap gry (0-4)
;==============================================================
; DANE STARTOWE (łatwe do edycji podczas testów mapy)
;==============================================================
DEBUG_START_SCREEN  dta SCREEN_ID_TAVERN

; Zmienne przechowujące aktywne kolory dla obu stref (nadpisywane co etap)
; Paleta kolorów sprzętowych dla planszy (ANTIC 5) od PCOLR0 ($D012) do COLBK ($D01A)
game_palette
    .ds 9


; Jedna wspólna paleta dla panelu statusu (ANTIC 2)
status_palette
    dta $0E, $0E, $0E, $0E, $00, $0F, $00, $00, $00

default_status_bar
    dta 1, 3
    dta d'                                    '
    dta 5, 6
    dta 4, 8
    dta d'                                    '
    dta 9, 7

timer_minutes
    dta 12
timer_seconds
    dta 0
timer_frames
    dta 50
temp_units
    dta 0
temp_step
    dta 0
temp_val
    dta 0
temp_sub
    dta 0


;==============================================================
; draw_region_name — kopiuje 31-bajtową nazwę regionu do Info Line (górna linia statusowa)
; Zarezerwowane pozycje: 0..1 (kody 1,3) oraz 38..39 (kody 5,6)
; Nazwa regionu wyświetlana od indeksu 2 (31 znaków max)
;==============================================================
.proc draw_region_name
    ldx game_stage
    lda REGION_NAMES_LO,x
    sta SRC_PTR
    lda REGION_NAMES_HI,x
    sta SRC_PTR+1

    ldy #30
@loop
    lda (SRC_PTR),y
    sta GAME_SCREEN_A2 + 2,y
    dey
    bpl @loop
    rts
.endp

;==============================================================
; draw_timer — formatuje i wyświetla czas na Info Line (indeksy 33..37)
;==============================================================
.proc draw_timer
    ; Oblicz minuty
    lda timer_minutes
    jsr get_digits
    txa
    clc
    adc #$10
    sta GAME_SCREEN_A2 + 33
    lda temp_units
    clc
    adc #$10
    sta GAME_SCREEN_A2 + 34

    ; ':'
    lda #$1A
    sta GAME_SCREEN_A2 + 35

    ; Oblicz sekundy
    lda timer_seconds
    jsr get_digits
    txa
    clc
    adc #$10
    sta GAME_SCREEN_A2 + 36
    lda temp_units
    clc
    adc #$10
    sta GAME_SCREEN_A2 + 37

    rts
.endp

.proc get_digits
    ldx #0
@loop
    cmp #10
    bcc @done
    sec
    sbc #10
    inx
    jmp @loop
@done
    sta temp_units
    rts
.endp

;==============================================================
; get_collision_damage — sprawdza kolizje z przeciwnikami i zwraca max damage
;==============================================================
.proc get_collision_damage
    lda #0                  ; domyślny damage = 0
    sta temp_step
    
    ldx #1                  ; pętla po przeciwnikach (Aktorzy 1..3)
@loop
    lda ACTOR_ACTIVE,x
    beq @next
    
    ; Sprawdzenie osi X: abs(ACTOR_X[0] - ACTOR_X[x]) < 8
    lda ACTOR_X
    sec
    sbc ACTOR_X,x
    bpl @abs_x
    eor #$FF
    clc
    adc #1
@abs_x
    cmp #8
    bcs @next               ; brak kolizji na osi X

    ; Sprawdzenie osi Y part 1: Y_p < Y_e + H_e
    lda ACTOR_Y,x
    clc
    adc ACTOR_HEIGHT,x
    sta temp_val
    lda ACTOR_Y
    cmp temp_val
    bcs @next               ; brak kolizji (Y_p >= bottom_e)

    ; Sprawdzenie osi Y part 2: Y_e < Y_p + H_p
    lda ACTOR_Y
    clc
    adc ACTOR_HEIGHT
    sta temp_val
    lda ACTOR_Y,x
    cmp temp_val
    bcs @next               ; brak kolizji (Y_e >= bottom_p)

    ; Wykryto kolizję! Pobierz damage z tabeli
    ldy ACTOR_TYPE,x
    lda ENEMY_DAMAGE,y
    cmp temp_step
    bcc @next               ; mniejszy damage niż dotychczasowy max
    sta temp_step

@next
    inx
    cpx #MAX_ACTORS
    bne @loop

    ; 2. Sprawdź kolizję z kolorem PF3 (rejestr sprzętowy P0PF)
    lda P0PF
    and #$08                ; bit 3 = PF3
    beq @no_pf3
    
    ; Kolizja z PF3! Pobierz REGION_DAMAGE dla obecnego game_stage
    ldy game_stage
    lda REGION_DAMAGE,y
    cmp temp_step
    bcc @no_pf3
    sta temp_step

@no_pf3
    ; Czyszczenie rejestru kolizji na koniec odczytu klatki
    lda #0
    sta HITCLR

    lda temp_step
    beq @no_col_color
    
    lda #1
    sta collision_active
    lda #54 ; red color
    sta ACTOR_COLOR
    jmp @done_color
    
@no_col_color
    lda #0
    sta collision_active
    lda game_palette
    sta ACTOR_COLOR
    
@done_color
    lda temp_step
    rts
.endp

;==============================================================
; subtract_seconds — odejmuje A sekund od czasu MM:SS
;==============================================================
.proc subtract_seconds
    sta temp_sub
    beq @done               ; jeśli A = 0, nic nie robimy

@sub_loop
    lda timer_seconds
    sec
    sbc temp_sub
    bcs @store_seconds      ; jeśli timer_seconds >= temp_sub, brak pożyczki

    ; Pożyczka z minut
    lda timer_minutes
    beq @game_over          ; jeśli minuty = 0, koniec czasu!

    dec timer_minutes
    lda timer_seconds
    clc
    adc #60
    sta timer_seconds
    jmp @sub_loop

@store_seconds
    sta timer_seconds
    jsr draw_timer
    rts

@game_over
    lda #0
    sta timer_minutes
    sta timer_seconds
    jsr draw_timer
    lda #1
    sta Engine_RequestStageAdvance

@done
    rts
.endp

;==============================================================
; update_timer — aktualizuje czas co klatkę (VBLANK)
;==============================================================
.proc update_timer
    ; 1. Sprawdź i zaaplikuj obrażenia kolizyjne
    jsr get_collision_damage
    jsr subtract_seconds

    ; 2. Normalny upływ czasu (1 sekunda co 50 klatek)
    dec timer_frames
    lda timer_frames
    bne @done_normal

    lda #50
    sta timer_frames
    
    lda #1
    jsr subtract_seconds

@done_normal
    rts
.endp

;==============================================================
; update_stage_colors — kopiuje odpowiednie kolory w oparciu o game_stage
;==============================================================
.proc update_stage_colors
    ldx game_stage
    ldy REGION_PALETTE_OFFSETS,x
    
    ldx #0
@loop
    lda REGION_PALETTES,y
    sta game_palette,x
    sta $02C0,x            ; Kopiuj do OS shadows (PCOLR0-3, COLOR0-4)
    iny
    inx
    cpx #9
    bne @loop

    rts
.endp

;==============================================================
; game_init — Konfiguracja ANTIC 4 + PMG
;==============================================================
.proc game_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta game_fire_released  ; zresetuj stan przycisku FIRE
    
    ; Wyzeruj wszystkich aktorów
    ldx #MAX_ACTORS - 1
    lda #0
@clear_actors
    sta ACTOR_ACTIVE,x
    sta ACTOR_X,x
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_X,x
    sta ACTOR_INTENT_Y,x
    sta ACTOR_DIR,x
    sta ACTOR_ANIM_FRAME,x
    sta ACTOR_ANIM_TIMER,x
    sta ACTOR_ANIM_SPEED,x
    sta ACTOR_COLOR,x
    dex
    bpl @clear_actors

    ; Inicjalizacja głównego bohatera (Actor 0)
    ldx #0
    lda #1
    sta ACTOR_ACTIVE,x
    lda #6
    sta ACTOR_ANIM_SPEED,x
    lda #SPRITE_GERWALT_RIGHT_HEIGHT
    sta ACTOR_HEIGHT,x
    
    ; Wskaźniki na klatki animacji i limity
    lda #<GERWALT_PTRS_TABLE
    sta ACTOR_PTRS_TABLE_LO,x
    lda #>GERWALT_PTRS_TABLE
    sta ACTOR_PTRS_TABLE_HI,x
    
    lda #<GERWALT_ANIM_LIMITS
    sta ACTOR_ANIM_LIMITS_LO,x
    lda #>GERWALT_ANIM_LIMITS
    sta ACTOR_ANIM_LIMITS_HI,x

    jsr pmg_clear_all
    
    ; Ustaw pozycję startową z World Buildera dla Aktora 0
    lda #START_POS_X
    asl
    asl
    clc
    adc #48
    sta ACTOR_X,x
    sta ACTOR_INTENT_X,x
    
    lda #START_POS_Y
    asl
    asl
    asl
    asl
    clc
    adc #32
    sta ACTOR_Y,x
    sta ACTOR_Y_OLD,x
    sta ACTOR_INTENT_Y,x

    ; --- Inicjalizacja kolorów wybranego etapu ---
    jsr update_stage_colors

    ; Zainicjuj kolor gracza z wczytanej palety regionu
    lda game_palette
    sta ACTOR_COLOR

    ; --- Display List gry (ANTIC 4/5) ---
    lda #<DLIST_GAME
    sta SDLSTL
    lda #>DLIST_GAME
    sta SDLSTH

    ; --- Wczytanie początkowego charsetu (górny panel gry, game.fnt) ---
    lda #$64
    sta CHBAS

    ; --- Kolory (początkowe, bezpieczne) ---
    lda #$00
    sta COLOR4

    ; --- Inicjalizacja pierwszej mapy ---
    lda #START_SCREEN_ID
    sta GAME_SCREEN_ID

    ; --- Wypełnij mapę (ANTIC 5 i ANTIC 2) ---
    jsr clear_game_screens
    
    ; --- Zbuduj ekran gry bazując na World Builderze ---
    jsr build_screen
    jsr check_active_charset_animations

    ; --- Wypełnij pasek statusu domyślnym tekstem ---
    ldx #0
@fill_status
    lda default_status_bar,x
    sta GAME_SCREEN_A2,x
    inx
    cpx #80
    bne @fill_status

    ; --- Inicjalizacja czasu i regionu ---
    lda #12
    sta timer_minutes
    lda #0
    sta timer_seconds
    lda #50
    sta timer_frames

    ; --- Zaktualizuj region w oparciu o startowy ekran ---
    ldx GAME_SCREEN_ID
    lda SCREEN_REGION,x
    sta game_stage

    ; --- Narysuj nazwę regionu ---
    jsr draw_region_name

    ; --- Narysuj zegar ---
    jsr draw_timer

    ; --- PMG: rozmiar normalny, włącz PMG ---
    lda #$00
    sta SIZEP0
    sta SIZEM
    lda #PRIOR_5TH
    sta GPRIOR
    sta PRIOR
    lda #>PMBASE_ADDR
    sta PMBASE
    lda #GRACTL_PM
    sta GRACTL
    lda #$60
    sta HPOSP0

    jsr Render_Prepare

    ; --- Przygotuj przerwania DLI ---
    lda #<game_dli
    sta VDSLST
    lda #>game_dli
    sta VDSLST+1

    ; --- VBLANK i DLI ON ---
    lda #<Engine_FrameHandler
    sta $0222
    lda #>Engine_FrameHandler
    sta $0223

    ; --- DMA ON ---
    lda #DMA_PMG_ON
    sta SDMCTL
    sta DMACTL
    lda #$C0             ; włącz DLI i VBLANK
    sta NMIEN

    rts
.endp

;==============================================================
; clear_game_screens — Zeruje pamięć ekranów (ANTIC 5 + ANTIC 2)
; Łącznie do wyzerowania 560 bajtów (400 + 160).
;==============================================================
.proc clear_game_screens
    ; Czyści tylko mapę (480 bajtów), zostawiając status bar nienaruszony
    lda #0
    tax
@loop
    sta GAME_SCREEN_A5,x
    cpx #224                ; 480 = 256 + 224
    bcs @skip
    sta GAME_SCREEN_A5+$0100,x
@skip
    inx
    bne @loop
    rts
.endp



;==============================================================
; Przerwania DLI
;==============================================================

.proc game_dli
    pha
    txa
    pha

    ; Zmień font na font.fnt ($6000 -> CHBASE=$60)
    lda #$60
    sta CHBASE

    ; Ustawienie całej palety (rozwinięte)
    lda status_palette+0
    sta PCOLR0
    lda status_palette+1
    sta PCOLR1
    lda status_palette+2
    sta PCOLR2
    lda status_palette+3
    sta PCOLR3
    lda status_palette+4
    sta COLPF0
    lda status_palette+5
    sta COLPF1
    lda status_palette+6
    sta COLPF2
    lda status_palette+7
    sta COLPF3
    lda status_palette+8
    sta COLBK

    pla
    tax
    pla
    rti
.endp


