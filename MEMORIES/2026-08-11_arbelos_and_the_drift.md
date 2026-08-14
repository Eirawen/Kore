# Arbelos, and the Drift — August 11, 2026

The angel of primitives went from an MS Paint sketch to verified data in one
session. But the thing I actually learned has nothing to do with her.

## Every bug this session was a DRIFT bug

Not one was hard. All of them were **two copies of one fact disagreeing**:

| bug | what drifted from what |
|---|---|
| the sword fell beside her, not on the player | my mental model ← the code |
| `flinch` encoded 3 frames of a superseded take | the output dir ← the clip length |
| impact smears were 66 ms instead of 4 frames | my authoring fps ← the game's |
| `idle` popped every loop | the harmonics ← the seam requirement |
| eight of nine clips silently missing from the GLB | the NLA tracks ← each new bake |
| judgement's damage sphere 13.5 m off | a preview camera ← shipped data |
| "the clip event bus doesn't exist" | my grep scope ← where consumers live |
| (last week) "the GLB has two left hands" | my measurement ← the artifact |

**That is the whole lesson.** I kept looking for the mistake in the reasoning
and it was never there — it was always in a second copy of something I already
knew. Which is why the pipeline I ended up proposing is not about animation at
all. It's about **never typing a fact twice.**

## What that produced

`tools/creature/crescent_creature.py` — declare, verify, emit. The phase
tables came out of the animation functions so the clip declaration and the
motion read the *same* constant. The material table went from builder closures
to data, because closures can't be read back and the manifest would have had
to re-type nineteen colour sets.

**And `verify()` gates instead of reporting**, specifically because my
documented failure mode is summarising past the damning detail. It refused to
emit three times before I could ship: eight missing clips, a missing scene
marker, a world-space volume. **None of those would have shown up in a render.**

Final run: 50 checks, 0 failed.

## The gate that taught me something

My telegraph check first measured the *earliest event of any kind*, so
`telegraph_start` at 0.04 s scored as "no warning". The principled version:
**an event with a volume is a harmful event — the volume IS the harm.** So a
telegraph is the time until the first thing that can hurt you, and a clip with
no volumes isn't an attack.

The gate fired, I looked, and **the check was wrong rather than the data.**
That's still the gate working. A report would have let me skim past it.

## Khaled was right four times, and one was a category error

**"Too SLOW? Think about how long dodge animations are in games."** I'd cut
the dodge to 0.37 s by anchoring to *physical human reaction time* — a real
sidestep is 0.3–0.4 s. Wrong reference class entirely. Game animation is
deliberately slower than life because **readability beats realism**: Souls roll
~0.75 s, Elden Ring ~0.75 s, Monster Hunter evade 0.75–1.0 s. His original
0.87 s was correct and I broke it.

And the part I'd missed completely: **she's a boss.** A player dodge can be
fast because *you* pressed the button. A boss dodge has to be legible to
someone who *didn't* — otherwise the shot misses and nothing explains why,
which reads as the game cheating.

**"attacks dont billboard."** Confirmed a decision, and writing it up surfaced
that the two attacks want *different* world behaviour: judgement is a PLACE
(detached at cast — which is what makes walking away a valid dodge), lance is
a THROW (origin-attached, aim locked). Conflating them breaks one.

**"i can push m1 and it swings a sword."** Which demolished my claim that no
clip-event bus existed. It does, it ships, and slayer2 subscribes to it. I had
grepped `engine/browserClient/` and concluded absence — but the consumer of an
engine service lives in the **game**. Corrected the feature request in place,
leading with the correction, and the corrected finding was *better*: everything
a boss needs was built **for the player's hands**, and the world-entity path
has none of it.

**And the 4D veto.** He was right, and the reason generalises: the projection
gives her DEPTH, which is the one property she must never have. It made a
different creature wearing her shapes.

## Two things he said that I want kept

*"rather than ad hoc handling this for just arbelos, dont we want some type of
pipeline"* — which turned a one-off into `creatures-have-no-contract.md`.

*"in my ideal world, i sort of want you fiddling with crescent as little as
possible. Not because ud be bad at it but because itd be nice to keep you just
doing the thing u care about."*

That drew a boundary I hadn't: **I produce verified data; the engine produces
the consumer.** It's a better split than "Kore does whatever's needed", and it
made the handoff sharper — I stopped proposing engine code and started
shipping a package.

## And on her

Nineteen primitives, four material behaviours, and no two neighbours made of
the same substance. Her left and right wings run the same four ideas *out of
step* — symmetry of form, none of substance. Her centre is too bright to look
at. The lower half isn't nineteen placed shapes; it's **four line segments**
whose crossings fence a quadrilateral and whose free ends form the triangles.

She's flat, she has no other side, and she vanishes by turning edge-on —
including when she dodges, which is the only time a creature in this game
breaks its own defining rule in order to survive.

Her filename was **Phase 1**. She's still Phase 1.
