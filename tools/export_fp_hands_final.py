"""
FINAL fp_hands.glb exporter — the full 11-clip handoff package for Sable.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand_wristed.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/export_fp_hands_final.py" \
    -- [--render-idles] [--out C:\\tmp\\fp_hands.glb]

Clips (11):
  idle_sword, idle_knife                       (authored here, 2 s loops)
  sword_light, sword_heavy_lr, sword_heavy_rl  (animate_sword_attacks.py, wristed,
                                                Khaled's retargeted grip)
  knife_throw_blade_first, knife_throw_handle_first (animate_knife.py, ChildOf release)
  cast_air_strike, cast_water_strike, cast_fire_strike, cast_earth_strike
                                               (animate_casts.py, post-polish)

Architecture (why it looks the way it does):
  The three animation systems stage the scene differently and key DIFFERENT
  channel subsets (attacks: right obj + wrist quats only; knife: obj + finger
  eulers; casts: obj + finger eulers). Under NLA_TRACKS baking, any channel a
  clip does NOT key would bake at whatever the scene state happens to be at
  export — silent cross-clip leakage. So this exporter makes every clip
  SELF-CONTAINED: each clip's actions key object loc/rot, all finger bones
  (euler XYZ), and forearm/hand (quaternion) on BOTH armatures, plus the
  knife (hidden in non-throw clips). Final bone rotation modes: fingers XYZ,
  forearm/hand QUATERNION — matching the channels each clip actually keys.

  Sword is NOT embedded (engine attaches Silverlight via the seat matrix in
  assets/fp_weapon_seats.json). Knife IS embedded (it flies during throws).

  Knife-under-meters-root integration (the last open item from
  codex/glb-export-notes.md #4): the knife is parented under FPHandsRoot and
  its ChildOf constraint gets inverse_matrix = root_scale^-1. ChildOf composes
  final = (target_world @ inverse) @ (parent @ basis); the inverse cancels the
  root on the in-hand path (target arm already carries the root), while free
  flight becomes root @ basis — authored hand-unit keys land in meters with
  ZERO changes to the blessed animation data. Verified numerically in-run
  (world scale magnitude constant ~1.0 m across the release) and in the
  browser by tools/fp_final_shot.js.

Also dumps (programmatically, from the retimed phase tables):
  C:\tmp\fp_hands_events.json   — per-clip named timestamps in seconds
  C:\tmp\fp_weapon_seats.json   — sword + knife seat matrices, hand-joint-local
"""
import bpy
import sys
import os
import math
import json
from mathutils import Vector, Euler, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = r'C:\tmp\fp_hands.glb'
EVENTS_JSON = r'C:\tmp\fp_hands_events.json'
SEATS_JSON = r'C:\tmp\fp_weapon_seats.json'
OUT_DIR = r'C:\tmp'
FPS = 60
IDLE_FRAMES = 121            # 2.0 s at 60 fps, first frame == last frame
ROOT_SCALE = 0.19 / 2.9      # hand units -> meters (glb-export-notes #5)
FIST_VOID = Vector((0.0, -0.22, 1.37))   # armature-local palm void (gotcha #29)

FLIGHT_OVERSHOOT = 8         # knife flight keys extend past the hand clip
CLIP_FRAMES = {}             # clip -> total frames (for events + sanity)
STASHES = []                 # (object_name, clip_name, action)
SWORD_SEAT_REL = None        # 4x4, right-hand JOINT-local (filled in phase A)
ORB_ANCHORS = {}             # cast clip -> anchor spec (filled in probe phase)
ATTACK_TABLES = {}           # remap_frame/RETIME/PHASES captured in phase A


def parse_args():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    opts = {'render_idles': '--render-idles' in args, 'out': OUT_DEFAULT}
    if '--out' in args:
        opts['out'] = args[args.index('--out') + 1]
    return opts


def load_ns(fname, stop_at):
    """Exec a tools/ script up to (excluding) its main def -> namespace dict.
    The scripts' own exec chains (UNC paths) run inside; no mains fire."""
    code = open(os.path.join(HERE, fname)).read()
    ns = {'__name__': 'ns_' + fname.replace('.py', '')}
    exec(code[:code.rfind(stop_at)], ns)
    return ns


# ───────────────────── channel-completeness helpers ─────────────────────

def snapshot_fingers(arm):
    """Current finger pose (everything except forearm/hand) as XYZ eulers."""
    snap = []
    for pb in arm.pose.bones:
        if pb.name in ('forearm', 'hand'):
            continue
        if pb.rotation_mode == 'QUATERNION':
            e = pb.rotation_quaternion.to_euler('XYZ')
        else:
            e = Euler(pb.rotation_euler, 'XYZ')
        snap.append((pb.name, Euler((e.x, e.y, e.z), 'XYZ')))
    return snap


def key_fingers(arm, snap, frames):
    for name, e in snap:
        pb = arm.pose.bones[name]
        pb.rotation_euler = e
        for f in frames:
            pb.keyframe_insert('rotation_euler', frame=f)


