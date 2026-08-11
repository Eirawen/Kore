#!/usr/bin/env python3
"""
build_arbelos.py — a divine being assembled from primitives.

BUILT TO KHALED'S SPEC, not to a vibe. He broke the drawing down part by
part (2026-08-05) after my first attempt came out, in his words, "incredibly
jumbled" — because I had been scattering plates with noise instead of PLACING
them. This version places every primitive exactly and adds disorder only as a
later, separate layer.

    FACE   four primitives meeting at ONE centre point:
             top    equilateral triangle, tip pointing DOWN into the centre
             left   wide-base isosceles, VERY SMALL, pointing RIGHT
             right  wide-base isosceles, VERY BIG, pointing LEFT
             bottom equilateral rhombus pointing UP, overlapping the point
    WINGS  overlapping, extremely thin rectangular PRISMS (boxes, not planes)
    BODY   there is none. Two rounded squares beneath the wings — one
           slightly smaller, one larger — which could be read as breasts but
           are of course squares.
    PINIONS 45-45-90 triangles of different sizes: upper pair pointing UP,
           lower pair pointing DOWN.

WHY THIS CREATURE IS BUILT AND NOT SCULPTED. From codex/the-real-game.md:
demons are human-esque and MUNDANE because they live inside the symbolic
language; divinity is OUTSIDE the compiler's vocabulary, so it renders as
noise. You cannot look at one properly until your sight improves. She is
therefore the one creature in the bestiary that is a FUNCTION rather than a
mesh — and the interesting parameter is how resolved she is to your eye.
"""
import bpy, bmesh, math, sys
from mathutils import Vector


# ─────────────────────────────────────────────────────────────────────
def _mesh(name, verts, coll, solid=0.0):
    """A flat polygon in the XY plane, optionally given prism depth."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmv = [bm.verts.new((v[0], v[1], 0.0)) for v in verts]
    f = bm.faces.new(bmv)
    if solid > 0.0:
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        vs = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, 0, solid), verts=vs)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def tri_apex(apex, base_c, half, coll, name, solid=0.0):
    """Isosceles triangle: apex at `apex`, base centred on `base_c`,
    half-width `half` measured perpendicular to the apex->base axis."""
    a = Vector(apex); b = Vector(base_c)
    d = (b - a); L = d.length
    n = Vector((-d.y / L, d.x / L))
    return _mesh(name, [a, b + n * half, b - n * half], coll, solid)


def right_iso(corner, leg, rot_deg, coll, name, solid=0.0):
    """45-45-90 triangle: right angle at `corner`, legs of length `leg`,
    the whole thing rotated by rot_deg."""
    pts = [Vector((0, 0)), Vector((leg, 0)), Vector((0, leg))]
    c, s = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    out = [(corner[0] + p.x*c - p.y*s, corner[1] + p.x*s + p.y*c) for p in pts]
    return _mesh(name, out, coll, solid)


def rounded_square(centre, w, h, r, coll, name, seg=4, solid=0.0):
    pts = []
    corners = [(w/2-r, h/2-r, 0), (-w/2+r, h/2-r, 90),
               (-w/2+r, -h/2+r, 180), (w/2-r, -h/2+r, 270)]
    for cx, cy, a0 in corners:
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg)
            pts.append((centre[0] + cx + r*math.cos(a),
                        centre[1] + cy + r*math.sin(a)))
    return _mesh(name, pts, coll, solid)


def rect(centre, w, h, coll, name, solid=0.0):
    x, y = centre
    return _mesh(name, [(x-w/2, y-h/2), (x+w/2, y-h/2),
                        (x+w/2, y+h/2), (x-w/2, y+h/2)], coll, solid)


# ─────────────────────────────────────────────────────────────────────
def build(coll=None):
    for o in list(bpy.data.objects):
        if o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    coll = coll or bpy.context.scene.collection
    P = {}
    THIN = 0.03                      # prism depth: "extremely thin"

    # ── FACE ── four primitives, one meeting point ───────────────────
    C = Vector((0.0, 2.72))
    face = []
    # top: equilateral, tip DOWN at C, base above
    side = 1.05
    hgt = side * math.sqrt(3) / 2
    face.append(_mesh('face_top', [C, (C.x - side/2, C.y + hgt),
                                   (C.x + side/2, C.y + hgt)], coll, THIN))
    # left: wide-base isosceles, VERY SMALL, pointing right (apex at C)
    face.append(tri_apex(C, (C.x - 0.40, C.y + 0.10), 0.20, coll,
                         'face_left', THIN))
    # right: wide-base isosceles, VERY BIG, pointing left (apex at C)
    face.append(tri_apex(C, (C.x + 0.62, C.y + 0.72), 0.42, coll,
                         'face_right', THIN))
    # bottom: equilateral rhombus pointing UP, overlapping the point
    rh = 0.34
    face.append(_mesh('face_rhombus',
                      [(C.x, C.y + 0.10), (C.x + rh, C.y - 0.42),
                       (C.x, C.y - 0.94), (C.x - rh, C.y - 0.42)], coll, THIN))
    P['face'] = face

    # ── WINGS ── overlapping thin prisms, rising as they go outward ──
    N = 5
    wings = []
    for side_i in (-1, 1):
        for i in range(N):
            t = i / (N - 1.0)                 # 0 = inner, 1 = outer
            s = 0.42 + 0.16 * t               # outer plates a touch larger
            x = side_i * (0.62 + t * 1.52)
            y = 1.86 + t * 0.62               # OUTER IS HIGHER
            ob = rect((x, y), s, s, coll,
                      'wing_%s_%d' % ('L' if side_i < 0 else 'R', i), THIN)
            ob['part'] = 'wing'; ob['side'] = side_i; ob['idx'] = i
            wings.append(ob)
    P['wing'] = wings

    # ── "BODY" ── there is none. Two rounded squares. ────────────────
    P['squares'] = [
        rounded_square((-0.52, 1.16), 0.94, 1.04, 0.20, coll, 'sq_small', solid=THIN),
        rounded_square(( 0.58, 1.04), 1.14, 1.26, 0.24, coll, 'sq_large', solid=THIN),
    ]

    # ── PINIONS ── 45-45-90s: upper pair UP, lower pair DOWN ─────────
    # PINIONS. Right-angled but STRETCHED — in the drawing they are long thin
    # blades that sweep outward and CROSS each other, not compact triangles.
    # Compact ones tiled into a box at the bottom, which read as furniture.
    # Upper pair rise outward; lower pair are larger and fall outward.
    P['pinion'] = [
        _mesh('pin_up_L', [(-2.55, 1.30), (0.30, 0.30), (-0.55, 0.22)], coll, THIN),
        _mesh('pin_up_R', [( 2.62, 1.16), (-0.22, 0.20), (0.62, 0.10)], coll, THIN),
        _mesh('pin_dn_L', [(-3.05, 0.05), (0.85, -0.55), (-1.05, -1.35)], coll, THIN),
        _mesh('pin_dn_R', [( 3.15, -0.10), (-0.70, -0.62), (1.25, -1.48)], coll, THIN),
    ]

    n = sum(len(v) for v in P.values())
    print('  built %d primitives: %s' % (n, {k: len(v) for k, v in P.items()}))
    return P


if __name__ == '__main__':
    build()
