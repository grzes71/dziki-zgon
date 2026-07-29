;----------------------------------------
; scenes/gameover/gameover.asm — Ekran końca gry
; ANTIC 4 (40×23 znaków) + tekst GAME OVER (ANTIC 2)
;----------------------------------------

; --- Palette Equates (rezerwowane komórki palety) ---
GO_COLBK  = $00     ; Tło (indeks 0: #000000 -> czarny)
GO_COLPF0 = $F2     ; Kolor PF0 (indeks 1: #8F6B29 -> ciemny brąz/złoto)
GO_COLPF1 = $F4     ; Kolor PF1 (indeks 2: #C3985D -> jasny brąz/pomarańcz)
GO_COLPF2 = $0F     ; Kolor PF2 (indeks 3: #FFFFFF -> biały)
GO_COLPF3 = $00     ; Kolor PF3 (nieużywany / zarezerwowany)


;---- Zmienne lokalne sceny ----
gameover_fire_released
    dta $00
go_dli_state
    dta $00

;==============================================================
; DLI_Gameover — 2-etapowa obsługa DLI:
; DLI #1 (góra): ustawia charset obrazka ($9000 -> CHBASE=$90)
; DLI #2 (dół): ustawia czcionkę systemową ($6000 -> CHBASE=$60)
;==============================================================
.proc DLI_Gameover
    pha
    lda go_dli_state
    bne @bottom_text

@top_image
    lda #$90            ; DLI #1 (góra): wygenerowany charset Game Over ($9000)
    sta CHBASE

    ; --- Kolory obrazka (wpis bezpośrednio do rejestrów sprzętowych GTIA) ---
    lda #GO_COLBK
    sta COLBK
    lda #GO_COLPF0
    sta COLPF0
    lda #GO_COLPF1
    sta COLPF1
    lda #GO_COLPF2
    sta COLPF2
    lda #GO_COLPF3
    sta COLPF3

    inc go_dli_state
    pla
    rti

@bottom_text
    lda #$60            ; DLI #2 (dół): czcionka systemowa ($6000) dla dolnej linii tekstu
    sta CHBASE
    lda #$0F            ; kolor tekstu (biały dla ANTIC 2)
    sta COLPF1
    lda #$00            ; tło (czarne)
    sta COLBK
    lda #0
    sta go_dli_state
    pla
    rti
.endp


.proc gameover_init
    lda #0
    sta DMACTL
    sta NMIEN
    sta GRACTL              ; wyłącz PMG DMA (GTIA)
    sta GPRIOR              ; reset priorytetów
    sta gameover_fire_released ; zresetuj stan przycisku FIRE
    sta go_dli_state        ; zresetuj stan 2-etapowego DLI


    ; --- Kopiuj właściwy bufor ekranu (920 B) do VRAM_ARENA ($4000) ---
    lda GAME_RESULT_STATUS
    cmp #1                  ; 1 = Sukces
    beq @do_success

@do_fail
    ldx #0
@loop_fail
    lda GameOverFail_Data,x
    sta VRAM_ARENA,x
    lda GameOverFail_Data+$100,x
    sta VRAM_ARENA+$100,x
    lda GameOverFail_Data+$200,x
    sta VRAM_ARENA+$200,x
    lda GameOverFail_Data+$298,x
    sta VRAM_ARENA+$298,x
    inx
    bne @loop_fail
    jmp @screen_done

@do_success
    ldx #0
@loop_succ
    lda GameOverSuccess_Data,x
    sta VRAM_ARENA,x
    lda GameOverSuccess_Data+$100,x
    sta VRAM_ARENA+$100,x
    lda GameOverSuccess_Data+$200,x
    sta VRAM_ARENA+$200,x
    lda GameOverSuccess_Data+$298,x
    sta VRAM_ARENA+$298,x
    inx
    bne @loop_succ

@screen_done
    jsr pmg_clear_all
    jsr copy_gameover_text

    ; --- Display List (ANTIC 4 + tekst ANTIC 2) ---
    lda #<DLIST_GAMEOVER
    sta SDLSTL
    sta DLISTL
    lda #>DLIST_GAMEOVER
    sta SDLSTH
    sta DLISTH

    ; --- Charset Game Over ($9000 -> CHBAS = $90) ---
    lda #$90
    sta CHBAS
    sta CHBASE

    ; --- Kolory palety Game Over ---
    lda #GO_COLBK
    sta COLOR4
    sta COLBK
    lda #GO_COLPF0
    sta COLOR0
    sta COLPF0
    lda #GO_COLPF1
    sta COLOR1
    sta COLPF1
    lda #GO_COLPF2
    sta COLOR2
    sta COLPF2
    lda #GO_COLPF3
    sta COLOR3
    sta COLPF3

    ; --- DLI: wektor + enable ---
    lda #<DLI_Gameover
    sta VDSLST
    lda #>DLI_Gameover
    sta VDSLST+1
    lda #$C0              ; DLI on, VBI on (music required)
    sta NMIEN

    ; --- DMA ON (normal playfield — 40 znaków, bez PMG) ---
    lda #$22
    sta SDMCTL
    sta DMACTL

    jsr title_audio_init
    rts
.endp


.proc gameover_run
    lda gameover_fire_released
    bne @check_press

    ; Czekaj na puszczenie przycisku FIRE z poprzedniego ekranu
    lda TRIG0
    beq @exit            ; wciąż trzyma — nie reaguj
    lda #1
    sta gameover_fire_released
    jmp @exit

@check_press
    lda TRIG0
    bne @exit
    lda #0
    sta NMIEN              ; wyłącz DLI przed zmianą stanu
    jsr advance_stage      ; powrót do pierwszego etapu z tablicy
@exit
    rts
.endp

;==============================================================
; copy_gameover_text — Kopiuje tekst GAME OVER z ROM do RAM ($5E10)
;==============================================================
.proc copy_gameover_text
    mRLE_Depack GO_TEXT_Data FOOTER_ADDR
    rts
.endp
