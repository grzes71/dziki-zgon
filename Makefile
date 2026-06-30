# Makefile — Wiedźmin: Dziki Zgon
# Budowanie projektu na Atari 800 XL / 65 XE

# ---- Narzędzia ----
MADS    := c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
PYTHON  := python
ASAPCONV  := C:/Apps/ASAP/asapconv.exe
RMT2ATASM := C:/Apps/rmt2atasm.exe

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

# Game Over screen
GO_PREFIX   := gameover
GO_IMG      := img/game-over.png
GO_BIN      := $(GEN_DIR)/$(GO_PREFIX).bin
GO_ASM      := $(GEN_DIR)/$(GO_PREFIX).asm
GO_COLORS   := $(GEN_DIR)/$(GO_PREFIX)_colors.asm
GO_DL       := $(GEN_DIR)/$(GO_PREFIX)_displaylist.asm

# Sprite'y
MOON_ASM    := $(GEN_DIR)/moon.asm
MOON_IMG    := img/moon.png
TITLE_ASM   := $(GEN_DIR)/dziki-zgon.asm
TITLE_IMG   := img/dziki-zgon.png

# Czcionki
FONT_FNT    := fonts/font.fnt
FONT_ASM    := $(GEN_DIR)/font.asm

# Muzyka
MUSIC_SAP       := music/title.sap
MUSIC_RMT       := $(GEN_DIR)/title.rmt
MUSIC_ASM_ATASM := $(GEN_DIR)/title_atasm.asm
MUSIC_ASM       := $(GEN_DIR)/title_music.asm
PLAYR_ASM       := $(GEN_DIR)/rmtplayr.asm

# Teksty skompresowane RLE
TEXTS_ASM   := $(GEN_DIR)/story_text.asm $(GEN_DIR)/gameover_text.asm

# ---- Cele ----
.PHONY: all xex bg go sprites texts fonts music clean run

all: texts sprites bg go fonts music xex

xex: $(TEXTS_ASM) $(MOON_ASM) $(TITLE_ASM) $(BG_BIN) $(GO_BIN) $(FONT_ASM) $(MUSIC_ASM) $(PLAYR_ASM) $(ASM_MAIN)
	@echo "=== Asemblacja $(ASM_MAIN) → $(XEX_OUT) ==="
	$(MADS) $(ASM_MAIN) -o:$(XEX_OUT)

# Generowanie tekstów
texts: $(TEXTS_ASM)

$(GEN_DIR)/story_text.asm: scripts/rle_compress_text.py texts/story.txt
	-@mkdir $(GEN_DIR)
	$(PYTHON) scripts/rle_compress_text.py -i story -o $@

$(GEN_DIR)/gameover_text.asm: scripts/rle_compress_text.py texts/gameover.txt
	-@mkdir $(GEN_DIR)
	$(PYTHON) scripts/rle_compress_text.py -i gameover -o $@

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
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(MOON_IMG) 1 --asm -o moon.asm -l 4 -c rle

$(TITLE_ASM): $(TITLE_IMG) scripts/img2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(TITLE_IMG) → $(TITLE_ASM) ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(TITLE_IMG) 1 --asm -o dziki-zgon.asm -l 5 -c rle

# Game Over screen (ANTIC D, 160×96, 4 kolory)
go: $(GO_BIN)

$(GO_BIN): $(GO_IMG) scripts/img2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(GO_IMG) → $(GO_PREFIX).* ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(GO_IMG) 2 --all -o $(GO_PREFIX) --screen-base 0x7000

# Generowanie czcionek
fonts: $(FONT_ASM)

$(FONT_ASM): $(FONT_FNT) scripts/fnt2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(FONT_FNT) → $(FONT_ASM) ==="
	$(PYTHON) scripts/fnt2asm.py -i $(FONT_FNT) -o $@ -l FontData

# Generowanie muzyki
music: $(MUSIC_ASM) $(PLAYR_ASM)

$(MUSIC_RMT): $(MUSIC_SAP)
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja SAP → RMT ==="
	-$(ASAPCONV) -o $@ $<

$(MUSIC_ASM_ATASM): $(MUSIC_RMT)
	@echo "=== Konwersja RMT → ATasm ==="
	$(RMT2ATASM) $< > $@

$(MUSIC_ASM): $(MUSIC_ASM_ATASM) scripts/atasm2mads.py
	@echo "=== Konwersja ATasm → MADS ==="
	$(PYTHON) scripts/atasm2mads.py -i $< -o $@

$(PLAYR_ASM): music/rmtplayr.asm scripts/atasm2mads.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja Player ATasm → MADS ==="
	$(PYTHON) scripts/atasm2mads.py -i $< -o $@

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
	@echo "  make fonts    — konwertuje czcionki (.fnt → .asm)"
	@echo "  make music    — konwertuje muzykę (.sap → .rmt → .asm → MADS)"
	@echo "  make clean    — usuwa pliki wygenerowane"
	@echo "  make help     — ta pomoc"
	@echo ""
	@echo "Żeby zmienić tło: make clean BG_PREFIX=title-2 && make"
