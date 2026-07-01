# Cave Spider — Slayer 2

Burrow enemy. `underground warm dusty`. Poisons on hit.

---

## Feel

**Deliberate. Low. Patient. Predatory.** Owns the cave. Doesn't chase — waits for slayers. Moves with the certainty of something that has never been in danger in its territory. The player should feel like an intruder.

From the design journal: "Blue-collar fantasy. Not epic. Not heroic. People doing a shitty dangerous job because the alternative is worse." The spider is part of that world. It's doing its job too.

---

## Model

- Source: Meshy text-to-3D, cleaned in Blender
- Vertices: ~3000 (low-poly stylized)
- Legs: 6 (Meshy's interpretation — missing 2 from real spider)
- File: `spider.glb`
- Known issues: triangle soup topology, some joints have limited deformation geometry

---

## Rig

- Pipeline: `python tools/auto_rig.py` → `tools/rig_spider_auto.py`
- Bones per leg: 4 (coxa/femur/tibia/tarsus) — all legs have tarsus after min_seg fix
- Weights: two-layer (branch segmentation + rigid chitin plates)
- Must run `transform_apply` before rigging (90° glTF rotation)
- Bone chain: body→foot (reversed from medial axis trace direction)

---

## Posture Parameters (the murder spider)

These transform the round mesh into angular blade geometry:

```python
FEMUR_ARCH = -28     # steep tent-pole arch — body hangs below
TIBIA_DROP = 18      # steep return to ground — sharp knee bend
TARSUS_TIPTOE = 65   # nearly vertical — needle point contact
FORWARD_LEAN = -3    # cephalothorax tilted toward prey
```

For a DOCILE variant (same mesh, different personality):
```python
FEMUR_ARCH = -8      # gentle arch — body higher
TIBIA_DROP = 5       # gradual slope — soft curves
TARSUS_TIPTOE = 15   # low angle — flat, unthreatening
FORWARD_LEAN = 0     # level — not approaching
```

---

## Animation: Burrow Prowl (`animate_prowl.py`)

### Motion philosophy
**Rowing, not pumping.** Coxa is the primary actuator — swings the leg FORWARD (reach), plants, then DRAGS BACKWARD (pull). Femur lift is secondary — just enough to clear the ground. The motion is horizontal, not vertical.

### Parameters
```python
COXA_SWING = 14      # primary — forward reach, backward pull
FEMUR_LIFT = 6       # secondary — ground clearance only
TIBIA_BEND = 4       # minimal
CYCLE_FRAMES = 36    # ~1.5 seconds at 24fps
SWING_FRACTION = 0.50 # seamless — no dead zone
OVERLAP = 2          # overlapping action delay
```

### Front/mid/rear differentiation
- Front legs: 1.4x lift, 1.5x reach — EXPLORATORY, sensing for prey
- Mid legs: 1.0x — workhorses
- Rear legs: 0.7x lift, 0.6x reach — compact PUSHERS

### Front leg hover
Front legs hold their reach for a beat before planting — testing the space. This is what makes them feel like sensors, not just legs.

### Pedipalps
Independent 14-frame twitch cycle. Alternating L/R. Always sensing. Not tied to the gait.

### Body
- Forward lean: -3° constant (approaching, not standing)
- Body bob: 1.0° (subtle)
- Body sway: 0.8° (minimal — controlled)

---

## Animation: Threat Display (`animate_threat.py`)

Anticipation → rear up → front legs raised → fangs spread → shimmy → snap down.
Bone-local axes. Overlapping action (FL arrives 2 frames before FR). Linear interpolation on the snap-down for sudden drop.

---

## Animation: Pedipalp Sensing (`animate_feel.py`)

Alternating L/R pedipalp reach-curl-retract. Body leans toward active palp. Fangs twitch during probing. Idle/sensing animation.

---

## Animation: Walk Cycle (`animate_walk.py`)

Generic alternating tripod. 48-frame cycle. Less character than the prowl. Used as the base before the prowl was developed.

---

## Gotchas Specific to This Model

1. **Mid-leg tarsus was being eaten by min_seg filter** — the tarsus is short (~2cm), the 3cm floor merged it into the tibia. Fixed by keeping endpoint segments always.
2. **3k mesh limits deformation** — keep rotations under ~30° at joints or the mesh tears visibly.
3. **Flipper feet** — tarsus curl during swing (negative angle) causes outward splay. Keep tarsus at constant TARSUS_TIPTOE throughout the cycle. No swing curl.
4. **Dead zone at 35% swing** — two groups × 35% = 70% coverage. Bumped to 50% for seamless gait.
5. **Bone-local axes required** — `rotation_quaternion` is in bone-local space. Must transform armature-space axes via `bone.matrix_local.to_3x3().inverted()`.

---

## Reference

YouTube spider walk cycle grids at:
`~/stitcher/contentGeneration/projects/spider-reference/zoom/`

The reference taught what biomechanics couldn't:
- Arch steepness (28°, not 15°)
- Foot angle (65°, not 25°)
- Rowing gait (coxa-dominant, not femur-dominant)
