# Dziki Zgon - Architektura Silnika (Atari 8-bit)

Dokument opisuje wysokopoziomową architekturę silnika gry "Dziki Zgon" pisanego w asemblerze 6502 (MADS) na platformę Atari XL/XE (PAL, 50Hz, 64 KB RAM).

---

## 1. Filozofia Projektowania
- **Determinizm (Fixed Update)**: Silnik działa w sztywnym reżimie jednej aktualizacji logiki na każdą klatkę (50 FPS PAL).
- **Zasada Jednej Odpowiedzialności (SRP)**: Każdy podsystem (wejście, fizyka, kolizje, interakcje, sekretne obiekty, rendering) znajduje się w osobnym, odizolowanym module w katalogu `/engine` lub `/lib`.
- **Oddzielenie Logiki od Renderowania**: Logika gry przelicza stany i pozycje w pętli ramki, a kopiowanie do pamięci PMG i rejestrów sprzętowych następuje tuż przed VBLANK (`Render_Prepare`) lub bezpośrednio w przerwaniach NMI.
- **Single Source of Truth (SSOT)**: Dane świata gry definiowane są w plikach YAML w katalogu `world/`. Kompilator `world_builder/` przetwarza je na optymalne struktury Structure-of-Arrays (SoA) w asemblerze 6502.
- **Wzorzec Mailbox (Skrzynki Pocztowe)**: Moduły komunikują się asynchronicznie poprzez globalne flagi żądań ze stałym narzutem $O(1)$.

---

## 2. Pętla Główna i Maszyna Stanów (main.asm)
Gra kontrolowana jest przez nadrzędną maszynę stanów zdefiniowaną w pliku `main.asm`. 
Istnieją 4 główne stany gry (`GAME_STATE` pod adresem `$9B` na stronie zerowej):
1. `STATE_TITLE` (0) — Ekran tytułowy
2. `STATE_STORY` (1) — Ekrany fabularne wprowadzające do gry
3. `STATE_GAME` (2) — Właściwa rozgrywka
4. `STATE_OVER` (3) — Ekran końca gry (porażka / sukces)

Przejścia pomiędzy stanami kontrolowane są przez procedurę `advance_stage`. 

Dla stanu `STATE_GAME`, pętla główna pełni funkcję dyspozytora klatek:
1. Czeka na sygnał nowej klatki (`Engine_WaitFrame`, synchronizujący się z `FrameCounter`).
2. Uruchamia potok silnika (`EngineScheduler`).
3. Sprawdza czy silnik zażądał zmiany etapu gry (`Engine_RequestStageAdvance`).

Dynamiczne przejścia między ekranami mapy wewnątrz `STATE_GAME` obsługiwane są przez flagi `REQ_SCREEN_TRANSITION` oraz `IS_PORTAL_TRANSITION` (ekran podróży `travel_screen.asm`).

---

## 3. Przerwania Sprzętowe (NMI) i Renderowanie

Podczas rozgrywki włączone są obydwa typy niemaskowalnych przerwań (NMI):

### Przerwanie VBLANK (Engine_FrameHandler)
Uruchamiane 50 razy na sekundę na początku powrotu pionowego plamki. Wykonuje wyłącznie operacje o krytycznym timingu:
1. Odtwarzanie dźwięku i efektów SFX (`Audio_Update`).
2. Ustawienie wektora DLI (`game_dli` w `VDSLST`).
3. Animację dynamicznych bajtów zestawu znaków kafelków (`animate_charset`, `update_animated_charset`).
4. Aktualizację zegara gry (`update_timer`).
5. Aktualizację wygasania komunikatów statusowych (`msg_update`).
6. Podbicie licznika klatek (`FrameCounter`).
7. Przepisanie cieni rejestrów OS (`SDLSTL`, `SDLSTH`, `SDMCTL`, `CHBAS`, `COLOR0..4`, `PCOLR0..3`) do rejestrów sprzętowych GTIA/ANTIC.
8. Powrót przez OS vector (`SYSVBV`).

### Przerwania DLI (Display List Interrupts)
Służą **wyłącznie** operacjom wizualnym na ekranie. Zmieniają rejestry sprzętowe w trakcie rysowania klatki przez układ ANTIC. W rozgrywce DLI realizują m.in. zmianę palety kolorów oraz przełączanie zestawu znaków (`CHBASE` z czcionki planszy `$6400` na czcionkę interfejsu `$6000`) oddzielając okno gry od panelu statusowego.

### Panel Statusowy (HUD) i System Komunikatów
Panel statusowy u dołu ekranu tworzą linie tekstowe w trybie ANTIC 2 (40 znaków szerokości):
- **Info Line** (górna linia statusowa): 
  - pozycje 0–1: zarezerwowane znaki ramki
  - pozycje 2–21: nazwa regionu (max 20 B)
  - pozycje 22–31: Ekwipunek `[........]` (10 B: `[` kod 59, 8 slotów po kodzie 14, `]` kod 61)
  - pozycja 32: spacja odstępu
  - pozycje 33–37: czas gry MM:SS
  - pozycje 38–39: zarezerwowane znaki ramki
