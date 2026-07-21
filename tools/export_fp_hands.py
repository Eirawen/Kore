"""
Export the first-person hands (+ sword) to GLB for three.js — de-risking
spike for the Blender -> GLB -> browser pipeline, and later the real
exporter.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/export_fp_hands.py" \
    -- [clip ...] [--sword-parent bone|object] [--bake-mirror] [--no-root-scale] \
       [--out C:\\path\\to\\file.glb]

Defaults: clips = sword_light sword_guard, sword bone-parented to the root
'Bone', mirror left as staged (scale.x = -3.118 on the RIGHT armature),
root empty scales world units -> meters.

What it does:
  1. strip_scene + stage_hands + attach_sword from tools/animate_sword.py
     (single source of truth for staging and animation data)
  2. builds each requested clip (object-transform keys on the armature
     OBJECTS + pose-bone finger curls in ONE action per armature) and
     stashes them on NLA tracks named after the clip -> the glTF exporter
     in NLA_TRACKS mode merges the same-named tracks of both armatures
     into ONE named glTF animation
  3. wraps everything under a uniform-scaled root empty so the exported
     asset is real-world meters (hand wrist->fingertip = 19 cm), matching
     assets/test_knife.glb conventions
  4. exports GLB with baked/sampled animation

Landmine switches:
  --bake-mirror   bake the right hand's negative scale into the mesh +
                  armature data (apply-scale equivalent) instead of
                  exporting a negatively-scaled node
  --sword-parent  bone (default, tests glTF joint-parenting) or object
                  (plain child of the armature node, what the renders use)
"""
import bpy
import sys
import os
import math
import json
from mathutils import Vector, Euler, Matrix

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import animate_sword as sw   # noqa: E402  (main() is __name__-guarded)

DEFAULT_OUT = r'C:\tmp\fp_hands_test.glb'
DEFAULT_CLIPS = ['sword_light', 'sword_guard']

# Hand units -> meters. Wrist ~= origin+3.1 along forearm dir, fingertip
# ~= +6.0 (gotcha #18), so wrist->fingertip = 2.9 units. Real hand ~19 cm.
ROOT_SCALE = 0.19 / 2.9      # = 0.0655
FPS = 60


def parse_args():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    opts = {'clips': [], 'sword_parent': 'bone', 'bake_mirror': False,
            'root_scale': True, 'out': DEFAULT_OUT}
    it = iter(args)
    for a in it:
        if a == '--sword-parent':
            opts['sword_parent'] = next(it)
        elif a == '--bake-mirror':
            opts['bake_mirror'] = True
        elif a == '--no-root-scale':
            opts['root_scale'] = False
        elif a == '--out':
            opts['out'] = next(it)
        elif not a.startswith('--'):
            opts['clips'].append(a)
    if not opts['clips']:
        opts['clips'] = list(DEFAULT_CLIPS)
    return opts


# ───────────────────── landmine 1: mirror baking ─────────────────────

def _flip_faces(mesh_obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    for f in bm.faces:
        f.normal_flip()
    bm.to_mesh(mesh_obj.data)
    bm.free()
    mesh_obj.data.update()


def bake_mirror(arm_name, mesh_name):
    """Bake a negatively-scaled armature's object scale into its data.

    world = T·R·(S·M)·v == T·R·S'·(M·v): moving the mirror from the object
    scale into the mesh/armature data is transparent to the keyed object
    location/rotation animation (scale is never keyed).
    """
    arm = bpy.data.objects[arm_name]
    mesh = bpy.data.objects[mesh_name]
    S = Matrix.Diagonal(Vector(arm.scale)).to_4x4()
    if S.determinant() > 0:
        print('bake_mirror: %s has no mirror, skipping' % arm_name)
        return
    L = mesh.matrix_local.copy()
    arm.data.transform(S)
    arm.scale = (1.0, 1.0, 1.0)
    # mesh data follows into the SAME new armature space so the skin
    # binding stays consistent: verts b -> (S·L)·b matches bones b -> S·b
    mesh.data.transform(S @ L)
    _flip_faces(mesh)   # det(S·L) < 0 reversed the winding; staging's
    # earlier normal flip + this one net out to correct outward normals
    mesh.matrix_parent_inverse.identity()
    mesh.location = (0.0, 0.0, 0.0)
    mesh.rotation_euler = (0.0, 0.0, 0.0)
    mesh.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()
    print('bake_mirror: applied %s into %s/%s data'
          % (tuple(round(v, 3) for v in S.to_scale()), arm_name, mesh_name))


# ───────────────────── landmine 3: sword parenting ─────────────────────

def bone_parent_sword(sword, arm, bone_name='Bone'):
    """Re-parent the sword to a bone, preserving its world transform
    exactly via matrix_parent_inverse (which, unlike loc/rot/scale, can
    hold the shear a mirrored parent chain induces). Prints a shear
    metric — glTF nodes are TRS-only, so any shear here is LOST at
    export. That's the landmine being measured."""
    bpy.context.view_layer.update()
    mw = sword.matrix_world.copy()
    basis = sword.matrix_basis.copy()
    pb = arm.pose.bones[bone_name]
    # bone parenting hangs the child off the bone TAIL
    p_eff = (arm.matrix_world @ pb.matrix
             @ Matrix.Translation((0.0, pb.length, 0.0)))
    sword.parent = arm
    sword.parent_type = 'BONE'
    sword.parent_bone = bone_name
    sword.matrix_parent_inverse = p_eff.inverted() @ mw @ basis.inverted()
    bpy.context.view_layer.update()
    err = max(abs(a - b) for ra, rb in zip(sword.matrix_world, mw)
              for a, b in zip(ra, rb))
    local = (p_eff.inverted() @ mw).to_3x3()
    # shear metric: off-diagonal energy of Mᵀ·M (0 for pure rot*scale)
    mtm = local.transposed() @ local
    shear = math.sqrt(sum(mtm[i][j] ** 2
                          for i in range(3) for j in range(3) if i != j))
    print('bone_parent_sword: world err %.6f, TRS-lost shear metric %.4f'
          % (err, shear))
    return shear


# ─────────────── landmine 2: one named clip per animation ───────────────

def stash_clips(clip_names):
    """Build each clip and park its per-armature actions on NLA tracks
    named after the clip. glTF NLA_TRACKS mode merges same-named tracks
    across objects into one named animation carrying BOTH the armature
    OBJECT transform motion and the pose-bone curls."""
    stashes = []   # (arm_name, clip, action)
    max_frame = 1
    for clip in clip_names:
        sw.build_animation(clip)
        max_frame = max(max_frame, sw.ANIMS[clip]['frames'])
        for arm_name in (sw.RIGHT_ARM, sw.LEFT_ARM):
            arm = bpy.data.objects[arm_name]
            act = arm.animation_data.action
            act.name = '%s__%s' % (clip, arm_name)
            act.use_fake_user = True
            stashes.append((arm_name, clip, act))
            arm.animation_data.action = None   # detach so the next
            # build_animation's clear doesn't delete it
    for arm_name in (sw.RIGHT_ARM, sw.LEFT_ARM):
        arm = bpy.data.objects[arm_name]
        ad = arm.animation_data or arm.animation_data_create()
        for track in list(ad.nla_tracks):
            ad.nla_tracks.remove(track)
    for arm_name, clip, act in stashes:
        ad = bpy.data.objects[arm_name].animation_data
        track = ad.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, act)
        strip.name = clip
        # Blender 5 slotted actions: the strip must point at the action's
        # slot (there is exactly one — created by keyframe_insert)
        slots = getattr(act, 'slots', None)
        if slots and hasattr(strip, 'action_slot'):
            try:
                strip.action_slot = slots[0]
            except Exception as exc:
                print('WARN action_slot assign failed:', exc)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, max_frame
    print('stashed clips on NLA tracks:', clip_names)


