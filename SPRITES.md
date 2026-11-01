# Dziki Zgon — System Sprite'ów

Dokument opisuje system wyświetlania duszka (sprite'a) w grze "Dziki Zgon" na platformę Atari XL/XE, format plików źródłowych, potok budowania oraz instrukcję krok po kroku jak dodać nową postać/przeciwnika do silnika gry.

---

## 1. Architektura i Ograniczenia Sprzętowe (Atari PMG)
Silnik gry wykorzystuje sprzętowy mechanizm **Player-Missile Graphics (PMG)** układu ANTIC/GTIA do renderowania postaci gracza (Gerwalta) oraz przeciwników na ekranie.

*   **Szerokość**: Każdy duszek ma sztywną szerokość **8 pikseli** (w trybie jednokrotnej szerokości, odpowiadającej rozdzielczości panelu gry).
*   **Wysokość**: Wysokość duszka jest zmienna (np. 15 linii dla sukkuba, 16 linii dla Gerwalta). Każdy duszek ma zdefiniowaną wysokość za pomocą stałej w pliku asemblera (np. `SPRITE_SUKKUB_RIGHT_HEIGHT`).
*   **Kolory (Duszki 2-kolorowe i 4-kolorowe)**:
    *   **2-kolorowy (Standardowy pojedynczy gracz)**: Duszek ma 1 kolor z rejestru `COLPM0..3` + przezroczyste tło.
    *   **4-kolorowy (Dual-Player Overlap)**: Atari GTIA przy włączonym bicie 5 rejestru priorytetów (`PRIOR` / `GPRIOR` $D01B) łączy nakładające się duszki (P0 z P1 lub P2 z P3) poprzez sprzętowy logiczny OR kolorów:
        *   `0`: Przezroczysty (kolor tła)
        *   `1`: Kolor gracza A (`COLPM0` lub `COLPM2`)
        *   `2`: Kolor gracza B (`COLPM1` lub `COLPM3`)
        *   `3`: Kolor miksu (`COLPM0 OR COLPM1` lub `COLPM2 OR COLPM3`)
*   **Wielokierunkowość i Animacja**: Klatki animacji i kierunki ruchu są mapowane programowo w strukturach asemblera poprzez podmienianie wskaźników do danych klatek w pamięci PMG.

---

## 2. Format Definicji Duszka (.sprite.json)
Wszystkie duszki w grze definiowane sunt w plikach JSON w katalogu `/sprites`. Każdy plik JSON może zawierać jeden lub więcej wariantów duszka (np. rozbicie na ruch w lewo i prawo).

### Przykładowa struktura pliku `sprites/sukkub.sprite.json`:
```json
{
  "version": 1,
  "sprites": [
    {
      "id": "SUKKUB_RIGHT",
      "width": 8,
      "height": 15,
      "color": 0,
      "animation": {
        "frame_duration": 4,
        "loop": true
      },
      "frames": [
        {
          "pixels": [
            "00100110",
            "00011101",
            "..."
          ]
        },
        {
          "pixels": [
            "00000000",
            "10010110",
            "..."
          ]
        }
      ]
    }
  ]
}
```

*   `id`: Unikalny identyfikator używany jako prefiks do generowanych etykiet i stałych w asemblerze (np. `SUKKUB_RIGHT`).
*   `width`/`height`: Wymiary duszka w pikselach.
*   `frames`: Tablica klatek animacji. Każda klatka to lista ciągów znaków złożonych z `0` i `1` reprezentujących piksele (bity w bajcie pamięci duszka).

---

## 3. Potok Kompilacji (Build Pipeline)
Konwersja plików JSON na kod asemblera zintegrowana jest z plikiem `Makefile`:

1.  Wszystkie pliki pasujące do wzorca `sprites/*.sprite.json` są automatycznie wykrywane.
2.  Skrypt `scripts/sprite2asm.py` przetwarza każdy plik `.sprite.json` i generuje plik asemblera w `/gen/<nazwa>.sprite.asm`.
3.  Wygenerowany kod asemblera zawiera:
    *   Stałe wysokości i liczby klatek:
        ```assembly
        .def SPRITE_SUKKUB_RIGHT_HEIGHT = 15
        .def SPRITE_SUKKUB_RIGHT_COLOR = 0
        .def SPRITE_SUKKUB_RIGHT_FRAMES = 2
        ```
    *   Etykiety danych klatek animacji (bajtowe reprezentacje wierszy pikseli):
        ```assembly
        SUKKUB_RIGHT_FRAME_0
            dta %00100110
            dta %00011101
            ...
        ```
    *   Tabelę wskaźników na klatki animacji:
        ```assembly
        SUKKUB_RIGHT_PTRS
            dta a(SUKKUB_RIGHT_FRAME_0)
            dta a(SUKKUB_RIGHT_FRAME_1)
        ```
    *   **Dla duszka 4-kolorowego**: skrypt rozdziela dane na dwie warstwy PMG (`P0` i `P1`):
        ```assembly
        .def SPRITE_BOSS_HEIGHT = 24
        .def SPRITE_BOSS_COLOR0 = $28 ; Kolor P0
        .def SPRITE_BOSS_COLOR1 = $94 ; Kolor P1
        .def SPRITE_BOSS_COLOR_MIX = $BC ; Kolor P0 OR P1
        .def SPRITE_BOSS_IS_4COLOR = 1

        BOSS_P0_FRAME_0
            dta %... ; bity gdzie piksel to 1 lub 3
        BOSS_P1_FRAME_0
            dta %... ; bity gdzie piksel to 2 lub 3

        BOSS_P0_PTRS
            dta a(BOSS_P0_FRAME_0)
        BOSS_P1_PTRS
            dta a(BOSS_P1_FRAME_0)
        ```

---

## 4. Krok po Kroku: Jak dodać nowego duszka/przeciwnika do gry

### Krok 1: Stworzenie pliku JSON
Stwórz plik `sprites/<nazwa_przeciwnika>.sprite.json` zawierający definicję pikseli i animacji. Jeśli duszek ma wyglądać inaczej w zależności od kierunku ruchu (np. w lewo/prawo), podziel go na dwa osobne wpisy w tablicy `sprites` (np. z `id` ustawionym na `<NAZWA>_RIGHT` i `<NAZWA>_LEFT`).

### Krok 2: Rejestracja w konfiguracji świata (`enemies.yaml`)
Dodaj unikalne ID nowego przeciwnika na końcu pliku [world/enemies.yaml](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/world/enemies.yaml):
```yaml
enemies:
  - id: "kikimora"
    name: "Kikimora"
  ...
  - id: "sukkub"
    name: "Sukkub"
```
> [!IMPORTANT]
> Kolejność przeciwników na tej liście ma krytyczne znaczenie! Indeks na liście (od 0) odpowiada kodowi typu przeciwnika (`e_type` / `OBJ_CODE`) w silniku gry.

### Krok 3: Dołączenie pliku asemblera
W pliku [main.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/main.asm) dołącz wygenerowany plik asemblera duszka w sekcji włączania zasobów (okolice linii 200+):
```assembly
    icl "gen/<nazwa_przeciwnika>.sprite.asm"
```

### Krok 4: Konfiguracja tabel kierunków w `engine/npc.asm`
W pliku [engine/npc.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/npc.asm) zdefiniuj tabele wskaźników klatek oraz limity animacji dla każdego z 4 kierunków ruchu aktora (0 = W prawo, 1 = W lewo, 2 = W górę, 3 = W dół):

```assembly
<NAZWA>_PTRS_TABLE
    dta a(<NAZWA>_RIGHT_PTRS) ; Ruch w prawo
    dta a(<NAZWA>_LEFT_PTRS)  ; Ruch w lewo
    dta a(<NAZWA>_RIGHT_PTRS) ; Ruch w górę (domyślny duszek)
    dta a(<NAZWA>_LEFT_PTRS)  ; Ruch w dół (domyślny duszek)

<NAZWA>_ANIM_LIMITS
    dta SPRITE_<NAZWA>_RIGHT_FRAMES, SPRITE_<NAZWA>_LEFT_FRAMES, SPRITE_<NAZWA>_RIGHT_FRAMES, SPRITE_<NAZWA>_LEFT_FRAMES
```

### Krok 5: Dodanie nowej postaci do tabel silnika (NPC Dispatcher)
W pliku [engine/npc.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/npc.asm) dopisz nowo zdefiniowane tabele na **koniec** wszystkich tabel indeksowanych przeciwników. Ich pozycja musi dokładnie odpowiadać indeksowi z kroku 2:

```assembly
ENEMY_PTRS_TABLE_LO
    ...
    dta <<NAZWA>_PTRS_TABLE

ENEMY_PTRS_TABLE_HI
    ...
    dta ><NAZWA>_PTRS_TABLE

ENEMY_LIMITS_LO
    ...
    dta <<NAZWA>_ANIM_LIMITS

ENEMY_LIMITS_HI
    ...
    dta ><NAZWA>_ANIM_LIMITS

ENEMY_HEIGHTS
    ...
    dta SPRITE_<NAZWA>_RIGHT_HEIGHT
```

### Krok 6: Umieszczenie przeciwnika na ekranie
Teraz możesz umieścić przeciwnika w konfiguracji dowolnego ekranu gry (np. `world/WHITE_FIELD/screens/VILLAGE.yaml`) podając przypisane ID:
```yaml
enemies:
  - enemy: sukkub
    x: 10
    y: 5
    strategy: horizontal
    speed: medium
    color: red
```

### Krok 7: Kompilacja i uruchomienie
Uruchom kompilację i testy za pomocą polecenia:
```bash
make all
```
Plik wynikowy `dziki_zgon.xex` zostanie wygenerowany z nowo wbudowanym duszkiem.
