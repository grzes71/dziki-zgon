# Wiedźmin: Dziki Zgon 🐺💀

Przygodowo-zręcznościowa gra z widokiem z góry na **Atari 800 XL / 65 XE** — humorystyczna parodia Wiedźmina.

## Fabuła

Po wielodniowej imprezie w karczmie „Pod Trzema Kuflami" wiedźmin **Gerwant** budzi się z potężnym kacem. Nie pamięta gdzie jest Płotka, gdzie są miecze, ani skąd wziął się rachunek na 18 000 orenów. Wyrusza w podróż przez 5 regionów, by odzyskać swój dobytek, wspomnienia i resztki godności.

## Założenia

- Gra działa na **gołym** Atari 800 XL / 65 XE z **64 KB RAM** — bez rozszerzeń pamięci, bez cartridge'ów.
- Obsługa wyłącznie **joysticka** i przycisku **FIRE** — bez klawiatury.
- Jeden plik wykonywalny `.XEX` ładowany z dowolnego DOS-a (lub bootowalny z dyskietki).
- Grafika w trybie **ANTIC E** (160×192, 4 kolory), ekrany przełączane po dojściu do krawędzi.
- Rozgrywka i sterowanie płynne w **50 FPS** (PAL).
- Kod pisany w asemblerze **MADS**, bez zależności od BASIC-a ani cartridge'ów.
- Szacowany rozmiar kodu + danych: do ~32 KB, reszta RAM na bufory, mapy i dźwięk.

## Struktura projektu

```
witcher-atari-game/
├── main.asm                     # Punkt startowy + maszyna stanów (title→story→game→gameover)
├── hardware.asm                 # Definicje rejestrów GTIA/ANTIC/POKEY i stałe
├── zeropage.asm                 # Zmienne page zero ($80–$81)
├── Makefile                     # Automatyzacja budowania
├── dziki_zgon.xex               # Skompilowany plik wykonywalny
├── lib/
│   └── pmg.asm                  # Procedury pomocnicze PMG
├── scenes/
│   ├── title/title.asm          # Ekran tytułowy (init + run + DLI + tęcza)
│   ├── story/story.asm          # Ekran opisu
│   ├── game/game.asm            # Gra właściwa
│   └── gameover/gameover.asm    # Ekran końca gry
├── gen/                         # Pliki generowane (nie commitować)
│   ├── title.bin                # Surowe dane binarne ekranu (z paddingiem 4KB)
│   ├── title.asm                # Dane .byte ekranu (MADS)
│   ├── title_colors.asm         # Kolory: stałe .equ (dla DLI) + kod init (lda/sta → GTIA)
│   ├── title_displaylist.asm    # ANTIC Display List (2 segmenty, LMS na $x000)
│   ├── moon.asm                 # Dane sprite'ów księżyca (24 wiersze × 4 bajty)
│   └── dziki-zgon.asm           # Dane sprite'ów napisu (37 wierszy × 5 bajtów)
├── scripts/
│   └── img2asm.py               # Konwerter PNG/BMP/GIF → .bin + .asm + DL + kolory
├── img/
│   ├── title.png                # Ekran tytułowy (160×192, 4 kolory)
│   ├── moon.png                 # Księżyc (32×24, 1 bpp, 4 graczy)
│   └── dziki-zgon.png           # Napis tytułowy (40×37, 1 bpp, 4 graczy + 5th)
├── docs/
│   └── KONSPEKT.md              # Dokument projektowy — fabuła, regiony, mechaniki
└── rgb2a8/                      # Referencyjna paleta Atari PAL (256 wartości RGB)
```

## Wymagania

