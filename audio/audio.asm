; ===================================================================
; audio/audio.asm — Sterownik systemu audio (Atari POKEY Music)
; Obsługa utworów dla scen: Title, Story, GameOver
; ===================================================================

SETVBV = $E45C
XITVBV = $E462
SYSVBV = $E45F

; --- Odtwarzanie poszczególnych motywów muzycznych ---

audio_play_title
    ldx #<music_title_data
    ldy #>music_title_data
    jmp audio_start_song

audio_play_intro
    ldx #<music_intro_data
    ldy #>music_intro_data
    jmp audio_start_song

audio_play_gameover_failure
    ldx #<music_gameover_failure_data
    ldy #>music_gameover_failure_data
    jmp audio_start_song

audio_play_gameover_success
    ldx #<music_gameover_success_data
    ldy #>music_gameover_success_data
    jmp audio_start_song

audio_play_gameover
    lda GAME_RESULT_STATUS
    cmp #1                      ; 1 = Sukces
    beq audio_play_gameover_success
    jmp audio_play_gameover_failure

; Alias dla zachowania wstecznej kompatybilności
title_audio_init = audio_play_title

; --- Inicjalizacja i uruchomienie wybranego utworu ---
audio_start_song
    jsr music_init
    jsr music_play

    ; Zapisz oryginalny wektor Immediate VBI ($0222)
    lda orig_vbi+1
    bne @already_saved
    lda $0222
    sta orig_vbi
    lda $0223
    sta orig_vbi+1
    lda orig_vbi+1
    cmp #$04
    bcs @already_saved
    lda #<SYSVBV
    sta orig_vbi
    lda #>SYSVBV
    sta orig_vbi+1

@already_saved
    ; Zainstaluj domyślny handler Immediate VBI
    lda NMIEN
    pha
    lda #0
    sta NMIEN               ; Wyłącz NMI na czas modyfikacji wektora
    lda #<audio_vblank_handler
    sta $0222
    lda #>audio_vblank_handler
    sta $0223
    pla
    and #$80
    ora #$40
    sta NMIEN
    rts

; --- Domyślny Immediate VBI handler dla odtwarzacza ---
audio_vblank_handler
    lda #0
    sta ATRACT
    jsr music_update
    jmp SYSVBV

; --- Zatrzymanie muzyki i wyciszenie POKEY ---
audio_stop
title_audio_stop
    ; Przywróć oryginalny wektor Immediate VBI
    lda #0
    sta NMIEN               ; Wyłącz NMI podczas przywracania
    
    lda orig_vbi+1
    cmp #$04
    bcs @valid_orig
    lda #<SYSVBV
    sta $0222
    lda #>SYSVBV
    sta $0223
    jmp @vbi_restored

@valid_orig
    lda orig_vbi
    sta $0222
    lda orig_vbi+1
    sta $0223

@vbi_restored
    lda #0
    sta orig_vbi
    sta orig_vbi+1
    sta NMIEN

    jsr music_stop
    jsr silence_pokey
    rts

orig_vbi
    dta a(0)
