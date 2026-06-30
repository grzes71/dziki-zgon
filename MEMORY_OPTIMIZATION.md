**Możliwe dalsze kierunki optymalizacji pamięci w projekcie**

| Obszar | Aktualny stan | Potencjalna oszczędność | Krótkie uzasadnienie |
|--------|----------------|------------------------|----------------------|
| **PMG (Player‑Missile Graphics)** | `$A400‑$A7FF` (2 KB – tryb **single‑line**) | **~1 KB** | W trybie **double‑line** PMG zajmuje tylko 1 KB (każdy bajt opisuje dwa wiersze). Jeśli wysokość graczy/missili nie wymaga pełnych 256 linii, można przełączyć `SDMCTL`‑bit 5 i skrócić bufor. |
| **OS ROM** (`PORTB` bit 0) | Włączony (`bit 0 = 1`) → `$C000‑$CFFF` oraz `$E000‑$FFFF` odblokowane dla ROM | **4 KB** | Wyłączenie OS ROM (ustawienie `PORTB` = `$FE` lub `$FC`) zwalnia `$C000‑$CFFF`. Interfejs DLI/NMI można przenieść do RAM, a obsługę klawiatury/klawiszy realizować własnym kodem. Wymagałoby to jednak obsługi odtwarzacza muzyki RMT za pomocą własnego handlera VBI bez pomocy systemu. |
| **Zbędne jednowierszowe zmienne** | np. `fire_released_flag` (1 B), `VDSLST` (2 B) | **~1‑2 B** | Pakowanie kilku flag w jeden bajt (bit‑field) – np. połączyć `fire_released_flag` z innymi jednowierszowymi flagami sceny w jeden wspólny bajt. |
| **Display‑Listy** | `$3E80‑$3FEE` (367 B) – bufor list | **~50‑100 B** | Zredukować liczbę komend DLI/WSYNC w listach (np. użyć krótszych trybów ANTIC, usunąć niepotrzebne oczekiwania). |
| **Podział wolnego RAM** | Wolny RAM rozproszony po blokach | **~300‑500 B** | Przenieść małe, rzadko używane stałe (np. stałe liczbowe, lookup‑tablice) z sekcji kodu do wolnych bloków i odwoływać się do nich pośrednio (np. przez `LDA $xxxx,Y`). Redukuje to rozmiar kodu w niższych obszarach, umożliwiając krótsze offsety i mniejsze instrukcje. |
| **Użycie trybu “bank‑switch”** | Nie wykorzystywany | **~2 KB** (teoretycznie) | Atari 800XL/XE posiada rozszerzone banki pamięci (`$4000‑$7FFF`). Jeśli kod i dane zostaną podzielone na banki, można mieć jednocześnie dwa aktywne „widoczne” obszary w RAM. Wymaga to dodatkowego kodu zarządzającego bankami. |

### Szybka lista priorytetów (od najłatwiejszych do najtrudniejszych)

1. **Double‑line PMG** – wymaga jedynie zmiany jednego bitu w `SDMCTL` i ewentualnej korekty danych sprite‑ów (przycięcie wysokości). Zmniejsza bufor PMG o 1 KB bez wpływu na resztę pamięci.
2. **Bit‑packing flag** – najmniej inwazyjne, wymaga jedynie zmiany kilku deklaracji zmiennych i odwołań.
3. **Wyłączenie OS ROM** – wymaga przeniesienia DLI/NMI do RAM i dokładnego przetestowania, ale daje dodatkowe 4 KB. Wymagałoby to przeniesienia odtwarzacza muzycznego pod całkowicie własny handler VBI/NMI.
4. **Przeniesienie małych stałych do wolnych bloków RAM** – polepsza lokalność kodu i może umożlić użycie krótszych adresów (zero‑page / relative).
5. **Rzeczywiste użycie bank‑switch** – najbardziej skomplikowane, wymaga restrukturyzacji całego systemu ładowania i zarządzania pamięcią.

---

### Co zrobić dalej?

* **Test double‑line PMG** – zmienić `SDMCTL` → `ORA #$20` (ustawienie bit 5) i skompilować. Sprawdzić, czy wszystkie sprite’y nadal wyświetlają się prawidłowo (wysokość nie powinna przekraczać 128 linii).
* **Rozważ wyłączenie OS ROM** – jeśli zajdzie potrzeba zwolnienia dodatkowych 4 KB RAM, przepisać wektory DLI/NMI do RAM i wyłączyć system (PORTB = $FE). Trzeba wdrożyć własną obsługę przerwań dla odtwarzacza muzyki.
* **Zbadaj możliwości pakowania flag** – przegląd zmiennych w `main.asm` i scenach, połączyć jednorazowe flagi w jedną byte‑packed strukturę.
