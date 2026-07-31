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

## 7. CHIRALITY — the rig shipped TWO LEFT HANDS (2026-07-29)

Khaled, looking at the sandbox: *"Perchance, are there two left fucking hands
in this scene? They both have thumbs on the right from the back."*

He was right. `fp_hands.glb` as imported into Blender renders **two left
hands**, and it had been that way since delivery.

### How to TEST chirality (none of my existing checks could)

Do not use frames or normals — a mirrored object lies through both (bone
frames invert, and normals get flipped to fix shading, which flips your test
with them). My first two attempts were degenerate/contaminated and gave
±0.0000.

**Signed tetrahedron volume of four landmarks. Positions only.**
```python
w = M @ pb['hand'].head
i = M @ pb['Bone.019'].tail   # index tip
p = M @ pb['Bone.010'].tail   # pinky tip
t = M @ pb['Bone.003'].tail   # thumb tip
sv = (i-w).cross(p-w).dot(t-w)      # sign IS the handedness
```
Mirroring flips this sign and nothing else does. Sanity-check `|(i-w)×(p-w)|`
is well above zero, or the points are coplanar and the sign is noise.

### What was measured
```
shipped glb, right arm  scale (-3.118,-3.118,-3.118)  sv -0.0000091  LEFT
same arm     scale (+3.118,+3.118,+3.118)  sv +0.0000091  RIGHT
left arm     scale (+3.118,+3.118,+3.118)  sv -0.0012024  LEFT
SOURCE cgtrader_hand_wristed.blend: BOTH armatures LEFT, both +scale,
   data chirality identical to 7 dp (-0.16296673 / -0.16296718)
   => the working blend is ONE hand duplicated, not the purchased pair.
```

Mirroring one hand is *correct practice* — a left and a right hand ARE mirror
images, identical topology, no remeshing needed (only normals invert, and
nothing on a bare hand is asymmetric). The bug is applying the mirror TWICE.

### The fix in the sandbox
Node scale to positive, then restore placement by rotating about the wrist:
```python
o.scale = tuple(abs(v) for v in o.scale)
corr = f_new.rotation_difference(f_old).to_matrix().to_4x4()
o.matrix_world = (Matrix.Translation(w_old) @ corr
                  @ Matrix.Translation(-w_new)) @ o.matrix_world
```
Wrist moved 0.00000 m, forearm angle 0.000°.

### OPEN — do NOT "fix" the exporter until this is answered
`bake_mirror` is behind a `--bake-mirror` flag that is OFF by default, and
when it runs it correctly zeroes the node scale. Staging applies
`(-3.118, +3.118, +3.118)` (ONE negative axis) but the shipped glb carries
`(-3.118,-3.118,-3.118)` (three) — so **Blender's glTF exporter re-decomposed
the transform**, and those two differ by a rotation, i.e. they can be
equivalent. So the defect may live in the Blender IMPORT round-trip rather
than the asset, in which case three.js may have been rendering it correctly
all along. **Verify in-engine before changing the exporter.**

### Why every check I had missed it
Deformation parity, weight audits, clip enumeration, GLB binary verification —
**all chirality-blind.** A perfectly mirrored hand passes every one of them.
`fp_weapon_seats.json` even documents "the RIGHT hand joint world matrix has
NEGATIVE determinant" as a quirk to work around: I wrote down the symptom and
never asked why it was there.

**Add a chirality assertion to the export verification** — right arm signed
volume must be positive — so this class cannot ship again.

## 8. WHAT KHALED'S POSED GRIP TAUGHT ME (2026-07-29)

He posed the sword grip by hand and asked: *"can you glean any useful
information, from me having posed the hands like this ... as you werent able
to before"*. Yes — and one finding inverts an approach I had been confident in.

Data: `poses/khaled_grip_v2.json` (seat matrix, both hands' angles, arms).

### 8a. MINIMISING INTERPENETRATION IS THE WRONG OBJECTIVE

I built an overlap checker, measured my seat at 14.75% "sword verts inside
hand", called it impalement, and ran a search that got it down to 6.01%. I
then reported that 6% was "still not a grip".

**His human-approved grip measures 11.69%** — nearly double my "improved"
version. A real grip presses fingers INTO the handle; that overlap IS the
contact. Optimising it downward walks away from a correct grip.

### 8b. The metric is WHERE the overlap is, not how much

Classify each overlapping vertex by whether it is nearer a FINGER bone or the
WRIST. On his grip:

```
overlap nearer FINGERS : 11.69%   <- gripping, correct
overlap nearer WRIST   :  0.00%   <- impalement, must stay zero
```

**Rule: wrist overlap ~0%. Finger overlap 10-12% is contact.** My 14.75%
failed not because it was large but because it was in the WRIST — a shaft
through flesh. Same number, opposite meaning, depending on location.

### 8c. A real grip curls about twice as hard as I was authoring

```
Khaled's grip  thumb [39, 86, 89]   index [22, 105, 60, 23]
               middle [20, 109, 65, 81]  ring [26, 100, 114, 61]
               pinky [36, 83, 73, 58]
```
Middle joints at **84-114 deg**. My cast/grip poses had been using 52-56 —
roughly half. That is why my hands always read as "resting near" a prop
rather than holding it.

His relaxed LEFT idle, for contrast (and it is a good FP idle):
```
thumb [31, 41, 46]  index [7, 19, 72, 14]  middle [6, 32, 60, 1]
ring  [9, 36, 47, 8]  pinky [9, 44, 12, 12]
```
Note the asymmetry — index/middle/ring/pinky all differ. Symmetric finger
values are the tell of a machine-authored hand.

### 8d. The seat, measured instead of derived

Sword in the hand bone's own frame (portable, survives re-staging):
```
translation [1.75318, -0.27734, -0.62177]
rotation(q) [0.51827, 0.51594, -0.34871, -0.58618]
scale       [-2.6953, -2.6953, -2.6953]
```
Fingertip-to-blade-surface distances 0.014-0.039 m — the tips are wrapped
PAST the handle, not touching it head-on.

**The lesson for the pipeline: when a spatial relationship resists derivation,
stop deriving and have Khaled pose it once, then MEASURE.** That is what the
sandbox is for, and it produced in one pass what my search could not reach.
