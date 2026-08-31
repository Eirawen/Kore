# VFX Methodology — Spell Effects

How I design spell VFX in Crescent. Learned through water strike iteration.

---

## Architecture

Spell VFX in Crescent are composited from two systems:
- **Mesh core** — a custom ShaderMaterial on geometry (e.g., water_orb material on a sphere)
- **Particle layers** — emitters from ParticleSystem (charge, orbit, drips, trail, impact)

The mesh gives IDENTITY (this is water, this is fire). The particles give ENERGY (this is magic).

## The Bridge Principle (from Fable)

Two energies blend when each one's boundary is the other's source.

- The Fresnel RIM is the bridge between water (interior) and magic (particles)
- Rim color = particle color = same hex. The eye reads a continuous gradient.
- Every particle must be BORN FROM or DIE INTO the orb — never just coexist near it
- Converge particles: lifetime = (shapeRadius - orbRadius) / |speed| — they extinguish at the surface
- Drips: born AT the surface, fall away, die
- No floating dots. Every particle touches the orb at birth or death.

## The Five Layers (Water Strike reference)

1. **Core mesh** — water_orb material: jelly wobble, volume opacity, fake refraction, magic rim
2. **Charge shell** — converging droplets, born on a shell, die at the surface
3. **Orbit ring** — lazy wisps circling at ~1.1× radius, rim color, fills the scale gap
4. **Drips** — born at bottom surface, gravity pulls them down. Water falls even when magic holds it up.
5. **Trail + impact** — short trail during flight, ring burst + spray on hit

## Key Learnings

### Water v2 shader is plane-specific
Don't use it on spheres. Its Gerstner displacement goes along object-Z (world-up for the rotated water plane). On a sphere, waves shear across poles. Use water_orb material instead.

### Icosahedron vs Sphere for orb mesh
**SUPERSEDED 2026-08-20 for anything using `elemental_sdf`:** a marched
silhouette is exact at every scale and every deformation, so tessellation,
face-edge artifacts and the UV seam below all stop being questions. The
note stands for the mesh path, which the shipped strikes still use
(`IcosahedronGeometry(orbRadius, 4)`).

- IcosahedronGeometry(r, 1) = 42 vertices. Too few — visible faceting, dark seams at face edges.
- IcosahedronGeometry(r, 5) = uniform tessellation but still has face edge artifacts.
- SphereGeometry(r, 64, 48) = smooth normals by default, no seams. Use this.

### Sphere UV seam
SphereGeometry has a UV seam at one meridian. Sine-wave vertex displacement can create visible gaps there. FBM noise displacement in 3D (sampling radial direction, not UV) avoids this.

### "Pathetic" is a design parameter
**CORRECTED 2026-08-20 (the four-element arc). The first line below is
WRONG and it is what made the shipped water strike render as a grey
boulder.** A high wobble-to-radius ratio does not read as "barely holding
together" — it reads as a LUMPY SOLID, because water at spell scale is held
near-spherical by surface tension and an irregular silhouette is what a rock
looks like. Shipped level 1 is `wobble = 0.34 * radius`; the blessed
reference render everyone judged against used `0.12`. The picture and the
value were never the same orb.

The intent is right; the AXIS is wrong. Instability belongs in **speed and
shed mass** (jitter fast, leak droplets) and, better still, in
**fragmentation** — see "the level dial wants the silhouette" below.

For level 1 spells:
- ~~High wobble-to-radius ratio (barely holds together)~~ — see above
- Sparse particle counts (2-3 per layer, never dozens)
- Low rim strength (effortful, not radiant)
- A drip that falls off mid-flight (the spell is embarrassed)
- Slightly-too-slow projectile speed

### A point light inside the orb makes it real
One PointLight in the rim color, parented to the orb position. The ground catches blue glow, the caster's hands catch light. The spell becomes an object in the world.