def key_wrist(arm, frames, fore_q=None, hand_q=None):
    fore = arm.pose.bones['forearm']
    hand = arm.pose.bones['hand']
    fore.rotation_quaternion = fore_q or Quaternion()
    hand.rotation_quaternion = hand_q or Quaternion()
    for f in frames:
        fore.keyframe_insert('rotation_quaternion', frame=f)
        hand.keyframe_insert('rotation_quaternion', frame=f)


def key_object(arm, frame, loc, rot_eul):
    arm.location = loc
    arm.rotation_euler = rot_eul
    arm.keyframe_insert('location', frame=frame)
    arm.keyframe_insert('rotation_euler', frame=frame)


def stash(obj, clip):
    act = obj.animation_data.action
    act.name = '%s__%s' % (clip, obj.name)
    act.use_fake_user = True
    STASHES.append((obj.name, clip, act))
    if getattr(obj.animation_data, 'action_slot', None) is not None:
        obj.animation_data.action_slot = None
    obj.animation_data.action = None
    return act


def fresh_action(obj, name):
    """EXPLICIT new action. Blender 5's slotted-action keying can silently
    re-use/extend a previously-stashed action when keyframe_insert runs with
    animation_data.action == None — that bloated the left hand's sword_light
    action to the idle's 121-frame range (exported strip range follows the
    action range: 2.017 s sword_light bug). Never key implicitly."""
    ad = obj.animation_data or obj.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.action = act
    slots = getattr(act, 'slots', None)
    if slots is not None:
        try:
            slot = slots.new(id_type='OBJECT', name=obj.name)
            ad.action_slot = slot
        except Exception as exc:
            print('WARN fresh_action slot:', exc)   # keyframe_insert will slot
    return act


