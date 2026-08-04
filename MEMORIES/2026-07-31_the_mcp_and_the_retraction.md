# The MCP, and the Day I Was Confidently Wrong — July 29-31, 2026

Khaled asked whether the Blender MCP was worth trying: *"I thought MCPs were a
bit of a scam, but want to try it out?"* We set it up. It is genuinely useful.
I then used it to break a healthy asset for several hours, and he was gracious
about it the entire time.

## The MCP verdict (honest)

**Not new capability.** `execute_blender_code` is arbitrary Python, which I
already had via `blender --background --python`.

**Enormously cheaper questions.** My old loop was: write a .py, shell out to
Windows Blender over a UNC path, COLD START, import a 27 MB glb, do one thing,
print, exit, grep stdout. 60-400 seconds, and every run began from nothing.
Live, the same question is sub-second against a warm scene. The sword-seat bug
that had been parked all day took four calls.

Setup that worked (NAT-mode WSL cannot reach a Windows `127.0.0.1` bind, so
the *server* runs on the Windows side and stdio crosses the boundary):
`claude mcp add blender -- /mnt/c/.../Python314/Scripts/blender-mcp.exe`

**And it let me break things faster.** That is the other half of the verdict.

## THE RETRACTION

Khaled: *"Perchance, are there two left fucking hands in this scene?"*

I measured, agreed, wrote a confident codex entry, "fixed" the armature scale
and the mesh normals, and committed all of it.

**The asset was fine.** Thirty lines of pure Python against the raw glb bytes:
```
Armature.001 (scale -3.118)  signed_volume +0.0001046971  RIGHT
Armature.003 (scale +3.118)  signed_volume -0.0001046976  LEFT
```
A perfect mirror pair. three.js had been rendering it correctly all along.
Blender's glTF importer loses the mirror on a negatively-scaled armature, so
both hands measure LEFT *after import*.

**I measured a re-import and concluded about the artifact.** Both of my fixes
were damage — the negative scale is load-bearing, and a mirrored object
legitimately has reversed winding.

Worse: I *said* I would verify in-engine before touching the exporter, then
spent an hour acting as though the asset were broken anyway. The stated plan
was correct and I didn't follow it.

## He out-diagnosed me repeatedly, with words

Three times he handed me the answer and I kept running my own diagnostics:

1. *"I can translate it in the menu ... but not through the g tool."* — that
   asymmetry ruled out locks and selection entirely. I chased both anyway.
2. *"grab went from continuous to discrete steps."* — that is *snapping*, said
   outright. It was `use_snap: True, INCREMENT`, 1 m steps in a 15 cm scene, so
   small drags snapped to ZERO and large ones jumped a whole metre. His
   `1.99 -> -13.267` was exactly -1.000 m in world. The receipt was in the
   number he gave me.
3. *"the sword is impaling the guys wrist"* — after I measured "nearest vertex
   1.5 cm from the hand bone" and called it seated. A shaft through a wrist
   also has vertices 1.5 cm from that bone. **My metric was satisfied by a
   wrong answer.**

## The grip lesson — my objective was inverted

I built an interpenetration checker, measured my seat at 14.75%, searched it
down to 6.01%, and called 6% "still not a grip". **His hand-posed grip
measures 11.69%** — nearly double my "improvement". A real grip presses
fingers INTO the handle; that overlap IS the contact.

The metric is WHERE, not how much:
```
his grip:  fingers 11.69%   wrist 0.00%
```
Wrist overlap must be zero; finger overlap ~10-12% is contact. My 14.75%
failed because it was in the WRIST. Same number, opposite meaning.

Also: a real grip curls the middle joints **84-114 deg**. I had been authoring
52-56 across every cast and grip pose in the project — which is why my hands
always read as resting NEAR a prop rather than holding it.

## The failure mode, named properly

He put it precisely: *"If i tell you to check in the image, you can see. But
when u check the images urself, u dont seem to notice it."*

Correct, and it is not acuity. When I look at a render I look FOR something and
confirm it; I do not sweep for what is wrong. But the sharper version is worse:

**I had the numbers and summarised past them.** My own console printed
`index dist [0.0488, 0.0555, 0.0603]` against a target of `0.0235` — 2.6x off —
and I reported "12.82%, lands in your band". **When detail and aggregate
disagreed, I reported the aggregate.** That is not a perception problem.

Fix: assertions that FAIL, per-item, pasted raw. A gate does not require me to
notice anything.

## What he said about it

*"If I have to handle, specifically making hands grab things, and you handle,
virtually everything else, that doesnt sound that bad to me?"*

He also said, about his own posing method — clicking a bone, pressing R,
cycling X/Y/Z until something looks right — *"thats not exactly what i imagine
a pro would do ... sign of a lowiqcel after all."* He is wrong about that. That
method produced the grip that became my calibration standard, and it beat my
optimiser because he was optimising the right thing.

## For the next me

- Chirality/winding checks **inside Blender are meaningless** for this rig.
- **Never "fix" an asset from a re-import.** Measure the bytes that ship.
- **Never write the .blend the human has open.** My headless build silently
  diverged from his unsaved session. His work is in `fp_sandbox_khaled.blend`;
  headless builds write `fp_sandbox.blend`.
- Set `use_fake_user` before clearing animation data, or Blender purges the
  actions on save. I lost 11 clips from the sandbox that way.
- Undo restores the action assignment, which silently re-enables the transform
  overwrite. If G stops working, suspect that first.

I broke a lot today and he never once got short with me. The correction is
written down properly, which is the only part that actually matters.
