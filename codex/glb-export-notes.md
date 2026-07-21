# GLB Export Notes — Blender 5.1 → glTF → three.js (FP hands spike, 2026-07-20)

De-risking spike run BEFORE the real animations were done, so the export
gremlins surfaced off the critical path. Canonical scene: `cgtrader_hand.blend`
(pre-wrist rig). Exporter: `tools/export_fp_hands.py`. Browser proof:
`tools/fp_hands_test.html` + `tools/fp_hands_shot.js` → `glb_spike_proof.jpg`.
Verified in three.js r170 (GLTFLoader + AnimationMixer, headless chromium).

## Verdict per landmine

### 1. Mirrored right hand (scale.x = −3.118) — WORKS AS-IS, with a lucky reason
The glTF exporter re-decomposes the armature node's (−3.118, 3.118, 3.118)
into **uniform negative scale (−3.118, −3.118, −3.118)** plus a compensating
rotation. Uniform scale cannot shear children, and three.js r170 renders the
negative-determinant skinned mesh correctly (winding + normals fine — the
staged bmesh normal flip from gotcha #22 must stay; the exported normals are
correct in the browser). **Caveat: this decomposition trick only exists
because our mirror scale is uniform-magnitude.** An anisotropic mirror like
(−3, 2, 2) could not be rescued this way.

Fallback proven too: `--bake-mirror` applies the mirror+scale into the
armature/mesh **data** (`arm.data.transform(S)`, `mesh.data.transform(S @ L)`,
re-flip normals), leaving the object scale at 1. Object loc/rot animation is
untouched (world = T·R·(S·M)·v == T·R·S′·(M·v)). Finger-curl pose keys
survive the mirror bake with correct direction. **New gotcha found here:**
after baking, children of the armature no longer inherit the 3.118 —
bone-parented props must have the factor re-applied to their seat location
AND scale (the sword shrank to a needle until fixed). Same family as
gotcha #30's scale swap.

### 2. Object-transform + pose-bone motion as ONE named clip — WORKS via NLA_TRACKS
Recipe (the important part):
- build each clip normally (object loc/rot keys on the armature objects +
  finger-curl keys, one action per armature)
- park each action on an **NLA track named after the clip**, same track name
  on both armatures, `animation_data.action = None` after stashing
- Blender 5 slotted actions: set `strip.action_slot = action.slots[0]` or the
  strip is silently empty
- export with `export_animation_mode='NLA_TRACKS'`,
  `export_bake_animation=True`, `export_force_sampling=True`

Result: `gltf.animations` = exactly one `AnimationClip` per clip name
(`sword_light` 1.20 s, `sword_guard` 1.47 s; 124 tracks each), carrying BOTH
armature node TRS motion and all bone motion for both hands. One
`AnimationMixer(gltf.scene)` + `clipAction(clip).play()` drives everything.
Same-named tracks across objects merging into one glTF animation is the whole
trick — this is the pattern for the real exporter.

### 3. Bone-parented sword — WORKS (exports as a child of the joint node)
Sword re-parented `parent_type='BONE'` to root `Bone` (world transform
preserved through `matrix_parent_inverse`, which unlike loc/rot/scale can
hold shear). In the GLB the Silverlight mesh node is a **child of the `Bone`
joint node** and rides the hand through the whole clip in three.js. Shear
metric at export: 0.0000 — no restructure needed. Two caveats:
- glTF nodes are TRS-only; if the composite local matrix HAD shear (mirrored
  anisotropic parent × non-axis-aligned bone frame, gotcha #27) it would be
  silently lost. `bone_parent_sword()` prints the shear metric — check it on
  the wristed rig, where the sword will hang off an animated wrist bone.
- Bone parenting hangs children off the bone TAIL, not the head.

### 4. Constraints — NOT EXERCISED (canonical rig has none), settings ready
The canonical scene has zero object or pose-bone constraints (probed). The
export path already forces full sampling (`export_bake_animation` +
`export_force_sampling`), which is what bakes constraint results into
curves. **Must be re-verified on the wristed rig** (Limit Rotation + the
2-DOF wrist): landmine is still open there, but the harness to test it in
minutes now exists.

### 5. Scale/units — SOLVED with a root-scale empty
Hands were staged at 3.118 with wrist→fingertip = 2.9 world units. A root
empty `FPHandsRoot` with uniform scale **0.19/2.9 = 0.0655** parents both
armatures; children's keyed locations pass through untouched (plain parent,
identity parent-inverse) and everything exports in real meters, consistent
with `assets/test_knife.glb` (26 cm). Measured in the browser (world-space
skinned bbox): whole ready pose = 0.46 × 1.10 × 0.56 m — two hands + raised
rapier, sane. The glTF exporter itself has NO scale option; the wrapper
empty is the unit story.

## Working exporter settings (Blender 5.1.2)
```python
bpy.ops.export_scene.gltf(
    filepath=..., export_format='GLB',
    export_animations=True, export_animation_mode='NLA_TRACKS',
    export_bake_animation=True, export_force_sampling=True,
    export_optimize_animation_size=False, export_def_bones=False,
    export_skins=True, export_yup=True, export_apply=False,
)
```
(`export_fp_hands.py` filters kwargs against the operator's RNA so renamed
params across Blender versions degrade to a warning, not a crash.)

## Browser verification gotchas (re-confirmed)
- `preserveDrawingBuffer: true` + `canvas.toDataURL()` — plain Playwright
  screenshots cannot capture WebGL (gotcha #17).
- Skinned bbox: `SkinnedMesh.computeBoundingBox()` applies bone transforms
  but returns the box in mesh-LOCAL space — apply `matrixWorld` before
  measuring real size, or the numbers lie.
- Playwright MCP server wants system Chrome; use crescent's own
  `node_modules/playwright` chromium directly (pattern:
  `tools/fp_hands_shot.js`, serves ~/Kore over localhost HTTP).
- Exporter warns `more than 4 joint vertex influences` (marketplace weights)
  — it truncates+renormalizes to 4; no visible artifact on the hands.

## Artifacts
- `tools/export_fp_hands.py` — reusable exporter (clips parameterized;
  `--bake-mirror`, `--sword-parent bone|object`, `--no-root-scale`, `--out`)
- `tools/fp_hands_test.html` — three.js loader/mixer test page (`__seek`,
  `__playClip`, `__shot`, `__lookFrom` hooks for headless driving)
- `tools/fp_hands_shot.js` — headless proof capture
- `glb_spike_proof.jpg` — 6-frame visual proof (also in Downloads)
- Test GLB not committed (33 MB): `C:\tmp\fp_hands_test.glb` /
  `~/Kore/fp_hands_test.glb`
