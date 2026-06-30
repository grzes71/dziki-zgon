; ===================================================================
; music/audio.asm — MADS configuration and integration of RMT player
; Configured to load at free RAM sector $8800
; ===================================================================

SETVBV = $E45C
XITVBV = $E462
SYSVBV = $E45F

    org $8800

; --- Initialize RMT and set up Immediate VBLANK ---
title_audio_init
    ldx #<MODUL
    ldy #>MODUL
    lda #0                  ; Subsong number
    jsr RASTERMUSICTRACKER  ; Init player

    ; Save original Immediate VBI vector ($0222)
    lda $0222
    sta orig_vbi
    lda $0223
    sta orig_vbi+1

    ; Install custom Immediate VBI handler directly
    lda #0
    sta NMIEN               ; Disable NMIs temporarily
    lda #<vblank_player
    sta $0222               ; Low byte of VVBLKI
    lda #>vblank_player
    sta $0223               ; High byte of VVBLKI
    lda #$C0                ; Restore NMIEN (DLI + VBI)
    sta NMIEN
    rts

; --- Immediate VBI Music player handler ---
vblank_player
    jsr RASTERMUSICTRACKER+3 ; Play one frame
    jmp SYSVBV              ; Exit to OS VBI processing (SYSVBV)

; --- Stop audio and silence Pokey ---
title_audio_stop
    ; Restore original Immediate VBI vector ($0222)
    lda #0
    sta NMIEN               ; Disable NMIs temporarily
    lda orig_vbi
    sta $0222
    lda orig_vbi+1
    sta $0223
    lda #$C0                ; Restore NMIEN (DLI + VBI)
    sta NMIEN

    jsr RASTERMUSICTRACKER+9 ; Silence tracker player

    ; Clear Pokey audio registers
    lda #0
    sta $D200
    sta $D201
    sta $D202
    sta $D203
    sta $D204
    sta $D205
    sta $D206
    sta $D207
    sta $D208
    rts

; --- Variables and Storage ---
orig_vbi
    dta a(0)

dummy_vbi
    jmp XITVBV

; --- Player and variables mapping ---
; Define player location (must be page aligned)
PLAYER = $8C00

; Include the converted player code
    icl "gen/rmtplayr.asm"

; Song data module
    .align 256
MODUL
    icl "gen/title_music.asm"
