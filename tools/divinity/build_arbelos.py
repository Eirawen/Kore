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
        bm.faces.new(vs)
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
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.film_transparent = True
try:
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
except Exception: pass
sc.render.resolution_x = sc.render.resolution_y = 1400
cd = bpy.data.cameras.new('C'); cd.type = 'ORTHO'; cd.ortho_scale = 9.6
cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector((0, 0, 3.1))
cam.location = tgt + Vector((0, -10, 0))
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()

MODE = 'still'
try:
    with open(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\divinity\.arbcfg') as fh:
        MODE = fh.read().strip() or 'still'
except Exception: pass

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
# ANIMATION — she has NO SKELETON, so the PRIMITIVE is the animatable
# unit. Nineteen independent 2D transforms; the vocabulary is entirely
# what plates can do to each other: drift, gather, stream, scatter.
# ══════════════════════════════════════════════════════════════════
import random
ALL = [o for o in bpy.data.objects if o.type == 'MESH']

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

# ── LANCE (gomu gomu) ─────────────────────────────────────────────
# NOT a stretch. The wing's plates FIRE OFF HER ONE AFTER ANOTHER along
# one line — a stack of cards launched in sequence, so the wing TRAVELS
# as a chain. gather -> hold -> stream -> hang -> snap back, with the
# rest of her recoiling the other way.
def make_lance(side, reach=7.2):
    chain = wing(side)
    sgn = 1.0 if side == 'R' else -1.0
    def f(o, i, t):
        if o in chain:
            n = plate_index(o)
            lead = 0.055 * (3 - n) if side == 'R' else 0.055 * n
            u = 0.0
            if   t < 0.20: u = -0.09 * (t/0.20)                    # gather IN
            elif t < 0.28: u = -0.09                               # HOLD
            elif t < 0.58:
                a = max(0.0, min(1.0, ((t-0.28)/0.30) - lead*2.2))
                u = -0.09 + (a**1.8) * 1.09                        # STREAM
            elif t < 0.72: u = 1.0                                 # hang
            else:
                a = (t-0.72)/0.28
                u = 1.0 - a**0.6 * 1.06                            # snap + overshoot
            o.location.x += sgn * u * reach
            o.rotation_euler[1] += math.radians(sgn * u * 26.0)
            sq = 1.0 + 0.55 * max(0.0, u)
            o.scale = (sq, 1.0, 1.0 - 0.16 * max(0.0, u))
        else:
            r = 0.0
            if 0.28 <= t < 0.62: r = math.sin((t-0.28)/0.34*math.pi)
            o.location.x -= sgn * r * 0.42                          # recoil
            o.rotation_euler[1] += math.radians(-sgn * r * 3.5)
    return f

# ── FLINCH ────────────────────────────────────────────────────────
# Registration failure, spiked. Every plate jumps out from the centre
# and comes back — the image is DISTURBED, not the body injured.
def flinch(o, i, t):
    d = math.exp(-4.2 * t) * math.sin(2*math.pi*t*3.4)
    ang = JIT[o.name][0]
    o.location.x += math.cos(ang) * d * 0.42
    o.location.z += math.sin(ang) * d * 0.42
    o.rotation_euler[1] += math.radians(d * 11.0)

# ── DISPERSE ──────────────────────────────────────────────────────
# She does not break, because she was never assembled. She stops being
# ARRANGED: every plate leaves along its own vector and keeps going.
def disperse(o, i, t):
    ang = JIT[o.name][0]; spd = 0.7 + JIT[o.name][2]
    e = t**1.7
    o.location.x += math.cos(ang) * e * 6.0 * spd
    o.location.z += math.sin(ang) * e * 6.0 * spd + e * 1.4
    o.rotation_euler[1] += math.radians(e * 190 * (1 if i % 2 else -1))
    k = max(0.02, 1.0 - e * 0.85)
    o.scale = (k, k, k)

CLIPS = [('idle', 150, idle), ('lance_R', 60, make_lance('R')),
         ('lance_L', 60, make_lance('L')), ('flinch', 30, flinch),
         ('disperse', 90, disperse)]

sc.render.resolution_x = sc.render.resolution_y = 700
for name, n, fn in CLIPS:
    bake(name, n, fn)
    d = os.path.join(OUT, 'anim', name)
    os.makedirs(d, exist_ok=True)
    sc.render.filepath = os.path.join(d, 'f_')
    bpy.ops.render.render(animation=True)
    print('CLIP %s %df' % (name, n))

print('ANIM DONE')
