"""
build_arbelos.py — the angel of primitives.

Divinity renders as NOISE because it is outside the compiler's vocabulary
(codex/the-real-game.md). She is not a sculpted body; she is a set of flat
primitives at exact positions — a FUNCTION, not a mesh. Which makes her the
first creature in the bestiary that is easier to build than to model.

SHE IS A BILLBOARD, AND THAT IS THE DESIGN (Khaled, 2026-08-11): flat
geometry that always faces the player. Walk around her and she does not turn
— she HAS no other side. There is no angle from which she resolves, because
there is nothing there to resolve. So every primitive is COPLANAR; z is used
only for draw order, never for form.

Phase 1 of a perception ladder. One float — how resolved she is to the
player's eye — should eventually carry her from this to a woman.

Khaled's spec, part by part:
  FACE     four primitives meeting at ONE point: a big equilateral triangle
           above with its tip pointing DOWN into the centre; a VERY SMALL
           wide-based isosceles left, pointing right; a VERY BIG one right,
           pointing left; an equilateral rhombus below pointing UP, its top
           vertex overlapping the meeting point.
  WINGS    the overlapping squares. A chain that rises as it goes outward.
  BODY     there is none. Two rounded squares beneath the wings, left
           smaller, right larger. "They are of course, squares."
  PINIONS  four 45-45-90 triangles of different sizes, CONNECTED BY LINES
           that enclose a square between them. The lines overshoot their
           corners, so what the eye reads is long blades crossing.
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector

OUT = r'C:\Users\kmessai\Downloads\Kore\Arbelos'
Z = 0.0                      # she is COPLANAR. z is draw order only.
DZ = 0.002                   # per-layer nudge so coplanar faces do not fight

def _mesh(name, verts2, z):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new((x, z, y)) for (x, y) in verts2]   # Y-up scene, flat in XZ
    bm.faces.new(vs)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob

FILL_MODE = [False]
Z_BASE = [0.0]
# THE SALAMI. She is not 3D and she is not zero — she is the thickness of
# GOLD LEAF ON AN ICON: the depth of paint on a surface, ~1/150th of her
# height. Zero width makes the dodge and the disperse read as renderer
# failures rather than as vanishing, robs the metals and the grime of an
# edge to catch, and — the one that would actually bite — every billboard
# lags a frame or two behind fast camera rotation, so a zero-width figure
# FLICKERS COMPLETELY OUT on those frames instead of merely going thin.
THICK = [0.040]
LW = 0.014                   # line weight. SHE IS LINE ART, NOT SILHOUETTE.

def poly(name, pts, layer=0, lw=None):
    """A shape is its OUTLINE, not its fill. Khaled's drawings are line art
    and the effect depends on seeing THROUGH the overlaps — a filled version
    destroys exactly the quality that makes her unresolvable. Each edge
    becomes a thin quad, which also keeps the very thin triangles honest
    (a centroid-inset outline collapses them)."""
    w = LW if lw is None else lw
    # MINUS: the camera sits at -Y looking toward +Y, so SMALLER Y is
    # NEARER. Adding layer*DZ pushed higher layers AWAY — which is why the
    # quad (layer 0) was covering the rounded squares (layer 6).
    z = Z_BASE[0] - layer * DZ
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if FILL_MODE[0]:
        vs = [bm.verts.new((x, z, y)) for (x, y) in pts]
        f = bm.faces.new(vs)
        if THICK[0] > 1e-6:
            r = bmesh.ops.extrude_face_region(bm, geom=[f])
            moved = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=moved, vec=(0.0, THICK[0], 0.0))
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, -THICK[0]*0.5, 0.0))
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        return ob
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]; bx, by = pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        if L < 1e-9: continue
        ux, uy = dx / L, dy / L
        ax -= ux * w * 0.5; ay -= uy * w * 0.5      # extend to close corners
        bx += ux * w * 0.5; by += uy * w * 0.5
        px, py = -uy * w * 0.5, ux * w * 0.5
        q = [(ax+px, ay+py), (bx+px, by+py), (bx-px, by-py), (ax-px, ay-py)]
        vs = [bm.verts.new((x, z, y)) for (x, y) in q]
        bm.faces.new(vs)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob

def rot(p, a, o=(0, 0)):
    c, s = math.cos(a), math.sin(a)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * c - y * s, o[1] + x * s + y * c)

def bar(name, a, b, w, layer=0, over=0.0):
    """A LINE as geometry: a thin quad from a to b, optionally overshooting
    both ends. The overshoot is what makes four edges read as long crossing
    blades rather than a tidy box."""
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    ax -= ux * over; ay -= uy * over
    bx += ux * over; by += uy * over
    px, py = -uy * w * 0.5, ux * w * 0.5
    return poly(name, [(ax + px, ay + py), (bx + px, by + py),
                       (bx - px, by - py), (ax - px, ay - py)], layer)

def rounded_square(name, cx, cy, w, h_, r, layer=0, seg=6):
    hw, hh = w * 0.5, h_ * 0.5; pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, math.pi/2), (-1, -1, math.pi), (1, -1, 3*math.pi/2)):
        ox, oy = cx + sx * (hw - r), cy + sy * (hh - r)
        for i in range(seg + 1):
            a = a0 + (math.pi / 2) * i / seg
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return poly(name, pts, layer)

bpy.ops.wm.read_factory_settings(use_empty=True)

def build(FILL):
    parts = []

    # ── FACE ──────────────────────────────────────────────────────────
    # Four primitives, one meeting point. The rhombus overlaps that point.
    C = (-0.47, 5.22)
    S = 1.18
    top = S * 1.15
    parts += [poly('face_top', [C, (C[0]-top*0.5, C[1]+top*0.87), (C[0]+top*0.5, C[1]+top*0.87)], 3)]
    sm = S * 0.34
    parts += [poly('face_left_small', [C, (C[0]-sm, C[1]+sm*0.62), (C[0]-sm*0.86, C[1]-sm*0.72)], 4)]
    bg = S * 1.02
    parts += [poly('face_right_big', [C, (C[0]+bg*0.94, C[1]+bg*0.80), (C[0]+bg*0.66, C[1]-bg*0.30)], 2)]
    rh = S * 0.46
    parts += [poly('face_rhombus', [(C[0], C[1]+rh*0.30), (C[0]+rh*0.62, C[1]-rh*0.62),
                                    (C[0], C[1]-rh*1.72), (C[0]-rh*0.62, C[1]-rh*0.62)], 5)]

    # ── WINGS: four RECTANGLES per side, wider than tall, stepping
    # down and inward, each overlapping its neighbour by about a third.
    WING = [(0.79, 0.49), (0.74, 0.60), (0.73, 0.64), (0.56, 0.42)]   # outer->inner
    STEP_IN, STEP_DN = 0.44, 0.28
    for side in (-1, 1):
        x = side * 2.16; y = 5.30
        for i, (w, h) in enumerate(WING):
            nm = 'wing_%s_%d' % ('L' if side < 0 else 'R', i)
            parts += [poly(nm, [(x-w/2, y-h/2), (x+w/2, y-h/2),
                                (x+w/2, y+h/2), (x-w/2, y+h/2)], 1)]
            x -= side * STEP_IN
            y -= STEP_DN

    # ── NO BODY. Two rounded squares. Left smaller, right larger. ─────
    parts += [rounded_square('sq_left',  -1.05, 3.51, 1.15, 1.34, 0.28, 6)]
    parts += [rounded_square('sq_right',  0.41, 3.42, 1.46, 1.57, 0.32, 6)]

    # ── THE LOWER STRUCTURE IS FOUR LINES. Everything else falls out.
    #
    # Two roughly-horizontal segments and two roughly-vertical ones, each
    # tilted a few degrees. Where they cross they fence off a quadrilateral —
    # the "square circumscribed between them". Each line then OVERSHOOTS its
    # crossings to a free end, and joining the two free ends at each corner to
    # their crossing point gives the four triangles. They differ in size only
    # because the overshoots differ in length. Nothing here is placed
    # independently: four segments, and the square and all four triangles are
    # consequences.
    H1 = ((-2.61, 3.28), (3.42, 3.07))      # upper horizontal
    H2 = ((-3.95, 1.52), (3.71, 0.92))      # lower horizontal
    V1 = ((-1.61, 4.18), (-2.12, 0.21))     # left vertical
    V2 = (( 1.62, 4.41), ( 1.31, 0.48))     # right vertical

    def cross(p, q):
        (x1,y1),(x2,y2) = p; (x3,y3),(x4,y4) = q
        d = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        a = x1*y2 - y1*x2; b = x3*y4 - y3*x4
        return ((a*(x3-x4) - (x1-x2)*b)/d, (a*(y3-y4) - (y1-y2)*b)/d)

    TL = cross(H1, V1); TR = cross(H1, V2)
    BR = cross(H2, V2); BL = cross(H2, V1)

    parts += [poly('quad', [TL, TR, BR, BL], 0)]                    # the square
    parts += [poly('tri_UL', [H1[0], V1[0], TL], 0)]                # free end, free end, crossing
    parts += [poly('tri_UR', [H1[1], V2[0], TR], 0)]
    parts += [poly('tri_LL', [H2[0], V1[1], BL], 0)]
    parts += [poly('tri_LR', [H2[1], V2[1], BR], 0)]

    return parts

def emit(parts, name):
    mat = bpy.data.materials.new('arb_' + name)
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (1, 1, 1, 1)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    # semi-transparent so OVERLAPS ACCUMULATE like real ink; the fill pass's
    # alpha channel then carries ink density, not just coverage
    mx.inputs[0].default_value = 0.40 if FILL_MODE[0] else 1.0
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(mx.outputs[0], out.inputs[0])
    mat.blend_method = 'BLEND'
    try: mat.show_transparent_back = True
    except Exception: pass
    for o in parts: o.data.materials.append(mat)

# ── DIVINITY, SHAPE BY SHAPE ──────────────────────────────────────
# Khaled: "Divinity is PASTELS next to NEON next to METALLIC next to
# ROUGH and GRIME and EVERYTHING ALL AT ONCE."
#
# The mistake was TRANCHING — three tidy coherent palettes, which is the
# opposite of the idea. And it is not only hue: flat neon cannot sit
# beside real metal unless the metal has a specular sweep across it and
# the grime actually mottles. So every shape gets its own TREATMENT.
#
# Nothing here is generated. Nineteen shapes, nineteen decisions.

def _mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em  = nt.nodes.new('ShaderNodeEmission'); em.inputs[1].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m, nt, em

def _coord(nt, scale=1.0, rot=0.0, space='Generated'):
    """GENERATED, not Object. Every part's origin sits at world zero (the
    meshes are built in world coords), so Object coords span the WHOLE
    figure and each small shape samples one thin slice of a single
    gradient — which is why the metals came out flat. Generated
    normalises to each object's own bounding box, so every shape gets its
    own sweep. Grime stays on Object so the grain size is consistent
    across her rather than scaling with each shape."""
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs[2].default_value[1] = rot
    mp.inputs[3].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs[space], mp.inputs[0])
    return mp

def FLAT(c, e=1.0):
    def f(name):
        m, nt, em = _mat(name)
        em.inputs[0].default_value = hx(c); em.inputs[1].default_value = e
        return m
    return f

def METAL(dark, lite, rot=0.0, sharp=0.55):
    """A specular sweep across the shape. Flat colour cannot read as metal;
    a hard bright band travelling over a dark body can."""
    def f(name):
        m, nt, em = _mat(name)
        mp = _coord(nt, 1.0, rot)
        gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'LINEAR'
        rm = nt.nodes.new('ShaderNodeMapRange')
        rm.inputs[1].default_value = sharp - 0.30
        rm.inputs[2].default_value = sharp + 0.30
        cr = nt.nodes.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = hx(dark)
        cr.color_ramp.elements[1].color = hx(lite)
        cr.color_ramp.elements[0].position = 0.44
        cr.color_ramp.elements[1].position = 0.57
        cr.color_ramp.interpolation = 'EASE'

        nt.links.new(mp.outputs[0], gr.inputs[0])
        nt.links.new(gr.outputs['Fac'], rm.inputs[0])
        nt.links.new(rm.outputs[0], cr.inputs[0])
        nt.links.new(cr.outputs[0], em.inputs[0])
        return m
    return f

def GRIME(base, filth, scale=9.0, e=1.0):
    """Mottled, uneven, corroded. Divinity that has been left outdoors."""
    def f(name):
        m, nt, em = _mat(name)
        mp = _coord(nt, 1.0, space='Object')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = 8.0
        nz.inputs['Roughness'].default_value = 0.75
        cr = nt.nodes.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = hx(filth)
        cr.color_ramp.elements[1].color = hx(base)
        cr.color_ramp.elements[0].position = 0.34
        cr.color_ramp.elements[1].position = 0.68
        nt.links.new(mp.outputs[0], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], cr.inputs[0])
        nt.links.new(cr.outputs[0], em.inputs[0])
        em.inputs[1].default_value = e
        return m
    return f

def IRIDESCENT(a, b, c, scale=0.5):
    """Oil on water: three hues sweeping, so the surface never commits."""
    def f(name):
        m, nt, em = _mat(name)
        mp = _coord(nt, 1.0, 0.6)
        gr = nt.nodes.new('ShaderNodeTexGradient')
        cr = nt.nodes.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = hx(a)
        cr.color_ramp.elements[0].position = 0.08
        cr.color_ramp.elements[1].color = hx(c)
        cr.color_ramp.elements[1].position = 0.92
        e2 = cr.color_ramp.elements.new(0.5); e2.color = hx(b)
        nt.links.new(mp.outputs[0], gr.inputs[0])
        nt.links.new(gr.outputs['Fac'], cr.inputs[0])
        nt.links.new(cr.outputs[0], em.inputs[0])
        return m
    return f

def hx(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)

# ── the nineteen ──────────────────────────────────────────────────
# NOTE ON STRENGTH: in a Standard view transform with no bloom, emission
# above 1.0 does not glow — it CLIPS TO WHITE. Every "luminous pastel" I
# pushed to 1.7-3.4 simply became paper. So everything sits at 1.0 and the
# identity is carried by CHROMA; the glow is added as a real bloom pass in
# post, where it belongs.
DIVINE = {
  # THE FACE — four incompatible substances meeting at one point
  'face_top':        METAL('#c47f00', '#ffe066', rot=0.9),   # gold leaf
  'face_left_small': FLAT('#ffffff'),                        # the sliver you cannot look at
  'face_right_big':  FLAT('#7b1fd4'),                        # ultraviolet
  'face_rhombus':    FLAT('#ff1744'),                        # arterial. the one ORGANIC thing.

  # LEFT WING
  'wing_L_0': FLAT('#3fc0ff'),                               # sky
  'wing_L_1': FLAT('#c6ff00'),                               # acid
  'wing_L_2': METAL('#008a72', '#3fffcf', rot=2.1),          # verdigris
  'wing_L_3': GRIME('#00d9ff', '#1436c8', 14.0),             # corrosion, electric teal

  # RIGHT WING — the same four ideas, OUT OF STEP. Not a pair.
  'wing_R_0': FLAT('#ff2fb2'),                               # neon where the left was pastel
  'wing_R_1': FLAT('#ff9e5c'),                               # pastel where the left was neon
  'wing_R_2': METAL('#a3005f', '#ff8ad9', rot=0.35),         # chrome rose
  'wing_R_3': GRIME('#ffc400', '#8a1fff', 11.0),             # gold blooming into violet

  # THE TWO SQUARES
  'sq_left':  IRIDESCENT('#ff6fcf', '#5ed8ff', '#9dff6f'),   # mother of pearl
  'sq_right': METAL('#d94f00', '#ffc247', rot=1.6, sharp=0.48),

  # THE CENTRE — the largest shape, a sheet of light that never settles on
  # one colour. Not a hole and not white: it OVERWHELMS.
  'quad':     IRIDESCENT('#ff7ac6', '#ffd76a', '#6fe8ff', scale=1.0),

  # FOUR PINIONS — one of each substance, so no corner agrees
  'tri_UL': FLAT('#9d7aff'),                                 # lavender
  'tri_UR': FLAT('#00ffd0'),                                 # electric
  'tri_LL': METAL('#b87400', '#ffe9a8', rot=2.7),            # brass
  'tri_LR': GRIME('#ff5ea8', '#ffb200', 8.0),                # rose-gold bloom
}

def paint_divine(parts):
    for o in parts:
        f = DIVINE.get(o.name)
        if f is None:
            f = FLAT('#ff00ff', 1.0)          # loud, so a miss is obvious
        o.data.materials.append(f('div_' + o.name))

def paint_flat(parts, rgba, name):
    m, nt, em = _mat(name); em.inputs[0].default_value = rgba
    for o in parts: o.data.materials.append(m)

# ── mode ────────────────────────────────────────────────────────
MODE = 'still'
try:
    with open(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\divinity\.arbcfg') as fh:
        MODE = fh.read().strip() or 'still'
except Exception: pass

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.film_transparent = True
try:
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
except Exception: pass
if MODE == 'fp':
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
elif MODE == 'hyper':
    sc.render.resolution_x = sc.render.resolution_y = 720
elif MODE == 'ext':
    sc.render.resolution_x, sc.render.resolution_y = 1120, 700
else:
    sc.render.resolution_x = sc.render.resolution_y = 1400
cd = bpy.data.cameras.new('C')
if MODE == 'still':
    cd.type = 'ORTHO'; cd.ortho_scale = 9.6
elif MODE == 'ext':
    cd.type = 'ORTHO'; cd.ortho_scale = 16.0
elif MODE == 'fp':
    # The real test of an attack is not whether it photographs well — it is
    # whether a player can READ IT IN TIME TO MOVE. Eye height, combat
    # distance, game field of view, 16:9.
    cd.type = 'PERSP'; cd.lens = 22.0          # ~80 deg horizontal
else:
    cd.type = 'PERSP'; cd.lens = 33.0
cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector((0, 0, 3.1))
if MODE == 'ext':
    # ~38 deg OFF her facing axis, not 90. Dead side-on she has ZERO WIDTH
    # and does not render at all — true to what she is, but it means the
    # frame shows only the attack. Off-axis she is foreshortened but
    # present, so her body and the projectile are legible together.
    tgt = Vector((0.0, -4.6, 2.10))
    cam.location = Vector((7.4, -13.2, 7.4))
elif MODE == 'fp':
    tgt = Vector((0.0, 0.0, 2.80))             # only a mild tilt up, so the
                                               # incoming lance stays IN FRAME
    cam.location = Vector((0.0, -9.5, 1.70))   # player eye height, closer
else:
    cam.location = tgt + Vector((0, -10 if MODE == 'still' else -13.5, 0))
    if MODE == 'anim': cam.location.z += 1.1
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()

for o in list(bpy.data.objects):
    if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
FILL_MODE[0] = True;  Z_BASE[0] = 0.0
fills = build(True); paint_divine(fills)
FILL_MODE[0] = False; Z_BASE[0] = -0.10
paint_flat(build(False), (0.10, 0.02, 0.16, 1), 'ink')

named = set(DIVINE); got = set(o.name for o in fills)
print('SHAPES %d   unstyled: %s' % (len(fills), sorted(got - named) or 'none'))

if MODE == 'still':
    sc.render.filepath = os.path.join(OUT, 'arbelos_divine.png')
    bpy.ops.render.render(write_still=True)
    raise SystemExit

# ══════════════════════════════════════════════════════════════════
if MODE == 'salami':
    import shutil
    for th, tag in ((0.0, 'zero'), (0.040, 'leaf'), (0.110, 'thick')):
        for ang, aname in ((90, 'edge'), (78, 'near'), (52, 'three_q')):
            for o in list(bpy.data.objects):
                if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
            THICK[0] = th
            FILL_MODE[0] = True;  Z_BASE[0] = 0.0
            paint_divine(build(True))
            FILL_MODE[0] = False; Z_BASE[0] = -0.10
            paint_flat(build(False), (0.10, 0.02, 0.16, 1), 'ink_%s_%d' % (tag, ang))
            r = math.radians(ang)
            tg = Vector((0, 0, 3.1))
            cam.location = tg + Vector((math.sin(r) * 12.5, -math.cos(r) * 12.5, 0.9))
            cam.rotation_euler = (tg - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(OUT, 'salami_%s_%s.png' % (tag, aname))
            bpy.ops.render.render(write_still=True)
    print('SALAMI grid done')
    raise SystemExit

# HYPER — 4D projection. VETOED FOR ARBELOS, KEPT AS A CAPABILITY.
#
# Khaled, 2026-08-11: "Veto'ing it. I preferred the 2d versions
# significantly. We can keep the 4d capability to try with other beings,
# that may fit it better, but the completely flat to 2d to 4d is probably
# just not the right format."
#
# He is right, and the reason generalises: the projection DESTROYS THE
# PROPERTY THAT MAKES HER WORK. She is compelling because she is flat and
# has no other side; a 4D->3D projection gives her depth, which is the one
# thing she was never supposed to have. It made a different creature
# wearing her shapes.
#
# Worth keeping for a being whose identity is NOT flatness — something
# that should read as intruding from outside the world rather than as a
# drawing pinned to it.
#
# Khaled's friend, looking at the lance: "Ur doing the 4d rotation thing
# where u interpolate between the 4th dimension or something?"
#
# I was not — that was a rotation gradient along a chain, which merely
# shares the visual signature. But he identified something better than
# what I built, because it EXPLAINS HER. Why she is flat. Why she cannot
# be walked around. Why her plates refuse to agree: they are not separate
# objects, they are cross-sections of ONE object at different depths in a
# dimension you do not have.
#
# So: give every vertex a real fourth coordinate w, rotate in two planes
# that both involve w, and project 4D->3D by dividing through by (D - w).
# Shapes then SWELL, CONTRACT and PASS THROUGH EACH OTHER while staying
# perfectly rigid — motion with no 3D explanation, which is the entire
# brief for a being outside the compiler's vocabulary.
#
# DOUBLE ROTATION, and the rates are incommensurate (golden ratio). A
# single rotation plane has a 3D lookalike; a double rotation does not.
# You cannot produce this by spinning anything, in any way, in 3D.
if MODE == 'salami':
    import shutil
    for th, tag in ((0.0, 'zero'), (0.040, 'leaf'), (0.110, 'thick')):
        for ang, aname in ((90, 'edge'), (78, 'near'), (52, 'three_q')):
            for o in list(bpy.data.objects):
                if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
            THICK[0] = th
            FILL_MODE[0] = True;  Z_BASE[0] = 0.0
            paint_divine(build(True))
            FILL_MODE[0] = False; Z_BASE[0] = -0.10
            paint_flat(build(False), (0.10, 0.02, 0.16, 1), 'ink_%s_%d' % (tag, ang))
            r = math.radians(ang)
            tg = Vector((0, 0, 3.1))
            cam.location = tg + Vector((math.sin(r) * 12.5, -math.cos(r) * 12.5, 0.9))
            cam.rotation_euler = (tg - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(OUT, 'salami_%s_%s.png' % (tag, aname))
            bpy.ops.render.render(write_still=True)
    print('SALAMI grid done')
    raise SystemExit

if MODE == 'hyper':
    import math as _m
    # These three numbers decide whether she SHIMMERS or DISINTEGRATES.
    # At spread 1.35 against D4 3.10 the projection factor hit 5x and she
    # tore herself off the screen. Keeping w small relative to the 4D
    # viewing distance holds the swell near +/-10%: wrongness, not wreckage.
    W_SPREAD = 1.30        # how far apart the slices sit in the 4th dimension
    W_TILT   = 0.34        # each shape is also TILTED in w, not just offset
    D4       = 6.00        # 4D viewing distance for the projection

    MESHES = [o for o in bpy.data.objects if o.type == 'MESH']
    ORIG, WCO = {}, {}
    for j, o in enumerate(MESHES):
        vs = [v.co.copy() for v in o.data.vertices]
        ORIG[o.name] = vs
        c = sum(vs, Vector((0,0,0))) / len(vs)
        base = W_SPREAD * (2.0 * (j / max(1, len(MESHES) - 1)) - 1.0)
        # Per-vertex w tilt must NOT be a linear function of x. Any
        # x-proportional depth is exactly what a 3D perspective rotation
        # produces, so correlating w with x makes the whole effect collapse
        # into a turntable. RADIAL from the shape's own centre instead:
        # unrelated to screen position, so no 3D rotation can imitate it.
        WCO[o.name] = [base + W_TILT * ((v - c).length - 0.55) for v in vs]

    NF = 132
    d = os.path.join(OUT, 'anim', 'hyper'); os.makedirs(d, exist_ok=True)
    for f in range(NF):
        t  = f / NF
        # ROTATE IN THE YW PLANE. This is the whole correction.
        #
        # xw rotation gives w' = x*sin(a) + w*cos(a) — and w proportional to
        # x, divided through by depth, IS a 3D perspective turntable. The
        # induced term (+/-0.83) outvoted the real per-shape w (+/-0.55), so
        # the "4D" motion degenerated into an ordinary 3D spin. Khaled called
        # it immediately.
        #
        # She is FLAT, so her y extent is ~0. Rotating in yw therefore gives
        # w' ~= w*cos(a) with NOTHING induced — every shape swells and
        # shrinks by its OWN hidden depth, with no relationship to where it
        # sits on screen. That is the part 3D cannot fake: you cannot spin an
        # object such that two shapes side by side scale in opposite
        # directions for reasons invisible in the picture.
        a1 = 2 * _m.pi * t                              # YW plane — full sweep
        a2 = 0.16 * _m.sin(2 * _m.pi * t * 0.6180339887)  # XW, small: lateral wrongness
        c1, s1 = _m.cos(a1), _m.sin(a1)
        c2, s2 = _m.cos(a2), _m.sin(a2)
        for o in MESHES:
            vs, ws = ORIG[o.name], WCO[o.name]
            for i, v in enumerate(o.data.vertices):
                x, y, z, w = vs[i].x, vs[i].y, vs[i].z, ws[i]
                y, w = y * c1 - w * s1, y * s1 + w * c1     # rotate in YW
                x, w = x * c2 - w * s2, x * s2 + w * c2     # rotate in XW (small)
                k = D4 / max(0.55, D4 - w)                  # 4D -> 3D projection
                v.co = (x * k, y, z * k)
            o.data.update()
        sc.render.filepath = os.path.join(d, 'f_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
    print('HYPER %d frames' % NF)
    raise SystemExit

# ══════════════════════════════════════════════════════════════════
# ANIMATION — she has NO SKELETON, so the PRIMITIVE is the animatable
# unit. Nineteen independent 2D transforms; the vocabulary is entirely
# what plates can do to each other: drift, gather, stream, scatter.
# ══════════════════════════════════════════════════════════════════
import random
# The lance is a CHAIN OF TRIANGLES stacking toward the viewer, so it
# needs geometry that does not exist in her resting form. Spawned here,
# parked at zero scale, and only the lance clip ever wakes them.
LANCE_N = 11
SEG = []
src = next(o for o in bpy.data.objects if o.name.startswith('tri_UR'))
# each segment gets its OWN material, cycling her substances, so the
# chain reads as a chain of distinct blades rather than one cyan mass
SEG_MATS = ['tri_UR', 'face_right_big', 'wing_R_0', 'tri_LL',
            'wing_L_1', 'face_top', 'wing_R_2', 'tri_UL']
for k in range(LANCE_N):
    c = src.copy(); c.data = src.data.copy(); c.name = 'lance_seg_%02d' % k
    bpy.context.collection.objects.link(c)
    c.data.materials.clear()
    c.data.materials.append(DIVINE[SEG_MATS[k % len(SEG_MATS)]]('seg_%d' % k))
    c.scale = (0.001, 0.001, 0.001)
    SEG.append(c)

# Where the PLAYER is. In fp that is the camera; in ext it is the target
# cube and the camera stands off to the side. Attacks aim at the player,
# never at the viewer — which only becomes a distinction in ext mode.
TARGET_POS = (Vector((0.0, -9.0, 1.05)) if MODE == 'ext' else
              Vector((0.0, -9.5, 1.70)) if MODE == 'fp' else
              Vector((0.0, -13.5, 3.1)))
CAM_POS = TARGET_POS
EXTRA = []
if MODE == 'ext':
    # the player, standing where the player stands
    bpy.ops.mesh.primitive_cube_add(size=1.55, location=(0.0, -9.0, 0.78))
    cube = bpy.context.active_object; cube.name = 'TARGET'
    mc, ntc, emc = _mat('target')
    emc.inputs[0].default_value = (0.55, 0.58, 0.62, 1.0)
    cube.data.materials.append(mc)
    # ground, so depth is READABLE — without it nothing has a position
    bpy.ops.mesh.primitive_plane_add(size=46.0, location=(0.0, -6.0, 0.0))
    gp = bpy.context.active_object; gp.name = 'GROUND'
    mg, ntg, emg = _mat('ground')
    emg.inputs[0].default_value = (0.055, 0.052, 0.070, 1.0)
    gp.data.materials.append(mg)
    EXTRA = [cube, gp]

# JUDGEMENT needs a blade. She does not SUMMON a weapon — divinity does
# not reach for a tool — she REARRANGES HERSELF INTO ONE. These are her
# own substance: plates that leave her, climb, and lock into an edge.
BLADE_N = 5
BLADE = []
bsrc = next(o for o in bpy.data.objects if o.name.startswith('face_right_big'))
# WARM METALS ONLY. Her body is deliberate material mismatch; a WEAPON
# has to read as ONE OBJECT, and seven unrelated substances fragment it
# into confetti. Gold, white-hot, molten, brass.
BLADE_MATS = ['face_top', 'face_left_small', 'sq_right', 'tri_LL', 'face_top']
for k in range(BLADE_N):
    c = bsrc.copy(); c.data = bsrc.data.copy(); c.name = 'blade_%02d' % k
    bpy.context.collection.objects.link(c)
    c.data.materials.clear()
    c.data.materials.append(DIVINE[BLADE_MATS[k % len(BLADE_MATS)]]('bl_%d' % k))
    c.scale = (0.001, 0.001, 0.001)
    BLADE.append(c)

ALL = [o for o in bpy.data.objects if o.type == 'MESH' and o not in EXTRA]

# rotation/scale must happen about each SHAPE's own centre, not world zero
bpy.ops.object.select_all(action='DESELECT')
for o in ALL: o.select_set(True)
bpy.context.view_layer.objects.active = ALL[0]
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
bpy.ops.object.select_all(action='DESELECT')

REST = {o.name: (o.location.copy(), o.rotation_euler.copy(), o.scale.copy()) for o in ALL}
FACE = [o for o in ALL if o.name.startswith('face') or o.name.startswith('div_face')]
def plate_index(o):
    """Fill and outline are separate objects that share a name, so Blender
    suffixes the second '.001'. Deriving the index from the NAME (not from
    list position) keeps a plate's fill and its outline on the same launch
    delay — otherwise the chain fires in eight uneven steps instead of four."""
    base = o.name.split('.')[0]
    try: return int(base.rsplit('_', 1)[1])
    except Exception: return 0

def wing(side):
    return [o for o in ALL if ('wing_%s_' % side) in o.name]

def key(o, f):
    o.keyframe_insert('location', frame=f)
    o.keyframe_insert('rotation_euler', frame=f)
    o.keyframe_insert('scale', frame=f)

def reset():
    for o in ALL:
        L, R, S = REST[o.name]
        o.location, o.rotation_euler, o.scale = L.copy(), R.copy(), S.copy()

def new_action(name):
    for o in ALL:
        o.animation_data_clear()
        o.animation_data_create()
        a = bpy.data.actions.new('%s_%s' % (name, o.name))
        a.use_fake_user = True
        o.animation_data.action = a

def bake(name, nframes, fn, fps=30):
    """fn(o, i, t) sets the object's transform for normalised time t."""
    new_action(name)
    for f in range(nframes + 1):
        t = f / nframes
        reset()
        for i, o in enumerate(ALL):
            fn(o, i, t)
        for o in ALL: key(o, f)
    sc.frame_start, sc.frame_end = 0, nframes
    sc.render.fps = fps

