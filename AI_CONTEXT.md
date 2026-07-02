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
| `scripts/img2asm.py` | Konwerter PNG → .bin + .asm + _colors.asm + _displaylist.asm |
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

## Tryb graficzny

- **ANTIC E** (Graphics 7), 160×192 px, 4 kolory (2 bpp), 40 B/linia — ekran tytułowy, gameover
- **ANTIC 2** (Graphics 0), 40×24 znaków (rozszerzony liniami pustymi $70 w display liście), 1 kolor (biały na czarnym, COLPF1=$0E), 320 B ekranu na $5E10 — współdzielony ekran opisu (story) i stopek
- **ANTIC 5 + ANTIC 2** (Split screen) — gra właściwa: górne 9 linii w trybie ANTIC 5 (znakowy, 4 kolory, podwójna wysokość - 16 scanlinii na znak, 360 B), dolne 6 linii w trybie ANTIC 2 (znakowy, 1 kolor, 8 scanlinii na znak, 240 B). Razem 600 B ekranu gry.
- Kolory: indeks 0→COLBK, 1→COLPF0, 2→COLPF1, 3→COLPF2
- Generator `_colors.asm` zapisuje **bezpośrednio do GTIA** ($D016-$D01A) — VBI wyłączony. Zawiera też stałe `.equ` (`TITLE_COLBK`, `TITLE_COLPF0`–2) do użycia w DLI — plik includowany globalnie (dla stałych) i lokalnie w `_init` (dla `lda`/`sta`)

## Mapa pamięci

Szczegółowa mapa pamięci, wolnych bloków oraz objaśnienia znajdują się w dedykowanym dokumencie [MEMORY_USAGE.md](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/MEMORY_USAGE.md). Skrócony podział pamięci:

| Adres | Zawartość |
|---|---|
| $0080–$0081 | Page zero: SRC_TMP ($80), GAME_STATE ($81) |
| $2000–$2FFF | Kod: main + lib/pmg + scenes/* + dane sprite'ów (~1.2 KB) |
| $3000–$30FF | Display List (title, story, game, gameover — każda oddzielna etykieta) |
| $4000–$5E0F | **VRAM_ARENA** (7.7 KB) — współdzielony bufor ekranu (nadpisywany przy przejściu między scenami) |
| $5E10–$5FFF | Współdzielony bufor tekstowy (ANTIC mode 2, 8 linii × 40 znaków) dla stopek i Story |
| $6000–$63FF | **Czcionka własna** — `fonts/font.asm`, 128 znaków × 8 B (1 KB) — CHBASE=$60 |
| $6400–$7FFF | **WOLNE (7 KB)** — odzyskane dzięki VRAM_ARENA, doskonałe na logikę gry |
| $8000–$87FF | Skompresowane wideo (ROM_DATA: title.rle, gameover.rle) oraz początek PMG (1K-aligned) |
| $A000–$A3FF | **Charset gry** — kafelki terenu (1 KB, ANTIC 4, CHBASE=$A0) |
| $A400–$BFFF | Wolne (7 KB) — mapy regionów, dane gry |

> PORTB=$FD — tylko BASIC wyłączony (8 KB zysk). OS ROM włączony → NMI działa normalnie przez OS. `jmp start` na $2000 zamiast `run start` (MADS domyślnie startuje od pierwszego `org`).

## Display List — generator i ograniczenia ANTIC

ANTIC ma 12-bitowy licznik adresu podczas pobierania linii → nie może przekroczyć granicy 4KB ($x000→$y000). `img2asm.py` rozwiązuje to przez:

1. `pack_pixels()` — dodaje padding ($00) przy granicach 4KB, wyrównując kolejną linię do $x000
2. `_compute_dl_segments()` — dzieli DL na 2 segmenty, każdy LMS na adresie $x000
3. `generate_asm_displaylist()` — generuje DL z `dta $4E/$4F, a(Label+offset)`

Parametr `--screen-base` (domyślnie 0x4000) — kluczowy dla poprawnego liczenia adresów bezwzględnych.

## PMG (Player/Missile Graphics)

- **Single-line resolution** (DMACTL bit 4=$10), PMBASE=$8000
- **System wyłączony**: `sei` + `IRQEN=0`, NMIEN=$80 (tylko DLI, bez VBI OS). PORTB=$FD (BASIC off, OS ROM on — NMI przez OS)
- Wszystkie rejestry zapisywane bezpośrednio do sprzętu (shadow nieużywane)
- 4 graczy (P0–P3) + missiles (M0–M3), PRIOR sterowany przez DLI
- Tytuł: x1 (SIZEP0–3=$00), PRIOR=$11 (5th player), COLPF3 dla missile
- Księżyc + gwiazdy: x1 (SIZEP=$00), PRIOR=$01 (bez 5th player, niezależne HPOSM)
- Gwiazdy dzielą kolor księżyca ($40) — PCOLR0-3 wspólne
- **Missile HPOS w odwrotnej kolejności**: M3(lewy)→M2→M1→M0(prawy), odstęp +2
- Dane sprite'ów transponowane z formatu wierszowego `[P0,P1,P2,P3,M]×37` do per-player
- Pozycje tytułu: $30, $38, $40, $48, $50 (co 8 color clocków przy x1)

## DLI — sekcje (tylko tytuł)

DLI odpala na `DLIST+2` (ostatnia pusta linia $70 przed trybem E) — brak DMA, pełne CPU. Gra nie używa DLI.

1. **Kolory tła**: COLPF0–2 + COLBK ustawiane ze stałych `TITLE_*` z `title_colors.asm` (generowane z obrazka)
2. **Tytuł**: SIZEP=x1, HPOSP=$30/$38/$40/$48, PRIOR=$11, 37 linii tęczy (RainbowColors → PCOLR0-3 + COLPF3)
3. **Po tęczy**: PRIOR=$01, PCOLR=$40, SIZEP=1x — wspólne dla gwiazd i księżyca
4. **Gwiazdy**: HPOSM = STARn_X (niezależne pozycje missile)
5. **Księżyc**: HPOSP = MOON_X+0/8/16/24, HPOSM = STARn_X (odświeżone)

KOREKTA=8 — dostrojone doświadczalnie dla DLI_DELAY.

## Dopasowanie kolorów (CIELAB/CIE2000)

`rgb_to_atari()` używa rzeczywistej palety Atari PAL (256×RGB z `rgb2a8.cpp`), konwertuje do CIELAB i porównuje uproszczoną formułą CIE2000 (K1=0.045, K2=0.015). Znacznie lepsze perceptualnie niż odległość Euklidesowa w RGB.

## Znane pułapki

1. **System OFF**: `sei` + `IRQEN=0`, `PORTB=$FD` (tylko BASIC off, OS ROM on), NMIEN=$80 (tylko DLI), DMACTL=$3E, DLISTL/DLISTH hardware ($D402/$D403). Entry point: `jmp start` na $2000 — nie używaj `run start` przy wielu `org` (MADS generuje błędne adresy INIT/RUN)
2. **Kolory bezpośrednio do GTIA**: `img2asm.py` generuje `sta $D016-$D01A` (nie shadow $02C4-$02C8) — VBI nie kopiuje. Plik `_colors.asm` includowany **dwukrotnie**: globalnie (dla stałych `.equ` widocznych w DLI) i wewnątrz `_init` (dla kodu `lda`/`sta`)
3. **PMG blank offset**: PMG counter start = TV line 8, liczy też puste linie DL ($70×3=24)
4. **DLI timing**: DMA kradnie cykle → DLI na pustej linii, nie na trybie z DMA
5. **MADS `OPT h+`**: MADS 2.1.6 wymaga wielkich liter
6. **Współdzielona Arena VRAM**: Wprowadzono VRAM_ARENA na $4000. Sceny tytułu, gry i game over w pełni nadpisują tę arenę, a ciężkie bitmapy (.rle) są przechowywane skompresowane w wolnym RAM-ie ($8000+) i rozpakowywane na bieżąco za pomocą RLE_Depack. Tekst stopki/story/gameover współdzieli bufor na $5E10. Dzięki temu odzyskano całą pamięć od $6400 do $7FFF!
