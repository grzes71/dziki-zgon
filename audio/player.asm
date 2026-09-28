; =============================================================================
; Relocatable 4-Channel POKEY Music Player for Atari 8-bit (MOS 6502)
; Compatible with MADS Macro Assembler
;
; Public API:
;   music_init        - X=song_lo, Y=song_hi: Initialize song & silence POKEY
;   music_play        - Start playback
;   music_stop        - Stop playback & silence POKEY
;   music_update      - Advance frame (call once per 50 Hz VBLANK)
;   music_is_playing  - Return A=1 if playing, A=0 if stopped
; =============================================================================

; --- Zero Page Configuration ---
    .ifndef PLAYER_ZP_BASE
PLAYER_ZP_BASE  = $80
    .endif

zp_ch1_ptr      = PLAYER_ZP_BASE + 0   ; 2 bytes: pointer to Ch 1 track data
zp_ch2_ptr      = PLAYER_ZP_BASE + 2   ; 2 bytes: pointer to Ch 2 track data
zp_ch3_ptr      = PLAYER_ZP_BASE + 4   ; 2 bytes: pointer to Ch 3 track data
zp_ch4_ptr      = PLAYER_ZP_BASE + 6   ; 2 bytes: pointer to Ch 4 track data
zp_tmp_ptr      = PLAYER_ZP_BASE + 8   ; 2 bytes: temporary pointer for headers/sequences

; --- Hardware Equates (if not included by caller) ---
AUDF1_REG       equ $D200
AUDC1_REG       equ $D201
AUDF2_REG       equ $D202
AUDC2_REG       equ $D203
AUDF3_REG       equ $D204
AUDC3_REG       equ $D205
AUDF4_REG       equ $D206
AUDC4_REG       equ $D207
AUDCTL_REG      equ $D208

; =============================================================================
; music_init
; Input: X = Song data address low byte
;        Y = Song data address high byte
; =============================================================================
.proc music_init
    stx song_ptr_lo
    sty song_ptr_hi
    stx zp_tmp_ptr
    sty zp_tmp_ptr + 1

    ; 1. Read Song Header
    ldy #0
    lda (zp_tmp_ptr),y          ; frames_per_tick
    sta tempo_divider
    sta tick_counter

    iny
    lda (zp_tmp_ptr),y          ; audctl_mode
    sta audctl_mode

    iny
    lda (zp_tmp_ptr),y          ; instruments_ptr low
    sta inst_ptr_lo
    iny
    lda (zp_tmp_ptr),y          ; instruments_ptr high
    sta inst_ptr_hi

    iny
    lda (zp_tmp_ptr),y          ; sequence_ptr low
    sta seq_ptr_lo
    iny
    lda (zp_tmp_ptr),y          ; sequence_ptr high
    sta seq_ptr_hi

    ; 2. Read Instruments Table (4 channels x 5 bytes)
    lda inst_ptr_lo
    sta zp_tmp_ptr
    lda inst_ptr_hi
    sta zp_tmp_ptr + 1

    ldy #0
    ldx #0
load_inst_loop:
    lda (zp_tmp_ptr),y          ; distortion
    sta ch_dist,x
    iny
    lda (zp_tmp_ptr),y          ; attack frames
    sta ch_att,x
    iny
    lda (zp_tmp_ptr),y          ; decay frames
    sta ch_dec,x
    iny
    lda (zp_tmp_ptr),y          ; sustain vol
    sta ch_sus,x
    iny
    lda (zp_tmp_ptr),y          ; release frames
    sta ch_rel,x
    iny
    inx
    cpx #4
    bne load_inst_loop

    ; 3. Reset Sequence and State
    lda #0
    sta seq_step_idx
    sta music_playing

    ; Force immediate note loading on all channels
    lda #0
    sta ch_dur + 0
    sta ch_dur + 1
    sta ch_dur + 2
    sta ch_dur + 3

    sta ch_env_phase + 0
    sta ch_env_phase + 1
    sta ch_env_phase + 2
    sta ch_env_phase + 3

    sta ch_cur_vol + 0
    sta ch_cur_vol + 1
    sta ch_cur_vol + 2
    sta ch_cur_vol + 3

    sta ch_mute_mask + 0
    sta ch_mute_mask + 1
    sta ch_mute_mask + 2
    sta ch_mute_mask + 3

    ; Load first pattern
    jsr load_pattern_ptrs

    ; 4. Silence POKEY
    jsr silence_pokey
    rts
