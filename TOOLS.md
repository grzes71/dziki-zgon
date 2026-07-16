# Narzędzia i Skrypty — Wiedźmin: Dziki Zgon

Projekt używa szeregu dedykowanych narzędzi (napisanych w Pythonie) do przygotowania zasobów graficznych, tekstowych oraz całego świata gry, by zamienić je w dane binarne zdatne dla układu 6502 (Atari 8-bit).

Poniżej znajduje się pełna lista wraz ze szczegółowym opisem wywołania.

---

## 1. Konwerter obrazów (`scripts/img2asm.py`)

Główne narzędzie odpowiedzialne za konwersję plików wejściowych (PNG, BMP, GIF) na surowe dane ekranu, kody źródłowe kolorów oraz Display Listy zgodne z układem graficznym ANTIC.

```
python img2asm.py <obraz> <bpp> [opcje]

Argumenty:
  obraz              Plik PNG, BMP lub GIF
  bpp                1=2 kolory, 2=4 kolory, 4=16, 8=256

Opcje:
  --all              Generuj wszystkie formaty (.bin, .asm, _colors.asm, _displaylist.asm; przy -c rle także .rle)
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

---

## 2. World Builder (`world_builder/`)

Dedykowany kompilator (moduł Pythona) tłumaczący pliki w formacie SSOT (Single Source of Truth) oparte o język YAML bezpośrednio na kod asemblera zoptymalizowany pod 6502. Obejmuje rygorystyczne sprawdzanie integralności oraz logikę wyliczania przesunięć krawędziowych (border overflow clipping).

- Wywołanie: `python -m world_builder <input_dir> <output_dir>`
- (Automatycznie używany przez komendę `make world`)

---

## 3. World Studio (`world_studio/`)

Zaawansowany, napisany w `PySide6` edytor graficzny z widokiem map świata. Służy do modyfikowania regionów i ekranów bez obawy o błędy składniowe YAML.
Pozwala na:
- Operacje kładzenia kafelków (pędzel z wsparciem komendy `repeat-x` oraz `repeat-y` do powtarzania bloków).
- Ustawienie markera pozycji Gracza (Player Start) jednym przyciskiem.
- Automatyczne renderowanie siatki ekranów zależnych po kompasowych współrzędnych (`north, south, east, west`).
- Wywołanie: `python -m world_studio.main`

---

## 4. Object Studio (`object_studio/`)

Aplikacja graficzna (także w `PySide6`) dedykowana edycji surowych obiektów zdefiniowanych z pojedynczych znaczków czcionki Atari 4x8 px. Zapisuje bazowy manifest `objects.yaml`. Posiada rozbudowany interfejs malowania pikseli i wyboru barw uwzględniający specyfikację inwersji antycznej (`ANTIC 4/5` - bit siódmy `INV`).
- Wywołanie: `python -m object_studio.main`

---

## 5. Kompresor tekstu RLE (`scripts/rle_compress_text.py`)

Optymalizuje długie bloki tekstowe ucinając puste przestrzenie oraz powtórzenia znaków na podstawie algorytmu kompresji zaimplementowanego w silniku `lib/rle.asm`.
- Wywołanie: `python scripts/rle_compress_text.py -i <input_file> -o <output_file>`

---

## 6. Narzędzia czcionkowe

Służą do konwersji i wymiany krojów pisma pomiędzy Atari Font Maker a projektem:
- **`scripts/fnt2asm.py`**: Zamienia binarny blok czcionki `1024b` (.fnt) na dyrektywy wektorowe asemblera (dta).
- **`scripts/png2fnt.py`**: Tłumaczy kafelki z narysowanego w programie graficznym obrazka (np. 128x64px) na format `.fnt`.
- **`scripts/fnt2png.py`**: Rewers, wypluwa `.fnt` do ułożonego w rzędy pliku `.png`.

---

## 7. Debug Bridge (`debug_bridge/`)

Narzędzie konsolowe do automatyzacji emulatora Altirra na potrzeby procesów Spec-Driven Development (SDD) oraz analizy stanów za pomocą AI. Narzędzie zostało wyodrębnione jako własny moduł pip i oferuje dwa zintegrowane tryby pracy (`snapshot` oraz `break`).

### Instalacja (jednorazowa w venv projektu):
```bash
cd debug_bridge
..\.venv\Scripts\python.exe -m pip install -e .
cd ..
```

### Tryby wywołania:

#### A. Tryb Snapshot (`snapshot` lub legacy `run`)
Automatyczne uruchomienie gry i zrzut stanu gry (pamięci, zrzutu ekranu oraz etykiet) po określonej liczbie klatek lub sekund. Domyślnie konfiguruje się go plikiem YAML.

```bash
# Wywołanie z domyślnym plikiem konfiguracyjnym
.\.venv\Scripts\debug-bridge.exe snapshot --config debug_bridge/debug.yaml