# ── IDLE ──────────────────────────────────────────────────────────
# Every plate on its OWN period, none commensurate, so the arrangement
# never repeats. The face runs at triple frequency: it is permanently
# the least stable thing on her. Plus a slow global bob.
PRIMES = [7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79]
random.seed(4)
JIT = {o.name: (random.uniform(0, 6.283), random.uniform(0, 6.283),
                random.uniform(0.6, 1.4)) for o in ALL}

def idle(o, i, t):
    if o in BLADE: o.scale = (0.001,0.001,0.001); return
    if o in SEG: o.scale = (0.001, 0.001, 0.001); return
    pa, pb, amp = JIT[o.name]
    fast = 3.0 if o in FACE else 1.0
    k = PRIMES[i % len(PRIMES)] / 23.0
    o.rotation_euler[1] += math.radians(2.4 * amp * fast
                                        * math.sin(2*math.pi*t*k + pa))
    o.location.x += 0.055 * amp * math.sin(2*math.pi*t*k*0.7 + pb)
    o.location.z += 0.048 * amp * math.cos(2*math.pi*t*k*1.3 + pa)
    o.location.z += 0.115 * math.sin(2*math.pi*t)          # global bob
    sc_ = 1.0 + 0.020 * amp * math.sin(2*math.pi*t*k*0.5 + pb)
    o.scale = (sc_, sc_, sc_)

