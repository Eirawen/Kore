"""FP POSE SANDBOX — the SHIPPED rig, seen through the ACTUAL game camera.

The old sandbox used an OBSERVER camera looking at the hands from outside.
Fine for judging a grip; useless for judging FRAMING, which is the complaint:
"the left arm is just upended, taking over most of the screen ... in our fpv
we see forearm" (Khaled, 2026-07-29).

DO NOT DERIVE THE CAMERA. I tried, twice, and got an empty frame both times —
the exporter rebases the armatures (blend 2.05,0,0 -> gltf 1.926,-0.029,2.408
with a baked rotation), so anything computed from the blend staging is wrong.

Instead: IMPORT assets/fp_hands.glb — literally what ships — and place the
camera where ViewmodelManager places it. From DEFAULT_CONFIG:
    fov 55 (vertical), near 0.01, far 20, scale 1
    offset [0,-0.05,0]  = rig root, camera-LOCAL, metres
The rig is a CHILD of the camera, so the camera sits 0.05 m ABOVE the rig
origin. glTF import puts the rig root at the blender origin already in metres
(FPHandsRoot bakes 0.0655), so: camera at (0, 0, 0.05), looking +Y.

    blender --background --python build_fp_sandbox.py
"""
import bpy, math
from mathutils import Vector

GLB      = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\assets\fp_hands.glb'
OUT      = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\fp_sandbox.blend'
SHOT     = r'C:\tmp\fp_check.png'
# SLAYER2 OVERRIDES THE DEFAULTS (games/slayer2/client/game.js:1563):
#     fov: 54,  offset: [0, -0.22, -0.45]
# The rig is pushed 0.22 m DOWN and 0.45 m FORWARD of the camera, so the eye
# sits at rig-local glTF (0, +0.22, +0.45). glTF (x,y,z) -> blender (x,-z,y),
# giving blender (0, -0.45, 0.22). Sable's own comment says this was "tuned
# in-browser ... so the hands read at the bottom of frame" — which is exactly
# the geometry that puts FOREARM on screen instead of HAND.
FOV_V    = 54.0
EYE      = (0.0, -0.45, 0.22)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene

# ── matte skin so shape reads, not texture ──
mat = bpy.data.materials.new('FP_Matte'); mat.use_nodes = True
b = mat.node_tree.nodes.get('Principled BSDF')
b.inputs['Base Color'].default_value = (0.62, 0.55, 0.50, 1.0)
b.inputs['Roughness'].default_value = 0.75
for o in bpy.data.objects:
    if o.type == 'MESH' and o.data:
        o.data.materials.clear(); o.data.materials.append(mat)
# the orb-anchor icospheres are 1 m helpers — they swallow the frame
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_viewport = o.hide_render = True

