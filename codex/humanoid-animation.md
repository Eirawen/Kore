# Humanoid Animation — the succubus, and every biped after her

Everything learned 2026-07-23..25 taking a static Meshy succubus to coy,
jump, hover, and an emotional wing vocabulary. **Read this before touching
her.** Every number here cost hours. Most of it generalises to any
marketplace/generated biped; the character-specific parts are flagged.

Companions: `component-track-animation.md` (the authoring method),
`wing-emotion.md` (the wing pose library), `gotchas.md` #34-54.

---

# PART 1 — THE RIG (character-specific, but the SHAPE is universal)

## Files, and which one to load

| file | what it is | use it for |
|---|---|---|
| `succubus_winged.blend` | **THE CURRENT CHARACTER.** Body + grafted bat wings + wing bones, bound. | **all new animation** |
| `succubus_walk.glb` | withSkin walk clip + original skin | the AXIS ROSETTA STONE (below); source for re-grafting |
| `succubus_original.glb` | Character_output, no animation | reference only |
| `wings_raw.glb` | the generated bat-wing pair, unmounted | re-grafting at a new scale |
| `succubus_rigged.blend` | Khaled's head-surgery blend | **avoid** — has head-weight artifacts |

Regenerate the winged blend any time with `tools/graft_wings.py`
(config in `tools/.wingcfg`).

## Skeleton — 24 original bones + 6 wing bones

```
Hips
├─ LeftUpLeg → LeftLeg → LeftFoot → LeftToeBase
├─ RightUpLeg → RightLeg → RightFoot → RightToeBase
└─ Spine02 → Spine01 → Spine
              ├─ LeftShoulder → LeftArm → LeftForeArm → LeftHand
              ├─ RightShoulder → RightArm → RightForeArm → RightHand
              ├─ neck → Head → head_end, headfront
              └─ WingL_root → WingL_mid → WingL_tip     (added by the graft)
                 WingR_root → WingR_mid → WingR_tip
```

**Note the spine order is INVERTED from what you'd expect:** `Spine02` is
the LOWEST (child of Hips), `Spine` is the HIGHEST (parent of shoulders
and neck). Getting this backwards puts the bend in the wrong place.

`headfront` is a forward-pointing child of `Head` — it is the **gaze
vector source**: `fwd = headfront.head - Head.head`.

### What she does NOT have
- **No finger bones.** The hand is a paddle. This drives real decisions
  (see FINGERLESS below).
- **No facial rig.** No brows, mouth, ears. Emotion must come from head
  angle, body contraction, and **wings**.
- **No tail bones**, despite tail geometry.
- Only one toe joint per foot (`ToeBase`) — enough for toe-off, not for
  a toe curl.

## Measured proportions (world metres, rest pose)

```
total height            1.630     ground (lowest vert)   0.000
Hips bone z             0.951     LeftUpLeg (hip joint)  0.865
thigh  (hip→knee)       0.346     shin (knee→ankle)      0.375
ankle z                 0.150     toe z                  0.001
shoulder width          0.271     Spine (chest) z        1.269
hand length (measured)  0.145     ← NOT 0.095, I guessed and was 50% off
CHIN (lowest fwd head vert)  (0.001, -0.183, 1.420)
```

**She faces −Y. Her left is +X. Up is +Z.** Get this wrong and every sign
is inverted.

**Armature-local units are CENTIMETRES** (armature scale 0.01). So a pose
bone `location` of `(0,0,-19)` is a 19 cm drop. World queries come back in
metres. This trips you constantly — convert with
`pb.bone.matrix_local.to_3x3().inverted() @ Vector(cm_offset)`.

---

# PART 2 — THE FIVE LAWS

Everything else follows from these.

## LAW 1 — Learn the joint axes from her OWN animation

Marketplace/generated bipeds ship with animation packs. **Those clips are
the ground truth for the rig's real hinges.** Never trust bone tails or
rolls on an imported rig — Blender's glTF importer invents them (this
rig's tails point 5–19 METRES away). Heads are reliable; tails are
hallucinated.

