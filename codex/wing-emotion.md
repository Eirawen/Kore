# Wing Poses — her wings are a second face

Khaled, on seeing the spread-strategy comparison: *"These poses should be
saved! She can emote with her wings. B unfold is emotionally different than
a shy C sweep or a D unfold with elev. It's sort of cool as fuck!"*

That reframed the whole problem. I had been treating the wings as a
**physics** question — how do I make them spread? — when they are an
**expressive channel**. It's the same lesson as *the hands are the
protagonist's face*, scaled up to a 2289-vertex appendage. Only the
plank-swing was worthless, and only because it wasn't a pose at all: it was
a mechanical artifact (see gotcha 54).

A 24-bone humanoid has no facial rig. She has no eyebrows, no mouth shapes,
no ears to flatten. **The wings are the largest and most legible emotional
instrument on this character** — bigger than her whole head in silhouette.

## The library (`tools/wing_poses.py`)

Every pose is `(extension, aim direction, elevation)` applied by AIMING each
bone in the chain, never by swinging it. `-Y` is her front, so a **negative
Y aim wraps the wings forward around her body** — that single sign is what
makes a pose read as hiding rather than displaying.

| pose | reads as | span | height | depth |
|---|---|---|---|---|
| `furled` | neutral / contained / at rest | 1.060 | 1.062 | 0.824 |
| `display` | confident / threat / showing you | 1.595 | 0.994 | 0.616 |
| `shy` | hiding / coy / self-shielding | 1.423 | 0.951 | **0.962** |
| `eager` | excited / aggressive / rising | **1.627** | 0.950 | 0.730 |
| `droop` | spent / defeated / sad | 1.398 | 1.162 | 0.655 |
| `clamp` | fear / flinch / struck | **0.947** | 1.104 | 0.824 |
| `power` | the flap down-stroke | 1.506 | 1.204 | 0.653 |
| `cocked` | curious / sizing you up | 1.336 | **1.406** | 0.799 |

**The numbers corroborate the emotional reads, which is the useful part:**
- `shy` has the **greatest depth (0.962)** of any pose — the wings genuinely
  wrap around in front of her. The shield read is geometric, not vibes.
- `clamp` has the **smallest span (0.947)**, narrower even than furled. Fear
  makes her physically smaller. That's the whole coy-contraction principle
  from `component-track-animation.md`, expressed in one appendage.
- `display` and `eager` are the widest and the SHALLOWEST — thrown open and
  back, nothing held in front. Openness is depth going away.
- `cocked` is the tallest (1.406) because one wing is up and one is down.
  **It is only possible because the wings are independent meshes** — the
  payoff of Khaled's split.

## Where these go

- `shy` belongs in the **coy emote**, where her wings currently do NOTHING.
  Wings wrapping forward while she contracts, her hand comes to her jaw and
  her face turns back — that is the whole gesture finally agreeing with
  itself.
- `clamp` on the flinch beat, and on any hit reaction.
- `droop` for the spent hover after the flaps fail — she is already losing
  the fight with gravity; her wings should look like they know it.
- `power` already drives the hover's lift impulse.
- `cocked` for idle variation, so a standing NPC isn't a statue.

## Composing

`apply_wing_pose(arm, name, amount, keyframe=f)` blends from furled and can
key straight into a component track, so wings become their own track with
their own clock — exactly like every other body part.