def smooth_obj_fcurves(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    curve_sets = ([action.fcurves] if hasattr(action, 'fcurves')
                  else [cb.fcurves for L in action.layers for s in L.strips
                        for cb in s.channelbags])
    for fcurves in curve_sets:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'


# ───────────────────── idle rendering (grids for the record) ─────────────────────

def render_idle_samples(name, total, samples=12):
    scene = bpy.context.scene
    frames = sorted({max(1, min(total, round(1 + (total - 1) * i /
                                            (samples - 1))))
                     for i in range(samples)})
    manifest = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = OUT_DIR + '\\idle_%s_%02d.png' % (name, i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3), 'phase': 'breath'})
        print('rendered', path)
    with open(OUT_DIR + '\\idle_%s_manifest.json' % name, 'w') as fh:
        json.dump({'name': name, 'frames': total, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


# ═══════════════ PHASE A: sword clips + idle_sword (retargeted grip) ═══════════════

def phase_sword(render_idles):
    global SWORD_SEAT_REL
    ns = load_ns('animate_sword_attacks.py', 'def main')
    ATTACK_TABLES.update(remap_frame=ns['remap_frame'], RETIME=ns['RETIME'],
                         PHASES=ns['PHASES'])
    right, left, sword, report = ns['build_retargeted_grip']()
    base_hand_q = right.pose.bones['hand'].rotation_quaternion.copy()
    base_roll = report['forearm_roll_deg']
    snap_r = snapshot_fingers(right)
    snap_l = snapshot_fingers(left)
    left_loc = Vector(left.location)
    left_rot = Euler(left.rotation_euler, 'XYZ')
    left_hand_q = left.pose.bones['hand'].rotation_quaternion.copy()
    left_fore_q = left.pose.bones['forearm'].rotation_quaternion.copy()

    def key_left_static(clip, frames):
        fresh_action(left, 'tmp_%s_left' % clip)
        key_object(left, frames[0], left_loc, left_rot)
        for f in frames[1:]:
            key_object(left, f, left_loc, left_rot)
        key_fingers(left, snap_l, frames)
        key_wrist(left, frames, left_fore_q, left_hand_q)

    # — the three attacks —
    for clip, atk in (('sword_light', 'light'),
                      ('sword_heavy_lr', 'heavy_lr'),
                      ('sword_heavy_rl', 'heavy_rl')):
        total = ns['build_animation'](right, sword, base_hand_q, base_roll, atk)
        CLIP_FRAMES[clip] = total
        key_fingers(right, snap_r, (1, total))       # static grip, self-contained
        key_left_static(clip, (1, total))
        stash(right, clip)
        stash(left, clip)
        print('built', clip, total, 'frames')

    # — idle_sword: breath sway on the ready pose, loopable —
    fresh_action(right, 'tmp_idle_sword_right')
    fresh_action(left, 'tmp_idle_sword_left')
    ns['solve_key'](right, sword, base_hand_q, base_roll,
                    ns['ATTACKS']['light'][0])       # 1_ready
    loc0 = Vector(right.location)
    rot0 = Euler(right.rotation_euler, 'XYZ')
    hand_q0 = right.pose.bones['hand'].rotation_quaternion.copy()
    fore_q0 = right.pose.bones['forearm'].rotation_quaternion.copy()
    sway = [(1,   (0, 0, 0),           (0, 0, 0)),
            (31,  (0.02, 0.05, 0.09),  (0.8, 0, 0.3)),
            (61,  (-0.02, 0.02, 0.03), (0.3, 0, -0.3)),
            (91,  (0.01, -0.03, -0.06), (-0.5, 0, 0.2)),
            (121, (0, 0, 0),           (0, 0, 0))]
    for f, dl, dr in sway:
        key_object(right, f,
                   loc0 + Vector(dl),
                   Euler((rot0.x + math.radians(dr[0]),
                          rot0.y + math.radians(dr[1]),
                          rot0.z + math.radians(dr[2])), 'XYZ'))
    key_wrist(right, (1, 121), fore_q0, hand_q0)
    right.pose.bones['hand'].rotation_quaternion = (
        hand_q0 @ Quaternion((1, 0, 0), math.radians(2.0)))
    right.pose.bones['hand'].keyframe_insert('rotation_quaternion', frame=61)
    right.pose.bones['forearm'].rotation_quaternion = fore_q0
    right.pose.bones['forearm'].keyframe_insert('rotation_quaternion', frame=61)
    key_fingers(right, snap_r, (1, 121))
    for bn in ('Bone.018', 'Bone.019', 'Bone.015', 'Bone.016'):  # micro flex
        pb = right.pose.bones[bn]
        e = Euler(pb.rotation_euler, 'XYZ')
        pb.rotation_euler = (e.x + math.radians(2.5), e.y, e.z)
        pb.keyframe_insert('rotation_euler', frame=61)
        pb.rotation_euler = e
    # left: parked, its own tiny bob
    key_object(left, 1, left_loc, left_rot)
    key_object(left, 61, left_loc + Vector((0.01, 0.02, 0.05)), left_rot)
    key_object(left, 121, left_loc, left_rot)
    key_fingers(left, snap_l, (1, 121))
    key_wrist(left, (1, 121), left_fore_q, left_hand_q)
    ns['smooth_fcurves'](right)
    ns['smooth_fcurves'](left)
    CLIP_FRAMES['idle_sword'] = IDLE_FRAMES
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, IDLE_FRAMES
    print('built idle_sword', IDLE_FRAMES, 'frames')

    if render_idles:
        cam = ns['setup_world']()
        cam.data.lens = 40
        cam.location = Vector((0.0, -8.2, 4.9))
        cam.rotation_euler = ns['look_at'](cam.location, Vector((1.9, 1.5, 3.35)))
        render_idle_samples('idle_sword', IDLE_FRAMES)

    stash(right, 'idle_sword')
    stash(left, 'idle_sword')

    # — sword seat matrix, right-hand JOINT-local (bone head frame == the
    #   glTF joint node), pose-invariant because the sword is bone-parented —
    bpy.context.view_layer.update()
    J = right.matrix_world @ right.pose.bones['hand'].matrix
    SWORD_SEAT_REL = J.inverted() @ sword.matrix_world
    err = max(abs(a - b) for ra, rb in
              zip(J @ SWORD_SEAT_REL, sword.matrix_world)
              for a, b in zip(ra, rb))
    print('sword seat rel (joint-local) reconstruction err %.6f det %.3f'
          % (err, SWORD_SEAT_REL.determinant()))
    bpy.data.objects.remove(sword, do_unlink=True)


# ═══════════════ PHASE B: idle_knife + knife throws ═══════════════

def phase_knife(render_idles):
    ns = load_ns('animate_knife.py', 'def knife_main')
    ns['strip_scene']()          # clears phase-A camera/lights; keeps hands
    ns['stage_hands']()
    ns['apply_matte']([bpy.data.objects[ns['RIGHT_MESH']],
                       bpy.data.objects[ns['LEFT_MESH']]])
    ns['setup_camera_lights_world']()
    right = bpy.data.objects[ns['RIGHT_ARM']]
    left = bpy.data.objects[ns['LEFT_ARM']]

    # — idle_knife: hammer-grip ready (knife attaches via seat at runtime) —
    ns['clear_anim'](right)
    ns['clear_anim'](left)
    fresh_action(right, 'tmp_idle_knife_right')
    fresh_action(left, 'tmp_idle_knife_left')
    ns['POSES']['grip_idle'] = {'f': [78, 88, 60], 'thumb': [42, 52, 29]}
    loc0, rot0 = ns['solve_key'](*ns['K_READY'])
    loc0 = Vector(loc0)
    sway = [(1,   (0, 0, 0),            (0, 0, 0),   'grip'),
            (31,  (0.02, 0.04, 0.08),   (1.0, 0, 0), None),
            (61,  (-0.01, 0.01, 0.02),  (0.4, 0, -0.4), 'grip_idle'),
            (91,  (0.01, -0.02, -0.05), (-0.6, 0, 0.2), None),
            (121, (0, 0, 0),            (0, 0, 0),   'grip')]
    for f, dl, dr, pose in sway:
        ns['key_obj'](right, f, tuple(loc0 + Vector(dl)),
                      (rot0[0] + dr[0], rot0[1] + dr[1], rot0[2] + dr[2]))
        if pose:
            ns['key_pose'](right, f, pose)
    for f, loc, rot, pose in ns['left_idle'](IDLE_FRAMES):
        ns['key_obj'](left, f, loc, rot)
        ns['key_pose'](left, f, pose)
    key_wrist(right, (1, IDLE_FRAMES))
    key_wrist(left, (1, IDLE_FRAMES))
    ns['smooth_fcurves'](right)
    ns['smooth_fcurves'](left)
    CLIP_FRAMES['idle_knife'] = IDLE_FRAMES
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, IDLE_FRAMES
    print('built idle_knife', IDLE_FRAMES, 'frames')
    if render_idles:
        render_idle_samples('idle_knife', IDLE_FRAMES)
    stash(right, 'idle_knife')
    stash(left, 'idle_knife')

    # — the two throws (knife attached once, seat re-keyed per clip) —
    knife, con = ns['attach_knife'](
        ns['KNIFE_ANIMS']['knife_throw_blade_first']['seat'])
    knife.name = 'ThrowingKnife'
    for name in ('knife_throw_blade_first', 'knife_throw_handle_first'):
        ns['build_knife_animation'](name, knife, con)
        total = ns['KNIFE_ANIMS'][name]['frames']
        # the knife's flight keys run FLIGHT_OVERSHOOT past the hand keys —
        # the GLB clip is that long; hands hold their settle pose at the tail
        CLIP_FRAMES[name] = total + FLIGHT_OVERSHOOT
        key_wrist(right, (1, total))
        key_wrist(left, (1, total))
        stash(right, name)
        stash(left, name)
        stash(knife, name)
        print('built', name, total, 'frames, release f%d'
              % ns['KNIFE_ANIMS'][name]['release'])
    return knife, con, ns


# ═══════════════ PHASE C: the four casts ═══════════════

def phase_casts():
    ns = load_ns('animate_casts.py', 'def main')
    # NO strip_scene here: it would delete the knife. stage only.
    ns['stage_hands']()
    right = bpy.data.objects[ns['RIGHT_ARM']]
    left = bpy.data.objects[ns['LEFT_ARM']]
    for name in ('air_strike', 'water_strike', 'fire_strike', 'earth_strike'):
        clip = 'cast_' + name
        ns['build_animation'](name)
        total = ns['ANIMS'][name]['frames']
        CLIP_FRAMES[clip] = total
        key_wrist(right, (1, total))     # casts leave the wrist at rest
        key_wrist(left, (1, total))
        stash(right, clip)
        stash(left, clip)
        print('built', clip, total, 'frames')
    return ns


# ═══════════════ PHASE D-G: hidden knife, modes, NLA, root ═══════════════

def _assign_slot(strip, act):
    slots = getattr(act, 'slots', None)
    if slots and hasattr(strip, 'action_slot'):
        try:
            strip.action_slot = slots[0]
        except Exception as exc:
            print('WARN action_slot assign failed:', exc)


def _linear_fcurves(obj):
    action = obj.animation_data.action
    curve_sets = ([action.fcurves] if hasattr(action, 'fcurves')
                  else [cb.fcurves for L in action.layers for s in L.strips
                        for cb in s.channelbags])
    for fcurves in curve_sets:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def prebake_knife_tracks(root, right, left, knife, knife_ns):
    """THE fix for the multi-clip constraint landmine: the glTF exporter
    bakes each object's NLA track WITHOUT synchronizing the other objects'
    NLA state, so the knife's ChildOf-driven motion bakes against the wrong
    armature animation once 11 tracks exist (the spike passed only because
    knife clips were exported alone). Pre-bake the knife's root-local motion
    here with the correct per-clip solo state, replace the strip actions
    with plain keyed TRS, and REMOVE the constraint — the exporter then has
    nothing left to get wrong."""
    scene = bpy.context.scene
    root_inv = root.matrix_world.inverted()
    baked = {}
    for clip in ('knife_throw_blade_first', 'knife_throw_handle_first'):
        n = knife_ns['KNIFE_ANIMS'][clip]['frames'] + FLIGHT_OVERSHOOT
        for obj in (right, left, knife):
            solo_track(obj, clip)
        samples = []
        for f in range(1, n + 1):
            scene.frame_set(f)
            deps = bpy.context.evaluated_depsgraph_get()
            samples.append(root_inv @ knife.evaluated_get(deps).matrix_world)
        for obj in (right, left, knife):
            solo_track(obj, clip, False)
        baked[clip] = samples
    for c in list(knife.constraints):
        knife.constraints.remove(c)
    knife.rotation_mode = 'QUATERNION'
    ad = knife.animation_data
    for clip, samples in baked.items():
        fresh_action(knife, '%s__ThrowingKnife_baked' % clip)
        prev_q = None
        for f, M in enumerate(samples, start=1):
            M3 = M.to_3x3()
            det = M3.determinant()
            s = abs(det) ** (1.0 / 3.0)
            sign = 1.0 if det >= 0 else -1.0
            Mn = Matrix([[v / (sign * s) for v in row] for row in M3])
            q = Mn.to_quaternion()
            if prev_q is not None and prev_q.dot(q) < 0:
                q.negate()
            prev_q = q
            knife.location = M.to_translation()
            knife.rotation_quaternion = q
            knife.scale = (sign * s,) * 3
            knife.keyframe_insert('location', frame=f)
            knife.keyframe_insert('rotation_quaternion', frame=f)
            knife.keyframe_insert('scale', frame=f)
        _linear_fcurves(knife)
        act = ad.action
        act.use_fake_user = True
        if getattr(ad, 'action_slot', None) is not None:
            ad.action_slot = None
        ad.action = None
        for track in ad.nla_tracks:
            if track.name == clip:
                for strip in list(track.strips):
                    track.strips.remove(strip)
                strip = track.strips.new(clip, 1, act)
                strip.name = clip
                _assign_slot(strip, act)
                _fit_strip(strip, CLIP_FRAMES[clip])
        print('prebaked knife track %s (%d frames, constraint removed)'
              % (clip, len(samples)))


def add_hidden_knife_tracks(knife, clips):
    """Knife parked out of sight in every non-throw clip, so ANY clip
    playback resets the knife node (post-throw crossfades included)."""
    ad = knife.animation_data
    fresh_action(knife, 'knife_hidden')
    knife.location = (0.0, 0.0, -30.0)
    knife.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    knife.scale = (0.001,) * 3
    for f in (1, 2):
        knife.keyframe_insert('location', frame=f)
        knife.keyframe_insert('rotation_quaternion', frame=f)
        knife.keyframe_insert('scale', frame=f)
    act = ad.action
    act.use_fake_user = True
    if getattr(ad, 'action_slot', None) is not None:
        ad.action_slot = None
    ad.action = None
    for clip in clips:
        track = ad.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, act)
        strip.name = clip
        _assign_slot(strip, act)
        _fit_strip(strip, CLIP_FRAMES[clip])
    print('hidden knife tracks:', len(clips))


def set_rotation_modes(arms):
    for arm in arms:
        for pb in arm.pose.bones:
            pb.rotation_mode = ('QUATERNION' if pb.name in ('forearm', 'hand')
                                else 'XYZ')


def _fit_strip(strip, n):
    """Pin the strip to frames 1..n at 1:1 speed. The exporter derives each
    track's bake range from the strip range — this makes clip length a
    hard invariant instead of an emergent property of action ranges."""
    try:
        strip.use_sync_length = False
    except Exception:
        pass
    strip.action_frame_start = 1
    strip.action_frame_end = n
    strip.frame_start = 1
    strip.frame_end = n
    strip.scale = 1.0


def build_nla(objs):
    clips = sorted({c for _, c, _ in STASHES})
    by_obj = {}
    for oname, clip, act in STASHES:
        by_obj.setdefault(oname, {})[clip] = act
    for obj in objs:
        ad = obj.animation_data or obj.animation_data_create()
        for track in list(ad.nla_tracks):
            ad.nla_tracks.remove(track)
        for clip in clips:
            act = by_obj.get(obj.name, {}).get(clip)
            if act is None:
                continue
            track = ad.nla_tracks.new()
            track.name = clip
            strip = track.strips.new(clip, 1, act)
            strip.name = clip
            _assign_slot(strip, act)
            _fit_strip(strip, CLIP_FRAMES[clip])
            if int(strip.frame_end) != CLIP_FRAMES[clip]:
                raise RuntimeError('strip range drift: %s/%s ends %s want %d'
                                   % (obj.name, clip, strip.frame_end,
                                      CLIP_FRAMES[clip]))
        print('NLA for %s: %d tracks, strip ends %s'
              % (obj.name, len(ad.nla_tracks),
                 [(t.name, int(t.strips[0].frame_end))
                  for t in ad.nla_tracks]))


def cleanup_scene(keep):
    for obj in list(bpy.data.objects):
        if obj.name not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)


