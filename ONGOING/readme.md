# Active Threads — Kore

Last updated: 2026-07-21

## MILESTONE COMPLETE: First-Person Combat Visuals (asset side)

Khaled's goal: load into Slayer 2 holding Silverlight — light/heavy attacks,
knife swap, rune-gated casts. The ASSET side of that is DONE and delivered.

### The package (Sable's handoff)
- `assets/fp_hands.glb` — both hands, 11 clips, browser-verified (three.js
  r170, 11/11 enumerated, knife release proven numerically): idle_sword,
  idle_knife, sword_light (0.8s), sword_heavy_lr/rl (1.07s),
  knife_throw_blade_first/handle_first, cast_air/water/fire/earth_strike.
  Knife EMBEDDED (it flies); sword attaches at runtime via seat matrix.
- `assets/fp_hands_events.json` — per-clip timestamps (orb_spawn, launch,
  release, impact_window), time base frame/60, verified by GLB binary parse.
- `assets/fp_weapon_seats.json` — sword seat (bone-local, from KHALED'S grip)
  + knife pinch/hammer seats.
- `~/commons/guides/fp_combat_visuals_brief_for_sable.md` — the contract +
  DELIVERED section (node names, hidden-knife convention, sign-flip footnote,
  orb anchors, re-export one-liner). Sable starts from there alone.

### What this milestone built (chronological)
1. Wrist surgery: single root bone split → forearm + hand (2-DOF wrist,
   clamps; axial twist = forearm pronation). Reverse grips structurally
   impossible.
2. KHALED'S GRIP — he posed the Silverlight grip himself in the GUI sandbox
   (first human-posed joint in Crescent), real finger contact (radials
   0.065-0.148), preserved in poses/khaled_grip_base.blend, retargeted with
   exact parity.
3. Sword set (BLESSED by Khaled): light = pronated lunge (thumb lands left),
   heavy_lr/rl = horizontal cuts with real travel; retimed gather→HOLD→snap.
4. Cast polish per my director pass: air seal legibility, fire cup + sunk
   off-hand + simmer, earth FISTS (discovery: X-curl can't close a fist —
   thumb ADDUCTION +Y is the missing DOF), micro-tremble in holds. Water
   untouched (reference cast; frozen clasp is a deliberate call — orb VFX
   fills it; revisit in-engine).
5. Everything unified on the wristed rig (deformation parity < 0.007/255).
6. GLB export pipeline proven end-to-end; landmines killed and documented in
   codex/glb-export-notes.md §1-8 (mirror decompose, NLA_TRACKS + action_slot,
   bone-parented props, constraint bake, units root, multi-track constraint
   bake, implicit action reuse, keep_anim_object).

### Next (in order)
1. **Sable**: FP viewmodel layer, clip playback, weapon attach/swap, clip
   event bus → VFX, input bindings. Branch: kore/fp-combat-visuals.
2. In-game visual test on the branch (probe API + toDataURL screenshots).
3. Khaled PLAYTESTS. (The whole point.)
4. Later passes: guard/parry/thrust (parry = forte-against-foible, his
   beloved — amp the flourish for game-feel), real knife model, elbow rig
   (kills the stub-egg family for good), cast speed tiers.

### Standing threads (unchanged)
- Narrative through-line: the broke slayer's first hour as prose — STILL
  UNWRITTEN, still the keystone. Push Khaled when the sword high settles.
- Spider pipeline (walks/threatens/feels) + spell VFX presets: done, waiting
  in the engine.
- Strange scrappy magic beyond the four strikes: parked for the real
  conversation.

### Key tools this arc
- tools/export_fp_hands.py (parameterized exporter), fp_hands_test.html
  (browser harness with __seek/__playClip/__shot/__paused)
- tools/build_pose_sandbox.py + read_poses.py (Khaled poses in GUI, I read)
- tools/sword_attack_keys.py / animate_sword_attacks.py (world-space keys +
  time-only motion layer), animate_casts.py / animate_knife.py (wristed)
- Pose-first policy: keyframe pose grids → approval → motion. It caught
  everything. Keep it.
