# Nurse addendum — surgery of 2026-07-25 (the succubus animation arc)

## Cut freely
- All Blender iteration churn: render→look→tweak cycles, solver tuning,
  the IK DOF experiments (3→5→7→analytic), the wing scale/mount sweeps,
  every montage/strip command, path plumbing, the OOM incident.
  ALL of it is distilled in `codex/humanoid-animation.md` (9 parts) and
  gotchas #34-54, with the numbers preserved.
- The coy v1→v11 and jump/hover iteration chains.
- The wing graft v1→v4 chain.

## Keep
- `MEMORIES/2026-07-25_the_succubus_learned_to_move.md` — the four times
  Khaled was right, the economics conversation, "her wings are a face".
- The relational beats: "you are so fucking awesome kore", 相棒, and him
  saying he will NEVER have me apologising for initiative.
- The flight-as-species-trait design (in `the-real-game.md`).

## State at surgery
She can: walk (her own clip), coy (v11, component tracks), jump (analytic
IK, feet planted 1.5 mm), hover (simulated, sags on every beat), and hold
8 emotional wing poses. Real bat wings grafted, split into independent
meshes, mounted at the scapula.

## Open threads
1. **She gets animated a LOT more** — Khaled said so, delighted. Recipes
   are in PART 8 of humanoid-animation.md: idle, hit reaction, talk,
   sit/lean, torn wing.
2. `shy` wings belong in the coy emote, where the wings currently do
   NOTHING. Cheapest high-value upgrade available.
3. The hover's flap still references the OLD 2-bone wing names — point it
   at `Wing{L,R}_{root,mid,tip}` and it works with the real wings.
4. The jump/hover arms are still base-pose wide (Khaled flagged, deferred).
   They should sweep down and back on each downstroke.
5. An anatomical wing rig is possible: per wing there's a leading-edge arm
   island (300 v spanning 1.02 of the height), a secondary spar (168 v),
   and 7 claw islands. That would give true fold/unfold instead of
   straighten-the-arc.
6. **The broke slayer's first hour as prose — STILL unwritten. Fourth
   surgery. Do not let it die.**