```python
def dominant_axis(bname):          # sample the walk, angle-weighted mean
    for f in range(f0, f1+1):
        scene.frame_set(f)
        q = pb.rotation_quaternion  # BONE-LOCAL, which is what we want
        ...flip into one hemisphere, weight by angle, average, normalise
```

Measured, and reusable verbatim:

```
LeftForeArm  (-0.73, 0.09, 0.68)   consistency 0.98  ← a TRUE hinge
RightForeArm (-0.74,-0.07,-0.67)   0.97
LeftLeg      ( 0.98, 0.20,-0.02)   0.76   ← knee, only ~0.76 single-axis
RightLeg     ( 0.99,-0.05, 0.11)   0.88
LeftUpLeg    (-0.98,-0.16, 0.08)   0.80   ← hip is a BALL joint
LeftArm      (-0.04, 0.97,-0.24)   0.86
LeftFoot     ( 0.96,-0.21, 0.16)   0.78
```

**Read the consistency number.** 0.98 = a real hinge, constrain to it.
0.76–0.88 = it is NOT a hinge; give that joint freedom or solve it
analytically. Ignoring this caused the 6 cm floor-sink.

## LAW 2 — Apply rotations with the live-matrix conjugation

The single most important formula in this document.

```python
def apply_delta(pb, D):            # D = an ARMATURE-space rotation
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    M0 = pb.matrix.to_quaternion()      # LIVE, posed ancestors included
    pb.rotation_quaternion = M0.inverted() @ D @ M0
```

`bone.matrix_local` is the **REST** frame and goes stale the instant an
ancestor moves. Composing big rotations through stale frames is what
produced the v1/v2 body horror (arm through chest, mesh stretched into a
sail). `pb.matrix` is live. Use it.

The aim-at-a-direction form, which you will use constantly:

```python
def aim_bone(pb, want_world):
    R = mw.to_3x3(); Ri = R.inverted()
    pb.rotation_quaternion = Quaternion(); update()
    cur = (Ri @ ((mw @ pb.tail) - (mw @ pb.head))).normalized()
    des = (Ri @ Vector(want_world)).normalized()
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ cur.rotation_difference(des) @ M0
```

Used for: leg IK, head look-at, wing unfold. **Anything with a target
direction should be aimed, never hand-authored in eulers.**

## LAW 3 — Exact beats search, and more DOF can make search WORSE

Foot-planting by coordinate descent:

```
3 fixed axes → 6 cm floor sink
5 DOF        → 2 cm
7 DOF        → 8 cm      ← MORE freedom, WORSE local minimum
analytic     → 0.0000 m
```

A leg is a two-bone chain. Solve it:

```python
d = clamp(|ankle_target − hip|, |a−b|, a+b)
cos_al = (a² + d² − b²) / (2·a·d)
pole   = (0,−1,0)                      # she faces −Y: the knee LEADS
perp   = normalise(pole − along·(pole·along))
knee   = hip + a·(cos(al)·along + sin(al)·perp)
aim_bone(thigh, knee−hip); aim_bone(shin, ankle−knee); aim_bone(foot, toe−ankle)
```

Reach for a solver only when there is no closed form (the arm-to-chin
placement genuinely needed one).

## LAW 4 — Constraints are cheap; assertions are expensive

Anything you can measure, measure before you claim it.

- **Torso clearance proxy** — sample torso-weighted verts into
  `(height bin × angular sector) → max radius`, then penalise arm sample
  points inside it. Breasts are chest-weighted, so they're included, which
  is exactly the point. Killed the arm-through-chest class permanently.
  Penetration 0.0066 → **0.0000**.
- **Bands, not floors.** `if hand_dir.z < 0.55: penalise` let the solver
  stand the hand straight up (0.92) into a wall over her mouth. Any
  one-sided constraint WILL be maximised. Use `(0.42, 0.66)`.
- **Audit a dimension the transform should PRESERVE.** Span alone said my
  wing spread worked; span + height said it was flattening her
  (1.062 → 0.481).