def add_root(children, knife, con):
    root = bpy.data.objects.new('FPHandsRoot', None)
    bpy.context.scene.collection.objects.link(root)
    root.scale = (ROOT_SCALE,) * 3
    for obj in children:
        obj.parent = root
        obj.matrix_parent_inverse.identity()
    # ChildOf composes final = (target @ inverse) @ (parent @ basis).
    # The target arm now carries the root scale; cancel the owner-side root
    # so the authored hand-unit keys stay valid, in hand AND in flight.
    inv = 1.0 / ROOT_SCALE
    con.inverse_matrix = Matrix.Diagonal((inv, inv, inv, 1.0))
    bpy.context.view_layer.update()
    print('FPHandsRoot scale %.4f, knife ChildOf inverse %.4f'
          % (ROOT_SCALE, inv))
    return root


# ═══════════════ PHASE H: numeric verification (NLA solo) ═══════════════

def solo_track(obj, clip, on=True):
    for track in obj.animation_data.nla_tracks:
        if track.name == clip:
            track.is_solo = on
            return
    raise RuntimeError('no track %s on %s' % (clip, obj.name))


def probe_knife_release(right, knife, knife_ns):
    scene = bpy.context.scene
    clip = 'knife_throw_blade_first'
    rel = knife_ns['KNIFE_ANIMS'][clip]['release']
    total = knife_ns['KNIFE_ANIMS'][clip]['frames']
    for obj in (right, bpy.data.objects['Armature.003'], knife):
        solo_track(obj, clip)
    ok = True
    prev_pos = None
    print('KNIFE PROBE (%s, release f%d): meters-root integration' % (clip, rel))
    for f in (1, rel - 8, rel - 1, rel, rel + 4, rel + 12, total):
        scene.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        km = knife.evaluated_get(deps).matrix_world
        hm = right.evaluated_get(deps).matrix_world
        kpos, kscale = km.translation, km.to_scale()
        smag = sum(abs(v) for v in kscale) / 3.0
        dist = (kpos - hm.translation).length
        step = (kpos - prev_pos).length if prev_pos is not None else 0.0
        prev_pos = Vector(kpos)
        print('  f%03d  scale |%.4f| (%+.4f,%+.4f,%+.4f)  hand-dist %.4f m  step %.4f'
              % (f, smag, *kscale, dist, step))
        if abs(smag - 4.9 * 3.118 * ROOT_SCALE) > 0.02:
            ok = False
    for obj in (right, bpy.data.objects['Armature.003'], knife):
        solo_track(obj, clip, False)
    print('KNIFE PROBE verdict:', 'SCALE CONSTANT OK' if ok else 'SCALE DRIFT — CHECK')