- **Message Line** (dolna linia statusowa): 
  - pozycje 0–1: zarezerwowane kody ramek (4 i 8)
  - pozycje 2–37: treść komunikatów i wyników interakcji (`MSG_STATE`, max 36 B)
  - pozycje 38–39: zarezerwowane kody ramek (9 i 7)

---

## 4. Potok Wykonawczy (Engine Scheduler)
Potok zlokalizowany w pliku `engine/engine_scheduler.asm` determinuje absolutnie niezmienną kolejność aktualizacji wszystkich podsystemów gry w każdej klatce:

```mads
.proc EngineScheduler
    jsr Engine_BeginFrame
    jsr Input_Update
    jsr Player_Update
    jsr NPC_Update
    jsr Collision_Update
    jsr IIS_Update
    jsr Secret_Check_Pickup
    jsr Inventory_Update
    jsr Dialogue_Update
    jsr Quest_Update
    jsr Animation_Update
    jsr World_Update
    jsr Render_Prepare
    jsr Engine_EndFrame
    rts
.endp
```

Kolejne etapy potoku:
1. `Engine_BeginFrame` — Inicjalizacja klatki.
2. `Input_Update` — Zbuforowanie stanu joysticka `PORTA` i przycisku `TRIG0`.
3. `Player_Update` — Przeliczenie intencji ruchu gracza.
4. `NPC_Update` — Przeliczenie AI, tras i pozycji przeciwników/NPC.
5. `Collision_Update` — Weryfikacja intencji ruchu ze ścianami oraz innymi aktorami. Ustalenie ostatecznych pozycji X/Y.
6. `IIS_Update` — System Interaktywnego Badania Obiektów (Interactive Inspection System).
7. `Secret_Check_Pickup` — Weryfikacja i podnoszenie sekretnych przedmiotów na mapie.
8. `Inventory_Update` — Aktualizacja stanu ekwipunku i zużywania przedmiotów.
9. `Dialogue_Update` — Logika okien i kwestii dialogowych.
10. `Quest_Update` — Weryfikacja postępu i flag zadań.
11. `Animation_Update` — Wyliczanie klatek animacji obiektów i postaci.
12. `World_Update` — Obsługa zmian ekranów i przejść portalami.
13. `Render_Prepare` — Przygotowanie buforów graficznych i pamięci PMG przed VBLANK.
14. `Engine_EndFrame` — Zakończenie obliczeń klatki.

Żadna z powyższych procedur nie wykonuje pętli blokujących.

---

## 5. Struktura Projektu i Katalogów

| Katalog / Plik | Rola i Zawartość |
|---|---|
| `/engine` | Modularny potok gry (scheduler, input, player, npc, collision, iis, secret_object, inventory, dialogue, quest, animation, world, render, travel_screen, msg_line, charset_anim, audio). |
| `/lib` | Reużywalne biblioteki techniczne (`pmg.asm`, `rle.asm`, `world_renderer.asm`). |
| `/scenes` | Moduły stanów gry (Title, Story, Game, GameOver). Każda scena eksportuje procedury `_init` i `_run`. |
| `/gen` | Auto-generated dane i kod ASM wygenerowany przez narzędzia (pliki `.asm`, `.bin`, `.inc`, `.rle`) — **nie edytować ręcznie**. |
| `/world` | SSOT w formacie YAML (`world.yaml`, `objects.yaml`, katalogi regionów z `region.yaml` oraz `screens/*.yaml`). |
| `/world_builder` | Kompilator świata w Pythonie (`parser.py`, `model.py`, `validator.py`, `asm_generator.py`). |
| `/world_studio` | Edytor map i ekranów w PySide6 zapisujący bezpośrednio do plików YAML. |
| `/object_studio` | Edytor kafelków i właściwości obiektów świata w PySide6. |
| `/music` | Odtwarzacz RMT tracker oraz moduły muzyczne i efekty SFX. |
| `/fonts` | Pliki binarne czcionek fontów (`.fnt`). |
| `/scripts` | Skrypty narzędziowe i konwertery (`img2asm.py`, `fnt2asm.py`, `rle_compress_text.py`, `check_memory.py`). |
| `/tests` | Zestaw testów jednostkowych i integracyjnych (`pytest` + emulator py65 6502). |
| `/docs` | Specyfikacja sprzętowa Atari oraz konspekt gry. |
| `main.asm` | Punkt startowy, maszyna stanów, inicjalizacja sprzętu, definicje Display List. |
| `hardware.asm` | Equates rejestrów sprzętowych Atari i stałe projektowe. |
| `zeropage.asm` | Alokacja zmiennych pamięci Zero Page (`$80–$A9`). |