.endp

; =============================================================================
; music_play
; Starts song playback
; =============================================================================
.proc music_play
    lda #1
    sta music_playing
    sta tick_counter            ; Trigger immediate row update on frame 1
    rts
.endp

; =============================================================================
; music_stop
; Stops playback and silences all channels
; =============================================================================
.proc music_stop
    lda #0
    sta music_playing
    jsr silence_pokey
    rts
.endp

; =============================================================================
; music_is_playing
; Returns A = 1 if playing, A = 0 if stopped
; =============================================================================
.proc music_is_playing
    lda music_playing
    rts
.endp

; =============================================================================
; music_update
; Frame update routine. Call exactly once per 50 Hz VBLANK frame.
; =============================================================================
.proc music_update
    lda music_playing
    bne @do_update
    rts

@do_update:
    ; 1. Decrement tick counter
    dec tick_counter
    bne @skip_row_advance

    ; Row advanced: reload tick counter
    lda tempo_divider
    sta tick_counter

    ; Advance row on each channel (0..3)
    ldx #0
advance_channel_loop:
    lda ch_dur,x
    beq @load_next_note
    dec ch_dur,x
    bne @channel_row_done

@load_next_note:
    jsr fetch_channel_note

@channel_row_done:
    inx
    cpx #4
    bne advance_channel_loop

@skip_row_advance:
    ; 2. Update envelopes for all channels
    jsr update_envelopes

    ; 3. Output to POKEY registers
    jsr write_pokey_registers
    rts
.endp

; =============================================================================
; fetch_channel_note
; Fetches next 3-byte note event for channel X from zp_ch[x]_ptr
; If $FF encountered, advances sequence and reloads pattern pointers
; =============================================================================
.proc fetch_channel_note
    ; Set up zp_tmp_ptr pointing to zp_ch[x]_ptr
    txa
    asl                         ; X * 2
    tay
    lda zp_ch1_ptr,y
    sta zp_tmp_ptr
    lda zp_ch1_ptr + 1,y
    sta zp_tmp_ptr + 1

    ldy #0
    lda (zp_tmp_ptr),y          ; Read AUDF or $FF
    cmp #$FF
    bne @got_note

    ; End of track encountered!
    ; If channel 0 reached end, advance whole song sequence
    cpx #0
    bne @early_end_track

    ; Channel 0 reached end of track: Advance sequence step
    txa
    pha                         ; Preserve channel index X
    clc
    lda seq_step_idx
    adc #2
    sta seq_step_idx
    jsr load_pattern_ptrs
    pla
    tax                         ; Restore channel index X

@reload_track_ptr:
    ; Re-fetch pointer for this channel after sequence advance
    txa
    asl
    tay
    lda zp_ch1_ptr,y
    sta zp_tmp_ptr
    lda zp_ch1_ptr + 1,y
    sta zp_tmp_ptr + 1

    ldy #0
    lda (zp_tmp_ptr),y
    jmp @got_note

@early_end_track:
    ; Channel X reached $FF before sequence advance: hold silence until pattern ends
    lda #0
    sta ch_audf,x
    sta ch_peak_vol,x
    sta ch_cur_vol,x
    sta ch_env_phase,x
    lda #1
    sta ch_dur,x
    rts

@got_note:
    sta ch_audf,x               ; Store AUDF
    iny

    lda (zp_tmp_ptr),y          ; Read duration
    sta ch_dur,x
    iny

    lda (zp_tmp_ptr),y          ; Read volume
    sta ch_peak_vol,x
    iny

    ; Advance pointer past this 3-byte event
    tya
    clc
    adc zp_tmp_ptr
    pha
    lda #0
    adc zp_tmp_ptr + 1
    tay                         ; high byte in Y
    pla                         ; low byte in A

    ; Store updated pointer back to zp_ch[x]_ptr
    cpx #0
    bne @check_ch1
    sta zp_ch1_ptr
    sty zp_ch1_ptr + 1
    jmp @setup_envelope
@check_ch1:
    cpx #1
    bne @check_ch2
    sta zp_ch2_ptr
    sty zp_ch2_ptr + 1
    jmp @setup_envelope
@check_ch2:
    cpx #2
    bne @check_ch3
    sta zp_ch3_ptr
    sty zp_ch3_ptr + 1
    jmp @setup_envelope
@check_ch3:
    sta zp_ch4_ptr
    sty zp_ch4_ptr + 1

