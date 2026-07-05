# Plan: Rozszerzenie testów dla Wiedźmin: Dziki Zgon

## TL;DR

Projekt posiada już solidne fundamenty testowe (smoke test Altirry, testy konwerterów graficznych, walidację mapy pamięci), ale brakuje testów jednostkowych samego kodu 6502 oraz automatycznej weryfikacji binarnego pliku XEX. Plan zakłada wdrożenie testów w priorytetowej kolejności, zaczynając od tych, które dają największy zwrot z inwestycji: testy RLE w py65, weryfikacja struktury XEX oraz testy dekompresji assetów. Celem jest wyłapanie problemów (pamięć, DLI, maszyna stanów, RLE) zanim ujawnią się one dopiero w emulatorze.

---

## Fazy i kroki

### Faza 1: Infrastruktura testowa 6502 (py65)

**Cel:** Umożliwić uruchamianie fragmentów kodu asemblera w izolacji bez konieczności uruchamiania emulatora.

1. **Utworzenie helpera py65** — moduł `tests/py65_helper.py` z funkcjami:
   - `load_xex(memory, path)` — ładuje dziki_zgon.xex do pamięci emulatora zgodnie z nagłówkami segmentów.
   - `set_zp_pointer(memory, addr, value)` — ustawia 16-bitowy wskaźnik w page zero (`SRC_PTR`, `DST_PTR`).
   - `run_until_rts(cpu, memory, max_cycles)` — wykonuje kod do `RTS` lub limitu cykli.
   - `run_interrupt_handler(cpu, memory, vector_addr)` — symuluje wywołanie DLI (zachowuje rejestry, ustawia PC, wykonuje do `RTI`).

2. **Testy depackera RLE** — plik `tests/test_rle_py65.py`:
   - Załadowanie skompresowanego tekstu `text_gameover` i dekompresja do bufora; porównanie z oczekiwanymi 32 bajtami.
   - Załadowanie `text_title` i dekompresja do 320 bajtów.
   - Załadowanie `text_story` i dekompresja do 320 bajtów.
   - Test graniczny: dane RLE z samym EOF (`$80`) — depacker powinien natychmiast zwrócić `RTS`.
   - Test ochronny: zły bajt flagi (`$FF`) — weryfikacja, że depacker nie wchodzi w nieskończoną pętlę (limit cykli).

3. **Testy maszyny stanów** — plik `tests/test_state_machine_py65.py`:
   - Wywołanie `advance_stage` dla każdego stanu początkowego (`STATE_TITLE`, `STATE_STORY`, `STATE_GAME`, `STATE_OVER`) i sprawdzenie, czy `GAME_STATE` przechodzi zgodnie z tablicą `stage_order`.
   - Test wrap-around: po `STATE_OVER` następuje `STATE_TITLE`.
   - Test nieprawidłowego stanu (np. `$FF`) — fallback do `STATE_TITLE`.

4. **Testy `system_init`** — plik `tests/test_system_init_py65.py`:
   - Wywołanie `system_init` i weryfikacja, że `DMACTL = 0`, `NMIEN = 0`, `GRACTL = 0`, `PORTB = $FF`.
   - Weryfikacja wyzerowania rejestrów GTIA `$D000-$D011`.

### Faza 2: Weryfikacja binarnego pliku XEX

**Cel:** Wykrywać błędy w adresach ładowania, nakładające się segmenty i nieprawidłowe nagłówki.

5. **Moduł walidacji XEX** — plik `scripts/validate_xex.py`:
   - Parsowanie nagłówków `$FF $FF` i segmentów start/end.
   - Sprawdzenie, że `start < end` dla każdego segmentu.
   - Sprawdzenie braku nakładania się segmentów (z wyjątkiem celowego overlayu, jeśli występuje).
   - Weryfikacja, że ostatni segment zawiera `run start` wskazujący na `$2000`.
   - Obliczenie całkowitego rozmiaru kodu + danych i porównanie z budżetem (alert przy > 32 KB).

6. **Testy XEX** — plik `tests/test_xex_structure.py`:
   - Wywołanie `scripts/validate_xex.py` na dziki_zgon.xex jako część zestawu `pytest`.
   - Testy negatywne z mockowanymi błędnymi plikami XEX.

### Faza 3: Testy assetów i generatorów

**Cel:** Upewnić się, że wygenerowane dane (RLE, czcionki, obrazy) są poprawne i mają oczekiwane rozmiary.

7. **Testy dekompresji assetów** — plik `tests/test_rle_assets.py`:
   - `title.rle` dekompresuje się do 7696 B.
   - `gameover.rle` dekompresuje się do 2784 B.
   - `text_title` dekompresuje się do 320 B.
   - `text_story` dekompresuje się do 320 B.
   - `text_gameover` dekompresuje się do 32 B.
   - Wszystkie testy używają wspólnej implementacji dekompresji w Pythonie (kopia logiki z rle.asm).

8. **Testy statyczne assetów** — plik `tests/test_assets.py`:
   - font.fnt i game.fnt mają dokładnie 1024 B.
   - title.png ma wymiary 160×192 i ≤ 4 kolorów.
   - game-over.png ma wymiary zgodne z trybem ANTIC D (128×96).
   - moon.png i dziki-zgon.png mają odpowiednie wymiary dla sprite'ów PMG.
   - Teksty w `texts/*.txt` nie zawierają znaków spoza mapy `POLISH_CHARS` w rle_compress_text.py.

### Faza 4: Rozszerzenie smoke testu emulatora

**Cel:** Wykrywać problemy wizualne i regresje w przejściach między scenami.

