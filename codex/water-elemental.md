# The Water Elemental — rigging and driving a liquid character

The Azure Tide Spirit, floor-1 boss of Slayer 2. You cannot hurt her with
melee, spells barely work, fire loses to specific heat, water magic feeds
her, lightning just electrifies her. **You fight her with a bucket** — scoop
water out, carry it to the gutter, repeat. See `eldritch-bosses.md`.

Built 2026-07-26. Read `humanoid-animation.md` first; this is the liquid
addendum.

## 1. Read the mesh before designing the rig

Meshy output, dynamically posed (NOT A-pose — and that's correct here: her
one arm is already in clear air, she has no legs to separate, and nothing
about her will ever come from a humanoid animation pack).

**glTF lied about the topology.** It reported 640 islands. glTF stores one
vertex per unique (position, normal, UV) triple, so every texture seam
duplicates vertices and a connected mesh imports as confetti.
`remove_doubles(1e-5)` -> 4365 verts becomes 2240, and **640 islands becomes
24**. Always merge-test before believing an island count.

Real structure:
| island | verts | what |
|---|---|---|
| isl0 | 1209 (54%) | body: torso, gown, base, AND the arm |
| isl1 | 502 (22%) | hair + its trailing ribbons (z 0.50 down to -0.24) |
| 22 more | 529 | loose splash shards — no bones, they just ride |

**Her anatomy is legible from a radius-per-height profile alone:**
```
z 0.40..0.50  r 0.065   head
z 0.30..0.40  r 0.072   neck
z 0.20..0.30  r 0.150 (max 0.315)   shoulders — the ARM branches here
z -0.20..0.20 r 0.12-0.15  gown column (waist = narrowest, r 0.122)
z -0.40..-0.20 r 0.180   the pool flares
```
Normalised to exactly 1.0 tall; real scale is a design decision (she should
LOOM — 2.2-2.5m — because the fight is manual labour at the feet of
something enormous and indifferent).

## 2. Find limbs by GEODESIC distance, never by radius

Radius gating ("anything far from the axis is arm") produced a centreline
whose y flipped +0.081 -> -0.119 between adjacent samples. Limbs don't
zigzag; it was catching ribbons that merely happened to be far out.

