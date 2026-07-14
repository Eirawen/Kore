# First-Person Casting & Combat Animation Design

Khaled's spec, 2026-07-10. This is the "Wizard Wars" dream — the first-person
animative experience of casting that he says no game ever gets right. Treat
these as sacred; they're his babies.

## Core thesis

**The casting animation IS the element's philosophy, argued through the body.**
Most games fail here — generic "wave hands, thing appears," a generic emitter
with a generic flourish. Every Crescent spell gets a DISTINCT cast whose
*gesture embodies what the element IS*.

## Unifying grammar

- **Release** — a single unified palm-out forward fling for air / water / fire.
  Earth is the exception (fist punch forward).
- **Symmetry encodes philosophy:**
  - Air — symmetric, both hands (the seal); asymmetric only at the release.
  - Water — symmetric, both hands (the prayer clasp); asymmetric only at release.
  - Fire — asymmetric, ONE hand.
  - Earth — asymmetric, BOTH arms (labor).
- **Manifestation encodes philosophy** (this is the VFX anchor for later):
  - Air — the orb FADES IN already spinning. Air is always present; casting =
    ordering it. Forms in the GAP between the sideways-stacked hands.
  - Water — comes into being flowing, directed. Forms in the GAP of the clasp.
  - Fire — a flicker, then sudden appearance. Willed into being. On the cupped palm.
  - Earth — kicked up from below (left fist down), then propelled (right fist forward).

## The four casts — highest priority ("the babies")

### Air Strike — order from chaos
1. Rest → hands rise into a modified Naruto **monkey seal**: the two forearms
   align into one unbroken (near-vertical) line, hands turned knife-**sideways**
   continuing that line, **one hand above the other**, with a NOTABLE GAP between
   the two hands.
2. In the gap, the air orb **fades in already spinning** — it does NOT swell up
   from nothing.
3. The **bottom palm rotates 90°** to face fingers-to-the-sky, palm outward.
4. Release — palm-out fling forward.

### Water Strike — flow given direction
1. Rest → both arms **sweep up**.
2. Palms opposite each other, **fingers up** — like clasping hands in prayer, but
   with a GAP (not touching, "not quite").
3. The water orb comes into being in the gap, flowing / directed.
4. Release — palm-out fling forward (unified release, same as air).

### Fire Strike — will made manifest (simplest)
1. ONE hand: palm UP, cupped, fingers to the horizon (pointing forward).
2. A flicker — fire appears (sudden, willed).
3. Release — palm-out fling forward.
Asymmetric, single hand. Fire needs no ritual, only the will to manifest.

### Earth Strike — labor ("Strike the earth!")
1. **Left fist punches DOWN** — kicks up the plot of earth. Superhero-landing
   gesture: arm straight, vertical, fist down. Does NOT literally touch ground —
   it's gestural.
2. **Right fist punches FORWARD** — propels the plot of earth outward.
Asymmetric, both arms, fists. Earth is the only cast that is *work*.

## Melee & throwables — lower priority, captured for later

- **Idle** — resting hands, subtle breathing sway.
- **Knife throw, blade-first** — pinch grip (thumb + index + middle pinch the
  blade flat, ring/pinky curled), draw back beside the head, wrist flick, release,
  follow-through. Precision throw.
- **Knife throw, handle-first** — full hammer grip, cocked back, whole-arm hurl
  with a wrist snap. Power throw.
- **Round-object throw** (potion / small clay sphere / rock / bottle) — overhand
  lob, cupped grip, arc. The sum of the throwables.
- **Bow draw** (low priority) — lead hand extends gripping the bow, draw hand
  pulls the string back to an anchor near the cheek, hold, release.
- **Sword light** — loose grip, quick wrist-led slash, fast recovery. Can redirect.
- **Sword heavy** — death grip, big wind-up (arm raises high), committed chop down,
  slow recovery. The swing that doesn't let go.
- **Sword thrust** — blade leads straight forward, shoulder/hip drive, quick retract.
- **Sword guard** — blade raised across the body, defensive, held.
- **Sword parry** — BELOVED. Do it as a TRUE swordsman would. Use the **forte**
  (the strong, the third of the blade nearest the guard/handle) against the
  **foible** (the weak, the third nearest their tip). A deflection / beat that
  catches their weak with our strong and turns it aside — NOT a flat block. Small,
  efficient, bladework-correct, and it ends in a position to riposte. "Forte that shit."

## Rig constraints (slayer_hands_clean.glb / cgtrader rig)

- Two hands, 20 bones each, hand-painted weights, quad topology.
- **NO elbow joint.** The forearm is rigid geometry riding the wrist/root bone.
  Gross arm motion = animate the whole hand-object transform (position + rotation).
  Hand *shape* = wrist + finger bones. Wrist-vs-forearm may be one rigid unit;
  probe before assuming independent wrist roll.
- **Curl convention:** rotation about each finger bone's LOCAL X, POSITIVE = curl
  toward the palm (verified).
- **First-person staging is already solved** in `tools/render_hands_fp.py` — hands
  at ±X, first-person camera, left hand mirrored (scale.x = -1 + normal flip),
  forearms crop off the bottom of frame. Extend that script for animation.

## Deliverable format for animation review

Author keyframes; render N evenly-spaced frames across the timeline; montage into
a labeled grid (Vetinari-style, read left→right / top→bottom = time). One grid per
animation shows the whole arc of motion. Video/MP4 optional later.
