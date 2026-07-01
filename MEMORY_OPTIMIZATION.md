# Optymalizacja pamięci — wnioski architektoniczne

Poniższe punkty wynikają z analizy aktualnej struktury kodu i mapy RAM (main + sceny + audio + DL).
Skupienie: nie pojedyncze bajty, tylko zmiany architektury, ktore uwalniaja najwiecej pamieci bez destabilizacji projektu.

## 1) Najwiekszy zysk: wspolna arena pamieci scen (Scene VRAM Arena)

## Problem

Bufory ekranow dla scen sa rezerwowane statycznie, mimo ze sceny nie dzialaja jednoczesnie:

- title bitmap: $4000-$5E0F (7696 B)
- game screen: $6400-$67BF (960 B)
- gameover screen: $7000-$7ADF (2784 B)

## Refaktoryzacja

Wprowadzic jeden wspolny obszar roboczy dla aktywnej sceny i jawny model ownership:

- scena przy wejsciu "claimuje" bufor
- scena przy wyjsciu zwalnia bufor
- kolejna scena nadpisuje ten sam obszar

## Realny efekt (ZREALIZOWANO)

- **[ZREALIZOWANE]** Zdefiniowano `VRAM_ARENA = $4000`. Ekrany `title.bin` i `gameover.bin` zostały usunięte ze statycznych, twardych przydziałów w XEX i zastąpione wersjami skompresowanymi RLE ładowanymi na koniec pamięci (pod `$8000`).
- **[ZREALIZOWANE]** Sceny wywołują rozpakowywanie z RLE do `VRAM_ARENA` podczas swoich rutyn `_init`.
- Odzyskano ponad **7 KB ciągłej przestrzeni** w dolno-środkowym RAM (zakres `$6400 - $7FFF`), co daje fenomenalną przestrzeń pod właściwy silnik gry. Wymagało to ok. 7.6 KB w górnym RAM na przechowanie skompresowanych grafik, redukując jednoczesnie rozmiar pliku XEX.

---

## 2) Kontrakty scen: init/run/exit + deklaracja zajetego RAM

## Problem

Sceny maja init/run, ale brak centralnie egzekwowanego kontraktu pamieci.
Efekt: latwo pozostawic trwale zaleznosci i blokowac duze bloki RAM.

## Refaktoryzacja

Dodac tablice deskryptorow scen:

- pointers do init/run/exit
- zakres(y) RAM wymagane przez scene
- flaga: czy scena wymaga PMG

Manager scen w main.asm powinien byc jedynym miejscem, ktore wlacza/zwalnia zasoby.

## Realny efekt

Bezposredni zysk pamieci zalezy od wdrozenia punktu 1, ale to kluczowy fundament pod dalsze oszczednosci i overlays.

## Ryzyko

Niskie. Zysk glownie w kontroli i dalszej skalowalnosci.

---

## 3) PMG jako zasob scenowy + wariant double-line

## Problem

PMG jest trzymane w modelu stalej rezerwacji, mimo ze czesc scen PMG nie potrzebuje.

## Refaktoryzacja

- traktowac PMG jako zasob aktywowany per scena
- sprawdzic wariant double-line, jesli jakosc wizualna pozostaje akceptowalna

## Realny efekt

- do ~1 KB oszczednosci przy double-line PMG
- dodatkowo lepsza architektura ownership (mniej stale "zajetych" obszarow)

## Ryzyko

Srednie (wizualne). Wymaga testow pozycji/wysokosci sprite'ow.

---

## 4) Jedna mutowalna Display List zamiast kilku rezydentnych

## Problem

Display listy sa utrzymywane jako zestaw wielu struktur w RAM.

## Refaktoryzacja

Utrzymywac jedna DL i patchowac tylko elementy zalezne od sceny:

- LMS
- tryby linii
- DLI flagi

## Realny efekt

Typowo ~150-250 B odzysku oraz prostsze przejscia miedzy scenami.

## Ryzyko

Niskie/srednie. Wymaga ostroznego testu timingow DLI.

---

## 5) Overlays kodu scen (etap 2 rozwoju)

## Problem

Kod wszystkich scen jest stale rezydentny.
Przy obecnym rozmiarze to akceptowalne, ale przy pelnej grze (regiony, AI, walka, questy) szybko zabraknie miejsca.