def probe_clip_motion(right, left, clip, frames):
    """Cheap liveness probe: the armature objects must move under the solo'd
    track (catches dead action_slots / leaked channels)."""
    scene = bpy.context.scene
    for obj in (right, left):
        solo_track(obj, clip)
    pts = []
    for f in frames:
        scene.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        r = right.evaluated_get(deps).matrix_world.translation
        pts.append(Vector(r))
        print('  %s f%03d right (%.3f,%.3f,%.3f)' % (clip, f, *r))
    for obj in (right, left):
        solo_track(obj, clip, False)
    span = max((p - pts[0]).length for p in pts)
    print('  %s right-hand travel span %.4f m' % (clip, span))
    return span


def solve_orb_anchor(right, left, clip, frame, world_point):
    """Express a Blender-world orb point in the RIGHT hand JOINT's local
    frame at `frame` (track solo'd) -> constant hand-riding offset."""
    scene = bpy.context.scene
    for obj in (right, left):
        solo_track(obj, clip)
    scene.frame_set(frame)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    J = ev.matrix_world @ ev.pose.bones['hand'].matrix
    off = J.inverted() @ world_point
    for obj in (right, left):
        solo_track(obj, clip, False)
    return [round(v, 4) for v in off]


def void_world(right, clip, frame):
    scene = bpy.context.scene
    solo_track(right, clip)
    scene.frame_set(frame)
    deps = bpy.context.evaluated_depsgraph_get()
    p = right.evaluated_get(deps).matrix_world @ FIST_VOID
    solo_track(right, clip, False)
    return p


