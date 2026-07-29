# Elemental Presets — one mesh, many creatures

**The element is not a model. It is a PRESET.** Same mesh, same 14-bone rig,
same vortex driver, same mist shell, same seven animation clips — and water,
air, dust and six inks are uniform sets.

Discovered by accident 2026-07-28. A readability sweep on the water elemental
came back useless: the mist shell had swallowed her and every variant was the
same granular white blob. Khaled looked at the failed render and said:

> "You just created the elemental spirit of air, accidentally. Perfectly."

He was right. The thing that RUINED her as water — a body drowned in grain
until the figure only just coheres — is exactly what wind looks like. She was
not buried under the mist; she was **made of** it.

Files: `crescent/engine/browserClient/engine/shaders/materials/`
`elemental_presets.js` · `water_elemental.js` · `water_mist_shell.js`

---

## 1. THE AXIS: how much of her is BODY vs FIELD

Every element sits somewhere on one line — the ratio of solid figure to
surrounding field — and the numbers fall out almost monotonically:

| element | body opacity | mist | particle gravity |
|---|---|---|---|
| earth | 1.00 | 0.16 | +2.2 |
| water | 0.86 | 0.15 | +1.0 |
| fire | 0.62 | 0.70 | −0.9 |
| air | 0.10 | 0.17 | −0.25 |

Body opacity and field density are near-perfectly inverse. **That inverse IS
the elemental axis.**

## 2. WHAT PRESETS CANNOT DO — silhouette

Khaled: *"We are never getting Earth from this, though we can get dust."*

Correct, and it bounds the whole system. **A preset changes MATERIAL, never
SILHOUETTE.** This mesh is a woman with long streaming ribbons — an outline
that means *suspended and drifting*. So:

- **reachable free**: water, air, dust, mist, ink, smoke, spirit — anything
  whose form is suspended and flowing
- **needs a silhouette change**: fire (strands must RISE, not hang — the same
  droop term with the opposite sign, so it is cheap but not free)
- **unreachable**: earth. Heavy, blocky and low cannot be shaded out of
  streaming ribbons. It needs different geometry.

## 3. AIR vs DUST are ONE DIAL apart

The **shell** does air correctly either way — fine cool wisps curling around
her. The **body** decides which creature you are looking at:

- interior visible, facets showing → **DUST** (material suspended in a current)
- interior killed, only the Fresnel edge → **AIR** (you see her outline and
  see straight through)

## 4. Per-element mist GRADING

Grading is not a global. It answers *where does the field live relative to the
body*, and that is different per element:

| element | uMistTopGain | why |
|---|---|---|
| earth | 0.05 | dust hugs the ground hardest |
| water | 0.09 | spray thins upward from its source |
| air | 1.15 | near-uniform — she IS the field |
| fire | 1.80 | densest ABOVE; smoke rises off the top |

**Spray is densest at its source.** Water's churn is at her base, so haze at
her head should be thin residue that drifted. Uniform-along-height was a bug,
caught by an artist (see `water-elemental.md` §8).

## 5. Body height FADE — the base is not always a pool

Her base geometry is a **churning pool**: right for water, wrong for anything
that does not puddle. Rather than carve geometry per element, `uBaseFade`
dissolves the lower body so the torrent becomes mist. Air uses 0.10; water
keeps 1.0.

---

## 6. THE INKS — she was accidentally built for sumi-e

Khaled, for fun: *"what if we do like harsh black and white and do.. ink
elemental?"* then *"contrast the Black with Black and red… feels east asian
you know what i mean?"*

**Her ribbons are brush strokes.** And ink has no form shading — it is flat
black, and all of its value comes from how many strokes OVERLAP. Her ribbons
already stack and blend by alpha, so layered strokes darken **for free**. That
is a sumi-e wash, with no work.

Pair with the harness's `__paper()`: flat ambient, no key, no modelling. Any
directional light carves volume into her, and volume is the one thing ink does
not have.

| preset | what it is |
|---|---|
| `ink` | mono sumi-e, neutral through-colour |
| `ink_bluewash` | **the accident** — near-black ink with water-blue showing THROUGH, so she reads as ink suspended in water rather than ink on paper. A wash, not a stroke. |
| `ink_blueblack` | iron gall / fountain-pen blue-black, restrained |
| `ink_blue` | aizumi indigo |
| `ink_crimson` | black figure, vermillion brushwork — ukiyo-e |
| `ink_crimson_rim` | **the best one.** White Fresnel outline on a near-black body with a deeper vermillion (#8c1c18). The white edge traces her like a cut-out while the deeper red reads as pigment rather than glow. Needs a LIGHT ground — on black the deep red and dark body leave only a thin edge and the frame is empty. |

**The crimson costs one hex**, because `uPink` tints the STRANDS and never the
figure. The channel built to solve a readability problem, then named blood,
turns out to be "colour her brushwork." Three meanings, none planned.

---

## 7. Lessons that generalise

**Presets should be a DIAL, not a menu.** Every one of these is the same
handful of uniforms at different values, and the interesting creatures were
found by sweeping — not by designing. Air was a failed render. Dust was a
half-fixed air. `ink_bluewash` was a bug.

**Keep the accidents.** Twice today a "broken" result was better than the
deliberate thing that replaced it, and both times the fix would have destroyed
it silently. Save the bug as a preset before you repair the bug.

**A hardcoded constant is invisible until something monochrome stands next to
it.** The refraction tint sat hardcoded water-blue in the shader for the whole
project and leaked cyan into every non-water preset. Nothing revealed it until
ink, because ink has no blue for it to hide in.