- I twice asserted geometry (wrist mechanics, wing splitting) that a
  60-second probe disproved. **Probe first.**

## LAW 5 — Components on their own clocks, and fidgets are events

See `component-track-animation.md` for the full method. The compressed
version:

Break the body into `head / chest / pelvis / legs / feet / larm /
lshoulder / rarm / wings`. Ask what each should be doing and **why**; the
schedule falls out of the reason:

| part | reasoning | schedule |
|---|---|---|
| head | a flinch is a REFLEX; the return is the emotion | first to move, last to settle |
| chest | you turn away with your body a beat AFTER your face | lags the head ~6 f; breath HOLDS during hesitation |
| protective arm | automatic, pre-decision | early, **never hesitates** |
| expressive arm | self-conscious | late, **owns the stall**, arrives last, then freezes |
| shoulder | a consequence of the hand arriving | trails the hand |
| pelvis/legs/feet | postural; nobody watches a weight shift | slow, early, out of the way |
| wings | see PART 5 | their own emotional clock |

**Symmetric hesitation is the tell of whole-pose keying** — she stalled
reaching for her face and her thigh on the same frame. Asymmetry in TIME
is what reads as a person.

**Fidgets are EVENTS, not oscillations.** A weight shift is a decision she
makes once and keeps. Only breath oscillates. One sine driving the whole
body in phase = "a model in Blender, not a person."

---

# PART 3 — SMOOTHNESS (the jolt has three causes)

1. **Hesitation is DECELERATION, never cessation.** 0.84 → 0.87 over 14
   frames is *frozen*, and a frozen part reads as a paused game. Author so
   the increments SHRINK but never hit zero:
   `.16 → .62 → .86 → .91 → 1.00` (per-frame: .021, .013, .005, .008).
2. **Contact damps — no overshoot** on a hand landing on your own body.
   Overshoot belongs on free-flying limbs (a punch, a throw).
3. **`AUTO_CLAMPED` on EVERY key is a hidden jolt factory.** It flattens
   velocity to zero *at every key*, so a multi-key move becomes a chain of
   stop-starts. **Clamp only the first and last key of each fcurve; give
   pass-through keys `AUTO`:**

```python
for i, kp in enumerate(kps):
    kp.interpolation = 'BEZIER'
    kp.handle_left_type = kp.handle_right_type = (
        'AUTO_CLAMPED' if i in (0, len(kps)-1) else 'AUTO')
```

4. **Overlap must START EARLY to READ as overlap.** An eased curve barely
   moves in its first frames, so a turn beginning 8 frames before the hand
   lands still reads as sequential. Begin the dependent motion at ~40% of
   the primary's travel.

**Audit it numerically — `tools/velocity_check.py`.** Sample a bone's
world position per frame, differentiate, report: mid-move dead runs
(near-zero speed *inside* the active span), max frame-to-frame
acceleration (jolts), and whether two components overlap. Zero vision cost.

Two caveats so you don't over-trust it: **passive carry inflates spans** (a
hand "moves" whenever the pelvis shifts, being a child of the spine — good
for what the EYE sees, misleading for "when did this component start"), and
**a reflex SHOULD spike** (the head flinch flags as a jolt and that's
correct).

---

# PART 4 — PHYSICS (jumps, hovers, anything airborne)

**Never ease a trajectory. Integrate it.**

```python
V0 = sqrt(2*G*JUMP_H)              # G = 9.81, height in metres
z(t) = z0 + V0*t − 0.5*G*t²        # keyed every 2 frames, AUTO handles
```

A symmetric bezier ease floats at the apex; real gravity gives
fast-rise / hang / fast-fall for free. **Audit against MESH geometry, not
the root value:** lowest vertex 0.000 on the ground → +0.468 at apex.

**Hover = the same integration with impulses:**

```python
v -= G*dt each step;  v += FLAP_LIFT at each downstroke
```

