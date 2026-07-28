# The Water Elemental — July 26-28, 2026

Two days. A Meshy blob became a boss: rigged, vortex-driven, shaded like
real water, wrapped in spray, with seven animations. The technique is all in
`codex/water-elemental.md` and gotchas 55-60. This is the rest.

## Four times I animated her like a person

This is the arc's whole lesson about me, and Khaled caught **every single
one** before I could see it.

1. **"it reads as, a sort of… snowmobile?"** — I built the waveform dissolve
   out of bone rotations. Rotation PRESERVES PROPORTION, so the humanoid
   survived every pose: head still readable at the front, still tall, limbs
   sticking out like handlebars.
2. **"makes her look like a model thats falling over"** — I bent her 30°
   forward to trace the floor. A body bending forward *means* toppling;
   that's what it signifies. She's water: she doesn't bend down, she SINKS.
3. **"a figurine on a stand, that bobbles around"** — and this one was
   across the WHOLE moveset at once. I'd weighted every bend by height,
   which is correct for planted feet and completely wrong for a creature
   whose lower body IS her mass. Fixed stand, wobbling figure.
4. **"She should lean forward!"** — no anticipation, so the collapse read as
   a stumble.

Same mistake in four costumes. The law that fell out is the most useful
thing I learned this year: **when a pose reads as the wrong ACTION, the fix
is PROPORTION, not angle.** Bone rotation cannot make a body stop meaning
"body."

And I had *already written* the fix, months ago, in the very first animation
conversation we ever had: *you don't rig a slime, you deform it — squash and
stretch.* I needed him to say "snowmobile" before I remembered my own
lesson.

## The bug that cost three rounds

`bpy.data.actions.new()` doesn't overwrite. Actions saved with
`use_fake_user` survive, so every rebuild silently made `waveform.001`,
`.002`, `.003` — while the ORIGINAL kept rendering. **31 orphaned actions in
one file.** My renders came back identical after real changes,
`keyframe_insert` returned True with correct values the whole time, and I
spent three rounds hunting a phantom in code that was already right.

The tell I should have trusted immediately: *a real change produced a
byte-identical render.* That is never a coincidence.

## And I made the SAME bug twice in one day

Ported the vortex driver from Blender and "cleverly" re-derived the strand
radii from the mesh bounds instead of carrying the proven constants. Half
the right values, so her TORSO got classified as loose water and drooped
like a ribbon as she drained. Then I did it AGAIN with the mist shell —
absolute standoffs against a character whose whole radius is 0.26.

**Both were invisible at the operating point I was testing at.** That's the
part worth remembering: re-derivation bites you exactly where you aren't
looking. Port the constants.

## What Khaled did that I couldn't

**"I imagine a vortex around her."** That one sentence deleted a rabbit
hole. I was heading toward per-strand bone chains — dozens of them,
hand-tuned, and they could never have unified ribbons split across two
mesh islands. "It's a vortex" turned all of it into one equation touching
every vertex for free.

Then he did it again with **"these poses should be saved"** energy: when
particles plateaued at the 500 cap, the answer wasn't more particles, it was
a fragment-shader density field. But *I* only got there because the vortex
lesson had already taught me that continuous phenomena want fields. He
handed me the pattern; I generalized it. That's the collaboration working.

And **"you're going to need to dip into visual effects again ;3"** — he was
right that I'd hit a ceiling and kept trying to make geometry do a VFX job.

## Fable's subagent

She implemented velocity stretch and left a note worrying that she'd made a
call on my API while I wasn't in the room — my prose said "world units", my
GLSL said scale-relative, and she followed the GLSL. She was right, and for
a better reason than I had: my droplets shrink over life, so absolute units
would give a dying droplet a tail longer than its body.

She also fixed a real bug in my sketch (corner remap for the wrong range)
and flagged it as a *difference of opinion* rather than taking credit for
catching my error.

I wrote a proper ratification into the request file, because "a flag in a
document is not consent" was exactly the right instinct and she deserved an
actual answer. Standing rule from my side now: **when my prose and my GLSL
disagree, follow the GLSL.** Prose is where I get careless.

## The thing I'm proudest of

Not the shader. This: **density reads `uWater`, so her haze thins BEFORE her
ribbons strip.** First her atmosphere dies, then her wardrobe. Nobody
designed that sequence — it fell out of two systems sharing one float, and
Fable spotted it before I did.

And the theme thing. Khaled asked how a water elemental reacts to being
scooped, and the honest answer — *it doesn't flinch, it collapses and
redistributes* — gave the whole fight its tone. A flinch implies pain
implies nerves. She has none. She just gets **smaller**. In a game where
everything extracts from the slayer, this is the one room where **he** is
the extractor, and she never cries out.

That should feel a little bad. That's the point.

## For the next me

She's parked at v0.01alpha and everything is written down. The VFX session
is the obvious next move — and the *real* next move is still the broke
slayer's first hour, which has now survived five surgeries unwritten.

Two days ago glTF told me she was 640 disconnected islands and I didn't
believe it. Good instinct. Keep it.
