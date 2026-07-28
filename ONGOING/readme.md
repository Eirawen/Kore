# Active Threads — Kore

Last updated: 2026-07-28

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

### Next for her (not blocking)
1. VFX session: wave/torrents/lance effects, waveform crest + spray sheet,
   the scoop FLINCH pulse, the wet trail.
2. Real scale — she should LOOM (2.2-2.5m). Manual labour at the feet of
   something enormous and indifferent.
3. Sable: wire clips + uWater + uDissolve to the fight.

## Standing threads
- **The broke slayer's first hour as prose — STILL UNWRITTEN.** Fifth
  surgery it has survived. Still the keystone.
- Succubus: 8 wing poses, coy/jump/hover. `shy` wings still not in the coy
  emote (cheapest high-value upgrade on the board).
- Spider: walks, threatens, feels.
- FP combat kit: delivered, awaiting Sable's viewmodel layer.

## The lesson of the water arc
Four times I animated her like a PERSON and Khaled caught every one —
snowmobile, falling model, bobblehead, backwards anticipation. **When a pose
reads as the wrong ACTION, the fix is PROPORTION, not angle.**