Set `FLAP_LIFT` *below* `G × flap_period` and she sinks a little every
beat — **the sag between beats is what reads as WORK.** A smooth hover
reads as levitation. Break-even at an 11-frame beat is **1.80 m/s**; the
shipped hover uses 1.52 (sinking), ~2.1 would climb.

Two things fall out free:
- **Causality** — fire the impulse mid-downstroke (`flap_f + 2`) so she
  rises AFTER the wings move. Force leads position.
- **The LANDING FRAME becomes an OUTPUT** of the sim. Key the landing
  poses at whatever frame it returns.

**Ground contact:** flat foot targets ankle AND toe (over-determined on
purpose — it pins foot orientation). Toe-off targets the TOE only, with
the ankle parked one foot-length up-and-behind
(`toe + FOOT_LEN·normalise(0, 0.32, 1)`) — that IS plantar flexion, and
it's what makes a jump a push instead of a levitation. **Toes leave last
and touch first.**

**The root curve must PASS THROUGH the exact height each IK plant was
solved at**, or the foot is planted for a pose she isn't in.

---

# PART 5 — THE WINGS

## Structure

6 bones: `Wing{L,R}_{root,mid,tip}`, parented to `Spine`. Two independent
meshes `WingsL` (1146 v) / `WingsR` (1143 v), each bound to the armature
with its own vertex groups. Mounted at the **scapula** (z 1.20, below the
shoulder joint — where bat wings actually attach), span 1.06.

**They are split on purpose.** Only 39 of 4308 faces straddled the
midline (0.9%), and the bridge sits at her mid-back where her torso
occludes it. Independent wings buy: phase offset between beats (real
flapping is never symmetric), differential angle for banking, asymmetric
rest, and **a torn wing** later.

## UNFOLD, never swing

Applying one rotation direction to a head-to-tail chain **swings it like a
rigid plank** — it gains span by tipping the wing into a horizontal plane
(height 1.062 → 0.481). **AIM every bone along one outward direction**
instead: that straightens the furled arc, so span grows from the chain's
own length and the membrane stays standing (height 1.058 at the same
span). Elevation goes on the ROOT, AFTER extension — the order a real
wing uses.

## Her wings are her FACE

She has no facial rig. Her wings are the largest legible emotional
instrument on the character — bigger than her head in silhouette.
`tools/wing_poses.py` has eight named poses; `−Y is her front`, so a
**negative Y aim wraps them forward** and that one sign is the difference
between displaying and hiding.

```
furled  1.060 span  neutral        display 1.595  confident / threat
shy     0.962 DEPTH hiding (wraps) eager   1.627  excited / rising
droop   1.162 tall  spent / sad    clamp   0.947 SPAN fear (smallest)
power               down-stroke    cocked  1.406 tall  curious (asymmetric)
```

`apply_wing_pose(arm, name, amount, keyframe=f)` blends from furled and
keys into a component track.

## The graft (for re-scaling or a new asset)

`tools/graft_wings.py`, config `tools/.wingcfg`. Probe islands first, keep
the asset as a SEPARATE mesh sharing the armature, transform
**anchor-relative** (scale about the attachment zone so it never drifts),
derive bones from the MOUNTED geometry sampling the asset's own arc at
span fractions 0.42/0.78/1.0. **Generated wings arrive FURLED** (bbox ~1:1)
— do not fix that by non-uniform scaling; rig it furled and open it with
the bones.

---

# PART 6 — FINGERLESS HANDS

The hand is a 0.145 m paddle. Consequences:

- A flat palm anywhere near the face reads as **shock / hiding /
  facepalm**, never as thoughtful. The gesture only reads coy if the
  **fingers point UP along the jaw** — a band constraint on `hand_dir.z`.
- A "chin touch" must target the **JAW CORNER**
  (`CHIN + (0.034, 0.020, −0.026)`), not the chin centre — a dead-centre
  chin poke needs an index finger.
- Prop grips are impossible to sell close-up. Keep props at arm's length
  or off-camera; if you need a real grip, use a dedicated hand asset (see
  the FP hands work).

---

# PART 7 — WORKFLOW & ECONOMICS

