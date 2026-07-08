;----------------------------------------
; zeropage.asm — Zmienne page zero
;----------------------------------------

SRC_TMP     equ $80         ; tymczasowa do obliczeń (transpozycja sprite'ów)
GAME_STATE  equ $81         ; bieżący stan gry: 0=title, 1=story, 2=game, 3=gameover
SRC_PTR     equ $82         ; wskaźnik źródłowy dla depackera RLE (2 bajty)
DST_PTR     equ $84         ; wskaźnik docelowy dla depackera RLE (2 bajty)

SCREEN_PTR  equ $86         ; wskaźnik na dane obiektów ekranu (2 bajty)
TILE_PTR    equ $88         ; wskaźnik na dane kafelków obiektu (2 bajty)
GAME_SCREEN_ID equ $8A      ; globalny ID aktualnego ekranu (1 bajt)

OBJ_X       equ $8B         ; pozycja x obiektu
OBJ_Y       equ $8C         ; pozycja y obiektu
OBJ_W       equ $8D         ; szerokość obiektu (w kafelkach)
OBJ_H       equ $8E         ; wysokość obiektu (w kafelkach)
OBJ_CODE    equ $8F         ; kod obiektu
TMP_X       equ $90         ; wewnętrzny iterator x pętli rysującej
TMP_Y       equ $91         ; wewnętrzny iterator y pętli rysującej

;--- Engine Variables ---
FrameCounter     equ $92    ; Zwiększany co klatkę przez VBLANK
InputState_Joy   equ $93    ; Zbuforowany stan PORTA (po eor #$FF)
InputState_Trig  equ $94    ; Zbuforowany stan TRIG0
Player_Intent_X  equ $95    ; Intencja ruchu gracza X
Player_Intent_Y  equ $96    ; Intencja ruchu gracza Y
Engine_RequestStageAdvance equ $97 ; Flaga prośby o zmianę sceny (1 = proszę o zmianę)
