# WRIST SURGERY on cgtrader_hand_wristed.blend (the COPY - never the canonical).
#
# For each hand pair (Armature.001/Sphere.001, Armature.003/Sphere.002):
#   1. Bake the mesh->armature relative matrix into the vertex data so mesh
#      space == armature space (gotcha #1: the glTF offset lives in
#      matrix_parent_inverse; bones and verts disagree until unified).
#      Custom split normals are rotated along.
#   2. Split root "Bone" at the empirically-located wrist crease
#      (t = WRIST_T along head->tail; X-width minimum plateau 0.74-0.80):
#        forearm: (0,0,0) -> wrist point   (new root, keeps old roll)
#        hand:    wrist point -> old tail  (child of forearm, same roll)
#      Reparent the five metacarpal roots (Bone.001/.004/.005/.006/.007)
#      to "hand"; heads/children untouched.
#   3. Re-weight ONLY the old root-group verts: weight w splits into
#      forearm w*(1-f) + hand w*f with f = smoothstep across a blend band
#      centred on the crease. Sum preserved => rest pose identical.
#      Vertex group "Bone" renamed to "forearm" in lockstep (gotcha #25).
#   4. Save the file in place.
#
# Both hands share identical local-space data (the mirror is object-transform
# only, applied at staging), so identical surgery keeps them correct mirrors.
import bpy, math
import numpy as np
from mathutils import Matrix, Vector

WRIST_T = 0.78          # split point along root head->tail (probed crease)
BAND    = 0.10          # blend band full width, local units (~1.5cm hand-scale)

PAIRS = [('Armature.001', 'Sphere.001'), ('Armature.003', 'Sphere.002')]
FINGER_ROOTS = ['Bone.001', 'Bone.004', 'Bone.005', 'Bone.006', 'Bone.007']


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def unify_spaces(arm, mesh):
    """Bake the mesh->armature relative transform into vertex data; after this
    mesh-data coordinates ARE armature-space coordinates."""
    rel = arm.matrix_world.inverted() @ mesh.matrix_world
    if all(abs(rel[i][j] - (1.0 if i == j else 0.0)) < 1e-6
           for i in range(4) for j in range(4)):
        print('  spaces already unified')
        return
    det = rel.to_3x3().determinant()
    assert det > 0, 'relative matrix mirrors! det=%f' % det
    rot3 = rel.to_3x3()
    me = mesh.data
    # rotate custom split normals along, if present
    custom = []
    if me.has_custom_normals:
        if hasattr(me, 'corner_normals'):           # Blender 4.1+/5.x
            src = [cn.vector for cn in me.corner_normals]
        else:
            me.calc_normals_split()
            src = [l.normal for l in me.loops]
        custom = [(rot3 @ Vector(n)).normalized() for n in src]
    for v in me.vertices:
        v.co = rel @ v.co
    if custom:
        me.normals_split_custom_set(custom)
    me.update()
    # keep world placement: mesh world must equal armature world now
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    resid = max(abs(a - b) for ra, rb in zip(mesh.matrix_world, arm.matrix_world)
                for a, b in zip(ra, rb))
    print('  spaces unified (rel det %.6f, world residual %.2e)' % (det, resid))


def split_root(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    old = eb['Bone']
    head = Vector(old.head); tail = Vector(old.tail)
    wrist = head.lerp(tail, WRIST_T)
    roll = old.roll

    old.name = 'forearm'
    old.tail = wrist                      # forearm: stub -> wrist (new root)

    hand = eb.new('hand')
    hand.head = wrist
    hand.tail = tail                      # hand: wrist -> metacarpal branch point
    hand.roll = roll                      # same axis+roll => same local frame
    hand.parent = eb['forearm']
    hand.use_connect = True

    for name in FINGER_ROOTS:
        b = eb[name]
        was_connected = b.use_connect
        b.parent = hand                   # heads coincide with hand.tail
        b.use_connect = was_connected
    bpy.ops.object.mode_set(mode='OBJECT')
    print('  split at %s (t=%.2f), forearm len %.3f, hand len %.3f' % (
        tuple(round(v, 4) for v in wrist), WRIST_T,
        (wrist - head).length, (tail - wrist).length))


def reweight(arm, mesh):
    """Split old root weights between forearm and hand along the crease.
    Mesh space == armature space here (unify_spaces ran first)."""
    b = arm.data.bones['forearm']
    head = np.array(b.head_local)
    # axis of the ORIGINAL full bone = forearm head -> hand tail
    tail = np.array(arm.data.bones['hand'].tail_local)
    axis = tail - head
    L = float(np.linalg.norm(axis)); axis /= L

    # Blender auto-syncs deformed meshes' vertex-group names on bone rename,
    # so the group may already be 'forearm'; rename manually if not (gotcha #25).
    vg_fore = mesh.vertex_groups.get('forearm') or mesh.vertex_groups['Bone']
    vg_fore.name = 'forearm'
    vg_hand = mesh.vertex_groups.new(name='hand')
    fidx = vg_fore.index

    lo = WRIST_T - BAND / 2.0
    n_fore = n_hand = n_blend = 0
    for v in mesh.data.vertices:
        w = None
        for g in v.groups:
            if g.group == fidx:
                w = g.weight
        if w is None or w <= 0.0:
            continue
        t = float(np.dot(np.array(v.co) - head, axis)) / L
        f = smoothstep((t - lo) / BAND)
        if f <= 0.0:
            n_fore += 1                   # stays fully on forearm
        elif f >= 1.0:
            vg_hand.add([v.index], w, 'REPLACE')
            vg_fore.remove([v.index])
            n_hand += 1
        else:
            vg_fore.add([v.index], w * (1.0 - f), 'REPLACE')
            vg_hand.add([v.index], w * f, 'REPLACE')
            n_blend += 1
    print('  reweighted: %d forearm, %d hand, %d blended (band %.2f..%.2f)' % (
        n_fore, n_hand, n_blend, lo, lo + BAND))


for ARM, MESH in PAIRS:
    print('===== %s / %s =====' % (ARM, MESH))
    arm = bpy.data.objects[ARM]
    mesh = bpy.data.objects[MESH]
    unify_spaces(arm, mesh)
    split_root(arm)
    reweight(arm, mesh)

bpy.ops.wm.save_mainfile()
print('SAVED', bpy.data.filepath)