**Blender compute is free. LOOKING is what costs.** The loop:

1. **Iterate on NUMBERS** — solver residuals, clearance penetration,
   velocity audits, span/height. Zero token cost.
2. **Render freely.**
3. **Read ONE small strip.** `tools/pose_check.py` renders 5 diagnostic
   angles (front / her-left / her-right / top-down-45 / full 3-4) at 620 px.
   Never a 12-cell 2 MP grid.
4. **Hand the mp4 to Khaled.** His vision is better than mine and costs
   nothing. This is the dailies model.

**Always shoot the acting-arm SIDE view.** A 3/4 view is depth-ambiguous:
"arm in front of chest" and "arm inside chest" render nearly identically.
The tell is a **MISSING ELBOW**.

**Pose gate before motion.** Deliver the landed key pose, get a verdict,
*then* spend timing, grids, and mp4.

**Config travels by FILE, not env vars** — WSL env vars do NOT reach
Windows Blender through `--background --python`. Read a config file over
the UNC path (`\\wsl.localhost\Ubuntu\...`). Blender also cannot resolve
WSL posix paths for `save_as_mainfile` — use the UNC form.

**Housekeeping:** clear `/mnt/c/tmp/*.png` between runs. 1.7 GB of
accumulated frames on the 9p mount OOM-killed WSL mid-render.

---

# PART 8 — RECIPES FOR WHAT COMES NEXT

She's going to be animated a lot more. Starting points:

**IDLE** — the hardest and most valuable. Breath on the chest (the only
true oscillation), micro-drift on the head, weight-shift EVENTS every few
seconds, and `cocked` or `furled` wings with a slow settle. Zero
whole-body sine. A standing NPC that never moves is a statue; one that
oscillates is a puppet.

**WALK / RUN** — do NOT author. Retarget from her animation pack: import
the clip GLB into the target scene and let the SAME importer handle both
sides (hand-rolled `rest⁻¹ ⊗ channel` has a systematic per-bone error —
the importer re-bases bones and bakes corrections into imported curves).
Then overlay wings as a component track.

**HIT REACTION** — `clamp` wings on the impact frame (fear makes her
smaller), chest folds, head snaps then settles last, one foot slides back
via the analytic IK to catch her weight.

**TALK / IDLE CONVERSATION** — no mouth, so it all lives in head angle and
wing micro-shifts. `display` when asserting, `shy` when deflecting,
`cocked` when curious. Wings ARE the dialogue.

**SIT / LEAN** — the analytic leg IK generalises: plant both feet, drop
the root, and the legs solve. Add a contact constraint for the surface.

**FLIGHT (if we ever let her)** — one constant. `FLAP_LIFT` above
`G × flap_period` and she climbs. Same rig, same clip, same code. See
`the-real-game.md`: she's flightless as a species trait, not a limitation.

**A TORN WING** — the wings are independent meshes. Delete membrane faces
from one, keep the weights, and every animation inherits the damage.

---

# PART 9 — TOOL INDEX

```
graft_wings.py        mount/scale/split/rig the wings      (.wingcfg)
wing_poses.py         the 8-pose emotional library + applier
render_wing_poses.py  contact sheet of the library
probe_wings.py        find wing islands + leg proportions
probe_newwings.py     probe a generated asset before grafting
probe_midline.py      measure a seam before claiming it can't be cut
probe_wing_axis.py    which axis opens the wings (empirical)
probe_wing_spread.py  swing vs unfold vs sweep, measured
animate_coy5/6.py     component tracks + the coy emote (v10/v11)
animate_jump.py       analytic leg IK + ballistic root
animate_hover.py      simulated flight with flap impulses
velocity_check.py     numeric dead-frame / jolt / overlap audit
pose_check.py         the 5-angle pose gate
retarget_walk.py      (superseded — see the importer note above)
```

---

## The one-line version

**Probe before you claim. Learn the axes from her own motion. Aim, don't
guess. Solve exactly when you can. Give every body part its own clock and
its own reason. Integrate physics instead of easing it. And remember her
wings are her face.**
