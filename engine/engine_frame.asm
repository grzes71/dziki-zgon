;----------------------------------------
; engine/engine_frame.asm
;----------------------------------------

.proc Engine_FrameHandler
    inc $D01A               ; PANIC FLASH: Miganie COLBK

    ; 1. Odtwarzacz muzyki/dźwięku
    jsr Audio_Update

    ; 2. Sygnał dla pętli głównej
    inc FrameCounter

    ; 3. Ręczne kopiowanie rejestrów-cieni do sprzętu
    lda SDLSTL
    sta DLISTL
    lda SDLSTH
    sta DLISTH
    lda SDMCTL
    sta DMACTL
    lda CHBAS
    sta CHBASE
    lda $02C0
    sta PCOLR0
    lda $02C1
    sta PCOLR1
    lda $02C2
    sta PCOLR2
    lda $02C3
    sta PCOLR3
    lda COLOR0
    sta COLPF0
    lda COLOR1
    sta COLPF1
    lda COLOR2
    sta COLPF2
    lda COLOR3
    sta COLPF3
    lda COLOR4
    sta COLBK

    ; 4. Przejście do odłożonego VBLANK (klawiatura, timery) pomijając SYSVBV
    jmp (VVBLKI)
.endp

.proc Engine_WaitFrame
    lda FrameCounter
@wait
    cmp FrameCounter
    beq @wait
    rts
.endp
