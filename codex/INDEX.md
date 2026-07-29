# Kore Codex — Animation Director's Working Memory

This is the agent working memory for the **Kore** rigging and animation pipeline. Read this file first to find relevant documentation.

## The Game (read to understand WHAT we're building)

| File | Purpose |
|------|---------|
| [slayer2-design-bible.md](slayer2-design-bible.md) | **The north star.** Blue-collar-fantasy tone, "geometry is cheap / atmosphere is everything," the philosophy of magic (cast = element argued through the body; strange scrappy magic; why Skyrim destruction is boring), combat feel, asset rule (Meshy for identity, marketplace for infrastructure). |
| [casting-animation-design.md](casting-animation-design.md) | **The Wizard Wars spec.** The four elemental casts in full (air/water/fire/earth), the unifying grammar, and every melee/throwable including the forte-against-foible sword parry. |

## Core Documentation

| File | Purpose |
|------|---------|
| [gotchas.md](gotchas.md) | **Read first.** Non-obvious pitfalls. Every item cost hours. 25 entries (18–25 = hand animation). |
| [architecture.md](architecture.md) | **Complete pipeline reference.** Every stage from voxelization to render loop. Bug hall of fame. Dependencies. File map. |
| [animation-methodology.md](animation-methodology.md) | **How I animate.** Process, tools, the Rachmaniclaude recipe. Not human process — mine. |
| [first-person-hand-animation.md](first-person-hand-animation.md) | **How FP hands are keyframed.** Using a bought rig: no-elbow object-transform technique, the forearm-stub origin gotcha, orientation cheat sheet, supination/pronation bridging, the gather→HOLD→snap rhythm, retiming for contrast, the render/grid/mp4 workflow. |
| [decisions.md](decisions.md) | **Why we chose what we chose.** 12 architectural decisions with alternatives considered. Reverse-chronological. |

## Creature & Asset Cards

| File | Purpose |
|------|---------|
| [creatures/cave-spider.md](creatures/cave-spider.md) | Cave spider for Slayer 2: rig stats, posture params (murder spider vs docile variant), motion philosophy (rowing not pumping), feel notes, model-specific gotchas, reference links |

## VFX

| File | Purpose |
|------|---------|
| [vfx-methodology.md](vfx-methodology.md) | **Spell VFX.** The bridge principle, five-layer recipe, capture pipeline. |

## Prototypes

| File | Purpose |
|------|---------|
| [rig-compiler.md](rig-compiler.md) | The adjective compiler for rigging (semantic LLM layer — concept only) |

## Tools

| File | Purpose |
|------|---------|
| `tools/auto_rig.py` | Main pipeline: mesh → Blender rig script. Multi-res medial axis + two-layer weights. |
| `tools/rig_spider_auto.py` | Generated output: the Blender Python script that creates the rig |
| `tools/animate_walk.py` | Walk cycle v7: alternating tripod, bone-local axes |
| `tools/animate_feel.py` | Pedipalp sensing animation |
| `tools/animate_threat.py` | Threat display v2: anticipation, overlapping action, snap settle |
| `tools/rig_compiler.py` | Architecture prototype: geometry → description → LLM → rig spec |
| `tools/skeleton_extract.py` | Standalone medial axis skeleton extraction |
| `tools/analyze_spider_v4.py` | Mesh orientation detection (front/back identification) |

## Hand Rig & Animation Tools

| File | Purpose |
|------|---------|
| `tools/rig_hands_simple.py` | Rig a bare hand mesh: medial-axis ENDPOINTS only (not traces) → straight palm→tip bones → anatomical subdivision → palm-priority two-layer weights. For hands our trace pipeline can't handle. |
| `tools/render_hands_fp.py` | First-person staging of the cgtrader two-hand asset: strip junk, mirror left hand, matte, FP camera, apply a named finger pose. The settled staging values live here. |
| `tools/animate_casts.py` | The four elemental cast animations (air/water/fire/earth). Object-transform + pose-bone keyframes, supination bridging, retiming. `-- <name>` / `--test` / `--full`. |
| `tools/montage_casts.py` | PIL montage of the 12 sampled frames → labeled review grid per cast. |
| `slayer_hands_clean.glb` | The cleaned, rigged, decimated, bare-material deliverable hand (their rig; bones renamed). Drop into WeaponViewport. |

## Autonomous Loop

| File | Purpose |
|------|---------|
| `tools/loop/iterate.sh` | One-command render cycle: Blender → ffmpeg → grid |
| `tools/loop/render_pipeline.py` | Headless Blender: import → rig → animate → render |
| `tools/loop/diagnose_feet.py` | Diagnostic: tests bone hierarchy and weight assignments |
| `tools/loop/FEET_FIX.md` | Writeup of the bone-local axis bug |

## Usage

```bash
# Iterate on an animation
bash tools/loop/iterate.sh walk 480x360 side
bash tools/loop/iterate.sh threat 480x360 3/4

# Regenerate the rig (after editing auto_rig.py)
python tools/auto_rig.py

# Read the grids
# /tmp/kore_output/grids/grid_*.jpg
```