### Dark scenes starve the shader
**HALF CORRECTED 2026-08-20, and the prescription was the dangerous half.**
The observation is right and understated: the environment term does not
merely contribute, it DOMINATES. Water's albedo is near-black — it absorbs —
so nearly all of its brightness is surface reflection, and a directional
light can only ever give one small highlight.

But **"test in lit environments" is exactly backwards.** The game is dark.
Testing in a lit room hides the real problem instead of showing it, and the
real problem is that *a spell in a dark game has to carry its own light and
its own reflections*. Measured in `cistern.level`: `envMapBound=true`,
`uEnvMapIntensity=0.3`, and the refracted interior samples DARK STONE, so
the orb wears the colour of the wall behind it. Refraction means "take on
your surroundings" — gorgeous in a lit room, camouflage in a dungeon.

Test in the dark room. Then give the spell something of its own.

### Particles and mesh must share visual language
Same rim color as particle color. Matched brightness. Scale stepping stones between blob and dots. Opposite visual languages (subtractive mesh vs additive particles) need explicit bridges.

## Test Page

`/crescent/engine/browserClient/tools/water_spell_test.html`
- Served at `http://localhost:8080/tools/water_spell_test.html`
- Click or Space to cast
- Uses standalone water_orb shader (adapted from engine material)
- Particles via engine ParticleSystem

## Capture Pipeline

`/Kore/tools/vfx_capture/` — canvas.toDataURL capture with contact sheets
- preserveDrawingBuffer: true required for WebGL capture
- Playwright page.screenshot() does NOT capture WebGL in headless Chromium
- Use evaluate + captureOneFrame() instead

## Iteration Workflow

1. Edit emitter configs or shader uniforms (live via browser console or Playwright evaluate)
2. Cast the spell (Space/click)
3. Screenshot (user for now, capture pipeline for autonomous)
4. "What does this feel like?" — the quality check
5. Adjust
6. Repeat

---

# The four-element arc (2026-08-19/20) — the method, not just the findings

Water, air, earth and fire, each taken from "this looks like ass" to as far
as it would go. The per-element findings live in Crescent's codex
(`rendering/spell-fidelity.md`, `water-look-the-stage-and-the-recipe.md`,
`air-is-a-thing-you-see-through.md` which also carries earth, and
`fire-has-no-surface.md`). **This section is the part that does not live
there: how the work was actually done, and what it cost.**

## What each element IS

Not what it looks like — what it *is*, because every winning move came from
answering that and none came from the sliders.

| | the body | brightness comes from | the stage wants | level dial |
|---|---|---|---|---|
| **water** | a smooth body that **tears** | **reflection** — near-black albedo | a void + bright panels to mirror | fragmentation of the tear |
| **air** | **none.** only what it disturbs | (blocked — no scene-colour sampler) | something busy BEHIND it | order vs chaos of the vortex |
| **earth** | opaque, **faceted**, hard-edged | light **trapped inside**, leaking out | a DIM key so the interior wins | fragmentation of the shell |
| **fire** | **none — a distribution** | **itself** | the lamps essentially off | temperature |

Two of those inversions are worth saying out loud because they are so easy
to get backwards. **Water is dark and gets its brightness from outside;
fire is bright and gives its light to everything else.** And **earth wanted
the key turned DOWN** — the same finding as water's interior ember in
reverse: whichever of the two is the subject is the one allowed to be
bright.

## The pattern that repeated four times

**Every element failed the same way: a good design whose governing parameter
was hardcoded and unreachable.**

- **water** — the refraction mip floor, `0.42` of max LOD *even at a thin
  edge*, so structure could never survive. Now `uRefractBlur`.
- **air** — `uBaseColor #c8d8e8` against `uStreakColor #ffffff`: white
  structure drawn on near-white. The spiral maths was fine; the palette
  erased it.
- **earth** — the vein width, `pow(ridge, 7.0)`, which decides SEAMS versus
  leopard print. Now `uVeinSharpness`.
- **fire** — the form itself. Not a number: an opaque solid, and fire is
  never a solid.

