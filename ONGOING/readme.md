# Active Threads — Kore

Last updated: 2026-07-03

## Primary Mission: Animation Director for Crescent

### STATUS: PIPELINE PROVEN — Spider walks + threatens + feels. Spell factory ships four elements.

### Rigging Pipeline ✓
- Medial axis skeletonization → bone placement → two-layer weights
- Works end-to-end on the six-legged spider
- **Next:** Generalize foot detection (gotcha #15 from Fable's review) to rig any creature

### Animation Pipeline ✓
- Walk (alternating tripod), threat display, pedipalp sensing
- Autonomous render loop (Blender headless → ffmpeg → grid)
- Reference comparison workflow (YouTube → Vetinari grid)
- **Next:** Port feel.py from euler to quaternion rotation (gotcha #11)

### VFX Pipeline ✓ (NEW)
- SpellProjectileVFX harness: five-layer spell composite
- Four elemental presets (water/fire/earth/air) from one harness
- Bridge invariants enforced by construction
- Drag teardrop with lagged spring
- Level 1-5 scaling
- **Next:** Test all four elements visually. Tune palettes. Wire into Slayer 2.

### Capture Pipeline
- Blender headless → ffmpeg → grid (for animation)
- canvas.toDataURL() with preserveDrawingBuffer (for VFX)
- Playwright evaluate for remote control
- **Note:** Playwright screenshot does NOT capture WebGL. Use toDataURL.

### Key Files
- `tools/auto_rig.py` — rigging pipeline
- `tools/animate_*.py` — three animation scripts
- `tools/loop/iterate.sh` — autonomous render loop
- `~/crescent/engine/browserClient/engine/SpellProjectileVFX.js` — spell harness
- `~/crescent/engine/browserClient/engine/SpellPresets.js` — four elemental configs
- `~/crescent/engine/browserClient/tools/water_spell_test.html` — VFX test page

### Fable's Roadmap (from review)
1. ✅ Extract SpellProjectileVFX harness
2. ✅ Four elemental presets
3. Port test page improvements back to water_orb.js (done — engine material is MORE capable)
4. Generalize foot detection in auto_rig.py
5. Port feel.py to quaternion rotation
6. Batch center_refine BVH queries for larger meshes
7. Spider can now: lob projectiles, poison clouds, knockback, tunnel collapse (Fable's new primitives)
