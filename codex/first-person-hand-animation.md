# First-Person Hand Animation — the technique

How to keyframe-animate first-person hands (casting, melee, throws) on a
bought/rigged two-hand asset in headless Blender. Learned building the four
elemental spell casts (2026-07-10). Reference implementation:
`tools/animate_casts.py` (motion) + `tools/render_hands_fp.py` (staging).

This is the counterpart to the auto-rig pipeline. Auto-rig is for creatures
nobody has modeled. This is for **using a rig you didn't build** — a marketplace
hand — and driving it with animation. See the design intent in
[casting-animation-design.md](casting-animation-design.md).

---

## The asset & its constraints (cgtrader two-hand)

- `Sphere.001` ↔ `Armature.001` = right hand; `Sphere.002` ↔ `Armature.003` = left.
- 20 bones/hand, hand-painted weights, quad topology. **Don't touch weights/mesh** —
  animate object transforms + pose-bone rotations only.
- **NO ELBOW.** The forearm is rigid geometry riding the wrist/root bone. This is
  the single fact that shapes the whole technique:
  - **Gross arm motion** (raising, sweeping, punching, rotating a whole hand to
    palm-out) = keyframe the **armature OBJECT transform** (`location` +
    `rotation_euler`).
  - **Hand shape** (curl, grip, splay) = keyframe **pose-bone X-curl**.

## Hand-local axes (memorize these)

After the left hand's `scale.x = -1` mirror, both hands share local axes:
- **fingers → +Z**, **palm → −Y** (faces the camera at identity), **forearm → −Z**,
  **thumb inboard**. Euler rotations are world `XYZ` (Rz·Ry·Rx).

## THE origin gotcha (cost the most time)

The armature **object origin is NOT the wrist — it sits at the forearm's lower
stub.** Along the hand's local +Z, at the authored scale 3.118:
- wrist joint ≈ origin **+3.1**
- curled-fist knuckles ≈ origin **+4.0**
- middle fingertip ≈ origin **+6.0**

Every staging position you guess will be off by ~3 units until you account for
this. When you want "the fist lands here," you're positioning the *origin*, so
subtract the offset. **Probe the rig at runtime; never guess the origin.**

## First person = the camera sees the BACKS of the hands

The player is behind their own hands. So every gather/hold/rest pose must live on
the **yaw-flipped branch** (Z near ±172/180), the same branch the release always
used. On that branch thumbs land **outboard** — correct for a vertical forearm
seen from behind. If you author on the un-flipped branch you get palms-to-camera,
which is wrong for FP and also fights the release orientations.

### Orientation cheat sheet (right hand; left mirrors: negate the Y and Z euler, negate X loc)

| Euler (deg) | Reads as | Used by |
|---|---|---|
| `(0, 0, 172)` | knuckles to camera, fingers up, palm downrange | rest / gather family |
| `(0, 0, 225)` | knife angled: palm inward+downrange, camera sees back-outboard quarter | seal / clasp |
| `(0, 0, 180)` | palm-out downrange, fingers up | **release family** |
| `(-108, 0, 10)` | palm up, tilted away, fingers to the horizon | fire cup |
| `(-180, 0, -8)` | fingers down, knuckles to camera | earth slam |

Note: exactly edge-on (Z≈270) reads palm-ish, not knife — use 225 for the
knife/seal quarter.

## Bridging orientations = forearm supination/pronation (the craft insight)

You **cannot teleport** between two orientations (e.g. gather Z≈172 → release
Z≈−180). A real wrist *rolls* through the transition. Insert **guide keys** that
supinate/pronate the forearm across the change:
- a boxing chamber rolls the palm up (supinate ~160°) before the punch,
- a scoop into a cup supinates ~160°,
- the release pronates back over the top.

Without guide keys the hand does an ugly 180° flip that looks broken frozen (and
only half-hides in motion blur). The guide key at the midpoint is what makes the
transition read as *a wrist*, not *a glitch*.

## The universal casting rhythm: gather → HOLD → snap

Every cast (and most actions) has three beats:
1. **Gather** — deliberate, eased-in wind-up (anticipation).
2. **HOLD** — a held beat at the signature pose. This is where the VFX orb forms
   and the eye reads it. The hold is non-negotiable; it's the "breath."
3. **Snap** — a fast release (fling/punch), then follow-through + settle.

## Retiming for contrast (author tight, then breathe)

Author the keys at natural spacing, then **retime** — don't re-pose. Each cast
carries a `retime` list of `(old_frame → new_frame)` anchors; `remap_frame` does
a monotonic piecewise-linear stretch. Push spacing **into the gather + hold**;
keep the **pull→fling span short** so the release stays snappy. A cast authored
at a flat ~1.3s reads as a keyframe-to-keyframe *sprint*; retiming gives it the
gather/hold/snap contrast that reads as intent. Applied once at import so
frames / phases / test-frames stay in sync.

