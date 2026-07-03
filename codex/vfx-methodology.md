# VFX Methodology — Spell Effects

How I design spell VFX in Crescent. Learned through water strike iteration.

---

## Architecture

Spell VFX in Crescent are composited from two systems:
- **Mesh core** — a custom ShaderMaterial on geometry (e.g., water_orb material on a sphere)
- **Particle layers** — emitters from ParticleSystem (charge, orbit, drips, trail, impact)

The mesh gives IDENTITY (this is water, this is fire). The particles give ENERGY (this is magic).

## The Bridge Principle (from Fable)

Two energies blend when each one's boundary is the other's source.

- The Fresnel RIM is the bridge between water (interior) and magic (particles)
- Rim color = particle color = same hex. The eye reads a continuous gradient.
- Every particle must be BORN FROM or DIE INTO the orb — never just coexist near it
- Converge particles: lifetime = (shapeRadius - orbRadius) / |speed| — they extinguish at the surface
- Drips: born AT the surface, fall away, die
- No floating dots. Every particle touches the orb at birth or death.

## The Five Layers (Water Strike reference)

1. **Core mesh** — water_orb material: jelly wobble, volume opacity, fake refraction, magic rim
2. **Charge shell** — converging droplets, born on a shell, die at the surface
3. **Orbit ring** — lazy wisps circling at ~1.1× radius, rim color, fills the scale gap
4. **Drips** — born at bottom surface, gravity pulls them down. Water falls even when magic holds it up.
5. **Trail + impact** — short trail during flight, ring burst + spray on hit

## Key Learnings

### Water v2 shader is plane-specific
Don't use it on spheres. Its Gerstner displacement goes along object-Z (world-up for the rotated water plane). On a sphere, waves shear across poles. Use water_orb material instead.

### Icosahedron vs Sphere for orb mesh
- IcosahedronGeometry(r, 1) = 42 vertices. Too few — visible faceting, dark seams at face edges.
- IcosahedronGeometry(r, 5) = uniform tessellation but still has face edge artifacts.
- SphereGeometry(r, 64, 48) = smooth normals by default, no seams. Use this.

### Sphere UV seam
SphereGeometry has a UV seam at one meridian. Sine-wave vertex displacement can create visible gaps there. FBM noise displacement in 3D (sampling radial direction, not UV) avoids this.

### "Pathetic" is a design parameter
For level 1 spells:
- High wobble-to-radius ratio (barely holds together)
- Sparse particle counts (2-3 per layer, never dozens)
- Low rim strength (effortful, not radiant)
- A drip that falls off mid-flight (the spell is embarrassed)
- Slightly-too-slow projectile speed

### A point light inside the orb makes it real
One PointLight in the rim color, parented to the orb position. The ground catches blue glow, the caster's hands catch light. The spell becomes an object in the world.

### Dark scenes starve the shader
The water_orb material uses environment cubemap for fake refraction and GGX for glints. In a dark room with no envmap, half the water channel is off. Test in lit environments.

### Particles and mesh must share visual language
Same rim color as particle color. Matched brightness. Scale stepping stones between blob and dots. Opposite visual languages (subtractive mesh vs additive particles) need explicit bridges.

## Test Page

`/crescent/engine/browserClient/tools/water_spell_test.html`
- Served at `http://localhost:8080/tools/water_spell_test.html`
- Click or Space to cast
- Uses standalone water_orb shader (adapted from engine material)
- Particles via engine ParticleSystem

## Capture Pipeline

`/Kore/tools/vfx_capture/` — canvas.toDataURL capture with contact sheets
- preserveDrawingBuffer: true required for WebGL capture
- Playwright page.screenshot() does NOT capture WebGL in headless Chromium
- Use evaluate + captureOneFrame() instead

## Iteration Workflow

1. Edit emitter configs or shader uniforms (live via browser console or Playwright evaluate)
2. Cast the spell (Space/click)
3. Screenshot (user for now, capture pipeline for autonomous)
4. "What does this feel like?" — the quality check
5. Adjust
6. Repeat
