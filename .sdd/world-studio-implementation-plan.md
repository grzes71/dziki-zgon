# Plan: World Studio (Spec-Driven Development)

Celem jest budowa potężnego edytora GUI **World Studio** w oparciu o framework PySide6. Aplikacja pozwoli na wizualne projektowanie map regionów oraz samych ekranów w trybie graficznym przypominającym rzeczywisty obraz na komputerze Atari (ANTIC 4/5), operując z rozdzielczością obiektową.

Aplikacja będzie bezstratnie i bezpośrednio edytować system plików formatu YAML narzucony przez kompilator *World Builder*.

## Proposed Changes

Cały kod znajdzie się w nowym katalogu `world_studio/` w korzeniu projektu.

### [NEW] world_studio/models.py
- Lekkie warstwy danych, na których operować będzie GUI: wewnętrzne drzewo projektowe przechowujące otwarty region, listę ekranów i ich obiekty, w tym wyciągnięcie metadanych z `world.yaml` (np. pozycja gracza).

### [NEW] world_studio/project_manager.py
- Sterownik `File I/O`. Odpowiedzialny za wczytanie (load) plików strukturalnych z danego katalogu `world/`: `world.yaml`, `colors.yaml`, `objects.yaml` (w trybie Read-Only do palety) oraz wszystkich `region.yaml` i `screens/*.yaml`. Zapisuje pliki powrotem do YAML. Zapewnia SSOT dla struktury świata. Plik fontu (`game.fnt`) nie jest ładowany stąd.

### [NEW] world_studio/charset.py
- Silnik renderujący piksele z `.fnt`, bardzo zbliżony do tego z `Object Studio` (ewentualnie zaimportowany). Przemnaża bajty kafelków na kolorową matrycę pikseli.

### [NEW] world_studio/widgets/region_tree.py
- `QTreeWidget` w lewym panelu: wyświetla strukturę `[Katalog Główny] -> [Regiony] -> [Ekrany]`.

### [NEW] world_studio/widgets/object_palette.py
- Dedykowany widok kafelkowy. W locie generuje miniatury obiektów załadowanych z `objects.yaml` (uwzględniając `width` i `height` danego obiektu, renderując jego kafelki). Służy jako wybór "pędzla". Będzie posiadać przycisk narzędziowy "Ustaw pozycję gracza".

### [NEW] world_studio/widgets/live_region_view.py
- Skalowalna kanwa wyświetlająca pełną siatkę regionu i miniaturyzująca wyrenderowane w pełni ekrany (obiekty naniesione na tło). Pełni rolę podglądu "Makro" mapy świata.

### [NEW] world_studio/widgets/screen_canvas.py
- "Mikro" edytor ekranu. Domyślny rozmiar 40x10 znaków. Posiada mechanizm "Snap to character grid", obsługuje narzędzia: przesuwanie, umieszczanie, usuwanie obiektów z listy. Rysuje również wskaźnik pozycji startowej gracza (jeśli jest przypisana do tego ekranu). Obsługuje odcinanie renderowania dla atrybutu `repeat-x`/`repeat-y` do granicy 40x10 znaków.

### [NEW] world_studio/main.py
- Główne okno aplikacji wprowadzające zakładki (`QTabWidget` w centralnej części) dla oszczędności miejsca w pionie (Tab 1: Live Region, Tab 2: Screen Editor). Zapewnia menu z odseparowanymi akcjami: `File -> Open World Folder...` (dla YAML-i) oraz `File -> Load Charset...` (dla `game.fnt`).

## User Review Required
> [!IMPORTANT]  
> 1. Czy powołanie nowego modułu `world_studio` to akceptowalne podejście? Zauważ, że część koncepcji (np. ładowanie .fnt, dekodowanie kolorów) powieli się lub będzie współdzielona z `object_studio`.
> 2. Pamiętaj, że ucięcie w GUI podczas wizualizacji atrybutu `repeat-x: 40` (do końca prawego okna) idealnie zasymuluje zachowanie parsera!

## Verification Plan
1. Uruchomienie aplikacji poprzez `python -m world_studio.main`.
2. Kliknięcie *File -> Open World Folder...* i wskazanie folderu `world/`.
3. Kliknięcie *File -> Load Charset...* i wskazanie pliku `fonts/game.fnt`.
4. Sprawdzenie, czy struktura katalogów (w tym `WHITE_FIELD`) poprawnie załaduje się do lewego drzewka nawigacji, a ekran domyślny pojawi się na podglądzie z prawidłowymi glifami.
5. Namalowanie i modyfikacja istniejącego poziomu (np. ekranu startowego, w tym zmiana współrzędnych startu gracza), zapisanie i ponowna kompilacja projektu (`make all`), co udowodni zgodność YAMLa z *World Builderem*.
