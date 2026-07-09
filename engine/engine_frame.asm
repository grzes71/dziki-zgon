;----------------------------------------
; engine/engine_frame.asm
;----------------------------------------

.proc Engine_FrameHandler
    inc $D01A               ; PANIC FLASH: Miganie kolorem tła (COLBK) - sygnalizuje że VBLANK działa
    
    ; 1. Odtwarzacz muzyki/dźwięku
    jsr Audio_Update
    
    ; 2. Sygnał dla pętli głównej
    inc FrameCounter
    
    ; 3. Standardowy powrót z VBLANK w Atari OS (SYSVBV)
    jmp $E45F
.endp

.proc Engine_WaitFrame
    lda FrameCounter
@wait
    cmp FrameCounter
    beq @wait
    rts
.endp
