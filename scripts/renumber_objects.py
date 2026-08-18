#!/usr/bin/env python3
"""
renumber_objects.py — Skrypt do przenumerowania kodów (code) obiektów w świecie gry.

ZASADA DZIAŁANIA:
1. Zlicza wystąpienia wszystkich obiektów na wszystkich ekranach we wszystkich regionach gry
   (z uwzględnieniem repeat-x i repeat-y).
2. Sortuje obiekty według częstotliwości użycia:
   - Najczęściej używane obiekty otrzymują najniższe kody (od code: 1 w górę).
   - Rzadziej używane obiekty otrzymują wyższe kody.
   - Obiekty w ogóle nieużywane w świecie gry trafiają na sam koniec (najwyższe kody).
3. Aktualizuje plik world/objects.yaml z zachowaniem formatowania i typów pól.
4. Generuje szczegółowy raport z przeprowadzonych zmian (stary code -> nowy code, liczba wystąpień).

PRZYPADKI UŻYCIA (USE CASES):
1. Podgląd (suchy przebieg / dry-run) bez modyfikacji plików:
   python scripts/renumber_objects.py

2. Zastosowanie zmian w pliku objects.yaml:
   python scripts/renumber_objects.py --apply
   (lub: python scripts/renumber_objects.py --fix)
"""

import sys
import argparse
from pathlib import Path
import yaml


class FlowList(list):
    """Custom list type to force flow style (inline array) in YAML dumps."""
    pass


def flow_list_rep(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)


yaml.add_representer(FlowList, flow_list_rep)


def count_object_usages(world_dir: Path, defined_objects: list[str]) -> tuple[dict[str, int], dict[str, set[str]]]:
    """Scans all region screens to count object instances."""
    counts = {oid: 0 for oid in defined_objects}
    locations = {oid: set() for oid in defined_objects}

    for region_dir in sorted(world_dir.iterdir()):
        if region_dir.is_dir() and (region_dir / "region.yaml").exists():
            screens_dir = region_dir / "screens"
            if screens_dir.exists() and screens_dir.is_dir():
                for screen_file in sorted(screens_dir.glob("*.yaml")):
                    screen_id = screen_file.stem
                    with open(screen_file, "r", encoding="utf-8") as sf:
                        screen_data = yaml.safe_load(sf) or {}

                    for obj_inst in screen_data.get("objects", []):
                        if not isinstance(obj_inst, dict):
                            continue
                        oid = obj_inst.get("object")
                        if not oid:
                            continue

                        rx = int(obj_inst.get("repeat-x", 1))
                        ry = int(obj_inst.get("repeat-y", 1))
                        cnt = rx * ry

                        if oid in counts:
                            counts[oid] += cnt
                            locations[oid].add(f"{region_dir.name}-{screen_id}")
                        else:
                            counts[oid] = counts.get(oid, 0) + cnt
                            if oid not in locations:
                                locations[oid] = set()
                            locations[oid].add(f"{region_dir.name}-{screen_id}")

    return counts, locations


