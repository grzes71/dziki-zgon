;----------------------------------------
; engine/collision.asm
;----------------------------------------

.proc Collision_Update
    ; Rozwiązywanie kolizji dla gracza
    ; Aktualnie brak kolizji ze światem, aplikujemy intencję
    
    lda Player_Intent_X
    sta hero_x
    lda Player_Intent_Y
    sta hero_y
    
    rts
.endp
