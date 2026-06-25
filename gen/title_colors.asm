; Kolory dla: title
; Automatycznie dopasowane do palety Atari (PAL)
;
; Zapis BEZPOŚREDNIO do rejestrów GTIA (VBI wyłączony).
;
;   COLBK  ($D01A)
;   COLPF0 ($D016)
;   COLPF1 ($D017)
;   COLPF2 ($D018)
;
;   indeks 0 → COLBK  $D01A = $00  (RGB #070604 → hue=0 (szary), lum=0)
;   indeks 1 → COLPF0 $D016 = $03  (RGB #5C533C → hue=0 (szary), lum=3)
;   indeks 2 → COLPF1 $D017 = $14  (RGB #87660C → hue=1 (złoty), lum=4)
;   indeks 3 → COLPF2 $D018 = $08  (RGB #A4A095 → hue=0 (szary), lum=8)

; --- Stałe kolorów (MADS .equ) — do użycia w DLI ---
TITLE_COLBK	= $00
TITLE_COLPF0	= $03
TITLE_COLPF1	= $14
TITLE_COLPF2	= $08

; --- Inicjalizacja kolorów (GTIA hardware registers) ---
	lda #$00
	sta $D01A	; COLBK (tło)
	lda #$03
	sta $D016	; COLPF0 (playfield 0)
	lda #$14
	sta $D017	; COLPF1 (playfield 1)
	lda #$08
	sta $D018	; COLPF2 (playfield 2)
