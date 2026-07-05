# AI Context — Wiedźmin: Dziki Zgon

## Projekt

Gra przygodowo-zręcznościowa na Atari 800 XL / 65 XE (64 KB RAM), humorystyczna parodia Wiedźmina. Widok z góry, ekrany przełączane krawędziowo, sterowanie joystick + FIRE.

## Architektura kodu

Projekt używa modułowej architektury z `icl` (MADS include library). Jeden plik `main.asm` jest punktem startowym — zawiera maszynę stanów przełączającą ekrany.

```
main.asm                     # Punkt startowy, maszyna stanów (title→story→game→gameover→title)
├── hardware.asm             # Wszystkie equ dla GTIA/ANTIC/POKEY/OS + stałe projektu
├── zeropage.asm             # Zmienne page zero ($80 SRC_TMP, $81 GAME_STATE)
├── lib/
│   └── pmg.asm              # Procedury PMG: pmg_clear_all, pmg_clear_range
├── fonts/
│   └── font.asm             # Własna czcionka 128 znaków (1 KB)
└── scenes/
    ├── title/
    │   └── title.asm        # Ekran tytułowy: title_init + title_run + DLI + tęcza
    ├── story/
    │   └── story.asm        # Ekran opisu (wyświetlanie i obsługa opisu)
    ├── game/
    │   └── game.asm         # Gra właściwa (placeholder)
    └── gameover/
        └── gameover.asm     # Ekran końca gry (placeholder)
```

**Konwencja**: każda scena eksportuje `_init` (konfiguracja jednorazowa) i `_run` (obsługa klatki). `_run` ustawia `GAME_STATE` by przejść do następnego stanu.

**Maszyna stanów**: `GAME_STATE` ($81) — 0=title, 1=story, 2=game, 3=gameover. Gameover wraca do title.

## Pliki kluczowe

| Plik | Rola |
|---|---|
| `main.asm` | Punkt startowy + maszyna stanów, kompilowany do `dziki_zgon.xex` |
| `hardware.asm` | Wspólne definicje rejestrów GTIA/ANTIC/POKEY i stałe |
| `scenes/title/title.asm` | Logika ekranu tytułowego (init, run, DLI, tabele kolorów) |
| `scenes/*/` | Kolejne sceny — każda z własnym `_init` i `_run` |
| `lib/pmg.asm` | Współdzielone procedury PMG |
| `scripts/img2asm.py` | Konwerter PNG → .bin + .asm + _colors.asm + _displaylist.asm (+ `.rle` przy `-c rle`) |
| `fonts/font.asm` | Własna czcionka 128 znaków (1 KB, $6000, CHBASE=$60) |
| `MEMORY_USAGE.md` | Szczegółowa mapa pamięci i alokacji wolnego RAM-u |
| `docs/KONSPEKT.md` | Dokument projektowy — fabuła, regiony, mechaniki |

## Build

```bash
make          # wszystko: sprite'y → tło → XEX
make sprites  # tylko moon + dziki-zgon
make bg       # tylko tło
make clean    # usuwa wygenerowane
```

Wymagania: Python 3.10+, Pillow 12.x, MADS 2.1.x, GNU Make.
Instalacja zależności: `pip install -r requirements.txt`

## Testowanie i Debugowanie

W projekcie zawarte są narzędzia wspomagające testowanie i diagnozowanie problemów z pamięcią gry:

1. **`atari-smoke-test`**
   - Własna aplikacja CLI (Python) służąca do automatycznego weryfikowania poprawności uruchamiania obrazów XEX w emulatorze Altirra.
   - Jeśli po uruchomieniu gry emulator "wisi" albo wyłącza się przedwcześnie, `atari-smoke-test` to wykryje i rzuci odpowiedni błąd (np. kod wyjścia 5 - `EmulatorCrashedError`).
   - Uruchamianie (w środowisku `.venv`): `python -m atari_smoke_test.main --xex dziki_zgon.xex --timeout 5`
   - Testy jednostkowe: `pytest tests/`

