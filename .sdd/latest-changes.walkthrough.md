# Walkthrough: Optymalizacja Kolizji przy Użyciu Siatki Bitowej (Bit-Grid Collision Map)

Wdrożyłem z powodzeniem optymalizację kolizji opartą na siatce bitowej o wymiarach 40×12 pól (dokładnie 60 bajtów bufora w pamięci RAM). 

Dzięki temu silnik gry nie musi przeszukiwać listy kilkudziesięciu lub ponad 100 obiektów na planszy w locie w każdej klatce obrazu. Zamiast tego test kolizji duszka sprowadza się do błyskawicznego sprawdzenia kilku bitów w siatce w stałym czasie $O(1)$. Rozwiązuje to wszelkie problemy wydajnościowe/timingowe na ekranach o dużym zagęszczeniu obiektów (takich jak Bagno).

---

## Dokonane Zmiany

### 1. Zmienne globalne w [actor.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/actor.asm)
- Dodałem bufor siatki kolizji w pamięci RAM:
  ```asm
  COLLISION_GRID
      .ds 60
  ```

### 2. Generowanie siatki w [world_renderer.asm](file:///c:/Users/lib/world_renderer.asm)
- Do funkcji `build_screen` dodałem czyszczenie bufora `COLLISION_GRID` przy każdym wejściu na dany ekran.
- Wdrożyłem procedurę `mark_object_blocking`, która na podstawie rozmiaru i pozycji obiektu w wierszach/kolumnach mapy ustawia odpowiednie bity w siatce kolizji, jeżeli obiekt posiada flagę `blocking` (`Bit 7` w `OBJ_FLAGS`).
- Zabezpieczyłem rejestr `X` (`OBJ_CODE`) po wywołaniu procedury zaznaczania, zapobiegając błędnemu renderowaniu kafelków.

### 3. Weryfikacja kolizji w [collision.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/collision.asm)
- Całkowicie przepisałem procedurę `Check_Objects_Collision`, zastępując pętlę po liście obiektów szybkim przeliczeniem współrzędnych pikselowych duszka na współrzędne wierszy i kolumn siatki:
  - Przeliczenie X: `Grid_X1 = (ACTOR_TMP_X - 48) / 4` i `Grid_X2 = (ACTOR_TMP_X - 48 + 7) / 4` (przesunięcia bitowe w prawo o 2 pozycje).
  - Przeliczenie Y: `Grid_Y1 = (ACTOR_TMP_Y - 32) / 16` i `Grid_Y2 = (ACTOR_TMP_Y - 32 + ACTOR_TMP_HEIGHT - 1) / 16` (poprawione przesunięcia bitowe z bazowym offsetem 32 scanline'ów odpowiadającym początkowi rysowania mapy).
  - Pętla testuje odpowiednie bity za pomocą lookup-table masek `bit_masks dta $80, $40, $20...`.
  - Wdrożyłem bezpieczne mechanizmy ograniczające (clamping) indeksów wierszy do `0..11` oraz kolumn do `0..39`, co zapobiega wyjściu poza bufor siatki.
- Zmodyfikowałem mocki w testach jednostkowych (`world_renderer_test.asm` oraz `world_integration_test.asm`), aby pomyślnie mockowały zmienną `COLLISION_GRID` w testach asemblera.

### 4. Korekta startowej pozycji Y duszka w [game.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/scenes/game/game.asm)
- Poprawiłem dodawanie początkowego przesunięcia (offsetu) dla pozycji gracza w pionie. Rysowanie planszy rozpoczyna się od scanline'u **32**, a nie **56** (ponieważ 24 puste linie w Display Liście liczone są od domyślnego startu rysowania układu ANTIC na linii 8: `8 + 24 = 32`). 
- Zmieniłem `adc #56` na `adc #32`, co sprawiło, że po ustawieniu współrzędnych startowych `x: 0, y: 0` w `world.yaml` gracz pojawia się idealnie na samej górze (w wierszu 0, kolumnie 0), bez żadnego przesunięcia w pionie.

### 5. Animowanie znaków charsetu (rolowanie w poziomie w VBLANK)
- Dodałem nowy plik [charset_anim.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/charset_anim.asm) z procedurą `animate_charset`.
- Procedura ta w tle (podczas przerwania VBLANK, o ile jesteśmy w stanie `STATE_GAME`) odlicza czas i wykonuje poziome rolowanie o dwa bity w lewo (`ROL ROL` poprzez szybkie bezwarunkowe instrukcje `asl / adc #0 / asl / adc #0`) dla określonych znaków z zestawu `game.fnt` (znaki `$05`, `$20`, `$40`, `$65`, `$66`).
- Zaimplementowałem tablice konfiguracji:
  - `anim_char_ids`: indeksy znaków do animacji.
  - `anim_char_speeds`: prędkość animacji (wartość w klatkach – domyślnie 10 dla każdego).
  - `anim_char_counters`: liczniki odliczające czas dla każdego znaku indywidualnie.
- Dołączyłem plik w [engine.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/engine.asm) i wywołałem funkcję w głównym handelerze przerwań `Engine_FrameHandler` w [engine_frame.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/engine/engine_frame.asm).
- Użycie rejestru `SRC_PTR` w przerwaniu jest w pełni bezpieczne dla głównego wątku gry dzięki zapisaniu i odtworzeniu go na stosie (`pha` / `pla`).

### 6. Testy integracyjne w Pythonie z użyciem Py65
- Stworzyłem plik testowy [test_charset_anim.py](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/tests/test_charset_anim.py) oraz asemblerowy plik pomocniczy [charset_anim_test.asm](file:///c:/Users/grzes/Documents/Projects/witcher-atari-game/tests/charset_anim_test.asm) w katalogu `tests/`.
- Testy emulują działanie kodu 6502 na wirtualnym procesorze Py65 i weryfikują dwa scenariusze:
  1. `test_charset_anim_counters_decrement`: sprawdza, czy liczniki klatek prawidłowo dekrementują się co klatkę bez uruchamiania animacji, jeśli nie osiągnęły wartości `0`.
  2. `test_charset_anim_rotate_and_reset`: sprawdza, czy po osiągnięciu wartości `1` licznik resetuje się do domyślnej prędkości (np. `12`), dane wybranego znaku (np. `$05`) są prawidłowo rolowane w lewo o 2 bity (`%10100101` -> `%10010110`), a inne znaki oraz wskaźniki Zero Page (`SRC_PTR`) pozostają nienaruszone.

---

## Wyniki Testów

Wszystkie automatyczne testy jednostkowe i integracyjne przeszły pomyślnie:
```bash
============================= 42 passed in 1.23s ==============================
```
Gra została pomyślnie skompilowana do pliku `dziki_zgon.xex`.
