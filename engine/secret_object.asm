;----------------------------------------
; engine/secret_object.asm — Obsługa obiektów typu Secret
;----------------------------------------

secret_grid_x1 dta $00
secret_grid_x2 dta $00
secret_grid_y1 dta $00
secret_grid_y2 dta $00

SECRET_COLLECTED_FLAGS .ds SCREEN_COUNT

;==============================================================
; Secret_Init — resetuje stan zebranych secret obiektów dla nowej gry
;==============================================================
.proc Secret_Init
    ldx #SCREEN_COUNT-1
    lda #0
@loop
    sta SECRET_COLLECTED_FLAGS,x
    dex
    bpl @loop
    rts
.endp

;==============================================================
; Secret_Check_Pickup — sprawdza czy Gerwalt wszedł na obiekt Secret
; Wywoływane co klatkę gry w maszynie stanów engine
;==============================================================
.proc Secret_Check_Pickup
    ldx GAME_SCREEN_ID
    lda SECRET_OBJ_PRESENT,x
    bne @has_secret
    rts

@has_secret
    ; Sprawdź czy secret na tym screenie nie został już zebrany
    lda SECRET_COLLECTED_FLAGS,x
    beq @not_collected_yet
    rts

@not_collected_yet
    ; Oblicz współrzędne siatki Gerwalta (Aktor 0)
    ; G_X1 = (ACTOR_X[0] - 48) / 4
    ; G_X2 = (ACTOR_X[0] - 48 + 7) / 4
    lda ACTOR_X
    sec
    sbc #48
    lsr
    lsr
    sta secret_grid_x1

    lda ACTOR_X
    sec
    sbc #48
    clc
    adc #7
    lsr
    lsr
    sta secret_grid_x2

    ; G_Y1 = (ACTOR_Y[0] - 32) / 16
    ; G_Y2 = (ACTOR_Y[0] - 32 + ACTOR_HEIGHT[0] - 1) / 16
    lda ACTOR_Y
    sec
    sbc #32
    lsr
    lsr
    lsr
    lsr
    sta secret_grid_y1

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
    sta secret_grid_y2

    ; Oblicz granice obiektu Secret (O_X1..O_X2, O_Y1..O_Y2)
    ldx GAME_SCREEN_ID
    
    ; O_X1 <= G_X2
    lda SECRET_OBJ_X,x
    cmp secret_grid_x2
    bcc @check_x2
    beq @check_x2
    rts                         ; O_X1 > G_X2 -> brak nachodzenia

@check_x2
    ; O_X2 >= G_X1  =>  SECRET_OBJ_X + SECRET_OBJ_W - 1 >= G_X1
    lda SECRET_OBJ_X,x
    clc
    adc SECRET_OBJ_W,x
    sec
    sbc #1
    cmp secret_grid_x1
    bcs @check_y1
    rts                         ; O_X2 < G_X1 -> brak nachodzenia

@check_y1
    ; O_Y1 <= G_Y2
    lda SECRET_OBJ_Y,x
    cmp secret_grid_y2
    bcc @check_y2
    beq @check_y2
    rts                         ; O_Y1 > G_Y2 -> brak nachodzenia

@check_y2
    ; O_Y2 >= G_Y1  =>  SECRET_OBJ_Y + SECRET_OBJ_H - 1 >= G_Y1
    lda SECRET_OBJ_Y,x
    clc
    adc SECRET_OBJ_H,x
    sec
    sbc #1
    cmp secret_grid_y1
    bcs @overlap_confirmed
    rts                         ; O_Y2 < G_Y1 -> brak nachodzenia

@overlap_confirmed
    ; Nachodzenie potwierdzone! Spróbuj dodać przedmiot do ekwipunku
    lda SECRET_OBJ_ITEM,x
    beq @done                   ; Jeśli item ID == 0, pomiń
    
    jsr inventory_add_item
    bcs @full                   ; C=1 oznacza brak miejsca w ekwipunku (8/8)

    ; Dodanie udane! Oznacz secret jako zebrany
    ldx GAME_SCREEN_ID
    lda #1
    sta SECRET_COLLECTED_FLAGS,x

    ; Wyczyść kafelki obiektu Secret w VRAM (bez przebudowy ekranu)
    jsr Secret_Clear_VRAM
    jsr draw_inventory

    ; Wyświetl komunikat "znalazłeś ..." na MESSAGE LINE
    ldx GAME_SCREEN_ID
    lda SECRET_OBJ_ITEM,x
    tax
    jsr Secret_Show_Pickup_Msg

@full
@done
    rts
.endp

;==============================================================
; Secret_Clear_VRAM — zeruje kafelki zebranego obiektu Secret w VRAM
; Wejście: X = GAME_SCREEN_ID
; Używa: OBJ_X, OBJ_Y, OBJ_W, OBJ_H, TMP_Y, DST_PTR
;==============================================================
.proc Secret_Clear_VRAM
    lda SECRET_OBJ_X,x
    sta OBJ_X
    lda SECRET_OBJ_Y,x
    sta OBJ_Y
    lda SECRET_OBJ_W,x
    sta OBJ_W
    lda SECRET_OBJ_H,x
    sta OBJ_H

    lda #0
    sta TMP_Y

@row_loop
    ; Oblicz adres VRAM dla wiersza (OBJ_Y + TMP_Y)
    lda OBJ_Y
    clc
    adc TMP_Y
    tay
    lda row_offsets_lo,y
    clc
    adc OBJ_X
    sta DST_PTR
    lda row_offsets_hi,y
    adc #0
    sta DST_PTR+1

    ; Zeruj kolumny w tym wierszu
    lda #0
    ldy OBJ_W
    dey
@col_loop
    sta (DST_PTR),y
    dey
    bpl @col_loop

    inc TMP_Y
    lda TMP_Y
    cmp OBJ_H
    bne @row_loop

    rts
.endp

;==============================================================
; Secret_Show_Pickup_Msg — buduje "znalazłeś <nazwa>" w buforze
; i wyświetla na MESSAGE LINE
; Wejście: X = Item ID
; Używa: SRC_TMP, secret_msg_buf
;==============================================================
.proc Secret_Show_Pickup_Msg
    ; Zapisz wskaźnik na nazwę przedmiotu
    lda ITEM_NAME_LO,x
    sta SRC_TMP
    lda ITEM_NAME_HI,x
    sta SRC_TMP+1

    ; Kopiuj prefix "znalazłeś " do bufora
    ldx #0
@copy_prefix
    lda secret_msg_prefix,x
    sta secret_msg_buf,x
    inx
    cpx #SECRET_MSG_PREFIX_LEN
    bne @copy_prefix
    ; X = SECRET_MSG_PREFIX_LEN (offset do dopisywania)

    ; Kopiuj nazwę przedmiotu za prefixem
    ldy #0
@copy_name
    lda (SRC_TMP),y
    beq @name_done
    sta secret_msg_buf,x
    inx
    iny
    cpx #36             ; max rozmiar bufora
    bcc @copy_name

@name_done
    ; Zakończ null
    lda #0
    sta secret_msg_buf,x

    ; Wyświetl komunikat
    lda #<secret_msg_buf
    ldy #>secret_msg_buf
    jsr msg_show
    rts
.endp

; Prefix "znalazłeś " zakodowany jako UTF-8
secret_msg_prefix
    dta 122, 110, 97, 108, 97, 122, 197, 130, 101, 197, 155, 32
SECRET_MSG_PREFIX_LEN = * - secret_msg_prefix

; Bufor roboczy na sklejony komunikat (RAM)
secret_msg_buf = $5F50
