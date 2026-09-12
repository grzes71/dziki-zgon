# World Studio

**World Studio** to oficjalny, zaawansowany edytor graficzny (GUI) stworzony w **Pythonie (PySide6)** na potrzeby gry *Dziki Zgon* (Atari 800 XL / XE). 

Narzędzie służy do wizualnego projektowania i edycji całego świata gry – regionów, ekranów, kafelków tła, wrogów, przejść kompasowych, portali, zadań, dialogów i sekretów – operując bezpośrednio na plikach **YAML** w katalogu `world/`, który stanowi **Pojedyncze Źródło Prawdy (SSOT)** projektu.

---

## 🚀 Wymagania i Uruchamianie

Aplikacja korzysta z wirtualnego środowiska projektu Python (`.venv`):

```bash
# Uruchomienie World Studio z poziomu głównego katalogu projektu:
python -m world_studio.main
```

Wymagane pakiety (`pip install -r requirements.txt`):
* Python 3.10+
* `PySide6` (interfejs graficzny Qt)
* `PyYAML` (serializacja i deserializacja plików map)
* `pydantic` (walidacja schematów i modeli danych)

---

## 🖥️ Układ Interfejsu (Przegląd Okna)

Interfejs aplikacji podzielony jest na ergonomiczne panele robocze:

```
+----------------------------------------------------------------------------------+
| Pasek Menu: File (Open World, Reload Objects, Load Charset, Save) | Tools (Items) |
+------------------------+---------------------------------------------------------+
| DRZEWO REGIONÓW        | ZAKŁADKI GŁÓWNE:                                        |
| • Regiony i Ekrany     | 1. [Live Region]       2. [Screen Canvas]               |
| • Dodaj / Usuń Region  | +--------------------+ +-------------------------------+ |
| • Palety barw regionów | | Widok mapy regionu | | Interaktywne płótno ekranu    | |
+------------------------+ | Siatka ekranów     | | ANTIC 5 (40x12 kafelków)      | |
| PALETA AKCJI I OBIEKT. | | Miniatury w locie  | | Układanie obiektów, wrogów,   | |
| • Tryb: Add Object /   | | Strzałki wyjść     | | sekretów, punktów startu      | |
|   Enemy / Portal /     | |                    | |                               | |
|   Player Start         | | Menu kontekstowe   | | Menu kontekstowe (LPM / PPM)  | |
| • Filtr Tagów          | | (Preview, Rename,  | | Precyzyjne przesuwanie        | |
| • Podgląd kafelków     | |  Exits, Clean)     | |                               | |
+------------------------+ +--------------------+ +-------------------------------+ |
+----------------------------------------------------------------------------------+
| Pasek Stanu (Status Bar): Informacje o załadowanych plikach, operacjach i błędach |
+----------------------------------------------------------------------------------+
```

---

## 📂 Pasek Menu (`MenuBar`)

| Menu | Opcja | Opis |
|---|---|---|
| **File** | **Open World Folder...** | Otwiera katalog ze światem gry (domyślnie katalog `world/`). Wczytuje `world.yaml`, `objects.yaml`, `items.yaml`, `enemies.yaml` oraz podkatalogi regionów. |
| **File** | **Reload Objects** | Ponownie wczytuje plik `objects.yaml` (przydatne, gdy obiekty były modyfikowane równolegle w *Object Studio*). |
| **File** | **Load Charset...** | Wczytuje plik czcionki Atari (`*.fnt`, dokładnie 1024 bajty). Domyślny zestaw krojów gry znajduje się w `fonts/`. |
| **File** | **Reload Charset** | Przeładowuje aktualnie wybrany plik czcionki z dysku. |
| **File** | **Save Project** | Zapisuje wszystkie modyfikacje (`world.yaml`, `items.yaml`, `region.yaml`, `screens/*.yaml`). Przed zapisem wykonywana jest automatyczna walidacja spójności. |
| **Tools** | **Inventory Items...** | Otwiera menedżer bazy przedmiotów ekwipunku (`items.yaml`). |

---

## 🗺️ Zakładka 1: Widok Regionu (`Live Region`)

Kluczowy widok do planowania topologii danego regionu. Prezentuje siatkę ekranów zdefiniowaną w parametrach `layout.rows` × `layout.columns`:

* **Podgląd w czasie rzeczywistym**: Każdy ekran jest natychmiast renderowany z uwzględnieniem obiektów i aktualnej palety kolorów Atari.
* **Wskaźniki wyjść kompasowych**: W prawym dolnym rogu każdej miniatury wyświetlany jest panel ze strzałkami wskazującymi aktywne przejścia (północ, południe, zachód, wschód).
* **Nawigacja**: Dwukrotne kliknięcie lewym przyciskiem myszy na ekranie natychmiast przenosi do zakładki **Screen Canvas** i otwiera ten ekran do szczegółowej edycji.
* **Menu kontekstowe pod prawym przyciskiem myszy (PPM)**:
  * **Preview Screen**: Otwiera pełnoekranowy, rzeczywisty podgląd ekranu w skali 1:1.
  * **Rename Screen...**: Zmienia identyfikator ekranu i **automatycznie aktualizuje wszystkie wyjścia (`exits`)** na sąsiednich ekranach, zapobiegając uszkodzeniu powiązań grafu.
  * **Set Exits...**: Otwiera okno dialogowe wyboru docelowych ekranów dla wyjść kompasowych (North, South, East, West).
  * **Clean**: Usuwa wszystkie obiekty z danego ekranu (po potwierdzeniu).
  * **Remove Screen**: Usuwa ekran z regionu.
  * **Add Screen Here...** *(na pustej komórce)*: Tworzy nowy ekran pod wskazanymi współrzędnymi siatki `(col, row)`.

---

## 🎨 Zakładka 2: Edytor Ekranu (`Screen Canvas`)

Obszar roboczy o wymiarach **40 kolumn × 12 wierszy**, odpowiadający trybowi graficznemu **ANTIC Mode 5**:

### Interakcja myszą:
* **Lewy Przycisk Myszy (LPM)**:
  * **Na pustym polu**: Wstawia aktualnie wybraną encję z palety (obiekt, wroga, pozycję startową lub punkt wejścia portalu).
  * **Na istniejącym obiekcie interaktywnym**: Otwiera edytor właściwości obiektu (`InteractiveObjectPropertiesDialog`).
  * **Na obiekcie typu Secret**: Otwiera okno przypisania przedmiotu ze skrytki (`SecretItemSelectionDialog`).
  * **Na wrogu**: Otwiera okno właściwości wroga (`EnemyPropertiesDialog`).
  * **Na punkcie Portal Entry**: Wyświetla okno ze szczegółami punktu wejścia.
* **Prawy Przycisk Myszy (PPM)**:
  * Otwiera menu kontekstowe dla wskazanego elementu:
    * **usuń**: Kasuje element z planszy.
    * **w lewo / w prawo / w górę / w dół**: Precyzyjnie przesuwa obiekt lub wroga o jeden krok siatki (z zachowaniem walidacji granic i wykrywania kolizji).

> [!NOTE]
> **Wyrównanie do siatki**: Współrzędne obiektów są automatycznie zaokrąglane do parzystych wartości kolumn i wierszy (`x // 2 * 2`, `y // 2 * 2`), co gwarantuje pełną zgodność ze sprzętowym dekoderem ANTIC Mode 5 w silniku 6502.

---

## 🧩 Obsługiwane Typy Elementów

### 1. Obiekty Zwykłe (Dekoracje i Teren)
* Wybierane z listy obiektów z możliwością filtrowania po tagach (np. `buildings`, `nature`, `water`).
* Renderowane z uwzględnieniem znaków z czcionki i właściwości `blocking` (kolizyjność).
* Narzędzie zapobiega nakładaniu się obiektów na inne encje oraz poza granice ekranu (40×12).

### 2. Obiekty Interaktywne (`interactive: true`)
> [!IMPORTANT]
> Zgodnie z ograniczeniami silnika gry, na danym ekranie może znajdować się **maksymalnie 1 obiekt interaktywny**. Próba postawienia kolejnego zostanie zablokowana.

Wspierane są dwa podtypy:
1. **`kwatera` (Wiedźmińska kwatera / NPC / Zleceniodawca)**:
   * `Wymagania spełnione (conditions_met)`: Tekst wypowiadany, gdy gracz posiada wymagane przedmioty.
   * `Wymagania niespełnione (conditions_unmet)`: Tekst wypowiadany przy braku wymaganych przedmiotów.
   * `Przedmioty wymagane (items_required)`: Lista ID przedmiotów z ekwipunku potrzebnych do ukończenia interakcji.
   * `Przedmioty otrzymane (items_provided)`: Lista ID przedmiotów przekazywanych graczowi.
   * `Koniec Gry (game_over)`: Flaga oznaczająca ukończenie gry po wejściu w interakcję.
2. **`portal` (Łodzie, wrota, punkty szybkiej podróży między regionami)**:
   * `Region docelowy (target_region)`: Wybór regionu docelowego spośród tych, które mają zdefiniowany `Portal Entry` dla obecnego regionu.
   * `Koszt podróży (cost_of_travel)`: Wymagana liczba monet/energii.
   * `Komunikat podróży (message_travel)`: Tekst wyświetlany przy skorzystaniu z portalu.

