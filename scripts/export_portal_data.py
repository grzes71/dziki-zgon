#!/usr/bin/env python3
"""Export structured, validated JSON data for Dziki Zgon game portal.

Extracts data directly from source-of-truth files:
- world/ (YAML maps, screens, objects, enemies, items)
- sprites/ (JSON sprite definitions)
- img/ & fonts/ & chars/ (real graphical assets)
- audio/ (POKEY compositions in JSON and DSL formats)
- texts/ (story, titles, endings, travel narratives)
- MEMORY_USAGE.md & check_memory.py & dziki_zgon.xex (memory layout)
- git tags & HISTORY.md (releases & development timeline)

Validates all outputs against Pydantic schemas and saves to reports/portal/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from pydantic import BaseModel, ConfigDict, Field
from PIL import Image

# Import existing world builder parser and models
from world_builder.parser import parse_world_dir, load_yaml
from world_builder.model import GameWorld


# ============================================================================
# Pydantic Schemas for Portal Validation
# ============================================================================

class GamePlatform(BaseModel):
    system: str
    cpu: str
    ram: str
    video: str
    sound: str
    tv_system: str
    media: str
    controls: str


class GameStory(BaseModel):
    title: str
    prologue: str
    game_over_fail: Dict[str, str]
    game_over_success: Dict[str, str]
    travel_texts: Dict[str, str]


class GameControl(BaseModel):
    input: str
    action: str


class GameStats(BaseModel):
    regions_count: int
    screens_count: int
    objects_count: int
    enemies_count: int
    items_count: int
    sprites_count: int
    music_tracks_count: int
    binary_size_bytes: Optional[int] = None
    memory_headroom_bytes: int


class GamePortalData(BaseModel):
    id: str = "dziki-zgon"
    title: str
    tagline: str
    version: str
    repository: str
    portal_url: str
    platform: GamePlatform
    story: GameStory
    controls: List[GameControl]
    features: List[str]
    stats: GameStats


class ScreenExitsData(BaseModel):
    north: Optional[str] = None
    south: Optional[str] = None
    east: Optional[str] = None
    west: Optional[str] = None


class ScreenObjectData(BaseModel):
    object: str
    x: int
    y: int
    repeat_x: int = 1
    repeat_y: int = 1
    type: Optional[str] = None
    target_region: Optional[str] = None
    message_travel: Optional[str] = None
    conditions_met: Optional[str] = None
    conditions_unmet: Optional[str] = None
    items_required: Optional[List[int]] = None
    items_provided: Optional[List[int]] = None
    cost_of_travel: Optional[int] = None
    game_over: Optional[bool] = None
    # Enriched from object definition
    size: Optional[Dict[str, int]] = None
    blocking: Optional[bool] = None
    interactive: Optional[bool] = None
    secret: Optional[bool] = None
    tags: List[str] = Field(default_factory=list)


class ScreenEnemyData(BaseModel):
    enemy: str
    name: str
    damage: int
    x: int
    y: int
    strategy: str
    speed: str
    color: str


class ScreenData(BaseModel):
    id: str
    exits: ScreenExitsData
    objects: List[ScreenObjectData]
    enemies: List[ScreenEnemyData]
    objects_count: int
    enemies_count: int


class PaletteColor(BaseModel):
    atari: int
    hex: str
    rgb: List[int]


class RegionData(BaseModel):
    id: str
    name: str
    damage: int
    layout: Dict[str, int]
    start_screen: str
    music: str
    palette: Dict[str, PaletteColor]
    portal_entries: Dict[str, Dict[str, Any]]
    travel_text: Optional[str] = None
    screens_count: int
    screens: List[ScreenData]


class TransitionLink(BaseModel):
    type: str  # "screen_exit" or "region_portal"
    from_region: str
    from_screen: str
    direction: Optional[str] = None
    to_region: str
    to_screen: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldPortalData(BaseModel):
    start_region: str
    start_screen: str
    start_position: Dict[str, int]
    regions_count: int
    screens_count: int
    regions: List[RegionData]
    transitions: List[TransitionLink]


class ObjectDefData(BaseModel):
    id: str
    code: int
    size: Dict[str, int]
    flags: Dict[str, bool]
    tiles: List[int]
    tags: List[str]
    usage_count: int
    regions_found: List[str]


class InventoryItemData(BaseModel):
    id: int
    description: str
    charset_position: int
    consumable: bool
    placed_instances: List[Dict[str, Any]]


class EnemyTypeData(BaseModel):
    id: str
    name: str
    damage: int
    instances_count: int
    regions_found: List[str]


class ObjectsPortalData(BaseModel):
    total_unique_objects: int
    total_unique_items: int
    total_unique_enemies: int
    objects: List[ObjectDefData]
    items: List[InventoryItemData]
    enemies: List[EnemyTypeData]
    enemy_colors: Dict[str, PaletteColor]


class SpriteAnimation(BaseModel):
    frame_duration: int
    loop: bool


class SpriteFrame(BaseModel):
    frame_index: int
    pixels: List[str]


class SpriteData(BaseModel):
    id: str
    description: Optional[str] = None
    source_file: str
    width: int
    height: int
    color: int
    color_mode: int
    color2: Optional[int] = None
    animation: Optional[SpriteAnimation] = None
    frames_count: int
    frames: List[SpriteFrame]


class PMGBitmapData(BaseModel):
    id: str
    name: str
    source_file: str
    width: int
    height: int
    bpp: int
    players_count: int
    bytes_size: int
    compression: str


class SpritesPortalData(BaseModel):
    sprites_count: int
    sprites: List[SpriteData]
    pmg_bitmaps: List[PMGBitmapData]


class ImageAssetData(BaseModel):
    id: str
    filename: str
    path: str
    width: int
    height: int
    color_mode: str
    bytes_size: int
    antic_mode: str
    description: str


class FontAssetData(BaseModel):
    id: str
    path: str
    bytes_size: int
    character_count: int
    memory_address: str
    description: str


class AnimatedCharData(BaseModel):
    index: int
    cycles_count: int
    description: str


class RotatedCharData(BaseModel):
    index: int
    duration: int


class AssetsPortalData(BaseModel):
    images: List[ImageAssetData]
    fonts: List[FontAssetData]
    animated_chars: List[AnimatedCharData]
    rotated_chars: List[RotatedCharData]


class MusicTrackData(BaseModel):
    id: str
    title: str
    author: str
    format: str
    source_file: str
    key: Optional[str] = None
    mode: Optional[str] = None
    bpm: Optional[int] = None
    duration_seconds: Optional[float] = None
    description: Optional[str] = None
    channels_count: int
    memory_label: str
    memory_address: str
    patterns_count: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AudioDriverData(BaseModel):
    name: str
    source_file: str
    memory_base: str
    size_bytes: int
    update_rate_hz: int
    channels: int
    description: str


class MusicPortalData(BaseModel):
    tracks_count: int
    tracks: List[MusicTrackData]
    driver: AudioDriverData


class MemorySegmentData(BaseModel):
    address_range: str
    start_hex: str
    end_hex: str
    start_dec: int
    end_dec: int
    size_bytes: int
    symbol: str
    area_type: str
    description: str


class ZeroPageEntry(BaseModel):
    address_range: str
    start_hex: str
    end_hex: str
    size_bytes: int
    symbol: str
    description: str


class FreeRegion(BaseModel):
    address_range: str
    start_hex: str
    end_hex: str
    size_bytes: int
    status: str = "safe_usable"  # "safe_usable" | "reserved_alignment"
    is_safe_for_allocation: bool = True
    description: str


class BinaryProvenance(BaseModel):
    origin: str  # "local_build" | "release_asset" | "unavailable"
    source_commit_sha: Optional[str] = None
    binary_sha256: Optional[str] = None
    release_tag: Optional[str] = None
    built_from_current_source: bool = False


class BinaryXexSegment(BaseModel):
    start_hex: str
    end_hex: str
    size_bytes: int


class BinaryInfoData(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    segments_count: int
    segments: List[BinaryXexSegment]
    run_address: Optional[str] = None
    init_addresses: List[str] = Field(default_factory=list)


class MemoryPortalData(BaseModel):
    total_ram_bytes: int = 65536
    usable_ram_limit: str = "$BFFF (49,152 B)"
    os_rom_boundary: str = "$C000"
    hardware_regs_boundary: str = "$D000 - $DFFF"
    basic_disabled: bool = True
    os_rom_enabled: bool = True
    total_mapped_bytes: int
    free_headroom_bytes: int
    safe_free_headroom_bytes: int
    reserved_headroom_bytes: int
    binary_provenance: BinaryProvenance
    segments: List[MemorySegmentData]
    zero_page: List[ZeroPageEntry]
    free_regions: List[FreeRegion]
    binary: Optional[BinaryInfoData] = None


class ReleaseItemData(BaseModel):
    tag: str
    version: str
    date: str
    title: str
    commit_sha: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class TimelineItemData(BaseModel):
    date: str
    title: str
    bullets: List[str]


class ReleasesPortalData(BaseModel):
    releases_count: int
    releases: List[ReleaseItemData]
    timeline: List[TimelineItemData] = Field(default_factory=list)


class LatestPortalData(BaseModel):
    version: str
    tag: str
    release_date: str
    binary_name: str
    binary_size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    download_url: str
    repository: str
    requirements: str
    highlights: List[str]


def get_git_commit_sha(root_dir: Path) -> Optional[str]:
    """Get current git commit SHA from environment or git command."""
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha.strip()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def resolve_game_binary(
    root_dir: Path,
    binary_path: Optional[Path] = None,
    binary_source: str = "local_build",
    release_tag: Optional[str] = None,
    fetch_if_missing: bool = False,
) -> Tuple[Optional[Path], BinaryProvenance]:
    """Resolve dziki_zgon.xex with explicit provenance tracking.
    
    Ensures source and binary consistency:
    - Never silently falls back to an older published binary when a current-source build is expected.
    - Records binary origin, SHA256, and git commit SHA in provenance.
    """
    xex_path = binary_path or (root_dir / "dziki_zgon.xex")
    commit_sha = get_git_commit_sha(root_dir)

    # 1. Local file already exists
    if xex_path.is_file() and xex_path.stat().st_size > 0:
        data = xex_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        origin = binary_source if binary_source in ["local_build", "release_asset"] else "local_build"
        is_current = (origin == "local_build")

        # Mirror to website/public/download if directory exists
        website_dl_dir = root_dir / "website" / "public" / "download"
        if website_dl_dir.exists():
            dl_target = website_dl_dir / "dziki_zgon.xex"
            if not dl_target.exists() or dl_target.stat().st_size != xex_path.stat().st_size:
                dl_target.write_bytes(data)

        provenance = BinaryProvenance(
            origin=origin,
            source_commit_sha=commit_sha,
            binary_sha256=sha256,
            release_tag=release_tag,
            built_from_current_source=is_current,
        )
        return xex_path, provenance

    # 2. Local file missing, but fetch_if_missing is explicitly requested (e.g. for release deploy)
    if fetch_if_missing or binary_source == "release_asset":
        tag = release_tag or "latest"
        url = (
            f"https://github.com/grzes71/dziki-zgon/releases/download/{tag}/dziki_zgon.xex"
            if release_tag
            else "https://github.com/grzes71/dziki-zgon/releases/latest/download/dziki_zgon.xex"
        )
        print(f"Fetching release binary from {url}...")
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "DzikiZgonPortal/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = resp.read()
                    xex_path.write_bytes(data)
                    sha256 = hashlib.sha256(data).hexdigest()
                    print(f"[OK] Downloaded release {xex_path.name} ({len(data)} bytes, sha256={sha256[:8]}...)")

                    website_dl_dir = root_dir / "website" / "public" / "download"
                    if website_dl_dir.exists():
                        (website_dl_dir / "dziki_zgon.xex").write_bytes(data)

                    provenance = BinaryProvenance(
                        origin="release_asset",
                        source_commit_sha=commit_sha,
                        binary_sha256=sha256,
                        release_tag=release_tag,
                        built_from_current_source=False,
                    )
                    return xex_path, provenance
        except Exception as e:
            print(f"Warning: Could not fetch release binary from {url} ({e})", file=sys.stderr)

    # 3. Binary missing and not fetching: do NOT silently substitute an unrelated older binary
    print(f"[INFO] dziki_zgon.xex not found. Run 'make all' or 'make xex' to compile local binary for analysis.")
    provenance = BinaryProvenance(
        origin="unavailable",
        source_commit_sha=commit_sha,
        binary_sha256=None,
        release_tag=release_tag,
        built_from_current_source=False,
    )
    return None, provenance


def ensure_game_binary(root_dir: Path) -> Optional[Path]:
    """Compatibility helper returning binary path if available."""
    xex_path, _ = resolve_game_binary(root_dir)
    return xex_path


def parse_zeropage_asm(zp_path: Path) -> List[Dict[str, Any]]:
    """Parse zeropage.asm as single source of truth for Zero Page registers."""
    if not zp_path.exists():
        return []

    entries = []
    lines = zp_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if " equ " in line:
            parts = line.split(" equ ", 1)
            sym = parts[0].strip()
            rest = parts[1].strip()
            comment = ""
            if ";" in rest:
                addr_part, comment = rest.split(";", 1)
                comment = comment.strip()
            else:
                addr_part = rest

            m_addr = re.search(r"\$([0-9A-Fa-f]+)", addr_part)
            if not m_addr:
                continue

            addr_dec = int(m_addr.group(1), 16)
            size = 1
            if "2 bajty" in comment or "PTR" in sym:
                size = 2
            elif sym == "PLAYER_ZP_BASE":
                size = 10
                if not comment:
                    comment = "Audio Player Zero Page ($CB - $D4: 10 bajtów)"

            end_dec = addr_dec + size - 1
            addr_range = f"${addr_dec:04X}–${end_dec:04X}" if size > 1 else f"${addr_dec:04X}–${addr_dec:04X}"

            entries.append({
                "address_range": addr_range,
                "start_hex": f"${addr_dec:04X}",
                "end_hex": f"${end_dec:04X}",
                "size_bytes": size,
                "symbol": sym,
                "description": comment or sym
            })

    entries.sort(key=lambda x: int(x["start_hex"].lstrip("$"), 16))
    return entries

def atari_color_to_rgb(atari_byte: int) -> List[int]:
    """Convert an Atari 8-bit color byte (hue 0-15, lum 0-14 even) to approximate RGB."""
    # Approximate NTSC/PAL palette mapping for Atari 8-bit
    # Base hue angles on chrominance subcarrier
    hues = [
        (0, 0),      # 0 = grayscale
        (20, 0.4),   # 1 = gold / orange
        (40, 0.45),  # 2 = orange-brown
        (5, 0.5),    # 3 = red-orange
        (345, 0.55), # 4 = pink / red
        (315, 0.5),  # 5 = purple
        (280, 0.55), # 6 = violet / blue-violet
        (250, 0.6),  # 7 = blue
        (220, 0.55), # 8 = blue-cyan
        (190, 0.5),  # 9 = cyan
        (150, 0.45), # 10 = blue-green
        (120, 0.5),  # 11 = green
        (90, 0.5),   # 12 = yellow-green
        (60, 0.55),  # 13 = yellow
        (45, 0.5),   # 14 = orange-yellow
        (30, 0.45),  # 15 = light orange
    ]
    hue_idx = (atari_byte >> 4) & 0x0F
    lum_idx = (atari_byte & 0x0E) / 14.0  # 0.0 to 1.0

    if hue_idx == 0:
        val = int(lum_idx * 255)
        return [val, val, val]

    # Convert simple HSL to RGB
    h, s = hues[hue_idx]
    l = 0.15 + lum_idx * 0.75
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if 0 <= h < 60:
        r1, g1, b1 = c, x, 0
    elif 60 <= h < 120:
        r1, g1, b1 = x, c, 0
    elif 120 <= h < 180:
        r1, g1, b1 = 0, c, x
    elif 180 <= h < 240:
        r1, g1, b1 = 0, x, c
    elif 240 <= h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x

    return [int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255)]


def get_git_output(cmd: List[str]) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""


def parse_history_md(history_path: Path) -> List[Dict[str, Any]]:
    """Parse HISTORY.md entries into structured release/change records."""
    if not history_path.exists():
        return []

    content = history_path.read_text(encoding="utf-8")
    entries: List[Dict[str, Any]] = []

    # Format: ## [YYYY-MM-DD] - [Brief Title]
    pattern = re.compile(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*-\s*(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(content))

    for i, match in enumerate(matches):
        date_str = match.group(1)
        title_str = match.group(2).strip()

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start_pos:end_pos].strip()

        bullets = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- "):
                bullets.append(line[2:].strip())

        entries.append({
            "date": date_str,
            "title": title_str,
            "bullets": bullets
        })

    return entries


def parse_memory_usage_md(memory_path: Path) -> Dict[str, Any]:
    """Parse MEMORY_USAGE.md for segments, zero page, and free RAM analysis."""
    if not memory_path.exists():
        return {"segments": [], "zero_page": [], "free_regions": [], "headroom_bytes": 0}

    content = memory_path.read_text(encoding="utf-8")

    # Parse detailed memory table
    table_section = re.search(r"## Szczegółowa Tabela Zajętości Pamięci\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    segments = []
    zero_page = []

    if table_section:
        lines = table_section.group(1).strip().splitlines()
        row_re = re.compile(
            r"\|\s*\*\*`\$([0-9A-Fa-f]{4})`\s*[-–]\s*`\$([0-9A-Fa-f]{4})`\*\*\s*\|\s*(\d+)\s*B\s*\|\s*`?([^|`]+)`?\s*\|\s*([^|]+)\|\s*([^|]+)\|"
        )
        for line in lines:
            line = line.strip()
            if not line.startswith("|") or line.startswith("| Zakres") or line.startswith("| :---"):
                continue
            m = row_re.search(line)
            if m:
                s_hex = m.group(1).upper()
                e_hex = m.group(2).upper()
                size_dec = int(m.group(3))
                symbol = m.group(4).strip()
                area_type = m.group(5).strip()
                desc = m.group(6).strip()

                s_dec = int(s_hex, 16)
                e_dec = int(e_hex, 16)

                item = {
                    "address_range": f"${s_hex}–${e_hex}",
                    "start_hex": f"${s_hex}",
                    "end_hex": f"${e_hex}",
                    "start_dec": s_dec,
                    "end_dec": e_dec,
                    "size_bytes": size_dec,
                    "symbol": symbol,
                    "area_type": area_type,
                    "description": desc
                }

                if area_type == "Zero Page":
                    zero_page.append({
                        "address_range": f"${s_hex}–${e_hex}",
                        "start_hex": f"${s_hex}",
                        "end_hex": f"${e_hex}",
                        "size_bytes": size_dec,
                        "symbol": symbol,
                        "description": desc
                    })
                else:
                    segments.append(item)

    # Parse free RAM section
    free_section = re.search(r"## Analiza Wolnej Pamięci RAM\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    free_regions = []
    headroom_bytes = 1834  # default from doc

    if free_section:
        free_lines = free_section.group(1).strip().splitlines()
        free_re = re.compile(r"`\$([0-9A-Fa-f]{4})`\s*[-–]\s*`\$([0-9A-Fa-f]{4})`\s*\(([\d\s]+)\s*B\)[^:]*:\s*(.*)")
        for line in free_lines:
            m = free_re.search(line)
            if m:
                s_hex = m.group(1).upper()
                e_hex = m.group(2).upper()
                sz = int(m.group(3).replace(" ", ""))
                desc = m.group(4).strip().rstrip(".")
                free_regions.append({
                    "address_range": f"${s_hex}–${e_hex}",
                    "start_hex": f"${s_hex}",
                    "end_hex": f"${e_hex}",
                    "size_bytes": sz,
                    "description": desc
                })

        sum_m = re.search(r"to\s*\*\*([\d\s]+)\s*B\*\*", free_section.group(1))
        if sum_m:
            headroom_bytes = int(sum_m.group(1).replace(" ", ""))

    return {
        "segments": segments,
        "zero_page": zero_page,
        "free_regions": free_regions,
        "headroom_bytes": headroom_bytes
    }


def parse_xex_binary(xex_path: Path) -> Optional[Dict[str, Any]]:
    """Parse real Atari DOS 2 XEX binary segments and headers."""
    if not xex_path.exists():
        return None

    data = xex_path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    size_bytes = len(data)

    segments = []
    run_address = None
    init_addresses = []

    pos = 0
    if len(data) >= 2 and data[0] == 0xFF and data[1] == 0xFF:
        pos = 2

    while pos + 4 <= len(data):
        if pos + 2 <= len(data) and data[pos] == 0xFF and data[pos + 1] == 0xFF:
            pos += 2
            continue

        start_addr = data[pos] | (data[pos + 1] << 8)
        end_addr = data[pos + 2] | (data[pos + 3] << 8)
        pos += 4

        if end_addr < start_addr:
            break

        seg_len = end_addr - start_addr + 1
        seg_data = data[pos:pos + seg_len]
        pos += seg_len

        # Check for RUNAD ($02E0) or INITAD ($02E2)
        if start_addr == 0x02E0 and seg_len >= 2:
            run_address = f"${(seg_data[0] | (seg_data[1] << 8)):04X}"
        elif start_addr == 0x02E2 and seg_len >= 2:
            init_addresses.append(f"${(seg_data[0] | (seg_data[1] << 8)):04X}")
        else:
            segments.append({
                "start_hex": f"${start_addr:04X}",
                "end_hex": f"${end_addr:04X}",
                "size_bytes": seg_len
            })

    return {
        "filename": xex_path.name,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "segments_count": len(segments),
        "segments": segments,
        "run_address": run_address or "$2000",
        "init_addresses": init_addresses
    }


def parse_music_dsl(dsl_path: Path) -> Dict[str, Any]:
    """Parse a POKEY music DSL file."""
    content = dsl_path.read_text(encoding="utf-8")
    meta: Dict[str, Any] = {
        "title": "Title Theme",
        "author": "POKEY Composer",
        "key": "D",
        "mode": "MINOR",
        "bpm": 90,
        "bass": "16BIT",
        "patterns": [],
        "sequence": [],
        "channels_used": 3
    }
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("TITLE "):
            meta["title"] = line[6:].strip(' "')
        elif line.startswith("AUTHOR "):
            meta["author"] = line[7:].strip(' "')
        elif line.startswith("KEY "):
            meta["key"] = line[4:].strip()
        elif line.startswith("MODE "):
            meta["mode"] = line[5:].strip()
        elif line.startswith("BPM "):
            try:
                meta["bpm"] = int(line[4:].strip())
            except ValueError:
                pass
        elif line.startswith("BASS "):
            meta["bass"] = line[5:].strip()
        elif line.startswith("SEQUENCE "):
            meta["sequence"] = line[9:].strip().split()
        elif line.startswith("[PATTERN "):
            pname = line.split()[1]
            meta["patterns"].append(pname)

    return meta


# ============================================================================
# Main Pipeline Implementation
# ============================================================================

class PortalDataPipeline:
    def __init__(
        self,
        root_dir: Path,
        output_dir: Path,
        binary_path: Optional[Path] = None,
        binary_source: str = "local_build",
        release_tag: Optional[str] = None,
        fetch_if_missing: bool = False,
    ):
        self.root_dir = root_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.binary_path = binary_path
        self.binary_source = binary_source
        self.release_tag = release_tag
        self.fetch_if_missing = fetch_if_missing

        # Preloaded models and cache
        self.world_model: Optional[GameWorld] = None
        self.raw_objects_data: Dict[str, Any] = {}
        self.raw_items_data: Dict[str, Any] = {}
        self.raw_enemies_data: Dict[str, Any] = {}

    def run(self) -> None:
        print(f"=== Dziki Zgon Portal Data Pipeline ===")
        print(f"Root: {self.root_dir}")
        print(f"Destination: {self.output_dir}")

        # 1. Parse World and source configs
        self._load_game_sources()

        # 2. Generate each JSON report and validate
        game_data = self.generate_game_data()
        self._save_json("game.json", game_data)

        world_data = self.generate_world_data()
        self._save_json("world.json", world_data)

        objects_data = self.generate_objects_data()
        self._save_json("objects.json", objects_data)

        sprites_data = self.generate_sprites_data()
        self._save_json("sprites.json", sprites_data)

        assets_data = self.generate_assets_data()
        self._save_json("assets.json", assets_data)

        music_data = self.generate_music_data()
        self._save_json("music.json", music_data)

        memory_data = self.generate_memory_data()
        self._save_json("memory.json", memory_data)

        releases_data = self.generate_releases_data()
        self._save_json("releases.json", releases_data)

        latest_data = self.generate_latest_data(releases_data, memory_data)
        self._save_json("latest.json", latest_data)

        print(f"[OK] All 9 portal data reports successfully generated and validated.")

    def _load_game_sources(self) -> None:
        world_dir = self.root_dir / "world"
        if not world_dir.exists():
            raise FileNotFoundError(f"Missing {world_dir}")

        # Load Pydantic GameWorld
        self.world_model = parse_world_dir(world_dir)
        self.raw_objects_data = load_yaml(world_dir / "objects.yaml")
        if (world_dir / "items.yaml").exists():
            self.raw_items_data = load_yaml(world_dir / "items.yaml")
        if (world_dir / "enemies.yaml").exists():
            self.raw_enemies_data = load_yaml(world_dir / "enemies.yaml")

    def _save_json(self, filename: str, model: BaseModel) -> None:
        target_path = self.output_dir / filename
        data_dict = model.model_dump(by_alias=True)
        # Deterministic serialization: indent 2, sort_keys=True
        json_str = json.dumps(data_dict, indent=2, sort_keys=True, ensure_ascii=False)
        target_path.write_text(json_str, encoding="utf-8")
        print(f"  -> Generated {filename} ({target_path.stat().st_size} bytes)")

        # Also mirror to website/src/data when exporting to canonical reports/portal directory
        default_reports_dir = (self.root_dir / "reports" / "portal").resolve()
        website_dir = self.root_dir / "website"
        if self.output_dir == default_reports_dir and website_dir.exists():
            website_data_dir = website_dir / "src" / "data"
            website_data_dir.mkdir(parents=True, exist_ok=True)
            (website_data_dir / filename).write_text(json_str, encoding="utf-8")

    def generate_game_data(self) -> GamePortalData:
        title_txt_path = self.root_dir / "texts" / "title.txt"
        version = "0.5.0"
        if title_txt_path.exists():
            content = title_txt_path.read_text(encoding="utf-8")
            m = re.search(r"wersja\s+([\d\.]+)", content, re.IGNORECASE)
            if m:
                version = m.group(1).strip()

        # Read story and endings
        texts_dir = self.root_dir / "texts"
        prologue = (texts_dir / "contents-story.txt").read_text(encoding="utf-8").strip() if (texts_dir / "contents-story.txt").exists() else ""
        header_story = (texts_dir / "header-story.txt").read_text(encoding="utf-8").strip() if (texts_dir / "header-story.txt").exists() else "dziki zgon"

        header_fail = (texts_dir / "header-gameover-fail.txt").read_text(encoding="utf-8").strip() if (texts_dir / "header-gameover-fail.txt").exists() else ""
        text_fail = (texts_dir / "contents-gameover-fail.txt").read_text(encoding="utf-8").strip() if (texts_dir / "contents-gameover-fail.txt").exists() else ""

        header_succ = (texts_dir / "header-gameover-success.txt").read_text(encoding="utf-8").strip() if (texts_dir / "header-gameover-success.txt").exists() else ""
        text_succ = (texts_dir / "contents-gameover-success.txt").read_text(encoding="utf-8").strip() if (texts_dir / "contents-gameover-success.txt").exists() else ""

        travel_texts = {}
        for travel_p in texts_dir.glob("contents-travel-*.txt"):
            reg_id = travel_p.stem.replace("contents-travel-", "")
            travel_texts[reg_id] = travel_p.read_text(encoding="utf-8").strip()

        # Count world statistics
        assert self.world_model is not None
        reg_count = len(self.world_model.regions)
        screen_count = sum(len(r.screens) for r in self.world_model.regions)
        obj_count = len(self.world_model.objects)
        enemy_count = len(self.world_model.enemies)
        item_count = len(self.world_model.inventory_items)

        sprites_dir = self.root_dir / "sprites"
        sprite_count = len(list(sprites_dir.glob("*.sprite.json")))

        audio_dir = self.root_dir / "audio"
        music_tracks_count = len(list(audio_dir.glob("dziki-zgon-*.json"))) + (1 if (audio_dir / "dziki-zgon-title.dsl").exists() else 0)

        xex_path, _ = resolve_game_binary(
            self.root_dir,
            binary_path=self.binary_path,
            binary_source=self.binary_source,
            release_tag=self.release_tag,
            fetch_if_missing=self.fetch_if_missing,
        )
        bin_size = xex_path.stat().st_size if (xex_path and xex_path.is_file()) else None

        mem_info = parse_memory_usage_md(self.root_dir / "MEMORY_USAGE.md")

        return GamePortalData(
            title="Dziki Zgon",
            tagline="Przygodowo-zręcznościowa gra z widokiem z góry na Atari 800 XL / 65 XE — humorystyczna parodia Wiedźmina",
            version=version,
            repository="https://github.com/grzes71/dziki-zgon",
            portal_url="https://grzes71.github.io/dziki-zgon/",
            platform=GamePlatform(
                system="Atari 800 XL / 65 XE",
                cpu="MOS 6502 @ 1.77 MHz (PAL) / 1.79 MHz (NTSC)",
                ram="64 KB RAM (bez rozszerzeń)",
                video="ANTIC + GTIA (ANTIC Modes 2, 3, 4, 5, D, E)",
                sound="POKEY 4-channel sound synthesizer",
                tv_system="PAL 50 Hz (zoptymalizowany timing)",
                media="Atari DOS 2 Binary Executable (.XEX)",
                controls="Atari digital joystick (Port 1) + przycisk FIRE"
            ),
            story=GameStory(
                title=header_story,
                prologue=prologue,
                game_over_fail={"header": header_fail, "text": text_fail},
                game_over_success={"header": header_succ, "text": text_succ},
                travel_texts=travel_texts
            ),
            controls=[
                GameControl(input="Joystick Góra / Dół / Lewo / Prawo", action="Płynne sterowanie Gerwantem w 4 kierunkach"),
                GameControl(input="Przycisk FIRE (Spust)", action="Interakcja z obiektami, badanie świata, rozpoczęcie gry"),
                GameControl(input="Klawisze konsoli (START/OPTION)", action="Start gry / pauza z poziomu konsoli Atari")
            ],
            features=[
                "Otwarty świat złożony z 5 różnorodnych regionów i 35 autorskich ekranów",
                "Struktury danych Structure-of-Arrays (SoA) zoptymalizowane pod bezpośrednie indeksowanie 6502",
                "Wielowarstwowy bohater (P0 + P1) w trybie GTIA OR-mix (4 kolory) oraz wrogowie jako 5. gracz",
                "Dynamiczne DLI podmieniające w locie zestaw znaków (CHBASE) oraz paletę kolorów HUD",
                "Animowany zestaw znaków kafelków (płynąca woda, bagno, gorejące pochodnie) taktowany przerwaniem VBLANK",
                "Autorski, relokowalny 4-kanałowy sterownik muzyki POKEY (50 Hz interrupt-driven)",
                "Ścisłe zmieszczenie wszystkich danych i kodu gry poniżej granicy OS ROM ($BFFF)"
            ],
            stats=GameStats(
                regions_count=reg_count,
                screens_count=screen_count,
                objects_count=obj_count,
                enemies_count=enemy_count,
                items_count=item_count,
                sprites_count=sprite_count,
                music_tracks_count=music_tracks_count,
                binary_size_bytes=bin_size,
                memory_headroom_bytes=mem_info["headroom_bytes"]
            )
        )

    def generate_world_data(self) -> WorldPortalData:
        assert self.world_model is not None
        world_yaml_path = self.root_dir / "world" / "world.yaml"
        world_cfg = load_yaml(world_yaml_path).get("world", {})

        objects_lookup = {obj.id: obj for obj in self.world_model.objects}
        enemies_lookup = {en.id: en for en in self.world_model.enemies}

        regions_list: List[RegionData] = []
        transitions_list: List[TransitionLink] = []

        texts_dir = self.root_dir / "texts"

        for reg in self.world_model.regions:
            # Region palette
            pal_dict: Dict[str, PaletteColor] = {}
            for col_key, atari_val in reg.palette.items():
                rgb = atari_color_to_rgb(atari_val)
                hex_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                pal_dict[col_key] = PaletteColor(atari=atari_val, hex=hex_str, rgb=rgb)

            # Portal entries
            portal_entries_dict: Dict[str, Dict[str, Any]] = {}
            for target_reg, pentry in reg.portal_entries.items():
                portal_entries_dict[target_reg] = {
                    "screen": pentry.screen,
                    "x": pentry.x,
                    "y": pentry.y
                }
                transitions_list.append(TransitionLink(
                    type="region_portal",
                    from_region=reg.id,
                    from_screen=pentry.screen,
                    direction=None,
                    to_region=target_reg,
                    to_screen="",  # Resolved on destination
                    metadata={"target_region": target_reg, "entry_coords": {"x": pentry.x, "y": pentry.y}}
                ))

            # Travel text if available
            travel_p = texts_dir / f"contents-travel-{reg.id}.txt"
            travel_text = travel_p.read_text(encoding="utf-8").strip() if travel_p.exists() else None

            # Process screens
            screens_list: List[ScreenData] = []
            for sc in reg.screens:
                # Exits
                exits_data = ScreenExitsData(
                    north=sc.exits.north,
                    south=sc.exits.south,
                    east=sc.exits.east,
                    west=sc.exits.west
                )

                for dir_name, target_sc in [("north", sc.exits.north), ("south", sc.exits.south), ("east", sc.exits.east), ("west", sc.exits.west)]:
                    if target_sc:
                        transitions_list.append(TransitionLink(
                            type="screen_exit",
                            from_region=reg.id,
                            from_screen=sc.id,
                            direction=dir_name,
                            to_region=reg.id,
                            to_screen=target_sc,
                            metadata={}
                        ))

                # Objects
                objs_data: List[ScreenObjectData] = []
                for oinst in sc.objects:
                    obj_def = objects_lookup.get(oinst.object)
                    objs_data.append(ScreenObjectData(
                        object=oinst.object,
                        x=oinst.x,
                        y=oinst.y,
                        repeat_x=oinst.repeat_x,
                        repeat_y=oinst.repeat_y,
                        type=oinst.type,
                        target_region=oinst.target_region,
                        message_travel=oinst.message_travel,
                        conditions_met=oinst.conditions_met,
                        conditions_unmet=oinst.conditions_unmet,
                        items_required=oinst.items_required,
                        items_provided=oinst.items_provided,
                        cost_of_travel=oinst.cost_of_travel,
                        game_over=oinst.game_over,
                        size={"width": obj_def.size.width, "height": obj_def.size.height} if obj_def else None,
                        blocking=obj_def.flags.blocking if obj_def else None,
                        interactive=obj_def.flags.interactive if obj_def else None,
                        secret=obj_def.flags.secret if obj_def else None,
                        tags=obj_def.tags if obj_def else []
                    ))

                # Enemies
                en_data: List[ScreenEnemyData] = []
                for einst in sc.enemies:
                    e_def = enemies_lookup.get(einst.enemy)
                    en_data.append(ScreenEnemyData(
                        enemy=einst.enemy,
                        name=e_def.name if e_def else einst.enemy.lower(),
                        damage=e_def.damage if e_def else 1,
                        x=einst.x,
                        y=einst.y,
                        strategy=einst.strategy,
                        speed=einst.speed,
                        color=einst.color
                    ))

                screens_list.append(ScreenData(
                    id=sc.id,
                    exits=exits_data,
                    objects=objs_data,
                    enemies=en_data,
                    objects_count=len(objs_data),
                    enemies_count=len(en_data)
                ))

            # Sort screens deterministically by ID
            screens_list.sort(key=lambda s: s.id)

            regions_list.append(RegionData(
                id=reg.id,
                name=reg.name,
                damage=reg.damage,
                layout={"rows": reg.layout.rows, "columns": reg.layout.columns},
                start_screen=reg.start_screen,
                music=reg.music,
                palette=pal_dict,
                portal_entries=portal_entries_dict,
                travel_text=travel_text,
                screens_count=len(screens_list),
                screens=screens_list
            ))

        regions_list.sort(key=lambda r: r.id)

        return WorldPortalData(
            start_region=world_cfg.get("start_region", "WHITE_FIELD"),
            start_screen=world_cfg.get("start_screen", "TAVERN"),
            start_position=world_cfg.get("start_position", {"x": 23, "y": 8}),
            regions_count=len(regions_list),
            screens_count=sum(r.screens_count for r in regions_list),
            regions=regions_list,
            transitions=transitions_list
        )

    def generate_objects_data(self) -> ObjectsPortalData:
        assert self.world_model is not None

        # Build usage and presence statistics across all screens
        obj_usage: Dict[str, int] = {}
        obj_regions: Dict[str, set] = {}
        item_placements: Dict[int, List[Dict[str, Any]]] = {}
        enemy_counts: Dict[str, int] = {}
        enemy_regions: Dict[str, set] = {}

        for reg in self.world_model.regions:
            for sc in reg.screens:
                for obj in sc.objects:
                    obj_usage[obj.object] = obj_usage.get(obj.object, 0) + 1
                    obj_regions.setdefault(obj.object, set()).add(reg.id)

                    if obj.items_provided:
                        for itm_id in obj.items_provided:
                            item_placements.setdefault(itm_id, []).append({
                                "region": reg.id,
                                "screen": sc.id,
                                "x": obj.x,
                                "y": obj.y,
                                "type": "provided"
                            })
                    if obj.items_required:
                        for itm_id in obj.items_required:
                            item_placements.setdefault(itm_id, []).append({
                                "region": reg.id,
                                "screen": sc.id,
                                "x": obj.x,
                                "y": obj.y,
                                "type": "required"
                            })

                for en in sc.enemies:
                    enemy_counts[en.enemy] = enemy_counts.get(en.enemy, 0) + 1
                    enemy_regions.setdefault(en.enemy, set()).add(reg.id)

        # Objects list
        objects_list: List[ObjectDefData] = []
        for obj in self.world_model.objects:
            objects_list.append(ObjectDefData(
                id=obj.id,
                code=obj.code,
                size={"width": obj.size.width, "height": obj.size.height},
                flags={
                    "blocking": obj.flags.blocking,
                    "interactive": obj.flags.interactive,
                    "secret": obj.flags.secret
                },
                tiles=obj.tiles,
                tags=obj.tags,
                usage_count=obj_usage.get(obj.id, 0),
                regions_found=sorted(list(obj_regions.get(obj.id, set())))
            ))
        objects_list.sort(key=lambda o: o.code)

        # Items list
        items_list: List[InventoryItemData] = []
        for itm in self.world_model.inventory_items:
            items_list.append(InventoryItemData(
                id=itm.id,
                description=itm.description,
                charset_position=itm.charset_position,
                consumable=itm.consumable,
                placed_instances=item_placements.get(itm.id, [])
            ))
        items_list.sort(key=lambda i: i.id)

        # Enemies list
        enemies_list: List[EnemyTypeData] = []
        for en in self.world_model.enemies:
            enemies_list.append(EnemyTypeData(
                id=en.id,
                name=en.name,
                damage=en.damage,
                instances_count=enemy_counts.get(en.id, 0),
                regions_found=sorted(list(enemy_regions.get(en.id, set())))
            ))
        enemies_list.sort(key=lambda e: e.id)

        formatted_enemy_colors: Dict[str, PaletteColor] = {}
        for cname, atari_val in self.raw_enemies_data.get("colors", {}).items():
            rgb = atari_color_to_rgb(atari_val)
            hex_str = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            formatted_enemy_colors[cname] = PaletteColor(atari=atari_val, hex=hex_str, rgb=rgb)

        return ObjectsPortalData(
            total_unique_objects=len(objects_list),
            total_unique_items=len(items_list),
            total_unique_enemies=len(enemies_list),
            objects=objects_list,
            items=items_list,
            enemies=enemies_list,
            enemy_colors=formatted_enemy_colors
        )

    def generate_sprites_data(self) -> SpritesPortalData:
        sprites_dir = self.root_dir / "sprites"
        sprites_list: List[SpriteData] = []

        for p in sorted(sprites_dir.glob("*.sprite.json")):
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)

            for s in raw.get("sprites", []):
                s_id = str(s.get("id"))
                desc = s.get("description")
                w = s.get("width", 8)
                h = s.get("height", 16)
                col = s.get("color", 0)
                col_mode = s.get("color_mode", 1)
                col2 = s.get("color2")

                anim = None
                if "animation" in s:
                    anim = SpriteAnimation(
                        frame_duration=s["animation"].get("frame_duration", 6),
                        loop=s["animation"].get("loop", True)
                    )

                frames: List[SpriteFrame] = []
                for idx, fr in enumerate(s.get("frames", [])):
                    pix = fr.get("pixels", [])
                    frames.append(SpriteFrame(frame_index=idx, pixels=pix))

                sprites_list.append(SpriteData(
                    id=s_id,
                    description=desc,
                    source_file=p.name,
                    width=w,
                    height=h,
                    color=col,
                    color_mode=col_mode,
                    color2=col2,
                    animation=anim,
                    frames_count=len(frames),
                    frames=frames
                ))

        pmg_bitmaps = [
            PMGBitmapData(
                id="MOON",
                name="Księżyc (Moon)",
                source_file="img/moon.png",
                width=32,
                height=24,
                bpp=1,
                players_count=4,
                bytes_size=96,
                compression="RLE (img2asm 1 bpp)"
            ),
            PMGBitmapData(
                id="TITLE_LOGO",
                name="Logo Dziki Zgon",
                source_file="img/dziki-zgon.png",
                width=40,
                height=37,
                bpp=1,
                players_count=5,
                bytes_size=185,
                compression="RLE (img2asm 1 bpp)"
            )
        ]

        return SpritesPortalData(
            sprites_count=len(sprites_list),
            sprites=sprites_list,
            pmg_bitmaps=pmg_bitmaps
        )

    def generate_assets_data(self) -> AssetsPortalData:
        # Images
        image_defs = [
            ("title", "img/title.png", "ANTIC E (160×192, 4 kolory)", "Ekran tytułowy gry z podziałem na część graficzną i tekstową"),
            ("travel", "img/travel.png", "ANTIC E (160×184, 4 kolory)", "Ekran przejścia między regionami (w podróży)"),
            ("gameover_fail", "img/screens/game_over-fail.png", "ANTIC D (160×184 narrow, 4 kolory)", "Ekran Game Over — Porażka Gerwanta"),
            ("gameover_success", "img/screens/game_over-success.png", "ANTIC D (160×184 narrow, 4 kolory)", "Ekran Game Over — Sukces i ocalenie godności"),
            ("cover", "cover.png", "RGB High-Res Art", "Oficjalna grafika promocyjna i okładka Dziki Zgon")
        ]

        images_list: List[ImageAssetData] = []
        for img_id, rel_path, antic_mode, desc in image_defs:
            fpath = self.root_dir / rel_path
            if fpath.exists():
                with Image.open(fpath) as im:
                    w, h = im.size
                    mode = im.mode
                images_list.append(ImageAssetData(
                    id=img_id,
                    filename=fpath.name,
                    path=rel_path,
                    width=w,
                    height=h,
                    color_mode=mode,
                    bytes_size=fpath.stat().st_size,
                    antic_mode=antic_mode,
                    description=desc
                ))

        # Fonts
        fonts_list = [
            FontAssetData(
                id="font",
                path="fonts/font.fnt",
                bytes_size=1024,
                character_count=128,
                memory_address="$6000",
                description="Główna czcionka interfejsu (HUD, dialogi, opisy, stopka)"
            ),
            FontAssetData(
                id="game_font",
                path="fonts/game.fnt",
                bytes_size=1024,
                character_count=128,
                memory_address="$6400",
                description="Zestaw kafli świata i terenu dla trybu ANTIC 4/5"
            )
        ]

        # Animated chars
        anim_path = self.root_dir / "chars" / "animated.json"
        anim_chars_list: List[AnimatedCharData] = []
        if anim_path.exists():
            with open(anim_path, "r", encoding="utf-8") as f:
                anim_raw = json.load(f)
            char_descs = {
                112: "Płynąca woda / rzeka",
                78: "Gorejąca pochodnia / ogień",
                113: "Bagno i bąble błota",
                25: "Magiczny portal / wir",
                124: "Krople rosy / roślinność",
                75: "Iskry i zarzewie"
            }
            for ch in anim_raw.get("characters", []):
                idx = ch.get("index")
                anims = ch.get("animation", [])
                anim_chars_list.append(AnimatedCharData(
                    index=idx,
                    cycles_count=len(anims),
                    description=char_descs.get(idx, f"Dynamiczny kafelek #{idx}")
                ))

        # Rotated chars
        rot_path = self.root_dir / "chars" / "rotated.json"
        rotated_chars_list: List[RotatedCharData] = []
        if rot_path.exists():
            with open(rot_path, "r", encoding="utf-8") as f:
                rot_raw = json.load(f)
                for item in rot_raw.get("characters", []):
                    rotated_chars_list.append(RotatedCharData(index=item.get("index", 0), duration=item.get("duration", 0)))

        return AssetsPortalData(
            images=images_list,
            fonts=fonts_list,
            animated_chars=anim_chars_list,
            rotated_chars=rotated_chars_list
        )

    def generate_music_data(self) -> MusicPortalData:
        audio_dir = self.root_dir / "audio"
        tracks: List[MusicTrackData] = []

        # 1. Title DSL
        title_dsl = audio_dir / "dziki-zgon-title.dsl"
        if title_dsl.exists():
            dsl_meta = parse_music_dsl(title_dsl)
            tracks.append(MusicTrackData(
                id="title",
                title=dsl_meta["title"],
                author=dsl_meta["author"],
                format="Atari Music DSL",
                source_file="audio/dziki-zgon-title.dsl",
                key=dsl_meta["key"],
                mode=dsl_meta["mode"],
                bpm=dsl_meta["bpm"],
                duration_seconds=61.44,
                description="Motyw tytułowy w stylu polskich gier 8-bitowych (LK Avalon / Mirage)",
                channels_count=3,
                memory_label="music_title_data",
                memory_address="$AB70–$B14D (1,502 B)",
                patterns_count=len(dsl_meta["patterns"]),
                details={"sequence": dsl_meta["sequence"], "bass_mode": dsl_meta["bass"]}
            ))

        # 2. Intro JSON
        intro_json = audio_dir / "dziki-zgon-intro.json"
        if intro_json.exists():
            with open(intro_json, "r", encoding="utf-8") as f:
                ij = json.load(f)
            meta = ij.get("metadata", {})
            tracks.append(MusicTrackData(
                id="intro",
                title=meta.get("title", "Karczma pod Kwiczącym Dzikiem"),
                author=meta.get("author", "AI Composer"),
                format="atari-music-composition v1",
                source_file="audio/dziki-zgon-intro.json",
                key=meta.get("key"),
                mode=meta.get("mode"),
                bpm=meta.get("bpm"),
                duration_seconds=meta.get("duration_seconds"),
                description=meta.get("description"),
                channels_count=4,
                memory_label="music_intro_data",
                memory_address="$B14E–$B2EC (415 B)",
                patterns_count=len(ij.get("patterns", {})),
                details={"form_plan": ij.get("form_plan", {})}
            ))

        # 3. Game Over Failure
        fail_json = audio_dir / "dziki-zgon-game-over-failure.json"
        if fail_json.exists():
            with open(fail_json, "r", encoding="utf-8") as f:
                fj = json.load(f)
            meta = fj.get("metadata", {})
            tracks.append(MusicTrackData(
                id="gameover_failure",
                title=meta.get("title", "Koniec Przygody"),
                author=meta.get("author", "AI Composer"),
                format="atari-music-composition v1",
                source_file="audio/dziki-zgon-game-over-failure.json",
                key=meta.get("key"),
                mode=meta.get("mode"),
                bpm=meta.get("bpm"),
                duration_seconds=meta.get("duration_seconds"),
                description="Mroczny, melancholijny motyw klęski Gerwanta",
                channels_count=4,
                memory_label="music_gameover_failure_data",
                memory_address="$B2ED–$B4D2 (486 B)",
                patterns_count=len(fj.get("patterns", {})),
                details={}
            ))

        # 4. Game Over Success
        succ_json = audio_dir / "dziki-zgon-game-over-success.json"
        if succ_json.exists():
            with open(succ_json, "r", encoding="utf-8") as f:
                sj = json.load(f)
            meta = sj.get("metadata", {})
            tracks.append(MusicTrackData(
                id="gameover_success",
                title=meta.get("title", "Witcher's Pathetic Victory"),
                author=meta.get("author", "AI Composer"),
                format="atari-music-composition v1",
                source_file="audio/dziki-zgon-game-over-success.json",
                key=meta.get("key"),
                mode=meta.get("mode"),
                bpm=meta.get("bpm"),
                duration_seconds=meta.get("duration_seconds"),
                description="Tryumfalny motyw odzyskania godności i spłaty długu",
                channels_count=4,
                memory_label="music_gameover_success_data",
                memory_address="$B4D3–$B668 (406 B)",
                patterns_count=len(sj.get("patterns", {})),
                details={}
            ))

        # 5. Travel
        travel_json = audio_dir / "dziki-zgon-travel.json"
        if travel_json.exists():
            with open(travel_json, "r", encoding="utf-8") as f:
                tj = json.load(f)
            meta = tj.get("metadata", {})
            tracks.append(MusicTrackData(
                id="travel",
                title=meta.get("title", "Witcher's Bumbling Journey"),
                author=meta.get("author", "AI Composer"),
                format="atari-music-composition v1",
                source_file="audio/dziki-zgon-travel.json",
                key=meta.get("key"),
                mode=meta.get("mode"),
                bpm=meta.get("bpm"),
                duration_seconds=meta.get("duration_seconds"),
                description="Wesoły, awanturniczy motyw drogi pomiędzy regionami",
                channels_count=4,
                memory_label="music_travel_data",
                memory_address="$B669–$B8E5 (637 B)",
                patterns_count=len(tj.get("patterns", {})),
                details={}
            ))

        driver = AudioDriverData(
            name="Atari POKEY 4-Channel Relocatable Player",
            source_file="audio/player.asm",
            memory_base="$A800–$AB6F",
            size_bytes=880,
            update_rate_hz=50,
            channels=4,
            description="Lekki odtwarzacz muzyki POKEY sterowany przerwaniem VBLANK NMI z mikserem efektów dźwiękowych SFX"
        )

        return MusicPortalData(
            tracks_count=len(tracks),
            tracks=tracks,
            driver=driver
        )

    def generate_memory_data(self) -> MemoryPortalData:
        xex_path, provenance = resolve_game_binary(
            self.root_dir,
            binary_path=self.binary_path,
            binary_source=self.binary_source,
            release_tag=self.release_tag,
            fetch_if_missing=self.fetch_if_missing,
        )
        xex_info = parse_xex_binary(xex_path) if xex_path else None

        # Parse zeropage directly from zeropage.asm (SSOT)
        zp_asm_entries = parse_zeropage_asm(self.root_dir / "zeropage.asm")
        mem_info = parse_memory_usage_md(self.root_dir / "MEMORY_USAGE.md")

        zp_data = [ZeroPageEntry(**z) for z in (zp_asm_entries or mem_info["zero_page"])]

        # Filter out obsolete duplicate table rows from MEMORY_USAGE.md
        raw_segments = [
            s for s in mem_info["segments"]
            if not (s["start_hex"] == "$6800" and s["end_hex"] == "$89A7" and "WOLNY RAM" in s["area_type"])
        ]
        segments_data = [MemorySegmentData(**s) for s in raw_segments]

        # Calculate exact non-overlapping allocated union
        # Include all code, data, VRAM arena ($4000-$5FFF), PMG ($A000-$A7FF), and OS low RAM ($0000-$05FF)
        allocated_intervals = [[0x0000, 0x05FF]]
        for s in segments_data:
            if "WOLNY RAM" in s.area_type or s.area_type == "Zero Page":
                continue
            # Skip load-time transient INITAD segment ($2000-$2007)
            if s.start_hex == "$2000" and s.end_hex == "$2007":
                continue
            allocated_intervals.append([s.start_dec, s.end_dec])

        # Merge intervals to prevent double-counting
        merged_intervals = []
        for start, end in sorted(allocated_intervals, key=lambda x: x[0]):
            if not merged_intervals:
                merged_intervals.append([start, end])
            else:
                prev_start, prev_end = merged_intervals[-1]
                if start <= prev_end + 1:
                    merged_intervals[-1][1] = max(prev_end, end)
                else:
                    merged_intervals.append([start, end])

        # Total mapped non-overlapping bytes in usable $0000-$BFFF (49,152 bytes)
        total_mapped = sum(end - start + 1 for start, end in merged_intervals)
        free_headroom = max(0, 0xC000 - total_mapped)

        # Calculate exact non-overlapping free regions (gaps) in usable $0000-$BFFF
        free_data: List[FreeRegion] = []
        gap_configs = {
            0x1E2D: {
                "desc": "Bufor wyrównania bajtowego w niskiej pamięci RAM (zarezerwowany)",
                "status": "reserved_alignment",
                "safe": False,
            },
            0x1F8C: {
                "desc": "Bufor niskiej pamięci RAM przed wejściem kodu programu ($2000, zarezerwowany dla procedur startowych)",
                "status": "reserved_alignment",
                "safe": False,
            },
            0x3FE8: {
                "desc": "Bufor wyrównania strony przed areną VRAM ($4000) chroniący Display Listy (zarezerwowany)",
                "status": "reserved_alignment",
                "safe": False,
            },
            0x5FEC: {
                "desc": "Bufor wyrównania strony przed zestawem znaków ($6000, zarezerwowany)",
                "status": "reserved_alignment",
                "safe": False,
            },
            0x9DC5: {
                "desc": "Czysty wolny bufor RAM w bloku danych i logiki gry przed pamięcią PMG ($A000) — bezpieczny dla danych świata/tekstów",
                "status": "safe_usable",
                "safe": True,
            },
            0xB992: {
                "desc": "Wewnętrzny bufor wyrównania kodu pomiędzy sterownikiem audio a procedurami GameOver (zarezerwowany)",
                "status": "reserved_alignment",
                "safe": False,
            },
            0xBCA9: {
                "desc": "Czysty wolny bufor RAM pod wyłączonym ROM-em BASIC za duszkami postaci do granicy OS ROM ($C000) — bezpieczny dla kodu/audio/grafiki",
                "status": "safe_usable",
                "safe": True,
            },
        }

        for i in range(len(merged_intervals) - 1):
            g_start = merged_intervals[i][1] + 1
            g_end = merged_intervals[i + 1][0] - 1
            if g_end >= g_start:
                sz = g_end - g_start + 1
                s_hex = f"${g_start:04X}"
                e_hex = f"${g_end:04X}"
                addr_range = f"{s_hex}–{e_hex}" if g_start != g_end else f"{s_hex}"
                cfg = gap_configs.get(g_start, {
                    "desc": f"Bufor pamięci RAM ({sz} B)",
                    "status": "safe_usable" if sz >= 32 else "reserved_alignment",
                    "safe": sz >= 32,
                })
                free_data.append(FreeRegion(
                    address_range=addr_range,
                    start_hex=s_hex,
                    end_hex=e_hex,
                    size_bytes=sz,
                    status=cfg["status"],
                    is_safe_for_allocation=cfg["safe"],
                    description=cfg["desc"]
                ))

        if merged_intervals and merged_intervals[-1][1] < 0xBFFF:
            g_start = merged_intervals[-1][1] + 1
            g_end = 0xBFFF
            sz = g_end - g_start + 1
            s_hex = f"${g_start:04X}"
            e_hex = f"${g_end:04X}"
            cfg = gap_configs.get(g_start, {
                "desc": "Czysty wolny bufor RAM pod wyłączonym ROM-em BASIC do granicy OS ROM ($C000)",
                "status": "safe_usable" if sz >= 32 else "reserved_alignment",
                "safe": sz >= 32,
            })
            free_data.append(FreeRegion(
                address_range=f"{s_hex}–{e_hex}",
                start_hex=s_hex,
                end_hex=e_hex,
                size_bytes=sz,
                status=cfg["status"],
                is_safe_for_allocation=cfg["safe"],
                description=cfg["desc"]
            ))

        safe_headroom = sum(fr.size_bytes for fr in free_data if fr.is_safe_for_allocation)
        reserved_headroom = sum(fr.size_bytes for fr in free_data if not fr.is_safe_for_allocation)
        bin_model = BinaryInfoData(**xex_info) if xex_info else None

        return MemoryPortalData(
            total_ram_bytes=65536,
            usable_ram_limit="$BFFF (49,152 B)",
            os_rom_boundary="$C000",
            hardware_regs_boundary="$D000 - $DFFF",
            basic_disabled=True,
            os_rom_enabled=True,
            total_mapped_bytes=total_mapped,
            free_headroom_bytes=free_headroom,
            safe_free_headroom_bytes=safe_headroom,
            reserved_headroom_bytes=reserved_headroom,
            binary_provenance=provenance,
            segments=segments_data,
            zero_page=zp_data,
            free_regions=free_data,
            binary=bin_model
        )

    def generate_releases_data(self) -> ReleasesPortalData:
        history_entries = parse_history_md(self.root_dir / "HISTORY.md")

        # Get git tags
        git_tags_out = get_git_output(["git", "tag", "-l", "--sort=-creatordate", "--format=%(refname:short)|%(creatordate:short)|%(subject)"])
        tag_lines = [l.strip() for l in git_tags_out.splitlines() if l.strip()]

        releases_list: List[ReleaseItemData] = []

        if tag_lines:
            for line in tag_lines:
                parts = line.split("|")
                tag = parts[0]
                date = parts[1] if len(parts) > 1 else "2026-11-03"
                subject = parts[2] if len(parts) > 2 else ""

                ver = tag.lstrip("v")
                matching_history = [h for h in history_entries if h["date"] == date]
                notes = []
                if matching_history:
                    notes = matching_history[0]["bullets"]
                elif subject:
                    notes = [subject]

                releases_list.append(ReleaseItemData(
                    tag=tag,
                    version=ver,
                    date=date,
                    title=f"Dziki Zgon {tag}",
                    notes=notes,
                    artifacts=[{
                        "name": "dziki_zgon.xex",
                        "type": "Atari 8-bit executable",
                        "description": "Standardowy plik wykonywalny Atari DOS 2 (XEX)"
                    }]
                ))
        else:
            # Fallback if git is not accessible
            for h in history_entries[:8]:
                releases_list.append(ReleaseItemData(
                    tag=f"v0.5.0",
                    version="0.5.0",
                    date=h["date"],
                    title=h["title"],
                    notes=h["bullets"],
                    artifacts=[{
                        "name": "dziki_zgon.xex",
                        "type": "Atari 8-bit executable"
                    }]
                ))

        timeline_list = [
            TimelineItemData(date=h["date"], title=h["title"], bullets=h["bullets"])
            for h in history_entries
        ]

        return ReleasesPortalData(
            releases_count=len(releases_list),
            releases=releases_list,
            timeline=timeline_list
        )

    def generate_latest_data(self, releases_data: ReleasesPortalData, memory_data: MemoryPortalData) -> LatestPortalData:
        latest_rel = releases_data.releases[0] if releases_data.releases else None
        tag = latest_rel.tag if latest_rel else "v0.5.0"
        ver = latest_rel.version if latest_rel else "0.5.0"
        date = latest_rel.date if latest_rel else "2026-11-03"
        highlights = latest_rel.notes if latest_rel else []

        bin_size = memory_data.binary.size_bytes if memory_data.binary else None
        sha256 = memory_data.binary.sha256 if memory_data.binary else None

        return LatestPortalData(
            version=ver,
            tag=tag,
            release_date=date,
            binary_name="dziki_zgon.xex",
            binary_size_bytes=bin_size,
            sha256=sha256,
            download_url=f"https://github.com/grzes71/dziki-zgon/releases/download/{tag}/dziki_zgon.xex",
            repository="https://github.com/grzes71/dziki-zgon",
            requirements="Atari 800 XL / 65 XE, 64 KB RAM, Joystick w porcie 1, telewizor / monitor PAL lub NTSC",
            highlights=highlights[:5]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Dziki Zgon portal data to JSON")
    parser.add_argument("--root-dir", type=Path, default=Path("."), help="Project root directory")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/portal"), help="Destination directory for reports")
    parser.add_argument("--binary-path", type=Path, default=None, help="Path to dziki_zgon.xex executable")
    parser.add_argument("--binary-source", choices=["local_build", "release_asset", "none"], default="local_build", help="Provenance origin of binary")
    parser.add_argument("--release-tag", type=str, default=None, help="Tag name if analyzing a release binary")
    parser.add_argument("--fetch-release-if-missing", action="store_true", help="Allow downloading release binary if missing")
    args = parser.parse_args()

    pipeline = PortalDataPipeline(
        root_dir=args.root_dir,
        output_dir=args.out_dir,
        binary_path=args.binary_path,
        binary_source=args.binary_source,
        release_tag=args.release_tag,
        fetch_if_missing=args.fetch_release_if_missing,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
