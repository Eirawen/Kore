"""
WING POSE LIBRARY — her wings are a second face.

Khaled, seeing the spread-strategy comparison: "These poses should be
saved! She can emote with her wings. B unfold is emotionally different
than a shy C sweep or a D unfold with elev."

He's right, and it reframes the whole thing: I'd been treating the wings
as a PHYSICS problem (how do I spread them?) when they're an EXPRESSIVE
channel — the same lesson as "the hands are the protagonist's face",
scaled to a 2289-vertex appendage. Only the plank-swing was worthless,
because it wasn't a pose, it was an artifact.

A pose is (extension, aim direction, elevation), applied by AIMING each
bone in the chain — never by swinging it (see gotcha 54).
  extend 0 = the furled rest arc, 1 = fully straightened
  out    = the outward aim; -Y is her FRONT, so negative Y WRAPS the
           wings forward around her body (this is what reads as shy)
  elev   = root elevation, applied AFTER extension like a real wing
  asym   = degrees of L/R difference; perfect symmetry is the
           manufactured look. Independent wings make this free.
  sides  = optional per-side overrides -> a cocked, asymmetric attitude

Usage:
    from wing_poses import WING_POSES, apply_wing_pose
    apply_wing_pose(arm, 'shy')
    apply_wing_pose(arm, 'display', amount=0.6)   # blend from furled
"""
import math
from mathutils import Vector, Quaternion

NAMES = {'L': ['WingL_root', 'WingL_mid', 'WingL_tip'],
         'R': ['WingR_root', 'WingR_mid', 'WingR_tip']}

WING_POSES = {
    # ── neutral: drawn up and in behind her. Contained, reserved. ──
    'furled': dict(extend=0.0, out=(1, 0.15, 0.10), elev=0, asym=5,
                   reads='neutral / contained / at rest'),

    # ── DISPLAY: wide, membrane standing, hooks up. What she IS. ──
    'display': dict(extend=1.0, out=(1, 0.18, 0.10), elev=12, asym=6,
                    reads='confident / threat display / showing you'),

    # ── SHY: swept FORWARD so the wings wrap around her, half-closed.
    # This is the one that belongs in the coy emote, where her wings
    # currently do nothing at all.
    'shy': dict(extend=0.34, out=(1, -0.60, 0.06), elev=-6, asym=9,
                reads='hiding / coy / self-shielding'),

    # ── EAGER: extended AND lifted high. About to do something. ──
    'eager': dict(extend=1.0, out=(1, 0.10, 0.42), elev=32, asym=7,
                  reads='excited / aggressive / rising'),

    # ── DROOP: open but hanging, no tension in the membrane. ──
    'droop': dict(extend=0.72, out=(1, 0.12, -0.50), elev=-34, asym=11,
                  reads='spent / defeated / sad'),

    # ── CLAMP: snapped tight to her back, as small as she gets. ──
    'clamp': dict(extend=0.0, out=(1, 0.30, -0.05), elev=-16, asym=3,
                  reads='fear / flinch / struck'),

    # ── POWER: the down-stroke. Drives the hover's lift impulse. ──
    'power': dict(extend=0.92, out=(1, 0.16, -0.72), elev=-52, asym=6,
                  reads='the flap down-stroke'),

    # ── COCKED: one wing out, one furled. Only possible because the
    # wings are independent meshes — the payoff of splitting them. ──
    'cocked': dict(extend=0.0, out=(1, 0.15, 0.10), elev=0, asym=0,
                   sides={'L': dict(extend=0.95, out=(1, 0.20, 0.16), elev=18),
                          'R': dict(extend=0.10, out=(1, 0.22, -0.02), elev=-10)},
                   reads='curious / sizing you up / casual asymmetry'),
}


def _aim(pb, want_world, mw):
    """Point the bone along want_world using its LIVE matrix, so posed
    ancestors are respected: pose = M0^-1 . D . M0."""
    R = mw.to_3x3()
    Ri = R.inverted()
    pb.rotation_quaternion = Quaternion()
    _update()
    cur = (Ri @ ((mw @ pb.tail) - (mw @ pb.head))).normalized()
    des = (Ri @ Vector(want_world)).normalized()
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ cur.rotation_difference(des) @ M0
    _update()


def _update():
    import bpy
    bpy.context.view_layer.update()


def apply_wing_pose(arm, name, amount=1.0, keyframe=None):
    """Apply a named wing pose. amount blends from furled. If keyframe is
    an int, insert keys there (so poses compose into component tracks)."""
    spec = WING_POSES[name]
    mw = arm.matrix_world
    for side, sgn in (('L', 1), ('R', -1)):
        sub = (spec.get('sides') or {}).get(side, spec)
        asym = 1.0 + (spec.get('asym', 0) / 100.0) * (1 if side == 'R' else -1)
        ext = sub.get('extend', 0.0) * amount
        out = sub.get('out', (1, 0.15, 0.10))
        elev = sub.get('elev', 0) * amount * asym
        d = Vector((sgn, out[1] * asym, out[2])).normalized()
        for nm in NAMES[side]:
            pb = arm.pose.bones.get(nm)
            if pb is None:
                continue
            pb.rotation_mode = 'QUATERNION'
            if ext <= 1e-4:
                pb.rotation_quaternion = Quaternion()
            else:
                _aim(pb, d, mw)
                pb.rotation_quaternion = Quaternion().slerp(
                    pb.rotation_quaternion.copy(), ext)
        # elevation AFTER extension, root only (the order a wing uses)
        root = arm.pose.bones.get(NAMES[side][0])
        if root is not None and abs(elev) > 1e-6:
            m = root.bone.matrix_local.to_3x3().inverted()
            ay = (m @ Vector((0, 1, 0))).normalized()
            root.rotation_quaternion = (root.rotation_quaternion
                                        @ Quaternion(ay, math.radians(elev * sgn)))
        _update()
        if keyframe is not None:
            for nm in NAMES[side]:
                pb = arm.pose.bones.get(nm)
                if pb is not None:
                    pb.keyframe_insert('rotation_quaternion', frame=keyframe)
