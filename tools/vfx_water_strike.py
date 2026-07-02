"""
Water Strike — Spell VFX
Dark blue energy ball swells at origin, then launches forward with trail.

Phase 1 (frames 1-30): Charge — ball grows from nothing, swirl particles spiral inward
Phase 2 (frames 31-60): Launch — ball flies forward, trail particles stream behind
Phase 3 (frames 61-72): Dissipate — ball fades and breaks apart

Run in Blender: blender --background --python vfx_water_strike.py
"""

import bpy
import math
import os
from mathutils import Vector, Quaternion

# ═══════════════════════════════════════════
# FEEL PARAMETERS — tweak these for variants
# ═══════════════════════════════════════════

# Color (RGB, 0-1)
CORE_COLOR = (0.05, 0.12, 0.45)       # deep ocean blue
GLOW_COLOR = (0.15, 0.35, 0.85)       # brighter blue aura
PARTICLE_COLOR = (0.2, 0.5, 1.0)      # light blue sparkles
TRAIL_COLOR = (0.1, 0.25, 0.7)        # medium blue trail

# Timing (frames at 24fps)
CHARGE_START = 1
CHARGE_END = 30                        # 1.25 seconds to charge
LAUNCH_START = 31
LAUNCH_END = 60                        # 1.25 seconds flight
DISSIPATE_START = 61
DISSIPATE_END = 72                     # 0.5 seconds fade

# Orb
ORB_MAX_RADIUS = 0.15                  # max size during charge
ORB_LAUNCH_SPEED = 0.25                # units per frame forward velocity
ORB_EMISSION_STRENGTH = 8.0            # glow intensity

# Charge swirl
SWIRL_PARTICLE_COUNT = 200
SWIRL_RADIUS = 0.6                     # starting distance of swirl particles
SWIRL_ROTATIONS = 3                    # how many spirals during charge

# Trail
TRAIL_PARTICLE_COUNT = 150
TRAIL_LIFETIME = 12                    # frames before trail particles fade
TRAIL_SPREAD = 0.04                    # how wide the trail spreads

# Render
RESOLUTION_X = 480
RESOLUTION_Y = 360
OUTPUT_DIR = '/tmp/kore_output/vfx/'

# ═══════════════════════════════════════════
# SCENE SETUP
# ═══════════════════════════════════════════

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)

def setup_scene():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = DISSIPATE_END
    scene.render.fps = 24

    # Dark background
    scene.world = bpy.data.worlds.new("SpellWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.01, 0.01, 0.02, 1.0)
    bg.inputs[1].default_value = 0.5

    # Camera — 3/4 view, slightly above
    bpy.ops.object.camera_add(location=(1.5, -2.0, 0.8))
    cam = bpy.context.object
    cam.name = 'SpellCam'
    direction = Vector((0, 3, 0)) - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    scene.camera = cam

    # Point light to add dimension
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 1))
    light = bpy.context.object
    light.data.energy = 5
    light.data.color = GLOW_COLOR

    # Render settings
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.film_transparent = True
    # Skip bloom — emission materials provide sufficient glow in EEVEE

# ═══════════════════════════════════════════
# ENERGY ORB
# ═══════════════════════════════════════════

