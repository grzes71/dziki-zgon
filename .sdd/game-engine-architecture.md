# Task

Refactor the Atari game engine to use a deterministic frame-based architecture driven by the Atari PAL VBLANK interrupt.

This is an architectural refactoring.

The goal is to build a modular game engine where all gameplay logic is executed exactly once per video frame.

The engine targets:

- Atari 8-bit
- PAL
- MADS Assembler

---

# Design Philosophy

The engine shall be based on the following principles:

- Single Responsibility Principle
- Modular design
- Deterministic execution
- One game update per video frame
- Separation of gameplay and rendering
- Future extensibility

---

# Overall Architecture

The engine shall follow this pipeline:

```
                    Atari Hardware
                           │
                    VBLANK Interrupt
                           │
                           ▼
                  Engine_FrameHandler
                 (Hardware, Audio, Flag)
                           │
                     (Sets Flag)
                           │
                           ▼
                       Main Loop
                           │
                           ▼
                   EngineScheduler
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Engine_BeginFrame      Fixed Update     Engine_EndFrame
                              │
                              ▼
                      Input_Update
                              │
                              ▼
                     Player_Update
                              │
                              ▼
                       NPC_Update
                              │
                              ▼
                  Collision_Update
                              │
                              ▼
                  Inventory_Update
                              │
                              ▼
                   Dialogue_Update
                              │
                              ▼
                     Quest_Update
                              │
                              ▼
                  Animation_Update
                              │
                              ▼
                    World_Update
                              │
                              ▼
                  Render_Prepare
```

---

# Main Loop

The main loop shall act as the primary dispatcher for gameplay logic, synchronized by the VBLANK interrupt.

It shall wait for the VBLANK flag and then execute the EngineScheduler. This allows game logic to be interrupted by DLIs (Display List Interrupts) without issue.

Example:

```asm
Main

    jsr Engine_Init

Loop

    jsr Engine_WaitFrame ; Waits for FrameCounter to change
    jsr EngineScheduler  ; Executes all game logic

    jmp Loop
```

---

# VBLANK

Install a custom VBLANK handler (NMI).

The handler SHALL execute as quickly as possible and must NOT contain any gameplay logic. It is responsible for critical hardware updates, audio timing, and signaling the main loop.

Example:

```asm
Engine_FrameHandler

    jsr Audio_Update     ; Must be perfectly timed
    ; ... apply shadow registers for graphics ...
    inc FrameCounter     ; Signal main loop

    rti
```

Gameplay logic must run in the main loop to avoid blocking other NMIs like DLIs.

---

# Engine Scheduler

Create a dedicated module:

```
engine_scheduler.asm
```

The scheduler SHALL execute the following pipeline:

```asm
EngineScheduler

    jsr Engine_BeginFrame

    jsr Input_Update

    jsr Player_Update

    jsr NPC_Update

    jsr Collision_Update

    jsr Inventory_Update

    jsr Dialogue_Update

    jsr Quest_Update

    jsr Animation_Update

    jsr World_Update

    jsr Render_Prepare

    jsr Engine_EndFrame

    rts
```

This execution order is mandatory.

---

# Engine_BeginFrame()

Responsible for:

- Increment global frame counter
- Update global timers
- Prepare frame state
- (Future) Start profiler

No gameplay.

---

# Input_Update()

Responsible for:

- Read joystick
- Read keyboard
- Store input state

Hardware must be read only once per frame.

Other systems must use the cached input state.

---

# Player_Update()

Responsible for:

- Movement intent (setting target position/velocity)
- Direction
- Start animations
- Screen transition requests

No collision detection. Calculates intention, but final position is decided by Collision_Update.

---

# NPC_Update()

Responsible for:

- NPC movement intent
- AI
- Enemy behaviour
- Friendly NPCs

---

# Collision_Update()

Responsible for:

- Verifying Player/world collision (resolving intent to final position)
- Verifying NPC/world collision (resolving intent to final position)
- Trigger activation
- Object collision