### 3. Obiekty Ukryte / Znajdźki (`secret: true`)
* Obiekty, w których ukryty jest skarb lub przedmiot fabularny.
* Każdy obiekt tego typu wymaga przypisania przedmiotu z ekwipunku (`items_provided`).
* **Reguła unikalności**: Dany przedmiot typu Secret może wystąpić w całym świecie gry **tylko jeden raz**. Dialog wyboru uniemożliwia wielokrotne użycie tego samego przedmiotu.

### 4. Wrogowie (`enemies`)
* Dozwolona liczba: **od 0 do 3 wrogów na ekran**.
* Konfiguracja każdego przeciwnika:
  * **Typ**: Wybór z bazy `enemies.yaml` (np. Strzyga, Utopiec).
  * **Strategia ruchu**: `vertical`, `horizontal`, `random`, `chaotic`, `patrol`, `pacing`, `snake`, `homing`.
  * **Prędkość**: `slow`, `medium`, `fast`.
  * **Kolor**: Barwa duszka PMG na ekranie (wybór z palety nazw angielskich).

### 5. Punkt Wejścia Portalu (`Portal Entry`)
* Miejsce na ekranie, w którym pojawi się Geralt po przybyciu do danego regionu z innego obszaru.
* Każdy inny region może mieć zdefiniowany dokładnie jeden punkt wejściowy w danym regionie docelowym.

### 6. Pozycja Początkowa Gracza (`Player Start`)
* Ustawia współrzędne początkowe Geralta po uruchomieniu nowej gry (`world.yaml`: `start_region`, `start_screen`, `start_position`).
* Na ekranie pozycja startowa oznaczana jest charakterystycznym markerem gracza.

---

## 🎨 Konfiguracja Palet Kolorów Atari per Region

Każdy region posiada niezależnie definiowany zestaw rejestrów barwnych ANTIC/GTIA:
* `BACKGROUND`: Kolor tła.
* `PF0`, `PF1`, `PF2`: Trzy kolory podstawowe pola gry (Playfield).
* `PF3_INV`: Czwarty kolor uaktywniany przez odwrócony 7. bit znaku (`INV`).

W World Studio kolory można modyfikować bezpośrednio z poziomu drzewa regionów (**Edit Region Colors**):
* Wybór z systemowego próbnika kolorów RGB.
* Wbudowana funkcja konwersji `img2asm.rgb_to_atari` przelicza wartości RGB na natywne indeksy kolorów procesora GTIA (odcienie i luminancje `$00`–`$FF`).
* Możliwość kopiowania schematu kolorów z innego istniejącego regionu jako szablon.

---

## 🎒 Menedżer Ekwipunku (`items.yaml`)

Dostępny w menu: `Tools -> Inventory Items...`:
* Dodawanie nowych przedmiotów do bazy gry.
* Definiowanie unikalnego indeksu `ID` (`1..255`).
* Definiowanie opisu tekstowego przedmiotu.
* `Pozycja w charset (charset_position)`: Indeks znaku graficznego w czcionce Atari używanego do wyświetlenia ikony przedmiotu w panelu ekwipunku.
* Flaga `Zużywalny (consumable)`: Określa, czy przedmiot znika z ekwipunku po użyciu w queście.

---

## 🛡️ Walidacja Projektu i Zabezpieczenia

World Studio rygorystycznie chroni projekt przed uszkodzeniem danych przed zapisem:
1. **Limit obiektów interaktywnych**: Jeśli na dowolnym ekranie znajdzie się więcej niż 1 obiekt interaktywny, zapis zostanie zablokowany z podaniem dokładnej nazwy regionu, ekranu i konfliktowych obiektów.
2. **Unikalność sekretów**: Weryfikacja, czy żaden przedmiot Secret nie został powielony.
3. **Integralność portali**: Wymuszenie istnienia punktu docelowego `Portal Entry` przed powiązaniem portalu.
4. **Weryfikacja granic**: Obiekty i wrogowie nie mogą przekraczać wymiarów ekranu (40×12) ani nakładać się na siebie nawzajem.

---

## ⚙️ Integracja z Potokiem Kompilacji (`make world`)

Po zapisaniu zmian w World Studio (`File -> Save Project`):
* Wszystkie pliki YAML w `world/` zostają zaktualizowane.
* Uruchomienie kompilatora asemblera:
  ```bash
  make world
  # lub pełny potok budowania:
  make all
  ```
  spowoduje automatyczne przetłumaczenie zmian na wysoce zoptymalizowany kod asemblera MADS w katalogu `gen/world/` (`screens.asm`, `regions.asm`, `exits.asm`, `objects.asm`, `world.inc`).
