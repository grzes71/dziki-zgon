# Optymalizacja pamięci — Strategie Architektoniczne i Plan Skalowania

Status weryfikacji z kodem: **2026-07-28** (Wersja v2.0 - zaktualizowana po refaktoryzacji stref pamięci i wyeliminowaniu nakładania ROM).

---

## 1. Stan Aktualny Pamięci (Baseline)

Dzięki konsolidacji areny VRAM, przeniesieniu czcionek i wyprostowaniu granic pamięci pod OS ROM, gra posiada **6 185 B (~6.2 KB)** bezpośrednio wolnego RAM-u.

### Podział wolnych bloków RAM:
- **`$8E3A` – `$9FFF` (4 550 B / 4.55 KB)**: **Główny, ciągły i czysty blok RAM** dedykowany pod nowe ekrany, regiony i obiekty świata.
- **`$A800` – `$A9DF` (480 B)**: Rezerwa przed odtwarzaczem RMT.
- **`$3D5E` – `$3E7F` (290 B)**: Bufor w dolnym RAM.
- **`$BEF9` – `$BFFF` (263 B)**: Rezerwa pod ROM-em BASIC.
- **`$1F2C` – `$1FFF` (212 B)**: Rezerwa w niskiej pamięci.
- **`$5F50` – `$5FFF` (176 B)** i **`$B242` – `$B2FF` (190 B)**.

---

## 2. Główne Strategie Odzysku Pamięci (Skalowanie Regionów i Świata)

Poniższe strategie pozwalają odzyskać kolejne **+8 KB do +12 KB RAM-u** na rozbudowę gry bez destabilizacji systemu:

### Strategia 1: Nakładanie pamięci Grafik Tytułowych w Runtime (Zysk: +8.2 KB RAM)
- **Problem**: Obrazek tytułowy `TitleScreen_Data` (5.9 KB pod `$0700`) oraz `GameOverScreen_Data` (2.2 KB pod `$8570`) zajmują stałe miejsce w RAM.
- **Rozwiązanie**: Podczas rozgrywki (`STATE_GAME`) grafiki tytułowa i gameover są niepotrzebne.
- **Wdrożenie**: Strefy `$0700`–`$1E35` (5.9 KB) oraz `$8570`–`$8E39` (2.2 KB) mogą być używane przez silnik jako dynamiczny bufor danych świata, obiektów i regionów aktywnej gry.
- **Potencjalny zysk**: **8 192 B (8.2 KB)** dodatkowego RAM-u podczas gry!

### Strategia 2: Kompresja i pakowanie danych World Buildera (Zysk: +1.5 KB – +3 KB)
- **Rozwiązanie**: Pakowanie struktur obiektów, bitfieldy flag interakcji oraz kompresja rzadziej używanych tabel ekranów i wyjść.
- **Wdrożenie**: Generator ASM (`world_builder/asm_generator.py`) generuje skondensowane tablice wskaźników i bity właściwości.

### Strategia 3: Odtwarzacz RMT — Stripping nieużywanych komend (Zysk: +500 B – +1 KB)
- **Rozwiązanie**: W pliku `gen/rmtplayr.asm` wyłączenie nieużywanych funkcji trackerowych (np. portamento, vibrato, zmienne filtry głośności) poprzez wyłączenie odpowiednich flag `FEAT_*`.
- **Wdrożenie**: Zmniejsza rozmiar kodu sterownika `RASTERMUSICTRACKER` z 1.3 KB do ~700 B.

### Strategia 4: Overlays kodu scen i regionów (Zysk: Bardzo duży w Etapie 2)
- **Rozwiązanie**: Kod specyficzny dla poszczególnych scen lub skomplikowanych mechanik walki/questów ładowany do wspólnego slotu kodu (`SCENE_CODE_SLOT`), podczas gdy rezydentny pozostaje tylko "kernel" silnika.

---

## 3. Zrealizowane i Otwarte Etapy Optymalizacji

### ZREALIZOWANE:
1. **[ZREALIZOWANE] Scene VRAM Arena (`$4000`–`$5E0F`)**:
   - Wszystkie sceny (Title, Game, GameOver) dzielą jedną arenę VRAM pod `$4000`.
   - Odzyskano ponad 7 KB przestrzeni operacyjnej.
2. **[ZREALIZOWANE] Usunięcie kolizji OS ROM (`$C000+`)**:
   - Wszystkie dane RLE, sprite'y i tablice zostały zamknięte poniżej `$BFFF`.
3. **[ZREALIZOWANE] Izolacja PMG i RMT**:
   - PMG przeniesione pod BASIC ROM (`$A000`), a RMT Audio usytuowane pod `$A9E0`–`$B610`.

### OTWARTE ETAPY:
- **Etap 1**: Wdrożenie nakładania danych regionów na strefę `TitleScreen_Data` w stanie `STATE_GAME` (+8.2 KB).
- **Etap 2**: Jedna mutowalna Display List pod `$3E80` zamiast osobnych struktur per scena (zysk: ~250 B).
- **Etap 3**: Wyłączenie nieużywanych komend w odtwarzaczu RMT (zysk: ~500 B).
- **Etap 4**: Overlays kodu dla rozbudowanej logiki gry i walki.

---

## 4. Lessons Learned — Kluczowe Zasady i Ograniczenia Pamięci Atari

### A. Ścisła granica OS ROM ($C000+)
- Gdy w systemie włączony jest OS ROM (`PORTB` bit 0 = 1), pamięć `$C000`–`$CFFF` (jądro OS ROM) oraz `$D000`–`$DFFF` (rejestry sprzętowe) jest **niedostępna jako RAM**.
- **Reguła**: Żadne dane (dane RLE, sprite'y, tablice świata, kod) **nie mogą przekraczać adresu `$BFFF`**. Zapis lub odczyt z obszarów powyżej `$BFFF` spowoduje odczyt instrukcji ROM systemowego Atari zamiast danych gry i zniszczy rejestry GTIA/ANTIC.

### B. Izolacja Odtwarzacza i Muzyki RMT ($A9E0 – $B610)
- Odtwarzacz RMT (`gen/rmtplayr.asm`) używa sztywnych adresów `org`:
  - `$A9E0` – `$ACFF`: Zmienne i tabele częstotliwości/głośności (`track_variables`, `frqtab`, `volumetab`).
  - `$AD00` – `$B241`: Kod wykonywalny `RASTERMUSICTRACKER`.
  - `$B300` – `$B610`: Moduł muzyczny `MODUL` (`title_music.asm`).
- **Reguła**: Zakres **`$A9E0` – `$B610`** jest w 100% zarezerwowany pod audio. Niedopuszczalne jest umieszczanie jakichkolwiek sprite'ów, obrazków czy kodu gry w tym obszarze.

### C. Sekwencyjność instrukcji `org` w `main.asm` (Brak backtracking)
- **Reguła**: Instrukcje `org` w `main.asm` muszą być ułożone w ściśle rosnącej kolejności fizycznej. Użycie `org` cofającego się do niższych adresów powoduje wygenerowanie przez Mad Assemblera bloków XEX, które podczas wczytywania przez Atari DOS/OS nadpisują wcześniej wczytane dane w RAM.

### D. Bezpieczne bufory tymczasowe (Scratchpad)
- **Reguła**: Nie wolno używać sztywnych adresów kodowych (np. `$3000`) jako buforów tymczasowych dekompresji (np. w `mRLE_Depack`), ponieważ rozbudowa kody silnika zniszczy bufor. Należy używać wyznaczonych buforów w RAM (np. `FOOTER_ADDR` = `$5E10`).
