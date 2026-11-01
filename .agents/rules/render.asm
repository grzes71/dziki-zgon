; ==============================================================================
; ENGINE/RENDER.ASM — Playfield Background Graphics Renderer
; Target: Atari 800XL / 65XE (MOS 6502)
; Mode: ANTIC Mode D ($0D, 160x96 2bpp, 2 scanlines/line, 40 bytes/line x 96 lines = 3,840 bytes)
; Features:
; - Full VRAM clearing ($3000-$3EFF)
; - Parameterized scene rendering (A = scene_id)
; - Automatic GTIA palette register setup
; - Direct 6502 row blitting with clipping
; - Hardware horizontal 2bpp flip support
; ==============================================================================

.proc clear_game_vram
    lda #0
    tax
@loop
    sta GAME_VRAM + $0000,x
    sta GAME_VRAM + $0100,x
    sta GAME_VRAM + $0200,x
    sta GAME_VRAM + $0300,x
    sta GAME_VRAM + $0400,x
    sta GAME_VRAM + $0500,x
    sta GAME_VRAM + $0600,x
    sta GAME_VRAM + $0700,x
    sta GAME_VRAM + $0800,x
    sta GAME_VRAM + $0900,x
    sta GAME_VRAM + $0A00,x
    sta GAME_VRAM + $0B00,x
    sta GAME_VRAM + $0C00,x
    sta GAME_VRAM + $0D00,x
    sta GAME_VRAM + $0E00,x
    inx
    bne @loop
    rts
.endp

.proc set_scene_palette
    ldx active_scene_id
    ldy scene_primary_tileset,x
    lda tileset_colbk,y
    sta COLOR4
    sta COLBK
    lda tileset_colpf0,y
    sta COLOR0
    sta COLPF0
    lda tileset_colpf1,y
    sta COLOR1
    sta COLPF1
    lda tileset_colpf2,y
    sta COLOR2
    sta COLPF2
    rts
.endp

.proc render_scene_background
    ; Parameter: A = scene index (0..SCENE_COUNT-1)
    cmp #SCENE_COUNT
    bcc @valid_scene
    rts

@valid_scene
    sta active_scene_id

    ; 1. Clear Game VRAM (3,840 bytes at $3000-$3EFF)
    jsr clear_game_vram

    ; 2. Configure GTIA palette registers from primary tileset of the scene
    jsr set_scene_palette

    ; 3. Setup element table pointers in zero page for active_scene_id
    ldx active_scene_id
    lda scene_elem_count,x
    sta zp_elem_count
    bne @has_elements
    rts

@has_elements
    lda scene_elem_tileset_lo,x
    sta zp_ptr_elem_ts
    lda scene_elem_tileset_hi,x
    sta zp_ptr_elem_ts+1

    lda scene_elem_src_x_byte_lo,x
    sta zp_ptr_elem_sx
    lda scene_elem_src_x_byte_hi,x
    sta zp_ptr_elem_sx+1

    lda scene_elem_src_y_lo,x
    sta zp_ptr_elem_sy
    lda scene_elem_src_y_hi,x
    sta zp_ptr_elem_sy+1

    lda scene_elem_w_byte_lo,x
    sta zp_ptr_elem_w
    lda scene_elem_w_byte_hi,x
    sta zp_ptr_elem_w+1

    lda scene_elem_h_lines_lo,x
    sta zp_ptr_elem_h
    lda scene_elem_h_lines_hi,x
    sta zp_ptr_elem_h+1

    lda scene_elem_dst_x_byte_lo,x
    sta zp_ptr_elem_dx
    lda scene_elem_dst_x_byte_hi,x
    sta zp_ptr_elem_dx+1

    lda scene_elem_dst_y_lo,x
    sta zp_ptr_elem_dy
    lda scene_elem_dst_y_hi,x
    sta zp_ptr_elem_dy+1

    lda scene_elem_flags_lo,x
    sta zp_ptr_elem_fl
    lda scene_elem_flags_hi,x
    sta zp_ptr_elem_fl+1

    ; 4. Draw each element (zp_elem_idx = 0 .. zp_elem_count - 1)
    lda #0
    sta zp_elem_idx

@elem_loop
    ldy zp_elem_idx

    ; Read element width & height
    lda (zp_ptr_elem_w),y
    sta zp_elem_w
    beq @do_skip

    lda (zp_ptr_elem_h),y
    sta zp_elem_h
    beq @do_skip

    ; Read element destination x & y
    lda (zp_ptr_elem_dx),y
    cmp #40
    bcs @do_skip
    sta zp_temp_x             ; dst_x_byte

    lda (zp_ptr_elem_dy),y
    cmp #96
    bcc @coords_ok

