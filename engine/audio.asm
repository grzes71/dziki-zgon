;----------------------------------------
; engine/audio.asm — Generator efektów dźwiękowych (SFX) silnika
;----------------------------------------

step_sfx_phase
    dta 0
item_sfx_phase
    dta 0
interact_sfx_phase
    dta 0

.proc Audio_Update
    ; 1. Sprawdź skrzynkę pocztową: podniesienie przedmiotu (Priorytet 1)
    lda Request_SFX_Item
    beq @chk_interact_req
    
    lda #0
    sta Request_SFX_Item
    lda #4
    sta item_sfx_phase
    jmp @process_item

@chk_interact_req
    ; 2. Sprawdź skrzynkę pocztową: interakcja z obiektem (Priorytet 2)
    lda Request_SFX_Interact
    beq @chk_step_req

    lda #0
    sta Request_SFX_Interact
    lda #4
    sta interact_sfx_phase
    jmp @process_item

@chk_step_req
    ; 3. Sprawdź skrzynkę pocztową: krok gracza (Priorytet 3)
    lda Request_SFX_Step
    beq @process_item
    
    lda #0
    sta Request_SFX_Step
    ; Jeśli trwa dźwięk przedmiotu lub interakcji, ignoruj krok
    lda item_sfx_phase
    ora interact_sfx_phase
    bne @process_item
    
    lda #3
    sta step_sfx_phase

@process_item
    ; Priorytet 1: Dźwięk podniesienia przedmiotu
    lda item_sfx_phase
    beq @process_interact
    
    dec item_sfx_phase
    ldx item_sfx_phase
    
    lda item_sfx_pitch,x
    sta AUDF1
    lda item_sfx_vol,x
    sta AUDC1
    rts

@process_interact
    ; Priorytet 2: Dźwięk interakcji z obiektem
    lda interact_sfx_phase
    beq @process_step

    dec interact_sfx_phase
    ldx interact_sfx_phase

    lda interact_sfx_pitch,x
    sta AUDF1
    lda interact_sfx_vol,x
    sta AUDC1
    rts

@process_step
    ; Priorytet 3: Dźwięk kroku
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

; --- Tabele SFX interakcji z obiektem (4 klatki tonu $C0 - klik/blip) ---
interact_sfx_pitch
    dta $1C, $1C, $28, $40

interact_sfx_vol
    dta $00, $C6, $CA, $CC



