# AI Context — Wiedźmin: Dziki Zgon

## Projekt

Gra przygodowo-zręcznościowa na Atari 800 XL / 65 XE (64 KB RAM), humorystyczna parodia Wiedźmina. Widok z góry, ekrany przełączane krawędziowo, sterowanie joystick + FIRE.

## Pliki kluczowe

| Plik | Rola |
|---|---|
| `witcher.asm` | Główny kod asemblera (MADS), kompilowany do `dziki_zgon.xex` |
| `scripts/img2asm.py` | Konwerter PNG → .bin + .asm + _colors.asm + _displaylist.asm |
| `title-0a.bin` | Dane ekranu (7696 B z paddingiem 4KB) |
| `title-0a_colors.asm` | Inicjalizacja kolorów playfieldu (bezpośrednio GTIA $D016-$D01A) |
| `title-0a_displaylist.asm` | ANTIC Display List (2 segmenty, LMS na $x000) |
| `dziki-zgon.asm` | Dane sprite'ów PMG (37 wierszy × 5 bajtów, 1 bpp) |
| `docs/KONSPEKT.md` | Dokument projektowy — fabuła, regiony, mechaniki |

## Build

```bash
make          # wszystko: sprite'y → tło → XEX
make sprites  # tylko moon + dziki-zgon
make bg       # tylko tło
make clean    # usuwa wygenerowane
```

Wymagania: Python 3.10+, Pillow 12.x, MADS 2.1.x, GNU Make.

## Tryb graficzny

- **ANTIC E** (Graphics 7), 160×192 px, 4 kolory (2 bpp), 40 B/linia
- Kolory: indeks 0→COLBK, 1→COLPF0, 2→COLPF1, 3→COLPF2
- Generator `_colors.asm` zapisuje **bezpośrednio do GTIA** ($D016-$D01A) — VBI wyłączony

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
- **System wyłączony**: `sei` + `IRQEN=0`, NMIEN=$80 (tylko DLI, bez VBI OS)
- Wszystkie rejestry zapisywane bezpośrednio do sprzętu (shadow nieużywane)
- 4 graczy (P0–P3) + missiles (M0–M3), PRIOR sterowany przez DLI
- Tytuł: x2 (SIZEP0–3=$01), PRIOR=$11 (5th player), COLPF3 dla missile
- Księżyc + gwiazdy: x1 (SIZEP=$00), PRIOR=$01 (bez 5th player, niezależne HPOSM)
- Gwiazdy dzielą kolor księżyca ($40) — PCOLR0-3 wspólne
- **Missile HPOS w odwrotnej kolejności**: M3(lewy)→M2→M1→M0(prawy), odstęp +2
- Dane sprite'ów transponowane z formatu wierszowego `[P0,P1,P2,P3,M]×37` do per-player
- Pozycje tytułu: $30, $40, $50, $60, $70 (co 16 color clocków przy x2)

## DLI — sekcje

DLI odpala na `DLIST+2` (ostatnia pusta linia $70 przed trybem E) — brak DMA, pełne CPU.

1. **Tytuł**: SIZEP=x2, HPOSP=$30/$40/$50/$60, PRIOR=$11, 37 linii tęczy (RainbowColors → PCOLR0-3 + COLPF3)
2. **Po tęczy**: PRIOR=$01, PCOLR=$40, SIZEP=1x — wspólne dla gwiazd i księżyca
3. **Gwiazdy**: HPOSM = STARn_X (niezależne pozycje missile)
4. **Księżyc**: HPOSP = MOON_X+0/8/16/24, HPOSM = STARn_X (odświeżone)

KOREKTA=8 — dostrojone doświadczalnie dla DLI_DELAY.

## Dopasowanie kolorów (CIELAB/CIE2000)

`rgb_to_atari()` używa rzeczywistej palety Atari PAL (256×RGB z `rgb2a8.cpp`), konwertuje do CIELAB i porównuje uproszczoną formułą CIE2000 (K1=0.045, K2=0.015). Znacznie lepsze perceptualnie niż odległość Euklidesowa w RGB.

## Znane pułapki

1. **System OFF**: `sei` + `IRQEN=0`, NMIEN=$80 (tylko DLI), DMACTL=$3E, DLISTL/DLISTH hardware ($D402/$D403)
2. **Kolory bezpośrednio do GTIA**: `img2asm.py` generuje `sta $D016-$D01A` (nie shadow $02C4-$02C8) — VBI nie kopiuje
3. **PMG blank offset**: PMG counter start = TV line 8, liczy też puste linie DL ($70×3=24)
4. **DLI timing**: DMA kradnie cykle → DLI na pustej linii, nie na trybie z DMA
5. **MADS `OPT h+`**: MADS 2.1.6 wymaga wielkich liter
6. **GitHub push email**: używać `users.noreply.github.com`