# ── LANCE (gomu gomu no pistoru) ──────────────────────────────────
# Khaled's drawing: not the wings, and not a stretch — TRIANGLES STACKING
# AT YOU, each rotated. Since she is a billboard permanently facing the
# player, the chain has to leave her plane and come OUT OF THE SCREEN.
# The camera sits at -Y, so the lance travels in -Y, and each segment is
# thrown alternately up and down so the chain zigzags as it reaches.
LANCE_REACH  = 0.82      # per segment, in -Y. The chain must STOP
                         # WELL SHORT of the lens: at 1.15 the last segment
                         # sat basically on the camera and filled the frame.
LANCE_ZIG    = 0.60      # alternating screen-vertical throw
LANCE_ANCHOR = Vector((1.05, 0.0, 2.75))

# Aimed at the CAMERA, not simply along -Y. A lance that travels parallel
# to the view axis passes beside you and reads as scenery; one that grows
# on your eye line reads as a threat you have to leave.
def _aim_frame():
    a = LANCE_ANCHOR
    d = (TARGET_POS - a); d.normalize()
    r = d.cross(Vector((0, 0, 1)));  r.normalize()
    u = r.cross(d);                  u.normalize()
    return d, r, u

def lance(o, i, t):
    # extend 0 -> 1 -> hold -> retract, with a hard snap out and a slower haul back
    # WIND-UP. Without this the attack goes from nothing to fully extended
    # in ~0.7s and there is nothing to react TO. The first three blades
    # gather at the source and SHIVER first — the player's cue to leave.
    TELE = 0.30
    if t < TELE:
        if o in SEG:
            k = SEG.index(o)
            if k > 2:
                o.scale = (0.001, 0.001, 0.001); return
            g = t / TELE
            sh = math.sin(t * 62.0) * 0.10 * g
            dv, rv, uv = _aim_frame()
            o.location = LANCE_ANCHOR + dv * (0.30 * k) + uv * (sh + 0.12 * k)
            o.rotation_euler = (math.radians(sh * 90), 0.0,
                                math.radians(30 * (1 if k % 2 else -1) * g))
            b = 0.16 * (0.4 + 0.6 * g)
            o.scale = (b, b, b)
        else:
            c = math.sin(t / TELE * math.pi) ** 2
            o.location.x += c * 0.22                  # she COCKS before she throws
            o.rotation_euler[1] += math.radians(c * 4.0)
        return

    t = (t - TELE) / (1.0 - TELE)                     # remap: the attack proper
    if   t < 0.14: u = 0.0
    elif t < 0.46: u = ((t - 0.14) / 0.32) ** 0.55        # SNAP out
    elif t < 0.62: u = 1.0                                # hang, fully extended
    else:          u = 1.0 - ((t - 0.62) / 0.38) ** 1.7   # haul back

    if o in SEG:
        k = SEG.index(o)
        lead = k / float(LANCE_N)                 # each segment waits its turn
        a = max(0.0, min(1.0, (u - lead * 0.72) / 0.28))
        if a <= 0.001:
            o.scale = (0.001, 0.001, 0.001); return
        dv, rv, uv = _aim_frame()
        reach = (k + 1) * LANCE_REACH * a
        # The zigzag TAPERS toward the player. Constant amplitude means the
        # near blades — a metre from the lens — swing right off the top of
        # frame. A lance CONVERGES on what it is aimed at: wide chaos at her
        # end, a point at yours.
        taper = 1.0 - 0.78 * (k / float(LANCE_N))
        zig   = LANCE_ZIG * taper * (1 if k % 2 else -1) * a
        o.location = LANCE_ANCHOR + dv * reach + uv * zig + rv * (0.10 * a * taper)
        # each one ROTATED — the chain pinwheels as it reaches
        o.rotation_euler = (math.radians(26 * (1 if k % 2 else -1) * a * taper),
                            math.radians(46 * k * a * 0.35),
                            math.radians(38 * (1 if k % 2 else -1) * a * taper))
        # shrink with depth so perspective ENLARGES them back toward
        # parity — the chain reads as receding blades, not a widening cone
        base = 0.50 * (1.0 - 0.50 * k / float(LANCE_N))
        sc_ = base * (0.35 + 0.65 * a)
        o.scale = (sc_, sc_, sc_)
    else:
        o.location.x -= u * 0.30                          # she recoils
        o.rotation_euler[1] += math.radians(-u * 3.0)

