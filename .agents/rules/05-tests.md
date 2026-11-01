---
trigger: always_on
---

# Domain: Test Design & Asset Agnosticism

## 1. No Hardcoded Asset Counts or Dynamic Resource Metrics
- **Dynamic Assets:** Never hardcode expectations or counts for resources and assets that evolve during game development (e.g., assets defined in `manifest.yaml`, `manifest.json`, `scenes/*.json`, `definitions.json`, such as number of objects, enemies, platforms, secrets, or element counts).
- **Source of Truth:** Derive expected metrics dynamically from the raw asset/source files (e.g., parsing the JSON/YAML source definition directly in the test setup or fixture) rather than asserting against hardcoded integer constants (e.g., avoid `assert len(scene.objects) == 8` or `assert sec_count == 4`).
- **Behavioral Assertions:** Focus integration tests and py65 emulation harnesses on verifying engine logic, mechanics, state transitions, algorithms, and invariant contracts rather than brittle content snapshots.
- **Resource Independence:** When a specific count or structure is strictly required for a unit test, prefer synthesized in-memory mock models or dedicated static test fixtures over mutating or binding tests tightly to live production game assets.
