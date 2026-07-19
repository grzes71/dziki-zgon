# Wiedźmin: Dziki Zgon 🐺💀

Przygodowo-zręcznościowa gra z widokiem z góry na **Atari 800 XL / 65 XE** — humorystyczna parodia Wiedźmina.

- Otwarty Świat
- Nieliniowa fabuła

![Game cover](/cover.png)

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
│   ├── title_audio.asm          # Integracja odtwarzacza w VBI, start/stop, wyciszanie POKEY
│   ├── rmt_feat.asm             # Konfiguracja funkcji (features) odtwarzacza RMT
│   └── rmtplayr.asm             # Kod asemblera odtwarzacza RMT (mono, relocatable)
├── scenes/
│   ├── title/title.asm          # Ekran tytułowy (init + run + DLI + tęcza)
│   ├── story/story.asm          # Ekran opisu (dekompresja story do stopki)
│   ├── game/game.asm            # Gra właściwa
│   └── gameover/gameover.asm    # Ekran końca gry (ANTIC D narrow + ANTIC 3 tęcza)
├── gen/                         # Pliki generowane podczas buildu (część jest trzymana w repo)
│   ├── title.bin                # Surowe dane binarne ekranu tytułu
│   ├── title.rle                # Skompresowany ekran tytułu (używany w runtime)
│   ├── title.asm                # Dane .byte ekranu tytułu (MADS)
│   ├── title_colors.asm         # Kolory tytułu: stałe .equ + kod init
│   ├── title_displaylist.asm    # ANTIC Display List tytułu (2 segmenty)
│   ├── title_music.asm          # Skonwertowany moduł muzyczny MADS (title.sap -> title_music.asm)
│   ├── rmtplayr.asm             # Skonwertowany kod playera RMT (MADS)
│   ├── gameover.bin             # Surowe dane binarne ekranu game over
│   ├── gameover.rle             # Skompresowany ekran game over (używany w runtime)
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
├── world/                       # Dane wejściowe w formacie YAML definiujące świat, ekrany i obiekty gry
├── world_builder/               # Dedykowany kompilator map gry w Pythonie (YAML → ASM)
├── object_studio/               # Graficzny edytor obiektów gry w PySide6 (GUI do edycji world/objects.yaml)
├── world_studio/                # Graficzny edytor map świata w PySide6 (GUI do wizualnej edycji regionów i ekranów)
├── tests/                       # Testy jednostkowe i integracyjne (Py65, World Builder)
└── rgb2a8/                      # Referencyjna paleta Atari PAL (256 wartości RGB)
```

## Wymagania

| Narzędzie | Wersja | Uwagi |
|---|---|---|
| [MADS](https://mads.atari8.info/) | 2.1.x | Asembler 6502/65816 dla Atari 8-bit |
| [Python](https://www.python.org/) | 3.10+ | Do uruchamiania konwertera `img2asm.py` |
| [Pillow](https://python-pillow.org/) | 12.x | Biblioteka do przetwarzania obrazów (`pip install -r requirements.txt`) |
| [PyYAML](https://pyyaml.org/) | — | Do parsowania plików map w World Builderze (`pip install -r requirements.txt`) |
| [Pydantic](https://docs.pydantic.dev/) | 2.x | Do zaawansowanej walidacji struktury map i obiektów (`pip install -r requirements.txt`) |
| [PySide6](https://doc.qt.io/qtforpython-6/) | 6.x | Do interfejsu graficznego narzędzia Object Studio (`pip install pyside6`) |
| Emulator Atari | — | Np. [Altirra](https://www.virtualdub.org/altirra.html), Atari800 |
| [Atari Image Converter](https://github.com/grzes71/py-image-converter/#atari-image-converter) | — | Konwersja obrazów na formaty Atari (PNG → GR7, GR8, MIC, i inne) |
| [html-to-markdown](https://github.com/grzes71/html-to-markdown#html-to-markdown) | — | Konwersja dokumentacji HTML do Markdown
| [py65](https://github.com/mnaberez/py65) | — | Emulator 6502 w Pythonie do testów (`pip install -r requirements.txt`) |

## Development (Windows)

Poniżej znajduje się opis kroków potrzebnych, aby zacząć development gry na systemie Windows:

1. Instalacja chocolatey (https://chocolatey.org/install#individual)
2. Instalacja za pomocą `choco install`:
   - `git`
   - `python`
   - `make`
3. Instalacja rmt2atasm https://github.com/CycoPH/rmt2atasm (Relocatable RMT player for atasm assembler) - skopiowanie pliku exe do `C:\Apps\`
4. Instalacja Mad-Assembler (https://github.com/tebe6502/Mad-Assembler/releases/tag/2.1.6) w lokalizacji `C:\Apps\Mad-Assembler-2.1.6`
5. Instalacja asapconv.exe (https://sourceforge.net/projects/asap/files/asap/8.0.0/asap-8.0.0-win64.zip/download) - do lokalizacji `C:\Apps\ASAP\`
6. Instalacja emulatora Altirra (do lokalizacji `C:\Apps\Altirra-4.40`)

### Tworzenie środowiska wirtualnego

Aby zainstalować pakiety Pythona, utwórz i aktywuj środowisko wirtualne, a następnie zainstaluj zależności:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Kompilacja

```bash
# Wszystko za jednym razem: sprite'y → tło → XEX
make

# Tylko konkretne cele
make world     # kompiluje wejściowe mapy YAML do zoptymalizowanych struktur ASM
make sprites   # generuje gen/moon.asm + gen/dziki-zgon.asm
make bg        # generuje m.in. gen/title.bin, gen/title.rle, gen/title_colors.asm, gen/title_displaylist.asm
make music     # konwertuje muzykę: music/title.sap -> gen/title_music.asm + music/rmtplayr.asm -> gen/rmtplayr.asm
make clean     # usuwa katalog gen/ oraz plik XEX

# Zmiana obrazu tła
make clean BG_PREFIX=title-0a && make

# Uruchomienie w emulatorze
altirra dziki_zgon.xex
```

## Narzędzia

Szczegółowe opisy wszystkich dedykowanych narzędzi, w tym **Konwertera obrazów**, kompilatora **World Builder**, oraz wizualnych edytorów GUI (**World Studio**, **Object Studio**), przeniesiono do pliku: [TOOLS.md](TOOLS.md).
## Licencja

Projekt hobbystyczny — do użytku niekomercyjnego.
