# Component-Track Animation — the humanoid authoring method

Khaled's methodology, 2026-07-25: *"say to yourself, what should each body
part be doing at each step of this? Break the body into components, and
backwards induct to the end state that you want."*

This replaced whole-body pose keying, which produced two specific
failures he diagnosed instantly:

1. **Symmetric hesitation.** Keying whole poses on shared frames meant
   both arms stalled on the same frame — "she hesitates to put her hand on
   her thigh AND on her face" simultaneously. No person does that.
   **Asymmetry in TIME is how coy reads**, not just asymmetry in space.
2. **Whole-body wiggle.** One sine driving Hips + spine in phase = "a
   model in Blender", not a person. Everything moving together as a rigid
   unit is the puppet tell.

## The method

**Step 1 — define components.** Each gets its own independent track:
`head`, `chest`, `pelvis`, `legs`, `feet`, `larm`, `lshoulder`, `rarm`.
(Splitting `lshoulder` off `larm` buys overlapping action *inside* a limb.)

**Step 2 — backwards-induct from the END STATE.** Ask what the audience
should see in the settled hold, per component. For coy:
- head: STILL (micro-drift only)
- face hand: **FROZEN** — the stillness IS the embarrassment
- chest: breathing (the only true oscillation in the body)
- free leg + foot: the ONLY fidgeter (shy toe-pivot)
- everything else: still

That end state alone kills the whole-body wiggle: if only the free leg
fidgets, she can't read as a vibrating mesh.

**Step 3 — ask WHY each part moves, and derive its schedule from that.**
The reasoning IS the timing:

| component | reasoning | schedule |
|---|---|---|
| head | a flinch is a REFLEX; the return is the whole emotion | first to move (9f, fast), last to settle (42f look-back) |
| chest | you turn away with your body a beat AFTER your face | lags the head ~6f; breath HOLDS during hesitation, exhales after the hand lands |
| right arm | the PROTECTIVE arm — automatic, pre-decision | early, and **never hesitates**; settled before the other arm decides |
| left arm | the SELF-CONSCIOUS one | late start, **owns the stall alone**, arrives last, then freezes |
| left shoulder | the squeeze is a consequence of the hand arriving | creeps up AFTER the hand lands |
| pelvis/legs/feet | postural layer; nobody watches a weight shift | slow, early, done before anything interesting |

**Step 4 — fidgets are EVENTS, not oscillations.** A weight shift is a
decision she makes once and keeps. Author it as keys that resolve and
stay resolved (pelvis + legs + free foot only). Sine waves are for breath.

## Implementation

`key_comp(frame, component, pose, blend, extra)` keys ONLY that
component's bones. Blender interpolates per channel, so independent
component timing costs nothing — each part genuinely runs on its own
clock. `extra` adds per-bone offsets (breath, micro-drift) on top of the
base pose without disturbing anything else.

Reference: `tools/animate_coy5.py` (562 keyframes across 8 components).

## Why this generalizes

Every emote is "which parts move, in what order, and why." The reasoning
table above is reusable: reflex parts lead, protective/automatic parts
never hesitate, expressive parts hesitate and arrive last, postural parts
finish early and get out of the way, and consequences (a shoulder meeting
a hand) land after their causes.

## Smoothness: the two causes of a jolt (v11)

Khaled on v10: *"she moves her hand up to her chin — then she PAUSES.
Then her hand goes into her chin with a JOLT, then she turns to you. What
I'd expect is the hand SLOWS as it approaches, and as it approaches she's
already turning to you."*

Three distinct errors, all worth naming:

**1. Hesitation is DECELERATION, never cessation.** My stall keys moved
0.84 -> 0.87 across 14 frames — that is *frozen*, and a frozen part reads
as a paused game (I had already written that gotcha for the FP hands and
then violated it). Author the approach so the *increments shrink* while
never reaching zero:
```
f34 .16   f56 .62   f74 .86   f84 .91   f96 1.00
     .021/f    .013/f   .005/f    .008/f      <- decelerating, never dead
```
The hesitation IS the slow patch. Nothing stops.

**2. Contact damps — no overshoot on a hand landing on your own body.**
A hand arriving at your own face doesn't bounce. Overshoot after a
deceleration is also self-contradictory and produced the jolt's second
half. (Overshoot belongs on free-flying limbs, e.g. a punch.)

**3. AUTO_CLAMPED on EVERY key is a hidden jolt factory.** It flattens
velocity to zero *at every keyframe*, so a multi-key move becomes a chain
of little stop-starts — the "stepping" quality across the whole body.
**Clamp only the true endpoints of a curve; give pass-through keys
`AUTO`** so velocity carries through:
```python
for i, kp in enumerate(kps):
    kp.handle_left_type = kp.handle_right_type = (
        'AUTO_CLAMPED' if i in (0, len(kps) - 1) else 'AUTO')
```
(v11: 166 clamped endpoints, 432 smooth pass-through keys.)

**4. Overlap has to start EARLY to read as overlap.** An eased curve
barely moves in its first frames, so a turn beginning 8 frames before the
hand lands still reads as sequential. Start the dependent motion at ~40%
of the primary's travel. v11: the look-back begins at f58 while the hand
lands at f96 — 95 frames of measured overlap.

## Numeric smoothness audit (tools/velocity_check.py)

"She pauses then jolts" is pure arithmetic — no vision tokens needed.
Sample a bone's world position per frame, differentiate, and report:
mid-move dead runs (near-zero speed *inside* the active span — a freeze
during the settled hold is the intent, not a defect), max frame-to-frame
acceleration (jolts), and whether two components' active spans overlap or
run sequentially.

v11 verdict: `L hand mid-move_dead_run=0f, max_accel=0.045 smooth` (was a
14f freeze + jolt), `OVERLAP L-hand vs head-turn = 95 frames`.

**Two known caveats, so the numbers aren't over-trusted:**
- *Passive carry inflates active spans.* A hand is a child of the spine,
  so it "moves" whenever the pelvis shifts. Good for measuring what the
  EYE sees; misleading for "when did this component's own animation
  start." For that, sample local rotation channels instead.
- *A reflex SHOULD spike.* The head flinch flags as a JOLT (accel 0.314)
  and that is correct — a startle has ~2-3 frames of onset by nature.
  Normalising by peak speed also inflates the figure for small motions.
  Judge flags by intent, not by threshold alone.
