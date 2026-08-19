;----------------------------------------
; lib/text_headers.asm — Procedury wyświetlania ikon i nagłówka tekstowego
;----------------------------------------

    icl "gen/header-story_text.asm"
    icl "gen/header-gameover-fail_text.asm"
    icl "gen/header-gameover-success_text.asm"

; --- Tabele Ikon (12 bajtów na zestaw: 6 B lewa, 6 B prawa) ---

story_icons
    .byte 76, 3, 88, 0, 4, 2      ; Lewa ikona (L1, L2, L3)
    .byte 5, 6, 0, 89, 9, 7       ; Prawa ikona (L1, L2, L3)

travel_icons
    .byte 10, 71, 81, 82, 11, 77  ; Lewa ikona (L1, L2, L3)
    .byte 10, 71, 81, 82, 11, 77  ; Prawa ikona (L1, L2, L3)

gameover_fail_icons
    .byte 87, 65, 85, 86, 96, 66  ; Lewa ikona (L1, L2, L3)
    .byte 87, 65, 85, 86, 96, 66  ; Prawa ikona (L1, L2, L3)

gameover_success_icons
    .byte 69, 69, 84, 84, 68, 70  ; Lewa ikona (L1, L2, L3)
    .byte 69, 69, 84, 84, 68, 70  ; Prawa ikona (L1, L2, L3)

; --- Procedury ---

.proc init_icon_header
    ; 1. Wyczyść 120 bajtów bufora ICON_ADDR
    ldx #120-1
    lda #0
@clr
    sta ICON_ADDR,x
    dex
    bpl @clr

    ; 2. Kopiuj Lewą Ikonę (kolumny 0, 1)
    ; Linia 1
    ldy #0
    lda (SRC_PTR),y
    sta ICON_ADDR
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+1
    
    ; Linia 2
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+40
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+41
    
    ; Linia 3
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+80
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+81

    ; 3. Kopiuj Prawą Ikonę (kolumny 38, 39)
    ; Linia 1
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+38
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+39
    
    ; Linia 2
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+40+38
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+40+39
    
    ; Linia 3
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+80+38
    iny
    lda (SRC_PTR),y
    sta ICON_ADDR+80+39
    rts
.endp

.proc show_story_header
    lda #<story_icons
    sta SRC_PTR
    lda #>story_icons
    sta SRC_PTR+1
    jsr init_icon_header
    mRLE_Depack text_header_story (ICON_ADDR+42)
    rts
.endp

.proc show_travel_header
    lda #<travel_icons
    sta SRC_PTR
    lda #>travel_icons
    sta SRC_PTR+1
    jsr init_icon_header

    ; Pobierz ID docelowego regionu dla NEW_SCREEN_ID
    ldx NEW_SCREEN_ID
    lda SCREEN_REGION,x
    tax                     ; X = RegionId

    ; Pobierz wskaźnik do 20-bajtowej nazwy regionu
    lda REGION_NAMES_LO,x
    sta SRC_PTR
    lda REGION_NAMES_HI,x
    sta SRC_PTR+1

    ; Kopiuj 20 znaków nazwy regionu na środek 2. linii (ICON_ADDR + 50)
    ldy #19
@copy_name
    lda (SRC_PTR),y
    sta ICON_ADDR + 50,y
    dey
    bpl @copy_name
    rts
.endp

.proc show_gameover_fail_header
    lda #<gameover_fail_icons
    sta SRC_PTR
    lda #>gameover_fail_icons
    sta SRC_PTR+1
    jsr init_icon_header
    mRLE_Depack text_header_gameover_fail (ICON_ADDR+42)
    rts
.endp

.proc show_gameover_success_header
    lda #<gameover_success_icons
    sta SRC_PTR
    lda #>gameover_success_icons
    sta SRC_PTR+1
    jsr init_icon_header
    mRLE_Depack text_header_gameover_success (ICON_ADDR+42)
    rts
.endp
