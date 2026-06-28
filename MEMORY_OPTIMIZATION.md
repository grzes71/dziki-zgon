**Możliwe dalsze kierunki optymalizacji pamięci w projekcie**

| Obszar | Aktualny stan | Potencjalna oszczędność | Krótkie uzasadnienie |
|--------|----------------|------------------------|----------------------|
| **PMG (Player‑Missile Graphics)** | `$A400‑$A7FF` (2 KB – tryb **single‑line**) | **~1 KB** | W trybie **double‑line** PMG zajmuje tylko 1 KB (każdy bajt opisuje dwa wiersze). Jeśli wysokość graczy/missili nie wymaga pełnych 256 linii, można przełączyć `SDMCTL`‑bit 5 i skrócić bufor. |
| **OS ROM** (`PORTB` bit 0) | Włączony (`bit 0 = 1`) → `$C000‑$CFFF` oraz `$E000‑$FFFF` niedostępne | **4 KB** | Wyłączenie OS ROM (ustawienie `PORTB` = `$FE` lub `$FC`) zwalnia `$C000‑$CFFF`. Interfejs DLI/NMI można przenieść do RAM (np. własny wektor w `$2000‑$2002`), a obsługę klawiatury/klawiszy można realizować własnym kodem. Trzeba więc: <br>1. Zapisać własne procedury DLI/NMI w RAM. <br>2. Ustawić `PORTB`‑bit 0 = 0 po wczytaniu tych procedur. |
| **Zbędne jednowierszowe zmienne** | np. `fire_released_flag` (1 B), `VDSLST` (2 B) | **~1‑2 B** | Pakowanie kilku flag w jeden bajt (bit‑field) – np. połączyć `fire_released_flag` z innymi jednowierszowymi flagami sceny w jeden wspólny bajt. |
| **Teksty story / Game‑Over** | `StoryText_Data` (320 B), `GO_TEXT_Data` (32 B) | **~50‑100 B** (potencjalnie) | Kompresja run‑length (RLE) lub tokenizacja (np. zamiana powtarzających się spacji/znaków na krótsze sekwencje) i dekompresja w czasie ładowania sceny. <br>‑ Można też przenieść tę część do ROM‑u (`$A800‑$ABFF`) – już jest wolna, ale wtedy nie będą dostępne w RAM przy wyświetlaniu. |
| **Sprite‑data (logo, księżyc)** | `DzikizgonData` ≈ 185 B, `MoonData` ≈ 96 B | **~50 B** (przy kompresji) | RLE lub algorytm „packed‑bits” (np. 2‑bitowy tryb graficzny) przy zachowaniu jakości. De‑kompresja w czasie wyświetlania (krótkie pętle) nie wpływa znacząco na wydajność. |
| **Display‑Listy** | `$3E80‑$3FEE` (367 B) – jedyny bufor list | **~50‑100 B** | Zredukować liczbę komend DLI/WSYNC w listach (np. użyć krótszych trybów ANTIC, usunąć niepotrzebne oczekiwania). |
| **Podział wolnego RAM** | Największy wolny blok `$2815‑$3E7F` (5 739 B) | **~300‑500 B** | Przenieść małe, rzadko używane stałe (np. stałe liczbowe, lookup‑tablice) z sekcji kodu (`$2003‑$2042` – `pmg.asm`, `$2043‑$22EB` – `title.asm`) do tego wolnego bloku i odwoływać się do nich pośrednio (np. przez `LDA $xxxx,Y`). Redukuje to rozmiar kodu w niższych obszarach, umożliwiając krótsze offsety i mniejsze instrukcje. |
| **Różne nieużywane segmenty** | `VDSLST` (2 B), wektor startu (3 B) – już w RAM, ale niepotrzebne w kodzie przy włączonym OS ROM | **‑** | Jeżeli zdecydujemy się wyłączyć OS ROM, te wektory będą już niepotrzebne i można je usunąć. |
| **Użycie trybu “bank‑switch”** | Nie wykorzystywany | **~2 KB** (teoretycznie) | Atari 800XL/XE posiada rozszerzone banki pamięci (`$4000‑$7FFF`). Jeśli kod i dane zostaną podzielone na banki, można mieć jednocześnie dwa aktywne „widoczne” obszary w RAM. Wymaga to dodatkowego kodu zarządzającego bankami, ale może pozwolić na jednoczesne trzymanie większej części danych w RAM jednocześnie. |

### Szybka lista priorytetów (od najłatwiejszych do najtrudniejszych)

1. **Double‑line PMG** – wymaga jedynie zmiany jednego bitu w `SDMCTL` i ewentualnej korekty danych sprite‑ów (przycięcie wysokości). Zmniejsza bufor PMG o 1 KB bez wpływu na resztę pamięci.
2. **Kompresja tekstów i sprite‑ów** – można dodać proste RLE w skryptach generujących `*.asm`. Dekompresja w czasie ładowania sceny jest bardzo szybka na 6502.
3. **Bit‑packing flag** – najmniej inwazyjne, wymaga jedynie zmiany kilku deklaracji zmiennych i odwołań.
4. **Wyłączenie OS ROM** – wymaga przeniesienia DLI/NMI do RAM i dokładnego przetestowania, ale daje dodatkowe 4 KB. Warto rozważyć, jeśli nie korzystamy z funkcji OS (np. obsługa klawiatury może być własna).
5. **Przeniesienie małych stałych do wolnego bloku `$2815‑$3E7F`** – polepsza lokalność kodu i może umożliwić użycie krótszych adresów (zero‑page / relative).
6. **Rzeczywiste użycie bank‑switch** – najbardziej skomplikowane, wymaga restrukturyzacji całego systemu ładowania i zarządzania pamięcią, ale potencjalnie otwiera dodatkowe 2 KB w krytycznych momentach.

---

### Co zrobić dalej?

* **Test double‑line PMG** – zmienić `SDMCTL` → `ORA #$20` (ustawienie bit 5) i skompilować. Sprawdzić, czy wszystkie sprite’y nadal wyświetlają się prawidłowo (wysokość nie powinna przekraczać 128 linii).
* **Implementacja prostego RLE** – można dodać mały konwerter w `scripts/` (np. `rle_encode.py`) i zamienić `StoryText_Data`, `GO_TEXT_Data` oraz sprite‑y na wersje skompresowane. Dodaj funkcję dekompresji w `gameover.asm` i `story.asm`.
* **Rozważ wyłączenie OS ROM** – jeżeli nie potrzebujesz żadnych funkcji systemowych (np. obsługi klawiatury – możesz odczytywać porty samodzielnie), przenieś wektor DLI/NMI do RAM (np. `$2000‑$2002`) i ustaw `PORTB = $FE`. To odblokuje `$C000‑$CFFF`.
* **Zbadaj możliwości pakowania flag** – przegląd zmiennych w `main.asm` i scenach, połączyć jednorazowe flagi w jedną byte‑packed strukturę.