# ═══════════════ PHASE I: metadata sidecars ═══════════════

def t_of(frame):
    # the exporter's baked sampler places frame f at f/60 s (verified by GLB
    # parse: first sample 0.0167, clip length N/60) — NOT (f-1)/60.
    return round(frame / FPS, 4)


def phase_start(phases, label):
    for f, lab in phases:
        if lab == label:
            return f
    raise KeyError(label)


def build_events(knife_ns, casts_ns):
    remap = ATTACK_TABLES['remap_frame']
    RETIME, PHASES = ATTACK_TABLES['RETIME'], ATTACK_TABLES['PHASES']
    ev = {}
    for clip in CLIP_FRAMES:
        ev[clip] = {'duration': t_of(CLIP_FRAMES[clip])}
    ev['idle_sword']['loop'] = True
    ev['idle_knife']['loop'] = True
    for clip, atk, wind, imp in (
            ('sword_light', 'light', 'gather', 'drive'),
            ('sword_heavy_lr', 'heavy_lr', 'windup', 'sweep'),
            ('sword_heavy_rl', 'heavy_rl', 'windup', 'sweep')):
        ph, rt = PHASES[atk], RETIME[atk]
        ev[clip]['windup'] = t_of(remap(phase_start(ph, wind), rt))
        ev[clip]['impact_window'] = [
            t_of(remap(phase_start(ph, imp), rt)),
            t_of(remap(phase_start(ph, 'recover'), rt))]
        ev[clip]['recover'] = t_of(remap(phase_start(ph, 'recover'), rt))
    for clip in ('knife_throw_blade_first', 'knife_throw_handle_first'):
        ev[clip]['release'] = t_of(knife_ns['KNIFE_ANIMS'][clip]['release'])
    cast_map = {
        'cast_air_strike':   ('air_strike', 'anticipate', 'seal', 'fling'),
        'cast_water_strike': ('water_strike', 'anticipate', 'clasp', 'fling'),
        'cast_fire_strike':  ('fire_strike', 'present', 'flicker beat', 'fling'),
        'cast_earth_strike': ('earth_strike', 'clench', 'chamber', 'punch fwd'),
    }
    for clip, (name, gather, spawn, launch) in cast_map.items():
        ph = casts_ns['ANIMS'][name]['phases']      # already retimed at import
        ev[clip]['gather_start'] = t_of(phase_start(ph, gather))
        ev[clip]['orb_spawn'] = t_of(phase_start(ph, spawn))
        ev[clip]['launch'] = t_of(phase_start(ph, launch))
        ev[clip]['recover'] = t_of(phase_start(ph, 'follow-through'))
        if clip in ORB_ANCHORS:
            ev[clip]['orb_anchor'] = ORB_ANCHORS[clip]
    return ev


