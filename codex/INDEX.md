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
