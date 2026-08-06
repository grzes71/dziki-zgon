;----------------------------------------
; engine/iis.asm — Inventory Interaction System (IIS)
;----------------------------------------

iis_fire_was_pressed dta $00
iis_grid_x1         dta $00
iis_grid_x2         dta $00
iis_grid_y1         dta $00
iis_grid_y2         dta $00
iis_obj_x1          dta $00
iis_obj_x2          dta $00
iis_obj_y1          dta $00
iis_obj_y2          dta $00

INTERACTIVE_OBJ_COMPLETE .ds SCREEN_COUNT

.proc iis_init
    lda #1
    sta iis_fire_was_pressed

    ldx #SCREEN_COUNT-1
@loop
    lda INTERACTIVE_OBJ_COMPLETE_INIT,x
    sta INTERACTIVE_OBJ_COMPLETE,x
    dex
    bpl @loop
    rts
.endp

.proc IIS_Update
    ; 1. Fire button edge trigger check (TRIG0 = 0 when pressed, 1 when released)
    lda InputState_Trig
    bne @fire_released

    ; Fire IS pressed (0)
    lda iis_fire_was_pressed
    bne @done                 ; already handled for this press
    lda #1
    sta iis_fire_was_pressed  ; mark handled
    jmp @check_interaction

@fire_released
    lda #0
    sta iis_fire_was_pressed
    rts

@check_interaction
    ; 2. Check if current screen (GAME_SCREEN_ID) has an interactive object
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_PRESENT,x
    bne @has_interactive_obj
@done
    rts

@has_interactive_obj
    ; 3. Compute Gerwalt's (Actor 0) grid bounding box
    ; G_X1 = (ACTOR_X[0] - 48) / 4
    ; G_X2 = (ACTOR_X[0] - 48 + 7) / 4
    lda ACTOR_X
    sec
    sbc #48
    lsr
    lsr
    sta iis_grid_x1

    lda ACTOR_X
    sec
    sbc #48
    clc
    adc #7
    lsr
    lsr
    sta iis_grid_x2

    ; G_Y1 = (ACTOR_Y[0] - 32) / 16
    ; G_Y2 = (ACTOR_Y[0] - 32 + ACTOR_HEIGHT[0] - 1) / 16
    lda ACTOR_Y
    sec
    sbc #32
    lsr
    lsr
    lsr
    lsr
    sta iis_grid_y1

    lda ACTOR_Y
    sec
    sbc #32
    clc
    adc ACTOR_HEIGHT
    sec
    sbc #1
    lsr
    lsr
    lsr
    lsr
    sta iis_grid_y2

    ; 4. Compute Interactive Object grid bounding box
    ; O_X1 = INTERACTIVE_OBJ_X,x
    ; O_X2 = O_X1 + INTERACTIVE_OBJ_W,x - 1
    ; O_Y1 = INTERACTIVE_OBJ_Y,x
    ; O_Y2 = O_Y1 + INTERACTIVE_OBJ_H,x - 1
    lda INTERACTIVE_OBJ_X,x
    sta iis_obj_x1
    clc
    adc INTERACTIVE_OBJ_W,x
    sec
    sbc #1
    sta iis_obj_x2

    lda INTERACTIVE_OBJ_Y,x
    sta iis_obj_y1
    clc
    adc INTERACTIVE_OBJ_H,x
    sec
    sbc #1
    sta iis_obj_y2

    ; 5. Proximity & Facing direction check (ACTOR_DIR[0]: 0=Right, 1=Left, 2=Up, 3=Down)
    ldy ACTOR_DIR
    cpy #0
    beq @facing_right
    cpy #1
    beq @facing_left
    cpy #2
    beq @facing_up
    cpy #3
    beq @facing_down
    rts

@facing_right
    ; Moving/Facing Right towards object:
    ; G_X2 + 1 >= O_X1 AND G_X1 < O_X1 AND Y-overlap (G_Y1 <= O_Y2 AND G_Y2 >= O_Y1)
    lda iis_grid_x2
    clc
    adc #1
    cmp iis_obj_x1
    bcc @no_interaction

    lda iis_grid_x1
    cmp iis_obj_x1
    bcs @no_interaction

    jmp @check_y_overlap

@facing_left
    ; Moving/Facing Left towards object:
    ; G_X1 <= O_X2 + 1 AND G_X2 > O_X2 AND Y-overlap
    lda iis_obj_x2
    clc
    adc #1
    cmp iis_grid_x1
    bcc @no_interaction

    lda iis_grid_x2
    cmp iis_obj_x2
    bcc @no_interaction
    beq @no_interaction

    jmp @check_y_overlap

@facing_up
    ; Moving/Facing Up towards object:
    ; G_Y1 <= O_Y2 + 1 AND G_Y2 > O_Y2 AND X-overlap (G_X1 <= O_X2 AND G_X2 >= O_X1)
    lda iis_obj_y2
    clc
    adc #1
    cmp iis_grid_y1
    bcc @no_interaction

    lda iis_grid_y2
    cmp iis_obj_y2
    bcc @no_interaction
    beq @no_interaction

    jmp @check_x_overlap

@facing_down
    ; Moving/Facing Down towards object:
    ; G_Y2 + 1 >= O_Y1 AND G_Y1 < O_Y1 AND X-overlap
    lda iis_grid_y2
    clc
    adc #1
    cmp iis_obj_y1
    bcc @no_interaction

    lda iis_grid_y1
    cmp iis_obj_y1
    bcs @no_interaction

    jmp @check_x_overlap

