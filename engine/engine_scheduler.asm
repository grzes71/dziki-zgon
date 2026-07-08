;----------------------------------------
; engine/engine_scheduler.asm
;----------------------------------------

.proc EngineScheduler
    jsr Engine_BeginFrame
    jsr Input_Update
    jsr Player_Update
    jsr NPC_Update
    jsr Collision_Update
    jsr Inventory_Update
    jsr Dialogue_Update
    jsr Quest_Update
    jsr Animation_Update
    jsr World_Update
    jsr Render_Prepare
    jsr Engine_EndFrame
    rts
.endp

.proc Engine_BeginFrame
    rts
.endp

.proc Engine_EndFrame
    rts
.endp
