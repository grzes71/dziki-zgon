# Reguły i Założenia Gry — Wiedźmin: Dziki Zgon (Atari 8-bit)

Dokument stanowi oficjalne **Single Source of Truth (SSOT)** dla wszystkich reguł rozgrywki, parametrów mechanik, ograniczeń sprzętowych i logiki gry zaimplementowanej w projekcie *Wiedźmin: Dziki Zgon*.

---

## 1. Cel Gry i Warunki Zwycięstwa / Porażki

- **Główny cel fabularny**: Gerwalt musi odnaleźć i odzyskać **Podarty rachunek** (przedmiot o `id: 5`), aby rozliczyć się za zlecenia i zakończyć przygodę sukcesem.
- **Warunek Zwycięstwa (`GAME_RESULT_STATUS = 1`)**:
  - Pomyślne spełnienie wymagań u zleceniodawcy / w kwaterze i odebranie przedmiotu *Podarty rachunek*.
  - Gra natychmiast przechodzi do sceny `STATE_OVER` z ekranem sukcesu (*"Gratulacje! Odzyskałeś podarty rachunek!"*).
- **Warunek Porażki (`GAME_RESULT_STATUS = 2`)**:
  - Upływ limitu czasu gry do wartości `00:00`.
  - Czas upływa naturalnie oraz jest drastycznie redukowany w wyniku obrażeń od potworów i niebezpiecznego podłoża.
  - Osiągnięcie `00:00` natychmiast kończy grę i przenosi do sceny `STATE_OVER` z ekranem porażki (*"Porażka! Czas minął lub Gerwalt poległ."*).

---

## 2. Zasób Czasu i System Obrażeń (Czas jako Zdrowie / HP)

W grze nie ma tradycyjnego paska zdrowia (HP) — **czas jest jedynym zasobem życiowym Gerwalta**.

- **Czas startowy**: `12:00` (12 minut = 720 sekund).
- **Naturalny upływ czasu**: Zegar odlicza dokładnie 1 sekundę co 50 ramek (1 sekunda czasu rzeczywistego w standardzie PAL 50 Hz).
- **Obrażenia jako redukcja czasu**:
  - Każde uderzenie przeciwnika lub kontakt z niebezpiecznym terenem odejmuje określoną liczbę sekund bezpośrednio z licznika `MM:SS`.
  - Jeśli liczba odejmowanych sekund przekracza aktualny stan licznika, czas spada do `00:00` i następuje natychmiastowy Game Over.
- **Efekty otrzymania obrażeń**:
  - Kolor duszka Gerwalta natychmiast zmienia się na czerwony (`kolor: 54`).
  - **Spowolnienie gracza (Collision Slowdown)**:
    - Ruch poziomy zostaje zredukowany o połowę (ruch o 1 px co 4 klatki zamiast co 2 klatki).
    - Ruch pionowy omija klatki parzyste (ruch o 1 px co 2 klatki zamiast w każdej klatce).

---

## 3. Ekwipunek i Przedmioty (Inventory)

- **Limit pojemności**: Maksymalnie **8 przedmiotów** (`MAX_INVENTORY_ITEMS = 8`).
- **Zasada przepełnienia**:
  - Gerwalt **nie może podnieść 9. przedmiotu**.
  - Próba zebrania przedmiotu przy pełnym ekwipunku (8/8) kończy się niepowodzeniem — przedmiot pozostaje nienaruszony na planszy do momentu zwolnienia miejsca.
- **Prezentacja w HUD (Info Line)**:
  - Format: `[........]` (indeksy 22..31 górnej linii statusu).
  - Pusty slot reprezentowany jest przez kropkę (`.`), zajęty slot przez dedykowany kafelek graficzny przedmiotu.
- **Zużywanie i usuwanie**:
  - Przedmioty są automatycznie usuwane z ekwipunku podczas pomyślnej interakcji (np. oddanie wymaganych przedmiotów zleceniodawcy).
- **Rejestr znanych przedmiotów**:

