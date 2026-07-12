;----------------------------------------
; tests/real_collision_test.asm
;----------------------------------------

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

FrameCounter    .ds 1
InputState_Joy  .ds 1
InputState_Trig .ds 1
game_fire_released .ds 1
Engine_RequestStageAdvance .ds 1
HPOSP0 .ds 4
PCOLR0 .ds 4

    org $2000
start_test_player
    jsr Player_Update
    brk
    rts
    
start_test_collision
    jsr Collision_Update
    brk
    rts

    org $4000
PMBASE_ADDR    .ds 2048
GAME_SCREEN_A5 .ds 480

SPRITE_GERWALT_RIGHT_FRAMES = 4
SPRITE_GERWALT_LEFT_FRAMES = 4
SPRITE_GERWALT_UP_FRAMES = 4
SPRITE_GERWALT_DOWN_FRAMES = 4

SCREEN_LIMIT_LEFT   = 48
SCREEN_LIMIT_RIGHT  = 200
SCREEN_LIMIT_TOP    = 32
SCREEN_LIMIT_BOTTOM = 210

TRANSITION_SPAWN_LEFT   = 48
TRANSITION_SPAWN_RIGHT  = 199
TRANSITION_SPAWN_TOP    = 32
TRANSITION_SPAWN_BOTTOM = 209

    org $5000
    icl "../engine/actor.asm"

    org $6000
    icl "../engine/player.asm"
    icl "../engine/collision.asm"

    org $7000
    icl "../gen/world/world.inc"
    icl "../gen/world/objects.asm"
    icl "../gen/world/regions.asm"
    icl "../gen/world/screens.asm"
    icl "../gen/world/exits.asm"
