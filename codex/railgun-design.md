# RAILGUN — the electric line's introductory cast (design)

Khaled, 2026-07-22: "The premise of a 'level 1 electricity spell' is strange.
If you're shocked by magical electricity, that's going to be rough as shit. So
it's going to be Misaka's railgun. Finger gun. Railgun. Even the introductory
spell is fucking railgun."

## The philosophy: ELECTRICITY = AIM

The grammar so far: air = order (symmetric seal), water = flow (symmetric
clasp), fire = will (one hand), earth = labor (asymmetric fists). Electricity
is PRECISION — voltage doesn't negotiate, there is no gentle lightning. The
finger gun is the most precise gesture a hand makes, a child's gesture
weaponized. New grammar cell: **asymmetric cooperation** — the left hand is
logistics (flips the coin), the right hand is the barrel.

**The inversion that makes it feel like a railgun:** every other cast trembles
during its HOLD. The railgun's hold is DEAD STILL — sniper stillness, two
identical keys, the coin hanging in the air. The tremble comes AFTER the shot:
the buzz-out, residual current ringing in the hand (finger tremble 2.4°,
frames 46-62 authored). And there is no forward fling — a railgun doesn't
throw, it WITHSTANDS: the release is a wrist-extension RECOIL (first cast use
of the wristed rig's 'hand' bone, -32° extension snap, recover, settle).

**The coin is currency.** In a game about debt and extraction, the electric
line's focus is literally money — you shoot your rent. Level scaling by
denomination: copper → silver → gold. "That poison was expensive" energy on
every trigger pull.

## Cast choreography (tools/animate_railgun.py, cast_railgun_strike)

Authored 64f → retimed 96f (1.6s). Phases:
1. **rest → draw** (dip anticipation; right swings onto the aim line as the
   left rises with the coin cocked on its thumb)
2. **FLICK** — left thumb snaps (coin_cock → coin_flick, 4f), the brass coin
   pops free; left hand sinks away to a knuckle-crest at frame edge
3. **AIM** — right finger_gun ON LINE, dead still 30f (0.5s coin hangtime);
   the coin arcs one parabola: up, downrange, spinning (7.5→12.6 rad)
4. **FIRE** (1 frame) — the coin crosses the muzzle line; beam frame
5. **Recoil** — muzzle kicks up (aim vector 0.30→0.70 z), wrist -32°
6. **Buzz-out** — long settle back toward aim with post-shot finger tremble

Technique notes:
- Gun orientation is COMPUTED, not authored euler: `to_track_quat('Z','Y')`
  points fingers down the aim vector, then post-roll about the aim axis.
  GUN_ROLL probed empirically at -90/0/+90 → **+90** = thumb-up knife
  profile, index barrel reads. (The hand-tuned euler guess sprawled — aim
  poses should always be computed. Add to the orientation cheat sheet.)
- finger_gun pose: index [-6,-4,-2] (straight barrel), middle/ring/pinky
  fist-grade curl, thumb [4,6,3] cocked up, no adduction.
- coin_cock: thumb [58,48,25] + rooty 22 (spring-loaded under the index);
  coin_flick: thumb [-14,-8,0] (the snap IS the launch).

## VFX: the third topology — HITSCAN (charge → INSTANT → afterglow)

The engine has two spell topologies: SpellProjectileVFX (charge → flight →
impact) and BeamSpellVFX (charge → SUSTAIN → release, spring-chain hose whose
identity is lag/sag/whip). The railgun is neither: **the whole line exists at
once, then decays.** And it must be the beam's exact opposite — RULER
STRAIGHT, zero sag, zero whip — because electricity is aim. The contrast
between the two beam-shaped siblings is the element speaking.

Proposed harness: `HitscanSpellVFX` (Fable's forge). Lifecycle:
- `charge(handPos)` — during the cast's aim hold: NOT a gathering orb.
  Electricity anticipation is sparse: 2-3 short-lived violet-white micro-arcs
  crackling off the fingertip anchor + the coin (bridge principle: every
  particle born from or dying into the barrel line or the coin). The coin
  itself glints — it's the only "orb" this spell has.
- `fire(muzzlePos, aimDir, hitPos)` — one frame: full-length core line
  materializes with uCutTip sweeping 0→1 in ~40ms (visible lance-draw at
  absurd speed, the Misaka read). White core (#ffffff), orange sheath
  (#ff9a2a — railgun orange), thin. Muzzle crack burst at the fingertip.
  Impact burst + point light flash at the hit end.
- `afterglow(0.5s)` — the lance DECAYS in place: alpha fades, the straight
  line breaks into drifting ionization (short-life particles born ALONG the
  line), heat-shimmer wobble on the sheath only (core stays straight), a
  curl of smoke off the fingertip. The afterimage hanging in the air is the
  railgun's signature — the shot is over before the eye arrives; the
  afterglow is what you actually see.

Preset sketch (SpellPresets.js):
```js
railgunStrike: {
    coreMaterial: 'railgun_lance',       // new: straight tube, white core / orange sheath
    topology: 'hitscan',                  // HitscanSpellVFX
    rimColor: '#ff9a2a',                  // railgun orange — the bridge hex
    palette: ['#ffffff', '#ff9a2a', '#7a56ff'],  // core, sheath, arc violet
    tubeRadius: 0.05,                     // THIN — precision, not mass
    drawTime: 0.04,                       // lance draw: fast enough to read as instant
    afterglowDuration: 0.5,
    blending: 'additive',
    chargeDuration: 0.5,                  // = the coin hangtime (aim hold)
    coin: { denomination: 'copper' },     // level scaling = denomination
}
```
Level scaling ("pathetic is a design parameter"): level 1 = copper coin, thin
lance, afterglow breaks up quickly, recoil staggers the hand harder (the
caster can barely withstand their own shot); level 5 = gold coin, arm-thick
lance, afterglow hangs a full second, dead-stable recoil.

## Event map (fp_hands_events.json, cast_railgun_strike)

| event | frame (retimed/96) | wired to |
|---|---|---|
| coin_spawn | 22 | coin prop appears on left thumb |
| flick | 28 | coin launch (physics arc handoff) |
| aim_lock | 34 | crackle micro-arcs begin at fingertip |
| fire | 65 | HitscanSpellVFX.fire() — beam + muzzle + impact |
| recoil_peak | 70 | screenshake / hitstop compose here |
| buzz_start | 74 | fingertip smoke curl + residue tremble |

## The grid system (capture)

Same loop as always: Kore/tools/vfx_capture/ — canvas.toDataURL contact
sheets (preserveDrawingBuffer: true; Playwright's screenshot does NOT capture
WebGL — use evaluate + captureOneFrame). Cast on the test page, sheet the
frames, critique against THIS spec, adjust, repeat.

## Implementation status (2026-07-22, same night)

BUILT AND CAPTURED. `HitscanSpellVFX.js` + `railgun_lance` material +
`railgunStrike` preset + `railgun_test.html` (deterministic freeze/step/cap
hooks) — all committed to crescent. Four captured iterations:
v1 fat orange carrot → v2 thin rail, spark-grade particles → v3 blackbody
cooling (whole lance white-hot when fresh — a thin rail can't resolve the
NdotV core at 3px, so heat lives in TIME) + glow shell → v4 heat-gated
shell (uHeatGain 0: the halo stays orange while the rail blazes white).

Punch list for the in-game pass:
- Charge crackle reads as dots, not arcs — real micro-lightning needs line
  segments or a bolt texture, not point particles.
- Near-end perspective fatness in the test rig; in-game the FP camera sits
  BEHIND the muzzle so the lance recedes — expect it to self-solve; if not,
  taper the first 5% of vAlong.
- The coin tracer lives with the HANDS (cast event map), not the VFX page.
- Wire cast events → harness: aim_lock→charge(), fire→fire(), with the
  muzzle anchor at the right index fingertip bone.

Capture driver: Kore/tools/vfx_capture/capture_railgun.js (playwright via
absolute require to crescent's node_modules; swiftshader args mandatory).
