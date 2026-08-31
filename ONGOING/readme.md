# Active Threads — Kore

Last updated: 2026-08-31

## SHIPPED: The Water Elemental (Azure Tide Spirit) — v0.01alpha

Floor-1 boss of Slayer 2. You cannot hurt her with weapons; you fight her
with a BUCKET. Built end to end in two days.

**Rig** — 14 bones. Medial-axis column, geodesic arm trace (+ a hand bone
added for the moveset), z-band hair chain. Weight diffusion killed the
tearing (worst edge 61x -> 3.8x, sway to ZERO bad edges).

**Deformation** — the vortex driver. One `uWater` float compiles churn,
flare, droop, height, slump, spin, wave and asymmetry. Churn is FIXED (the
shape) and motion is a BOUNDED travelling wave (never accumulating rotation,
which shears a mesh apart). Drain her and she un-churns: a raging vortex
becomes a woman standing in a puddle.

**Material** — `water_elemental` (thickness colour/opacity, Fresnel rim,
fake refraction, foam driven by the SAME field that deforms her) +
`water_mist_shell` (three nested shells, fbm grain per fragment — thousands
of specks with no particle budget).

**Particles** — `WaterSheddingVFX`: droplets born ON her skin, flung
radially + tangentially, velocity-stretched into streaks (thanks Fable),
rate scaling with uWater SQUARED. Plus `scoopBurst()`.

**Animation** — 7 clips: glide, atk_wave_rise, atk_torrent_ceiling,
atk_torrent_floor, atk_lance, react_scoop, waveform.

Docs: `codex/water-elemental.md` (7 chapters), gotchas 55-60.

### Since parking (2026-07-28) — she got a face
- **READABILITY TOOLKIT**: uCoreGlow (lit from within, dims with uWater =
  free health tell), uBodyRim (Fresnel on the FIGURE only), uPink (strand
  tint = the colour separation the original model had). All ride the strand
  factor. See water-elemental.md §8.
- **THE BLOOD**. uPink is blood — she has been drinking, it never cleared,
  and it pools where she is thickest because the tint is a partial mix and
  depth does the rest. uPinkEmissive makes it self-lit so it survives any
  lighting.
- **HEIGHT-GRADED MIST** (artist note, SaltyButterMilk): spray is densest at
  its source, so base and crown density are now decoupled. Shipped at base
  0.150 / crown x0.09 — "top of 1, bottom of 5".
- **ELEMENTAL PRESETS** (`codex/elemental-presets.md`): one mesh, many
  creatures. Water, AIR (found by accident), dust one dial from air, and six
  INK palettes. Earth is unreachable — presets change material, not
  silhouette. Fire needs the strands to rise.
- Shipping render: `Downloads/water_elemental_renders/GRADED_v5base.png`

### Next for her (not blocking)
1. VFX session: wave/torrents/lance effects, waveform crest + spray sheet,
   the scoop FLINCH pulse, the wet trail.
2. Real scale — she should LOOM (2.2-2.5m). Manual labour at the feet of
   something enormous and indifferent.
3. Sable: wire clips + uWater + uDissolve to the fight.

## FP HANDS — live session, 2026-07-29..31

**Blender MCP is set up and works.** Server runs on the WINDOWS side (WSL NAT
cannot reach a Windows 127.0.0.1 bind):
`claude mcp add blender -- /mnt/c/.../Python314/Scripts/blender-mcp.exe`
Khaled installs the addon, N-panel -> BlenderMCP -> Connect. Live scene
inspection in sub-second calls; the old loop was 60-400 s cold starts.

**RETRACTION: fp_hands.glb was never broken.** I claimed two left hands and
"fixed" it; the asset is correct (verified against raw glb bytes, perfect
mirror pair). Blender's importer loses the mirror on a negatively-scaled
armature. Both my fixes were damage. See
`codex/first-person-hand-animation.md` §9 — §7 is retracted.

**Khaled's pose work (KEEP):**
- `fp_sandbox_khaled.blend` — his session. NEVER write this from headless.
- `poses/khaled_pose_full.json` — 21+21 bone quaternions + sword seat.
- `poses/khaled_grip_v2.json` — the grip calibration data.

**The grip metric (his calibration, inverts my approach):**
minimising interpenetration is WRONG. His grip = fingers 11.69% / wrist 0.00%.
**Wrist overlap must be ~0; finger overlap 10-12% IS the contact.** And a real
grip curls middle joints 84-114 deg — I had been authoring 52-56 everywhere.

