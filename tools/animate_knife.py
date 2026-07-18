"""
First-person throwing-knife animations — assets/test_knife.glb in the right
hand, with a REAL release: the knife rides a keyed ChildOf constraint
(influence 1 -> 0 on the release frame) and then flies downrange on its own
world-space keys. The hand truly lets go.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_knife.py" \
    -- knife_throw_blade_first     # or knife_throw_handle_first / all

Staging, chirality fix, world-space key solver, euler unwrap and render
plumbing are shared with tools/animate_sword.py (exec-included below).

Two throws:
  - blade_first: PINCH grip — thumb+index+middle pinch the flat of the
    blade, ring/pinky curled; the knife lies along the palm, tip past the
    fingertips. Draw back beside the head, held beat, wrist-flick release,
    knife flies tip-first (no spin), follow-through.
  - handle_first: HAMMER grip — full fist on the handle like a sword,
    blade out the thumb side. Cock over the shoulder, whole-arm hurl,
    knife tumbles end-over-end downrange.
"""
import bpy  # noqa: F401  (bpy provided by Blender; exec brings the rest)

_SWORD = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\animate_sword.py'
_code = open(_SWORD).read()
exec(_code[:_code.rfind('def main')])

KNIFE_GLB = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\assets\test_knife.glb'
# knife is authored in meters (0.26 total); world scale: hand ~2.9 units for
# ~19 cm -> 1 world unit ~6.5 cm -> 26 cm knife = 4.0 world = 1.28 hand-local
# -> object scale 4.9 under the hand's 3.118.
KNIFE_SCALE = 4.9

POSES['pinch'] = {'index': [45, 50, 30], 'middle': [50, 55, 35],
                  'ring': [85, 90, 60], 'pinky': [90, 95, 65],
                  'thumb': [30, 35, 20]}
POSES['open_release'] = {'f': [-5, 2, 0], 'thumb': [-5, 5, 0]}

# hand-local seats (loc, euler-deg) per grip.
# pinch: knife along the palm plane, blade mid at the fingertip pinch
# (-0.05, -0.33, 1.5), tip up past the fingertips, handle down the palm.
SEAT_PINCH = ((-0.05, -0.33, 1.18), (0, 0, 0))
# hammer: handle center in the fist void (0, -0.22, 1.37), blade out the
# thumb side (hand -X) => Ry(-90), origin offset 0.34 along +X.
SEAT_HAMMER = ((-0.34, -0.22, 1.37), (0, -90, 0))


def attach_knife(seat):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=KNIFE_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    knife = [o for o in new if o.type == 'MESH'][0]
    knife.parent = None
    for o in new:
        if o is not knife and o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    knife.rotation_mode = 'XYZ'
    loc, rot = seat
    knife.location = loc
    knife.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    knife.scale = (KNIFE_SCALE,) * 3
    con = knife.constraints.new('CHILD_OF')
    con.target = bpy.data.objects[RIGHT_ARM]
    con.inverse_matrix = Matrix.Identity(4)
    return knife, con


def hand_world_matrix(loc, authored_rot):
    """World matrix of the right armature at an authored key (analytic —
    avoids depsgraph evaluation)."""
    rot = Euler([math.radians(a) for a in flip_chirality(authored_rot)], 'XYZ')
    return (Matrix.Translation(Vector(loc)) @ rot.to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector((-HAND_SCALE, HAND_SCALE, HAND_SCALE))).to_4x4())


# ───────────────────── the two throws ─────────────────────
# Right-hand keys use the sword solver format: (frame, fist, fdir, bdir, pose)
# where bdir = world direction of the THUMB side (hand-local -X).
# 'release' names the (pre-retime) frame where the knife leaves the hand.

K_READY = ((2.05, 1.1, 0.20), (-0.20, 0.90, 0.32), (-0.12, 0.25, 0.96))

KNIFE_ANIMS = {}