# ── IDLE FLAP ─────────────────────────────────────────────────────
# Normal wings move as one. Hers move ONE SQUARE AT A TIME, with lag —
# a travelling wave down the chain, so the wing never holds a shape. The
# rest of her breathes underneath it.
def flap(o, i, t):
    if o in SEG or o in BLADE: o.scale = (0.001,0.001,0.001); return
    ph = 2 * math.pi * t
    if '_L_' in o.name or '_R_' in o.name:
        k = plate_index(o)
        lag = k * 0.62                                     # THE LAG
        w = math.sin(ph - lag)
        o.location.z += 0.34 * w
        o.location.x += 0.10 * w * (-1 if '_L_' in o.name else 1)
        o.rotation_euler[1] += math.radians(9.0 * math.sin(ph - lag - 0.5))
    else:
        o.location.z += 0.075 * math.sin(ph - 1.1)         # body rides the beat, late
        pa = JIT[o.name][0]
        o.rotation_euler[1] += math.radians(1.6 * math.sin(ph * 0.7 + pa))

# ── FLINCH ────────────────────────────────────────────────────────
# Registration failure, spiked. Every plate jumps out from the centre
# and comes back — the image is DISTURBED, not the body injured.
def flinch(o, i, t):
    if o in BLADE: o.scale = (0.001,0.001,0.001); return
    if o in SEG: o.scale = (0.001, 0.001, 0.001); return
    d = math.exp(-4.2 * t) * math.sin(2*math.pi*t*3.4)
    ang = JIT[o.name][0]
    o.location.x += math.cos(ang) * d * 0.42
    o.location.z += math.sin(ang) * d * 0.42
    o.rotation_euler[1] += math.radians(d * 11.0)