## Easing

Bezier + `AUTO_CLAMPED` handles on every keyframe = smooth eases **without
overshoot**. (Overshoot handles cause fingers to hyperextend past their pose.)

## Metacarpal fraction

Non-thumb fingers are 4 bones: `[metacarpal, prox, mid, dist]`. The pose's three
angles go on the phalanges; the **metacarpal takes ~15%** of the proximal angle
(`METACARPAL_FRACTION = 0.15`) so the knuckle line bends slightly instead of
rigidly. Thumb is 3 bones, 3 angles, no metacarpal fraction.

## Blender 5.x layered actions (fcurve gotcha)

`action.fcurves` was **removed** in Blender 5.x. FCurves now live at
`action.layers[*].strips[*].channelbags[*].fcurves`. Handle both:
```python
curve_sets = ([action.fcurves] if hasattr(action, 'fcurves')
              else [cb.fcurves for L in action.layers for s in L.strips
                    for cb in s.channelbags])
```

## Mirror = normal flip

The left hand is the right-hand mesh with `scale.x = -1`. Negative determinant
flips face winding → renders inside-out. Flip the mesh normals via bmesh after
staging (guard on `matrix_world.determinant() < 0`).

## Workflow (headless, from WSL)

```bash
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
BLEND="\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand.blend"
SCRIPT="\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_casts.py"

# 12-frame review grids (default)
"$BLENDER" --background "$BLEND" --python "$SCRIPT" -- air_strike
python3 tools/montage_casts.py            # → cast_<name>_grid.jpg (+ Downloads)

# two sanity stills only (fast iteration on one pose)
"$BLENDER" --background "$BLEND" --python "$SCRIPT" -- air_strike --test

# every frame → ffmpeg → real-time MP4
"$BLENDER" --background "$BLEND" --python "$SCRIPT" -- air_strike --full
ffmpeg -framerate 60 -i /mnt/c/tmp/air_strike_%04d.png -pix_fmt yuv420p air_strike.mp4
```

- Scripts referenced by Blender need the `\\wsl.localhost\Ubuntu` UNC prefix;
  output paths **inside** the script must be Windows (`C:\tmp\...`), landing at
  `/mnt/c/tmp/...` from WSL. Engine: `BLENDER_EEVEE` (fallback `BLENDER_EEVEE_NEXT`).
- **Review via the grid** (Vetinari-style, L→R / T→B = time). Read it with the
  Read tool and critique against the design spec. Get ONE cast convincing before
  scaling to the rest.

## What read well / what didn't (first pass, honest)

- **Water = best.** Big whole-arm sweep + an unambiguous clasp-with-gap. The eye
  sees the vessel before the orb exists. Ship-adjacent.
- **Earth = strong.** Clench → high wind-up → vertical slam column → forward
  punch. Real anticipation/overshoot weight. Rough: rigid-forearm stiffness on
  the slam, thumb hooks at the fist bottom.
- **Air = right bones, weak signature.** Best *release* of the four, but the
  stacked-knife monkey-seal doesn't read from this camera — looks like one
  vertical hand, not two framing a gap. Needs a dedicated tucked-thumb knife pose
  and possibly a camera that sells the vertical stack.
- **Fire = weakest read.** One-hand cast → the idle *other* hand hangs there
  dead, stealing focus. The fix is the idle hand (drop it low / give it a support
  gesture), not the fire hand.

**Lesson:** big gross-motion + unambiguous hand *shape* reads; subtle stacked
poses and dead second hands don't. Stage for the camera you have.

## Next-pass improvements (logged)

- No **wrist-bone secondary motion** yet — all gross motion is object-level.
  Adding wrist lead/drag (the wrist arrives a beat after/before the forearm) is
  the single biggest quality lever left.
- Air seal: dedicated knife pose + camera.
- Fire: fix the idle hand.
- Earth: soften the slam column, fix thumb hook.

---

# THE INSPECTION SIDE (added 2026-07-29)

Everything above is the AUTHORING side — how to keyframe. This section is the
other half: how to look at the shipped rig the way the PLAYER sees it, which
is what you need when the note is about framing rather than motion.

Written after burning four dead ends on "set up a scene so Khaled can fix the
FP framing." Three of them were preventable by a document.

## 1. THE CAMERA IS NOT IN THE ENGINE DEFAULTS — the GAME overrides it

`ViewmodelManager.DEFAULT_CONFIG` says `fov: 55, offset: [0,-0.05,0]`.
**Slayer2 does not use that.** `games/slayer2/client/game.js` (registerViewmodel):