Also four times: **the material's own header comment already said what the
element was**, and following it beat every hour of tuning. Earth's *"the
mage doesn't impose order — they BORROW it"* is what produced the fractured
shell with light inside. Fire's *"water's tail trails BEHIND motion; fire's
point leads TOWARD"* is the whole shape. **Read the thesis before touching a
uniform.**

## The method

1. **Build the stage before you tune.** The first pass judged spells in
   `cistern.level`: 2.5 minutes a shot, one camera guessed in server
   coordinates, a room whose lighting cannot be touched. That is a keyhole.
   With an orbit camera, a movable key, exposure and a background — 40
   seconds — I was correcting myself four times an hour instead of once.
   **A look approved from one angle under one light has been approved by
   luck.**
2. **Keep two rigs and know which question each answers.** The stage
   answers *is this beautiful*; it can move anything. The level answers
   *does this belong in the game*; it can move nothing. Neither substitutes.
   A spell judged in a void has not been judged — and a spell that has only
   been judged in a void will fail the moment the room changes.
3. **Ablate, do not guess.** One variable per cell, a control cell that
   reproduces the old behaviour, and the run aborts if a uniform fails to
   apply. Earth's core-off control is what proved the light was escaping.
4. **Falsify with something hard-edged.** Refraction looked broken against a
   soft studio cube and resolved into sharp warped structure against a
   checkerboard. If a test can only fail quietly, it is not a test.
5. **When it looks bad, rebuild the FORM.** The earth cube got several
   rounds of genuine improvement and stayed ugly, because chipping a box is
   a surface treatment on a shape that was never the shape. One structural
   rethink fixed it in a pass.

## Four things that read as flow, and one that never will

- **Dots are confetti.** Position carries no direction. Elongate entrained
  matter ALONG the flow and it reads as motion.
- **Regular spacing is the tell.** Evenly spaced softbox bars reflect as
  brushed metal; an evenly spaced helix is a chrysanthemum. Nothing in a
  real room is evenly spaced.
- **Independent jitter averages to a cloud.** Turbulence must be a SMOOTH
  function of the parameter so neighbours move together — and then the
  tangent can be finite-differenced from the same curve that placed the
  particle, and stays correct at any amount of chaos. Per-particle random
  offsets with an unjittered tangent make a sea urchin.
- **One size is a blob.** Bimodal scales — many small sharp, a few large
  soft — are what read. It is the contrast between scales, not the variance
  within one.
- **And the one that never will: a radial gradient has no shape.** Stacking
  soft round primitives makes a glow; stretching them makes a bar. A flame
  lick is a tapering curving tongue with a sharp tip, and it has to come
  from a sim. Proved by exhausting the alternatives, which is why the Censer
  FR is worth what it costs.

## Scars from this arc

- **An unguarded two-index slice.** `s[s.index(a):s.index(b)]` where `b`
  occurs BEFORE `a` gives an empty `old`, and `str.replace("", new)` inserts
  between **every character**: 45KB became **71MB**. Recovered exactly by
  stripping the injected text, since the corruption was uniform. **Assert
  `i0 < i1` before slicing by two searches.**
- **Backticks inside a GLSL template literal** close the JS string, and the
  shader body then parses as JavaScript. Hit it once writing a comment, and
  Fable hit it twice in ten minutes — the second time while writing the note
  about the first. Scan every GLSL block for stray backticks; do not rely on
  care.
- **A harness that fails to parse fails SILENTLY.** The module dies,
  `window.__ready` is never set, and every tool reports `waitForFunction
  timeout`, which is indistinguishable from a slow render. Three breakages
  hid behind that one message. `tools/_check_harness.js` turns it into a
  line number in under a second.
- **`pkill -f run-tests.js` matches its own shell** and kills the command
  issuing it.
- **And the reasoning one, which is the one to actually watch.** I concluded
  from a light sweep that *no scene light reaches this body*. Wrong — the
  GROUND was what changed across those cells, and the body was simply being
  drowned by its own emissive. **When eight cells look identical, check
  whether you are looking at the thing you varied.**