# ── DISPERSE, rebuilt ─────────────────────────────────────────────
# The radial explosion was Windows Movie Maker. The right idea is already
# in what she IS: she is FLAT, so a plate turned edge-on STOPS EXISTING.
# She does not break apart — she has no other side to show you, so she
# vanishes by trying to show it. Staggered, so she goes out plate by
# plate, and the face is LAST because the face is the last thing to admit
# it was never there.
def disperse(o, i, t):
    if o in BLADE: o.scale = (0.001,0.001,0.001); return
    if o in SEG: o.scale = (0.001, 0.001, 0.001); return
    order = 0.72 if o in FACE else (JIT[o.name][2] - 0.6) * 0.55
    a = max(0.0, min(1.0, (t - order * 0.55) / 0.42))
    if a <= 0.0: return
    e = a ** 0.8
    o.rotation_euler[2] += math.radians(92.0 * e)          # turn EDGE-ON
    o.rotation_euler[1] += math.radians(14.0 * e * (1 if i % 2 else -1))
    o.location.z += 0.55 * e * e                            # and drift up as it goes
    o.location.x += 0.18 * e * math.cos(JIT[o.name][0])

# ── JUDGEMENT ─────────────────────────────────────────────────────
# She sweeps UP to bring it forth and DOWN to drive it home. The blade is
# made of her own plates: they climb, lock into an edge above her, hang
# (that hang IS the dodge window), then fall — INTEGRATED, not eased, so
# it arrives with weight instead of floating down.
BLADE_TOP  = 13.6
BLADE_GAP  = 2.15      # segments must TILE, not leave gaps
BLADE_REST = 0.55          # where the point ends up: ground level