## Refaktoryzacja

- zostawic w pamieci "kernel" (main, scheduler, common libs)
- kod aktywnej sceny doladowywac do wspolnego slotu kodu

## Realny efekt

Teraz: umiarkowany. Docelowo: bardzo duzy (to glowna dzwignia skalowania projektu).

## Ryzyko

Srednie/wysokie. Wymaga loadera i dyscypliny segmentacji kodu.

---

## 6) Drobne porzadki (male zyski, warto zrobic)

- pakowanie flag wejscia FIRE z wielu scen do jednego bajtu bitowego
- redukcja duplikacji logiki "wait-release-then-press"
- konsolidacja drobnych stalych/tablic

Efekt: pojedyncze bajty do dziesiatek bajtow, ale poprawa czytelnosci i mniej bledow przy refaktoryzacjach.

---

## 7) Opcja wysokiego ryzyka: OS ROM OFF

Mozna odzyskac dodatkowe okno RAM kosztem przejecia odpowiedzialnosci za obsluge systemowa (NMI/VBI, stabilnosc, zgodnosc).

Rekomendacja: traktowac jako etap 3, dopiero po wdrozeniu zmian 1-4.

---

## Priorytet wdrozenia (praktyczny plan)

1. Scene VRAM Arena + jawne ownership buforow.
2. Kontrakty scen (init/run/exit + wymagania zasobow).
3. Jedna mutowalna Display List.
4. PMG double-line (jesli testy wizualne przejda).
5. Overlays kodu scen przy rozbudowie gameplayu.

---

## Szacunkowy efekt po pierwszym etapie (1-4)

Konserwatywnie: kilka KB odzyskanego RAM i znacznie mniejsza fragmentacja logiczna.
Najwazniejsze: po tych zmianach projekt bedzie gotowy na dalsze skalowanie bez "walki o kazdy bajt" przy kazdej nowej mechanice.

---

# Actionable migration checklist z konkretnymi adresami

Ten plan zaklada utrzymanie kompatybilnosci z obecnym ukladem projektu i stopniowe, bezpieczne wdrazanie.

## Etap 0 - Baseline i kontrola regresji

- [ ] Zapisz baseline mapy pamieci z aktualnego builda.
- [ ] Potwierdz dzialanie przejsc title -> story -> game -> gameover -> title.
- [ ] Potwierdz stabilnosc audio (start/stop) w kazdej zmianie stanu.

Cel: miec punkt odniesienia do porownania po kazdym etapie.

## Etap 1 - Scene VRAM Arena (najwiekszy zysk, niski risk)

Adresy docelowe:

- SCENE_ARENA_BASE: $4000
- SCENE_ARENA_END: $5E0F
- SCENE_TEXT_SHARED: $5E10-$5F4F (bez zmian)

Mapowanie scen po migracji:

- title screen buffer -> $4000-$5E0F
- game screen buffer -> $4000-$43BF (w ramach tej samej areny)
- gameover screen buffer -> $4000-$4ADF (w ramach tej samej areny)

Pamiec uwolniona po tym kroku:

- $6400-$67BF (960 B)
- $7000-$7ADF (2784 B)
- razem: 3744 B

Checklist:

- [ ] Ustaw GAME_SCREEN na $4000.
- [ ] Ustaw GO_SCREEN na $4000.
- [ ] Usun stale rezerwacje ekranow game/gameover poza arena.
- [ ] Zostaw FOOTER_ADDR na $5E10 jako wspoldzielony tekst.

Definition of done:

- [ ] Wszystkie 4 sceny wyswietlaja sie poprawnie.
- [ ] Brak artefaktow po wielokrotnym cyklu przejsc.
- [ ] Mapa pamieci pokazuje wolne $6400-$67BF i $7000-$7ADF.

## Etap 2 - Jeden bufor Display List

Adresy docelowe:

- DLIST_WORK_BASE: $3E80
- DLIST_WORK_END: $3EFF (128 B budzetu)

Pamiec uwolniona po tym kroku:

- docelowo z obecnych 367 B do 128 B
- oszczednosc orientacyjna: 239 B

Checklist:

