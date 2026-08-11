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

LW = 0.020                   # line weight. SHE IS LINE ART, NOT SILHOUETTE.

def poly(name, pts, layer=0, lw=None):
    """A shape is its OUTLINE, not its fill. Khaled's drawings are line art
    and the effect depends on seeing THROUGH the overlaps — a filled version
    destroys exactly the quality that makes her unresolvable. Each edge
    becomes a thin quad, which also keeps the very thin triangles honest
    (a centroid-inset outline collapses them)."""
    w = LW if lw is None else lw
    z = Z + layer * DZ
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
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

# ── one flat emissive material, wireframe-ish look comes from the shapes
mat = bpy.data.materials.new('arbelos_line')
mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
em = nt.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (0.02, 0.02, 0.025, 1)
out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(em.outputs[0], out.inputs[0])
for o in parts: o.data.materials.append(mat)

bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
arb = bpy.context.active_object
arb.name = 'Arbelos_Phase1'

# ── render: front, plus three yaws to prove the billboard case ────
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.film_transparent = False
w = bpy.data.worlds.new('W'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sc.world = w
sc.render.resolution_x = sc.render.resolution_y = 900

cd = bpy.data.cameras.new('C'); cd.type = 'ORTHO'; cd.ortho_scale = 9.6
cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector((0, 0, 3.1))
for nm, yaw in (('front', 0), ('yaw20', 20), ('yaw45', 45), ('yaw80', 80)):
    a = math.radians(yaw)
    cam.location = tgt + Vector((math.sin(a)*10, -math.cos(a)*10, 0))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, 'arbelos_%s.png' % nm)
    bpy.ops.render.render(write_still=True)

bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'arbelos_phase1.glb'),
                          export_format='GLB', use_selection=False)
print('PARTS %d  ->  %s' % (len(parts), OUT))
