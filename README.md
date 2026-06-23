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
├── witcher.asm              # Główny kod asemblera (MADS)
├── dziki_zgon.xex           # Skompilowany plik wykonywalny
├── scripts/
│   └── img2asm.py           # Konwerter PNG/BMP/GIF → .bin + .asm + DL + kolory
├── img/
│   ├── title.png            # Obraz źródłowy ekranu tytułowego
│   ├── title-0.png          # Ekran tytułowy — wersja 0
│   ├── title-0a.png
│   ├── title-2.png
│   └── title-3.png
├── title-0.bin              # Surowe dane binarne ekranu (z paddingiem 4KB)
├── title-0.asm              # Dane .byte dla MADS
├── title-0_colors.asm       # Inicjalizacja rejestrów kolorów (COLBK, COLPF0–2)
└── title-0_displaylist.asm  # ANTIC Display List
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
# 1. Konwersja obrazów (generuje .bin, .asm, _colors.asm, _displaylist.asm)
python scripts/img2asm.py img/title-0.png 2 --all

# 2. Asemblacja
mads witcher.asm -o:dziki_zgon.xex

# 3. Uruchomienie w emulatorze
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
# Konwersja ekranu 160×192, 4 kolory — wszystkie pliki
python scripts/img2asm.py img/title-0.png 2 --all

# Tylko surowy .bin z kompresją RLE
python scripts/img2asm.py img/sprite.bmp 2 --bin -c rle

# Ekran przy adresie $8000
python scripts/img2asm.py img/title-0.png 2 --all --screen-base 0x8000

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

ANTIC E mapuje 2-bitowe indeksy pikseli na rejestry GTIA:

| Piksel | Rejestr | Adres |
|---|---|---|
| `00` | COLBK | `$D01A` |
| `01` | COLPF0 | `$D016` |
| `10` | COLPF1 | `$D017` |
| `11` | COLPF2 | `$D018` |

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
