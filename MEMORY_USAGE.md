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
| **`$00A6` – `$00A6`** | 1 B | `IS_PORTAL_TRANSITION` | Zero Page | Flaga przejścia przez portal (0=zwykłe wyjście, 1=ekran podróży). |

| **`$00CB` – `$00DD`** | 19 B | `p_tis` .. `tmp` | Zero Page | Rejestry robocze odtwarzacza muzyki RMT (zmienne mono playera). |
| **`$0200` – `$0201`** | 2 B | `VDSLST` | OS RAM | Wektor przerwania DLI (Display List Interrupt) w pamięci cieni OS. |
| **`$0600` – `$1D35`** | 5942 B | `TitleScreen_Data` | Dane (ROM) | Skompresowany obrazek tytułowy (`title.rle`). |
| **`$1D36` – `$1DCA`** | 149 B | `DzikizgonData` | Dane (Sprites) | Skompresowane RLE dane graficzne logo "Dziki Zgon". |
| **`$1DCB` – `$1E2C`** | 98 B | `MoonData` | Dane (Sprites) | Skompresowane RLE dane graficzne księżyca. |
| **`$1E2D` – `$1E2D`** | 1 B | — | **WOLNY RAM** | Bufor wolnego RAM-u w niskiej pamięci. |
| **`$1FFD` – `$1FFF`** | 3 B | `start` (jump) | Kod programu | Jawny skok `jmp start` uruchamiający inicjalizację gry. |
| **`$2000` – `$2007`** | 8 B | `disable_basic_loader` | INI Loader | Wyłączenie BASICa (obsługa INI na starcie xex). |
| **`$2000` – `$202A`** | 43 B | `pmg.asm` | Kod programu | Wspólne procedury PMG (`pmg_clear_all`, `pmg_clear_range`). |
| **`$202B` – `$361C`** | 5618 B | `rle.asm` | Kod programu | Wspólna procedura dekompresji RLE (`RLE_Depack`). |
| **`$361D` – `$3B56`** | 1338 B | `title.asm` | Kod programu | Inicjalizacja, pętla ekranu tytułowego, kolory, DLI. |
| **`$9D21` – `$9DC4`** | 164 B | `story.asm` | Kod programu | Logika i inicjalizacja ekranu opisu fabularnego (*Story*). |
| **`$3B57` – `$3D2D`** | 471 B | `game.asm` | Kod programu | Logika gry właściwej (inicjalizacja, ruch gracza, mapa). |
| **`$3D2E` – `$3E7F`** | 338 B | `main.asm` | Kod programu | Maszyna stanów, pętla główna, `system_init`, `advance_stage`. |
| **`$3E80` – `$3FE7`** | 360 B | Display Lists | Display Lists | Skonsolidowane Display Listy gry ($3E80-$3FE7, dopasowane do strony 1 KB). |
| **`$3FE8` – `$3FFF`** | 24 B | — | **WOLNY RAM** | Mały bufor wolnej pamięci przed buforem ekranu. |
| **`$4000` – `$5E0F`** | 7696 B | `VRAM_ARENA` | VRAM / Bufor | Współdzielona arena wideo (title, game, gameover). |
| **`$5E10` – `$5F4F`** | 320 B | `FOOTER_ADDR` | VRAM / Bufor | Tekst stopki tytułowej / tekst Story / tekst GameOver. |
| **`$5F50` – `$5F73`** | 36 B | `secret_msg_buf` | RAM (Bufor) | Bufor roboczy na sklejony komunikat podniesienia secretu. |
| **`$5F74` – `$5FEB`** | 120 B | `ICON_ADDR` | RAM (Bufor) | Bufor nagłówka z ikonami dla ekranów tekstowych. |
| **`$5FEC` – `$5FFF`** | 20 B | — | **WOLNY RAM** | Pozostały wolny RAM przed własną czcionką. |
| **`$6000` – `$63FF`** | 1024 B | `font.asm` | Dane (Charset) | Główna czcionka gry (interfejs). Wskazywana przez `CHBASE = $60`. |
| **`$6400` – `$67FF`** | 1024 B | `game_font.asm` | Dane (Charset) | Czcionka graficzna do rysowania planszy w ANTIC 5. |
| **`$6800` – `$8862`** | 8291 B | `World Builder Data` | Dane (World) | Tabele świata (obiekty, ekrany, wyjścia). |
| **`$8863` – `$9D20`** | 5310 B | `all_gameover_texts` | Dane (Teksty) | Teksty komunikatów wygranej i przegranej. |
| **`$6800` – `$8862`** | 8291 B | — | **WOLNY RAM** | Wolna pamięć RAM w bloku `$6800–$9FFF`. |
| **`$1E2E` – `$1F8B`** | 350 B | `all_texts` | Dane (Teksty) | Skompresowane tekstualne zasoby gry (title, story). |
| **`$A800` – `$A9DF`** | 480 B | `secret_objects.asm` | Dane (World) | Obiekty sekretów na planszach. |
| **`$B79A` – `$B836`** | 157 B | `title_audio.asm` | Kod programu | Sterownik odtwarzacza muzyki dla scen. |
| **`$A000` – `$A7FF`** | 2048 B | `PMG` | Pamięć PMG | Pamięć Player/Missile Graphics (M0-M3, P0-P3). |
| **`$B6EE` – `$B799`** | 172 B | `travel_screen.asm` | Kod programu | Logika i renderowanie ekranu podróży. |
| **`$9DC5` – `$9FFF`** | 571 B | — | **WOLNY RAM** | Wolna pamięć przed zmiennymi RMT. |
| **`$A9E0` – `$ACFF`** | 800 B | `rmtplayr_vars` | Dane (Odtwarzacz) | Zmienne i tabele odtwarzacza RMT. |
| **`$AD00` – `$B241`** | 1346 B | `rmtplayr.asm` | Kod (Odtwarzacz) | Moduł odtwarzacza RMT. |
| **`$B300` – `$B610`** | 785 B | `title_music.asm` | Dane (Muzyka) | Moduł muzyczny RMT. |
| **`$B618` – `$B6ED`** | 214 B | `gameover.asm` | Kod programu | Logika i sterowanie ekranu końca gry (GameOver). |
| **`$B837` – `$B9BA`** | 388 B | `sprites` | Dane (Sprites) | Klatki sprite'ów postaci (Gerwalt + przeciwnicy). |
| **`$B9BB` – `$BEA4`** | 1258 B | `interactive_objects.asm` | Dane (World) | Obiekty interaktywne na planszach. |

