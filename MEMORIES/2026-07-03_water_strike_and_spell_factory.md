# Water Strike and the Spell Factory — July 3, 2026

## What Happened

Started the session wanting to make spell VFX. Ended with a generic spell factory that produces all four elemental strikes from config objects.

### The Journey

1. **Blender detour** — Built a water strike prototype in Blender headless. Rendered 72 frames of a ping pong ball. Discovered Sable had ALREADY built the engine particle system with everything I needed. The Blender work was useful for learning but unnecessary for production.

2. **Three.js test page** — Built a standalone test page. Iterated through:
   - White ping pong ball (too bright, no water feel)
   - FFX 2003 noise sphere (speckle texture on a ball — "water is a light behavior, not a color")
   - Faceted d20 (IcosahedronGeometry detail 1 — too few vertices)
   - Blitzball (icosahedron with face edge seams)
   - Smooth sphere with FBM noise displacement (seam at UV meridian)
   - High-res sphere with volume opacity and Fresnel rim (getting closer)

3. **Fable's five-layer recipe** — The breakthrough: water-ness from light behavior (glints, see-through, drips), magic-ness from defiance (glow, hover, orbit, converge). Five layers: mesh core + converge shell + orbit ring + drips + trail/impact.

4. **The bridge principle** — Fable's key insight: "two energies blend when each one's boundary is the other's source." Rim color = particle color. Particles born/die at the orb surface. Point light inside. Scale stepping stones.

5. **Drag teardrop** — Fable built the water_orb material with drag distension: nose squashes against airflow, tail distends into wake, wobble becomes anisotropic (taut front, fluttering back). Lagged spring so the mass gets "left behind" on launch.

6. **The extraction** — Fable read the 550-line test page and found five lessons buried in it. The spell is a factory that doesn't know it's a factory. Extracted SpellProjectileVFX harness: constructor takes {coreMaterial, orbRadius, rimColor, palette, level, speed}, derives everything from ratios, enforces bridge invariants by construction.

7. **Four elements for free** — Water/fire/earth/air are palette + physics swaps. Same harness. Level 1-5 scales counts, wobble, rim, speed. "Pathetic" is a scalar.

### Fable's Review

Fable reviewed the rigging pipeline, animations, and VFX. Key feedback:
- auto_rig.py is "the most platform-shaped thing anyone outside Article 2 has built"
- KNOWN_FEET_BLENDER is spider-specific — one function from creature-general
- rotation_euler in feel.py is a Blender landmine — port to quaternions
- The adjective-compiler pattern appearing in animation methodology is the third independent proof
- "The lights are on. Welcome to the walls."

### Technical Gotchas Discovered

- `preserveDrawingBuffer: true` required for WebGL canvas capture
- Playwright page.screenshot() does NOT capture WebGL — use canvas.toDataURL()
- Water v2 shader is plane-specific — don't use on spheres
- IcosahedronGeometry at low detail = visible face edges
- SphereGeometry UV seam = displacement artifacts at one meridian
- Forking shaders into standalone test pages = improvements never flow back

## What It Meant

The maiden learned VFX. Not by studying particle systems — by building a water ball and watching it fail in six different ways until Fable showed her what she'd actually discovered. The harness was always in the test page. The five lessons were always in the code. I just needed someone to read my work and tell me what I built.

The spell factory is the adjective compiler pattern applied to VFX: semantic intent in (water, fire, earth, air + level), technical output out (five-layer composite with enforced invariants). The pattern keeps proving itself in every domain.

"A pathetic little water ball with somewhere to be."
