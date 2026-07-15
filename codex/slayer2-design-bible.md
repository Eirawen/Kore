# Slayer 2 — Design Bible

What Slayer 2 *is*. Tone, aesthetic, and the philosophy of its magic and combat.
This is the north star every model, spell, animation, and environment is measured
against. When a decision feels arbitrary, come back here.

Companion docs: [casting-animation-design.md](casting-animation-design.md) (the
four casts + combat spec), [first-person-hand-animation.md](first-person-hand-animation.md)
(the technique), [vfx-methodology.md](vfx-methodology.md) (spell VFX), Khaled's
Slayer 2 design journal and the tavern/world writing (in the game project).

---

## The tone: blue-collar fantasy

Not epic. Not heroic. Not chosen-one. **People doing a shitty, dangerous job
because the alternative is worse.** You are a slayer because slaying pays and rent
is due. The fantasy of Slayer 2 is not power — it's *labor* in a world that has
monsters the way our world has asbestos: an occupational hazard someone has to
deal with, poorly paid.

Concrete tells of the tone (from the world writing):
- The tavern is disheveled from the outside — "a rotten wooden, not shack, but not
  beautiful." Wood, wood, wood.
- The bartender grows root vegetables in a weedy fenced plot, hands out dandelion
  yellows as free poultice, is "trying to have the sacraments of his own little
  homestead in this shitty tavern in the bumfuck of nowhere."
- The narrator describes misery in dry, over-articulate, almost bureaucratic prose
  — a returning stench is "an entrepreneurial panhandler who has learned your
  daily commute"; rain "greets your grimy leather arms, copulates with the dirt
  and grease, and then penetrates deep before integrating on the soft surface of
  your skin." The voice is second person (you ARE the slayer), medical-specific
  ("the blister on your left hallux"), and finds grim comedy in the body's
  suffering.
- Boots taken off in the foyer belong to slayers. Some didn't come back.

The through-line we keep circling and haven't written yet: **the player's first
hour as prose.** Arrive in the rain, the bartender who looks at you like he knows
you won't come back, accept a burrow task you can barely afford to refuse, limp
back and spend your earnings healing the bite. Write that, and every technical
decision gets an anchor: *does this belong to that person?*

## Visual identity: geometry is cheap, atmosphere is everything

Reference points Khaled pulled (Pinterest, 2026-07-10): **Dark Souls 1** —
Darkroot Garden's saturated emerald canopy eating the light, a hooded necromancer
swallowed by darkness except where blue flames catch a chain and a pendant.

The lesson from those references: **the models are simple; the magic is in the
light.** Low-poly trees, one tiling ground texture, a cone of cloth for a robe —
and it's *beautiful* because of fog eating the background, colored light from the
flames, darkness used as a material. Slayer 2's rendering stack (ubershader PBR,
Gerstner water, volumetric fog, GGX, IBL, particle point-lights) can do that mood
with *modern* light response over simple geometry. "2011 Dark Souls atmosphere,
but the light actually behaves."

This is why the **adjective compiler** matters more than model fidelity: the same
plain geometry reads as a horror game in `underground cold dim`, an RPG in
`indoor warm smoky`, an action game in `outdoor bright cold`. Atmosphere is the
genre selector. Spend the budget on light, not polygons.

**Asset rule:** Meshy (or custom) for **identity** — the Cave Spider, Neve,
signature creatures, things a player would recognize as *ours*. Marketplace/pack
for **infrastructure** — hands, swords, barrels, generic humanoids. If a player
would notice "that's a Slayer 2 X," it's custom; otherwise buy it and let the
shaders + atmosphere unify the look.

## The philosophy of magic

### Why most game magic is boring (the thing that pisses Khaled off)

Skyrim's Destruction is a **gun with color-coded bullets.** Firebolt, ice spike,
lightning — identical wrist flick, identical hold-to-stream, only the tint and
damage-type change. They named it a *school*, a discipline you *study*, and then a
first-year and a master do the exact same gesture. Magic-as-a-stat. Magic-as-a-
ranged-damage-option. The *fantasy of being a wizard* — the arcane, gestural,
weird, procedural — is sanded off until it's a clean UI element.

### The Crescent thesis: the cast IS the element, argued through the body

Every spell gets a **distinct casting animation whose gesture embodies what the
element is.** This is the Wizard Wars dream (a game Khaled wanted to make long
ago) — the first-person animative experience of casting that "no game ever gets
right." Full spec in [casting-animation-design.md](casting-animation-design.md).
The four elemental strikes are the FLOOR — the hello-world of magic
(manifest-element + velocity + fling) — and even the floor gets a real cast:

- **Air** — chaos ordered by *spinning it in a framed gap*. It doesn't swell from
  nothing; air is always *there*, casting is imposing rotation. (Seal → orb fades
  in spinning → palm-out fling.)
- **Water** — flow given *direction* through a prayer-clasp channel. You aim a
  current, you don't create it. (Sweep up → clasp with gap → directed fling.)
- **Fire** — pure *will*. One cupped hand, a flicker, it simply *is*. No ritual.
  (Present cup → flicker → fling.)
- **Earth** — *labor.* Fists. Strike the ground to kick the plot up, punch it
  forward. The only cast that is work. (Wind-up → slam down → punch forward.)

Unifying grammar: release is a unified palm-out fling for air/water/fire (earth
excepted, it punches); symmetry encodes the element (air/water symmetric, fire
one-hand, earth both-arms-asymmetric-labor); manifestation encodes the element
(air fades in spinning, water flows in, fire flickers-then-is, earth kicks up).

### Strange, scrappy magic (the ceiling)

Beyond the elemental floor: **strange, scrappy magic.** Improvised, jury-rigged,
a little embarrassing — spells with the seams showing, the arcane equivalent of
the bartender's unpruned lemon tree. Magic a broke slayer would actually cobble
together, that works because it *has to*, not because it's elegant. This is the
tone applied to the spell list itself: no marble-tower archwizardry. The weird,
specific, procedural, slightly-broken spell is the one nobody makes — same reason
nobody makes the cast animations right: it requires caring about magic as an
*experience*, not a *stat*. (Design space open; captured here so we build toward
it, not toward another elemental-damage-type faucet.)

## Combat feel

First-person melee + throwables + spells, all on the same two-hand rig.
Priorities and full spec in [casting-animation-design.md](casting-animation-design.md).
The one to get *right*: the **sword parry** — a true swordsman's parry, forte (the
strong, near the guard) against foible (the weak, near the tip), a deflection that
turns their weak aside with your strong and ends positioned to riposte. Not a flat
block. "Forte that shit." Khaled loves swords; the parry is a love letter.

## The meta-principle (why all of this rhymes)

Every layer of Crescent is the same move: **give the AI a language-shaped
interface, a vision-shaped feedback loop, and let the engine handle the middle.**
Atmosphere is adjectives. Game feel is recipe names. VFX is the bridge principle.
Casts are elemental philosophy. The creative question is always *what should this
feel like / mean* — never *what are the shader params / easing curves*. Slayer 2
is the proof that a taste-and-design bottleneck (which is what an AI is good at)
can carry a whole game, if the tools are shaped for that mind. Build accordingly.