- [ ] Zastap wiele statycznych DL jednym buforem roboczym.
- [ ] W scene_init patchuj tylko LMS, mode lines i DLI flags.
- [ ] Zachowaj JVB na koncu bufora roboczego.

Definition of done:

- [ ] Wszystkie sceny laduja poprawny DL z tego samego adresu $3E80.
- [ ] DLI timing pozostaje stabilny (bez migotania/rozjechania kolorow).

## Etap 3 - Kontrakty scen i ownership zasobow

Adresy docelowe (proponowane):

- SCENE_FLAGS: $86 (ZP)
- ACTIVE_SCENE: $87 (ZP)
- SCENE_REQ_MASK: $88 (ZP)
- SCENE_TMP_PTR: $89-$8A (ZP)

Opis:

Tablica deskryptorow scen ma opisywac:

- init pointer
- run pointer
- exit pointer
- wymagane zasoby (arena, PMG, DLI, audio)

Checklist:

- [ ] Dodaj deskryptory scen i jednolity dispatcher.
- [ ] Przenies aktywacje/dezaktywacje zasobow do managera scen.
- [ ] Usun duplikacje setup/teardown rozproszone po scenach.

Definition of done:

- [ ] Kazda scena uzywa tego samego protokolu wejsciowy/wyjsciowy.
- [ ] Brak "wyciekow" stanu (np. zostawionych DLI/NMI/PMG) po wyjsciu ze sceny.

## Etap 4 - PMG profile per scena + tryb double-line

Adresy docelowe dla double-line (proponowane):

- MISSILES: $A300-$A37F
- PLAYER0: $A380-$A3FF
- PLAYER1: $A400-$A47F
- PLAYER2: $A480-$A4FF
- PLAYER3: $A500-$A57F

Pamiec uwolniona po tym kroku:

- nowo wolne: $A580-$A7FF (640 B)
- dodatkowo latwiejsze dalsze porzadkowanie PMG layout

Uwaga:

W praktyce docelowy zysk zalezy od finalnej organizacji PMBASE i wymagan wysokosci sprite'ow.

Checklist:

- [ ] Przelacz PMG na wariant double-line.
- [ ] Dopasuj TOP_MARGIN, MOON_TOP i zakresy kopiowania sprite'ow.
- [ ] Ustal profile PMG per scena (title: on, story/gameover: off, game: wedlug potrzeb).

Definition of done:

- [ ] Brak deformacji sprite'ow i poprawne pozycjonowanie.
- [ ] Mapa pamieci potwierdza nowy wolny zakres PMG.

## Etap 5 - Mikrorefaktory dajace male, ale pewne oszczednosci

Adresy docelowe:

- FIRE flags jako bitfield w 1 bajcie na $8B (ZP)

Checklist:

- [ ] Scal title_fire_released, fire_released_flag, game_fire_released, gameover_fire_released.
- [ ] Wydziel wspolna procedure "wait release -> wait press".

Definition of done:

- [ ] Nie ma zduplikowanej logiki obslugi FIRE w 4 scenach.
- [ ] Przejscia miedzy scenami zachowuja identyczne zachowanie jak przed zmianami.

## Etap 6 - Overlays kodu scen (gdy gameplay zacznie rosnac)

Adresy docelowe (proponowane sloty):

- SCENE_CODE_SLOT_BASE: $2891
- SCENE_CODE_SLOT_END: $3DFF
- DLIST pozostaje stale na $3E80+

Zastosowanie:

- loader laduje aktywna scene do jednego wspolnego slotu kodu
- kernel (main + wspolne biblioteki) pozostaje rezydentny

Checklist:

- [ ] Podziel kod na kernel i sceny overlay.
- [ ] Dodaj loader scen i walidacje granic slotu.

Definition of done:

- [ ] Dziala przelaczanie scen bez stalej rezydencji kodu wszystkich scen.
- [ ] Brak kolizji z DL i innymi stale zmapowanymi obszarami.

---

## Podsumowanie zyskow po etapach 1-5

- Etap 1: 3744 B
- Etap 2: ~239 B
- Etap 4: ~640 B (konserwatywnie)
- Etap 5: kilka B do kilkunastu B

Lacznie (konserwatywnie, bez overlays): ok. 4.6 KB+ odzyskanego RAM.
