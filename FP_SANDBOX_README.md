# FP Pose Sandbox — open `fp_sandbox.blend`

## What it is
The **shipped** `fp_hands.glb`, on the **idle_sword** pose, seen through the
**actual slayer2 viewmodel camera**. What you see is what the player sees.

Camera is not a guess — it is `games/slayer2/client/game.js:1563`:
`fov: 54`, `offset: [0, -0.22, -0.45]` (rig pushed 0.22 m down, 0.45 m
forward), which puts the eye at blender `(0, -0.45, 0.22)` looking +Y.

## How to use it
1. Open it, hover the viewport, hit **Numpad 0** → you are looking through
   `FP_EYE`. Judge everything from this view.
2. **The fix is mostly OBJECT MODE, not pose mode.** Your complaint is
   placement, and placement lives on the armature objects:
   - `Armature.001` = **RIGHT** arm (sword hand)
   - `Armature.003` = **LEFT** arm (the upended one)
   - click one → **G** move, **R** rotate, **S** scale
   - to make the left hand **invisible**: select it and press **H**
     (I read the hidden flag)
   - to make it **smaller**: **S**, then drag / type a number
3. Finger + wrist tweaks: **Tab** into Pose Mode, click a bone, **R**.
4. **Ctrl+S**, then tell me. I read every object transform, every posed bone,
   and each arm's on-screen footprint.

## Current numbers (what you are complaining about, measured)
```
RIGHT  eats 19% width x 55% height of frame
LEFT   eats 20% width x 76% height of frame   <- taller than the right
```
Both run off the bottom edge — that is the forearm.

## Two different levers (worth knowing before you move things)
- **Both arms together** (less forearm, more hand) can ALSO be done for free
  by changing Sable's `offset` in game.js — no re-export. Pull the rig back
  and up and the forearms leave frame.
- **The left arm specifically** (hide / shrink / re-pose) has to come from
  the rig, which means a re-export of `fp_hands.glb`.
  So: pose it here, and I will port it.

## Known gap
`Silverlight` is imported but **hidden** — blender bone-parenting adds a
tail-length frame the seat matrix does not account for, so it lands off in
space. A wrong sword is worse than no sword while judging framing. Unhide it
in the outliner if you want to fight it.
