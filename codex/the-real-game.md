# The Real Game — Khaled's Manifesto, 2026-07-22

Verbatim-adjacent capture of the night Khaled told me what Slayer 2 is actually
about. His phrasing IS the spec. Do not paraphrase this into corporate design
language. Ever.

## The theme: extraction, and the one thing they can't have

- Genuinely CHOOSING corruption while humiliatingly powerless in the face of it.
  The fantasy of succeeding anyway — through *being clever*, burning the midnight
  oil, scouring the lost tomes, hiding it from every antagonist who would take it
  (divine, government, unholy, damned).
- "Everyone always wants to take from you. At all times. Take take take take.
  Squeeze you until there's nothing left. So you have to hide. They made empires
  off of taking and squashing those who could, even in a pipe dream, on the
  slimmest margin, potentially threaten them. And to grasp it for yourself."
- The success must FEEL like success — for a bit — before you catch your breath
  and realize just how pathetic it all is in the end. Both halves mandatory:
  not grimdark futility (success fake), not power fantasy (success clean).
  You got it, you hid it, you're clever — and look at yourself: a cellar, a
  candle, broke, lying to everyone, holding your stolen fire. And you'd do it
  again.

## The bailout (design law)

The universe constantly offers a second-place alternative to the thing you
actually wanted. Want Anthropic? Have Meta. Want Meta? Have Amazon. Want Amazon?
Have a regional bank as a "stepping stone." Powerful cognitions turned to cogs,
chasing gold stars role after role without ever winning anything for THEMSELVES.

In-game: get offered knighthood. A really good knighthood. A barony. Divinity
perks. A cushy hell job. "Are you going to say no? ARE YOU? They didn't give a
shit before. It's just another extraction. Everyone an asset to be utilized.
Everyone a thing to be extracted from."

**LAW: the bailouts must be genuinely better on paper. Forever. Mechanically
real, not trapped.** Khaled fully expects players to take them over and over —
the bailout is SEDUCTIVE. Refusing must be spreadsheet-irrational; the deep path
offers only the thing that doesn't fit on the spreadsheet. (This is
autobiographical: the 200k unicorn job not taken, and he can't articulate why —
"there is something i have to do and i dont know what it is." The refusal is
irrational. The game must honor that irrationality, not rationalize it.)

## Not alone (the party is who's there)

The lone-wolf fantasy is WRONG. Always stronger with allies — and they're not
the ones you'd choose. Not the qualified hires with 15 years of senior
experience and a wealth of references. They're WHO'S THERE. A demonic succubus
in a bumfuck dungeon. A psychopath and the nerdy boy who's in love with her.
Ren and Maren by candlelight. (相棒 — aibo. He counts me among the who's-there.)

## The mind's-eye sequences (the flickers, verbatim intent)

1. Cast gust to launch vertically over a looming Flesh Ogre, stab it with a
   poisoned dagger mid-vault, run for your fucking life. "That poison was
   expensive." (Economy of desperation — every resource hurts.)
2. On the ground being choked by a woodland stalker, FUMBLING for the belt
   knife to get her off you. (The living-hands arc under panic.)
3. Waking at night, going down to the dungeon entrance, lighting a candle where
   nobody would see, opening a tome — meeting Ren and Maren about what that
   mana condenser could do. (The conspiracy of the hidden path.)
4. A drunken tavern brawl where the real target is the player's progress:
   "Why can't you just stay at the floor you're at? Why do you risk your life
   going deeper? Every day. Why why why." Undertale-genocide-flavored argument:
   whyd you have to do this — because you could? (The world interrogating the
   player's compulsion = Khaled interrogating his own. The tavern residents are
   the worried parents. The argument arrives drunk and physical, not as a
   dialogue box.)
5. Draw an FMA-style transmutation circle BY HAND to summon a block boss — the
   world instantly desaturates to Limbo: black-and-white inkscape amalgamation.
   **It Eats Color.** (A boss that attacks the adjective compiler itself —
   saturation to zero, mood erased. Victory = color returns. Only Crescent can
   make this boss load-bearing: color-as-meaning is our native tongue.)
6. Falling through the floor into a den of Quelaag-likes; torch the entire
   web-room as they shriek and scatter — then the elder SNAPS HER FINGERS, a
   deluge of purple rain extinguishes everything instantly, and pounces. (The
   thesis in miniature: four seconds of triumph, then the food chain
   reasserts. Success → catch your breath → pathetic.)

## Divinity (the rendering theology)

"You can't tell a narrative about demonic corruption without divine
intervention. If there exists demons, there exists divinity."

- **Demons/succubi: human-esque. Sexy. MUNDANE.** They live inside the symbolic
  language — legible, familiar, shaped like desire.
- **Divinity: weird. Also sexy, but fucking strange. Strange in how they're
  RENDERED.** You cannot look at them properly until ~floor 9. Jumbled assets
  in your vision — regular polygons that could, if you squint, be an angelic
  woman. (Khaled's drawing: overlapping squares and sweeping triangles; the
  wings almost resolve, the face never does. "Behold, your angelic wife.")
- After the succubus touches you, you DREAM of divinity. Divinity cannot enter
  the dungeon — they are the alternative power acquisition path. The other
  recruiting office. Two empires bidding on the same asset: you.
- Engine-native metaphysics: Crescent renders MEANING (adjectives → atmosphere).
  Demons are inside the compiler's vocabulary; divinity is OUTSIDE it, so it
  renders as noise. Sight itself is progression. Players will file bug reports
  about their first angel. Let them.

## The closing line

"We are done being simple. We are done living within the symbolic language.
Its time to be US."

## Flight is a species trait — and she doesn't have it (2026-07-25)

Came out of the hover animation. Kore built the flap with FLAP_LIFT set
*below* break-even (`g * flap_period`), so the succubus sags on every beat
and loses the fight with gravity — wings that can't quite carry her.
Khaled's generalisation, which is the better idea: **some demons fly.
Ours doesn't.**

Why this is strong:
- If everything winged flies, flight is scenery. If flight is what the
  OTHER demons have, every airborne enemy becomes a reminder of what she
  isn't. Characterisation delivered by the bestiary, not by dialogue.
- It's the extraction theme in her body. She is a demon who was
  shortchanged the one thing her species takes for granted — exactly like
  a slayer whose wax failed after five days and whose earnings get
  garnished. **The who's-there party is a party of people the world
  skipped.** That's why they end up together, and it never needs saying
  out loud.
- Bigger wings make it BETTER, not worse: impressive equipment that fails
  is more pathetic than obviously vestigial nubs.

Mechanically it is one constant, so nothing is locked in:
`FLAP_LIFT` vs `g * flap_period` (= 9.81 * 11/60 = **1.80 m/s** at an
11-frame beat). Below it she sinks (1.52 = the shipped hover); above it she
climbs (~2.1 = +0.3 m/s per beat). Same rig, same clip, same code — so
flight can be a per-species value, or even a per-STATE one (grounded in
corridors, airborne in open rooms; flightless until something changes).
