;----------------------------------------
; engine/collision.asm
;----------------------------------------

.proc Collision_Update
    ldx #0
@actor_loop
    lda ACTOR_ACTIVE,x
    beq @next_actor

    ; Copy current actor's intent and height to ZP temp variables
    lda ACTOR_INTENT_X,x
    sta ACTOR_TMP_X
    lda ACTOR_INTENT_Y,x
    sta ACTOR_TMP_Y
    lda ACTOR_HEIGHT,x
    sta ACTOR_TMP_HEIGHT

    ; Limity dla osi X (48 - 200)
    lda ACTOR_TMP_X
    cmp #48
    bcs @check_right
    lda #48
    sta ACTOR_TMP_X
    jmp @check_y

@check_right
    cmp #200
    bcc @check_y
    lda #200
    sta ACTOR_TMP_X

@check_y
    ; Limity dla osi Y (32 - 178) 
    lda ACTOR_TMP_Y
    cmp #32
    bcs @check_bot
    lda #32
    sta ACTOR_TMP_Y
    jmp @screen_ok

@check_bot
    cmp #178
    bcc @screen_ok
    lda #178
    sta ACTOR_TMP_Y

@screen_ok
    ; Save actor index on stack before calling world collision
    txa
    pha

    ; Weryfikacja kolizji z obiektami świata
    jsr Check_Objects_Collision
    cmp #1
    beq @reject

    ; Pop actor index
    pla
    tax

@apply
    ; Aplikujemy zweryfikowaną intencję do rzeczywistej pozycji aktora
    lda ACTOR_TMP_X
    sta ACTOR_X,x
    lda ACTOR_TMP_Y
    sta ACTOR_Y,x
    jmp @next_actor
    
@reject
    pla
    tax
    
@next_actor
    inx
    cpx #MAX_ACTORS
    bne @actor_loop
    rts
.endp

.proc Check_Objects_Collision
    ; Wyliczamy przeciwległy róg aktora (ActorX2, ActorY2)
    lda ACTOR_TMP_X
    clc
    adc #7          ; Szerokość sprite'a PMG to zawsze 8 px w trybie pojedynczym
    sta col_px2
    
    lda ACTOR_TMP_Y
    clc
    adc ACTOR_TMP_HEIGHT
    sec
    sbc #1
    sta col_py2

    ; Przygotuj wskaźnik na dane obiektów aktualnego ekranu
    ldx GAME_SCREEN_ID
    lda SCREEN_POINTERS_LO,x
    sta SCREEN_PTR
    lda SCREEN_POINTERS_HI,x
    sta SCREEN_PTR+1

    ldy #0
    lda (SCREEN_PTR),y          ; Liczba obiektów na ekranie
    bne @start_objects
    jmp @no_col
@start_objects
    tax                         ; X = licznik obiektów do przetworzenia

@object_loop
    ; Czytaj OBJ_CODE
    inc SCREEN_PTR
    bne @read_code
    inc SCREEN_PTR+1
@read_code
    ldy #0
    lda (SCREEN_PTR),y
    sta OBJ_CODE
    
    ; Czytaj OBJ_X
    inc SCREEN_PTR
    bne @read_x
    inc SCREEN_PTR+1
@read_x
    lda (SCREEN_PTR),y
    sta OBJ_X

    ; Czytaj OBJ_Y
    inc SCREEN_PTR
    bne @read_y
    inc SCREEN_PTR+1
@read_y
    lda (SCREEN_PTR),y
    sta OBJ_Y

    ; Zapisz licznik (X) na stosie, bo zaraz będziemy go używać do odczytu danych obiektu
    txa
    pha

    ; Czy obiekt jest blokujący?
    ldx OBJ_CODE
    lda OBJ_FLAGS,x
    and #$80        ; Maska flagi blocking (Bit 7)
    beq @next_obj   ; Brak flagi -> obiekt przenikalny

    ; Oblicz O_X1 = 48 + OBJ_X * 4
    lda OBJ_X
    asl
    asl
    clc
    adc #48
    sta col_ox1
    
    ; Oblicz O_Y1 = 32 + OBJ_Y * 16
    lda OBJ_Y
    asl
    asl
    asl
    asl
    clc
    adc #32
    sta col_oy1
    
    ; Wypakuj z OBJ_SIZE i oblicz O_X2 (O_X1 + Szerokość * 4 - 1)
    lda OBJ_SIZE,x
    pha
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1          ; W (w kafelkach)
    asl
    asl             ; W * 4 (w pikselach PMG)
    sec
    sbc #1
    clc
    adc col_ox1
    sta col_ox2
    
    ; Wypakuj z OBJ_SIZE i oblicz O_Y2 (O_Y1 + Wysokość * 16 - 1)
    pla
    and #$0F
    clc
    adc #1          ; H (w kafelkach)
    asl
    asl
    asl
    asl             ; H * 16 (w pikselach)
    sec
    sbc #1
    clc
    adc col_oy1
    sta col_oy2
    
    ; --- TEST KOLIZJI (AABB) ---
    
    ; 1. P_X1 > O_X2 -> brak kolizji
    lda ACTOR_TMP_X
    cmp col_ox2
    beq @chk2       ; Jeśli równe, krawędzie się stykają (zatem kolizja)
    bcs @next_obj   ; Jeśli > (Z=0, C=1), brak kolizji

@chk2
    ; 2. P_X2 < O_X1 -> brak kolizji
    lda col_px2
    cmp col_ox1
    bcc @next_obj   ; Jeśli < (C=0), brak kolizji
    
    ; 3. P_Y1 > O_Y2 -> brak kolizji
    lda ACTOR_TMP_Y
    cmp col_oy2
    beq @chk4       ; Jeśli równe, kolizja
    bcs @next_obj

@chk4
    ; 4. P_Y2 < O_Y1 -> brak kolizji
    lda col_py2
    cmp col_oy1
    bcc @next_obj

    ; Jeśli żaden z powyższych warunków separacji nie zaszedł, MAMY KOLIZJĘ!
    pla             ; Zdejmij zapisany licznik ze stosu
    lda #1          ; Zwróć 1 (wykryto kolizję)
    rts

@next_obj
    pla
    tax             ; Przywróć licznik obiektów
    dex
    beq @no_col
    jmp @object_loop

@no_col
    lda #0          ; Zwróć 0 (brak kolizji)
    rts

; Zmienne lokalne do obliczeń (aby nie zaśmiecać i tak zapchanego Zero Page)
col_px2 dta $00
col_py2 dta $00
col_ox1 dta $00
col_oy1 dta $00
col_ox2 dta $00
col_oy2 dta $00

.endp