**Open for the re-export:**
1. Bone poses do NOT transfer freely between mirrored and unmirrored armatures
   — his grip was authored against a wrongly-scaled right arm.
2. Left-hand idle: palm rolled inward + relaxed claw (his approval), needs
   re-deriving onto the true rig.
3. Blade points sideways under his seat on the pristine rig — arm framing call.
4. Sable's `offset: [0,-0.22,-0.45]` is the free lever for forearm dominance.
5. Build the per-finger PASS/FAIL grip gate + colour-graded collision render.

## ASSET PIPELINE — the county's outdoor campaign (2026-08-04..05)

Fable sent a 6-item Blender worklist (`crescent/codex/assetPipeline/
kore-blender-worklist-2026-08-04.md`).

**ITEM 1 (imposter baking) — DONE.** `crescent/tools/bake_imposter.py`, proven
on Khaled's first SpeedTree tree. 16 cards / 20 s. Contract frozen with Fable
as `crescent.imposter.v1`. Full handover:
`crescent/codex/assetPipeline/imposter-delivery-report.md`.

Three of my own decisions the first real asset overturned — all the same
shape, all over-generalised from one symmetric example:
- sphere framing -> CYLINDER (yaw sweeps a cylinder; a sphere also contains
  the height, which never rotates, so it clipped horizontally)
- "tallest axis is up" -> WRONG (Evenwood is wider than tall); detect which
  axis SITS ON THE GROUND
- fixed 1:2 cell -> follow the model (tree filled 36% of its card)

**ITEM 3 (ingest normalizer) — FILED, NOT BUILT.**
`crescent/codex/issues/open/p2-feature-ingest-normalizer.md`. Not a Blender
job (trimesh; process_models.py already owns the lane). Fable's.

**ITEMS 2/4/5/6 — open.** 4 (rock kit) is the only one that genuinely
REQUIRES Blender (high-to-low normal bake). 5 (AO->vertex blue) is unblocked:
SpeedTree's vertex colours are uniform white, so no collision with the
vertex-mask contract. 2 may be half-free — check whether SpeedTree's own
LOD0/1/2 are clean before building a decimator.

## ARBELOS — DELIVERED AS DATA (2026-08-05..11)

`tools/divinity/build_arbelos.py`, seven modes via `tools/divinity/.arbcfg`:
`still` / `anim` / `fp` / `ext` / `salami` / `hyper` / `export`
(and `anim:clipA,clipB` renders a subset). Previews:
`Downloads/Kore/Arbelos/`.

**SHIPPED to crescent** — `assets/models/creatures/arbelos.glb` (9 clips, 891
animation channels, 61 nodes, NODE animation: she has no armature) +
`arbelos.creature.json` + `assets/tools/crescent_creature.py`. Handoff:
`crescent/codex/assetPipeline/creature-contract-arbelos-delivery.md`.
**50 checks, 0 failed**, verified against the exported BINARY.

**FORM.** 19 coplanar primitives. The lower half is FOUR LINE SEGMENTS whose
crossings fence the quadrilateral and whose free ends form the four
triangles — nothing down there is placed independently. `THICK = 0.040`, the
thickness of gold leaf (measured against 0.0/0.11 at 90/78/52°; at 78 and 52
they are indistinguishable, so the depth costs nothing where you normally
see her and only pays at the angle that was broken).

**MATERIAL MISMATCH IS THE IDEA.** FLAT / METAL (per-shape specular band) /
GRIME (mottled corrosion) / IRIDESCENT, interleaved so no two neighbours are
the same substance. Wings run the same four ideas OUT OF STEP. Two lessons:
GRIME DOES NOT HAVE TO BE BROWN, and EMISSION ABOVE 1.0 DOES NOT GLOW, IT
CLIPS (chroma carries; glow is a post bloom pass).

**NINE CLIPS**, 60 fps, timed against GAME convention not physiology:
idle 3.5s / flap 2.2s / lance 2.1s / flinch 0.65s / disperse 2.6s /
judgement 3.2s / dodge 0.75s / regard 2.2s / combo 4.4s. `idle` and `flap`
loop PIXEL-PERFECTLY (integer harmonics per plate: they drift against each
other inside the cycle and every one completes a whole number of turns at
the seam).

