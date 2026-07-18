"""
First-person staging + pose render for the cgtrader two-hand asset.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/render_hands_fp.py" \
    -- idle            # or one/more pose names, or 'all' (default)

What it does:
  - keeps only Sphere.001/Armature.001 (right hand) and Sphere.002/Armature.003
    (left hand, mirrored via scale.x = -1 + normal flip), deletes everything else
  - overrides materials with a bare matte, dark world, 2 sun lights
  - restages both armatures into a first-person arrangement: fingers up/forward,
    palms toward camera, long forearms running off the bottom of frame
  - clears the authored pose-bone quaternions, applies a named finger pose
    (rotation about bone local +X = curl toward palm), renders to C:\\tmp\\fp_<pose>.png

The rig/weights are untouched — only object transforms + pose-bone rotations.
"""
import bpy
import sys
import math
from mathutils import Vector, Euler

# ───────────────────────── configuration ─────────────────────────

OUT_DIR = r'C:\tmp'

# Bone chains (root->tip). Non-thumb chains: [metacarpal, prox, mid, dist].
CHAINS = {
    'thumb':  ['Bone.001', 'Bone.002', 'Bone.003'],
    'index':  ['Bone.004', 'Bone.017', 'Bone.018', 'Bone.019'],
    'middle': ['Bone.005', 'Bone.014', 'Bone.015', 'Bone.016'],
    'ring':   ['Bone.006', 'Bone.011', 'Bone.012', 'Bone.013'],
    'pinky':  ['Bone.007', 'Bone.008', 'Bone.009', 'Bone.010'],
}
METACARPAL_FRACTION = 0.15   # metacarpal takes ~15% of the proximal curl

# Phalanx curl angles in DEGREES about each bone's local X (+X curls to palm).
# 'f' applies to index/middle/ring/pinky unless the finger is named explicitly.
POSES = {
    'idle':         {'f': [20, 30, 15],  'thumb': [15, 20, 10]},
    'cup':          {'f': [35, 45, 30],  'thumb': [20, 25, 15]},
    'flame':        {'f': [-5, -3, 5],   'thumb': [-10, 5, 0]},
    'fist':         {'f': [80, 85, 60],  'thumb': [40, 50, 30]},
    'spiral':       {'f': [-15, -10, -5], 'thumb': [-20, -10, -5]},
    'knife_blade':  {'index': [50, 40, 25], 'middle': [55, 45, 30],
                     'ring': [75, 80, 50], 'pinky': [80, 85, 55],
                     'thumb': [30, 15, 5]},
    'knife_handle': {'f': [70, 75, 45],  'thumb': [35, 45, 20]},
    'sword_light':  {'f': [45, 35, 20],  'thumb': [20, 25, 10]},
    'sword_heavy':  {'f': [85, 90, 65],  'thumb': [45, 55, 35]},
}

# ── first-person staging values (settled by iteration on the idle render) ──
HAND_SCALE   = 3.118          # keep the authored scale
HAND_X       = 2.05           # wrist distance from centerline
HAND_Z       = 0.0            # wrist height (world)
HAND_Y       = 0.0            # wrist depth
TILT_BACK    = -14.0          # deg about X: lean fingers away from camera
TIP_INWARD   = 9.0            # deg about Y: fingertips lean toward centerline
ROLL_INWARD  = 8.0            # deg about Z: palms angle slightly toward center

CAM_LOC      = Vector((0.0, -8.2, 4.6))
CAM_AIM      = Vector((0.0, 0.0, 3.3))
CAM_LENS     = 36.0
RES_X, RES_Y = 960, 720

MATTE_COLOR  = (0.62, 0.55, 0.50, 1.0)
MATTE_ROUGH  = 0.75
WORLD_COLOR  = (0.12, 0.13, 0.16, 1.0)

KEEP = {'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002'}
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'


# ───────────────────────── helpers ─────────────────────────

def look_at_rotation(loc, target):
    return (target - loc).to_track_quat('-Z', 'Y').to_euler()


def strip_scene():
    for obj in list(bpy.data.objects):
        if obj.name not in KEEP:
            bpy.data.objects.remove(obj, do_unlink=True)
    # purge orphaned data
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_recursive=True)


def ensure_parented(mesh, arm):
    """Meshes ship parented to their armatures in this file; if a future copy
    of the asset is not, parent keeping the world transform."""
    if mesh.parent != arm:
        mw = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_parent_inverse = arm.matrix_world.inverted()
        mesh.matrix_world = mw