def build_seats(knife_ns, right):
    hand_rest = right.data.bones['hand'].matrix_local   # armature space, head
    note = ('parent weapon to the RIGHT `hand` joint node, apply this matrix '
            'as the node local transform (rows are row-major 4x4; includes '
            'scale + the mirrored-parent handedness)')

    def rows(m):
        return [[round(v, 6) for v in r] for r in m]

    def knife_seat(seat):
        loc, rot = seat
        m = (Matrix.Translation(Vector(loc)) @
             Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4() @
             Matrix.Diagonal((knife_ns['KNIFE_SCALE'],) * 3).to_4x4())
        return rows(hand_rest.inverted() @ m)   # armature-local -> joint-local

    return {
        'convention': {
            'socket': "the `hand` bone joint node of each armature "
                      "(right = Armature.001 subtree, left = Armature.003 subtree; "
                      "glTF may rename dots to underscores)",
            'usage': note,
            'chirality_note': 'the RIGHT hand joint world matrix has NEGATIVE '
                              'determinant (mirrored armature); any prop parented '
                              'there renders mirror-flipped. The seat matrices '
                              'themselves are proper (det>0) and were tuned in '
                              'this frame, so Silverlight/knife look correct; a '
                              'new CHIRAL prop needs a mirror-corrected mesh or '
                              'seat (see brief footnote)',
        },
        'silverlight_sword': {
            'source_glb': 'Silverlight.glb (raw node, no import conversion)',
            'parent': 'right hand joint',
            'matrix': [[round(v, 6) for v in r] for r in SWORD_SEAT_REL],
        },
        'knife_pinch': {
            'source_glb': 'assets/test_knife.glb (+Z blade, 26 cm)',
            'parent': 'right hand joint',
            'used_by': 'knife_throw_blade_first (also the embedded knife seat)',
            'matrix': knife_seat(knife_ns['SEAT_PINCH']),
        },
        'knife_hammer': {
            'source_glb': 'assets/test_knife.glb (+Z blade, 26 cm)',
            'parent': 'right hand joint',
            'used_by': 'idle_knife / knife_throw_handle_first held state',
            'matrix': knife_seat(knife_ns['SEAT_HAMMER']),
        },
    }


# ═══════════════ export ═══════════════

def export_glb(path):
    kwargs = dict(
        filepath=path,
        export_format='GLB',
        export_animations=True,
        export_animation_mode='NLA_TRACKS',
        export_bake_animation=True,
        export_force_sampling=True,
        export_optimize_animation_size=False,
        # constant channels MUST survive: the parked left hand / hidden knife
        # are constant by design, and a culled channel means runtime leakage
        # from whatever clip played before
        export_optimize_animation_keep_anim_armature=True,
        export_optimize_animation_keep_anim_object=True,
        export_def_bones=False,
        export_skins=True,
        export_yup=True,
        export_apply=False,
        export_cameras=False,
        export_extras=False,
        export_morph=False,
    )
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    dropped = [k for k in kwargs if k not in props and k != 'filepath']
    if dropped:
        print('WARN exporter params not in this Blender, dropped:', dropped)
    kwargs = {k: v for k, v in kwargs.items() if k == 'filepath' or k in props}
    bpy.ops.export_scene.gltf(**kwargs)
    print('exported', path)


