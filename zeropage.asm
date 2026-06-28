;----------------------------------------
; zeropage.asm — Zmienne page zero
;----------------------------------------

SRC_TMP     equ $80         ; tymczasowa do obliczeń (transpozycja sprite'ów)
GAME_STATE  equ $81         ; bieżący stan gry: 0=title, 1=story, 2=game, 3=gameover
SRC_PTR     equ $82         ; wskaźnik źródłowy dla depackera RLE (2 bajty)
DST_PTR     equ $84         ; wskaźnik docelowy dla depackera RLE (2 bajty)