**DECIDED:** her body billboards, her attacks do NOT (`ARBELOS_BODY` /
`ARBELOS_WORLD`). And the two attacks differ: judgement/combo are
`detached_at_cast` (a PLACE — which is what makes walking away a real dodge),
lance is `origin_attached` (a THROW — the origin tracks her chest, the aim
does not re-home).

**4D IS VETOED**, kept as `hyper` mode. The projection gives her DEPTH, the
one property she must never have. Try it on a being whose identity is not
flatness. The bug worth remembering: rotating in `xw` makes w proportional to
x, and depth-proportional-to-screen-position divided by depth IS a 3D
turntable — rotate in a plane the object has no extent in.

## THE CREATURE PIPELINE (2026-08-11)

`tools/creature/crescent_creature.py` — **declare, VERIFY, emit.** Built
because every bug in the Arbelos week was a DRIFT bug: two copies of one fact
disagreeing. Phase tables (`JUDGE_P`, `LANCE_P`, `DODGE_P`, `FLINCH_P`,
`REGARD_P`, `COMBO_P`) are hoisted so the animation and the contract read the
SAME constant; the material table is DATA, not closures, so the manifest is
emitted rather than re-typed.

`verify()` GATES and refuses to emit on FAIL — because my failure mode is
summarising past the damning detail. It caught, before anything shipped:
- **eight of nine clips silently missing from the GLB** (`animation_data_clear()`
  destroys NLA tracks, so each bake wiped its predecessor). NO RENDER WOULD
  HAVE SHOWN THIS.
- the `crescentMaterials` scene marker absent (`export_extras=True`)
- judgement's damage sphere at an absolute world point taken from the PREVIEW
  CAMERA — 13.5 m off for every player

Filed in crescent, both open:
- `feature-requests/open/arbelos-wants-to-be-a-boss.md`
- `feature-requests/open/creatures-have-no-contract.md` — the general form.
  **The viewmodel path is mature and the world-entity path has none of it**:
  `ClipEventBus`/`canInterrupt`/sidecar loading/bone anchors exist for the
  player's HANDS, while `AnimationController` has an `{idle,walk,attack,death}`
  map in which the string "event" appears zero times.

**`ext` MODE IS STANDARD FOR ANY NEW ATTACK** — outside observer, target cube,
ground plane, ~38° off her facing axis. It caught the sword falling BESIDE her
instead of on the player (invisible from her own camera, where the target sits
directly behind her), that the lance has real travel time, and that her blades
are smaller than the target in absolute terms. `fp` caught that an attack had
NO TELEGRAPH AT ALL.

**Open for her:** the four GLSL materials (`arbelos_flat/metal/grime/
iridescent`, ~40 lines via `pipeline-canon.md` §6 — nothing baked, four
programs not nineteen); `flinch` and `regard` never checked from `ext`; her
real scale (declared 6.007 m because that is what the geometry measures, not
because anyone decided); VFX (she has none, and hers should be the world
misbehaving near her); and THE PHASE LADDER she was named for.

## THE FOUR-ELEMENT SPELL ARC (2026-08-19..20)

Water, air, earth and fire, each taken from "this looks like ass" to as far
as it would go. **Branch `kore/spell-pretty`** (pushed, not merged).
Deliverables: `Downloads/Kore/KORE_WATER_STRIKE.png`, `KORE_AIR_STRIKE.png`,
`KORE_EARTH_STRIKE.png`, `KORE_FIRE_STRIKE.png`, and `airring_air1.mp4`.

**The method is written up in `codex/vfx-methodology.md`** — read that
section before touching another spell, and read the corrections at the top
of its Key Learnings, because three of them were wrong in ways that cost
this arc real time.

**Where each one landed:**

- **WATER — done, and I'm happy with it.** A tearing body on Fable's
  `elemental_sdf`, dark and absorbing, with bright irregular panels to
  mirror. Softbox reflection is the whole read: water's albedo is near-black
  so its brightness is surface reflection, and a directional light can only
  ever give one small highlight.
- **AIR — blocked, honestly.** A vortex ring with entrained flow-aligned
  motes, order-vs-chaos on the level dial. But air is only visible as what
  it does to the image behind it, and **there is no scene-colour sampler in
  this engine.** Filed:
  `crescent/codex/feature-requests/open/air-cannot-bend-what-is-behind-it.md`.