---

## Analiza Wolnej Pamięci RAM

Dostępne wolne obszary RAM (zgodne z tabelą powyżej):

1.  **`$1F2D` – `$1FFF` (211 B)**: Wolny bufor w niskiej pamięci za sprite'ami księżyca.
2.  **`$3DA0` – `$3E7F` (224 B)**: Wolny bufor w dolnym RAM-ie przed Display Listami.
3.  **`$3FE8` – `$3FFF` (24 B)**: Mały bufor pomiędzy Display Listami a areną VRAM.
4.  **`$5F50` – `$5FFF` (176 B)**: Wolny bufor przed czcionkami.
5.  **`$84F4` – `$8FFF` (2 828 B)** & **`$9ED8` – `$9FFF` (296 B)**: **Obszar wolnej pamięci RAM** w bloku `$8000–$9FFF` dostępny na rozbudowę danych świata, logiki i ekranów.
6.  **`$A800` – `$A9DF` (480 B)**: Wolny bufor przed zmiennymi odtwarzacza RMT.
7.  **`$B242` – `$B2FF` (190 B)**: Wolny obszar pomiędzy kodem playera RMT a modułem muzycznym.
8.  **`$BEF9` – `$BFFF` (263 B)**: Wolna pamięć pod ROM-em BASIC-a za sprite'ami postaci.

Łącznie czysty, bezpośrednio dostępny wolny RAM w tej chwili to **5 265 B**.


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