---

## 6. Organizacja Pamięci na Stronie Zerowej (Zero Page `$00–$FF`)

Najszybszy obszar pamięci adresowej adresowany jest następująco:

- **`$80 – $85` (Wskaźniki pomocnicze & RLE)**: `SRC_TMP` (`$80-$81`), `SRC_PTR` (`$82-$83`), `DST_PTR` (`$84-$85`).
- **`$86 – $8A` (Wskaźniki Świata)**: `SCREEN_PTR` (`$86-$87`), `TILE_PTR` (`$88-$89`), `GAME_SCREEN_ID` (`$8A`).
- **`$8B – $91` (Iteratory Rysowania)**: `OBJ_X` (`$8B`), `OBJ_Y` (`$8C`), `OBJ_W` (`$8D`), `OBJ_H` (`$8E`), `OBJ_CODE` (`$8F`), `TMP_X` (`$90`), `TMP_Y` (`$91`).
- **`$92 – $95` (Zmienne Logiki Klatki)**: `FrameCounter` (`$92`), `InputState_Joy` (`$93`), `InputState_Trig` (`$94`), `Engine_RequestStageAdvance` (`$95`).
- **`$96 – $9A` (Zmienne Aktorów & PMG)**: `PMG_PTR` (`$96-$97`), `ACTOR_TMP_X` (`$98`), `ACTOR_TMP_Y` (`$99`), `ACTOR_TMP_HEIGHT` (`$9A`).
- **`$9B` (Stan Gry)**: `GAME_STATE` (`$9B`).
- **`$9C – $A1` (Przejścia Ekranów)**: `REQ_SCREEN_TRANSITION` (`$9C`), `NEW_SCREEN_ID` (`$9D`), `NEW_ACTOR_X/Y` (`$9E-$9F`), `ENEMY_COUNT_TMP` (`$A0`), `CURRENT_ACTOR` (`$A1`).
- **`$A2 – $A6` (Interfejs i Portale)**: `MSG_STATE` (`$A2`), `GAME_RESULT_STATUS` (`$A3`), `GO_RAINBOW_PTR` (`$A4-$A5`), `IS_PORTAL_TRANSITION` (`$A6`).
- **`$A7 – $A9` (Mailboxy Efektów SFX)**: `Request_SFX_Step` (`$A7`), `Request_SFX_Item` (`$A8`), `Request_SFX_Interact` (`$A9`).
- **`$CB – $DD` (Zmienne Odtwarzacza RMT)**: Rejestry robocze odtwarzacza muzyki RMT.

---

## 7. Komunikacja Międzymodułowa (Wzorzec Mailbox)

Moduły gry nie wywołują się nawzajem bezpośrednio. Zamiast tego stosowany jest wysoce zoptymalizowany dla 6502 wzorzec **Mailbox (Globalne Flagi Żądań)**:

1. **Producent**: Moduł zgłaszający zdarzenie zapisuje żądanie w dedykowanej zmiennej na stronie zerowej (np. `sta Request_SFX_Step` lub `sta REQ_SCREEN_TRANSITION`).
2. **Konsument**: Moduł odpowiedzialny za obsługę zdarzenia (np. `Audio_Update` lub `World_Update`) podczas swojej kolei w `EngineScheduler` lub VBLANK odczytuje flagę (`lda Request_SFX_Step`). Jeśli flaga jest ustawiona, wykonuje właściwą akcję i czyści flagę (`sta Request_SFX_Step`).

Wzorzec ten gwarantuje determinizm, brak wywołań rekurencyjnych, zerowy narzut stosu oraz stałą wydajność $O(1)$.

---

## 8. Automatyzacja Budowania i Weryfikacji (Build Chain & Testing)

Projekt wykorzystuje system `Make` połączony z natywnymi narzędziami w Pythonie:
- **Pełen cykl kompilacji (`make all`)**:
  ```
  texts → sprites → bg → go → fonts → music → world → test → xex → check_memory
  ```
- **Kompilator Świata (`world_builder`)**: Automatycznie waliduje ograniczenia spójności (graf przejść, zasięgi obiektów, unikalne identyfikatory) i generuje pliki `.asm` / `.inc` w `gen/world/`.
- **Integracyjny Test Parzystości VRAM (`tests/test_world_integration.py`)**: Weryfikuje za pomocą emulatora py65, że 6502 assembler `lib/world_renderer.asm` i Pythonowy parser wyliczają identyczny 480-bajtowy bufor VRAM dla każdego ekranu.
- **Automatyczna Walidacja Pamięci (`scripts/check_memory.py`)**: Po kompilacji analizuje plik symboli `game.lab` i synchronizuje plik `MEMORY_USAGE.md`.

