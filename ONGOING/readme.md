# Active Threads — Kore

Last updated: 2026-06-26

## Primary Mission: Text-Native Rigging and Animation Pipeline for Crescent

### Current State: MEDIAL AXIS PIPELINE PROVEN

The auto-rigging pipeline works end-to-end:
1. ✅ Voxelize mesh (handles triangle soup from Meshy)
2. ✅ 3D skeletonize (medial axis extraction via scikit-image)
3. ✅ Branch tracing (found all 6 legs, 2 pedipalps, 2 fangs, 1 abdomen)
4. ✅ Joint detection via curvature analysis (needs refinement)
5. ✅ Proximity-based vertex weights (mesh deforms! bypasses Blender auto-weight failure)
6. ⚠️ Three quality issues remain (subagent working on fixes)

### Issues Being Fixed (subagent dispatched)

1. **Weight falloff too broad** — ankle bones deform the mouth. Need sharper falloff (1/d⁴ instead of 1/d) and distance cutoff.
2. **Spurious joints** — curvature detection creates tiny stub bones at leg endpoints. Need minimum segment length filtering.
3. **Branch misclassification** — pedipalp classified as abdomen because it was longer. Need spatial classification (most positive Y = rear = abdomen).

### Key Discovery: Medial Axis Matches Hand-Clicked Landmarks

The computationally-derived centerlines matched Khaled's manually-clicked joint positions within 1-4cm. This validates the entire approach — mesh geometry IMPLIES its own skeleton. No landmarks needed.

### Files

- Spider mesh: ~/Kore/spider.glb
- Skeleton extraction: ~/Kore/tools/skeleton_extract.py
- Auto-rig pipeline: ~/Kore/tools/auto_rig.py
- Generated Blender script: ~/Kore/tools/rig_spider_auto.py
- Landmark-based rig (superseded): ~/Kore/tools/rig_spider.py
- Orientation detection: ~/Kore/tools/analyze_spider_v4.py
- Spider skeleton points: ~/Kore/spider_skeleton_points.npy

### Next Steps (when resuming)

1. Review subagent fixes to auto_rig.py
2. Test updated rig in Blender
3. If deformation quality is good: animate! (hexapod gait)
4. If not: iterate on weight computation and joint detection
5. Eventually: build the Crescent CLI tool (`crescent rig model.glb`)

### Architecture Decisions

- Voxelize + skeletonize is the general approach (works on ANY mesh)
- Proximity weights bypass Blender's manifold requirement
- Blender is used as the rigging runtime (via Python scripts), not as an interactive tool
- Future: could replace Blender with pure Python glTF writing (pygltflib)

### Not Started

- Procedural animation (IK-based locomotion)
- Slime deformation system (squash-stretch, no skeleton)
- Integration with Crescent's animation system
- Crescent CLI rig command
- Landmark clicking tool (Three.js viewer)
