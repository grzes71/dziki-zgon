# Mapa Pamięci i Zużycie RAM — Wiedźmin: Dziki Zgon

Dokument ten opisuje bieżący podział pamięci RAM komputera Atari 800 XL / 65 XE (64 KB) w projekcie gry. 

## Podsumowanie konfiguracji systemowej

*   **Pamięć RAM**: Dostępna w pełnym zakresie od `$0000` do `$BFFF` (56 KB RAM).
*   **BASIC ROM**: Wyłączony (`PORTB = $FF` / `%11111111`), co zwalnia dodatkowe 8 KB RAM w obszarze `$A000–$BFFF`.
*   **OS ROM**: Włączony (wspiera obsługę przerwań NMI oraz DLI za pośrednictwem handlera OS ROM). RAM pod OS ROM (`$C000–$CFFF` i `$E000–$FFFF`) oraz rejestry sprzętowe (`$D000–$DFFF`) są niedostępne dla kodu gry jako zwykły RAM.

---

## Szczegółowa Tabela Zajętości Pamięci

| Zakres adresów (Hex) | Rozmiar (Dec) | Nazwa / Symbol | Typ obszaru | Opis i zastosowanie |
| :--- | :--- | :--- | :--- | :--- |
| **`$0080` – `$0080`** | 1 B | `SRC_TMP` | Zero Page | Zmienna tymczasowa używana m.in. do transpozycji sprite'ów. |
| **`$0081` – `$0081`** | 1 B | `GAME_STATE` | Zero Page | Bieżący stan maszyny stanów gry (0=Title, 1=Story, 2=Game, 3=GameOver). |
| **`$0082` – `$0083`** | 2 B | `SRC_PTR` | Zero Page | Wskaźnik źródłowy dla depackera RLE (2 bajty). |
| **`$0084` – `$0085`** | 2 B | `DST_PTR` | Zero Page | Wskaźnik docelowy dla depackera RLE (2 bajty). |
| **`$0086` – `$0087`** | 2 B | `SCREEN_PTR` | Zero Page | Wskaźnik na dane obiektów aktualnego ekranu gry. |
| **`$0088` – `$0089`** | 2 B | `TILE_PTR` | Zero Page | Wskaźnik na kafelki obiektu (World Builder). |
| **`$008A` – `$008A`** | 1 B | `GAME_SCREEN_ID` | Zero Page | Globalny ID aktualnego ekranu mapy. |
| **`$008B` – `$0091`** | 7 B | Zmienne renderera | Zero Page | Rejestry iteracyjne pętli renderującej (X, Y, W, H, CODE, TMP_X, TMP_Y). |
| **`$0092` – `$0095`** | 4 B | Zmienne silnika | Zero Page | `FrameCounter`, `InputState_Joy`, `InputState_Trig`, `Engine_RequestStageAdvance`. |
| **`$0096` – `$009A`** | 5 B | Zmienne aktorów | Zero Page | `PMG_PTR`, `ACTOR_TMP_X`, `ACTOR_TMP_Y`, `ACTOR_TMP_HEIGHT`. |
| **`$009C` – `$00A1`** | 6 B | Zmienne ekranu/aktorów | Zero Page | `REQ_SCREEN_TRANSITION`, `NEW_SCREEN_ID`, `NEW_ACTOR_X/Y`, `CURRENT_ACTOR`. |
| **`$00A2` – `$00A2`** | 1 B | `MSG_STATE` | Zero Page | Stan linii komunikatów (0=brak, 1=wyświetlanie, 2=1s do końca). |
| **`$00CB` – `$00DD`** | 19 B | `p_tis` .. `tmp` | Zero Page | Rejestry robocze odtwarzacza muzyki RMT (zmienne mono playera). |
| **`$0200` – `$0201`** | 2 B | `VDSLST` | OS RAM | Wektor przerwania DLI (Display List Interrupt) w pamięci cieni OS. |
| **`$0700` – `$1E35`** | 5942 B | `TitleScreen_Data` | Dane (ROM) | Skompresowany obrazek tytułowy (`title.rle`). |
| **`$1E36` – `$1ECA`** | 149 B | `DzikizgonData` | Dane (Sprites) | Skompresowane RLE dane graficzne logo "Dziki Zgon". |
| **`$1ECB` – `$1F2C`** | 98 B | `MoonData` | Dane (Sprites) | Skompresowane RLE dane graficzne księżyca. |
| **`$1F2D` – `$1FFF`** | 211 B | — | **WOLNY RAM** | Bufor wolnego RAM-u w niskiej pamięci. |
| **`$2000` – `$2002`** | 3 B | `start` (jump) | Kod programu | Jawny skok `jmp start` uruchamiający inicjalizację gry. |
| **`$2003` – `$200A`** | 8 B | `disable_basic_loader` | Kod programu | Wyłączenie BASICa (obsługa ini). |
| **`$200B` – `$2035`** | 43 B | `pmg.asm` | Kod programu | Wspólne procedury PMG (`pmg_clear_all`, `pmg_clear_range`). |
| **`$2036` – `$31A6`** | 4465 B | `rle.asm` | Kod programu | Wspólna procedura dekompresji RLE (`RLE_Depack`). |
| **`$31A7` – `$34CB`** | 805 B | `title.asm` | Kod programu | Inicjalizacja, pętla ekranu tytułowego, zmienna, kolory, procedury DLI. |
| **`$34CC` – `$34CC`** | 1 B | `fire_released_flag` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Story*. |
| **`$34CD` – `$353E`** | 114 B | `story.asm` | Kod programu | Logika i inicjalizacja ekranu opisu fabularnego (*Story*). |
| **`$353F` – `$353F`** | 1 B | `game_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Game*. |
| **`$3722` – `$3902`** | 481 B | `game.asm` | Kod programu | Logika gry właściwej (inicjalizacja, ruch graczem, testowa mapa). |
| **`$3903` – `$3903`** | 1 B | `gameover_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *GameOver*. |
| **`$3968` – `$3A4A`** | 227 B | `gameover.asm` | Kod programu | Logika, inicjalizacja, DLI handler, tęcza oraz dekompresja tekstu. |
| **`$3A4B` – `$3AFF`** | 181 B | `main.asm` | Kod programu | Maszyna stanów, pętla główna, `system_init`, `advance_stage`. |
| **`$3A7E` – `$3AFF`** | 130 B | `align padding` | Padding | Wyrównanie do granicy strony przed tekstami. |
| **`$3B00` – `$3B0E`** | 15 B | `GO_TEXT_Data` | Dane (Tekst) | Skompresowany RLE tekst "GAME OVER". |
| **`$3B0F` – `$3C3C`** | 302 B | `StoryText_Data` | Dane (Tekst) | Skompresowane RLE dane tekstu fabularnego (rozpakowywane do `$5E10`). |
| **`$3C3D` – `$3D5D`** | 289 B | `TitleFooterROM` | Dane (Tekst) | Skompresowany tekst stopki tytułowej. |
| **`$3D5E` – `$3E7F`** | 290 B | — | **WOLNY RAM** | Bufor wolnej pamięci w dolnym RAM-ie. |
| **`$3E80` – `$3FE7`** | 360 B | Display Lists | Display Lists | Skonsolidowane Display Listy gry (Title, Story, Game, GameOver). |
| **`$3FE8` – `$3FFF`** | 24 B | — | **WOLNY RAM** | Mały bufor wolnej pamięci przed buforem ekranu. |
| **`$4000` – `$5E0F`** | 7696 B | `VRAM_ARENA` | VRAM / Bufor | Współdzielona arena wideo (title, game, gameover). Rozpakowywana w runtime. |
| **`$5E10` – `$5F4F`** | 320 B | `FOOTER_ADDR` | VRAM / Bufor | Tekst stopki tytułowej / tekst Story / tekst GameOver. *Współdzielony.* |
| **`$5F50` – `$5FFF`** | 176 B | — | **WOLNY RAM** | Bufor wolnego RAM-u przed własną czcionką. |
| **`$6000` – `$63FF`** | 1024 B | `font.asm` | Dane (Charset) | Główna czcionka gry (interfejs). Wskazywana przez `CHBASE = $60`. |
| **`$6400` – `$67FF`** | 1024 B | `game_font.asm` | Dane (Charset) | Czcionka graficzna do rysowania planszy w ANTIC 5. Wskazywana przez `CHBASE = $64`. |
| **`$6800` – `$8505`** | 7430 B | `World Builder Data` | Dane (World) | Tabele świata (obiekty, ekrany, wyjścia, obiekty interaktywne). |
| **`$8506` – `$856F`** | 106 B | `title_audio.asm` | Kod programu | Inicjalizacja dźwięku, handler Immediate VBI, wyciszanie POKEY. |
| **`$8570` – `$8E39`** | 2250 B | `GameOverScreen_Data` | Dane (ROM) | Skompresowany obrazek GameOver (`gameover.rle`). |
| **`$A000` – `$A2FF`** | 768 B | PMG Padding | PMG Reserved | Wyrównanie pamięci PMG do granicy 2 KB. Nieużywane bezpośrednio. |
| **`$A300` – `$A3FF`** | 256 B | `MISSILES` | Pamięć PMG | Pozycje pionowe pocisków (M0–M3) w rozdzielczości jednoliniowej. |
| **`$A400` – `$A4FF`** | 256 B | `PLAYER0` | Pamięć PMG | Klatka/obraz gracza P0. |
| **`$A500` – `$A5FF`** | 256 B | `PLAYER1` | Pamięć PMG | Klatka/obraz gracza P1. |
| **`$A600` – `$A6FF`** | 256 B | `PLAYER2` | Pamięć PMG | Klatka/obraz gracza P2. |
| **`$A700` – `$A7FF`** | 256 B | `PLAYER3` | Pamięć PMG | Klatka/obraz gracza P3. |
| **`$A800` – `$A9DF`** | 480 B | `GAME_CHARSET` | PMG Reserved | Rezerwa na charset / bufor cieni RMT. |
| **`$A9E0` – `$ACFF`** | 800 B | `rmtplayr_vars` | Dane (Odtwarzacz) | Zmienne i tabele odtwarzacza RMT (`TRACK_VARIABLES`, `FRQTAB`, `VOLUMETAB`). |
| **`$AD00` – `$B241`** | 1346 B | `rmtplayr.asm` | Kod (Odtwarzacz) | Moduł odtwarzacza RMT (kod + tabele częstotliwości). |
| **`$B242` – `$B2FF`** | 190 B | — | **WOLNY RAM** | Padding wyrównania do następnej strony pamięci dla modułu muzycznego. |
| **`$B300` – `$B610`** | 785 B | `title_music.asm` | Dane (Muzyka) | Skompilowany i dostrojony moduł muzyczny RMT ekranu tytułowego. |
| **`$B611` – `$BF08`** | 2296 B | `GERWALT_RIGHT_FRAME_0` | Dane (Sprites) | Dane klatek sprite'ów gracza i przeciwników (pod ROM BASIC). |

