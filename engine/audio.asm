;----------------------------------------
; engine/audio.asm — Generator efektów dźwiękowych (SFX) silnika
;----------------------------------------

step_sfx_phase
    dta 0

.proc Audio_Update
    ; 1. Obsługa skrzynki pocztowej: żądanie odtworzenia dźwięku kroku
    lda Request_SFX_Step
    beq @chk_active
    
    ; Wyczyść flagę skrzynki pocztowej
    lda #0
    sta Request_SFX_Step
    
    ; Rozpocznij odtwarzanie kroku (3 klatki czasu trwania)
    lda #3
    sta step_sfx_phase

@chk_active
    lda step_sfx_phase
    beq @done
    
    dec step_sfx_phase
    ldx step_sfx_phase
    
    ; Ustaw POKEY kanał 1: barwa (distortion) $20 (szum 4-bitowy) + głośność
    lda step_sfx_pitch,x
    sta AUDF1
    lda step_sfx_vol,x
    sta AUDC1

@done
    rts
.endp

; Tabele obniżania barwy i głośności dla dźwięku kroku (3 klatki opadającego stuku)
; Index 2: klatka 1 (częstotliwość $D0, głośność $24 = szum 4-bit, vol 4)
; Index 1: klatka 2 (częstotliwość $E0, głośność $23 = szum 4-bit, vol 3)
; Index 0: klatka 3 (częstotliwość $F0, głośność $00 = cisza)
step_sfx_pitch
    dta $F0, $E0, $D0

step_sfx_vol
    dta $00, $23, $24

