; ===================================================================
; music/title_audio.asm — MADS configuration and integration of RMT player
; Configured to load at free RAM sector $8800
; ===================================================================

SETVBV = $E45C
XITVBV = $E462
SYSVBV = $E45F

; --- Initialize RMT and set up Immediate VBLANK for Title Screen ---
title_audio_init
    ldx #<MODUL
    ldy #>MODUL
    lda #0                  ; Subsong number
    jsr RASTERMUSICTRACKER  ; Init player

    ; Save original Immediate VBI vector ($0222) if valid, else default to SYSVBV
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
    ; Install custom Immediate VBI handler directly
    lda NMIEN
    pha
    lda #0
    sta NMIEN               ; Disable NMIs temporarily
    lda #<vblank_player
    sta $0222               ; Low byte of VVBLKI
    lda #>vblank_player
    sta $0223               ; High byte of VVBLKI
    pla
    and #$80
    ora #$40
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
    sta NMIEN               ; Disable NMIs during audio stop & transition
    
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