Walk the mesh instead (Dijkstra over edges) from the extremity inward. A
ribbon hanging 1cm from her fingertip is spatially adjacent but half a metre
away *along the surface*. Then watch the **spread** (mean distance of a
band's verts from their own centroid):
```
0.021 0.028 0.023 0.039   <- tight: a tube, i.e. a limb
0.068 0.089               <- doubled: you have reached the body
```
The shoulder is wherever "tube" stops being true. Nobody tells it where the
joint is; **the mesh reports its own anatomy.** Same technique as the spider
legs.

Result: shoulder (0.011,-0.068,0.332) -> elbow (0.079,-0.054,0.247, hangs
BELOW the shoulder) -> tip (0.223,-0.186,0.271).

## 3. Rig: 14 bones, and that is deliberate

7 column + 2 arm + 4 hair (hosted: arm on the shoulder-height column bone,
hair on the top one). **She is mostly shader; the skeleton only does
deliberate motion** — sway, locomotion lag, slow arm gestures.

- **Hair chain from Z-BANDS, not geodesic bands.** Geodesic centroids
  zigzag at max distance because the band spans both sides of her body and
  the centroid lands in mid-air between them. Z-bands are monotonically
  descending by construction (0.500 -> 0.316 -> 0.132 -> -0.052 -> -0.236).
- **Weight diffusion, not nearest-bone assignment** (gotcha 57). Hard
  partitions create a cliff at every seam.
- Audit with edge-length ratio vs rest — costs no vision:
  `sway 13.75 -> 1.83 (0 bad edges), hair 61.38 -> 3.80`.

## 4. THE VORTEX DRIVER — one float compiles her whole presence

Khaled's reframe: she is not "visually busy", she is **a vortex** — those
strands are water rotating around her. And draining her should take her from
gushing vortex to sad stream **without deforming the mesh at the scoop
point** (that would look wrong and be much harder).

So the strands are **not bones**. A vortex is a continuous FIELD: rotate
every vertex about her axis by an amount growing with radius and height.
That works across ALL islands at once, which matters because her ribbons are
split between the body island and the hair island — no bone chain could ever
unify them. Bones do deliberate motion; the shader does the vortex.

**The physical story is spin vs gravity.** At full water, centrifugal force
throws the strands outward horizontal. As the spin drains, gravity wins and
the same strands hang. The player causes it.

```
water -> churn amplitude · centrifugal flare · gravity droop · column
         height · slump · spin rate · wave amplitude · asymmetry
```

### 4a. Split CHURN (shape) from MOTION — gotcha 55
First version travelled from intact legs (phase 0) to shredded (phase 3/4)
and back, forever: the player watches her legs dissolve and regrow. **An
idle has no beginning; it must be true at every frame.** Bake the
characteristic deformation as a fixed always-on offset (she IS a vortex),
then animate only bounded variation on top.

### 4b. Use a TRAVELLING WAVE, never accumulating rotation — gotcha 56
`theta += phase * f(position)` tears geometry whenever f varies in space,
whether by radius, height, or angle — the difference grows without bound.
Real fluid escapes this by continuously advecting; a fixed mesh cannot.
```
theta += WAVE_AMP * sin(phase - theta0*WAVE_K + h*WAVE_H)
```
Bounded by construction. **And it keeps deliberate asymmetry anchored** — a
rigid spin rotates the calm zone away from her arm within a second.

### 4c. Two motion zones (vertical)
Vortex below the waist, gentle lateral DRIFT above, so the figure stays
readable. The concept dies if the water hides the woman: she'd read as a
pile of ribbons with a head. It also fixes attack telegraphs — a clear upper
body means her torso and arm can wind up legibly while the vortex below is
pure spectacle. Her waist is already the narrowest point of the column
(h=0.35), so it is the natural seam. Shipped: `VTX_LO/HI = 0.14 / 0.46`.

### 4d. Asymmetry (horizontal) — the thing that made it sing
Perfect radial symmetry reads as manufactured. Angular mask centred on the
ARM direction (`CALM_DIR = -0.695 rad`, computed from the fingertip, not
eyeballed), chaos peaking opposite, `CHAOS_FLOOR = 0.30` so the calm side
still lives. It scales churn, flare AND wobble together, so the two halves
differ in shape, spread and liveliness at once — not just one of the three.
One half shatters into shards; the other carries a single coherent sheet,
and her arm is on the coherent side.

### 4e. The beat nobody designed
Churn scales with `water`, so **draining her UN-churns her**. Full power: a
raging vortex with no legs. Drained: just a woman standing in a puddle. That
is the manifesto beat (`the-real-game.md`) delivered by one multiplication —
it feels like a victory until you catch your breath and see what you
actually beat.

Shipped constants (`tools/vortex_anim.py`):
```
BASE_CHURN 4.60   TWIST 3.10   FLARE 0.55   DROOP 0.66   SQUAT 0.46
SLUMP 0.10   WOBBLE 0.30   WAVE_AMP 0.85   WAVE_K 2.0   WAVE_H 1.8
VTX_LO/HI 0.14/0.46   CALM_DIR -0.695   CHAOS_FLOOR 0.30
```

## 5. Open
- Port the driver to a `water_vortex` material so it runs off a uniform
  in-engine instead of Python.
- GLIDE locomotion: no legs means no gait, no foot plants, no IK. She slides,
  and what sells liquid is LAG — base leads, torso trails, head trails more,
  ribbons furthest; stopping overshoots and settles. Simulate it (integrate,
  don't ease). Plus SURGE: collapse to a low fast wave, travel, re-form.
- Subdivide the body (1209 verts is faceted for something that must sag).
- Set real scale.
- Moveset should be WHOLE-BODY, not limb-based — her silhouette is too busy
  for an arm swing to telegraph.

---

# 6. THE VFX LAYER (2026-07-27)

## 6a. Her skin — `water_elemental` material

Inherits `water_orb`'s liquid vocabulary (thickness colour/opacity via
NdotV, Fresnel rim, fake refraction, detail ripple) and replaces its
projectile deformation with the vortex driver. **One field drives geometry
AND shading:** the vertex stage computes churn authority (strand factor x
height zone x angular asymmetry) and hands it over as `vTurb`, which drives
FOAM. She froths where she is violent, stays glassy where she is calm, and
it stays true as she drains because both read `uWater`. No second authoring
pass, ever.

## 6b. THE BUG THAT BIT TWICE — scale-relative or nothing

Porting the Blender driver, I re-derived the strand radii from the mesh
bounds (`R*0.17 / R*0.52`) instead of carrying over the proven constants
(0.085 / 0.26 on R=0.257). Half the correct values, so her TORSO was
classified as a loose strand: as she drained, her body drooped like a ribbon
and stretched triangles into huge opaque grey sheets. **Invisible at full
water**, because droop and squat are zero there.

Then I did it AGAIN with the mist shells — standoffs of 0.06/0.15/0.27
against a character whose entire radius is 0.26, so the outer shell more
than doubled her width and three additive layers buried her.

**LAW: when porting a proven driver, port its CONSTANTS. Re-derivation bites
you away from the operating point you tuned at — which is exactly where you
are not looking.** Everything downstream now READS the material's uniforms
rather than keeping copies.

## 6c. Particles — `WaterSheddingVFX`

Bridge principle: every particle is born ON her surface; one spawned in air
is confetti. Velocity = radial fling + `tangential` swirl, which is what a
vortex does to water it cannot hold. Spawn angles are **rejection-sampled
against the shader's own chaos mask**, so droplets can only leave from water
that is actually moving. Rate scales with `uWater` SQUARED — she looks spent
well before she is empty.

Three iterations of what a droplet IS:
1. **Untextured → motes of light.** The default sprite is a soft white
   radial gradient: bright centre, shapeless. That is a spark. A droplet is
   the INVERSE — clear core (you look through water), bright RIM (a curved
   surface bends light at you at its silhouette), one off-centre glint.
2. **Textured → Nickelodeon bubbles.** A hard bright ring plus a hard glint
   is a SOAP BUBBLE. Softened the rim, dimmed the glint.
3. **Round → suspended.** Circles read as floating no matter the texture. A
   droplet in motion is a STREAK. Fable's velocity stretch (particles-v2)
   fixed it: `stretch 1.40 / stretchMax 3.5 / stretchTaper 0.45`. Note the
   proposed 0.35 would have given only +58% at my ~1.65 spawn speed — always
   compute the stretch you need from your actual speeds. Bonus: it keys off
   LIVE speed, so a droplet goes round at its apex and re-stretches as
   gravity takes it. Free physics.

## 6d. The aura — `water_mist_shell`, and WHY it is not particles

Khaled wanted the Morphling look: hundreds of specks, constantly gushing.
Particles plateau — the pool is preallocated (an InstancedMesh instance
buffer sized at construction) and every speck costs a CPU integration step.
**Same lesson as the vortex: a continuum wants a FIELD, not thousands of
objects faking one.** The shell samples fbm per FRAGMENT, so the speck count
is bounded by screen area, not by any pool.

- It **shares `water_elemental`'s vertex stage verbatim** (extracted at build
  time), then inflates along the normal — so it can never drift out of sync
  with the body it wraps, however the vortex is retuned.