| ID | Nazwa przedmiotu | Pozycja glifu w zestawie znaków (`charset_position`) | Opis i rola |
|:--:|---|:--:|---|
| **1** | fałszywe pieniądze | 35 | Monety do przekupstwa lub podejrzanych transakcji |
| **2** | miecz na potwory | 33 | Srebrne ostrze do walki z bestiami |
| **3** | miecz na ludzi | 34 | Stalowy miecz przydatny w ludzkich osadach |
| **4** | sznurek | 41 | Przedmiot użytkowy do wiązania i napraw |
| **5** | podarty rachunek | 74 | **Główny cel gry (Warunek Zwycięstwa)** |
| **6** | wiosła | 78 | Przedmiot potrzebny do przepraw wodnych / łodzi |

---

## 4. Przeciwnicy i Bestiariusz (Enemies & Combat)

- **Limit na ekranie**: Maksymalnie **3 przeciwników jednocześnie** na jednym ekranie (`MAX_ACTORS = 4`, gdzie Aktor 0 to gracz, a Aktorzy 1..3 to przeciwnicy).
- **Kolizje i zadawanie obrażeń**:
  - Kolizja zachodzi, gdy duszek Gerwalta nachodzi na duszka przeciwnika (sprawdzanie `abs(X_p - X_e) < 8` oraz overlap osi Y).
  - W przypadku jednoczesnego kontaktu z wieloma wrogami aplikowane są najwyższe obrażenia z dotykanych bestii.

### Bestiariusz i Obrażenia

| Identyfikator | Nazwa | Obrażenia (utrata czasu) | Wysokość duszka (PMG) |
|---|---|:--:|:--:|
| `kikimora` | Kikimora | **1 s** | 10 px |
| `strzyga` | Strzyga | **2 s** | 16 px |
| `bazyliszek` | Bazyliszek | **5 s** | 16 px |
| `sukkub` | Sukkub | **10 s** | 16 px |

### Strategie Ruchu AI (`strategy`)

1. `horizontal` (0): Ruch wyłącznie w poziomie (lewo/prawo), odbicie i zmiana zwrotu na przeciwny po napotkaniu ściany lub przeszkody.
2. `vertical` (1): Ruch wyłącznie w pionie (góra/dół), odbicie po napotkaniu ściany lub przeszkody.
3. `random` (2): Losowy wybór osi początkowej (pozioma lub pionowa) podczas ładowania ekranu.
4. `chaotic` (3): Po uderzeniu w przeszkodę losuje nową oś i zwrot ruchu.
5. `patrol` (4): Po kolizji z przeszkodą wykonuje rotację o 90° w prawo (zgodnie z ruchem wskazówek zegara: góra → prawo → dół → lewo → góra).
6. `pacing` (5): Po dotarciu do przeszkody zatrzymuje się w bezruchu na 30 klatek (~0.6 sekundy), po czym zawraca.
7. `snake` (6): Porusza się do przodu, zmieniając losowo kierunek co 64 klatki (1.28 s) oraz odbijając się od ścian.
8. `homing` (7): Aktywny pościg za Gerwaltem. Co 16 klatek (0.32 s) przelicza wektor odległości $\Delta X$ i $\Delta Y$ do gracza i wybiera dominujący kierunek pościgu.

### Prędkości Ruchu (`speed`)

- `slow` (0): Ruch o 1 px co 4 klatki (~12.5 px/s).
- `medium` (1): Ruch o 1 px co 2 klatki (~25.0 px/s).
- `fast` (2): Ruch o 1 px w każdej klatce (~50.0 px/s).

### Dostępne Kolory Przeciwników (GTIA)
`white` (15), `red` (54), `green` (198), `blue` (136), `yellow` (238), `magenta` (148), `cyan` (166), `orange` (24), `purple` (90), `brown` (32), `gray` (10), `black` (0).

---

## 5. Obiekty Interaktywne (Interactive Inspection System — IIS)

- **Limit**: Maksymalnie **1 obiekt interaktywny na ekran**.
- **Mechanika aktywacji**:
  - Gracz musi stanąć bezpośrednio przed obiektem i być zwróconym twarzą w jego stronę.
  - Naciśnięcie przycisku **FIRE (TRIG0)** inicjuje interakcję i wyzwala dźwięk interakcji (`Request_SFX_Interact`).

### Typy Obiektów Interaktywnych

