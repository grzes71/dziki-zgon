;----------------------------------------
; tests/actor_test.asm
; Test Harness dla systemu aktorów
;----------------------------------------

; --- Mocki adresów Zero Page (takie jak w zeropage.asm) ---
    org $20
ACTOR_TMP_X       .ds 1
ACTOR_TMP_Y       .ds 1
ACTOR_TMP_HEIGHT  .ds 1
ACTOR_TMP_PAD     .ds 1
PMG_PTR         .ds 2   ; 2 bajty dla Render_Prepare
SRC_PTR         .ds 2   ; 2 bajty dla wskaźników
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
ENEMY_COUNT_TMP       .ds 1
CURRENT_ACTOR         .ds 1

FrameCounter    .ds 1
InputState_Joy  .ds 1
InputState_Trig .ds 1
game_fire_released .ds 1
Engine_RequestStageAdvance .ds 1
Request_SFX_Step           .ds 1
Request_SFX_Item           .ds 1
Request_SFX_Interact       .ds 1
HPOSP0 .ds 4
HPOSP1 = HPOSP0 + 1
HPOSP2 = HPOSP0 + 2
HPOSP3 = HPOSP0 + 3
HPOSM0 .ds 4
HPOSM1 = HPOSM0 + 1
HPOSM2 = HPOSM0 + 2
HPOSM3 = HPOSM0 + 3
PCOLR0 .ds 4
PCOLR1 = PCOLR0 + 1
PCOLR2 = PCOLR0 + 2
PCOLR3 = PCOLR0 + 3

MISSILES = PMBASE_ADDR + $300
PLAYER0  = PMBASE_ADDR + $400
PLAYER1  = PMBASE_ADDR + $500
PLAYER2  = PMBASE_ADDR + $600
PLAYER3  = PMBASE_ADDR + $700

HERO_COLOR_0 = $F4
HERO_COLOR_1 = $18
HERO_COLOR_DAMAGE = $34

; --- Entry Points ---
    org $2000
start_test_player
    jsr Player_Update
    brk
    rts

start_test_collision
    jsr Collision_Update
    brk
    rts

start_test_render
    jsr Render_Prepare
    brk
    rts

start_test_npc_update
    jsr NPC_Update
    brk
    rts

start_test_load_enemies
    jsr Load_Screen_Enemies
    brk
    rts

; --- Mockowanie globalnych tablic kolizji ---
    org $3000
SCREEN_POINTERS_LO .ds 256
SCREEN_POINTERS_HI .ds 256
OBJ_SIZE           .ds 256
OBJ_FLAGS          .ds 256
EXITS_TABLE        .ds 1024

; --- Mockowanie PMG i Ekranu ---
    org $4000
PMBASE_ADDR    .ds 2048 ; 2KB bufor PMG
GAME_SCREEN_A5 .ds 480

; --- Zmienne globalne i Actor System ---
    org $5000
    icl "../engine/actor.asm"

; --- Biblioteki silnika ---
    org $6000
    icl "../engine/player.asm"
    icl "../engine/collision.asm"
    icl "../engine/render.asm"
    icl "../engine/npc.asm"

    ; Mock dla pmg_clear_all (z main.asm)
pmg_clear_all
    rts

; Mocki tablic sprite'ów
HERO_ANIM_SPEED_HORIZ = 4
HERO_ANIM_SPEED_VERT = 6
HERO_STEP_SFX_INTERVAL = 6
SPRITE_GERWALT_RIGHT_FRAMES = 4
SPRITE_GERWALT_LEFT_FRAMES = 4
SPRITE_GERWALT_UP_FRAMES = 4
SPRITE_GERWALT_DOWN_FRAMES = 4

SPRITE_KIKIMORA_FRAMES = 2
SPRITE_KIKIMORA_HEIGHT = 16
SPRITE_STRZYGA_FRAMES = 2
SPRITE_STRZYGA_HEIGHT = 16
SPRITE_BAZYLISZEK_FRAMES = 2
SPRITE_BAZYLISZEK_HEIGHT = 16
SPRITE_SUKKUB_RIGHT_FRAMES = 2
SPRITE_SUKKUB_LEFT_FRAMES = 2
SPRITE_SUKKUB_RIGHT_HEIGHT = 16
SPRITE_SUKKUB_LEFT_HEIGHT = 16

KIKIMORA_PTRS
STRZYGA_PTRS
BAZYLISZEK_PTRS
SUKKUB_RIGHT_PTRS
SUKKUB_LEFT_PTRS
    dta a(0)

SCREEN_LIMIT_LEFT   = 48
SCREEN_LIMIT_RIGHT  = 200
SCREEN_LIMIT_TOP    = 32
SCREEN_LIMIT_BOTTOM = 210

TRANSITION_SPAWN_LEFT   = 48
TRANSITION_SPAWN_RIGHT  = 199
TRANSITION_SPAWN_TOP    = 32
TRANSITION_SPAWN_BOTTOM = 209

GERWALT_RIGHT_PTRS
GERWALT_LEFT_PTRS
GERWALT_UP_PTRS
GERWALT_DOWN_PTRS
GERWALT_RIGHT_P0_PTRS
GERWALT_LEFT_P0_PTRS
GERWALT_UP_P0_PTRS
GERWALT_DOWN_P0_PTRS
GERWALT_RIGHT_P1_PTRS
GERWALT_LEFT_P1_PTRS
GERWALT_UP_P1_PTRS
GERWALT_DOWN_P1_PTRS
    dta a(GERWALT_SPRITE)

GERWALT_SPRITE
    .ds 14
