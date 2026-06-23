; Kolory dla: title-0a
; Automatycznie dopasowane do palety Atari (PAL)
;
; Zapis BEZPOŚREDNIO do rejestrów GTIA (VBI wyłączony).
;
;   COLBK  ($D01A)
;   COLPF0 ($D016)
;   COLPF1 ($D017)
;   COLPF2 ($D018)
;
;   indeks 0 → COLBK  $D01A = $00  (RGB #000000 → hue=0 (szary), lum=0)
;   indeks 1 → COLPF0 $D016 = $13  (RGB #795801 → hue=1 (złoty), lum=3)
;   indeks 2 → COLPF1 $D017 = $03  (RGB #5F5F5D → hue=0 (szary), lum=3)
;   indeks 3 → COLPF2 $D018 = $16  (RGB #A68A58 → hue=1 (złoty), lum=6)

; --- Inicjalizacja kolorów (GTIA hardware registers) ---
	lda #$00
	sta $D01A	; COLBK (tło)
	lda #$13
	sta $D016	; COLPF0 (playfield 0)
	lda #$03
	sta $D017	; COLPF1 (playfield 1)
	lda #$16
	sta $D018	; COLPF2 (playfield 2)
