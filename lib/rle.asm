; =============================================================================
; Depacker RLE (run-length encoding) dla 6502
;
; Format RLE:
;   Bajt flagi (cmd):
;     bit 7 = 1 -> powtórzenie: bity 6..0 = liczba powtórzeń - 1 (1..128)
;                  Wyjątek: cmd = $80 -> EOF (koniec danych)
;     bit 7 = 0 -> literały:    bity 6..0 = długość - 1 (1..128)
;
; Wejście:
;   SRC_PTR (word) – adres skompresowanych danych (Strona Zerowa)
;   DST_PTR (word) – adres bufora docelowego (Strona Zerowa)
;
; Niszczy: A, X, Y
; =============================================================================

.proc RLE_Depack
        ldy #0

loop
        ; --- Odczytaj bajt flagi ---
        lda (SRC_PTR),Y
        tax                 ; zachowaj bajt flagi w X
        inc SRC_PTR
        bne skip_inc_src
        inc SRC_PTR+1
skip_inc_src
        txa                 ; przywróć bajt flagi do A (odnawia flagi N i Z!)
        bmi do_repeat       ; bit 7 = 1 -> powtórzenie lub EOF

        ; --- Literały (bit 7 = 0) ---
        tax                 ; X = liczba literałów - 1
        inx                 ; X = liczba literałów (1..128)
        ldy #0
@lit_copy
        lda (SRC_PTR),Y
        sta (DST_PTR),Y
        inc SRC_PTR
        bne @lit_skip_src
        inc SRC_PTR+1
@lit_skip_src
        inc DST_PTR
        bne @lit_skip_dst
        inc DST_PTR+1
@lit_skip_dst
        dex
        bne @lit_copy
        beq loop            ; zawsze powrót do głównej pętli

        ; --- Powtórzenie (bit 7 = 1) ---
do_repeat
        and #$7F            ; bity 6..0 = liczba powtórzeń - 1
        beq exit_rle        ; jeśli bity 6..0 == 0 (czyli pierwotnie cmd = $80), to EOF!
        tax
        inx                 ; X = liczba powtórzeń (1..128)
        ldy #0
        lda (SRC_PTR),Y      ; wczytaj bajt do powtórzenia
        inc SRC_PTR
        bne @rep_skip_src
        inc SRC_PTR+1
@rep_skip_src
        ldy #0
@rep_store
        sta (DST_PTR),Y
        inc DST_PTR
        bne @rep_skip_dst
        inc DST_PTR+1
@rep_skip_dst
        dex
        bne @rep_store
        beq loop            ; powrót do głównej pętli

exit_rle
        rts
.endp