- Density = grain x view-angle gate (a shell is thickest at the SILHOUETTE,
  which is where the reference is densest) x chaos mask x `uWater`.
- The field advects down her spine AND around it, so the haze curls in
  lockstep with the vortex rather than on its own clock.
- **THREE NESTED SHELLS** with decorrelated noise offsets at 7/17/28% of her
  radius. One thin shell reads as frost ON her skin; a stack reads as a
  cloud AROUND her. Fur/cloud shell technique, still pure fragment work.

**GRAIN vs SMOKE.** High frequency + a HARD threshold gives isolated specks;
low frequency + a soft threshold gives connected veils, i.e. smoke. My first
pass built smoke and called it spray. A second decorrelated sample punches
holes so grains stay separated. Swept 28/38/48/62 → **38**.

## 6e. The overture nobody authored

Density reads `uWater`, so the haze thins BEFORE the ribbons strip. At 10%
water she is bare while her ribbons remain: **first her atmosphere dies,
then her wardrobe.** (Fable's catch.) Two systems sharing one float produced
a damage-state sequence neither of us designed.

## 6f. Division of labour

```
shell shader -> the continuous haze (thousands of specks, free)
particles    -> coarse readable elements: droplets, scoop burst, base froth
bones        -> deliberate motion: sway, gesture, locomotion lag
```

## 6g. Files
```
crescent engine/shaders/materials/water_elemental.js      her skin
crescent engine/shaders/materials/water_mist_shell.js     the aura
crescent engine/WaterSheddingVFX.js                       droplets + scoop
crescent tools/water_elemental_test.html                  harness
Kore tools/vfx_capture/capture_water.js                   capture driver
Kore tools/vfx_capture/sweep_shell.js                     parameter sweeps
Kore tools/subdivide_water.py                             2240 -> 42021 verts
assets/models/creatures/water_elemental_sub.glb           the shipped mesh
```

## 6h. Open
- Wet trail (needs glide locomotion first — a trail needs her moving)
- The scoop FLINCH: a pulse travelling through her body away from the
  bucket, so she reacts without denting her silhouette
- Glide + surge locomotion (base leads, head trails, overshoot on stop)
- Real scale (she is normalised to 1.0; she should LOOM, 2.2-2.5m)

---

# 7. THE MOVESET (2026-07-28)

Seven clips on the 14-bone rig (arm extended to arm0 → arm1 → **arm_hand**;
two bones could not sell a snap, and a circling arm reads through WHERE THE
HAND POINTS). Event map: `Kore/assets/water_events.json`.

## 7a. THE LAW THIS ARC PROVED: the body sells it, the arm aims it

I flagged early that her silhouette is too busy for a limb gesture to
telegraph — then built four arm-based attacks anyway. v1 of `atk_wave_rise`
proved it: all a viewer reads is a lean and some hair. The arm is buried in
ribbons.

**Fix: the COLUMN commits hard enough that the SILHOUETTE changes, and the
arm rides on top as the precise origin the VFX spawns from.** Column lean on
wave_rise went from ±8° to −32°/+40°. On the torrents the whole upper body
ORBITS with the arm, so the telegraph is a moving MASS, readable at any
distance.

Applies to any creature whose outline is noisy. Silhouette is the only
channel that survives clutter.

## 7b. Clips

| clip | f | what |
|---|---|---|
| `glide` | 60 loop | lag cascade: base leads, head trails, hair furthest. No legs = no gait, no plants, no IK. Root translation is the game's. |
| `atk_wave_rise` | 84 | deep COIL (rear-back) → uncoil surge; wave leaves on the arm arc @43 |
| `atk_torrent_ceiling` | 108 | arm circles overhead, body orbits with it, snap @82 |
| `atk_torrent_floor` | 108 | mirror: she STOOPS and traces the floor |
| `atk_lance` | 30 | no gather, no arc — a jab. Its shortness is what makes the big ones feel big. |
| `react_scoop` | 54 | see below |
| `waveform` | 96 | dissolve → surge → reform |

**Sign gotcha:** negative X-bend pitches her FORWARD. Ceiling must arch her
BACK (+), floor must stoop her FORWARD (−). v1 had them inverted and both
attacks stooped identically.

## 7c. `react_scoop` — water does not flinch

**A flinch implies pain, and pain implies a nervous system.** When you remove
volume from a body of water the rest FLOWS to fill the void: a depression at
the scoop point, a wave propagating outward, a sag toward the missing mass,
then re-cohesion — smaller. The clip is a damped wave travelling UP her
column, each segment peaking later than the one below it. Her arm goes slack
rather than bracing.

It reads as **"you are not hurting me, you are diminishing me"**, which is
right for a boss immune to weapons. And it inverts the game's theme: this is
the one fight where **the PLAYER is the extractor**. She never cries out; she
just gets smaller. That should feel a little bad.

## 7d. `waveform` — the visual contract for invulnerable

Dissolve (12) → formless (25) → travel 2.6m → reform (60) → landed (85), with
a `uDissolve` envelope in the events file for the material to read.

**No readable figure IS the invulnerability contract** — the player should
never need a UI cue to know she cannot be hit.

v1 froze in the wave shape while translating, so the travel frames were
identical; water in motion churns. Added an undulation running nose-to-tail
(the mass ROLLS forward rather than sliding) plus a crest weight so the
silhouette peaks forward and tapers behind. Reform throws the arm out on an
overshoot — the water gathers, overshoots, settles.

## 7e. VFX marked TODO (animation is done; effects are a later session)
- rising wave travelling downrange along the arm arc
- torrent falling from the ceiling / erupting from beneath
- water lance, hitscan-fast
- wave crest + spray sheet during waveform travel; splash ring on reform
- the scoop's spray burst already exists (`WaterSheddingVFX.scoopBurst`)

## 7f. v0.01alpha — PARKED 2026-07-28

Seven clips on the 14-bone rig, event-mapped in `assets/water_events.json`.

**Four laws this arc produced, all the same mistake in different clothes:
I kept animating her like a PERSON.**

| symptom (Khaled's words) | cause | fix |
|---|---|---|
| "a sort of… snowmobile?" | rotated a humanoid and expected a wave — rotation PRESERVES proportion | squash-stretch: object scale IS the dissolve |
| "a model that's falling over" | a body bending 30° forward MEANS toppling | she doesn't bend down, she SINKS |
| "a figurine on a stand, that bobbles" | bends weighted by height — right for planted feet, wrong when the lower body IS the mass | base weight floor 0.55, root translates, col0/col1 slosh with lag |
| "she should lean forward!" | no anticipation; a collapse without a decision reads as a stumble | lunge before form is lost (and a coil BACK before a forward surge is correct — anticipation is counter-motion) |

**The through-line: when a pose reads as the wrong ACTION, the fix is
PROPORTION, not angle.** Bone rotation cannot make a body stop meaning
"body".

**And the ceiling is real (Khaled):** the mesh only gets you to "low fast
formless mass". Everything that reads as WATER — crest spray, foam sheet,
churn at the floor, splash ring on reform — is the VFX layer. Recorded as a
dedicated session rather than chased with bone angles.

### Known, accepted for alpha
- `atk_wave_rise` peak frame still balls up slightly
- `react_scoop` is legible but wants the VFX burst to land the impact
- `glide` lean is a little static; root translation is the game's job
- scale is still normalised 1.0 — she should LOOM (2.2–2.5m)
- the wet trail needs glide-with-translation first

---

# 8. READABILITY (2026-07-28)

Khaled, looking back across the whole arc: *"do u feel like maybe at some
point we lost the plot?"* He was right, and the regression was invisible to
me because **I only ever compared each step to the step before it, never to
where we started.**

## 8a. What was actually lost

The ORIGINAL model's legibility came from **colour separation** — pink
ribbons, blue body, pale hair. Three materials telling you where the woman
ends and the water begins. I replaced all of it with ONE water material,
which is correct for the concept but **spent the entire readability budget
and never bought it back.** Then the vortex added strand density. Then the
aura added haze. Each step defensible; the sum is murk.

**Readability is not "less", it is HIERARCHY.** Decide what carries
information — her figure, her posture, her volume — and give THAT the
contrast. The decorative water can stay quiet. Reducing noise uniformly just
makes a quieter blur.

## 8b. The toolkit — all three ride the strand factor

The vortex already computes what is her BODY and what is her WATER, so all
three readability tools are gated on the same mask. Each is independently
switchable so they can be permuted.

- **`uCoreGlow`** — lit from WITHIN. Reads as solid-inside-translucent, and
  it dims with `uWater`, so her brightness IS her health.
- **`uBodyRim`** — Fresnel outline on the FIGURE only, never the strands, so
  her silhouette gets drawn for her without the water competing.
- **`uPink`** — the strands take a tint the body does not. This is the colour
  separation the original had.

Isolation sweep verdict: **the tools work and the MIST was the culprit.** With
all three on and no mist she is the most readable she has ever been — better
than the original, still unmistakably water. Mist then erodes it step by step.
The answer was both, in a ratio.

## 8c. Self-lit colour — albedo is at the mercy of the room

The pink bleached to grey under the beauty rig. Cause: the key is `#bfe6ff`
at 4.2 and **a red albedo cannot reflect light that is not there**, plus the
additive cyan core glow diluting it again.

**LAW: any colour that must survive arbitrary lighting cannot live in albedo
alone.** `uPinkEmissive` makes the blood ride `uCoreGlow`, so it is lit from
INSIDE her and holds under any scene. Also the physically honest answer —
blood suspended in glowing water would catch that glow.

## 8d. The blood

Khaled named it ~40 minutes after the tint existed: *"i have the answer for
why - its blood. its just blood."* Not minerals, not decoration. **She has
been drinking.** Something died in that water and never fully cleared, so it
hangs in her strands and pools where she is thickest — which is exactly what
the shader already did unprompted, because the tint is a PARTIAL mix over
what is there and depth does the rest.

It changes the fight: you are hauling buckets out of something visibly not
clean, and every load has that in it. She never cries out; she gets smaller
and paler, and the last thing to leave her is the red.

**Design note: a reason may arrive after the design. Sometimes you just do
things you like** (Khaled: "Hideaki anno with the cross on the first angel").
The justification showed up late and turned out to be load-bearing.

## 8e. The artist's note — height-graded mist

SaltyButterMilk (artist): *"i like the top part of 1 and the bottom part of 5
… its too distracting if theres too much wispyness on top but on the bottom
is fine … keep it at a lower level than around the leg area."*

Right, and physically correct: **spray is densest at its source.** The churn
is at her base. Haze at her head should be thin residue that drifted up.

`uMistTopGain` / `uMistFalloffLo` / `uMistFalloffHi`. The real win is that
base and crown density are **decoupled** — before, "more atmosphere at the
pool" always cost "busier head", which is exactly the trade she objected to.
Shipped: base 0.150 (v5), crown ×0.09 (~0.013). Literally top of 1, bottom
of 5.

**Both of the day's art notes were correct for reasons beyond taste.** Neither
person was expressing a preference; both had noticed something UNTRUE about
the image and reached for the nearest words. Treat "I don't like this" as a
report that something is lying.

## 8f. The beauty rig

`__pretty()` in the harness. **Backlight is what makes anything translucent
live** — key goes BEHIND her so the water lights from within rather than
being surfaced. Cool fill shapes the front, warm kicker stops the blue going
monotone, uplight catches the pool, camera drops low so she looms.

Shipping render: `Downloads/water_elemental_renders/GRADED_v5base.png`.
