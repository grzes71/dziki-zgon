# Dziki Zgon - Architektura Silnika (Atari 8-bit)

Dokument opisuje wysokopoziomową architekturę silnika gry "Dziki Zgon" pisanego w asemblerze 6502 (MADS) na platformę Atari XL/XE (PAL, 50Hz).

## 1. Filozofia Projektowania
- **Determinizm (Fixed Update)**: Silnik działa w sztywnym reżimie jednej aktualizacji logiki na każdą klatkę (50 FPS).
- **Zasada Jednej Odpowiedzialności (SRP)**: Każdy system (np. wejście, kolizje, rendering) znajduje się w osobnym module.
- **Oddzielenie logiki od renderowania**: Logika gry wykonuje obliczenia, a rendering następuje bezpośrednio w przerwaniach lub jest przygotowywany tuż przed VBLANK.

---

## 2. Pętla Główna i Maszyna Stanów (main.asm)
Gra kontrolowana jest przez nadrzędną maszynę stanów zdefiniowaną w pliku `main.asm`. 
Istnieją 4 główne stany (`GAME_STATE`):
1. `STATE_TITLE` (Ekran tytułowy)
2. `STATE_STORY` (Ekrany fabularne przed grą)
3. `STATE_GAME` (Właściwa gra)
4. `STATE_OVER` (Ekran końca gry)

Przejścia pomiędzy stanami są kontrolowane przez procedurę `advance_stage`.

Dla stanu `STATE_GAME`, pętla główna pełni funkcję disptachera:
1. Czeka na sygnał nowej klatki (`Engine_WaitFrame`).
2. Uruchamia logikę silnika (`EngineScheduler`).
3. Sprawdza czy silnik zażądał zmiany stanu gry (`Engine_RequestStageAdvance`).

---

## 3. Przerwania sprzętowe (NMI)
Podczas rozgrywki włączone są obydwa typy niemaskowalnych przerwań (NMI):

### Przerwanie VBLANK (Engine_FrameHandler)
Uruchamiane 50 razy na sekundę na początku powrotu pionowego. Jest możliwie jak najkrótsze i wykonuje tylko to, co krytyczne dla synchronizacji:
- Odtwarzanie audio (`Audio_Update`) - aby zapewnić perfekcyjny timing bez rwania dźwięku.
- Podbicie licznika klatek (`FrameCounter`), na który czeka pętla główna.

### Przerwania DLI (Display List Interrupts)
Służą **wyłącznie** operacjom wizualnym na ekranie. Zmieniają rejestry sprzętowe w trakcie rysowania klatki przez układ ANTIC. W tej grze DLI realizują m.in. zmianę palety kolorów i zestawu znaków (`CHBASE`) oddzielając panel statusu od właściwego okna gry.

### Panel Statusowy (HUD)
Panel statusowy u dołu ekranu tworzą linie tekstowe w trybie ANTIC 2 (40 znaków szerokości). Wykorzystuje precyzyjną nomenklaturę:
- **Info Line** (górna linia statusowa): zawiera zarezerwowane kody 1 i 3 (indeksy 0–1), nazwę regionu przesuniętą do indeksów 2–32 (max 31 B), czas gry MM:SS przesunięty do indeksów 33–37 oraz zarezerwowane kody 5 i 6 (indeksy 38–39).
- **Message Line** (dolna linia statusowa): linia przeznaczona na teksty i komunikaty związane z interaktywnymi akcjami. Zawiera zarezerwowane kody 4 i 8 (indeksy 0–1 / adresy 40–41), treść komunikatu (indeksy 2–37 / adresy 42–77, max 36 B) oraz zarezerwowane kody 9 i 7 (indeksy 38–39 / adresy 78–79).

---

## 4. Potok Wykonawczy (Engine Scheduler)
Znajduje się w pliku `engine/engine_scheduler.asm` i determinuje absolutnie niezmienną kolejność aktualizacji wszystkich podsystemów gry na klatkę.