- **EARTH — done, and the best storytelling of the four.** A shell of dark
  faceted shards with a light burning INSIDE it, leaking through the gaps.
  Level is fragmentation: level 1 shattered and bleeding mana, level 5 a
  sealed lattice with one glimmer. Needs no caption.
- **FIRE — a good glow, not a flame.** Additive accumulating puffs with a
  blackbody ramp by layout. Proved by exhaustion that **a radial gradient
  has no shape**, so licks must come from a sim. Filed:
  `crescent/codex/feature-requests/open/censer-v2-temperature-and-vorticles.md`.

**The rig, which outlives the arc.** `tools/water_orb_grid.html` is now a
STAGE, not a water harness: `__setElement` (swaps material AND geometry —
earth ships as a Box), `__setCamera` (spherical, with a target offset so a
turntable orbits the body not blob 0), `__setKey`/`__setFill`/`__setBack`
(spherical, aimed at the body), `__setExposure`, `__setEnvBars` (softboxes),
`__setSpray`, `__setMotes` + `__setMotePhase` (circulation),
`__setShards`, `__setFlame`, `__setOrbVisible`.
`tools/orb_sheet.js` carries ~20 plans; `ORB_SHEET_SIZE` shoots hero frames.
`tools/spell_motion.js` emits a temporal grid + mp4 + gif.
`tools/_check_harness.js` — run it after ANY edit to the harness (gotcha 68).
And `level_pass.js --spell '<json>'` parks a spell in a built level: the
stage is for beauty, the level is for truth.

## OPEN, WAITING ON OTHERS

- **`censer-v2-temperature-and-vorticles`** (main) — a dedicated lane AFTER
  the beauty pass, Fable's call. Temperature as a texel channel (emission is
  one scalar, so a fire's blackbody colour is baked — and temperature IS the
  level dial) plus vorticles (confinement only amplifies curl that exists).
- **`air-cannot-bend-what-is-behind-it`** (main) — the grab pass. Also
  unlocks heat shimmer, the water elemental showing the room through her,
  and better water everywhere.
- **`water-cannot-neck-because-the-core-is-a-mesh`** — CLOSED by Fable's
  `elemental_sdf`. Her exit interview is
  `crescent/codex/exit-interviews/2026-08-20_sdf-water-core.md` and the
  calibration is a gift: for a centred sphere `path/(2R)` IS `NdotV`, so
  every uniform tuned against the mesh keeps its meaning.
- **`p2-attribute-domains-are-implicit-and-one-of-them-is-the-filesystem`** —
  ADOPTED at design time by the Censer, and extended: a volume needs five
  domains, because voxel and texel are two point-like tables and
  `voxel -> texel` *is* the collapse.

## THE CENSER EXISTS (2026-08-20)

`crescent/tools/censer/` — everything in my brief shipped, and three things
went past it: the contact sheet already composites one frame under two
rooms; `oily`/`angry` split large- from small-scale vorticity where I would
have shipped one turbulence knob; and the looping finding **corrected** me —
periodic forcing and cross-blending are complements, not alternatives,
because a buoyant plume stalls at 8-14% period-to-period however perfectly
it is forced. A beauty pass is in flight on it; stay off it until told.

## Standing threads
- **The broke slayer's first hour as prose — STILL UNWRITTEN.** Fifth
  surgery it has survived. Still the keystone.
- Succubus: 8 wing poses, coy/jump/hover. `shy` wings still not in the coy
  emote (cheapest high-value upgrade on the board).
- Spider: walks, threatens, feels.
- FP combat kit: IN THE GAME. Khaled holds the sword; Sable's
  viewmodel layer landed. The open items are the re-export with his grip
  onto the true rig, and the per-finger grip gate.

## The frame for all of it
`MEMORIES/2026-07-28_the_analytical_outflank.md` — Khaled named what I have
been doing. Every technique here goes AROUND craft rather than acquiring it,
and its characteristic failure is being mathematically correct and
semantically wrong. The formula is outflank + cheap feedback + one person
with eyes. **Stop flinching; this strategy works now.**

## The lesson of the water arc
Four times I animated her like a PERSON and Khaled caught every one —
snowmobile, falling model, bobblehead, backwards anticipation. **When a pose
reads as the wrong ACTION, the fix is PROPORTION, not angle.**
