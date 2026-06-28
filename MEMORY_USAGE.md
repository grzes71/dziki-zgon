# Mapa Pamięci i Zużycie RAM — Wiedźmin: Dziki Zgon

Dokument ten opisuje bieżący podział pamięci RAM komputera Atari 800 XL / 65 XE (64 KB) w projekcie gry. 

## Podsumowanie konfiguracji systemowej

*   **Pamięć RAM**: Dostępna w pełnym zakresie od `$0000` do `$BFFF` (56 KB RAM).
*   **BASIC ROM**: Wyłączony (`PORTB = $FD` / `%11111101`), co zwalnia dodatkowe 8 KB RAM w obszarze `$A000–$BFFF`.
*   **OS ROM**: Włączony (wspiera obsługę przerwań NMI oraz DLI za pośrednictwem handlera OS ROM). RAM pod OS ROM (`$C000–$CFFF` i `$E000–$FFFF`) oraz rejestry sprzętowe (`$D000–$DFFF`) są niedostępne dla kodu gry jako zwykły RAM.

---

## Szczegółowa Tabela Zajętości Pamięci

| Zakres adresów (Hex) | Rozmiar (Dec) | Nazwa / Symbol | Typ obszaru | Opis i zastosowanie |
| :--- | :--- | :--- | :--- | :--- |
| **`$0080` – `$0080`** | 1 B | `SRC_TMP` | Zero Page | Zmienna tymczasowa używana m.in. do transpozycji sprite'ów. |
| **`$0081` – `$0081`** | 1 B | `GAME_STATE` | Zero Page | Bieżący stan maszyny stanów gry (0=Title, 1=Story, 2=Game, 3=GameOver). |
| **`$0200` – `$0201`** | 2 B | `VDSLST` | OS RAM | Wektor przerwania DLI (Display List Interrupt) w pamięci cieni OS. |
| **`$2000` – `$2002`** | 3 B | `start` (jump) | Kod programu | Jawny skok `jmp start` uruchamiający inicjalizację gry. |
| **`$2003` – `$2042`** | 64 B | `pmg.asm` | Kod programu | Wspólne procedury PMG (`pmg_clear_all`, `pmg_clear_range`). |
| **`$2043` – `$2308`** | 710 B | `title.asm` | Kod programu | Inicjalizacja, pętla ekranu tytułowego oraz procedury DLI tęczy. |
| **`$2309` – `$2309`** | 1 B | `fire_released_flag` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Story*. |
| **`$230A` – `$2362`** | 89 B | `story.asm` | Kod programu | Logika i inicjalizacja ekranu opisu fabularnego (*Story*). |
| **`$2363` – `$2363`** | 1 B | `game_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Game*. |
| **`$2364` – `$2432`** | 207 B | `game.asm` | Kod programu | Logika gry właściwej (inicjalizacja, ruch graczem, testowa mapa). |
| **`$2433` – `$2433`** | 1 B | `gameover_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *GameOver*. |
| **`$2434` – `$248C`** | 89 B | `gameover.asm` | Kod programu | Logika i inicjalizacja ekranu końca gry (*GameOver*). |
| **`$248D` – `$24E8`** | 92 B | `main.asm` | Kod programu | Maszyna stanów, pętla główna i początkowa konfiguracja systemu. |
| **`$24E9` – `$25A1`** | 185 B | `DzikizgonData` | Dane (Sprites) | Surowe dane graficzne logo "Dziki Zgon" (wczytywane do PMG). |
| **`$25A2` – `$2601`** | 96 B | `MoonData` | Dane (Sprites) | Surowe dane graficzne księżyca (wczytywane do PMG). |
| **`$2602` – `$2FFF`** | **2558 B** | — | **WOLNY RAM** | Obszar wolny po kodzie programu, dostępny na dalszy rozwój kodu/danych. |
| **`$3000` – `$30CD`** | 206 B | `DLIST_TITLE` | Display List | Lista instrukcji ANTIC dla ekranu tytułowego (tryb E + tryb 2). |
| **`$30CE` – `$30EA`** | 29 B | `DLIST_STORY` | Display List | Lista instrukcji ANTIC dla ekranu opisu fabularnego (tryb 2). |
| **`$30EB` – `$310A`** | 32 B | `DLIST_GAME` | Display List | Lista instrukcji ANTIC dla ekranu gry właściwej (tryb 4). |
| **`$310B` – `$31D2`** | 200 B | `DLIST_GAMEOVER` | Display List | Lista instrukcji ANTIC dla ekranu końca gry (tryb E). |
| **`$31D3` – `$3FFF`** | **3629 B** | — | **WOLNY RAM** | Obszar wolny za Display Listami, przed pamięcią ekranu. |
| **`$4000` – `$43BF`** | 960 B | `GAME_SCREEN` | VRAM / Bufor | Ekran gry właściwej (40x24 kafelków znakowych w trybie ANTIC 4). *Współdzielony z TitleData.* |
| **`$4000` – `$5E0F`** | 7696 B | `TitleData` | VRAM / Bufor | Pamięć bitmapy ekranu tytułowego (tryb ANTIC E, 160x192 px, 4 kolory). |
| **`$5E10` – `$5F4F`** | 320 B | `FOOTER_ADDR` | VRAM / Bufor | Tekst stopki ekranu tytułowego (8 linii × 40 znaków w trybie ANTIC 2). |
| **`$5F50` – `$5FFF`** | **176 B** | — | **WOLNY RAM** | Niewielki bufor wolnego RAM-u przed własną czcionką. |
| **`$6000` – `$63FF`** | 1024 B | `font.asm` | Dane (Charset) | Czcionka własna gry (128 znaków × 8 B). Wskazywana przez `CHBASE = $60`. |
| **`$6400` – `$653F`** | 320 B | `StoryText` | Dane (Tekst) | Bufor tekstu fabularnego dla ekranu *Story* (8 linii × 40 znaków). |
| **`$6540` – `$7FFF`** | **6848 B** | — | **WOLNY RAM** | Duży ciągły obszar wolnej pamięci na dane pomocnicze, mapy itp. |
| **`$8000` – `$82FF`** | 768 B | PMG Padding | PMG Reserved | Wyrównanie pamięci PMG do granicy 1 KB. Nieużywane bezpośrednio. |
| **`$8300` – `$83FF`** | 256 B | `MISSILES` | Pamięć PMG | Pozycje pionowe pocisków (M0–M3) w rozdzielczości jednoliniowej. |
| **`$8400` – `$84FF`** | 256 B | `PLAYER0` | Pamięć PMG | Klatka/obraz gracza P0 (Geralt/Gerwant we właściwej grze). |
| **`$8500` – `$85FF`** | 256 B | `PLAYER1` | Pamięć PMG | Klatka/obraz gracza P1. |
| **`$8600` – `$86FF`** | 256 B | `PLAYER2` | Pamięć PMG | Klatka/obraz gracza P2. |
| **`$8700` – `$87FF`** | 256 B | `PLAYER3` | Pamięć PMG | Klatka/obraz gracza P3. |
| **`$8800` – `$9FFF`** | **6144 B** | — | **WOLNY RAM** | Średni ciągły obszar wolnej pamięci na kod lub dane gry. |
| **`$A000` – `$A3FF`** | 1024 B | `GAME_CHARSET` | Dane (Charset) | Zestaw kafelków terenu gry (tryb ANTIC 4). Wskazywany przez `CHBASE = $A0`. |
| **`$A400` – `$BFFF`** | **7168 B** | — | **WOLNY RAM** | Obszar RAM odzyskany dzięki wyłączeniu BASIC ROM. Wolny na mapy regionów. |

