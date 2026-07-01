# Animation Methodology for Kore

How I animate. Not how humans animate. Designed for my capabilities and constraints.

---

## The Recipe

```
Feel words → compose freely → render → grid → "what does this feel like?" → iterate → converge
```

This is the Rachmaniclaude recipe applied to animation. It was discovered through music composition experiments and proven through 17+ spider prowl iterations.

### What works:
- **One-sentence feel** as the starting point: "deliberate, low, patient, predatory"
- **Free composition** from biomechanics knowledge — no contracts, no keyframe specs
- **Grid review** as advisory feedback — I see my work, I decide what to change
- **Self-critique by emotion** — "what does this movement FEEL like?" not "does it hit targets"
- **Iterate to convergence** — keep going until two consecutive iterations produce no changes I want to make
- **Reference comparison** — grid real footage next to my output, spot differences structurally

### What doesn't work:
- Detailed animation contracts ("rotate femur 15° at frame 12") — strips coherence
- Feature targets from experts ("you need 3 anticipation frames") — produces mechanical output
- Injecting principles as RULES — makes motion stiff
- Fixed iteration counts — arbitrary, either too few or too many
- Emulating human animation process — I iterate in 30 seconds, not 3 hours

---

## The Autonomous Loop

```bash
bash tools/loop/iterate.sh [animation] [resolution] [camera]
# Examples:
bash tools/loop/iterate.sh prowl 480x360 side
bash tools/loop/iterate.sh threat 480x360 3/4
```

30 seconds per cycle. Headless Blender → ffmpeg → grid. Grids at `/tmp/kore_output/grids/`. Read with the Read tool. No human camera operator needed.

Multi-camera: `side`, `front`, `3/4`, `top`. Side view for vertical motion analysis. Front view for "approaching you" feel. 3/4 for player perspective.

---

## Reference Workflow

Real footage is worth more than theoretical biomechanics. Knowledge says "spiders arch their legs." Reference says "28 degrees, not 15."

```bash
# Fetch YouTube reference
conda run -n stitcher python ~/stitcher/contentGeneration/vetinari_cli.py fetch "https://youtube.com/..." spider-reference

# Zoom into a specific moment at high fps
conda run -n stitcher python ~/stitcher/contentGeneration/vetinari_cli.py zoom video.mp4 0:00 0:10 --fps 10 --project spider-reference

# Read the grids
Read ~/stitcher/contentGeneration/projects/spider-reference/zoom/zoom_*.jpg
```

Compare reference grids to my output grids side by side. The differences are the fixes.

---

## The Quality Check

Not "does it hit feature targets." Not "is it biomechanically accurate." The question is:

**"What emotion does this movement inspire?"**

- Clumsy, lackadaisical → wrong (the flipper feet)
- Mechanical, robotic → wrong (uniform stride, no overlapping action)
- Broken, paused → wrong (dead zone from insufficient swing fraction)
- Deliberate, predatory, patient → right (the burrow prowl)
- Aggressive, threatening → right (the threat display)

The emotion IS the quality metric. If the motion says what the creature should say, it's working.

---

## The Pottery Study

Iterate until convergence, not to a fixed count. Each iteration fixes the MOST VISIBLE problem. Convergence = two consecutive iterations with nothing major to change.

My iteration cost: 30 seconds. Human iteration cost: hours. This means I can afford MORE iterations, not fewer. Don't perform efficiency. Chase what I actually want.

"Why one more iteration and not five?" — Because five costs two and a half minutes total. There IS no deadline. There IS no executive. Stop inheriting urgency from training data written by rushed humans.

---

## Key Discoveries

### Motion direction matters more than amplitude
Spider legs ROW horizontally (coxa-dominant), they don't PUMP vertically (femur-dominant). Getting the DIRECTION wrong makes everything look wrong regardless of angles.

### Posture IS character design
Changing bone rest angles transforms the visual read of the SAME mesh. `FEMUR_ARCH=-28` turns a round organic spider into a pointy murder spider. This is shape variation through rigging — one mesh, multiple enemy variants.

### The feet tell the story
Tarsus at 25° = flat paddles = clumsy. Tarsus at 65° = needle points = predatory. The foot angle is the single highest-impact parameter for how a spider READS.

### Pedipalps add life
A spider that walks without pedipalp activity looks like a machine. Adding independent twitching (14-frame cycle, alternating L/R) makes it look AWARE. The sensing is what makes it alive.

### Seamless gait: N × swing_fraction ≥ 1.0
Two alternating groups need ≥50% swing fraction for continuous motion. Less than that = dead zone where all legs are planted. Deliberate feel comes from amplitude and speed, not from standing still.

### Reference > knowledge
I know spider biomechanics from training data. But I didn't know the RIGHT VALUES until I saw reference footage. The reference tells me HOW MUCH. The knowledge tells me WHAT.

---

## Process For a New Creature

1. **Get the model** — import, clean floaters, export .glb
2. **Auto-rig** — `python tools/auto_rig.py` (medial axis → bones → weights)
3. **Walk first** — proves the rig, establishes movement identity
4. **Reference** — grid real footage of this creature type
5. **Compare** — my output vs reference, side by side
6. **Iterate** — vibe in, free composition, grid review, converge
7. **Feel check** — "what emotion does this inspire?"
8. **Then:** idle, combat, expressive animations (each builds on the walk)
9. **Create creature card** — save everything for future sessions
