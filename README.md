# Wiedźmin: Dziki Zgon 🐺💀

Przygodowo-zręcznościowa gra z widokiem z góry na **Atari 800 XL / 65 XE** — humorystyczna parodia Wiedźmina.

## Fabuła

Po wielodniowej imprezie w karczmie "Pod Trzema Kuflami" wiedźmin **Gerwant** budzi się z potężnym kacem. Nie pamięta gdzie jest Plotka, gdzie są miecze, ani skąd wziął się rachunek na 18 000 orenów. Wyrusza w podróż przez 5 regionów, by odzyskać swój dobytek, wspomnienia i resztki godności.

## Development z AI agentami

Agent AI powinien przeczytać oraz postępować wg zasad umieszczonych w pliku [profile.md](.agent/profile.md).

Kontekst techniczny jest także zawarty w pliku [AI_CONTEXT.md](AI_CONTEXT.md).

## Założenia

- Gra działa na **gołym** Atari 800 XL / 65 XE z **64 KB RAM** — bez rozszerzeń pamięci, bez cartridge'ów.
- Obsługa wyłącznie **joysticka** i przycisku **FIRE** — bez klawiatury.
- Jeden plik wykonywalny `.XEX` ładowany z dowolnego DOS-a (lub bootowalny z dyskietki).
- Grafika w trybach **ANTIC E** (tytuł), **ANTIC D** (game over, narrow playfield 128 px), **ANTIC 2** / **ANTIC 3** (ekran opisu / tekst game over) oraz **ANTIC 4** (rozgrywka).
- Rozgrywka i sterowanie płynne w **50 FPS** (PAL).
- Kod pisany w asemblerze **MADS**, bez zależności od BASIC-a ani cartridge'ów.
- Szacowany rozmiar kodu + danych: do ~32 KB, reszta RAM na bufory, mapy i dźwięk.

## Struktura projektu

```
witcher-atari-game/
├── main.asm                     # Punkt startowy + maszyna stanów (title→story→game→gameover)
├── hardware.asm                 # Definicje rejestrów GTIA/ANTIC/POKEY i stałe
├── zeropage.asm                 # Zmienne page zero ($80–$85)
├── Makefile                     # Automatyzacja budowania
├── dziki_zgon.xex               # Skompilowany plik wykonywalny
├── requirements.txt              # Zależności Pythona (Pillow)
├── lib/
│   ├── pmg.asm                  # Procedury pomocnicze PMG
│   └── rle.asm                  # Wspólny dekompresor RLE (6502)
├── music/                       # Silnik audio i utwory muzyczne
│   ├── title.sap                # Oryginalny plik muzyki w formacie ASAP (.sap)
│   ├── audio.asm                # Integracja odtwarzacza w VBI, start/stop, wyciszanie POKEY
│   ├── rmt_feat.asm             # Konfiguracja funkcji (features) odtwarzacza RMT
│   └── rmtplayr.asm             # Kod asemblera odtwarzacza RMT (mono, relocatable)
├── scenes/
│   ├── title/title.asm          # Ekran tytułowy (init + run + DLI + tęcza)
│   ├── story/story.asm          # Ekran opisu (dekompresja story do stopki)
│   ├── game/game.asm            # Gra właściwa
│   └── gameover/gameover.asm    # Ekran końca gry (ANTIC D narrow + ANTIC 3 tęcza)
├── gen/                         # Pliki generowane (nie commitować)
│   ├── title.bin                # Surowe dane binarne ekranu tytułu
│   ├── title.asm                # Dane .byte ekranu tytułu (MADS)
│   ├── title_colors.asm         # Kolory tytułu: stałe .equ + kod init
│   ├── title_displaylist.asm    # ANTIC Display List tytułu (2 segmenty)
│   ├── title_music.asm          # Skonwertowany moduł muzyczny MADS (title.sap -> title_music.asm)
│   ├── rmtplayr.asm             # Skonwertowany kod playera RMT (MADS)
│   ├── gameover.bin             # Surowe dane binarne ekranu game over
│   ├── gameover.asm             # Dane .byte ekranu game over (MADS)
│   ├── gameover_colors.asm      # Kolory game over: stałe .equ + kod init
│   ├── gameover_displaylist.asm # ANTIC Display List game over (ANTIC D)
│   ├── moon.asm                 # Sprite księżyca (MADS)
│   └── dziki-zgon.asm           # Sprite logo (MADS)
├── texts/
│   ├── story.txt                # Źródłowy tekst fabuły (ASCII)
│   └── gameover.txt             # Źródłowy tekst końca gry (ASCII)
├── fonts/
│   └── font.asm                 # Własna czcionka 128 znaków (1 KB, $6000)
├── scripts/
│   ├── atasm2mads.py            # Konwerter kodu asemblera z ATasm na dyrektywy MADS (odtwarzacz + muzyka)
│   ├── fnt2asm.py               # Konwerter plików czcionek (.fnt) na dane asemblera MADS (.asm)
│   ├── fnt2png.py               # Konwerter pliku czcionki (.fnt) na podgląd obrazu PNG (8x8)
│   ├── png2fnt.py               # Konwerter siatki znaków PNG na plik binarny czcionki (.fnt)
│   ├── img2asm.py               # Konwerter PNG/BMP/GIF → .bin + .asm + DL + kolory
│   ├── rle_compress_text.py     # Skrypt do kodowania i kompresji tekstów RLE
│   └── cleanup_docs.py          # Skrypt pomocniczy do porządkowania dokumentacji projektu
├── img/
│   ├── title.png                # Ekran tytułowy (160×192, 4 kolory)
│   ├── game-over.png            # Ekran game over (128×96, 4 kolory)
│   ├── moon.png                 # Księżyc (32×24, 1 bpp, 4 graczy)
│   └── dziki-zgon.png           # Napis tytułowy (40×37, 1 bpp, 4 graczy + 5th)
├── docs/
│   ├── KONSPEKT.md              # Dokument projektowy — fabuła, regiony, mechaniki
│   └── py65.md                  # Dokumentacja emulatora Py65 (6502 w Pythonie)
├── tests/                       # Testy jednostkowe i integracyjne (Py65)
└── rgb2a8/                      # Referencyjna paleta Atari PAL (256 wartości RGB)
```