def judgement(o, i, t):
    if o in SEG: o.scale = (0.001, 0.001, 0.001); return
    T_CALL, T_LOCK, T_HANG, T_FALL, T_HIT = 0.22, 0.36, 0.48, 0.58, 0.66

    if o in BLADE:
        k = BLADE.index(o)
        if t < T_CALL * 0.35:
            o.scale = (0.001, 0.001, 0.001); return
        # gather: plates arrive scattered, then converge into an edge
        g = min(1.0, max(0.0, (t - T_CALL*0.35) / (T_LOCK - T_CALL*0.35)))
        g = g ** 0.7
        ang = JIT[o.name][0] if o.name in JIT else k * 1.7
        sx = math.cos(ang) * 3.4 * (1 - g)
        sz = math.sin(ang) * 2.2 * (1 - g)
        # fall: v0=0, z = z0 - 1/2 g t^2, so it ACCELERATES like a mass
        drop = 0.0
        if t > T_HANG:
            u = min(1.0, (t - T_HANG) / (T_FALL - T_HANG + 0.001))
            # Constant chosen so the POINT actually reaches the ground:
            # from BLADE_TOP 13.6 to BLADE_REST 0.55 is a 13.05 drop, and
            # 0.5*9.81*0.62^2 = 1.885, so C = 6.92. At 4.6 it stopped 4.9
            # units short and the sword hung in the air and faded — all
            # wind-up, no landing.
            drop = 0.5 * 9.81 * (u * 0.62) ** 2 * 7.0
        top = BLADE_TOP - drop
        z = max(BLADE_REST + k * BLADE_GAP, top - k * BLADE_GAP)
        o.location = Vector((sx * 0.6, 0.0, z + sz))
        o.rotation_euler = (0.0, math.radians(180 * (1 - g) * (1 if k % 2 else -1)), 0.0)
        w = 0.34 + 1.05 * (k / float(BLADE_N - 1))        # TAPERS TO A POINT
        h = 2.55                                          # tall enough to tile
        o.scale = (w * g, 1.0, h * g)
        if t > T_HIT:                                      # shatter at the base
            e = (t - T_HIT) / (1.0 - T_HIT)
            o.location.z += e * e * 1.2 * k * 0.3
            o.location.x += math.cos(ang) * e * e * 5.0
            o.scale = (w*g*(1-e*0.8), 1.0, h*g*(1-e*0.8))
        return

    # HER: sweep up to call it, drive down to land it
    if t < T_CALL:
        c = (t / T_CALL) ** 0.8
        o.location.z += c * 0.85
        o.rotation_euler[1] += math.radians(c * 7.0 * (1 if i % 2 else -1))
    elif t < T_HANG:
        o.location.z += 0.85
    elif t < T_HIT:
        u = (t - T_HANG) / (T_HIT - T_HANG)
        o.location.z += 0.85 - u * 1.65                    # DRIVES it down
        o.rotation_euler[1] += math.radians(-u * 5.0)
    else:
        e = (t - T_HIT) / (1.0 - T_HIT)
        o.location.z += -0.80 * (1 - e ** 0.55)            # settle back up
        o.location.x += math.sin(e * 22.0) * 0.10 * (1 - e) # ring from the impact