```js
fov: 54,
offset: [0, -0.22, -0.45],   // rig pushed 0.22 m DOWN, 0.45 m FORWARD
```

The rig is a CHILD of the viewmodel camera, so `offset` is the rig's position
in camera-local space — meaning **the eye sits at rig-local (0, +0.22, +0.45)
in glTF metres.** glTF (x,y,z) → blender (x, −z, y), so in blender:

> **camera at (0, −0.45, 0.22), looking +Y, 54° VERTICAL fov**
> (`sensor_fit='VERTICAL'`, `angle_y = radians(54)`)

Sable's own comment: *"push it forward and down so the hands read at the bottom
of frame."* **That offset IS the forearm-dominance complaint** — it is the
cause, not a symptom. Before re-rigging anything to fix framing, check whether
changing this one array fixes it for free.

## 2. DO NOT DERIVE THE CAMERA FROM THE BLEND — import the shipped glb

The exporter **rebases the armatures**. Blend staging `(2.05, 0, 0)` ships as
glTF `(1.926, −0.029, 2.408)` with a baked rotation. So any camera computed
from the blend's staging constants is wrong, and you get an empty frame with
no clue why.

**Import `assets/fp_hands.glb` instead.** `FPHandsRoot` bakes `ROOT_SCALE`
(0.0655), so the imported scene is already in real metres and the rig origin
is the blender origin — the camera formula above then just works.

Two things to hide after import: the **orb-anchor Icospheres** (1 m helpers
that swallow the frame) and, unless you have fixed the seat, the weapon.

## 3. IMPORTED CLIPS USE SLOTTED ACTIONS (blender 5)

Each clip is ONE action with THREE named slots:
`['Armature.001', 'Armature.003', 'ThrowingKnife']`.

Assigning the action to an object without binding it to **its own** slot makes
every object read the FIRST slot — both arms then stack on top of each other
at the right arm's transform, which looks like a rig bug and is not one.

```python
act = next(a for a in bpy.data.actions if 'idle_sword' in a.name)
for o in bpy.data.objects:
    slot = next((s for s in act.slots if s.name_display == o.name), None)
    if not slot: continue
    if not o.animation_data: o.animation_data_create()
    o.animation_data.action = act
    o.animation_data.action_slot = slot
```

**Always open a sandbox on `idle_sword`, never the rest pose.** The rest pose
is arms-up-and-open and the player never sees it; judging framing against it
is judging a pose that does not exist.

## 4. Weapon seats are in RAW glTF space

`assets/fp_weapon_seats.json` — the key is **`silverlight_sword`** (not
`sword`), and `matrix` is a NESTED row-major 4×4 (not flat 16). Its own
`convention` block says *"raw node, no import conversion"*, so it is glTF-space
and needs conjugating into blender space (`C · G · C⁻¹`, C = +90° about X).

**Still not sufficient**, and this is an open gap: blender bone-parenting adds
a bone-TAIL-length frame that the seat does not account for, so the blade
lands off in space. The old source-blend sandbox handled it with
`frame = pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))` then
`matrix_basis = frame.inverted() @ seat`; that has not yet been reconciled
with the glTF-space seat. **Until it is, ship the weapon HIDDEN** — a wrong
sword is worse than no sword when the question is framing.

Also from the seats file: the RIGHT hand joint has a **negative-determinant**
world matrix (mirrored armature), so any new chiral prop parented there
renders mirror-flipped.

## 5. MEASURE the framing — do not eyeball it

"That arm eats the screen" should be a number. `tools/read_fp_pose.py`
projects each hand mesh through the FP camera with
`bpy_extras.object_utils.world_to_camera_view` and reports the on-screen
footprint. Baseline on the shipped idle:

```
RIGHT (Armature.001)  19% frame width x 55% frame height
LEFT  (Armature.003)  20% frame width x 76% frame height
```

The left arm is measurably TALLER in frame than the right — which is exactly
what "the left arm takes over most of the screen" means, now stated as data
you can regress against after a fix.

## 6. The workflow

- `tools/build_fp_sandbox.py` → builds `fp_sandbox.blend` (shipped glb,
  idle_sword, real game camera, helpers hidden). **Numpad 0 to judge.**
- Khaled works in **OBJECT MODE** — framing complaints are placement, and
  placement lives on the armature objects, not the bones. `H` hides an arm.
- `tools/read_fp_pose.py` → object transforms + posed bones + screen
  footprint, as JSON.
- `FP_SANDBOX_README.md` → his copy of the above.

**Which lever:** both-arms framing can be fixed for FREE via slayer2's
`offset` (no re-export). Anything ASYMMETRIC — hide the left, shrink the left,
re-pose one arm — must come from the rig and needs a re-export.
