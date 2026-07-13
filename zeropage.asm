;----------------------------------------
; zeropage.asm — Zmienne page zero
;----------------------------------------

SRC_TMP     equ $80         ; wskaźnik tymczasowy (2 bajty, $80-$81)
GAME_STATE  equ $9B         ; bieżący stan gry: 0=title, 1=story, 2=game, 3=gameover
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
Engine_RequestStageAdvance equ $95 ; Flaga prośby o zmianę sceny (1 = proszę o zmianę)

;--- Actor System Zero Page Variables ---
PMG_PTR             equ $96 ; (2 bajty) Wskaźnik do pamięci PMG aktualnie renderowanego aktora
ACTOR_TMP_X         equ $98 ; Tymczasowa intencja X aktora (do kolizji)
ACTOR_TMP_Y         equ $99 ; Tymczasowa intencja Y aktora (do kolizji)
ACTOR_TMP_HEIGHT    equ $9A ; Tymczasowa wysokość aktora (do kolizji)

;--- Screen Transition Variables ---
REQ_SCREEN_TRANSITION equ $9C ; Flaga żądania zmiany ekranu (1 = tak)
NEW_SCREEN_ID         equ $9D ; ID nowego ekranu do wczytania
NEW_ACTOR_X           equ $9E ; Nowa pozycja gracza na nowym ekranie
NEW_ACTOR_Y           equ $9F ; Nowa pozycja gracza na nowym ekranie
ENEMY_COUNT_TMP       equ $A0 ; Tymczasowa liczba przeciwników na ekranie
CURRENT_ACTOR         equ $A1 ; Indeks aktualnie ładowanego aktora (1..3)
