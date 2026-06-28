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
| **`$0200` – `$0201`** | 2 B | `VDSLST` | OS RAM | Wektor przerwania DLI (Display List Interrupt) w pamięci cieni OS. |
| **`$2000` – `$2002`** | 3 B | `start` (jump) | Kod programu | Jawny skok `jmp start` uruchamiający inicjalizację gry. |
| **`$2003` – `$202E`** | 44 B | `pmg.asm` | Kod programu | Wspólne procedury PMG (`pmg_clear_all`, `pmg_clear_range`). |
| **`$202F` – `$2075`** | 71 B | `rle.asm` | Kod programu | Wspólna procedura dekompresji RLE (`RLE_Depack`). |
| **`$2076` – `$236E`** | 761 B | `title.asm` | Kod programu | Inicjalizacja, pętla ekranu tytułowego, zmienna, kolory, procedury DLI. |
| **`$236F` – `$236F`** | 1 B | `fire_released_flag` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Story*. |
| **`$2370` – `$23DE`** | 111 B | `story.asm` | Kod programu | Logika i inicjalizacja ekranu opisu fabularnego (*Story*). |
| **`$23DF` – `$23DF`** | 1 B | `game_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *Game*. |
| **`$23E0` – `$24C1`** | 226 B | `game.asm` | Kod programu | Logika gry właściwej (inicjalizacja, ruch graczem, testowa mapa). |
| **`$24C2` – `$24C2`** | 1 B | `gameover_fire_released` | Zmienna (RAM) | Flaga puszczenia przycisku FIRE w scenie *GameOver*. |
| **`$24C3` – `$25B7`** | 245 B | `gameover.asm` | Kod programu | Logika, inicjalizacja, DLI handler, tęcza oraz dekompresja tekstu. |
| **`$25B8` – `$265C`** | 165 B | `main.asm` | Kod programu | Maszyna stanów, pętla główna, `system_init`, `advance_stage`. |
| **`$265D` – `$278A`** | 302 B | `StoryText_Data` | Dane (Tekst) | Skompresowane RLE dane tekstu fabularnego (rozpakowywane do `$5E10` przy wejściu w Story). |
| **`$278B` – `$2799`** | 15 B | `GO_TEXT_Data` | Dane (Tekst) | Skompresowany RLE tekst "GAME OVER" (rozpakowywany do `$5E10` przy GameOver). |
| **`$279A` – `$282E`** | 149 B | `DzikizgonData` | Dane (Sprites) | Skompresowane RLE dane graficzne logo "Dziki Zgon" (rozpakowywane do bufora $3000). |
| **`$282F` – `$2890`** | 98 B | `MoonData` | Dane (Sprites) | Skompresowane RLE dane graficzne księżyca (rozpakowywane do bufora $3000). |
| **`$2891` – `$3E7F`** | **5615 B** | — | **WOLNY RAM** | Główny, ciągły obszar wolnej pamięci w dolnym RAM-ie na logikę gry / silnik. |
| **`$3E80` – `$3FEE`** | 367 B | Display Lists | Display Lists | Skonsolidowane Display Listy gry (Title, Story, Game, GameOver). |
| **`$3FEF` – `$3FFF`** | **17 B** | — | **WOLNY RAM** | Mały bufor wolnej pamięci przed buforem ekranu. |
| **`$4000` – `$5E0F`** | 7696 B | `TitleData` | VRAM / Bufor | Pamięć bitmapy ekranu tytułowego (ANTIC E, 160×192, 4 kolory). |
| **`$5E10` – `$5F4F`** | 320 B | `FOOTER_ADDR` | VRAM / Bufor | Tekst stopki tytułowej / tekst Story / tekst GameOver. *Współdzielony.* |
| **`$5F50` – `$5FFF`** | **176 B** | — | **WOLNY RAM** | Bufor wolnego RAM-u przed własną czcionką. |
| **`$6000` – `$63FF`** | 1024 B | `font.asm` | Dane (Charset) | Czcionka własna gry (128 znaków × 8 B). Wskazywana przez `CHBASE = $60`. |
| **`$6400` – `$67BF`** | 960 B | `GAME_SCREEN` | VRAM / Bufor | Ekran gry właściwej (tryb ANTIC 4, 40×24 znaków). Przeniesiony z $4000 by uniknąć nadpisywania bitmapy tytułu. |
| **`$67C0` – `$7FFF`** | **6208 B** | — | **WOLNY RAM** | Wolny ciągły blok RAM w środkowym obszarze. |
| **`$8000` – `$9FFF`** | **8192 B** | — | **WOLNY RAM** | Duży ciągły blok wolnej pamięci (PMG przeniesiony do $A000, BASIC wyłączony). |
| **`$A000` – `$A2FF`** | 768 B | PMG Padding | PMG Reserved | Wyrównanie pamięci PMG do granicy 2 KB. Nieużywane bezpośrednio. |
| **`$A300` – `$A3FF`** | 256 B | `MISSILES` | Pamięć PMG | Pozycje pionowe pocisków (M0–M3) w rozdzielczości jednoliniowej. |
| **`$A400` – `$A4FF`** | 256 B | `PLAYER0` | Pamięć PMG | Klatka/obraz gracza P0. |
| **`$A500` – `$A5FF`** | 256 B | `PLAYER1` | Pamięć PMG | Klatka/obraz gracza P1. |
| **`$A600` – `$A6FF`** | 256 B | `PLAYER2` | Pamięć PMG | Klatka/obraz gracza P2. |
| **`$A700` – `$A7FF`** | 256 B | `PLAYER3` | Pamięć PMG | Klatka/obraz gracza P3. |
| **`$A800` – `$ABFF`** | 1024 B | `GAME_CHARSET` | Dane (Charset) | Zestaw kafelków terenu gry (tryb ANTIC 4). Wskazywany przez `CHBASE = $A8`. |
| **`$AC00` – `$BFFF`** | **5120 B** | — | **WOLNY RAM** | Obszar RAM pod BASIC-em. Wolny na mapy regionów / dialogi. |

---

## Analiza Wolnej Pamięci RAM

Dzięki wdrożonym optymalizacjom gra posiada obecnie **`25 328 bajtów`** (~24.7 KB) wolnego i w pełni adresowalnego RAM-u, podzielonego na następujące duże bloki:

1.  **`$2891` – `$3E7F` (5 615 B)**: Idealne miejsce na główny silnik gry, logikę ruchu przeciwników, mechanikę walki.
2.  **`$67C0` – `$7FFF` (6 208 B)**: Duży blok pamięci RAM za ekranem gry. Doskonały na mapy regionów, tabele położeń obiektów.
3.  **`$8000` – `$9FFF` (8 192 B)**: Kolejny wielki obszar, który został scalony dzięki przeniesieniu PMG do $A000 i BASIC off.
4.  **`$AC00` – `$BFFF` (5 120 B)**: Wolna przestrzeń pod ROM-em BASIC-a. Idealna na statyczne bazy danych (teksty zadań, dialogi).

Zredukowano fragmentację pamięci z 8 małych dziur do zaledwie kilku dużych, jednolitych bloków, co ułatwi projektowanie bardziej złożonej logiki gry.

---

## Współdzielenie i Optymalizacja Pamięci

Projekt wysoce optymalizuje zużycie pamięci poprzez nakładanie na siebie buforów ekranów, które nie są wyświetlane jednocześnie:

*   **Bufor Wideo `$4000–$5FFF`**:
    *   W stanie **Title** obszar ten zajmuje pełna bitmapa ekranu tytułowego `$4000–$5E0F` (7696 B) oraz stopka `$5E10–$5F4F` (320 B).
    *   W stanie **Game** ekran gry został przeniesiony do `GAME_SCREEN = $6400` (960 B), aby nie nadpisywać bitmapy tytułu przy powrocie z gry do ekranu tytułowego.
    *   W stanie **GameOver** bitmapa znajduje się w `GO_SCREEN = $7000` (2784 B), a tekst w `GO_TEXT = $7C00` (32 B) — niezależnie od obszaru tytułu.
    *   Dzięki tym zmianom wszystkie trzy ekrany nie kolidują ze sobą, a przejścia między stanami nie wymagają przeładowywania bitmap z ROM-u.

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
*   `GAME_CHARSET` został przesunięty na `$A800` (CHBASE = $A8), tuż za obszarem PMG.
*   Dziura wyrównania `$A000–$A2FF` (768 B) znajduje się teraz pod ROM-em BASIC, gdzie i tak nie byłaby użyteczna dla ciągłego kodu/danych — nie marnuje cennego dolnego RAM-u.
