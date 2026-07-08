# Task

Refactor the engine to use the **Mailbox Pattern** (Global Request Flags) for inter-module communication instead of a universal Event Queue.

This is an architectural improvement designed for maximum 6502 efficiency.

The objective is to decouple engine systems and remove direct dependencies between modules without the overhead of iterating through arrays of events.

---

# Design Philosophy

The engine shall rely on simple Zero Page (or general RAM) flags, acting as "mailboxes" where a sender can leave a specific request (e.g., "Play Sound", "Load Map"), and the receiver checks that mailbox during its update cycle.

Advantages on 6502:
- 0 bytes overhead for queue metadata.
- Instant push (`sta Request_Dialog_Start`).
- Instant pop/check (`lda Request_Dialog_Start`, `beq`).
- No missed events due to multiple consumers.

---

# Architecture

Instead of a complex `engine/events.asm`, communication relies on globally defined flags in `zeropage.asm` or a dedicated `engine/requests.inc`.

## Examples of Mailboxes:

```asm
; in zeropage.asm or engine variables
Request_Audio_Play         dta $00
Request_Dialogue_Start     dta $00
Request_Map_Load           dta $00
```

---

# Producers

Modules that generate events simply set the flag (and optionally argument variables).

```asm
Collision_Update:
    ; ... collision detected with NPC ...
    lda #NPC_ID_BLACKSMITH
    sta Request_Dialogue_Start
```

---

# Consumers

Modules responsible for handling requests check the flags during their execution in the `EngineScheduler`.

```asm
Dialogue_Update:
    lda Request_Dialogue_Start
    beq @no_dialog

    ; Start dialogue logic...
    ; Clear the flag so it doesn't trigger again
    lda #0
    sta Request_Dialogue_Start

@no_dialog:
```

---

# Acceptance Criteria

✓ Event Queue concept abandoned in favor of Mailbox pattern.

✓ Global request flags are used for inter-module communication.

✓ Direct subroutine calls across different domains (e.g. Collision calling Dialogue directly) are eliminated.

✓ Performance is strictly `O(1)` for sending and checking messages.
