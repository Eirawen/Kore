# Kore Codex — Animation Director's Working Memory

This is the agent working memory for the **Kore** rigging and animation pipeline. Read this file first to find relevant documentation.

## Pipeline Reference

| File | Purpose |
|------|---------|
| [gotchas.md](gotchas.md) | **Read first.** Non-obvious pitfalls. Every item cost hours. |
| [animation-methodology.md](animation-methodology.md) | **How I animate.** Process, tools, the Rachmaniclaude recipe. Not human process — mine. |
| [creatures/cave-spider.md](creatures/cave-spider.md) | Cave spider creature card: rig, posture, motion, feel, gotchas |
| [rig-compiler.md](rig-compiler.md) | The adjective compiler for rigging (semantic LLM layer — prototype) |

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
