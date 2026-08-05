;----------------------------------------
; engine/audio.asm — Generator efektów dźwiękowych (SFX) silnika
;----------------------------------------

step_sfx_phase
    dta 0
item_sfx_phase
    dta 0

.proc Audio_Update
    ; 1. Sprawdź skrzynkę pocztową: podniesienie przedmiotu (wyższy priorytet)
    lda Request_SFX_Item
    beq @chk_step_req
    
    lda #0
    sta Request_SFX_Item
    lda #4
    sta item_sfx_phase
    jmp @process_item

@chk_step_req
    ; 2. Sprawdź skrzynkę pocztową: krok gracza
    lda Request_SFX_Step
    beq @process_item
    
    lda #0
    sta Request_SFX_Step
    ; Jeśli trwa dźwięk podniesienia przedmiotu, ignoruj krok
    lda item_sfx_phase
    bne @process_item
    
    lda #3
    sta step_sfx_phase

@process_item
    ; Priorytet 1: Dźwięk podniesienia przedmiotu
    lda item_sfx_phase
    beq @process_step
    
    dec item_sfx_phase
    ldx item_sfx_phase
    
    lda item_sfx_pitch,x
    sta AUDF1
    lda item_sfx_vol,x
    sta AUDC1
    rts

@process_step
    ; Priorytet 2: Dźwięk kroku
    lda step_sfx_phase
    beq @done
    
    dec step_sfx_phase
    ldx step_sfx_phase
    
    lda step_sfx_pitch,x
    sta AUDF1
    lda step_sfx_vol,x
    sta AUDC1

@done
    rts
.endp

; --- Tabele SFX kroku (3 klatki szumu 4-bit) ---
step_sfx_pitch
    dta $F0, $E0, $D0

step_sfx_vol
    dta $00, $23, $24

; --- Tabele SFX przedmiotu (4 klatki czystego tonu $A0 - wykrzyknik/chime) ---
item_sfx_pitch
    dta $18, $18, $24, $30

item_sfx_vol
    dta $00, $A8, $AA, $AA