Wywołania:
1. `Engine_BeginFrame` - Start klatki
2. `Input_Update` - Skopiowanie stanu joysticka/przycisków do zmiennych buforujących.
3. `Player_Update` - Tłumaczenie wejścia na "intencję ruchu" (velocity/target position) gracza.
4. `NPC_Update` - Tłumaczenie AI i fizyki NPC na ich "intencję ruchu".
5. `Collision_Update` - Weryfikacja intencji ruchu ze światem i innymi aktorami (Late collision resolution). Po jej wykonaniu, obiekty mają już ostateczne pozycje X/Y.
6. `Inventory_Update` - Zarządzanie przedmiotami, zużywaniem zasobów.
7. `Dialogue_Update` - System rozmów z NPC.
8. `Quest_Update` - Weryfikacja flag misji.
9. `Animation_Update` - Kalkulowanie klatek animacji (na bazie opóźnień wynikających z `FrameCounter`).
10. `World_Update` - Zmiany ekranów, wczytywanie nowych lokacji (World Builder).
11. `Render_Prepare` - Przepisanie uaktualnionego stanu obiektów do sprzętu (np. skopiowanie grafiki Player/Missile Graphics w odpowiednie miejsce pamięci przed kolejnym VBLANK).
12. `Engine_EndFrame` - Zakończenie klatki.

Żadna z tych procedur nie powinna wykonywać blokujących nieskończonych pętli.

---

## 5. Struktura Katalogów
- `/engine` - Kompletny, modularny potok wyliczania klatki (fizyka, AI, rendering).
- `/lib` - Reużywalne biblioteki techniczne niskiego poziomu (obsługa PMG, dekompresja RLE).
- `/scenes` - Poszczególne stany gry (Title, Story, Gameover, Game). Odpowiadają za unikalne listy wyświetlania (Display Lists) oraz ich startowe init routines.
- `/gen` - Wygenerowane automatycznie dane z narzędzi graficznych lub kreatorów map (World Builder).
- `/world` - Surowe pliki i definicje świata (przetwarzane przez skrypty).
- `/music` - Odtwarzacze muzyczne.

---

## 6. Organizacja Pamięci na Stronie Zerowej (Zero Page)
Konwencja używania najszybszej pamięci adresowej $00-$FF:
- **Stan Globalny / Silnik**: Zakres `$92 - $97` przetrzymuje kluczowe zmienne współdzielone przez moduły (np. buforowany stan joysticka `InputState_Joy`, flagę zmiany ekranu `Engine_RequestStageAdvance`).
- **Scratchpad (Tymczasowa)**: Zakres m.in. `$80`, `$90 - $91` to rejestry używane na bieżąco, np. w podwójnych pętlach for jako indeksy. Żaden moduł nie może oczekiwać, że dane zachowają się tam do następnej klatki. 
- **Zmienne modułowe**: Przechowywane zazwyczaj poza Zero Page (np. instrukcje w pamięci RAM obok logiki).

---

## 7. Komunikacja Międzymodułowa (Wzorzec Mailbox)
Systemy nie wywołują się nawzajem bezpośrednio (np. `Collision_Update` nie wywołuje `Start_Dialogue`).
Zamiast tego stosowany jest wysoce zoptymalizowany dla architektury 6502 wzorzec **Mailbox** (Globalne Flagi Żądań).

- Moduł zgłaszający zdarzenie (Producent) zapisuje żądanie w przypisanej globalnej zmiennej, tzw. skrzynce (np. `sta Request_Dialogue_Start`).
- Moduł odpowiedzialny za obsługę (Konsument) w swojej kolejce działania w ramach `EngineScheduler` sprawdza tę flagę (`lda Request_Dialogue_Start`). Jeśli jest zapalona - wykonuje odpowiednią logikę i po jej przetworzeniu zeruje flagę.

Podejście to jest w pełni deterministyczne, zużywa pojedyncze cykle procesora i gwarantuje stały narzut $O(1)$ wydajności, eliminując potrzebę iterowania po uniwersalnych tablicach i kolejkach zdarzeń.