1. **`kwatera` (Zadania, Postacie, Wymiana)**:
   - Weryfikuje listę wymaganych przedmiotów (`items_required`).
   - **Warunki spełnione (`conditions_met`)**:
     - Wszystkie wymagane przedmioty zostają usunięte z ekwipunku.
     - Wszystkie przedmioty z `items_provided` trafiają do ekwipunku gracza.
     - Na dolnym pasku pojawia się komunikat sukcesu (`conditions_met`).
     - Obiekt zostaje oznaczony jako trwale ukończony (`INTERACTIVE_OBJ_COMPLETE = 0`).
     - Jeśli wśród otrzymanych przedmiotów jest *Podarty rachunek* (`id: 5`), następuje **Zwycięstwo**!
   - **Warunki niespełnione (`conditions_unmet`)**:
     - Jeśli brakuje choć jednego wymaganego przedmiotu, przedmioty nie są pobierane.
     - Na dolnym pasku pojawia się komunikat o niespełnieniu wymagań (`conditions_unmet`).
2. **`portal` (Podróże międzyregionalne)**:
   - Dwuetapowa aktywacja zapobiegająca przypadkowemu teleportowaniu:
     - **1. naciśnięcie FIRE**: Wyświetla komunikat podróży (`message_travel`) na pasku wiadomości.
     - **2. naciśnięcie FIRE** (podczas gdy komunikat jest widoczny): Zamyka komunikat i uruchamia 5-sekundowy ekran podróży (`travel_screen`), przenosząc gracza na punkt wejścia (`Portal Entry`) w regionie docelowym.

---

## 6. Sekretne Obiekty (Secret Objects / Znajdźki)

- **Zasada działania**:
  - Przedmioty ukryte na planszach (np. skrzynie, krzaki, zakamarki).
  - Zebranie następuje automatycznie, gdy Gerwalt wejdzie na pole sekretu (overlap współrzędnych).
- **Obsługa zebrania**:
  - Jeśli ekwipunek **nie jest pełny** (< 8 przedmiotów):
    1. Przedmiot trafia do ekwipunku gracza.
    2. Kafelki sekretu w buforze VRAM zostają natychmiast wyzerowane (obiekt znika z planszy).
    3. Sekret zostaje trwale oznaczony jako zebrany na danym ekranie (`SECRET_COLLECTED_FLAGS`).
    4. Na pasku wiadomości pojawia się komunikat: `"znalazłeś <nazwa_przedmiotu>"`.
    5. Odtwarzany jest dźwięk podniesienia przedmiotu (`Request_SFX_Item`).
  - Jeśli ekwipunek **jest pełny** (8 przedmiotów):
    - Obiekt nie jest zbierany i pozostaje widoczny na planszy.

---

## 7. Świat Gry, Regiony i Obrażenia Środowiskowe

- **Siatka ekranu**: 40 kolumn × 12 wierszy kafelków w trybie ANTIC 5 (bufor VRAM: 480 bajtów).
- **Nawigacja wewnątrz regionu**:
  - Ruch za krawędź planszy (North / South / East / West) płynnie przenosi gracza na powiązany ekran i umieszcza go przy przeciwległej krawędzi:
    - Wyjście na zachód ($X < 48$) $\rightarrow$ Spawn po prawej stronie ($X = 198$).
    - Wyjście na wschód ($X > 200$) $\rightarrow$ Spawn po lewej stronie ($X = 50$).
    - Wyjście na północ ($Y < 32$) $\rightarrow$ Spawn na dole ($Y = 206$).
    - Wyjście na południe ($Y > 208$) $\rightarrow$ Spawn na górze ($Y = 34$).
- **Obrażenia środowiskowe (Hazard Terenu — rejestr kolizji `P0PF` bit 3 / kolor PF3)**:
  - Wejście na niebezpieczne pole (np. trujące bagna, lawa) zadaje obrażenia czasowe zależne od specyfiki regionu.

### Regiony Gry i Parametry

| ID Regionu | Nazwa w grze | Wymiary siatki | Obrażenia środowiskowe (PF3) | Muzyka RMT |
|---|---|:--:|:--:|---|
| `WHITE_FIELD` | białe pole | 3 × 3 | **10 s** | `WHITE_FIELD` |
| `LAS_PIJANEGO_ZAJACA` | las pijanego zająca | 2 × 3 | **10 s** | `LAS_PIJANEGO_ZAJACA` |
| `OLD_WYZIMA` | stara wyżyma | 4 × 3 | **10 s** | `OLD_WYZIMA` |
| `SAMOTNIA_MISTRZA` | samotnia mistrza | 2 × 2 | **20 s** | `SAMOTNIA_MISTRZA` |
| `JAR_WIECZNEJ_ZGAGI` | jar wiecznej zgagi | 1 × 6 | **25 s** | `JAR_WIECZNEJ_ZGAGI` |

