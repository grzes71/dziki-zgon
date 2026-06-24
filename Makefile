# Makefile — Wiedźmin: Dziki Zgon
# Budowanie projektu na Atari 800 XL / 65 XE

# ---- Narzędzia ----
MADS    := c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
PYTHON  := python

# ---- Cross-platform: wykrywanie OS (Windows vs Linux/macOS) ----
ifeq ($(OS),Windows_NT)
    RM    := cmd /c del /q
    RMDIR := cmd /c rmdir /s /q
    MKDIR := mkdir
else
    RM    := rm -f
    RMDIR := rm -rf
    MKDIR := mkdir -p
endif

# ---- Pliki ----
ASM_MAIN    := main.asm
XEX_OUT     := dziki_zgon.xex
GEN_DIR     := gen

BG_PREFIX   := title
BG_IMG      := img/$(BG_PREFIX).png

# Pliki generowane przez img2asm.py (w katalogu gen/)
BG_BIN      := $(GEN_DIR)/$(BG_PREFIX).bin
BG_ASM      := $(GEN_DIR)/$(BG_PREFIX).asm
BG_COLORS   := $(GEN_DIR)/$(BG_PREFIX)_colors.asm
BG_DL       := $(GEN_DIR)/$(BG_PREFIX)_displaylist.asm

# Sprite'y
MOON_ASM    := $(GEN_DIR)/moon.asm
MOON_IMG    := img/moon.png
TITLE_ASM   := $(GEN_DIR)/dziki-zgon.asm
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
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(BG_IMG) → $(BG_PREFIX).* ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(BG_IMG) 2 --all -o $(BG_PREFIX) --footer 0x5E10

# Generowanie sprite'ów
sprites: $(MOON_ASM) $(TITLE_ASM)

$(MOON_ASM): $(MOON_IMG) scripts/img2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(MOON_IMG) → $(MOON_ASM) ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(MOON_IMG) 1 --asm -o moon.asm -l 4

$(TITLE_ASM): $(TITLE_IMG) scripts/img2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(TITLE_IMG) → $(TITLE_ASM) ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(TITLE_IMG) 1 --asm -o dziki-zgon.asm -l 5

# Sprzątanie
clean:
	@echo "=== Usuwanie plików wygenerowanych ==="
	-$(RM) $(XEX_OUT)
	-$(RMDIR) $(GEN_DIR)

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
