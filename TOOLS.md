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

Narzędzie konsolowe do automatyzacji emulatora Altirra na potrzeby procesów Spec-Driven Development (SDD) oraz analizy stanów za pomocą AI. Pozwala na automatyczne uruchomienie gry, zatrzymanie w określonej klatce (lub czasie), zrzut pamięci i zrzut ekranu do weryfikacji testowej. Narzędzie zostało wyodrębnione jako własny moduł pip.

### Instalacja (jednorazowa w venv projektu):
```bash
cd debug_bridge
..\.venv\Scripts\python.exe -m pip install -e .
cd ..
```

### Wywołanie:
Konfiguracja odbywa się przez plik YAML (domyślnie `debug_bridge/debug.yaml`).

```bash
.\.venv\Scripts\debug-bridge.exe run --config debug_bridge/debug.yaml
```

Wyniki, w tym `debug_state.json`, `debug_report.md` oraz zrzuty ekranu (`screenshot.png`), lądują w katalogu zdefiniowanym w sekcji `output` (domyślnie `out/`).

---

## 8. Altirra Auto-Debugger Basic (`scripts/atdbg.py`)

Proste, jednoplikowe narzędzie konsolowe (CLI) dla systemu Windows, pozwalające na automatyczne, deterministyczne debugowanie kodu na emulatorze Altirra. Skrypt stawia wskazany breakpoint (programowy lub sprzętowy), wykonuje zrzuty pamięci i wypuszcza ustrukturyzowany wynik w formacie JSON (zawierający rejestry, zdeasemblowaną instrukcję, call stack i zrzuty pamięci).

Narzędzie przydaje się zarówno do szybkiego testowania, jak i jako warstwa spodnia (subprocess) dla większego `debug_bridge`. Zawsze bezpiecznie sprząta pliki tymczasowe i sprawnie zarządza opóźnieniami (timeout).

### Zależności:
- Python 3.8+ (wyłącznie biblioteki standardowe, zero zewnętrznych zależności)
- Windows (Altirra)

### Przykłady użycia:

```bash
# Breakpoint programowy (software) pod danym adresem
python scripts/atdbg.py --rom dziki_zgon.xex --bp '$4000'

# Breakpoint z wykorzystaniem nazwy etykiety (automatycznie odczytanej z pliku .lab)
python scripts/atdbg.py --rom dziki_zgon.xex --bp GAME_STATE --lab-file dziki_zgon.lab

# Breakpoint sprzętowy (hardware) - np. na moment zapisu do rejestru NMIEN
python scripts/atdbg.py --rom dziki_zgon.xex --bx 'write($D40E)'

# Tryb Warp (brak limitu FPS), zrzuty wybranych bloków pamięci i własny limit czasu (timeout)
python scripts/atdbg.py --rom dziki_zgon.xex --bp '$4000' \
    --mem-dump '$0600:L$40' --mem-dump '$A000:L$100' \
    --timeout 30 --warp --verbose

# Zapisanie wyniku JSON do dodatkowego pliku (np. na potrzeby AI lub CI)
python scripts/atdbg.py --rom dziki_zgon.xex --bp '$4000' --output-json result.json
```