def apply_matte(objs):
    mat = bpy.data.materials.new('FP_Matte')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = MATTE_COLOR
    bsdf.inputs['Roughness'].default_value = MATTE_ROUGH
    for obj in objs:
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def stage_hands():
    right = bpy.data.objects[RIGHT_ARM]
    left = bpy.data.objects[LEFT_ARM]
    ensure_parented(bpy.data.objects[RIGHT_MESH], right)
    ensure_parented(bpy.data.objects[LEFT_MESH], left)

    tb = math.radians(TILT_BACK)
    ti = math.radians(TIP_INWARD)
    ri = math.radians(ROLL_INWARD)

    # In hand-local space: fingers +Z, palm -Y, forearm -Z.
    # With identity rotation the palm faces the camera (camera sits at -Y),
    # fingers point world-up, forearm drops straight down out of frame.
    #
    # CHIRALITY (verified by render 2026-07-17): the un-mirrored mesh staged
    # this way shows its thumb OUTBOARD, i.e. it reads as the WRONG hand for
    # its side (Khaled caught this by thumb position). The fix is an in-place
    # chirality flip on BOTH slots: keep the location, negate the euler Y and
    # Z components, toggle the scale.x mirror. Screen-right is therefore the
    # MIRRORED mesh, screen-left the un-mirrored one; each thumb lands
    # INBOARD (toward screen center), which is what a true first-person view
    # of the backs of your own hands looks like.
    right.location = (HAND_X, HAND_Y, HAND_Z)
    right.rotation_euler = Euler((tb, ti, -ri), 'XYZ')
    right.scale = (-HAND_SCALE, HAND_SCALE, HAND_SCALE)

    left.location = (-HAND_X, HAND_Y, HAND_Z)
    left.rotation_euler = Euler((tb, -ti, ri), 'XYZ')
    left.scale = (HAND_SCALE, HAND_SCALE, HAND_SCALE)

    # Negative determinant flips face winding; flip the mesh normals so the
    # mirrored hand does not render inside-out. Applied to whichever mesh is
    # mirrored (guard on the determinant, not the name).
    bpy.context.view_layer.update()
    for mesh_name in (RIGHT_MESH, LEFT_MESH):
        m = bpy.data.objects[mesh_name]
        if m.matrix_world.determinant() < 0:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(m.data)
            for f in bm.faces:
                f.normal_flip()
            bm.to_mesh(m.data)
            bm.free()
            m.data.update()


def setup_camera_lights_world():
    scene = bpy.context.scene

    cam_data = bpy.data.cameras.new('FP_Camera')
    cam_data.lens = CAM_LENS
    cam = bpy.data.objects.new('FP_Camera', cam_data)
    cam.location = CAM_LOC
    cam.rotation_euler = look_at_rotation(CAM_LOC, CAM_AIM)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def add_sun(name, loc, energy, color=(1, 1, 1)):
        data = bpy.data.lights.new(name, 'SUN')
        data.energy = energy
        data.color = color
        data.angle = math.radians(6)
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = look_at_rotation(Vector(loc), Vector((0, 0, 2.5)))
        scene.collection.objects.link(obj)

    # key: high camera-left; fill: low camera-right, cooler and dimmer
    add_sun('FP_Key',  (-6, -8, 10), 2.0, (1.0, 0.97, 0.92))
    add_sun('FP_Fill', (7, -6, 2),   0.8, (0.85, 0.90, 1.0))

    world = bpy.data.worlds.new('FP_World')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = WORLD_COLOR
    bg.inputs['Strength'].default_value = 1.0
    scene.world = world

    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.image_settings.file_format = 'PNG'


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def apply_pose(arm, pose):
    clear_pose(arm)
    for finger, chain in CHAINS.items():
        angles = pose.get(finger, pose.get('f'))
        if angles is None:
            continue
        if finger == 'thumb':
            phalanges = chain          # thumb: 3 bones, 3 angles, no metacarpal
        else:
            meta = arm.pose.bones[chain[0]]
            meta.rotation_euler.x = math.radians(angles[0] * METACARPAL_FRACTION)
            phalanges = chain[1:]
        for bone_name, deg in zip(phalanges, angles):
            arm.pose.bones[bone_name].rotation_euler.x = math.radians(deg)


def render_pose(name):
    pose = POSES[name]
    for arm_name in (RIGHT_ARM, LEFT_ARM):
        apply_pose(bpy.data.objects[arm_name], pose)
    path = OUT_DIR + '\\fp_' + name + '.png'
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('rendered', path)


# ───────────────────────── main ─────────────────────────

def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    names = list(POSES) if (not args or args == ['all']) else args

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_camera_lights_world()
    for name in names:
        render_pose(name)


main()