Executed exactly once per frame.

---

# Inventory_Update()

Responsible for:

- Item usage
- Item pickup
- Item removal

---

# Dialogue_Update()

Responsible for future dialogue system.

May initially be empty.

---

# Quest_Update()

Responsible for:

- Quest progress
- Quest completion
- Trigger evaluation

May initially be empty.

---

# Animation_Update()

Responsible only for animation state.

Example:

```
FrameCounter++

if counter == duration

    NextFrame()
```

Animation timing shall always be frame-based.

Never time-based.

---

# World_Update()

Responsible for:

- Screen transitions
- Loading neighbouring screens
- World events

---

# Audio_Update()

Responsible for:

- Music (e.g. RMT player)
- Sound effects

Must be called directly from the VBLANK handler to ensure perfect 50Hz timing and avoid audio jitter.

---

# Render_Prepare()

Responsible for preparing rendering data only.

Allowed:

- Update PMG positions
- Update animation frame indices
- Prepare screen buffers

Forbidden:

- Gameplay
- AI
- Collision

ANTIC performs the rendering automatically.

---

# Engine_EndFrame()

Responsible for:

- Finish frame
- (Future) Performance statistics
- (Future) Overflow detection
- (Future) Debug hooks

Initially may be empty.

---

# Display List Interrupts (DLI)

DLI shall contain ONLY display operations.

Allowed:

- Color changes
- CHBASE changes
- PMG register changes
- Status bar colors
- Split-screen effects

Forbidden:

- AI
- Movement
- Collision
- Quest logic
- Inventory
- Dialogue

Every DLI should execute in as few CPU cycles as possible.

---

# Timing

The engine assumes:

PAL Atari

50 Hz

One EngineScheduler execution equals one frame.

Every time-dependent system shall use frame counters.

Example:

```
Walk animation

Frame duration = 4

Animation changes every four GameTicks.
```

---

# Code Organization

Suggested directory structure:

```
engine/

    engine.asm

    engine_scheduler.asm

    engine_frame.asm

    engine_begin.asm

    engine_end.asm

    input.asm

    player.asm

    npc.asm

    collision.asm

    inventory.asm

    dialogue.asm

    quest.asm

    animation.asm

    world.asm

    audio.asm

    render.asm

    vblank.asm

    dli.asm
```

Each module shall have one responsibility.

---

# Future Compatibility

The architecture must allow easy addition of:

- Save Game
- NPC system
- Dialogue system
- Particle system
- Weather
- Cut-scenes
- Scripting engine

No redesign of EngineScheduler should be required.

---

# Memory & Zero Page Management

The engine shall define strict rules for Zero Page (ZP) usage:

- **Global State**: ZP addresses reserved for engine state (e.g., FrameCounter, random seed) are globally accessible.
- **Scratchpad**: A designated block of ZP addresses (e.g., 8-16 bytes) shall be reserved as temporary "scratchpad" registers. Modules can safely use them during their `Update` execution, but must not expect the data to persist across different module updates.
- **Private State**: Variables that need to persist across frames for a specific module should ideally avoid ZP unless performance-critical, in which case they must be uniquely allocated.

---

# Documentation

Update the engine documentation.

Include:

- Engine lifecycle
- Scheduler pipeline
- VBLANK responsibilities
- DLI responsibilities
- Module overview

Generate an architecture diagram.

---

# Acceptance Criteria

The refactoring is complete only if:

✓ Main loop executes EngineScheduler exactly once per frame, synchronized by VBLANK.

✓ VBLANK executes Audio_Update and critical hardware updates only.

✓ EngineScheduler implements the complete update pipeline.

✓ Every subsystem is isolated.

✓ Input is sampled once per frame.

✓ Collision is executed once per frame.

✓ Animation is frame-based.

✓ DLI performs display operations only.

✓ Documentation is updated.

✓ Existing gameplay behaviour remains unchanged.

✓ The architecture is ready for future engine extensions.