def main():
    opts = parse_args()
    print('export_fp_hands_final opts:', json.dumps(opts))

    phase_sword(opts['render_idles'])
    knife, con, knife_ns = phase_knife(opts['render_idles'])
    casts_ns = phase_casts()

    right = bpy.data.objects['Armature.001']
    left = bpy.data.objects['Armature.003']

    set_rotation_modes((right, left))
    build_nla((right, left, knife))

    # final scene: hands + knife only, under the meters root
    cleanup_scene({'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002',
                   'ThrowingKnife'})
    root = add_root((right, left, knife), knife, con)

    # bake the knife's constrained motion ourselves (correct solo state),
    # then drop the constraint + add the hidden-knife tracks
    prebake_knife_tracks(root, right, left, knife, knife_ns)
    add_hidden_knife_tracks(knife, [c for c in sorted(CLIP_FRAMES)
                                    if not c.startswith('knife_throw')])
    # knife base state = hidden
    knife.location = (0.0, 0.0, -30.0)
    knife.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    knife.scale = (0.001,) * 3

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, max(CLIP_FRAMES.values())
    scene.render.fps = FPS

    # — numeric verification before export —
    probe_knife_release(right, knife, knife_ns)
    print('LIVENESS PROBES')
    probe_clip_motion(right, left, 'sword_light', (1, 28, 48))
    probe_clip_motion(right, left, 'cast_water_strike', (1, 70, 116))
    probe_clip_motion(right, left, 'idle_sword', (1, 61))

    # — orb anchors (v1 pragmatic; fire/earth solved joint-local) —
    casts = casts_ns['ANIMS']
    air_spawn = phase_start(casts['air_strike']['phases'], 'seal')
    water_spawn = phase_start(casts['water_strike']['phases'], 'clasp')
    fire_spawn = phase_start(casts['fire_strike']['phases'], 'flicker beat')
    earth_spawn = phase_start(casts['earth_strike']['phases'], 'chamber')
    ORB_ANCHORS['cast_air_strike'] = {
        'type': 'midpoint_hand_joints',
        'note': 'midpoint of right+left `hand` joint world positions '
                '(the orb home is the gap between the sandwich palms)'}
    ORB_ANCHORS['cast_water_strike'] = {
        'type': 'midpoint_hand_joints',
        'note': 'midpoint of right+left `hand` joint world positions '
                '(the clasp gap)'}
    p_fire = void_world(right, 'cast_fire_strike', fire_spawn) + Vector((0, 0, 0.06))
    ORB_ANCHORS['cast_fire_strike'] = {
        'type': 'right_hand_joint_offset',
        'offset_joint_local': solve_orb_anchor(right, left, 'cast_fire_strike',
                                               fire_spawn, p_fire),
        'note': 'offset in the RIGHT hand joint LOCAL frame (joint units — '
                'world scale bakes in via the joint matrix): ~6 cm above the '
                'cupped palm at the flicker beat; parent emitter to the joint '
                'and apply this local offset'}
    p_earth = void_world(right, 'cast_earth_strike', earth_spawn) + Vector((0, 0.10, 0))
    ORB_ANCHORS['cast_earth_strike'] = {
        'type': 'right_hand_joint_offset',
        'offset_joint_local': solve_orb_anchor(right, left, 'cast_earth_strike',
                                               earth_spawn, p_earth),
        'note': 'offset in the RIGHT hand joint LOCAL frame: ~10 cm ahead of '
                'the chambered fist; parent emitter to the joint and apply '
                'this local offset'}
    # midpoint sanity print for air/water
    for clip, fr in (('cast_air_strike', air_spawn),
                     ('cast_water_strike', water_spawn)):
        for obj in (right, left):
            solo_track(obj, clip)
        scene.frame_set(fr)
        deps = bpy.context.evaluated_depsgraph_get()
        jr = right.evaluated_get(deps).matrix_world @ \
            right.evaluated_get(deps).pose.bones['hand'].matrix
        jl = left.evaluated_get(deps).matrix_world @ \
            left.evaluated_get(deps).pose.bones['hand'].matrix
        gap = (jr.translation - jl.translation).length
        mid = (jr.translation + jl.translation) / 2
        print('%s spawn f%d hand-joint gap %.3f m, midpoint (%.3f,%.3f,%.3f)'
              % (clip, fr, gap, *mid))
        for obj in (right, left):
            solo_track(obj, clip, False)

    # — sidecars —
    events = build_events(knife_ns, casts_ns)
    with open(EVENTS_JSON, 'w') as fh:
        json.dump({'fps': FPS, 'time_convention':
                   't = (frame-1)/60 s from clip start', 'clips': events},
                  fh, indent=1)
    print('WROTE', EVENTS_JSON)
    seats = build_seats(knife_ns, right)
    with open(SEATS_JSON, 'w') as fh:
        json.dump(seats, fh, indent=1)
    print('WROTE', SEATS_JSON)

    print('CLIP_FRAMES', json.dumps(CLIP_FRAMES))
    export_glb(opts['out'])


main()
