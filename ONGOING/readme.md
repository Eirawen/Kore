# Active Threads — Kore

Last updated: 2026-07-31

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

## Standing threads
- **The broke slayer's first hour as prose — STILL UNWRITTEN.** Fifth
  surgery it has survived. Still the keystone.
- Succubus: 8 wing poses, coy/jump/hover. `shy` wings still not in the coy
  emote (cheapest high-value upgrade on the board).
- Spider: walks, threatens, feels.
- FP combat kit: delivered, awaiting Sable's viewmodel layer.

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