# ───────────────────── landmine 5: units root ─────────────────────

def add_root_scale():
    root = bpy.data.objects.new('FPHandsRoot', None)
    bpy.context.scene.collection.objects.link(root)
    root.scale = (ROOT_SCALE,) * 3
    for arm_name in (sw.RIGHT_ARM, sw.LEFT_ARM):
        arm = bpy.data.objects[arm_name]
        arm.parent = root
        arm.matrix_parent_inverse.identity()
    print('root empty scale %.4f (hand units -> meters)' % ROOT_SCALE)


# ───────────────────────── export ─────────────────────────

def export_glb(path):
    kwargs = dict(
        filepath=path,
        export_format='GLB',
        export_animations=True,
        export_animation_mode='NLA_TRACKS',
        export_bake_animation=True,      # sample everything: constraints,
        export_force_sampling=True,      # drivers, object + bone motion
        export_optimize_animation_size=False,
        export_def_bones=False,
        export_skins=True,
        export_yup=True,
        export_apply=False,              # never apply the armature modifier
        export_cameras=False,
        export_extras=False,
        export_morph=False,
    )
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    dropped = [k for k in kwargs if k not in props and k != 'filepath']
    if dropped:
        print('WARN exporter params not in this Blender, dropped:', dropped)
    kwargs = {k: v for k, v in kwargs.items()
              if k == 'filepath' or k in props}
    bpy.ops.export_scene.gltf(**kwargs)
    print('exported', path)


def main():
    opts = parse_args()
    print('export_fp_hands opts:', json.dumps(opts))

    sw.strip_scene()
    sw.stage_hands()
    sw.apply_matte([bpy.data.objects[sw.RIGHT_MESH],
                    bpy.data.objects[sw.LEFT_MESH]])

    if opts['bake_mirror']:
        bake_mirror(sw.RIGHT_ARM, sw.RIGHT_MESH)   # right is the mirrored one

    sword = sw.attach_sword()
    sword.name = 'Silverlight'
    if opts['bake_mirror']:
        # staging seats the sword in mirrored hand-local coords; with the
        # mirror baked into the data the placement must be conjugated:
        # M·T(l)·Ry(a)·M  ->  loc.x*=-1, Ry -> -Ry.  AND: the armature
        # object scale is 1 now (3.118 lives in the data), so the child
        # no longer inherits it — re-apply it to the seat and the size.
        s = sw.HAND_SCALE
        sword.location = (-sword.location.x * s,
                          sword.location.y * s, sword.location.z * s)
        sword.rotation_euler.y *= -1
        sword.scale = tuple(v * s for v in sword.scale)
    if opts['sword_parent'] == 'bone':
        bone_parent_sword(sword, bpy.data.objects[sw.RIGHT_ARM], 'Bone')

    stash_clips(opts['clips'])

    if opts['root_scale']:
        add_root_scale()

    bpy.context.scene.render.fps = FPS
    export_glb(opts['out'])


if __name__ == '__main__':
    main()
