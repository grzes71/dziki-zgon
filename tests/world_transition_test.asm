;----------------------------------------
; tests/world_transition_test.asm
; Test Harness dla World_Update i przejść między ekranami
;----------------------------------------

; --- Mocki adresów Zero Page ---
    org $20
ACTOR_TMP_X       .ds 1
ACTOR_TMP_Y       .ds 1
ACTOR_TMP_HEIGHT  .ds 1
ACTOR_TMP_PAD     .ds 1
PMG_PTR         .ds 2
SRC_PTR         .ds 2
DST_PTR         .ds 2
SRC_TMP         .ds 2
SCREEN_PTR      .ds 2
GAME_SCREEN_ID  .ds 1
OBJ_CODE        .ds 1
OBJ_X           .ds 1
OBJ_Y           .ds 1
REQ_SCREEN_TRANSITION .ds 1
NEW_SCREEN_ID         .ds 1
NEW_ACTOR_X           .ds 1
NEW_ACTOR_Y           .ds 1
game_stage            .ds 1

HPOSP0 = $D000
HITCLR = $D01E

; --- Entry Point ---
    org $2000
start_test_world_update
    jsr World_Update
    brk
    rts

; --- Mocki buforów i danych ---
    org $4000
GAME_SCREEN_A5 .ds 480
GAME_SCREEN_A2 .ds 80
SCREEN_REGION  .ds 256

; --- System Aktorów ---
    org $5000
    icl "../engine/actor.asm"

; --- Moduł World ---
    org $6000
    icl "../engine/world.asm"

; Mocki procedur zewnętrznych wywoływanych przez World_Update
clear_game_screens
    rts
build_screen
    rts
check_active_charset_animations
    rts
update_stage_colors
    rts
draw_region_name
    rts
pmg_clear_all
    rts
init_game_missiles
    rts
