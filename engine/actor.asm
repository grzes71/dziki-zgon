;----------------------------------------
; engine/actor.asm — System Aktorów (SoA)
;----------------------------------------

MAX_ACTORS = 4

; Zmienne globalne w głównym bloku RAM
ACTOR_ACTIVE
    .ds MAX_ACTORS
ACTOR_X
    .ds MAX_ACTORS
ACTOR_Y
    .ds MAX_ACTORS
ACTOR_Y_OLD
    .ds MAX_ACTORS
ACTOR_INTENT_X
    .ds MAX_ACTORS
ACTOR_INTENT_Y
    .ds MAX_ACTORS
ACTOR_DIR
    .ds MAX_ACTORS
ACTOR_ANIM_FRAME
    .ds MAX_ACTORS
ACTOR_ANIM_TIMER
    .ds MAX_ACTORS
ACTOR_ANIM_SPEED
    .ds MAX_ACTORS
ACTOR_PTRS_TABLE_LO
    .ds MAX_ACTORS
ACTOR_PTRS_TABLE_HI
    .ds MAX_ACTORS
ACTOR_ANIM_LIMITS_LO
    .ds MAX_ACTORS
ACTOR_ANIM_LIMITS_HI
    .ds MAX_ACTORS
ACTOR_HEIGHT
    .ds MAX_ACTORS
ACTOR_COLOR
    .ds MAX_ACTORS