def renumber_objects(world_dir: Path, apply_changes: bool = False) -> dict:
    """Renumbers objects by descending usage count and saves to objects.yaml."""
    objects_file = world_dir / "objects.yaml"
    if not objects_file.exists():
        raise FileNotFoundError(f"Could not find objects.yaml at {objects_file}")

    with open(objects_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    available_tags = data.get("tags", [])
    raw_objects = data.get("objects", [])

    if not raw_objects:
        return {"total": 0, "changes": []}

    defined_ids = [obj.get("id") or obj.get("object") for obj in raw_objects if obj.get("id") or obj.get("object")]
    counts, locations = count_object_usages(world_dir, defined_ids)

    # Sort objects: descending count, then ascending ID for determinism
    sorted_objects = sorted(
        raw_objects,
        key=lambda obj: (-counts.get(obj.get("id") or obj.get("object", ""), 0), obj.get("id") or obj.get("object", ""))
    )

    changes = []
    out_objects = []

    for new_code, obj in enumerate(sorted_objects, start=1):
        obj_id = obj.get("id") or obj.get("object")
        old_code = obj.get("code")
        count = counts.get(obj_id, 0)

        changes.append({
            "id": obj_id,
            "old_code": old_code,
            "new_code": new_code,
            "count": count,
            "screens_count": len(locations.get(obj_id, set())),
        })

        size_data = obj.get("size", {})
        flags_data = obj.get("flags", {})
        tiles_data = obj.get("tiles", [])
        tags_data = obj.get("tags", [])

        obj_dict = {
            "object": obj_id,
            "id": obj_id,
            "code": new_code,
            "size": {
                "width": size_data.get("width", 1),
                "height": size_data.get("height", 1),
            },
            "flags": {
                "blocking": bool(flags_data.get("blocking", False)),
                "interactive": bool(flags_data.get("interactive", False)),
                "secret": bool(flags_data.get("secret", False)),
            },
            "tiles": FlowList(tiles_data),
        }
        if tags_data:
            obj_dict["tags"] = FlowList(tags_data)

        out_objects.append(obj_dict)

    if apply_changes:
        new_yaml_data = {}
        if available_tags:
            new_yaml_data["tags"] = FlowList(available_tags)
        new_yaml_data["objects"] = out_objects

        with open(objects_file, "w", encoding="utf-8") as f:
            yaml.dump(new_yaml_data, f, sort_keys=False, indent=2, allow_unicode=True)

    return {
        "total": len(out_objects),
        "used_count": sum(1 for c in changes if c["count"] > 0),
        "unused_count": sum(1 for c in changes if c["count"] == 0),
        "changes": changes,
        "applied": apply_changes,
    }


def print_report(result: dict):
    """Prints a clear summary report of the renumbering operation."""
    changes = result["changes"]
    total = result["total"]
    used = result["used_count"]
    unused = result["unused_count"]
    applied = result["applied"]

    status_str = "ZASTOSOWANO W PLIKU objects.yaml" if applied else "TRYB PODGLĄDU (DRY-RUN - bez zmian w pliku)"

    print("=" * 80)
    print(f" RAPORT PRZENUMEROWANIA OBIEKTÓW ({status_str})")
    print("=" * 80)
    print(f"Liczba wszystkich obiektów: {total}")
    print(f"  - Używane na planszach:   {used} (nowe kody 1 .. {used})")
    print(f"  - Nieużywane w grze:      {unused} (nowe kody {used + 1} .. {total})")
    print("-" * 80)
    print(f"{'NOWY':<6} {'STARY':<6} {'STATUS':<10} {'WYSTĄPIENIA':<13} {'ID OBIEKTU'}")
    print("-" * 80)

    for c in changes:
        code_status = "=" if c["old_code"] == c["new_code"] else f"-> {c['new_code']}"
        usage_status = f"{c['count']}x ({c['screens_count']} map)" if c["count"] > 0 else "0 (nieużywany)"
        print(f"{c['new_code']:<6} {c['old_code']:<6} {code_status:<10} {usage_status:<13} {c['id']}")

    print("=" * 80)
    if not applied:
        print("\nAby zapisać powyższe zmiany w objects.yaml, uruchom:")
        print("  python scripts/renumber_objects.py --apply\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Renumber object codes based on frequency of use in the game world.")
    parser.add_argument(
        "--apply", "--fix",
        action="store_true",
        help="Apply changes and rewrite world/objects.yaml (default: dry-run only)"
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent / "world"
    if not base_dir.exists():
        base_dir = Path("world")

    if not base_dir.exists():
        print("Error: Could not find 'world' directory. Run from project root.", file=sys.stderr)
        sys.exit(1)

    result = renumber_objects(base_dir, apply_changes=args.apply)
    print_report(result)


if __name__ == "__main__":
    main()