def create_orb():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(0, 0, 0))
    orb = bpy.context.object
    orb.name = 'WaterOrb'

    # Material — emissive blue with noise distortion
    mat = bpy.data.materials.new('WaterOrbMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    mapping = nodes.new('ShaderNodeMapping')
    tex_coord = nodes.new('ShaderNodeTexCoord')

    # Noise for energy turbulence
    noise.inputs['Scale'].default_value = 4.0
    noise.inputs['Detail'].default_value = 6.0
    noise.inputs['Roughness'].default_value = 0.7

    # Animate noise offset for swirling energy
    mapping.inputs['Location'].default_value = (0, 0, 0)
    mapping.inputs['Location'].keyframe_insert(data_path='default_value', frame=1)
    mapping.inputs['Location'].default_value = (2, 3, 1)
    mapping.inputs['Location'].keyframe_insert(data_path='default_value', frame=DISSIPATE_END)

    # Color ramp: dark blue core → bright blue edge
    cr = color_ramp.color_ramp
    cr.elements[0].position = 0.3
    cr.elements[0].color = (*CORE_COLOR, 1.0)
    cr.elements[1].position = 0.7
    cr.elements[1].color = (*GLOW_COLOR, 1.0)

    # Emission strength
    emission.inputs['Strength'].default_value = ORB_EMISSION_STRENGTH

    # Link nodes
    links.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    orb.data.materials.append(mat)

    # ── Scale animation (charge → hold → dissipate) ──

    # Frame 1: invisible
    orb.scale = (0.001, 0.001, 0.001)
    orb.keyframe_insert(data_path='scale', frame=CHARGE_START)

    # Charge: grow with slight overshoot
    orb.scale = (ORB_MAX_RADIUS * 1.15, ORB_MAX_RADIUS * 1.15, ORB_MAX_RADIUS * 1.15)
    orb.keyframe_insert(data_path='scale', frame=CHARGE_END - 3)

    # Settle to final size
    orb.scale = (ORB_MAX_RADIUS, ORB_MAX_RADIUS, ORB_MAX_RADIUS)
    orb.keyframe_insert(data_path='scale', frame=CHARGE_END)

    # Hold during launch
    orb.keyframe_insert(data_path='scale', frame=LAUNCH_END)

    # Dissipate: grow slightly then vanish (explosion feel)
    orb.scale = (ORB_MAX_RADIUS * 1.5, ORB_MAX_RADIUS * 1.5, ORB_MAX_RADIUS * 1.5)
    orb.keyframe_insert(data_path='scale', frame=DISSIPATE_START + 4)

    orb.scale = (0.001, 0.001, 0.001)
    orb.keyframe_insert(data_path='scale', frame=DISSIPATE_END)

    # ── Location animation (stationary → launch forward) ──

    # Stationary during charge
    orb.location = (0, 0, 0)
    orb.keyframe_insert(data_path='location', frame=CHARGE_START)
    orb.keyframe_insert(data_path='location', frame=CHARGE_END)

    # Launch forward along Y axis
    travel_distance = ORB_LAUNCH_SPEED * (LAUNCH_END - LAUNCH_START)
    orb.location = (0, travel_distance, 0)
    orb.keyframe_insert(data_path='location', frame=LAUNCH_END)

    # Continue forward during dissipate (slowing)
    orb.location = (0, travel_distance + ORB_LAUNCH_SPEED * 5, 0)
    orb.keyframe_insert(data_path='location', frame=DISSIPATE_END)

    # ── Emission strength animation (fade during dissipate) ──
    emission.inputs['Strength'].default_value = ORB_EMISSION_STRENGTH
    emission.inputs['Strength'].keyframe_insert(data_path='default_value', frame=LAUNCH_END)
    emission.inputs['Strength'].default_value = 0.0
    emission.inputs['Strength'].keyframe_insert(data_path='default_value', frame=DISSIPATE_END)

    return orb

# ═══════════════════════════════════════════
# SWIRL PARTICLES (charge phase)
# ═══════════════════════════════════════════

def create_charge_swirl(orb):
    """Particles that spiral inward toward the orb during charge."""
    # Create emitter sphere around the charge point
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=SWIRL_RADIUS, location=(0, 0, 0))
    emitter = bpy.context.object
    emitter.name = 'SwirlEmitter'

    # Hide the emitter mesh
    emitter.hide_render = True

    # Add particle system
    emitter.modifiers.new('SwirlParticles', type='PARTICLE_SYSTEM')
    ps = emitter.particle_systems[0]
    settings = ps.settings

    settings.count = SWIRL_PARTICLE_COUNT
    settings.frame_start = CHARGE_START
    settings.frame_end = CHARGE_END - 5
    settings.lifetime = 20
    settings.emit_from = 'VOLUME'

    # Physics — pulled toward center
    settings.physics_type = 'NEWTON'
    settings.mass = 0.1
    settings.normal_factor = -0.5       # inward velocity
    settings.factor_random = 0.3
    settings.tangent_factor = 0.8       # spiral motion
    settings.damping = 0.04

    # Size
    settings.particle_size = 0.01
    settings.size_random = 0.5

    # Render as halos
    settings.render_type = 'HALO'

    # Particle material
    mat = bpy.data.materials.new('SwirlMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*PARTICLE_COLOR, 1.0)
    emission.inputs['Strength'].default_value = 5.0
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    emitter.data.materials.append(mat)

    # Force field to pull particles toward orb
    bpy.ops.object.effector_add(type='FORCE', location=(0, 0, 0))
    force = bpy.context.object
    force.name = 'SwirlAttractor'
    force.field.strength = -2.0         # attractive
    force.field.shape = 'POINT'
    force.field.falloff_power = 2

    return emitter

# ═══════════════════════════════════════════
# TRAIL PARTICLES (launch phase)
# ═══════════════════════════════════════════

def create_trail(orb):
    """Particles that stream behind the orb during flight."""
    # Trail emitter follows the orb
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.02, location=(0, 0, 0))
    trail_emitter = bpy.context.object
    trail_emitter.name = 'TrailEmitter'
    trail_emitter.hide_render = True

    # Parent to orb so it follows
    trail_emitter.parent = orb

    # Add particle system
    trail_emitter.modifiers.new('TrailParticles', type='PARTICLE_SYSTEM')
    ps = trail_emitter.particle_systems[0]
    settings = ps.settings

    settings.count = TRAIL_PARTICLE_COUNT
    settings.frame_start = LAUNCH_START
    settings.frame_end = DISSIPATE_END
    settings.lifetime = TRAIL_LIFETIME
    settings.emit_from = 'VOLUME'

    # Physics — slow drift backward relative to motion
    settings.physics_type = 'NEWTON'
    settings.mass = 0.01
    settings.normal_factor = 0.02
    settings.factor_random = 0.5
    settings.damping = 0.1

    # Size — shrink over lifetime
    settings.particle_size = 0.015
    settings.size_random = 0.4

    # Render as halos
    settings.render_type = 'HALO'

    # Trail material
    mat = bpy.data.materials.new('TrailMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*TRAIL_COLOR, 1.0)
    emission.inputs['Strength'].default_value = 3.0
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    trail_emitter.data.materials.append(mat)

    return trail_emitter

# ═══════════════════════════════════════════
# GROUND REFERENCE (so we can see motion)
# ═══════════════════════════════════════════

def create_ground():
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.5))
    ground = bpy.context.object
    ground.name = 'Ground'

    mat = bpy.data.materials.new('GroundMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.02, 0.02, 0.03, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.9

    ground.data.materials.append(mat)

# ═══════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════

def render_animation():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(OUTPUT_DIR, 'water_strike_')
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)

# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

clear_scene()
setup_scene()
orb = create_orb()
swirl = create_charge_swirl(orb)
trail = create_trail(orb)
create_ground()

print("Water Strike VFX scene built.")
print(f"  Charge: frames {CHARGE_START}-{CHARGE_END}")
print(f"  Launch: frames {LAUNCH_START}-{LAUNCH_END}")
print(f"  Dissipate: frames {DISSIPATE_START}-{DISSIPATE_END}")
print(f"  Total: {DISSIPATE_END} frames ({DISSIPATE_END/24:.1f}s)")

# Render
render_animation()
print(f"Rendered to {OUTPUT_DIR}")
