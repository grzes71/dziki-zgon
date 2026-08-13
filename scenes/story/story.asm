;----------------------------------------
; scenes/story/story.asm — Ekran opisu (ANTIC mode 2, 40 znaków/linia)
;----------------------------------------

;---- Zmienne lokalne sceny ----
fire_released_flag
    dta $00

;---- story_init — Konfiguracja ANTIC mode 2 ----
.proc story_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta GPRIOR               ; reset priorytetów
    sta fire_released_flag  ; zresetuj stan joysticka

    jsr pmg_clear_all
    jsr copy_story_text

    ; --- Display List ---
    lda #<DLIST_STORY
    sta SDLSTL
    sta DLISTL
    lda #>DLIST_STORY
    sta SDLSTH
    sta DLISTH

    ; --- Charset (własny font $6000 — ten sam co w tytule) ---
    lda #$60
    sta CHBAS
    sta CHBASE

    ; --- Kolory: biały tekst na czarnym tle ---
    lda #$00
    sta COLOR4
    sta COLBK            ; czarna ramka
    sta COLOR2
    sta COLPF2           ; czarne tło znaków
    sta COLOR3
    sta COLPF3           ; nieużywane
    sta COLOR0
    sta COLPF0           ; nieużywane
    lda #$0E
    sta COLOR1
    sta COLPF1           ; biały tekst (COLPF1 w ANTIC mode 2)

    ; --- Audio ---
    jsr title_audio_init

    ; --- DMA ON (playfield, bez PMG) ---
    lda #$22
    sta SDMCTL
    sta DMACTL

    ; --- VBI ON, DLI OFF ---
    lda #$40
    sta NMIEN

    rts
.endp

;==============================================================
; story_run — Czeka na puszczenie FIRE, potem na FIRE → GAME
;==============================================================
.proc story_run
    lda fire_released_flag
    bne @wait_press

    ; 1. Czekaj na puszczenie przycisku FIRE (trzymany z ekranu tytułowego)
    lda TRIG0
    beq @exit            ; wciąż trzyma — zostań w story
    lda #1
    sta fire_released_flag
    bne @exit            ; wyjdź w tej klatce

@wait_press
    ; 2. Czekaj na ponowne naciśnięcie przycisku FIRE
    lda TRIG0
    bne @exit            ; jeszcze nie nacisnął ponownie
    jsr advance_stage
@exit
    rts
.endp

;==============================================================
; copy_story_text — Kopiuje tekst story (320 B) z ROM do RAM ($5E10)
;==============================================================
.proc copy_story_text
    jsr show_story_header

    ; Clear footer buffer (320 B)
    ldx #0
    lda #0
@clr
    sta StoryText_RAM,x
    cpx #64
    bcs @skip
    sta StoryText_RAM+256,x
@skip
    inx
    bne @clr

    mRLE_Depack StoryText_Data StoryText_RAM
    rts
.endp
