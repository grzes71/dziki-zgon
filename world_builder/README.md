# World Builder

**World Builder** to autorskie narzędzie typu kompilator służące do konwersji definicji świata i map dla gry *Wiedźmin: Dziki Zgon* z czytelnego formatu YAML na wysoce zoptymalizowane struktury asemblerowe dla procesora MOS 6502 (tablice wskaźników LO/HI, format Structure of Arrays).

Narzędzie stanowi w projekcie **Pojedyncze Źródło Prawdy (SSOT)**. Programiści operują wyłącznie na plikach `.yaml`, a kod asemblera do wklejenia w kompilator MADS jest generowany automatycznie.

---

## 🚀 Uruchamianie

Skrypt World Builder zintegrowany jest w potoku `make` (wywoływany automatycznie jako polecenie `make world` jeśli zmieniono pliki YAML). 

Aby uruchomić kompilator manualnie:
```bash
python -m world_builder <katalog_wejsciowy> <katalog_wyjsciowy>
```

**Przykład**:
```bash
python -m world_builder world gen/world
```

---

## 📁 Struktura Katalogów Wejściowych

Kompilator oczekuje następującego drzewa i nazewnictwa plików wejściowych:
```
world/
├── world.yaml                  # Globalne ustawienia i punkt startowy gracza
├── objects.yaml                # Baza danych obiektów i ich rozmiarów
└── NAZWA_REGIONU/              # Katalog danego obszaru mapy
    ├── region.yaml             # Parametry ogólne regionu (np. szer./wys. w ekranach)
    └── screens/                # Zbiór plików ekranów należących do regionu
        ├── 000.yaml            
        └── 001.yaml
```

---

## 📝 Format Plików YAML (Przykłady)

Poniżej znajduje się specyfikacja i przykłady dla kluczowych plików obsługiwanych przez system:

### 1. `world.yaml`
Zawiera konfigurację globalną, w tym lokację początkową, na której gracz zostanie osadzony (kombinacja nazwy regionu oraz ID ekranu).

```yaml
start:
  region: WHITE_FIELD
  screen: TAVERN
```

### 2. `objects.yaml`
Centralny rejestr struktur umieszczanych w świecie. Obejmuje unikalny identyfikator mnemoniczny, `code` od 1 do 254 (zoptymalizowany dla 6502 jako indeks), fizyczny rozmiar w kafelkach znaków oraz parametry fizyki.
> **Uwaga**: Wymiary `width` i `height` mają narzucony limit od 1 do 16. Silnik kompresuje je pod spodem w półbajty jako wartości `w-1` / `h-1`.
> Atrybut `tiles` zawiera listę kodów znaków w charset'cie. Liczba elementów musi wynosić dokładnie `width * height`. Kody wstawiane są od lewej do prawej i z góry na dół.

```yaml
objects:
  - id: HOUSE_SMALL
    code: 1
    size:
      width: 4
      height: 3
    flags:
      blocking: true
      interactive: false
    tiles: [
      10, 11, 12, 13,
      20, 21, 22, 23,
      30, 31, 32, 33
    ]

  - id: TREE_SMALL
    code: 2
    size:
      width: 2
      height: 3
    flags:
      blocking: true
      interactive: false
    tiles: [
      40, 41, 
      50, 51, 
      60, 61
    ]
```

### 3. `region.yaml`
Plik zawarty bezpośrednio w katalogu konkretnego regionu. Określa przestrzeń w wymiarze liczby mniejszych ekranów.

```yaml
id: WHITE_FIELD
grid:
  width: 4
  height: 5
```

### 4. Ekran (`screens/000.yaml` itp.)
Ekrany budują właściwą planszę gry (odpowiadają trybowi graficznemu ANTIC 5, matrycy 40x10 kafelków). Zawierają listę zinstancjonowanych `objects` oraz system przejść do sąsiednich plansz `exits`.

```yaml
id: TAVERN
objects:
  # Zbuduj obiekt HOUSE_SMALL na współrzędnej x=10, y=2 na ekranie TAVERN
  - object: HOUSE_SMALL
    x: 10
    y: 2
  - object: TREE_SMALL
    x: 30
    y: 5

exits:
  # Przejdź na ekran VILLAGE, gdy gracz wejdzie w południową krawędź planszy
  south: VILLAGE
  east: CROSSROADS
```

---

## 🗄️ Pliki Wyjściowe (.asm)

Zgodnie z konwencją narzędzie produkuje wynik swojej walidacji do określonego na starcie folderu z 5 wygenerowanymi plikami z rozszerzeniem MADS ASM:

1. **`objects.asm`**: Zawiera rozpakowane na tablice *SoA* (Structure of Arrays) wymiary obiektów (`OBJ_SIZE`), ich atrybuty fizyczne (`OBJ_FLAGS`) oraz wektory na adresy poszczególnych kafli mapowania znaków (`OBJ_TILES_LO/HI`).
2. **`regions.asm`**: Definicje offsetów identyfikujących globalne zasoby mapy ułożonych względem nazw.
3. **`screens.asm`**: Wyliczone tablice wskaźników LO/HI (`SCREEN_POINTERS`) z danymi dla wszystkich ekranów, zawierające rozliczenie każdego postawionego obiektu.
4. **`exits.asm`**: Powiązania nawigacyjne. Tablice o długości liczby ekranów informujące silnik, jaki kod ma zostać wywołany (lub ignorowany) po przekroczeniu przez gracza granic północ, południe, zachód, wschód.
5. **`world.inc`**: Zbiór stałych w formacie `.equ`, udostępniający środowisku globalną zmienną `START_SCREEN_ID` informującą `main.asm` gdzie umieścić gracza przy init.

---

## 🛠️ Mechanizmy Walidacji (Bezpieczeństwo)
Kompilator World Builder surowo chroni kod przed nielegalnymi alokacjami w asemblerze:
- Przerwie proces, jeżeli kod dowolnego obiektu ulegnie duplikacji.
- Przerwie proces, jeżeli w matrycy zostanie użyte ID obszaru/obiektu, który nie figuruje w głównej bazie.
- **Obrys Ekranu**: Weryfikuje i wyklucza obiekty wystające poza granice obszaru widzialnego ANTIC 5 `(x + w > 40)` lub `(y + h > 10)`.
- Weryfikuje spójność tablicy kafelków `tiles` (jej długość rygorystycznie musi zgadzać się ze zdefiniowanym rozmiarem).
