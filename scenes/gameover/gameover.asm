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
go_timer_frames
    dta $00
go_current_line
    dta $00
go_text_max_lines
    dta $00

; Adresy początkowe linii tekstu w buforze FOOTER_ADDR ($5E10..$5F4F)
GoLineAddrLo
    dta <$5E10, <$5E38, <$5E60, <$5E88, <$5EB0, <$5ED8, <$5F00, <$5F28
GoLineAddrHi
    dta >$5E10, >$5E38, >$5E60, >$5E88, >$5EB0, >$5ED8, >$5F00, >$5F28

;==============================================================
; gameover_vbi — Obsługa Immediate VBI dla ekranu Game Over
; - Odtwarza muzykę RMT
; - Liczy klatki i co 5 sekund (250 klatek przy 50 Hz) cyklicznie przełącza linię tekstu
;==============================================================
.proc gameover_vbi
    jsr RASTERMUSICTRACKER+3 ; Odtwórz 1 klatkę muzyki RMT

    inc go_timer_frames
    lda go_timer_frames
    cmp #250                ; 5.0 s = 250 klatek przy 50 Hz (PAL)
    bcc @done

    lda #0
    sta go_timer_frames

    lda go_text_max_lines
    cmp #2
    bcc @done               ; Jeśli jest 1 linia lub mniej, nie przełączaj

    inc go_current_line
    lda go_current_line
    cmp go_text_max_lines
    bcc @apply_line

    lda #0
    sta go_current_line

@apply_line
    ldx go_current_line
    lda GoLineAddrLo,x
    sta GO_TEXT_LMS+1
    lda GoLineAddrHi,x
    sta GO_TEXT_LMS+2

@done
    jmp SYSVBV
.endp

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
    lda #$9C            ; DLI #1 (góra): wspólny wygenerowany charset Game Over/Travel ($9C00)
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

    ldy #0
    sty COLPF0    
    sty COLPF1
    sty COLBK

@rainbow_loop
    lda (GO_RAINBOW_PTR),y
    sta WSYNC
    sta COLPF2
    iny
    cpy #10
    bne @rainbow_loop

    lda #0
    sta go_dli_state
    pla
    rti
.endp

; Tablica kolorów tła dla paska tęczy (10 linii skanowania)
GoRainbow
    dta $94, $96, $98, $9A, $9C, $9A, $98, $96, $94, $00

GoRainbow_Failure
    dta $34, $36, $38, $3A, $3C, $3A, $38, $36, $34, $00

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
    lda #<GoRainbow_Failure
    sta GO_RAINBOW_PTR
    lda #>GoRainbow_Failure
    sta GO_RAINBOW_PTR+1

    ldx #0
@loop_fail
    lda GameOverFail_Data,x
    sta VRAM_ARENA,x
    lda GameOverFail_Data+$100,x
    sta VRAM_ARENA+$100,x
    lda GameOverFail_Data+$200,x
    sta VRAM_ARENA+$200,x
    lda GameOverFail_Data+$300,x
    sta VRAM_ARENA+$300,x
    inx
    bne @loop_fail
    jmp @screen_done

@do_success
    lda #<GoRainbow
    sta GO_RAINBOW_PTR
    lda #>GoRainbow
    sta GO_RAINBOW_PTR+1

    ldx #0
@loop_succ
    lda GameOverSuccess_Data,x
    sta VRAM_ARENA,x
    lda GameOverSuccess_Data+$100,x
    sta VRAM_ARENA+$100,x
    lda GameOverSuccess_Data+$200,x
    sta VRAM_ARENA+$200,x
    lda GameOverSuccess_Data+$300,x
    sta VRAM_ARENA+$300,x
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

    ; --- Charset Game Over (GO_CHARSET -> CHBAS) ---
    lda #>GO_CHARSET
    sta CHBAS
    sta CHBASE


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

    ; --- Podepnij własny VBI handler (wywołuje tracker + odliczanie klatek) ---
    lda #0
    sta NMIEN
    lda #<gameover_vbi
    sta $0222
    lda #>gameover_vbi
    sta $0223
    lda #$C0
    sta NMIEN
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
; copy_gameover_text — Kopiuje tekst GAME OVER (porażka/sukces) z ROM do RAM ($5E10)
;==============================================================
.proc copy_gameover_text
    lda #0
    sta go_timer_frames
    sta go_current_line

    lda #<$5E10
    sta GO_TEXT_LMS+1
    lda #>$5E10
    sta GO_TEXT_LMS+2

    lda GAME_RESULT_STATUS
    cmp #1                  ; 1 = Sukces
    beq @do_success

@do_fail
    mRLE_Depack text_gameover_fail FOOTER_ADDR
    lda text_gameover_fail_lines
    sta go_text_max_lines
    rts

@do_success
    mRLE_Depack text_gameover_success FOOTER_ADDR
    lda text_gameover_success_lines
    sta go_text_max_lines
    rts
.endp
