# Makefile — Wiedźmin: Dziki Zgon
# Budowanie projektu na Atari 800 XL / 65 XE

# ---- Narzędzia ----
MADS    := c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
PYTHON  := python

# ---- Pliki ----
ASM_MAIN    := witcher.asm
XEX_OUT     := dziki_zgon.xex


BG_PREFIX   := title
BG_IMG      := img/$(BG_PREFIX).png

# Pliki generowane przez img2asm.py
BG_BIN      := $(BG_PREFIX).bin
BG_ASM      := $(BG_PREFIX).asm
BG_COLORS   := $(BG_PREFIX)_colors.asm
BG_DL       := $(BG_PREFIX)_displaylist.asm

# Sprite'y
MOON_ASM    := moon.asm
MOON_IMG    := img/moon.png
TITLE_ASM   := dziki-zgon.asm
TITLE_IMG   := img/dziki-zgon.png

# ---- Cele ----
.PHONY: all xex bg sprites clean run

all: sprites bg xex

xex: $(MOON_ASM) $(TITLE_ASM) $(BG_BIN) $(ASM_MAIN)
	@echo "=== Asemblacja $(ASM_MAIN) → $(XEX_OUT) ==="
	$(MADS) $(ASM_MAIN) -o:$(XEX_OUT)

# Generowanie tła (bin + colors + display list)
bg: $(BG_BIN)

$(BG_BIN): $(BG_IMG) scripts/img2asm.py
	@echo "=== Konwersja $(BG_IMG) → $(BG_PREFIX).* ==="
	$(PYTHON) scripts/img2asm.py $(BG_IMG) 2 --all -o $(BG_PREFIX) --footer 0x5E10

# Generowanie sprite'ów
sprites: $(MOON_ASM) $(TITLE_ASM)

$(MOON_ASM): $(MOON_IMG) scripts/img2asm.py
	@echo "=== Konwersja $(MOON_IMG) → $(MOON_ASM) ==="
	$(PYTHON) scripts/img2asm.py $(MOON_IMG) 1 --asm -l 4

$(TITLE_ASM): $(TITLE_IMG) scripts/img2asm.py
	@echo "=== Konwersja $(TITLE_IMG) → $(TITLE_ASM) ==="
	$(PYTHON) scripts/img2asm.py $(TITLE_IMG) 1 --asm -l 5

# Sprzątanie
clean:
	@echo "=== Usuwanie plików wygenerowanych ==="
	rm -f $(XEX_OUT)
	rm -f $(BG_BIN) $(BG_ASM) $(BG_COLORS) $(BG_DL)
	rm -f $(MOON_ASM) $(TITLE_ASM)

# Pomoc
help:
	@echo "Dostępne cele:"
	@echo "  make          — buduje wszystko + $(XEX_OUT)"
	@echo "  make bg       — konwertuje obraz tła ($(BG_IMG))"
	@echo "  make sprites  — konwertuje sprite'y (moon + dziki-zgon)"
	@echo "  make clean    — usuwa pliki wygenerowane"
	@echo "  make help     — ta pomoc"
	@echo ""
	@echo "Żeby zmienić tło: make clean BG_PREFIX=title-2 && make"
