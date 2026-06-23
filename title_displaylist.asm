; ANTIC Display List dla: title
; Tryb ANTIC:   $0E  (160×192, 4 kolory)
; Bajtów/linia: 40
; Adres ekranu: $4000
; Segmentów:    2  (linii łącznie: 192)
; Danych (z paddingiem): 7696 bajtów

DLIST
	; 24 puste linie (górna ramka)
	dta $70, $70, $70

	; --- Segment 1: LMS = $4000
	;     linie 0..101 (102 linii, offset danych 0) ---
	dta $4E, a(TitleData + 0)
	.rept 101
	dta $0E
	.endr
	; --- Segment 2: LMS = $5000
	;     linie 102..191 (90 linii, offset danych 4096) ---
	dta $4E, a(TitleData + 4096)
	.rept 89
	dta $0E
	.endr

	; Koniec Display List
	dta $41, a(DLIST)	; JVB – skok z oczekiwaniem na VBLANK