@do_skip
    jmp @skip_elem

@coords_ok
    sta zp_temp_y             ; dst_y

    ; Read flags (bit 0 = flip_x)
    lda (zp_ptr_elem_fl),y
    sta zp_flags

    ; Clip width: if dst_x_byte + w > 40 -> w = 40 - dst_x_byte
    lda zp_temp_x
    clc
    adc zp_elem_w
    cmp #41
    bcc @w_clipped_ok
    lda #40
    sec
    sbc zp_temp_x
    sta zp_elem_w
@w_clipped_ok

    ; Clip height: if dst_y + h > 96 -> h = 96 - dst_y
    lda zp_temp_y
    clc
    adc zp_elem_h
    cmp #97
    bcc @h_clipped_ok
    lda #96
    sec
    sbc zp_temp_y
    sta zp_elem_h
@h_clipped_ok

    ; Read tileset ID and set up stride and row tables
    ldy zp_elem_idx
    lda (zp_ptr_elem_ts),y
    tax                       ; X = tileset_id (0..3)

    lda tileset_w_bytes,x
    sta zp_stride

    lda tileset_row_lo_table_lo,x
    sta zp_ptr_row_lo
    lda tileset_row_lo_table_hi,x
    sta zp_ptr_row_lo+1

    lda tileset_row_hi_table_lo,x
    sta zp_ptr_row_hi
    lda tileset_row_hi_table_hi,x
    sta zp_ptr_row_hi+1

    ; Calculate initial src_ptr = tileset_base + row_offset(src_y) + src_x_byte
    ldy zp_elem_idx
    lda (zp_ptr_elem_sy),y
    tay                       ; Y = src_y
    lda (zp_ptr_row_lo),y     ; row_offset lo
    ldy zp_elem_idx
    clc
    adc (zp_ptr_elem_sx),y    ; + src_x_byte
    sta zp_ptr_src
    lda (zp_ptr_elem_sy),y
    tay
    lda (zp_ptr_row_hi),y     ; row_offset hi
    adc #0
    sta zp_ptr_src+1

    ; Add tileset_data base address (tileset X)
    clc
    lda zp_ptr_src
    adc tileset_data_lo,x
    sta zp_ptr_src
    lda zp_ptr_src+1
    adc tileset_data_hi,x
    sta zp_ptr_src+1

    ; Calculate initial dst_ptr = playfield_row[dst_y] + dst_x_byte
    ldy zp_temp_y
    clc
    lda playfield_row_lo,y
    adc zp_temp_x
    sta zp_ptr_dst
    lda playfield_row_hi,y
    adc #0
    sta zp_ptr_dst+1

    ; Scanline draw loop
@scanline_loop
    lda zp_flags
    lsr                       ; Bit 0 = flip_x
    bcs @draw_flip_line

    ; Normal blit (left-to-right copy)
    ldy #0
@copy_col
    lda (zp_ptr_src),y
    sta (zp_ptr_dst),y
    iny
    cpy zp_elem_w
    bne @copy_col
    jmp @advance_line

@draw_flip_line
    ; Flipped blit (right-to-left source, reversed 2bpp pixel order)
    ldy zp_elem_w
    dey
    sty zp_src_idx            ; start from w - 1
    lda #0
    sta zp_dst_idx            ; write to 0
    lda zp_elem_w
    sta zp_bytes_left

@flip_col
    ldy zp_src_idx
    lda (zp_ptr_src),y
    tax
    lda flip_byte_2bpp,x
    ldy zp_dst_idx
    sta (zp_ptr_dst),y
    inc zp_dst_idx
    dec zp_src_idx
    dec zp_bytes_left
    bne @flip_col

@advance_line
    ; Advance src_ptr by zp_stride
    clc
    lda zp_ptr_src
    adc zp_stride
    sta zp_ptr_src
    lda zp_ptr_src+1
    adc #0
    sta zp_ptr_src+1

    ; Advance dst_ptr by 40
    clc
    lda zp_ptr_dst
    adc #40
    sta zp_ptr_dst
    lda zp_ptr_dst+1
    adc #0
    sta zp_ptr_dst+1

    dec zp_elem_h
    bne @scanline_loop

@skip_elem
    inc zp_elem_idx
    lda zp_elem_idx
    cmp zp_elem_count
    bcs @done
    jmp @elem_loop

@done
    rts
.endp
