;----------------------------------------
; engine/inventory.asm — System Ekwipunku (Inventory)
;----------------------------------------

MAX_INVENTORY_ITEMS    = 8
INVENTORY_EMPTY_CHAR   = 14  ; Kod Atari 14 dla kropki '.'
INVENTORY_OPEN_BRACKET  = 59  ; Kod Atari 59 dla '['
INVENTORY_CLOSE_BRACKET = 61  ; Kod Atari 61 dla ']'

ITEM_SZNUREK_ID       = 4   ; ID dla Sznurka (id: 4)

inventory_count
    dta 0
inventory_items
    dta 0, 0, 0, 0, 0, 0, 0, 0

;==============================================================
; inventory_init — inicjalizuje pusty ekwipunek (8 pustych miejsc)
;==============================================================
.proc inventory_init
    lda #0
    sta inventory_count
    ldx #0
@loop
    sta inventory_items,x
    inx
    cpx #MAX_INVENTORY_ITEMS
    bne @loop
    rts
.endp

;==============================================================
; draw_inventory — rysuje ekwipunek na Info Line (indeksy 22..32)
; Format: [........] (kod 59, 8 slotów, kod 61, spacja na 32)
;==============================================================
.proc draw_inventory
    ; Otwarty nawias kwadratowy '[' (indeks 22)
    lda #INVENTORY_OPEN_BRACKET
    sta GAME_SCREEN_A2 + 22

    ; 8 slotów ekwipunku (indeksy 23..30)
    ldx #0
@loop
    cpx inventory_count
    bcs @empty
    ldy inventory_items,x
    lda ITEM_CHARSET_POS,y
    jmp @store
@empty
    lda #INVENTORY_EMPTY_CHAR
@store
    sta GAME_SCREEN_A2 + 23,x
    inx
    cpx #MAX_INVENTORY_ITEMS
    bne @loop

    ; Zamknięty nawias kwadratowy ']' (indeks 31)
    lda #INVENTORY_CLOSE_BRACKET
    sta GAME_SCREEN_A2 + 31

    ; Spacja odstępu przed czasem gry (indeks 32)
    lda #0
    sta GAME_SCREEN_A2 + 32

    rts
.endp

;==============================================================
; inventory_add_item — dodaje przedmiot do ekwipunku
; Wejście: A = ID przedmiotu
; Wyjście: C=0 (sukces), C=1 (ekwipunek pełny)
;==============================================================
.proc inventory_add_item
    ldx inventory_count
    cpx #MAX_INVENTORY_ITEMS
    bcs @full

    sta inventory_items,x
    inc inventory_count
    jsr draw_inventory

    ; Zgłoszenie żądania odtworzenia dźwięku podniesienia przedmiotu (Mailbox pattern)
    lda #1
    sta Request_SFX_Item

    clc
    rts
@full
    sec
    rts
.endp

;==============================================================
; inventory_has_item — sprawdza obecność przedmiotu w ekwipunku
; Wejście: A = ID przedmiotu
; Wyjście: C=0 (znaleziono, X=indeks slotu), C=1 (brak)
;==============================================================
.proc inventory_has_item
    ldx #0
@loop
    cpx inventory_count
    bcs @not_found
    cmp inventory_items,x
    beq @found
    inx
    jmp @loop
@found
    clc
    rts
@not_found
    sec
    rts
.endp

;==============================================================
; inventory_remove_item — usuwa przedmiot z ekwipunku
; Wejście: A = ID przedmiotu
; Wyjście: C=0 (usunięto), C=1 (nie było w ekwipunku)
;==============================================================
.proc inventory_remove_item
    jsr inventory_has_item
    bcs @done

@shift
    inx
    cpx inventory_count
    bcs @shifted
    lda inventory_items,x
    sta inventory_items - 1,x
    jmp @shift

@shifted
    dec inventory_count
    ldx inventory_count
    lda #0
    sta inventory_items,x

    jsr draw_inventory
    clc
@done
    rts
.endp

.proc Inventory_Update
    rts
.endp