2. **`dump.py` (Zrzucanie segmentów pamięci XEX)**
   - W przypadku pojawienia się błędu "PROGRAM ERROR" lub zawieszenia programu zaraz po starcie, użyj skryptu `dump.py` do sprawdzenia wewnętrznej struktury wybudowanego pliku XEX.
   - Uruchamianie: `python dump.py`
   - Pokazuje on przedziały adresów każdego z zapisanych bloków, dzięki czemu łatwo wykryjesz czy MADS połączył ("zmergował") bloki leżące blisko siebie w jeden wielki segment i czy przez to np. blok inicjalizacyjny (jak `org $AC00`) nie został przykryty zerami ładującymi się z bloku nadrzędnego (jak `org $AA82` w `rmtplayr`).

3. **`check_memory.py` (Automatyczna walidacja mapy pamięci)**
   - Skrypt zintegrowany bezpośrednio z Makefile. Podczas kompilacji (`make all`) automatycznie weryfikuje zajętość RAM-u.
   - Analizuje zrzuconą przez kompilator tablicę symboli `game.lab` i samodzielnie aktualizuje tabele adresów i pojemności bloków w `MEMORY_USAGE.md`.
   - Zwalnia nas to z ręcznego aktualizowania dokumentacji pamięci — plik MD zawsze w 100% odpowiada temu, co siedzi w pliku XEX.

## Tryb graficzny

- **ANTIC E** (Graphics 7), 160×192 px, 4 kolory (2 bpp), 40 B/linia — ekran tytułowy
- **ANTIC D** (Graphics 7 narrow), 128×96 px, 4 kolory (2 bpp) — ekran game over
- **ANTIC 2** (Graphics 0), 40×24 znaków, 1 kolor (biały na czarnym, COLPF1=$0E) — ekran opisu (story) i współdzielony bufor tekstu pod $5E10
- **Gra właściwa** używa dwóch trybów łączonych w jednym ekranie (Display List):
  - **ANTIC 5** (górne 10 linii), 40×10 znaków podwójnej wysokości, kolorowa plansza gry (używa czcionki kafelków pod $6400)
  - **ANTIC 2** (dolne 4 linie), 40×4 znaków, panel statusowy (używa systemowej czcionki pod $6000)
- Kolory: indeks 0→COLBK, 1→COLPF0, 2→COLPF1, 3→COLPF2
- Generator `_colors.asm` zapisuje **bezpośrednio do GTIA** ($D016-$D01A) i dostarcza stałe `.equ` (`TITLE_COLBK`, `TITLE_COLPF0`-2) do użycia w DLI

## Mapa pamięci

Szczegółowa mapa pamięci, wolnych bloków oraz objaśnienia znajdują się w dedykowanym dokumencie [MEMORY_USAGE.md](MEMORY_USAGE.md). Skrócony podział pamięci:

| Adres | Zawartość |
|---|---|
| $0080-$0085 | Page zero: `SRC_TMP`, `GAME_STATE`, `SRC_PTR`, `DST_PTR` |
| $2000-$2664 | Kod: main + lib + scenes |
| $2700-$295A | Dane tekstów i sprite'ów (RLE) |
| $295B-$3E7F | Duży wolny blok RAM |
| $3E80-$3FEE | Display Lists (Title/Story/Game/GameOver) |
| $4000-$5E0F | **VRAM_ARENA** (współdzielony bufor ekranu scen) |
| $5E10-$5F4F | Współdzielony bufor tekstu (Story/GameOver/stopka tytułu) |
| $6000-$63FF | Czcionka systemowa (interfejs) gry (`font.asm`, `CHBASE=$60`) |
| $6400-$67FF | Czcionka mapy gry (`game_font.asm`, `CHBASE=$64`) |
| $6800-$7FFF | Duży wolny blok RAM (odzyskany po VRAM_ARENA) |
| $8000-$9DC3 | `ROM_DATA` (`title.rle`, `gameover.rle`) |
| $A000-$A7FF | PMG (`PMBASE_ADDR=$A000`, single-line) |
| $A800-$ABFF | Dawniej `GAME_CHARSET`, obecnie rezerwa (nieużywana) |
| $AD00-$B4BE | Odtwarzacz RMT |
| $B500-$B810 | Moduł muzyki title |

> PORTB=$FF (OS ROM on, BASIC off). Program startuje jawnie przez `jmp start` na $2000.

