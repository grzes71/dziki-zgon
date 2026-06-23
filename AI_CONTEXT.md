# AI Context — Wiedźmin: Dziki Zgon

## Projekt

Gra przygodowo-zręcznościowa na Atari 800 XL / 65 XE (64 KB RAM), humorystyczna parodia Wiedźmina. Widok z góry, ekrany przełączane krawędziowo, sterowanie joystick + FIRE.

## Pliki kluczowe

| Plik | Rola |
|---|---|
| `witcher.asm` | Główny kod asemblera (MADS), kompilowany do `dziki_zgon.xex` |
| `scripts/img2asm.py` | Konwerter PNG → .bin + .asm + _colors.asm + _displaylist.asm |
| `title-0a.bin` | Dane ekranu (7696 B z paddingiem 4KB) |
| `title-0a_colors.asm` | Inicjalizacja kolorów playfieldu (shadow registers $02C4-$02C8) |
| `title-0a_displaylist.asm` | ANTIC Display List (2 segmenty, LMS na $x000) |
| `dziki-zgon.asm` | Dane sprite'ów PMG (37 wierszy × 5 bajtów, 1 bpp) |
| `docs/KONSPEKT.md` | Dokument projektowy — fabuła, regiony, mechaniki |

## Build

```bash
python scripts/img2asm.py img/title-0a.png 2 --all -o title-0a
mads witcher.asm -o:dziki_zgon.xex
```

Wymagania: Python 3.10+, Pillow 12.x, MADS 2.1.x.

## Tryb graficzny

- **ANTIC E** (Graphics 7), 160×192 px, 4 kolory (2 bpp), 40 B/linia
- Kolory: indeks 0→COLBK, 1→COLPF0, 2→COLPF1, 3→COLPF2
- **Uwaga**: generator `_colors.asm` zapisuje do shadow registers ($02C4–$02C8), nie bezpośrednio do GTIA

## Mapa pamięci

| Adres | Zawartość |
|---|---|
| $2000–$2FFF | Kod programu, DLI handler, tabele |
| $3000–$30FF | Display List |
| $4000–$5E0F | Dane ekranu (z paddingiem 16 B przy $4FF0) |
| $8000–$87FF | PMG (1K-aligned): $8300=missiles, $8400=P0, $8500=P1, $8600=P2, $8700=P3 |

## Display List — generator i ograniczenia ANTIC

ANTIC ma 12-bitowy licznik adresu podczas pobierania linii → nie może przekroczyć granicy 4KB ($x000→$y000). `img2asm.py` rozwiązuje to przez:

1. `pack_pixels()` — dodaje padding ($00) przy granicach 4KB, wyrównując kolejną linię do $x000
2. `_compute_dl_segments()` — dzieli DL na 2 segmenty, każdy LMS na adresie $x000
3. `generate_asm_displaylist()` — generuje DL z `dta $4E/$4F, a(Label+offset)`

Parametr `--screen-base` (domyślnie 0x4000) — kluczowy dla poprawnego liczenia adresów bezwzględnych.

## PMG (Player/Missile Graphics)

- **Single-line resolution** (DMACTL bit 4=$10), PMBASE=$8000
- 4 graczy (P0–P3) + missiles jako 5. gracz (PRIOR=$11)
- Gracze x2 (SIZEP0–3=$01), białe (PCOLR0–3=$0E, shadow $02C0–$02C3)
- 5. gracz: kolor z COLPF3 ($D019, shadow $02C7), missiles w jednym bajcie na linię
- **Missile HPOS w odwrotnej kolejności**: M3(lewy)→M2→M1→M0(prawy), odstęp +2
- **SIZEM nie wpływa na odstępy** w trybie 5th player
- Dane sprite'ów transponowane z formatu wierszowego `[P0,P1,P2,P3,M]×37` do per-player
- Pozycje: $30, $40, $50, $60, $70 (co 16 color clocków przy x2)

## DLI Rainbow

- DLI na `DLIST+2` (ostatnia pusta linia $70) — **nie** na pierwszej linii trybu E (DMA opóźnia CPU)
- Handler czeka `DLI_DELAY = TOP_MARGIN - DL_BLANKS - KOREKTA` linii przez WSYNC
- Potem 37 linii zmienia PCOLR0–3 + COLPF3 z tabeli `RainbowColors`
- KOREKTA=8 — dostrojone doświadczalnie
- Kolory w DLI zapisywane **bezpośrednio do GTIA** (shadow nie są potrzebne — VBI jeszcze nie nadpisało)

## Dopasowanie kolorów (CIELAB/CIE2000)

`rgb_to_atari()` używa rzeczywistej palety Atari PAL (256×RGB z `rgb2a8.cpp`), konwertuje do CIELAB i porównuje uproszczoną formułą CIE2000 (K1=0.045, K2=0.015). Znacznie lepsze perceptualnie niż odległość Euklidesowa w RGB.

## Znane pułapki

1. **Shadow registers**: PCOLR0–3 ($02C0–$02C3), PRIOR ($026F), COLPF3 ($02C7), playfield colors ($02C4–$02C8) — VBI nadpisuje hardware z shadow
2. **PMG blank offset**: PMG counter start = TV line 8, liczy też puste linie DL ($70×3=24)
3. **DLI timing**: DMA kradnie cykle → DLI na pustej linii, nie na trybie z DMA
4. **MADS string constants**: brak konkatenacji dla `icl`/`ins` — używać komentarzy `SCREEN_PREFIX`
5. **GitHub push email**: używać `users.noreply.github.com`
6. **`OPT h+`**: MADS 2.1.6 wymaga wielkich liter `OPT`, małe `opt` może powodować "Undeclared macro H"