KNIFE_ANIMS['knife_throw_blade_first'] = {
    'frames': 34,
    'seat': SEAT_PINCH,
    'release': 19,
    'flight': {'dir': (-0.15, 0.97, -0.05), 'speed': 1.5, 'spin': 0},
    # slow draw, held aim beat, SNAP flick, eased follow-through
    'retime': [(1, 1), (10, 24), (15, 46), (19, 52), (24, 62), (34, 80)],
    'right': [
        (1,  *K_READY, 'pinch'),
        (10, (2.25, -0.55, 2.60), (0.10, 0.18, 0.98), (-0.10, 0.95, -0.15), 'pinch'),  # drawn beside the head
        (15, (2.30, -0.65, 2.65), (0.10, 0.16, 0.98), (-0.10, 0.95, -0.15), 'pinch'),  # aim beat
        (19, (1.45, 2.6, 0.85), (-0.15, 0.75, -0.64), (-0.05, 0.65, 0.75), 'pinch'),  # FLICK: release here
        (24, (1.10, 3.1, 0.10), (-0.18, 0.72, -0.67), (-0.05, 0.60, 0.79), 'open_release'),  # follow-through
        (34, *K_READY, 'idle'),
    ],
    'phases': [(1, 'ready'), (4, 'draw'), (15, 'aim beat'), (17, 'flick'),
               (20, 'release'), (25, 'recover')],
}

KNIFE_ANIMS['knife_throw_handle_first'] = {
    'frames': 36,
    'seat': SEAT_HAMMER,
    'release': 20,
    'flight': {'dir': (-0.10, 0.97, -0.10), 'speed': 1.4, 'spin': -900},
    # big cock, held beat, whole-arm HURL, heavier follow-through
    'retime': [(1, 1), (11, 28), (16, 52), (20, 58), (26, 70), (36, 90)],
    'right': [
        (1,  *K_READY, 'grip'),
        (11, (2.10, -0.70, 2.80), (0.12, 0.10, 0.99), (0.00, 0.90, -0.12), 'grip_tight'),  # cocked over shoulder
        (16, (2.15, -0.80, 2.85), (0.12, 0.08, 0.99), (0.00, 0.90, -0.12), 'grip_tight'),  # gather
        (20, (1.30, 2.9, 0.60), (-0.15, 0.72, -0.68), (-0.05, 0.68, 0.72), 'grip'),       # HURL: release here
        (26, (1.00, 3.3, -0.20), (-0.18, 0.68, -0.71), (-0.05, 0.62, 0.78), 'open_release'),
        (36, *K_READY, 'idle'),
    ],
    'phases': [(1, 'ready'), (4, 'cock'), (16, 'gather'), (18, 'hurl'),
               (21, 'release'), (27, 'recover')],
}


def _bake_knife():
    for name, spec in KNIFE_ANIMS.items():
        solved = []
        for frame, fist, fdir, bdir, pose in spec['right']:
            loc, rot = solve_key(fist, fdir, bdir)
            solved.append((frame, loc, rot, pose))
        spec['right'] = unwrap_eulers(solved)
        spec['left'] = left_idle(spec['frames'])
        anchors = spec.get('retime')
        if anchors:
            for side in ('right', 'left'):
                spec[side] = [(remap_frame(fr, anchors), loc, rot, pose)
                              for (fr, loc, rot, pose) in spec[side]]
            spec['phases'] = [(remap_frame(fr, anchors), lab)
                              for fr, lab in spec['phases']]
            spec['frames'] = remap_frame(spec['frames'], anchors)
            spec['release'] = remap_frame(spec['release'], anchors)


_bake_knife()


