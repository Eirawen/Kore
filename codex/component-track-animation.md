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
