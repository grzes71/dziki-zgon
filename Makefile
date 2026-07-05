# Makefile — Wiedźmin: Dziki Zgon
# Budowanie projektu na Atari 800 XL / 65 XE

# ---- Narzędzia ----
MADS    := c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
PYTHON  := $(CURDIR)/.venv/Scripts/python.exe
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
GAME_FONT_FNT := fonts/game.fnt
GAME_FONT_ASM := $(GEN_DIR)/game_font.asm

# Muzyka
MUSIC_SAP       := music/title.sap
MUSIC_RMT       := $(GEN_DIR)/title.rmt
MUSIC_ASM_ATASM := $(GEN_DIR)/title_atasm.asm
MUSIC_ASM       := $(GEN_DIR)/title_music.asm
PLAYR_ASM       := $(GEN_DIR)/rmtplayr.asm

TEXTS_SRC := $(wildcard texts/*.txt)
TEXTS_ASM := $(patsubst texts/%.txt, $(GEN_DIR)/%_text.asm, $(TEXTS_SRC))

# Śwat Gry (World Builder)
WORLD_DIR := world
WORLD_GEN_DIR := $(GEN_DIR)/world
WORLD_INC := $(WORLD_GEN_DIR)/world.inc
WORLD_YAMLS := $(wildcard $(WORLD_DIR)/*.yaml) $(wildcard $(WORLD_DIR)/*/*.yaml) $(wildcard $(WORLD_DIR)/*/screens/*.yaml)

# ---- Cele ----
.PHONY: all xex bg go sprites texts fonts music world clean run

all: texts sprites bg go fonts music world xex

# Updated Makefile rules
xex: $(GEN_DIR)/all_texts.asm $(MOON_ASM) $(TITLE_ASM) $(BG_BIN) $(GO_BIN) $(FONT_ASM) $(GAME_FONT_ASM) $(MUSIC_ASM) $(PLAYR_ASM) $(WORLD_INC) $(ASM_MAIN)
	@echo "=== Asemblacja $(ASM_MAIN) → $(XEX_OUT) ==="
	$(MADS) $(ASM_MAIN) -o:$(XEX_OUT) -l:$(GEN_DIR)/game.lst -t:$(GEN_DIR)/game.lab
	@echo "=== Weryfikacja mapy pamięci ==="
	$(PYTHON) scripts/check_memory.py $(GEN_DIR)/game.lab MEMORY_USAGE.md

# Kompilator świata gry
world: $(WORLD_INC)

$(WORLD_INC): $(WORLD_YAMLS)
	-@mkdir $(WORLD_GEN_DIR) 2>nul || mkdir -p $(WORLD_GEN_DIR)
	@echo "=== Kompilacja świata gry ==="
	$(PYTHON) -m world_builder $(WORLD_DIR) $(WORLD_GEN_DIR)

# Generowanie tekstów
texts: $(GEN_DIR)/all_texts.asm

$(GEN_DIR)/all_texts.asm: $(TEXTS_ASM) scripts/gen_texts_list.py
	@echo "=== Generowanie $@ ==="
	-@mkdir $(GEN_DIR)
	$(PYTHON) scripts/gen_texts_list.py $@ $(TEXTS_ASM)

$(GEN_DIR)/%_text.asm: texts/%.txt scripts/rle_compress_text.py
	-@mkdir $(GEN_DIR)
	$(PYTHON) scripts/rle_compress_text.py -i $< -o $@

# Generowanie tła (bin + colors + display list)
bg: $(BG_BIN)

$(BG_BIN): $(BG_IMG) scripts/img2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(BG_IMG) → $(BG_PREFIX).* ==="
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(BG_IMG) 2 --all -o $(BG_PREFIX) --footer 0x5E10 --screen-base 0x4000 -c rle

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
	cd $(GEN_DIR) && $(PYTHON) ../scripts/img2asm.py ../$(GO_IMG) 2 --all -o $(GO_PREFIX) --screen-base 0x4000 -c rle

# Generowanie czcionek
fonts: $(FONT_ASM) $(GAME_FONT_ASM)

$(FONT_ASM): $(FONT_FNT) scripts/fnt2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(FONT_FNT) → $(FONT_ASM) ==="
	$(PYTHON) scripts/fnt2asm.py -i $(FONT_FNT) -o $@ -l FontData

$(GAME_FONT_ASM): $(GAME_FONT_FNT) scripts/fnt2asm.py
	-@mkdir $(GEN_DIR)
	@echo "=== Konwersja $(GAME_FONT_FNT) → $(GAME_FONT_ASM) ==="
	$(PYTHON) scripts/fnt2asm.py -i $(GAME_FONT_FNT) -o $@ -l GameFontData

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
	@echo "  make world    — buduje świat z plików YAML do gen/world"
	@echo "  make bg       — konwertuje obraz tła ($(BG_IMG))"
	@echo "  make sprites  — konwertuje sprite'y (moon + dziki-zgon)"
	@echo "  make fonts    — konwertuje czcionki (.fnt → .asm)"
	@echo "  make music    — konwertuje muzykę (.sap → .rmt → .asm → MADS)"
	@echo "  make clean    — usuwa pliki wygenerowane"
	@echo "  make help     — ta pomoc"
	@echo ""
	@echo "Żeby zmienić tło: make clean BG_PREFIX=title-2 && make"