def build_knife_animation(name, knife, con):
    spec = KNIFE_ANIMS[name]
    for arm_name, side in ((RIGHT_ARM, 'right'), (LEFT_ARM, 'left')):
        arm = bpy.data.objects[arm_name]
        clear_anim(arm)
        for frame, loc, rot, pose in spec[side]:
            key_obj(arm, frame, loc, rot)
            if pose:
                key_pose(arm, frame, pose)
        smooth_fcurves(arm)

    # ── the release ──
    rel = spec['release']
    seat_loc, seat_rot = spec['seat']
    knife.animation_data_clear()

    # in-hand: constant local seat until the release frame. Scale is keyed
    # too: under ChildOf(influence=1) the hand's 3.118 multiplies in, in
    # free flight it does not — without the swap the knife would shrink 3x
    # at the moment of release.
    knife.location = seat_loc
    knife.rotation_euler = Euler([math.radians(a) for a in seat_rot], 'XYZ')
    knife.scale = (KNIFE_SCALE,) * 3
    for fr in (1, rel - 1):
        knife.keyframe_insert('location', frame=fr)
        knife.keyframe_insert('rotation_euler', frame=fr)
        knife.keyframe_insert('scale', frame=fr)
    knife.scale = (KNIFE_SCALE * HAND_SCALE,) * 3
    knife.keyframe_insert('scale', frame=rel)

    # world start = hand matrix at the release key @ seat
    rel_key = [k for k in spec['right'] if k[0] == rel]
    if not rel_key:
        raise ValueError('release frame %d has no right-hand key' % rel)
    _, hloc, hrot, _ = rel_key[0]
    m = hand_world_matrix(hloc, hrot)
    start = m @ Vector(seat_loc)

    fl = spec['flight']
    d = _norm(fl['dir'])
    # fly tip-first: knife +Z tracks the flight direction
    aim = d.to_track_quat('Z', 'Y').to_euler('XYZ')
    knife.location = start
    knife.rotation_euler = aim
    knife.keyframe_insert('location', frame=rel)
    knife.keyframe_insert('rotation_euler', frame=rel)
    n = spec['frames']
    for step, fr in ((1, rel + 4), (2, min(n, rel + 12)), (3, n + 8)):
        knife.location = start + d * fl['speed'] * (fr - rel)
        spin = math.radians(fl['spin']) * (fr - rel) / max(1, n - rel)
        e = Euler((aim.x + spin, aim.y, aim.z), 'XYZ')
        knife.rotation_euler = e
        knife.keyframe_insert('location', frame=fr)
        knife.keyframe_insert('rotation_euler', frame=fr)

    # constraint influence: rigid until release, free after
    con.influence = 1.0
    con.keyframe_insert('influence', frame=rel - 1)
    con.influence = 0.0
    con.keyframe_insert('influence', frame=rel)

    # knife curves: linear + constant switches (no eases on a ballistic prop)
    ad = knife.animation_data
    action = ad.action
    curve_sets = ([action.fcurves] if hasattr(action, 'fcurves')
                  else [cb.fcurves for L in action.layers for s in L.strips
                        for cb in s.channelbags])
    for fcurves in curve_sets:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = ('CONSTANT'
                                    if 'influence' in fc.data_path
                                    or kp.co[0] <= rel - 1 else 'LINEAR')

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, spec['frames']


def render_knife_animation(name, knife, con, samples=12):
    build_knife_animation(name, knife, con)
    spec = KNIFE_ANIMS[name]
    n = spec['frames']
    frames = sorted({max(1, min(n, round(1 + (n - 1) * i / (samples - 1))))
                     for i in range(samples)})
    scene = bpy.context.scene
    manifest = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = OUT_DIR + '\\knife_%s_%02d.png' % (name, i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3),
                         'phase': phase_of_knife(name, f)})
        print('rendered', path)
    with open(OUT_DIR + '\\knife_%s_manifest.json' % name, 'w') as fh:
        json.dump({'name': name, 'frames': n, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


def render_knife_full(name, knife, con):
    """Every frame -> <name>_%04d.png (ffmpeg -> mp4). Release constraint
    switch and flight keys ride along since build authors them."""
    build_knife_animation(name, knife, con)
    scene = bpy.context.scene
    scene.render.filepath = OUT_DIR + '\\%s_' % name
    bpy.ops.render.render(animation=True)
    print('rendered full sequence for', name)


def phase_of_knife(name, frame):
    label = ''
    for start, lab in KNIFE_ANIMS[name]['phases']:
        if frame >= start:
            label = lab
    return label


def knife_main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    full = '--full' in args
    args = [a for a in args if not a.startswith('--')]
    names = list(KNIFE_ANIMS) if (not args or args == ['all']) else args

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_camera_lights_world()
    for name in names:
        knife, con = attach_knife(KNIFE_ANIMS[name]['seat'])
        if full:
            render_knife_full(name, knife, con)
        else:
            render_knife_animation(name, knife, con)
        bpy.data.objects.remove(knife, do_unlink=True)


knife_main()