- **Ekran Podróży (`travel_screen`)**:
  - Podczas podróży portalem wyświetlany jest statyczny ekran w trybie ANTIC 2 przez **5 sekund (250 klatek)**.
  - Wyświetla 8-wierszowy, skompresowany RLE tekst klimatyczny opisujący dotarcie do nowego regionu.

---

## 8. Interfejs Gracza (HUD) i Komunikaty

Panel statusowy zlokalizowany jest u dołu ekranu i składa się z dwóch linii w trybie ANTIC 2 (40 znaków szerokości):

### Górna linia (Info Line)
- **Poz. 0–1**: Znaki narożnika ramki.
- **Poz. 2–21**: Nazwa aktualnego regionu (wyrównana, max 20 znaków).
- **Poz. 22–31**: Wizualizacja ekwipunku `[........]` (8 slotów).
- **Poz. 32**: Odstęp (spacja).
- **Poz. 33–37**: Licznik pozostałego czasu w formacie `MM:SS` (np. `12:00`).
- **Poz. 38–39**: Znaki narożnika ramki.

### Dolna linia (Message Line)
- **Poz. 0–1**: Znaki narożnika ramki.
- **Poz. 2–37**: Treść komunikatów i dialogów (max 36 znaków, automatycznie wyśrodkowana).
- **Poz. 38–39**: Znaki narożnika ramki.
- **Czas wyświetlania**: Komunikat znika automatycznie po **5 sekundach (250 klatek)**.
- **Łączenie zdań (Separator `&`)**: Jeśli tekst zawiera znak `&`, kolejne zdanie jest automatycznie prezentowane po upływie 5 sekund poprzedniego zdania.
- **Diakrytyka**: Pełna obsługa polskich znaków UTF-8 (`ą`, `ć`, `ę`, `ł`, `ń`, `ó`, `ś`, `ź`, `ż`).

---

## 9. Sterowanie i Fizyka Ruchu Gracza

- **Sterowanie**: Joystick w porcie 1 (`PORTA`) + przycisk `TRIG0` (Fire).
- **Kierunki i Priorytety**:
  - Dostępne 4 kierunki podstawowe: Lewo, Prawo, Góra, Dół.
  - Przy ruchach skośnych pierwszeństwo w wyznaczaniu animacji i zwrotu mają osie poziome: `Lewo` > `Prawo` > `Góra` > `Dół`.
- **Prędkość poruszania się**:
  - **Ruch pionowy**: 1 piksel na każdą klatkę (50 px/s).
  - **Ruch poziomy**: 1 piksel co drugą klatkę (25 px/s).
  - **W stanie kolizji / po trafieniu**: ruch poziomy spowalnia do 1 px co 4 klatki (12.5 px/s), a ruch pionowy omija klatki parzyste (25 px/s).
- **Animacja kroków**:
  - Cykl animacji zmienia klatkę co 6 ramek (`ACTOR_ANIM_SPEED = 6`).
  - Zakończenie pełnego cyklu animacji kroku zgłasza żądanie odtworzenia efektu dźwiękowego kroków (`Request_SFX_Step = 1`).

---

## 10. Przepływ Maszyny Stanów Gry (State Machine)

1. `STATE_TITLE` (0) — Ekran tytułowy z okładką graficzną i motywem muzycznym. Naciśnięcie FIRE przechodzi do wprowadzenia.
2. `STATE_STORY` (1) — Ekran fabularny przedstawiający tło przygody i cel misji. Naciśnięcie FIRE rozpoczyna właściwą rozgrywkę.
3. `STATE_GAME` (2) — Główna pętla gry (eksploracja, walka, zagadki, interakcje).
4. `STATE_OVER` (3) — Ekran zakończenia (Sukces lub Porażka z odpowiednim podsumowaniem fabularnym). Naciśnięcie FIRE resetuje stan i powraca do początku.
