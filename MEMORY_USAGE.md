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
| **`$00CB` – `$00DD`** | 21 B | `p_tis` .. `tmp` | Zero Page | Rejestry robocze odtwarzacza muzyki RMT (zmienne mono playera). |
| **`$0200` – `$0201`** | 2 B | `VDSLST` | OS RAM | Wektor przerwania DLI (Display List Interrupt) w pamięci cieni OS. |
| **`$2000` – `$2002`** | 3 B | `start` (jump) | Kod programu | Jawny skok `jmp start` uruchamiający inicjalizację gry. |
| **`$2003` – `$200A`** | 8 B | `disable_basic_loader`| Kod programu | Wyłączenie BASICa (obsługa ini). |
| **`$200B` – `$2036`** | 44 B | `pmg.asm` | Kod programu | Wspólne procedury PMG (`pmg_clear_all`, `pmg_clear_range`). |
| **`$2037` – `$207D`** | 71 B | `rle.asm` | Kod programu | Wspólna procedura dekompresji RLE (`RLE_Depack`). |
| **`$207E` – `$2376`** | 761 B | `title.asm` | Kod programu | Inicjalizacja, pętla ekranu tytułowego, zmienna, kolory, procedury DLI. |
| **`$2377` – `$2377`** | 1 B | `fire_released_flag` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Story*. |
| **`$2378` – `$23E6`** | 111 B | `story.asm` | Kod programu | Logika i inicjalizacja ekranu opisu fabularnego (*Story*). |
| **`$23E7` – `$23E7`** | 1 B | `game_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Game*. |
| **`$23E8` – `$24C9`** | 226 B | `game.asm` | Kod programu | Logika gry właściwej (inicjalizacja, ruch graczem, testowa mapa). |
| **`$24CA` – `$24CA`** | 1 B | `gameover_fire_released`| Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *GameOver*. |
| **`$24CB` – `$25BF`** | 245 B | `gameover.asm` | Kod programu | Logika, inicjalizacja, DLI handler, tęcza oraz dekompresja tekstu. |
| **`$25C0` – `$2664`** | 165 B | `main.asm` | Kod programu | Maszyna stanów, pętla główna, `system_init`, `advance_stage`. |
| **`$2665` – `$26FF`** | 155 B | `align padding` | Padding | Wyrównanie do granicy strony przed tekstami. |
| **`$2700` – `$270E`** | 15 B | `GO_TEXT_Data` | Dane (Tekst) | Skompresowany RLE tekst "GAME OVER". |
| **`$270F` – `$283C`** | 302 B | `StoryText_Data` | Dane (Tekst) | Skompresowane RLE dane tekstu fabularnego (rozpakowywane do `$5E10`). |
| **`$283D` – `$2863`** | 39 B | `TitleFooterROM` | Dane (Tekst) | Skompresowany tekst stopki tytułowej. |
| **`$2864` – `$28F8`** | 149 B | `DzikizgonData` | Dane (Sprites) | Skompresowane RLE dane graficzne logo "Dziki Zgon". |
| **`$28F9` – `$295A`** | 98 B | `MoonData` | Dane (Sprites) | Skompresowane RLE dane graficzne księżyca. |
| **`$295B` – `$3E7F`** | **5413 B** | — | **WOLNY RAM** | Główny, ciągły obszar wolnej pamięci w dolnym RAM-ie na logikę gry / silnik. |
| **`$3E80` – `$3FEE`** | 367 B | Display Lists | Display Lists | Skonsolidowane Display Listy gry (Title, Story, Game, GameOver). |
| **`$3FEF` – `$3FFF`** | **17 B** | — | **WOLNY RAM** | Mały bufor wolnej pamięci przed buforem ekranu. |
| **`$4000` – `$5E0F`** | 7696 B | `VRAM_ARENA` | VRAM / Bufor | Współdzielona arena wideo (title, game, gameover). Rozpakowywana w runtime, zwalnia ogromne połacie RAM. |
| **`$5E10` – `$5F4F`** | 320 B | `FOOTER_ADDR` | VRAM / Bufor | Tekst stopki tytułowej / tekst Story / tekst GameOver. *Współdzielony.* |
| **`$5F50` – `$5FFF`** | **176 B** | — | **WOLNY RAM** | Bufor wolnego RAM-u przed własną czcionką. |
| **`$6000` – `$63FF`** | 1024 B | `font.asm` | Dane (Charset) | Czcionka własna gry (128 znaków × 8 B). Wskazywana przez `CHBASE = $60`. |
| **`$6400` – `$7FFF`** | **7168 B** | — | **WOLNY RAM** | Gigantyczny, ciągły blok wolnego RAM-u odzyskany dzięki VRAM_ARENA! Całkowicie pusty. |
| **`$8000` – `$9DC3`** | 7620 B | `ROM_DATA` | Dane (ROM) | Skompresowane grafiki w XEX (`title.rle` oraz `gameover.rle`). Rozpakowywane do `VRAM_ARENA`. |
| **`$9DC4` – `$9E2F`** | 108 B | `title_audio.asm` | Kod programu | Inicjalizacja dźwięku, handler Immediate VBI, wyciszanie POKEY (przesunięty z `$AC00`). |
| **`$9E30` – `$9FFF`** | **464 B** | — | **WOLNY RAM** | Wolna pamięć powyżej skompresowanych danych RLE, tuż pod granicą PMG. |
| **`$A000` – `$A2FF`** | 768 B | PMG Padding | PMG Reserved | Wyrównanie pamięci PMG do granicy 2 KB. Nieużywane bezpośrednio. |
| **`$A300` – `$A3FF`** | 256 B | `MISSILES` | Pamięć PMG | Pozycje pionowe pocisków (M0–M3) w rozdzielczości jednoliniowej. |
| **`$A400` – `$A4FF`** | 256 B | `PLAYER0` | Pamięć PMG | Klatka/obraz gracza P0. |
| **`$A500` – `$A5FF`** | 256 B | `PLAYER1` | Pamięć PMG | Klatka/obraz gracza P1. |
| **`$A600` – `$A6FF`** | 256 B | `PLAYER2` | Pamięć PMG | Klatka/obraz gracza P2. |
| **`$A700` – `$A7FF`** | 256 B | `PLAYER3` | Pamięć PMG | Klatka/obraz gracza P3. |
| **`$A800` – `$ABFF`** | 1024 B | `GAME_CHARSET` | Dane (Charset) | Zestaw kafelków terenu gry. Wskazywany przez `CHBASE = $A8`. Uwaga: Odtwarzacz RMT nadpisuje część tego obszaru (od `$A9E0`). |
| **`$AC00` – `$ACFF`** | **256 B** | — | **WOLNY RAM** | Wolna pamięć (pokrywa się częściowo ze zmiennymi i kodem RMT). |
| **`$AD00` – `$B4BE`** | 1983 B | `rmtplayr.asm` | Kod (Odtwarzacz) | Moduł odtwarzacza RMT (kod + tabele częstotliwości). Część danych i zmiennych rozciąga się wstecz od `$AA82` do `$ACFF`. |
| **`$B4BF` – `$B4FF`** | **65 B** | — | **WOLNY RAM** | Padding wyrównania do następnej strony pamięci dla modułu muzycznego. |
| **`$B500` – `$B810`** | 785 B | `title_music.asm`| Dane (Muzyka) | Skompilowany i dostrojony moduł muzyczny RMT ekranu tytułowego. |
| **`$B811` – `$BFFF`** | **2031 B** | — | **WOLNY RAM** | Wolna pamięć za modułem muzycznym (pod ROM-em BASIC-a). |

---

## Analiza Wolnej Pamięci RAM

Dzięki przeniesieniu odtwarzacza RMT pod ROM BASIC-a, gra posiada zredukowaną fragmentację i bardzo duże bloki wolnego RAM-u, podzielone na następujące obszary:

1.  **`$2891` – `$3E7F` (5 615 B)**: Główny silnik gry, logika ruchu przeciwników, mechanika walki.
2.  **`$5F50` – `$5FFF` (176 B)**: Wolny bufor przed czcionką.
3.  **`$67C0` – `$7FFF` (6 208 B)**: Dane map, tabele położeń obiektów.
4.  **`$8000` – `$9FFF` (8 192 B)**: **Skonsolidowany, wielki blok (8 KB)** w górnym RAM uzyskany po przeniesieniu muzyki. Idealny na bardzo duże zasoby, wczytywane pliki czy duże mapy.
5.  **`$AC75` – `$ACFF` (139 B)**: Wolny obszar między inicjalizacją dźwięku a playerem.
6.  **`$B4BF` – `$B4FF` (65 B)**: Wyrównanie pamięci dla muzyki.
7.  **`$B811` – `$BFFF` (2 031 B)**: Pozostała wolna przestrzeń pod ROM-em BASIC-a po załadowaniu playera i modułu.

Zredukowano znacznie fragmentację pamięci z 8 małych dziur do potężnych, jednolitych bloków (głównie `$8000-$9FFF`), co dramatycznie ułatwia projektowanie złożonej logiki gry.

---

## Współdzielenie i Optymalizacja Pamięci

Projekt wysoce optymalizuje zużycie pamięci poprzez nakładanie na siebie buforów ekranów, które nie są wyświetlane jednocześnie:

*   **Współdzielona Arena VRAM (`$4000–$5E0F`)**:
    *   Rozległe bitmapy i bufory nie są już trzymane osobno - wszystkie sceny (Title, Game, GameOver) używają wspólnie pamięci na `$4000`.
    *   W stanie **Game**, ekran gry (rozgrywka) używa trybu **ANTIC 5** (górne 9 linii, podwójna wysokość) oraz **ANTIC 2** (dolne 6 linii). Zajmuje to jedynie 600 B (360 B + 240 B), rezydując we wspólnej arenie na `$4000`.
    *   W stanie **GameOver** i **Title**, skompresowane w `ROM_DATA` grafiki `.rle` są dekompresowane proceduralnie przez depacker na `$4000`, przywracając ekran w całości.
    *   Dzięki temu rozwiązaniu udało się odzyskać gigantyczny ciągły obszar od `$6400` do `$7FFF` na logikę gry.

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
*   `GAME_CHARSET` został przesunięty na `$A800` (CHBASE = $A8), tuż za obszarem PMG. (Zestaw będzie współdzielony pomiędzy ANTIC 5 a ANTIC 2)
*   Dziura wyrównania `$A000–$A2FF` (768 B) znajduje się teraz pod ROM-em BASIC, gdzie i tak nie byłaby użyteczna dla ciągłego kodu/danych — nie marnuje cennego dolnego RAM-u.