# Wywołanie z nadpisaniem pliku XEX lub docelowego katalogu wyjściowego
.\.venv\Scripts\debug-bridge.exe snapshot --config debug_bridge/debug.yaml --xex dziki_zgon.xex --out custom_out/
```

#### B. Tryb Breakpoint (`break`)
Pozwala na uruchomienie emulatora i wstrzymanie w momencie napotkania breakpointu programowego (`--bp`) lub pułapki sprzętowej (`--bx` lub predefiniowane `--trap-wsync`, `--trap-vbi`, `--trap-dli`). Wypluwa pełen raport w formacie JSON zawierający stan rejestrów, call stack, opcjonalny dump pamięci i deasemblację.

```bash
# Zatrzymanie na etykiecie i zrzut rejestrów
.\.venv\Scripts\debug-bridge.exe break --xex dziki_zgon.xex --bp GAME_STATE --lab main.lab --hw-regs
```

---

## 8. Altirra Auto-Debugger Compatibility Shim (`scripts/atdbg.py`)

Skrypt `scripts/atdbg.py` został zintegrowany z **Debug Bridge** i służy obecnie jako przejściowa nakładka (shim) wstecznej kompatybilności. Automatycznie mapuje dawne parametry (`--rom` -> `--xex` oraz `--lab-file` -> `--lab`) i przekazuje wywołanie bezpośrednio do polecenia `debug-bridge break`, zwracając kod wyjścia (exit code) oraz wygenerowany dokument JSON na standardowe wyjście (stdout).

### Przykłady użycia shima:
```bash
# Wywołanie shima (automatycznie mapuje --rom na --xex)
python scripts/atdbg.py --rom dziki_zgon.xex --bp '$4000'

# Z użyciem pliku lab (mapuje --lab-file na --lab)
python scripts/atdbg.py --rom dziki_zgon.xex --bp GAME_STATE --lab-file dziki_zgon.lab

---

## 9. Konwerter Sprite'ów z PNG (`scripts/png2sprite.py`)

Narzędzie konsolowe konwertujące klatki sprite'a z 1-bitowego indeksowanego obrazu PNG bezpośrednio na format JSON zgodny ze Sprite Studio.

```bash
python scripts/png2sprite.py -i <obraz_png> -n <ilosc_klatek> [opcje]

Argumenty:
  -i, --input        Ścieżka do pliku wejściowego PNG (indeksowany, 1-bitowy)
  -n, --frames       Ilość klatek animacji pionowej na arkuszu

Opcje:
  -o, --output       Ścieżka do pliku wyjściowego JSON (domyślnie: <input>.sprite.json)
  --id ID            Identyfikator sprite'a w pliku JSON (domyślnie: nazwa pliku wielkimi literami)
  --mirror           Obraca klatki w poziomie (lustrzane odbicie)
  --add-mirrored     Generuje w jednym pliku oryginalny sprite oraz jego lustrzane odbicie (z sufiksem _MIRRORED)
  --invert           Inwertuje piksele (0 -> 1, 1 -> 0)
  --color COLOR      Indeks koloru w strukturze JSON (domyślnie: 0)
  --duration DUR     Czas trwania klatki (domyślnie: 4)
  --no-loop          Wyłącza pętlę animacji (domyślnie: włączona)
```

### Przykłady

```bash
# Konwersja arkusza 8x96 z 6 klatkami (każda klatka o wysokości 16)
python scripts/png2sprite.py -i sprites/gerwalt_sheet.png -n 6 --id GERWALT

# Konwersja z automatycznym wygenerowaniem wersji w lustrzanym odbiciu (GERWALT i GERWALT_MIRRORED w jednym pliku)
python scripts/png2sprite.py -i sprites/gerwalt_sheet.png -n 6 --id GERWALT --add-mirrored
```

```