## Display List — generator i ograniczenia ANTIC

ANTIC ma 12-bitowy licznik adresu podczas pobierania linii → nie może przekroczyć granicy 4KB ($x000→$y000). `img2asm.py` rozwiązuje to przez:

1. `pack_pixels()` — dodaje padding ($00) przy granicach 4KB, wyrównując kolejną linię do $x000
2. `_compute_dl_segments()` — dzieli DL na 2 segmenty, każdy LMS na adresie $x000
3. `generate_asm_displaylist()` — generuje DL z `dta $4E/$4F, a(Label+offset)`

Parametr `--screen-base` (domyślnie 0x4000) — kluczowy dla poprawnego liczenia adresów bezwzględnych.

## PMG (Player/Missile Graphics)

- **Single-line resolution** (`DMA_PMG_ON=$3E`), `PMBASE_ADDR=$A000`
- Układ PMG: `MISSILES=$A300`, `PLAYER0=$A400`, `PLAYER1=$A500`, `PLAYER2=$A600`, `PLAYER3=$A700`
- Wszystkie rejestry zapisywane bezpośrednio do sprzętu (shadow nieużywane)
- 4 graczy (P0-P3) + missiles (M0-M3), PRIOR zależny od sceny
- Tytuł: x1 (`SIZEP0-3=$00`), `PRIOR=$11` (5th player), `COLPF3` dla missile
- Story/GameOver: PMG wyłączane (`GRACTL=0`, czyszczenie PMG)
- Dane sprite'ów transponowane z formatu wierszowego `[P0,P1,P2,P3,M]xN` do per-player

## DLI — sekcje

Projekt używa DLI w co najmniej dwóch scenach:

1. **Title**: DLI_Handler steruje kolorami, PRIOR i tęczą PMG (logo + księżyc/gwiazdy).
2. **GameOver**: DLI_Gameover przełącza paletę pomiędzy obrazkiem i migotaniem tekstu (efekt pulse/rainbow).
3. **Game**: Używa łańcucha dwóch DLI (przełączają się nawzajem na koniec swojego wykonania):
   - `game_dli_1`: ładuje 9-kolorową paletę (tło + PMG) odpowiadającą bieżącemu etapowi (od 0 do 4) oraz ustawia charset mapy na `CHBASE=$64`.
   - `game_dli_2`: uruchamia się przed strefą statusową, zmieniając kolory tekstu i tła oraz ładując czytelny charset `CHBASE=$60`.

System palet etapów oparty jest na szybkim indeksowaniu tablic konfiguracyjnych w trakcie startu sceny (`update_stage_colors`).

## Dopasowanie kolorów (CIELAB/CIE2000)

`rgb_to_atari()` używa rzeczywistej palety Atari PAL (256×RGB z `rgb2a8.cpp`), konwertuje do CIELAB i porównuje uproszczoną formułą CIE2000 (K1=0.045, K2=0.015). Znacznie lepsze perceptualnie niż odległość Euklidesowa w RGB.

## Znane pułapki

1. **Init scen i NMI**: `system_init` zeruje `DMACTL/NMIEN/GRACTL` przed wejściem do sceny. Każda scena musi jawnie przywrócić potrzebne ustawienia.
2. **Kolory bezpośrednio do GTIA**: `img2asm.py` generuje `sta $D016-$D01A` (nie shadow OS). Plik `_colors.asm` jest includowany globalnie (stałe `.equ`) i lokalnie w `_init` (kod `lda`/`sta`).
3. **DLI timing**: DMA kradnie cykle, więc punkty DLI muszą być testowane na docelowym emulatorze/sprzęcie.
4. **VRAM_ARENA ownership**: Title/Game/GameOver współdzielą ten sam bufor `$4000-$5E0F`; każda scena musi kompletnie odtworzyć własny ekran w `_init`.
5. **Wspólny bufor tekstu**: Story/GameOver/stopka Title współdzielą `$5E10-$5F4F`; przejścia scen nie mogą zakładać trwałości poprzedniej treści.
6. **MADS `OPT h+`**: MADS 2.1.6 wymaga wielkich liter dyrektyw i ostrożności przy wielu segmentach `org`.