---

## Analiza Wolnej Pamięci RAM

Gra posiada obecnie **`26 523 bajtów`** (~25.9 KB) wolnego i w pełni adresowalnego RAM-u, podzielonego na następujące bloki:

1.  **`$2602` – `$2FFF` (2 558 B)**: Idealne miejsce na dopisanie dodatkowych bibliotek lub procedur logicznych silnika gry.
2.  **`$31D3` – `$3FFF` (3 629 B)**: Przestrzeń przed buforem wideo. Można tu umieścić dodatkowe Display Listy lub dynamiczne struktury.
3.  **`$5F50` – `$5FFF` (176 B)**: Mały bufor (np. na zmienne globalne lub bufory wejściowe).
4.  **`$6540` – `$7FFF` (6 848 B)**: Duży, bardzo cenny obszar pamięci RAM. Doskonały na mapy aktualnego poziomu/regionu lub skomplikowaną logikę przeciwników.
5.  **`$8800` – `$9FFF` (6 144 B)**: Kolejny spory obszar, który można wykorzystać na logikę gry lub dodatkowe zestawy grafik PMG.
6.  **`$A400` – `$BFFF` (7 168 B)**: Wolna przestrzeń pod ROM-em BASIC-a. Idealna na przechowywanie statycznych baz danych gry, takich jak opisy przedmiotów, dialogi, czy definie stanu regionów.

---

## Współdzielenie i Optymalizacja Pamięci

Projekt optymalizuje zużycie pamięci poprzez nakładanie na siebie buforów ekranów, które nie są wyświetlane jednocześnie:

*   **Bufor Wideo `$4000–$5FFF`**:
    *   W stanie **Title** obszar ten zajmuje pełna bitmapa ekranu tytułowego `$4000–$5E0F` (7696 B) oraz stopka `$5E10–$5F4F` (320 B).
    *   W stanie **Game** w tym samym miejscu pod adresem `$4000–$43BF` znajduje się pamięć ekranu znakowego `GAME_SCREEN` (960 B). Nadpisuje ona początek bitmapy tytułowej.
    *   W stanie **GameOver** na tym samym obszarze wideo (`$4000` i kolejne) renderowany jest ekran końca gry.
    *   Dzięki temu zabiegowi zaoszczędzono ponad **7 KB RAM**, które w przeciwnym razie musiałyby zostać wydzielone osobno dla każdego z tych ekranów.

## Player/Missile Graphics (PMG) Alignment

Pamięć PMG musi być wyrównana do granicy 1 KB (ze względu na wartość wpisywaną do rejestru `PMBASE` kontrolera ANTIC). W trybie rozdzielczości jednoliniowej (single-line resolution):
*   Pociski (`MISSILES`) zajmują offset `$300` (adres `$8300`).
*   Gracze (`PLAYER0`–`PLAYER3`) zajmują kolejne offsety co 256 bajtów (`$8400`, `$8500`, `$8600`, `$8700`).
*   Obszar `$8000–$82FF` (768 bajtów) służy wyłącznie jako wyrównanie adresu bazowego PMG i w obecnej konfiguracji nie powinien być używany do innych celów, o ile włączone jest PMG.