9. **Porównanie zrzutów ekranu** — plik `atari_smoke_test/screenshot.py`:
   - Po uruchomieniu Altirry i odczekaniu `timeout` wykonanie zrzutu ekranu (`PIL.ImageGrab`).
   - Porównanie z referencyjnym zrzutem (hash percepcyjny lub proste porównanie histogramu).
   - Test wykrywa czarne ekrany, złe kolory lub brak inicjalizacji.

10. **Wstrzykiwanie inputu** — plik `atari_smoke_test/input_injector.py`:
    - Wysyłanie klawisza FIRE (spacja lub skonfigurowany klawisz) do okna Altirry przez `pyautogui` lub `SendKeys`.
    - Automatyczna sekwencja: title → story → game → gameover → title z weryfikacją, że emulator nie uległ awarii po każdym przejściu.

11. **Integracja z CLI** — rozszerzenie cli.py:
    - Opcja `--reference-screenshot` do porównania.
    - Opcja `--auto-input` do włączenia automatycznych przejść.

### Faza 5: Testy timingowe i regresyjne

**Cel:** Zapobiegać artefaktom graficznym i niekontrolowanemu wzrostowi kodu.

12. **Testy budżetu cykli DLI** — plik `tests/test_dli_timing.py`:
    - Wykonanie każdego handlera DLI (`DLI_Handler`, `TEXT_DLI`, `DLI_Gameover`, `game_dli_1`, `game_dli_2`) w py65.
    - Pomiar liczby cykli między wejściem a `RTI`.
    - Alert, jeśli którykolwiek handler przekracza bezpieczny próg (np. 100 cykli przed `WSYNC`).

13. **Testy mapy pamięci** — plik `tests/test_memory_map.py`:
    - Wczytanie `game.lab` i porównanie adresów kluczowych symboli (`start`, `RLE_Depack`, `DLIST_TITLE`, `VRAM_ARENA`, `PMBASE_ADDR`) z baseline w `scripts/memory_baseline.json`.
    - Wyliczenie wolnych bloków RAM i alert przy zmniejszeniu któregokolwiek z nich.
    - Sprawdzenie, czy żadne dwa symbole nie nachodzą na siebie.

14. **Aktualizacja check_memory.py**:
    - Rozszerzenie o generowanie/aktualizację `scripts/memory_baseline.json`.
    - Integracja z `make all` pozostaje bez zmian.

---

## Relevant files

- rle.asm — logika dekompresji RLE do testowania w py65.
- main.asm — maszyna stanów (`advance_stage`, `system_init`, `main_loop`).
- hardware.asm — definicje rejestrów i stałych pamięci.
- dziki_zgon.xex — plik wykonywalny do walidacji struktury.
- `gen/*.rle`, `gen/*_text.asm` — skompresowane assety do testów dekompresji.
- launcher.py, process.py — smoke test do rozszerzenia.
- check_memory.py — walidacja mapy pamięci do rozbudowy.
- Makefile — integracja nowych testów z procesem buildu.

---

## Verification

1. **Build przechodzi:** `make all` kończy się sukcesem i generuje dziki_zgon.xex.
2. **Pytest przechodzi:** `pytest tests/` wykonuje wszystkie nowe testy bez błędów.
3. **XEX jest poprawny:** `python scripts/validate_xex.py dziki_zgon.xex` zwraca kod wyjścia 0.
4. **Smoke test działa:** `python -m atari_smoke_test.main --xex dziki_zgon.xex --timeout 5` zwraca `Smoke Test PASSED`.
5. **RLE dekompresuje się:** testy `tests/test_rle_py65.py` i `tests/test_rle_assets.py` potwierdzają poprawność wszystkich assetów.
6. **Mapa pamięci jest stabilna:** `tests/test_memory_map.py` nie wykazuje regresji względem baseline.
7. **DLI mieści się w budżecie:** `tests/test_dli_timing.py` nie zgłasza przekroczenia cykli.

---

## Decisions

- **Priorytet P0:** testy RLE w py65 i walidacja XEX — największy potencjał wykrycia błędów zawieszających grę.
- **Priorytet P1:** testy assetów RLE i rozszerzenie smoke testu o screenshoty — wykrywają regresje wizualne i w rozmiarach danych.
- **Priorytet P2:** testy maszyny stanów i timingowe DLI — uzupełniają pokrycie logiki i wydajności.
- **Priorytet P3:** baseline mapy pamięci — chroni przed niekontrolowanym wzrostem kodu.
- **Nie w zakresie:** testy na prawdziwym sprzęcie Atari, pełna emulacja GTIA/ANTIC/POKEY w py65 (py65 nie emuluje tych układów).
- **Założenie:** wszystkie nowe testy Pythona używają istniejącego środowiska wirtualnego .venv i zależności z requirements.txt.

---

## Further Considerations

1. **Czy smoke test powinien być uruchamiany automatycznie w CI?** Obecnie wymaga Altirry na Windows. Rekomendacja: uruchamiać go lokalnie i/lub na maszynie z zainstalowanym emulatorem; pozostałe testy (py65, pytest) mogą działać w CI.
2. **Czy warto dodać testy porównawcze obrazów (pixel-perfect) dla każdej sceny?** Referencyjne zrzuty ekranu są podatne na drobne różnice w emulatorze. Rekomendacja: zacząć od detekcji czarnego ekranu i histogramu, a pixel-perfect rozważyć później.
3. **Czy rozszerzyć py65 o prosty model pamięci GTIA?** Dla testów DLI wystarczy obserwacja zapisów do `$D0xx`, ale pełna weryfikacja wizualna wymagałaby emulacji ANTIC/GTIA. Rekomendacja: na razie testować DLI pod kątem braku nieskończonych pętli i poprawnego `RTI`.

