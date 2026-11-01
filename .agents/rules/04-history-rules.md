---
trigger: always_on
---

## Definition of Done (CRITICAL)
- **History Tracking:** Whenever you successfully implement a feature, fix a bug, or complete a significant refactor, you MUST automatically update the `HISTORY.md` file.
- **Placement:** Prepend your new entry exactly below the HTML comment `<!-- AGENT INSTRUCTIONS... -->`. Do not put it at the bottom of the file. Insert new entries, never replace the existing first heading.
- **Format:** Use the format `## [YYYY-MM-DD] - [Brief Title]`. Underneath, provide a concise bulleted list of the actual technical changes made (e.g., functions added, files modified, registers altered).
- **Paths in History:** When referencing files in `HISTORY.md`, ALWAYS use relative paths (relative to project root, e.g., `scenes/game.asm` or `[scenes/game.asm](scenes/game.asm)`). NEVER use absolute paths or `file:///` URIs.
- **Trigger:** Perform this update automatically as the final step before telling the user the task is complete.