| Narzędzie | Wersja | Uwagi |
|---|---|---|
| [MADS](https://mads.atari8.info/) | 2.1.x | Asembler 6502/65816 dla Atari 8-bit |
| [Python](https://www.python.org/) | 3.10+ | Do uruchamiania konwertera `img2asm.py` |
| [Pillow](https://python-pillow.org/) | 12.x | Biblioteka do przetwarzania obrazów |
| Emulator Atari | — | Np. [Altirra](https://www.virtualdub.org/altirra.html), Atari800 |

## Kompilacja

```bash
# Wszystko za jednym razem: sprite'y → tło → XEX
make

# Tylko konkretne cele
make sprites   # generuje gen/moon.asm + gen/dziki-zgon.asm
make bg        # generuje gen/title.bin + gen/title_colors.asm + gen/title_displaylist.asm
make clean     # usuwa katalog gen/ oraz plik XEX

# Zmiana obrazu tła
make clean BG_PREFIX=title-0a && make

# Uruchomienie w emulatorze
altirra dziki_zgon.xex
```

## Konwerter obrazów (`scripts/img2asm.py`)

```
python img2asm.py <obraz> <bpp> [opcje]

Argumenty:
  obraz              Plik PNG, BMP lub GIF
  bpp                1=2 kolory, 2=4 kolory, 4=16, 8=256

Opcje:
  --all              Generuj wszystkie formaty (.bin, .asm, _colors.asm, _displaylist.asm)
  --bin              Tylko surowy plik .bin
  --asm              Tylko dane .byte (MADS)
  --colors           Tylko plik z kolorami (_colors.asm)
  --dl               Tylko Display List (_displaylist.asm)
  --screen-base ADR  Adres bazowy ekranu (domyślnie: 0x4000)
  -c {rle,zx5}       Kompresja RLE lub ZX5
  -l N               Bajtów na linię w .byte (domyślnie: 8)
  --test             Uruchom testy jednostkowe DL
  -o NAZWA           Bazowa nazwa plików wyjściowych
```

### Przykłady

```bash
# Konwersja ekranu 160×192, 4 kolory — wszystkie pliki do katalogu gen/
mkdir -p gen
cd gen && python ../scripts/img2asm.py ../img/title.png 2 --all -o title --footer 0x5E10

# Sprite'y — same dane .byte (do katalogu gen/)
cd gen && python ../scripts/img2asm.py ../img/moon.png 1 --asm -o moon.asm -l 4
cd gen && python ../scripts/img2asm.py ../img/dziki-zgon.png 1 --asm -o dziki-zgon.asm -l 5

# Tylko surowy .bin z kompresją RLE
python scripts/img2asm.py img/sprite.bmp 2 --bin -c rle

# Testy algorytmu Display List
python scripts/img2asm.py --test
```

## Szczegóły techniczne

### Tryb graficzny

| Parametr | Wartość |
|---|---|
| Tryb ANTIC | **E** (Graphics 7) |
| Rozdzielczość | 160 × 192 pikseli |
| Kolory | 4 (2 bpp) |
| Bajtów na linię | 40 |
| Pamięć ekranu | $4000–$5E0F (7696 B z paddingiem) |
| Display List | $3000 |
| Kod programu | $2000 |

### Rejestry kolorów

ANTIC E mapuje 2-bitowe indeksy pikseli na rejestry GTIA.
Kolory zapisywane **bezpośrednio do sprzętu** (VBI OS wyłączony).
Plik `title_colors.asm` zawiera zarówno kod inicjalizacji, jak i stałe `.equ`
(`TITLE_COLBK`, `TITLE_COLPF0`–`TITLE_COLPF2`) do użycia w DLI.

| Piksel | Rejestr | Stała .equ | Adres |
|---|---|---|---|
| `00` | COLBK | `TITLE_COLBK` | `$D01A` |
| `01` | COLPF0 | `TITLE_COLPF0` | `$D016` |
| `10` | COLPF1 | `TITLE_COLPF1` | `$D017` |
| `11` | COLPF2 | `TITLE_COLPF2` | `$D018` |

### Rejestry sprzętowe (system wyłączony)

Program działa bez OS — `sei` + NMIEN=$80 (tylko DLI).
Wszystkie rejestry zapisywane bezpośrednio:

| Rejestr | Adres | Opis |
|---|---|---|
| DMACTL | `$D400` | Włączenie DMA ($3E = playfield + PMG single-line) |
| DLISTL/H | `$D402`/`$D403` | Adres Display List (sprzętowo, nie shadow!) |
| NMIEN | `$D40E` | $80 = tylko DLI, VBI wyłączony |
| IRQEN | `$D20E` | 0 = POKEY wyłączony |

### Obsługa granicy 4KB (ANTIC limitation)

ANTIC używa 12-bitowego licznika podczas pobierania linii — nie może przekroczyć granicy bloku 4KB (`$x000`). Konwerter automatycznie:

1. **Dodaje padding** (bajty `$00`) między liniami przy granicy 4KB
2. **Generuje 2-segmentową Display List** — każdy segment zaczyna LMS od równego adresu `$x000`
3. Efekt: **zero artefaktów**, wszystkie 192 linie wyświetlone poprawnie

```
Segment 1: LMS=$4000  →  102 linie (0–101)  →  $4000–$4FE7
Padding:                →   16 bajtów $00    →  $4FF0–$4FFF
Segment 2: LMS=$5000  →   90 linii (102–191) →  $5000–$5E0F
```

### Format danych obrazu

- Pakowanie **MSB-first** (lewy piksel w najstarszych bitach)
- 2 bpp: 4 piksele na bajt — `[7:6][5:4][3:2][1:0]`
- 1 bpp: 8 pikseli na bajt — `[7][6][5][4][3][2][1][0]`

### Kompresja RLE

Dostępna opcjonalna kompresja danych ekranu:

```
python scripts/img2asm.py img/title-0.png 2 --bin -c rle
```

Generuje plik `.rle` oraz depacker 6502 (`_rle_depack.asm`).

Format RLE:
- `$00–$7F` → ciąg N+1 literałów
- `$80–$FF` → powtórzenie bajta N−127 razy

## Licencja

Projekt hobbystyczny — do użytku niekomercyjnego.
