# Gotchas — Non-Obvious Pitfalls for Rigging & Animation

Read this before touching the pipeline. Every item here cost hours.

## Rigging

### 1. Apply mesh transforms BEFORE creating the armature
The glTF importer puts a 90° X rotation on the mesh as an OBJECT TRANSFORM. If you create the armature without applying this, bones are in a different coordinate space than the mesh vertices. They look offset by ~10cm in all directions.
**Fix:** `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` on the mesh, then create armature at `(0, 0, 0)`.

### 2. Bone chain must go body→foot, not foot→body
The medial axis traces from endpoints (feet) inward (body). If you build bones in this order, the foot is the PARENT and the body is the CHILD. Rotating the femur moves the body instead of the foot.
**Fix:** Reverse the joints array before creating bones: `joints[::-1]`.

### 3. Medial axis resolution tradeoff
Higher voxel resolution = more precise centerlines BUT noisier skeleton with more spurious branches that fragment the trace. 0.001m gives sub-mm precision but the topology breaks. 0.012m gives stable topology but ~1cm precision.
**Fix:** Multi-resolution. Coarse (0.012m) for topology, fine (0.003m) for centerline refinement.

### 4. Triangle soup voxelization
Meshy meshes are non-manifold triangle soup. Blender's auto-weight painting (ARMATURE_AUTO) will FAIL with "Bone Heat Weighting: failed to find solution." Don't use it.
**Fix:** Custom proximity or physics-based weights via ARMATURE_NAME + manual vertex group assignment.

## Weights

### 5. Branch segmentation, not bone proximity
NEVER use bone proximity alone for body-part assignment. The abdomen bone is closer to rear leg vertices than leg bones are. Body-priority heuristics (multipliers, hard radii) are band-aids that break in new ways.
**Fix:** Two-layer weights. Layer 1: assign vertices to body parts using medial axis branch PATHS (full centerlines, not bone positions). Layer 2: rigid-plate weighting within each body part.

### 6. Body-blend check goes on the BODY end
After reversing the bone chain, `chain_idx == 0` is the body end (coxa) and `chain_idx == len(chain)-1` is the foot end. The body-blend check must use `chain_idx == 0` and `best_t < blend_t`, NOT `chain_idx == len(chain)-1` and `best_t > (1-blend_t)`. Getting this wrong anchors all foot vertices to the cephalothorax.

### 7. Abdomen is a "body" bone for weight purposes
When doing branch segmentation, vertices closest to the abdomen branch should be assigned to group "body", not to a separate "abdomen" group. Otherwise they might not get the body-priority treatment.

## Animation

### 8. rotation_quaternion is in BONE-LOCAL space
`PoseBone.rotation_quaternion` is interpreted in bone-local space, not armature space. If you compute the rotation axis in armature space and set it as a quaternion, the bone rotates around a wrong axis. Legs splay sideways instead of lifting.
**Fix:** Transform the desired rotation axis to bone-local space: `bone.matrix_local.to_3x3().inverted() @ armature_space_axis`.

### 9. Euler rotation_euler uses GLOBAL axes
The `set_rot(rx, ry, rz)` helper with `rotation_mode = 'XYZ'` rotates around global axes. Every leg points in a different direction, so global X produces different motion for each leg.
**Fix:** Use quaternion rotation around computed bone-local axes instead of Euler angles.

### 10. Blender 5.1 broke action.fcurves
`Action.fcurves` no longer exists in Blender 5.1. FCurves are now at `action.layers[].strips[].channelbags[].fcurves`. The Bezier smoothing code needs to handle both APIs.