@setup_envelope:
    ; Check if note is Rest (AUDF == 0 or peak_vol == 0)
    lda ch_audf,x
    beq @is_rest
    lda ch_peak_vol,x
    beq @is_rest

    ; Trigger new note: Attack phase
    lda #1
    sta ch_env_phase,x
    lda #0
    sta ch_env_frame,x
    sta ch_cur_vol,x
    rts

@is_rest:
    lda #0
    sta ch_env_phase,x
    sta ch_cur_vol,x
    rts
.endp

; =============================================================================
; load_pattern_ptrs
; Loads pattern track pointers for current seq_step_idx into zp_ch1..zp_ch4
; =============================================================================
.proc load_pattern_ptrs
    ; zp_tmp_ptr = seq_ptr + seq_step_idx
    clc
    lda seq_ptr_lo
    adc seq_step_idx
    sta zp_tmp_ptr
    lda seq_ptr_hi
    adc #0
    sta zp_tmp_ptr + 1

    ldy #0
    lda (zp_tmp_ptr),y
    tax
    iny
    lda (zp_tmp_ptr),y
    tay

    ; Check for $FFFF end of sequence marker
    cpx #$FF
    bne @valid_pat
    cpy #$FF
    bne @valid_pat

    ; End of song: Loop back to step 0
    lda #0
    sta seq_step_idx
    jmp load_pattern_ptrs

@valid_pat:
    ; X, Y contains address of pattern track list (pat_X_tracks)
    stx zp_tmp_ptr
    sty zp_tmp_ptr + 1

    ; Read 4 track pointers (8 bytes) into zp_ch1_ptr .. zp_ch4_ptr
    ldy #0
    lda (zp_tmp_ptr),y
    sta zp_ch1_ptr
    iny
    lda (zp_tmp_ptr),y
    sta zp_ch1_ptr + 1

    iny
    lda (zp_tmp_ptr),y
    sta zp_ch2_ptr
    iny
    lda (zp_tmp_ptr),y
    sta zp_ch2_ptr + 1

    iny
    lda (zp_tmp_ptr),y
    sta zp_ch3_ptr
    iny
    lda (zp_tmp_ptr),y
    sta zp_ch3_ptr + 1

    iny
    lda (zp_tmp_ptr),y
    sta zp_ch4_ptr
    iny
    lda (zp_tmp_ptr),y
    sta zp_ch4_ptr + 1
    rts
.endp

; =============================================================================
; update_envelopes
; Computes per-frame ADSR volume for all 4 channels
; =============================================================================
.proc update_envelopes
    ldx #0
@env_loop:
    lda ch_env_phase,x
    beq @phase_idle
    cmp #1
    beq @phase_attack
    cmp #2
    beq @phase_decay
    cmp #3
    beq @phase_sustain
    jmp @phase_release

@phase_idle:
    lda #0
    sta ch_cur_vol,x
    jmp @next_channel

@phase_attack:
    lda ch_att,x
    beq @attack_instant
    inc ch_env_frame,x
    lda ch_env_frame,x
    cmp ch_att,x
    bcc @attack_ramp

@attack_instant:
    ; Attack finished -> Decay phase
    lda #2
    sta ch_env_phase,x
    lda #0
    sta ch_env_frame,x
    lda ch_peak_vol,x
    sta ch_cur_vol,x
    jmp @next_channel

@attack_ramp:
    ; Ramp up towards peak volume
    lda ch_peak_vol,x
    lsr
    ora #1
    sta ch_cur_vol,x
    jmp @next_channel

@phase_decay:
    lda ch_dec,x
    beq @decay_instant
    inc ch_env_frame,x
    lda ch_env_frame,x
    cmp ch_dec,x
    bcc @decay_ramp

@decay_instant:
    ; Decay finished -> Sustain phase
    lda #3
    sta ch_env_phase,x
    lda ch_sus,x
    sta ch_cur_vol,x
    jmp @next_channel

@decay_ramp:
    lda ch_sus,x
    sta ch_cur_vol,x
    jmp @next_channel

@phase_sustain:
    lda ch_sus,x
    sta ch_cur_vol,x
    ; If note duration is finishing (<= release_frames), switch to release
    lda ch_dur,x
    cmp ch_rel,x
    bcs @next_channel
    lda #4
    sta ch_env_phase,x
    jmp @next_channel

@phase_release:
    ; Release phase: fade volume towards 0
    lda ch_cur_vol,x
    beq @release_done
    sec
    sbc #1
    sta ch_cur_vol,x
