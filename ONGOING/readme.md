# Active Threads — Kore

Last updated: 2026-06-28

## Primary Mission: Text-Native Rigging and Animation Pipeline

### STATUS: PIPELINE PROVEN ✓

The auto-rigging pipeline works end-to-end. A spider walks.

### What Works
1. ✅ Voxelize mesh (any topology, including triangle soup)
2. ✅ 3D skeletonize (medial axis, multi-resolution: coarse topology + fine precision)
3. ✅ Branch classification (legs, abdomen, pedipalps, fangs — spatial isolation heuristic)
4. ✅ Joint detection (curvature analysis with minimum segment filtering)
5. ✅ Center refinement (surface averaging to push bones to true geometric center)
6. ✅ Bone placement INSIDE mesh (transform_apply fix — bake mesh transforms first)
7. ✅ Reversed bone chain (body→foot, not foot→body)
8. ✅ Physics-based arthropod weights (rigid chitin plates + linear blend at joints)
9. ✅ Body priority (cephalothorax/abdomen vertices locked to body bones)
10. ✅ Three animations: walk cycle, pedipalp sensing, threat display

### What Needs Work
- **Rotation axes**: all animations use global X/Y/Z rotation. Need per-bone LOCAL axis computation so legs lift UP instead of splaying sideways.
- **Mesh quality**: 3k vertices works but limits deformation quality. Higher-res mesh would animate more smoothly.
- **Animation refinement**: apply Disney 12 principles (anticipation, follow-through, overlapping action, slow-in/out). Current animations are functional, not beautiful.
- **The rig compiler**: prototype exists (rig_compiler.py) but not integrated into the pipeline. Need LLM semantic layer between topology extraction and rig generation.

### Key Discovery: The Transform Bug
The bones were always computed correctly. The medial axis was always right. The offset that plagued us for hours was because the mesh had a 90° rotation as an OBJECT TRANSFORM, and the armature didn't. One line — `bpy.ops.object.transform_apply()` — fixed everything by baking the rotation into the vertices.

### Key Discovery: Reversed Bone Chain  
The medial axis traces from endpoints (feet) inward (body). Building bones in this order creates an inverted hierarchy where the foot is the parent. Reversing the joint array before bone creation fixes parent-child propagation.

### Key Discovery: Physics-Based Weights
Arthropod exoskeletons are rigid chitin plates connected by narrow flexible membranes. This gives BINARY weights (1.0 to local bone) on rigid segments and LINEAR BLEND only at joint membranes. Simpler AND more correct than proximity or heat diffusion heuristics.

### Files
- `tools/auto_rig.py` — the main pipeline (mesh → rigged Blender script)
- `tools/rig_spider_auto.py` — generated Blender script (output of auto_rig)
- `tools/animate_walk.py` — alternating tripod walk cycle
- `tools/animate_feel.py` — pedipalp sensing/probing animation
- `tools/animate_threat.py` — threat display (rear up, fangs spread, shimmy)
- `tools/rig_compiler.py` — architecture prototype (adjective compiler for rigging)
- `tools/skeleton_extract.py` — standalone skeleton extraction
- `tools/analyze_spider_v4.py` — orientation detection (front/back identification)
- `spider.glb` — the six-legged test spider