---

## Analiza Wolnej Pamięci RAM

Dostępne wolne obszary RAM (zgodne z tabelą powyżej):

1.  **`$2B5B` – `$3E7F` (4 901 B)**: Główny, ciągły blok wolnej pamięci w dolnym RAM-ie na logikę gry.
2.  **`$3FE8` – `$3FFF` (24 B)**: Mały bufor pomiędzy Display Listami a areną VRAM.
3.  **`$5F50` – `$5FFF` (176 B)**: Wolny bufor przed czcionkami.
4.  **`$6800` – `$7FFF` (6 144 B)**: Największy wolny blok w dolnym RAM-ie, dobry na duże struktury danych.
5.  **`$B242` – `$B2FF` (190 B)**: Wolny obszar pomiędzy kodem playera RMT a modułem muzycznym.
6.  **`$B611` – `$BFFF` (2 543 B)**: Wolna pamięć pod ROM-em BASIC-a za modułem muzycznym.

Łącznie wolny RAM z tych bloków to **891 B**.

---

## Współdzielenie i Optymalizacja Pamięci

Projekt wysoce optymalizuje zużycie pamięci poprzez nakładanie na siebie buforów ekranów, które nie są wyświetlane jednocześnie:

*   **Współdzielona Arena VRAM (`$4000–$5E0F`)**:
    *   Rozległe bitmapy i bufory nie są już trzymane osobno - wszystkie sceny (Title, Game, GameOver) używają wspólnie pamięci na `$4000`.
    *   W stanie **Game**, ekran gry (rozgrywka) używa trybu **ANTIC 5** (górne 10 linii) oraz **ANTIC 2** (dolne 4 linie). Zajmuje to jedynie 560 B (400 B + 160 B), rezydując we wspólnej arenie na `$4000`. W połowie ekranu w oparciu o DLI gra dynamicznie podmienia również zestaw znaków (`CHBASE`).
    *   W stanie **GameOver** i **Title**, skompresowane w `ROM_DATA` grafiki `.rle` są dekompresowane proceduralnie przez depacker na `$4000`, przywracając ekran w całości.
    *   Dzięki temu rozwiązaniu udało się odzyskać gigantyczny ciągły obszar od `$6800` do `$7FFF` na logikę gry.