@release_done:

@next_channel:
    inx
    cpx #4
    beq @env_all_done
    jmp @env_loop
@env_all_done:
    rts
.endp

; =============================================================================
; write_pokey_registers
; Writes AUDF1..4, AUDC1..4, and AUDCTL to POKEY hardware registers
; Supports both 8-bit mode and 16-bit bass pairing
; =============================================================================
.proc write_pokey_registers
    lda audctl_mode
    sta AUDCTL_REG

    ; Check 16-bit bass mode (bit 4: AUDCTL_JOIN_1_2_16BIT)
    and #$10
    bne @write_16bit

    ; --- Standard 8-bit Mode (All 4 channels independent) ---
    ; Channel 1 (Bass)
    lda ch_audf + 0
    sta AUDF1_REG
    lda ch_mute_mask + 0
    bne @mute_ch1
    lda ch_cur_vol + 0
    beq @mute_ch1
    ora ch_dist + 0
@mute_ch1:
    sta AUDC1_REG

    ; Channel 2 (Counter / Harmony)
    lda ch_audf + 1
    sta AUDF2_REG
    lda ch_mute_mask + 1
    bne @mute_ch2
    lda ch_cur_vol + 1
    beq @mute_ch2
    ora ch_dist + 1
@mute_ch2:
    sta AUDC2_REG
    jmp @write_ch3_ch4

@write_16bit:
    ; --- 16-bit Bass Mode (Channels 1 & 2 joined) ---
    ; Ch 1 = AUDF low divider, AUDC muted
    lda ch_audf + 0
    sta AUDF1_REG
    lda #0
    sta AUDC1_REG

    ; Ch 2 = AUDF high divider, AUDC active volume
    lda ch_audf + 1
    sta AUDF2_REG
    lda ch_mute_mask + 0
    ora ch_mute_mask + 1
    bne @mute_ch2_16
    lda ch_cur_vol + 1
    beq @mute_ch2_16
    ora ch_dist + 1
@mute_ch2_16:
    sta AUDC2_REG

@write_ch3_ch4:
    ; Channel 3 (Lead Melody)
    lda ch_audf + 2
    sta AUDF3_REG
    lda ch_mute_mask + 2
    bne @mute_ch3
    lda ch_cur_vol + 2
    beq @mute_ch3
    ora ch_dist + 2
@mute_ch3:
    sta AUDC3_REG

    ; Channel 4 (Rhythm / Percussion / Ornament)
    lda ch_audf + 3
    sta AUDF4_REG
    lda ch_mute_mask + 3
    bne @mute_ch4
    lda ch_cur_vol + 3
    beq @mute_ch4
    ora ch_dist + 3
@mute_ch4:
    sta AUDC4_REG
    rts
.endp

; =============================================================================
; silence_pokey
; Sets all audio channels to volume 0 and zeroes AUDF registers
; =============================================================================
.proc silence_pokey
    lda #0
    sta AUDCTL_REG
    sta AUDC1_REG
    sta AUDC2_REG
    sta AUDC3_REG
    sta AUDC4_REG
    sta AUDF1_REG
    sta AUDF2_REG
    sta AUDF3_REG
    sta AUDF4_REG
    rts
.endp

; =============================================================================
; Player Runtime Variables (Relocatable BSS / Data area)
; =============================================================================
music_playing   .byte 0
tempo_divider   .byte 4
tick_counter    .byte 1
audctl_mode     .byte 0
seq_step_idx    .byte 0

song_ptr_lo     .byte 0
song_ptr_hi     .byte 0
inst_ptr_lo     .byte 0
inst_ptr_hi     .byte 0
seq_ptr_lo      .byte 0
seq_ptr_hi      .byte 0

; Per-channel state arrays (4 channels: 0..3)
ch_audf         .byte 0, 0, 0, 0
ch_dur          .byte 0, 0, 0, 0
ch_peak_vol     .byte 0, 0, 0, 0
ch_cur_vol      .byte 0, 0, 0, 0
ch_env_phase    .byte 0, 0, 0, 0
ch_env_frame    .byte 0, 0, 0, 0

ch_dist         .byte $C0, $A0, $A0, $00
ch_att          .byte 0, 1, 1, 0
ch_dec          .byte 4, 3, 4, 3
ch_sus          .byte 10, 9, 12, 8
ch_rel          .byte 2, 2, 3, 2
ch_mute_mask    .byte 0, 0, 0, 0
