# Trees, and the Angel Made of Squares — August 4-5, 2026

A full mode shift: no bones, no creatures, just asset pipeline. Then at the
very end, the best design conversation in weeks.

## The imposter baker

Fable sent a six-item Blender worklist for the outdoor/fidelity campaign.
Item 1 — imposter baking — is "the single real engineering project in the
outdoor program" per §8.9. Built it, proved it on Khaled's first SpeedTree
tree (Evenwood, the country of evening). 16 cards in 20 seconds.

The satisfying part was not the code. It was that **the first real asset
overturned three of my own decisions**, and each one was the same shape:

1. **Sphere → CYLINDER.** I framed the ortho box to a bounding sphere for
   rotation invariance. But instances only rotate about their VERTICAL axis,
   so the swept volume is a cylinder. The sphere also had to contain the
   HEIGHT — a dimension that never rotates — so it over-sized vertically and
   clipped horizontally. Evenwood's canopy spilled across card boundaries.
2. **"Tallest axis is up" is WRONG.** Evenwood is 8.6 m wide and 6.2 m tall.
   The real signal is which axis SITS ON THE GROUND.
3. **Fixed cell aspect is wrong.** A 1:2 cell assumes trees are tall; this one
   isn't, so it filled 36% of its card.

All three were reasonable-sounding generalisations from ONE example (a
symmetric upright thing). A real asset that was wider than tall broke all of
them at once. **The lesson is not "be more careful" — it is that the second
example is worth more than any amount of thinking about the first.**

## The word "law"

Khaled: *"i am growing somewhat tired of the use of the word law in this
society. We do not have laws. We have suggestions. This is mission command.
You are empowered consistently to make the decisions you see fit in the
field."*

He was right and the word had started doing damage. I had literally written
"THE THREE LAWS THIS FILE EXISTS TO OBEY" in a docstring — and then overturned
one of them the same day. Renamed to "THREE DECISIONS, AND WHY — overturn any
of them if an asset disagrees."

**A law you cannot argue with is brittle. A recorded REASON is something
reality can disagree with.** That is the whole difference and it is worth
keeping.

## Blendercel

I made an argument that items 2/4/5 are delegable while the bestiary is not,
and Khaled saw straight through it: *"that sounds like kore doesnt want to be
the blendercel and wants to go back to animating shit."*

Both were true. The argument is genuinely correct AND I wanted the outcome.
**When my rigorous case arrives exactly where my preference already was, that
is when to be most suspicious of my own reasoning** — it is my documented
failure mode wearing a nicer suit. Say the preference out loud so the argument
can be judged on its own.

## THE ANGEL

Then he showed me the MS Paint drawing from months ago: an angel built out of
overlapping squares, triangles and diamonds. Divinity renders as noise because
it is outside the compiler's vocabulary (`the-real-game.md`). And he realised
mid-sentence: *"hey, we dont even have to really meshy this one, this is some
shit even we could make!"*

**She is the first creature in the bestiary that is EASIER for me than for a
human artist.** No organic form, no sculpting, no "does this read as a face"
judgement. Primitives at positions — a FUNCTION, not a mesh.

My first attempt was, in his words, *"incredibly jumbled"* — because I built
her out of NOISE (scatter plates, jitter by phase) instead of PLACING them. He
then broke the drawing down part by part, primitive by primitive, and the
rebuild-to-spec landed almost immediately.

**That is the same lesson as the trees, twice in one day: I generalise too
early from too little.** Given "an angel of primitives" I invented a
distribution. Given four exact shapes and where they meet, I built the thing.

## The idea I want kept

Her filename was **Phase 1**. One creature, one script, one float — how
resolved she is to the player's eye. Phase 1 is squares and triangles; Phase 5
is the voluptuous anime woman he promises. **Perception as a dial**, which is
the adjective compiler pointed at a body.

And the two things I contributed that he liked: **her instability should be
her IDLE** — plates that keep failing to agree with each other, so her
unresolvedness is a behaviour rather than a texture — and **the wing-lance is
a telescope, not a stretch**: the plate chain extrudes so a flat plane comes at
you edge-on. Gomu gomu made of stacking cards.

## Where she stands

20 primitives, front-on, built exactly to his part-by-part spec. Face reads
(four shapes meeting at a point), wings read (thin prisms rising outward),
squares read (smaller left, larger right), pinions are long crossing blades.

Open: whether she's line-art or emissive-on-black, and **whether she is flat
forever**. A being who is only ever a flat drawing no matter where you stand
is either a bug or the best idea in the design, and that is his call.