@check_y_overlap
    ; Y-overlap check: G_Y1 <= O_Y2 AND G_Y2 >= O_Y1
    lda iis_grid_y1
    cmp iis_obj_y2
    beq @y_ok
    bcc @y_ok
    rts
@y_ok
    lda iis_grid_y2
    cmp iis_obj_y1
    bcs @proximity_ok
    rts

@check_x_overlap
    ; X-overlap check: G_X1 <= O_X2 AND G_X2 >= O_X1
    lda iis_grid_x1
    cmp iis_obj_x2
    beq @x_ok
    bcc @x_ok
    rts
@x_ok
    lda iis_grid_x2
    cmp iis_obj_x1
    bcs @proximity_ok
@no_interaction
    rts

@proximity_ok
    ; 6. Gerwalt is in front of interactive object! Trigger interaction SFX
    lda #1
    sta Request_SFX_Interact

    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_COMPLETE,x
    bne @do_interaction_incomplete
    jmp @interaction_already_complete


@do_interaction_incomplete
    ; INTERACTION_COMPLETE == 1: object expects required items interaction
    lda INTERACTIVE_OBJ_REQ_COUNT,x
    beq @has_all_reqs           ; 0 items required -> conditions met

    sta SRC_TMP+1               ; store REQ_COUNT in SRC_TMP+1
    lda INTERACTIVE_OBJ_REQ_PTR_LO,x
    sta SRC_PTR
    lda INTERACTIVE_OBJ_REQ_PTR_HI,x
    sta SRC_PTR+1

    ldy #0
@check_req_loop
    lda (SRC_PTR),y
    jsr inventory_has_item
    bcs @conditions_unmet       ; item missing! C=1

    iny
    cpy SRC_TMP+1
    bne @check_req_loop

@has_all_reqs
    ; 7. Conditions Met! Remove required items, add provided items
    ldx GAME_SCREEN_ID
    lda #0
    sta INTERACTIVE_OBJ_COMPLETE,x   ; Mark interaction complete!

    lda INTERACTIVE_OBJ_REQ_COUNT,x
    beq @add_provided

    sta SRC_TMP+1
    lda INTERACTIVE_OBJ_REQ_PTR_LO,x
    sta SRC_PTR
    lda INTERACTIVE_OBJ_REQ_PTR_HI,x
    sta SRC_PTR+1

    ldy #0
@remove_req_loop
    tya
    pha                         ; save Y loop index on stack
    lda (SRC_PTR),y
    jsr inventory_remove_item
    pla
    tay                         ; restore Y loop index
    iny
    cpy SRC_TMP+1
    bne @remove_req_loop

@add_provided
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_PROV_COUNT,x
    beq @show_met_msg

    sta SRC_TMP+1
    lda INTERACTIVE_OBJ_PROV_PTR_LO,x
    sta SRC_PTR
    lda INTERACTIVE_OBJ_PROV_PTR_HI,x
    sta SRC_PTR+1

    ldy #0
@add_prov_loop
    tya
    pha                         ; save Y loop index
    lda (SRC_PTR),y
    pha                         ; save item ID
    jsr inventory_add_item
    pla                         ; A = item ID
    cmp #5                      ; Check if received Item 5 ("Podarty rachunek")
    bne @not_item_5

    ; Success! Set GAME_RESULT_STATUS = 1 & request stage advance
    lda #1
    sta GAME_RESULT_STATUS
    sta Engine_RequestStageAdvance

@not_item_5
    pla
    tay                         ; restore Y loop index
    iny
    cpy SRC_TMP+1
    bne @add_prov_loop

@show_met_msg
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_MSG_MET_LO,x
    ldy INTERACTIVE_OBJ_MSG_MET_HI,x
    jsr msg_show
    rts

@conditions_unmet
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_MSG_UNMET_LO,x
    ldy INTERACTIVE_OBJ_MSG_UNMET_HI,x
    jsr msg_show
    rts

@interaction_already_complete
    ; INTERACTION_COMPLETE == 0: check object type
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_TYPE,x
    beq @type_kwatera          ; 0 = kwatera -> do nothing
    cmp #1
    beq @type_portal           ; 1 = portal
    rts

@type_kwatera
    rts

@type_portal
    ; Check if message_travel is already being displayed (MSG_STATE != 0)
    lda MSG_STATE
    bne @do_portal_transition

    ; MSG_STATE == 0: 1st press -> show message_travel
    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_MSG_TRAVEL_LO,x
    ldy INTERACTIVE_OBJ_MSG_TRAVEL_HI,x
    jsr msg_show
    rts

@do_portal_transition
    ; MSG_STATE != 0: 2nd press -> clear message & execute portal transition
    jsr clear_msg_line_display
    lda #0
    sta MSG_STATE

    ldx GAME_SCREEN_ID
    lda INTERACTIVE_OBJ_PORTAL_SCREEN,x
    cmp #$FF
    beq @portal_err            ; invalid portal target

    sta NEW_SCREEN_ID
    lda INTERACTIVE_OBJ_PORTAL_X,x
    sta NEW_ACTOR_X
    lda INTERACTIVE_OBJ_PORTAL_Y,x
    sta NEW_ACTOR_Y

    lda #1
    sta REQ_SCREEN_TRANSITION
    sta IS_PORTAL_TRANSITION

@portal_err
    rts
.endp