# ── lights mirroring ViewmodelManager (ambient .7, key, fill) ──
w = bpy.data.worlds.new('W'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.10,.11,.14,1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
sc.world = w
for nm, d, e, c in (('Key', (0.5, -1.0, 0.3), 2.2, (1,1,1)),
                    ('Fill', (-0.3, 0.5, 0.2), 0.8, (0.8,0.8,1.0))):
    L = bpy.data.lights.new(nm, 'SUN'); L.energy = e; L.color = c
    o = bpy.data.objects.new(nm, L)
    o.rotation_euler = (-Vector(d)).to_track_quat('-Z','Y').to_euler()
    sc.collection.objects.link(o)

# ── THE GAME CAMERA ──
cd = bpy.data.cameras.new('FP_EYE')
cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(FOV_V)
cd.clip_start, cd.clip_end = 0.01, 20.0
cam = bpy.data.objects.new('FP_EYE', cd)
cam.location = EYE
cam.rotation_euler = (math.radians(90), 0, 0)      # look along +Y (gltf -Z)
sc.collection.objects.link(cam); sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
try: sc.render.engine = 'BLENDER_EEVEE'
except TypeError: sc.render.engine = 'BLENDER_EEVEE_NEXT'

# ── start from the REAL in-game idle, not the rest pose ──
# The rest pose is arms-up-and-open; the player never sees it.
#
# LANDMINE (blender 5 slotted actions): ONE action drives ALL THREE objects
# via named SLOTS ['Armature.001','Armature.003','ThrowingKnife']. Assigning
# the action without binding each object to ITS OWN slot makes every object
# read the FIRST slot — both arms then sit on top of each other at the right
# arm's transform. Bind per object by matching slot.name_display.
IDLE = 'idle_sword'
act = next((a for a in bpy.data.actions if IDLE in a.name), None)
if act:
    for o in bpy.data.objects:
        if o.type not in ('ARMATURE', 'MESH'): continue
        slot = next((sl for sl in getattr(act, 'slots', [])
                     if sl.name_display == o.name), None)
        if slot is None: continue
        if not o.animation_data: o.animation_data_create()
        o.animation_data.action = act
        o.animation_data.action_slot = slot
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    print('IDLE applied:', act.name)
else:
    print('IDLE not found; have:', [a.name for a in bpy.data.actions][:12])

# ── seat Silverlight in the right fist (attached at RUNTIME in game,
# so it is absent from the glb; without it you are posing a sword idle
# with no sword). Seat comes from assets/fp_weapon_seats.json, the same
# matrix the viewmodel uses.
import json, os
SWORD = r'\\wsl.localhost\Ubuntu\home\khaled\crescent\assets\models\silverlight.glb'
try:
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD)
    new = [o for o in bpy.data.objects if o not in pre]
    meshes = [o for o in new if o.type == 'MESH']
    if meshes:
        sw = meshes[0]; sw.name = 'Silverlight'
        for o in new:
            if o is not sw and o.type != 'MESH':
                try: bpy.data.objects.remove(o, do_unlink=True)
                except Exception: pass
        right = bpy.data.objects.get('Armature.001')
        seats = json.load(open('/home/khaled/Kore/assets/fp_weapon_seats.json'))
        entry = seats.get('silverlight_sword') or {}
        socket = 'hand'
        M = entry.get('matrix')
        sw.parent = right; sw.parent_type = 'BONE'; sw.parent_bone = socket
        sw.matrix_parent_inverse.identity()
        bpy.context.view_layer.update()
        if M:
            from mathutils import Matrix
            # nested row-major 4x4, expressed in RAW GLTF space ("no import
            # conversion"). Blender's importer rotates the world +90 about X
            # (gltf Y-up -> blender Z-up), so the seat must be conjugated into
            # blender space: B = C . G . C^-1
            G = Matrix([[float(v) for v in row] for row in M])
            C = Matrix.Rotation(math.radians(90), 4, 'X')
            sw.matrix_basis = C @ G @ C.inverted()
        # KNOWN GAP: blender bone-parenting adds a tail-length frame that
        # this conjugation does not account for, so the blade lands off in
        # space. A WRONG sword is worse than none while judging arm framing,
        # so it ships hidden. Unhide 'Silverlight' in the outliner if wanted.
        sw.hide_viewport = sw.hide_render = True
        bpy.context.view_layer.update()
        print('SWORD imported (hidden — seat needs the bone-tail frame)')
except Exception as e:
    print('SWORD skipped:', e)

arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
for a in arms:
    print('ARM %-16s loc=%s scale=%s' % (a.name,
          [round(v,3) for v in a.location], [round(v,3) for v in a.scale]))
deps = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.vertices: continue
    eo = o.evaluated_get(deps)
    pts = [eo.matrix_world @ v.co for v in eo.data.vertices]
    print('MESH %-14s x[%6.3f %6.3f] y[%6.3f %6.3f] z[%6.3f %6.3f]' % (o.name,
        min(p.x for p in pts), max(p.x for p in pts),
        min(p.y for p in pts), max(p.y for p in pts),
        min(p.z for p in pts), max(p.z for p in pts)))

bpy.ops.wm.save_as_mainfile(filepath=OUT)
sc.render.filepath = SHOT
bpy.ops.render.render(write_still=True)
print('saved', OUT)