### 11. NEVER mix rotation_euler and rotation_quaternion across actions
(From Fable's review) `animate_feel.py` uses `rotation_euler` (XYZ mode) while walk/threat use `rotation_quaternion`. The rotation mode is per-posebone STATE, not per-action. Leftover euler channels fight quaternion channels when actions get blended or NLA-layered (which game export does). Pick quaternions everywhere.
**Fix:** Port feel.py to quaternion rotation. 20 minutes now vs a haunted-rig afternoon later.

## Pipeline

### 12. WSL→Windows environment variables are unreliable
`export KORE_ANIMATION=threat` in WSL doesn't reliably reach Windows Blender via `--background --python`. The animation defaults to "walk."
**Fix:** Write config to a file (`tools/loop/.render_config`) and read it from the Blender script via UNC path.

### 13. Walk cycles: N groups need ≥(1/N) swing fraction for seamless gait
For any walk cycle with N alternating leg groups, each group's swing phase must cover at least 1/N of the total cycle. Otherwise there are frames where ALL groups are in stance and nothing moves (dead zone).
- 2 groups (alternating tripod): swing ≥ 50%
- 3 groups (wave gait): swing ≥ 33%
- 4 groups: swing ≥ 25%

`N × swing_fraction ≥ 1.0` or the gait has gaps. "Deliberate" feel comes from amplitude and speed, not from spending more time standing still. Standing still reads as broken, not patient.

### 14. Blender headless path format
The `--python` argument to Windows Blender must use Windows UNC paths: `\\wsl.localhost\Ubuntu\path\to\script.py`. WSL paths like `/home/khaled/...` get mangled.
**Fix:** Use `wslpath -w` to convert, or hardcode the UNC prefix.

### 15. KNOWN_FEET_BLENDER is spider-specific (from Fable's review)
The hardcoded foot positions make auto_rig.py a spider-rigger, not a creature-rigger. Generalization: feet = lowest-Z endpoints of the N longest branches, labelable by sign/rank of (x, y). One function away from rigging any creature.

### 16. trace_branch neighbor selection is arbitrary (from Fable's review)
At multi-neighbor voxels, `trace_branch` takes `neighbors[0]`. On thick limb junctions this wanders. Prefer the neighbor most aligned with the current direction (dot product) for deterministic, straighter traces.

### 17. preserveDrawingBuffer for WebGL capture
Playwright page.screenshot() does NOT capture WebGL canvas content. Canvas.toDataURL() works but ONLY with `preserveDrawingBuffer: true` on the WebGLRenderer. Without it, the draw buffer is cleared after presenting.

## Hand Animation (marketplace rig)

### 18. Armature object origin is at the FOREARM STUB, not the wrist
On the cgtrader hand, the armature object origin sits at the lower forearm. Along
local +Z (scale 3.118): wrist ≈ origin+3.1, fist knuckles ≈ +4.0, fingertip ≈ +6.0.
Every staging position you guess is off by ~3 units until measured. **Probe at
runtime; position the origin, not the wrist.** Cost the most time in the cast pass.

### 19. First person = camera sees the BACKS of the hands → yaw-flipped branch
All gather/hold/rest poses must live on the Z≈±172/180 branch (thumbs land
outboard), the same branch the release uses. Authoring on the un-flipped branch
gives palms-to-camera (wrong for FP) and fights the release orientation.

### 20. You cannot teleport between hand orientations — roll through them
A big Z change (gather 172 → release −180) done as a straight interp is an ugly
180° flip. Insert a guide key at the midpoint that supinates/pronates the forearm
(palm-up roll into a chamber; scoop-supinate into a cup). That's what a real wrist
does; it's what makes the transition read as a wrist, not a glitch.

### 21. Blender 5.x removed action.fcurves
FCurves moved to `action.layers[*].strips[*].channelbags[*].fcurves`. Guard with
`hasattr(action, 'fcurves')` and fall back to the layered path. (Also bit the
Bezier-smoothing code on the spider — same fix.)

### 22. Mirror hand needs a normal flip
Left hand = right mesh with scale.x = −1. Negative determinant flips winding →
inside-out render. Flip mesh normals via bmesh after staging (guard on
`matrix_world.determinant() < 0`).

### 23. Casts authored flat read as a sprint — retime for contrast
Uniform keyframe spacing makes a cast feel like a keyframe-to-keyframe rush. Push
spacing into the gather + HOLD, keep the pull→release span short. Retime (remap
frames), don't re-pose. The held beat on the signature pose is where the VFX
forms and the eye reads it — it's the breath of the whole motion.

### 24. Marketplace rig > auto-rig for generic parts
Our medial-axis pipeline is for creatures nobody modeled. For a HAND (or sword,
barrel, generic humanoid), a bought pre-rigged model + ~10 min cleanup (strip
junk, bare material, decimate, rename bones + matching vertex groups) beats
fighting Meshy topology and auto-weights. Meshy for identity, marketplace for
infrastructure.

### 25. Rename bones AND their vertex groups together
The armature modifier binds bone→vertex-group by NAME. Renaming a bone without
renaming its vertex group breaks the bind. Rename both in lockstep.

### 26. FP hands: thumbs must land INBOARD — verify chirality by render
The yaw-flipped FP staging put both thumbs OUTBOARD, i.e. each side showed the
WRONG hand (Khaled caught it by thumb position; the old codex note claiming
"thumbs outboard is correct" was wrong). The fix is an in-place chirality flip
applied uniformly at application time: keep every authored location, negate
euler Y and Z, toggle the scale.x mirror (screen-right = mirrored mesh now).
Pose-bone X-curls are mirror-invariant and pass through. Never trust chirality
reasoning — probe thumb-tip world X vs hand center and LOOK at the render.

### 27. Anisotropic mirror scale SHEARS rotated children
A prop parented under an armature scaled (−S, S, S) inherits the mirror. Any
child rotation that is not axis-aligned gets sheared (world = T·R·S_parent ·
child). Keep prop rotations at 90° multiples (e.g. sword Ry(−90)), or bake the
roll into the mesh data instead of the object transform.

### 28. World-space key authoring beats euler guessing for props
For the sword set, keys are authored as (fist position, forearm dir, blade dir)
and solved to origin+euler at build time (tools/animate_sword.py: solve_key).
Blade dir gets projected ⊥ forearm (rigid hammer grip: blade is ALWAYS ⊥ the
metacarpals — a thrust can never go point-in-line on this rig). Unwrap eulers
key-to-key (mod-360 + the (x+180, 180−y, z+180) equivalent triple) or
interpolation does a 300° flip instead of a wrist roll.

### 29. Seat props in the PROBED fist void, not where you think the palm is
The curled-'grip' fist's enclosed void is at hand-local (0, −0.22, 1.37) —
probed via posed bone positions (tools/probe_fist_void.py). Three blind
guesses missed it; one probe hit it.

### 30. Throwable release = keyed ChildOf influence + scale swap
Real let-go: prop rides ChildOf(hand) with influence keyed 1→0 (CONSTANT) at
the release frame, then flies on its own world-space LINEAR keys. Two traps:
(a) key the scale across the switch — under the constraint the hand's 3.118
multiplies in, in free flight it doesn't (prop shrinks 3× otherwise);
(b) compute the world start analytically from the release key's loc/euler
(T·R·S), no depsgraph needed.

### 31. The forearm-stub egg — avoid stub-at-camera poses
Any pose whose forearm points down-forward aims the CUT END of the forearm
stub at the camera; it renders as a big smooth egg (thrust chambers, riposte
poses, air-seal top hand). Keep forearm dirs near-horizontal or entering from
a frame edge so the stub stays edge-on or cropped.

### 32. Forearm roll is a WORLD-POSE NO-OP under the world-space key solver
When a key is authored as (blade dir, forearm-side hint) and solved to an
object rotation, the forearm-roll channel cannot change the world pose: the
solver pins blade + hint, and the forearm AXIS is invariant under rotation
about itself, so the assembly spin about the blade is fully determined by
(blade, hint). Swept roll_d -125..+44 at the light strike — thumb dir
identical every time. To pronate/supinate the FIST in world space, rotate
the HINT about the blade axis (spins fist + elbow together; wrist flex/dev
shifts thumb-vs-elbow). roll_d only affects internal wrist state + a small
fist-void drift.

### 33. Two sparse object-rotation keys swing an offset fist on a huge arc
The fist sits ~3+ units from the armature origin (gotcha 18). Interpolating
a big object rotation between just two keys sweeps that offset point on a
wild detour — the heavy_rl coil sent the fist to y=-2.3, BEHIND the camera
plane, off a 2-key ready->windup pair whose endpoints both had y≈+0.5.
Probe per-frame fist positions numerically (animate_sword_attacks --probe)
and pin the path with in-between keys; never trust two keys across a large
rotation.

### 14b. hide_render sabotage (the bare-handle night)
A mesh can be visible in the artist's viewport but set `hide_render: True`
(outliner CAMERA icon, distinct from the eye). Headless renders honor
hide_render, not hide_viewport — so the subject silently vanishes from every
render while looking fine to the human. Cost a full night of "why is the
handle bare" camera-blame. **Probe `obj.hide_render` FIRST when a subject is
mysteriously absent from renders.** Also: aim cameras at EVALUATED (posed)
geometry via depsgraph — `bound_box` is rest-pose and lies about posed hands.

## Humanoid posing (succubus arc, 2026-07-25)

### 34. Learn joint axes from the character's OWN animations
Meshy/marketplace bipeds arrive with animation packs. Those clips ARE the
ground truth for the rig's real hinge axes — sample each bone's pose
quaternions across a walk and take the angle-weighted dominant axis
(`dominant_axis()` in tools/animate_coy3.py). Her elbow came back
single-axis at 0.98 consistency. Never trust bone tails/rolls on an
imported rig — the glTF importer invents them (this rig's tails point
5-19 METRES away). Heads are reliable; tails are hallucinated.

### 35. Blender's glTF importer re-bases bones — don't hand-roll retargeting
`rest_gltf⁻¹ ⊗ channel_quat` is NOT enough: the importer invents its own
bone orientations and bakes correction transforms into imported curves.
Hand-rolled transfer produced a systematic per-bone offset (a hunch in
the spine, splay in the arms). Correct method: import the clip GLB into
the target scene and let the SAME importer handle both sides.

### 36. A pose solver without a collision term will tunnel through the body
The coy arm went straight through her chest because the cost function only
knew about wrist-to-target distance. Worse, my "coy elbows tuck" penalty
on lateral elbow offset actively REWARDED the elbow for moving medially —
into the ribcage. I wrote the constraint that caused the defect.
**Fix:** TORSO CLEARANCE PROXY — sample torso-weighted verts into a
(height bin x angular sector -> max radius) profile (breasts included:
they're chest-weighted), then penalise arm sample points inside it.
Penetration went 0.0066 -> 0.0000. Costs no vision tokens.

### 37. MEASURE the hand, don't guess its length
Guessed 0.095 m; measured 0.145 m from 337 hand-weighted verts. A 50%
reach error made a chin touch look geometrically impossible and pushed
the solver into bad configurations. `HAND_LEN = max(|vert - wrist|) *
0.92` over hand-weighted verts. Same for the CHIN target: the lowest
forward head-weighted vertex, not a guess offset from the head bone.

### 38. Fingerless rigs: the coy/covering distinction is one term
24-bone Mixamo bipeds have NO finger bones — the hand is a paddle. A flat
palm anywhere near the face reads as shock/hiding/facepalm. The gesture
only reads coy if the FINGERS POINT UP along the jaw: add
`if hand_dir.z < 0.55: cost += (0.55 - hand_dir.z) * w`.

### 39. Always shoot the acting-arm SIDE view (pose gate)
A 3/4 view is depth-ambiguous: "arm in front of chest" and "arm inside
chest" render nearly identically. The side view makes it undeniable —
the tell is a MISSING ELBOW (forearm emerging from the chest mass with no
elbow projecting outside the ribs). tools/pose_check.py renders 5
diagnostic angles (front / her-left / her-right / top-down-45 / full 3-4)
into one small strip. Read that ONE strip, never a 12-cell 2MP grid.

### 40. Blender compute is free; LOOKING is what costs
Token cost lives in reading images, not in rendering them. So: iterate on
NUMBERS (solver + clearance report), render freely, read one small strip,
and hand the mp4 to the human — human vision is better than mine and
costs nothing. Multi-start the solver (4 seeds): the chest-tunnel pose was
a local minimum that a single start walked straight into.

### 41. Coy is approach-avoidance — the body turns AWAY, the face comes BACK
The single biggest miss in my first coy pass: I only tilted her head into
her hand. No conflict = no flirtation. The gesture requires opposition —
torso twisted away from the audience (Z on Hips/Spine chain), face yawed
back toward them, chin tucked. Verified numerically: gaze·audience goes
0.41 (flinch away) -> 0.90 (looked back). Supporting vocabulary that all
reads: knees converged (uchimata — verify the sign by MEASURING the knee
gap, don't guess it), spine curled forward (making herself small), the
raised-arm shoulder lifted to MEET the hand (the bashful squeeze), and the
idle arm given a job (crossing the body — an idle arm kills a pose).

### 42. Head orientation: compute a LOOK-AT; and the conjugation that kills
### stale rest frames
Guessed head eulers hid her face. Instead build a desired facing
(`gaze_dir(yaw_vs_audience, pitch_down)`) and solve exactly:
`D = current_fwd.rotation_difference(desired)`. To apply an ARMATURE-space
rotation to a bone whose ancestors are already posed:
    pose = M0⁻¹ · D · M0    (M0 = pb.matrix.to_quaternion() at identity pose)
This uses the bone's LIVE world matrix, so it never goes stale the way
`matrix_local` (rest frame) does — that staleness was the v1/v2 body
horror. Split the turn neck/head (~38/62) so it reads as a curve, not a
snapped-on head. Then roll about the final forward for the tilt.
**And: pitch down ~15 deg, not 26.** At 26 the hair and tilt hide her
face entirely; coy needs the face VISIBLE. Buy the shyness with ROLL
(head tilt), which costs you nothing.

### 43. One-sided constraints get maximized — use BANDS
`if hand_dir.z < 0.55: penalize` let the solver stand the paddle straight
up (0.92) into a wall over her mouth. A floor is not a target. Bands:
`(0.42, 0.66)` penalizes both directions and lands the hand angled ALONG
the jaw. General rule: any constraint you write as an inequality, ask what
the solver does if it maximizes that term — it will.

## Jump / locomotion (succubus, 2026-07-25)

### 44. Meshy auto-rigs weight WINGS to the nearest LIMB
Her wings were one 330-vert island weighted to `LeftArm=118, RightArm=115`
— so every arm gesture dragged her wings around (that flat "sail" in the
early coy renders was a wing being hauled by an arm). Probe for it: find
connected islands (bmesh flood fill), then look for one spanning both x
signs at shoulder height. **Fix:** add bones parented to `Spine`, re-weight
the island to them exclusively (`vg.remove()` from every old group first),
2 bones per wing with a smoothstep falloff along the span. Payoff beyond
posing: rigged wings can be driven by the engine's SPRING BONE system as
free secondary motion, forever.

### 45. EXACT analytic IK beats a solver, and more DOF makes search WORSE
Foot-planting by coordinate descent: 3 fixed axes -> 6cm floor sink;
5 DOF -> 2cm; **7 DOF -> 8cm.** Adding freedom gave the local optimizer a
worse basin to fall into. A leg is a TWO-BONE CHAIN, so solve it in closed
form and get zero residual with no search:
1. `d = |ankle_target - hip|`, clamp to `[|a-b|, a+b]`
2. law of cosines for the hip angle: `cos = (a²+d²-b²)/(2ad)`
3. knee = `hip + a*(cos(al)*along + sin(al)*perp)`, where `perp` is the
   POLE direction (she faces -Y, so the knee leads -Y) orthogonalised
   against `along`
4. aim each bone at its target direction with the conjugation
   `pose = M0⁻¹ · D · M0` off the bone's LIVE matrix
Result: `foot_error 0.0000m`, floor penetration 6cm -> **1.5mm**.
Reusable for every crouch, landing, stair and walk this rig will ever do.

### 46. Flat foot vs TOE-OFF are different IK problems
Flat contact: target the ankle AND the toe (over-determined on purpose —
it pins the foot's orientation too). Toe-off: target the toe ONLY and park
the ankle one foot-length up-and-behind it (`toe + FOOT_LEN *
normalize((0, 0.32, 1))`) — that IS plantar flexion, and it's what makes a
jump read as a push instead of a levitation. Toes are last to leave the
ground and first to touch it.

### 47. The root curve must PASS THROUGH the height each plant was solved at
I solved the toe-off plant at hips −6cm but the root curve was at −3.4cm
on that frame, so the foot was planted for a pose she wasn't in (4cm
sink). Any IK-solved contact pose needs a matching root keyframe at the
exact solve height.

### 48. Flight height is COMPUTED, not eased
`z(t) = v0*t − g*t²/2`, `v0 = sqrt(2*g*h)`, keyed every 2 frames with AUTO
handles. A symmetric bezier ease floats at the apex; real gravity gives
fast-rise / hang / fast-fall for free. Verified by measuring the mesh's
lowest vertex per frame: 0.000 on the ground -> **+0.468 at apex** (41cm of
hip rise for a requested 34cm ballistic + 7cm takeoff extension). Always
audit "does she actually leave the floor" against mesh geometry, not the
root value.

### 49. A hover should be SIMULATED, and the sag between beats is the point
A smooth hover reads as levitation. A hover that SAGS BETWEEN BEATS reads
as WORK — each downstroke arrests the fall and buys back altitude, gravity
takes it during the recovery stroke. So integrate instead of keying:
```
v -= g*dt each step;  v += FLAP_LIFT at each downstroke
```
Set `FLAP_LIFT` deliberately BELOW `g * flap_period` (1.52 vs 1.80 m/s) and
she loses a little every beat — barely winning, then losing. The measured
profile is the characterisation:
```
rise  7 -> 21.5 -> 31.6 -> 37.4 -> 38.8      (ballistic, decelerating)
flap1 43.5 -> 46.3 -> 44.8    up then SAG
flap2 49.0 -> 48.9 -> 46.9    up then SAG
flap3 48.2 -> 45.2 -> 42.8    up then SAG
fall  41.2 -> 35.1 -> 24.8 -> 10.0           (gravity wins)
```
Two things fall out free: **CAUSALITY** — fire the impulse mid-downstroke
(flap_f + 2) so she starts rising AFTER the wings move; force leads
position, which is what makes the lift read as *caused by* the flapping.
And the **LANDING FRAME becomes an OUTPUT** of the sim, not a number you
pick — then key the landing poses at whatever frame it returns.
Small wings must beat FAST (11-frame period here). Give the stroke a
loaded top (WING_UP) to beat down from and a partly-folded recovery
(sheds drag, real flapping). Let the legs DANGLE and lag the bob — they're
along for the ride, not helping.

### 50. Wing scale is a PARAMETER, not a modelling job
Because the wing surgery finds the island by geometry and places the bones
from the island's *measured* extents, growing the wings is one number:
scale each side's verts away from its attachment anchor BEFORE bone
placement, then re-measure. Bones and weights re-derive automatically.
Span/height scale fully; thickness only ~30% (a wing is a membrane).
Verts at the anchor barely move, so the midline seam across her back holds.
Measured silhouettes at the power stroke: 1.0x = 1.04 x 1.57 m,
1.7x = 1.16 x 1.77, 2.4x = 1.63 x 1.99.
(And gotcha #11 bites again: WSL env vars do NOT reach Windows Blender.
Pass the scale in a CONFIG FILE read over the UNC path.)

### 51. Grafting a generated asset onto a rigged character
Meshy wing pair -> her back. The pattern generalises to any prop/appendage:
- **Probe islands first**, then MEASURE before declaring a constraint. I
  claimed a shared membrane meant the wings couldn't be split. Khaled
  pushed back; the measurement said he was right (see #53). Assertions
  about geometry are cheap to test — test them.
- **Keep it a SEPARATE mesh object sharing the armature.** Not joined into
  the body: no vertex-index disruption, no weight contamination, and it's
  how game characters are actually built (submeshes).
- **Anchor-relative transform.** Find the asset's attachment zone (verts
  within ~8% of the span of its midline), then scale/rotate about THAT
  point and translate the anchor onto the target bone. The attachment
  never drifts as you re-scale.
- **Derive bones from the mounted geometry**, sampling the asset's own
  shape at span fractions (0.42 / 0.78 / 1.0) so the chain follows the
  membrane's arc instead of a straight line.
- Attach at the anatomically right place: bat wings mount at the SCAPULA,
  lower than the shoulder joint.

### 52. Generated wings arrive FURLED — spread is a POSE, not geometry
The asset's bbox was 1:1 (as tall as wide) because the wings were
generated raised/furled, not spread. Scaling for span made them tower
above her head; scaling for height made them narrow. Do NOT fix this by
non-uniform scaling (it distorts the membrane) — **rig it furled and open
it with the root bones.** The spread then costs nothing and is animatable,
which the flap needs anyway.
And probe the opening axis rather than guessing it (same method as the
railgun's GUN_ROLL): measured span per axis/sign —
  X+-40: 0.860 (no change)   Y+40: **1.373**   Y-40: 0.919
  Z+40: 0.793                Z-40: 1.177 (sweeps back, flattens depth)
+Y opens; my authored sign was inverted, which folded the wings across her
head. Z- is the secondary sweep-back.

### 53. Measure a constraint before asserting it (the split that was fine)
I told Khaled the wings couldn't be split into left/right because the
membrane was one connected sheet and the seam would tear. He asked why,
which is the correct response to an unmeasured claim. The topology probe:
```
straddle faces  39 of 4308  (0.9%)
edges crossing  39 of 6484
verts already ON x=0          17
bridge z=[-0.500,-0.055]  = the bottom 44.5% of the asset
```
So the two wings are joined only by the V-notch at the BOTTOM CENTRE —
which, once mounted, sits on her mid-back where her own torso occludes it.
The concern was real in principle (coincident boundary verts diverge if the
sides get different transforms) and negligible in this geometry.

`bmesh.ops.bisect_plane(clear_inner=True)` per side cuts the straddling
faces exactly at the plane: WingsL 1146v / WingsR 1143v, total 2289 (UP
from 2217 — the cut adds boundary verts, which is the sign it worked).
No dual-root midline weighting needed afterwards.

**What splitting buys, all of which needs independent wings:** phase offset
between beats (real flapping is never symmetric), differential angle for
banking, an asymmetric rest pose (`ASYM`, a few degrees — perfect symmetry
is the manufactured look), and a torn/damaged wing for a character who
fights in dungeons.

### 54. SWINGING a bone chain is not EXTENDING a wing (measure height, not just span)
Khaled: *"I hypothesize you're rotating around the wrong axis somehow. When
you rotate the wings you're rotating them vertically, so to speak, rather
than extending them out."* He was right, and the tell was a metric I wasn't
watching — **wing HEIGHT**:

| spread strategy | span | wing height |
|---|---|---|
| furled | 1.060 | 1.062 |
| A: same-sign +Y on all 3 bones (swing) | 1.695 | **0.481** |
| B: aim each bone outward (UNFOLD) | 1.670 | **1.058** |
| C: rotate about vertical (sweep only) | 1.411 | 1.062 |

A and B reach the SAME span. A gets there by tipping the wing over into a
horizontal plane — it gains width by **lying down**, losing 55% of its
vertical presence, and reads as a flat cape. Applying one rotation
direction to a head-to-tail chain swings it like a rigid plank.

**A real wing spreads by UNFOLDING its joints.** Use `aim_bone` (the
`M0⁻¹·D·M0` live-matrix conjugation) to point every bone in the chain along
one outward direction — that STRAIGHTENS the furled arc, so span grows out
of the chain's own length and the membrane stays standing. Apply elevation
AFTER extension, at the root only: that's the order a real wing does it in.

**Lesson beyond wings: when a transform is supposed to EXTEND something,
audit a dimension it should PRESERVE.** Span alone said A worked. Span plus
height said A was flattening. One extra measured number caught it.

### 55. An idle must be true at EVERY frame — never a transformation
A looping animation has no beginning, so any clip that travels from state A
to state B reads as a repeating *event*, not an idle. The water elemental's
first vortex went from intact legs (phase 0) to shredded (phase 3/4) and
back forever — the player watches her legs dissolve and regrow on loop.
**Fix:** separate the SHAPE from the MOTION. Bake the characteristic
deformation as a fixed offset that is always on (she IS a vortex), then
animate only bounded variation on top of it.

### 56. Accumulating rotation shears a mesh apart; use a travelling wave
Any rotation whose magnitude varies across space AND grows with time
generates shear that increases without bound. `theta += phase * f(position)`
will always tear geometry, whether f varies by radius ("spin the strands"),
by height ("spin only at the bottom"), or by angle ("spin only one half").
Real fluid escapes this because it continuously advects; a fixed-topology
mesh cannot.
**Fix:** a bounded azimuthal wave — `theta += A * sin(phase - theta0*k +
h*p)`. It reads as water turning, but amplitude is capped by A, so it can
never accumulate. Bonus: a rigid spin also ROTATES any deliberate asymmetry
away from where you placed it (the calm zone orbits off the character's arm
within a second). A travelling wave keeps the asymmetry anchored.

### 57. Weight diffusion beats per-vertex nearest-bone assignment
Hard-partitioning verts to bone sets (trunk->column bones, arm->arm bones)
creates a weight CLIFF at every seam: two verts sharing an edge get disjoint
weights and the edge stretches without limit (measured 61x on the water
elemental). **Fix:** initial inverse-square weights over the K nearest
bones, then diffuse over the mesh graph (`w = 0.45*w + 0.55*mean(neighbours)`,
~12 iterations). Enforces continuity across every seam automatically.
1-2 bones/vert -> 4.79, worst edge ratio 61.38 -> 3.80, and sway went to
ZERO bad edges. Audit with edge-length ratio vs rest; it costs no vision.

### 58. `bpy.data.actions.new()` does NOT overwrite — fake users pile up
An action saved with `use_fake_user=True` survives the next run, so
`actions.new('waveform')` silently returns **`waveform.001`**, then `.002`,
`.003`… Every rebuild lands in a fresh orphan while the ORIGINAL keeps
playing, so renders look unchanged and you conclude your edit "didn't take"
— then chase a phantom bug in perfectly correct code. I burned three
debugging rounds on this and found 31 orphaned actions in one file.

**Tells:** the render is byte-identical after a real change; the action's
fcurve count doesn't match what you keyed (`keyframe_insert` returns True
and the values are right, but a later inspection of `actions['name']` shows
them missing).

**Fix:** purge before creating.
```python
for old in [x for x in bpy.data.actions
            if x.name == name or x.name.startswith(name + '.')]:
    old.use_fake_user = False
    bpy.data.actions.remove(old)
a = bpy.data.actions.new(name)
```
Generalises to every `bpy.data.*.new()` — meshes, materials, armatures all
name-suffix on collision rather than replacing.

### 59. A humanoid cannot ROTATE into a non-humanoid
Waveform v1 read as "a person hunched over a snowmobile" because I built a
dissolve out of bone rotations. **Rotation preserves proportion**, so the
figure survives every pose you put it in: the head still reads at the front,
the height stays, limbs stick out like handlebars — and a readable head is
the single strongest anti-wave cue there is.

**To stop being a body you must destroy the PROPORTIONS — squash and
stretch.** Object scale IS the dissolve (height 0.28, travel 2.55, width
1.18), plus folding the upper column hard so the head sinks INTO the mass.
Compensate the squash with a downward offset (`base_z * (1 - sz)`) or she
floats off the floor.

This is the slime lesson from the very first animation conversation: you do
not rig a liquid, you deform it.

### 60. For a liquid/amorphous creature, the base is NOT a stand
Weighting bends by height (`0.25 + 0.75*h`) is correct for a BIPED — the
feet are planted and the torso swings. Apply it to a creature whose lower
body IS its mass (water, slime, a swarm) and you build a **bobblehead**: the
base sits rigid while the figure wobbles on top of it, and every clip reads
as a figurine on a plinth.

Khaled spotted it across the whole moveset at once — "a figurine on a stand,
that bobbles around."

**The conceptual error is animating a woman STANDING ON a base.** The pool at
her feet is not furniture, it is the heaviest part of her body. **In a fluid,
mass leads from the BOTTOM** — a wave is driven by what is underneath, not by
the tip.

Fix, applied to every clip:
- raise the weight floor (0.25 → 0.55) so the base carries real motion
- the ROOT translates laterally with the lean/orbit: water shifts its whole
  mass, it does not pivot about a fixed foot
- give `col0`/`col1` an explicit slosh that LAGS the top (the base arrives
  late, then keeps going)

### 61. Shader colour constants are LINEAR; hex on the CPU side is sRGB
A shader's `vec3(0.30, 0.52, 0.68)` is a LINEAR colour. Reading those numbers
and writing `new THREE.Color('#4d85ad')` applies the darkening TWICE, because
`THREE.Color` treats hex as sRGB and converts it TO linear on the way in.
Luminous teal comes out as royal navy and the cause is invisible.
**Fix:** convert properly — linear→sRGB is
`c <= 0.0031308 ? 12.92c : 1.055·c^(1/2.4) − 0.055`. For the above: **#95bfd7**.
Khaled spotted it by eye without knowing it was a gamma error; he just knew
the blue was wrong.

### 62. Additive shells SATURATE — density is not the knob
Stacking three additive layers at 0.5+ each clips past white, and everything
reads as cut glass no matter how you tune opacity. Sweeping density will not
fix it because density is not what is broken. **Fix:** much lower per-layer
opacity AND a dimmer, cooler source colour. Also check the emissive gain — a
1.6× multiplier on a near-white colour is a lightbulb, not a haze.

### 63. Colour uniforms must be `.set()`, never overwritten
`mat.uniforms.uFoo.value = '#aabbcc'` replaces a `THREE.Color` with a String
and the shader dies at draw time with no useful error. Any generic uniform
setter needs to be colour-aware:
`if (u.value && u.value.isColor) u.value.set(v); else u.value = v;`

### 64. A GLSL uniform validator must be STAGE-AWARE — and just compile it
I wrote a regex validator that checked declarations against vertex and
fragment uniforms COMBINED, so a vertex-only uniform used in the fragment
passed clean. The shader then failed to compile and the character rendered as
literally nothing. "Fixing" it produced a false POSITIVE, because the regex
found the uniform's name inside the comment I had written explaining the bug.
**The real validator was one command away the whole time**: the GPU compiles
it and reports `ERROR: 0:1808: 'uWater' : undeclared identifier`. Precise,
authoritative, free. Measure the thing; do not measure a proxy for the thing.

### 65. Hardcoded constants hide until something monochrome stands next to them
The refraction tint was a hardcoded water-blue inside the shader for the whole
project, leaking cyan into every non-water preset. Nothing exposed it until an
INK preset, because ink has no blue for it to hide in. **Any constant that
describes a look, rather than physics, should be a uniform from the start.**
