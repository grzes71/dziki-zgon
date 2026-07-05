;----------------------------------------
; lib/pmg.asm — Procedury pomocnicze PMG
;----------------------------------------

;--------------------------------------------------------------
; pmg_clear_all — Zeruje całą pamięć PMG (wszystkie 5 buforów)
; Zakres: 0..239 (120 linii × 2 dla double-line, ale
;          single-line w tym projekcie używa pełnych 128 B)
; Niszczy: A, X
;--------------------------------------------------------------
.proc pmg_clear_all
    lda #0
    tax
@lp
    sta PLAYER0,x
    sta PLAYER1,x
    sta PLAYER2,x
    sta PLAYER3,x
    sta MISSILES,x
    inx
    bne @lp
    rts
.endp

;--------------------------------------------------------------
; pmg_clear_range — Zeruje zakres linii PMG
; Wejście:  X = indeks ostatniej linii do wyzerowania (odliczanie do 0)
; Niszczy:  A, X
;--------------------------------------------------------------
.proc pmg_clear_range
    lda #0
@lp
    sta PLAYER0,x
    sta PLAYER1,x
    sta PLAYER2,x
    sta PLAYER3,x
    sta MISSILES,x
    dex
    bpl @lp
    rts
.endp
