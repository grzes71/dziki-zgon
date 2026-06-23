; Kolory dla: title-0a
; Automatycznie dopasowane do palety Atari (PAL)
;
; Zapis do rejestrów CIENIOWYCH OS (shadow registers).
; VBLANK skopiuje je automatycznie do sprzętowych GTIA.
;
;   COLOR4 ($02C8) → COLBK  ($D01A)
;   COLOR0 ($02C4) → COLPF0 ($D016)
;   COLOR1 ($02C5) → COLPF1 ($D017)
;   COLOR2 ($02C6) → COLPF2 ($D018)
;
;   indeks 0 → COLOR4  $02C8 = $00  (RGB #000000 → hue=0 (szary), lum=0)
;   indeks 1 → COLOR0  $02C4 = $13  (RGB #795801 → hue=1 (złoty), lum=3)
;   indeks 2 → COLOR1  $02C5 = $03  (RGB #5F5F5D → hue=0 (szary), lum=3)
;   indeks 3 → COLOR2  $02C6 = $16  (RGB #A68A58 → hue=1 (złoty), lum=6)

; --- Inicjalizacja kolorów (shadow registers) ---
	lda #$00
	sta $02C8	; COLOR4 → $D01A (tło (COLBK))
	lda #$13
	sta $02C4	; COLOR0 → $D016 (playfield 0 (COLPF0))
	lda #$03
	sta $02C5	; COLOR1 → $D017 (playfield 1 (COLPF1))
	lda #$16
	sta $02C6	; COLOR2 → $D018 (playfield 2 (COLPF2))
