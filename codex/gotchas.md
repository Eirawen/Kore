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
