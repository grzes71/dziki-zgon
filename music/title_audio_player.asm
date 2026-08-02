; ===================================================================
; music/title_audio_player.asm — RMT Player & Music Module ($A9E0 - $B610)
; ===================================================================

PLAYER = $AD00

; Include the converted player code
    icl "gen/rmtplayr.asm"

; Song data module for title screen
    .align 256
MODUL
    icl "gen/title_music.asm"