## Wymagania

| Narzędzie | Wersja | Uwagi |
|---|---|---|
| [MADS](https://mads.atari8.info/) | 2.1.x | Asembler 6502/65816 dla Atari 8-bit |
| [Python](https://www.python.org/) | 3.10+ | Do uruchamiania konwertera `img2asm.py` |
| [Pillow](https://python-pillow.org/) | 12.x | Biblioteka do przetwarzania obrazów (`pip install -r requirements.txt`) |
| Emulator Atari | — | Np. [Altirra](https://www.virtualdub.org/altirra.html), Atari800 |
| [Atari Image Converter](https://github.com/grzes71/py-image-converter/#atari-image-converter) | — | Konwersja obrazów na formaty Atari (PNG → GR7, GR8, MIC, i inne) |
| [html-to-markdown](https://github.com/grzes71/html-to-markdown#html-to-markdown) | — | Konwersja dokumentacji HTML do Markdown
| [py65](https://github.com/mnaberez/py65) | — | Emulator 6502 w Pythonie do testów (`pip install -r requirements.txt`) |

## Kompilacja

```bash
# Wszystko za jednym razem: sprite'y → tło → XEX
make

# Tylko konkretne cele
make sprites   # generuje gen/moon.asm + gen/dziki-zgon.asm
make bg        # generuje gen/title.bin + gen/title_colors.asm + gen/title_displaylist.asm
make music     # konwertuje muzykę: music/title.sap -> gen/title_music.asm + music/rmtplayr.asm -> gen/rmtplayr.asm
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
  -c {rle}           Wybór kompresji (RLE)
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

# Tylko dane .byte z kompresją RLE
python scripts/img2asm.py img/sprite.bmp 2 --asm -c rle

# Testy algorytmu Display List
python scripts/img2asm.py --test
```

## Szczegóły techniczne

### Tryb graficzny

| Parametr | Tytuł | Story | Gra właściwa | Game Over |
|---|---|---|---|---|
| Tryb ANTIC | **E** (Graphics 7) | **2** (Graphics 0) | **4** (Graphics 12) | **D** (Graphics 7 narrow) + **3** (tekst) |
| Rozdzielczość | 160 × 192 px | 40 × 24 znaków (8×8 px) | 40 × 24 znaków (4×8 px) | 128 × 96 px + 32 znaki tekstu |
| Kolory | 4 (2 bpp) | 1 + COLBK (biały na czarnym) | 4 + COLBK | 4 (2 bpp) + DLI tęcza |
| Pamięć ekranu | $4000–$5E0F (7696 B) | $5E10–$5F4F (320 B, RLE) | $4000–$43BF (960 B) | $7000–$7ADF (2784 B) + $7C00 tekst |
| Charset | $6000–$63FF (font.asm) | $6000–$63FF (font.asm) | $A800–$ABFF (kafelki terenu) | $6000–$63FF (font.asm) |
| Display List | $3E80 | $3E80 | $3E80 | $3E80 |
| Kod programu | $2000 | $2000 | $2000 | $2000 |
| PORTB | $FF — BASIC off, OS on | ← | ← | ← |
| Czcionka | CHBASE=$60 | CHBASE=$60 | CHBASE=$A8 | CHBASE=$60 |

### Rejestry kolorów

**ANTIC E** mapuje 2-bitowe indeksy pikseli na rejestry GTIA.
Kolory zapisywane **bezpośrednio do sprzętu** (VBI OS wyłączony).
Plik `title_colors.asm` zawiera zarówno kod inicjalizacji, jak i stałe `.equ`
(`TITLE_COLBK`, `TITLE_COLPF0`–`TITLE_COLPF2`) do użycia w DLI.

**ANTIC 4** (gra): każdy znak używa 4 kolorów — bity w definicji znaku
wybierają COLBK (00), COLPF0 (01), COLPF1 (10) lub COLPF2 (11).
COLPF3 dostępny jako 5. kolor (bit 7 kodu znaku) lub dla PMG.

| Piksel | Rejestr | Stała .equ | Adres |
|---|---|---|---|
| `00` | COLBK | `TITLE_COLBK` | `$D01A` |
| `01` | COLPF0 | `TITLE_COLPF0` | `$D016` |
| `10` | COLPF1 | `TITLE_COLPF1` | `$D017` |
| `11` | COLPF2 | `TITLE_COLPF2` | `$D018` |

### Rejestry sprzętowe (przerwania systemowe)

Program działa przy włączonym OS ROM, obsługując przerwania NMI (DLI + VBI) w celu koordynacji odtwarzacza muzycznego. Odtwarzacz jest podpięty pod Immediate VBLANK (`$0222`), co gwarantuje stabilne odtwarzanie muzyki w tle i zapobiega blokadzie za pośrednictwem systemowej flagi `CRITIC`.

Wszystkie rejestry sprzętowe są modyfikowane bezpośrednio:

| Rejestr | Adres | Opis |
|---|---|---|
| DMACTL | `$D400` | Włączenie DMA ($3E = playfield + PMG single-line) |
| DLISTL/H | `$D402`/`$D403` | Adres Display List (sprzętowo, nie shadow!) |
| NMIEN | `$D40E` | $C0 = włączony DLI oraz VBI (niezbędny do muzyki) |
| IRQEN | `$D20E` | 0 = IRQ wyłączone (blokada za pomocą `sei` + rejestr IRQEN) |

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

Dostępna opcjonalna kompresja danych ekranu (obrazów) oraz tekstów (przez dedykowane skrypty w `scripts/`):

```bash
# Kompresja tła/sprite'ów z opcją RLE:
python scripts/img2asm.py img/title.png 2 --asm -c rle

# Kompresja tekstów:
python scripts/rle_compress_text.py -i story -o gen/story_text.asm
```

Gra wykorzystuje wspólny depacker 6502 zdefiniowany w [lib/rle.asm](lib/rle.asm).

Format RLE (PackBits + marker EOF):
- `$00–$7F` → ciąg `cmd + 1` literałów (1..128)
- `$80`     → znacznik końca danych (EOF)
- `$81–$FF` → powtórzenie kolejnego bajtu `(cmd & $7F) + 1` razy (2..128)

## Testowanie z Py65

Projekt używa [py65](https://github.com/mnaberez/py65) — emulatora 6502 w Pythonie — do testowania kodu asemblerowego bez uruchamiania pełnego emulatora Atari.

### Instalacja

```bash
pip install -r requirements.txt
```

### Uruchomienie monitora

```bash
py65mon
```

### Podstawowe komendy

| Komenda | Opis |
|---|---|
| `load "dziki_zgon.xex" 0` | Ładuje plik `.xex` pod adres `$0000` |
| `registers` | Wyświetla stan rejestrów (PC, A, X, Y, SP, flags) |
| `disassemble $2000:$2100` | Deasembluje kod w podanym zakresie |
| `mem $4000:$4040` | Wyświetla zawartość pamięci |
| `add_breakpoint $2060` | Ustawia pułapkę (breakpoint) na adresie |
| `goto $2000` | Uruchamia wykonanie od adresu |
| `step` | Wykonuje jedną instrukcję (krok) |
| `fill $4000:$5FFF 0` | Wypełnia zakres zerami |
| `help` | Lista wszystkich komend |

### Przykład sesji testowej

```bash
py65mon
.load "dziki_zgon.xex" 0        # ładuje plik XEX
.add_breakpoint $2060            # pułapka w title_init
.goto $2000                      # start od jmp start
registers                        # sprawdź stan po pułapce
disassemble $2000:$2100          # podejrzyj kod
mem $4000:$4040                  # pierwsze linie ekranu
step                             # wykonaj krok
```

Pełna dokumentacja: [`docs/py65.md`](docs/py65.md)

## Licencja

Projekt hobbystyczny — do użytku niekomercyjnego.
