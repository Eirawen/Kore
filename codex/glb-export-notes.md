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

### 4. Constraints — PROVEN (2026-07-21, knife release on the wristed rig)
The hard case is closed: `knife_throw_blade_first` (influence-keyed ChildOf
release + the 3.118 scale swap, gotcha #30) exported from
`cgtrader_hand_wristed.blend` (Limit Rotation wrist constraints present)
via the knife path in `export_fp_hands.py`, verified in three.js by
`tools/fp_knife_shot.js` with a NUMERIC node probe (`window.__sceneRoot`
hook in the test page):
- knife↔hand distance **3.824 constant** while in hand (t ≤ 0.83 s),
  then 4.7 → 10.2 → 23.7 → 45.0 after the release — detaches in the
  BROWSER and flies downrange ballistically;
- knife world-scale magnitude **15.278 = 4.9 × 3.118 constant across the
  switch** — the release scale swap survives the bake, no shrink;
- one clip, 133 tracks: both armatures + the knife object merged via the
  same-named NLA tracks.

Two footnotes:
- the baked knife node scale flips SIGN at release (−15.278 → +15.278 on
  x): while pinched, the mirrored hand's negative determinant is baked
  into the knife node. Matches Blender's render (faithful bake), and a
  cone is symmetric so it's invisible — but a CHIRAL prop would render
  mirror-flipped while held. Consider `--bake-mirror` for chiral props.
- the knife test exports `--no-root-scale` (hand units): the release
  scale swap assumes hand units end-to-end. Folding the knife under the
  meters root empty is the real exporter's one remaining integration.
  **RESOLVED (2026-07-21, final package):** parent the knife under
  `FPHandsRoot` and set the ChildOf `inverse_matrix = root_scale^-1`.
  ChildOf composes `final = (target @ inverse) @ (parent @ basis)`; the
  inverse cancels the root on the in-hand path (the target arm already
  carries it) while free flight becomes `root @ basis` — every authored
  hand-unit key stays valid, world scale magnitude 1.001 m constant
  across the release (browser-verified).

Browser screenshot gotcha found here: the test page's RAF loop keeps
playing after `__seek`, so screenshots drifted (a wrapped LoopRepeat clip
masqueraded as a shrunken knife). `window.__paused = true` freezes the
mixer for deterministic stills; the synchronous numeric probes were never
affected.

### 5. Scale/units — SOLVED with a root-scale empty
Hands were staged at 3.118 with wrist→fingertip = 2.9 world units. A root
empty `FPHandsRoot` with uniform scale **0.19/2.9 = 0.0655** parents both
armatures; children's keyed locations pass through untouched (plain parent,
identity parent-inverse) and everything exports in real meters, consistent
with `assets/test_knife.glb` (26 cm). Measured in the browser (world-space
skinned bbox): whole ready pose = 0.46 × 1.10 × 0.56 m — two hands + raised
rapier, sane. The glTF exporter itself has NO scale option; the wrapper
empty is the unit story.

## Final-package landmines (2026-07-21, export_fp_hands_final.py)

Found assembling the real 11-clip `fp_hands.glb`; each cost a debug loop
against GLB binary parses. All fixed in `tools/export_fp_hands_final.py`.

### 6. Multi-track constraint bake uses the WRONG cross-object state
In NLA_TRACKS mode the exporter bakes each object's track after muting
only THAT OBJECT's other tracks — other objects sit at their full
unmuted NLA stack (last track wins). A constraint whose target is
another object (the knife's ChildOf → armature) therefore bakes against
the wrong armature animation as soon as multiple tracks exist. The
spike's knife proof passed ONLY because knife clips were exported alone.
Fix: pre-bake the constrained object's parent-local TRS per frame in
Blender with the correct per-clip `is_solo` state, key it plainly
(quaternion mode, LINEAR), and DELETE the constraint before export.

### 7. Blender 5 implicit action reuse corrupts stashed actions
`keyframe_insert` with `animation_data.action == None` can silently
re-use/extend a previously stashed action instead of creating a fresh
one (slotted-actions behavior). Symptom: the left hand's `sword_light`
action absorbed the idle keys — action frame_range ballooned to 121, and
since NLA strip length follows action range, the exported sword_light
became 2.017 s with a dead tail. Fix: ALWAYS create actions explicitly
(`bpy.data.actions.new` + slot + assign), clear `action_slot` before
`action = None` when stashing, and pin every strip to its clip length
(`action_frame_start/end` + `frame_start/end`) with a hard validation.

### 8. Constant OBJECT channels are culled even with optimize OFF
`export_optimize_animation_size=False` does NOT keep constant object
channels — `export_optimize_animation_keep_anim_object=True` does
(armature counterpart already defaults True). A culled channel is
runtime cross-clip leakage: the parked left hand / hidden knife would
stay wherever the previous clip left them.

### Bonus: baked sampler time base
Baked samples put frame f at `f/60` s (first sample 0.0167), NOT
`(f-1)/60`. Event timestamps must use `frame/60`.

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
