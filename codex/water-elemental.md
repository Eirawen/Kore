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