# ── DODGE ─────────────────────────────────────────────────────────
# She cannot sidestep and she cannot turn — she is a billboard. But she
# is FLAT, so she can present ZERO CROSS-SECTION: go edge-on and the
# projectile passes through where she is not. For a few frames she breaks
# the one rule that defines her, which is exactly why it reads as
# impossible rather than as animation. The inverse of flinch: flinch is
# the image DISTURBED, dodge is the image briefly ABSENT.
def dodge(o, i, t):
    if o in SEG or o in BLADE: o.scale = (0.001, 0.001, 0.001); return
    # centre-out lag, so she WIPES out of existence rather than flipping
    lag = min(0.34, abs(o.location.x) * 0.085)
    u = max(0.0, min(1.0, (t - lag) / (0.62 - lag)))
    swing = math.sin(u * math.pi) ** 0.65
    o.rotation_euler[2] += math.radians(88.0 * swing)
    o.location.x += 0.30 * swing * (1 if o.location.x >= 0 else -1)

# ── REGARD ────────────────────────────────────────────────────────
# She has no aggro moment. And since her whole identity is NEVER
# RESOLVING, the most unsettling thing available to her is to snap into
# perfect coherence — every plate registered, the drift stopped, the face
# aligned — hold, and then come apart again. She looks at you by choosing,
# briefly, to be legible.
def regard(o, i, t):
    if o in SEG or o in BLADE: o.scale = (0.001, 0.001, 0.001); return
    if   t < 0.26: k = 1.0 - (t / 0.26) ** 0.45      # chaos -> ALIGNED
    elif t < 0.58: k = 0.0                            # HELD. she is looking.
    else:          k = ((t - 0.58) / 0.42) ** 1.6     # and releases
    pa, pb, amp = JIT[o.name]
    ph = 2 * math.pi * (0.31 + t * 0.4)
    o.rotation_euler[1] += math.radians(3.1 * amp * k * math.sin(ph + pa))
    o.location.x += 0.075 * amp * k * math.sin(ph * 0.7 + pb)
    o.location.z += 0.065 * amp * k * math.cos(ph * 1.3 + pa)
    o.location.z += 0.10 * (1.0 - k) * math.sin(t * math.pi)   # rises as it locks

CLIPS = ([('lance_ext', 66, lance), ('judge_ext', 108, judgement),
          ('dodge_ext', 26, dodge)] if MODE == 'ext' else
         [('lance_fp', 66, lance)] if MODE == 'fp' else
         [('idle', 150, idle), ('flap', 96, flap), ('lance', 66, lance),
          ('flinch', 30, flinch), ('disperse', 96, disperse),
          ('judgement', 108, judgement), ('dodge', 26, dodge),
          ('regard', 54, regard)])

if MODE not in ('fp', 'ext'):
    sc.render.resolution_x = sc.render.resolution_y = 700
for name, n, fn in CLIPS:
    bake(name, n, fn)
    d = os.path.join(OUT, 'anim', name)
    os.makedirs(d, exist_ok=True)
    sc.render.filepath = os.path.join(d, 'f_')
    bpy.ops.render.render(animation=True)
    print('CLIP %s %df' % (name, n))

print('ANIM DONE')