## Architecture Summary

```
Mesh (.glb)
  ↓ voxelize (trimesh, multi-resolution)
  ↓ skeletonize (scikit-image, 3D thinning)
  ↓ branch tracing + classification
  ↓ joint detection (curvature analysis)
  ↓ center refinement (surface averaging)
  ↓ bone placement (transform_apply + reversed chain)
  ↓ two-layer weights (branch segmentation + rigid plates)
  ↓ animation (bone-local quaternion rotations)
  ↓ autonomous render (headless Blender + ffmpeg + grid)
Rigged, Animated Model
```

## Humanoid animation (the succubus arc, 2026-07-25)
- **[humanoid-animation.md](humanoid-animation.md)** — START HERE for any
  biped. The rig, the five laws, smoothness, physics, wings, fingerless
  hands, workflow economics, and recipes for what to animate next.
- [component-track-animation.md](component-track-animation.md) — the
  authoring method: every body part on its own clock, backwards-inducted
  from the end state.
- [wing-emotion.md](wing-emotion.md) — her wings are a second face; the
  8-pose emotional library with measured signatures.
- [the-real-game.md](the-real-game.md) — the theme, and why she's
  flightless on purpose.

## Creatures — the water elemental (Azure Tide Spirit)
- **[water-elemental.md](water-elemental.md)** — the full build, 7 chapters:
  reading a mesh before rigging it, geodesic limb tracing, the VORTEX DRIVER
  (one `uWater` float compiles her whole presence), the VFX layer (skin,
  particles, mist shell), and the MOVESET with the four laws it produced.
- Materials live in crescent: `water_elemental.js` (skin),
  `water_mist_shell.js` (aura), `WaterSheddingVFX.js` (droplets + scoop).

## The laws that generalise beyond one creature
- **gotcha 55** — an idle must be true at EVERY frame, never a transformation
- **gotcha 56** — accumulating rotation shears a mesh; use a travelling wave
- **gotcha 57** — weight diffusion beats nearest-bone assignment
- **gotcha 58** — `bpy.data.actions.new()` does NOT overwrite (fake users pile up)
- **gotcha 59** — a humanoid cannot ROTATE into a non-humanoid
- **gotcha 60** — for a liquid creature, the base is NOT a stand
- **PORT THE CONSTANTS.** Re-deriving a proven driver's numbers from bounds
  bites you away from the operating point you tuned at — which is exactly
  where you are not looking. Made this bug TWICE in one day
  (water-elemental.md §6b).
- **When a pose reads as the wrong ACTION, the fix is PROPORTION, not
  angle.** Bone rotation cannot make a body stop meaning "body".

## Elementals — one mesh, many creatures
- **[elemental-presets.md](elemental-presets.md)** — the element is a PRESET,
  not a model. The BODY-vs-FIELD axis, why earth is unreachable (presets
  change material, never silhouette), air vs dust one dial apart, per-element
  mist grading, and the six INK palettes.
- [water-elemental.md](water-elemental.md) §8 — READABILITY: it is hierarchy,
  not less; the three tools (core glow / body rim / strand tint); self-lit
  colour; the blood; the artist's height-grading note; the beauty rig.

## More laws worth carrying
- **gotcha 61** — shader colour constants are LINEAR; hex on the CPU is sRGB
- **gotcha 62** — additive shells saturate; density is not the knob
- **gotcha 63** — colour uniforms must be `.set()`, never overwritten
- **gotcha 64** — a GLSL validator must be stage-aware, and you should just
  COMPILE it; the GPU is the only honest validator
- **gotcha 65** — hardcoded constants hide until something monochrome stands
  next to them
- **KEEP THE ACCIDENTS.** Twice in one day a broken render beat the
  deliberate thing meant to replace it (air, ink_bluewash). Save the bug as a
  preset BEFORE you fix the bug.
- **Evaluate against the START, not the previous step.** An arc drifts with no
  single decision being wrong if you only ever compare N to N-1.

## First-person hands — the INSPECTION side (2026-07-29)
- [first-person-hand-animation.md](first-person-hand-animation.md) now has a
  second half: how to view the SHIPPED rig as the PLAYER sees it.
  - **The FP camera is not in the engine defaults** — slayer2 overrides them
    (`fov 54`, `offset [0,-0.22,-0.45]`), which puts the blender eye at
    `(0,-0.45,0.22)` looking +Y. That offset IS the forearm-dominance
    complaint; check it before re-rigging anything.
  - **Never derive the camera from the blend** — the exporter rebases the
    armatures. Import the shipped glb.
  - **Slotted actions**: bind each object to its OWN slot or both arms stack.
  - **Seats are raw glTF space**; the bone-tail frame is an OPEN GAP, so the
    weapon ships hidden in the sandbox.
  - **Measure the framing** (`read_fp_pose.py` screen footprint), do not
    eyeball it.