*   **Współdzielona Stopka Tekstowa (`$5E10–$5F4F`)**:
    *   W stanie **Title** `copy_title_footer` przywraca tekst zachęty z ROM (`TitleFooterROM`).
    *   W stanie **Story** `copy_story_text` dekompresuje tekst fabularny (RLE) w to samo miejsce.
    *   W stanie **GameOver** `copy_gameover_text` dekompresuje tekst "GAME OVER" (RLE) w to samo miejsce.
    *   Każda scena samodzielnie przygotowuje swój tekst przed włączeniem DMA — brak konfliktów.

## Player/Missile Graphics (PMG) Alignment

Pamięć PMG została przeniesiona do obszaru pod ROM-em BASIC (**`PMBASE = $A0`**) aby wyeliminować 768-bajtową dziurę wyrównania w dolnym RAM-ie. W trybie rozdzielczości jednoliniowej (single-line resolution):
*   Adres bazowy: `PMBASE_ADDR = $A000`
*   Pociski (`MISSILES`) zajmują offset `$300` → adres `$A300`.
*   Gracze (`PLAYER0`–`PLAYER3`) zajmują kolejne offsety co 256 B → `$A400`, `$A500`, `$A600`, `$A700`.
*   Czcionki `game_font.asm` oraz `font.asm` zostały umieszczone w bezpiecznej dolnej połowie pamięci (`$6400` oraz `$6000`), a przełączanie ich odbywa się poprzez DLI w trakcie generowania obrazu. Dawna przestrzeń na font gry na `$A800` pod ROM-em przestała być aktywnie czytana przez ANTIC.
*   Dziura wyrównania `$A000–$A2FF` (768 B) znajduje się teraz pod ROM-em BASIC, gdzie i tak nie byłaby użyteczna dla ciągłego kodu/danych — nie marnuje cennego dolnego RAM-u.
