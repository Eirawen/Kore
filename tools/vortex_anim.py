"""Two clips: (1) the vortex SPINNING at full water — does it read as a
whirlpool in motion? (2) the DRAIN, water 1.0 -> 0.08 while spinning — the
death curve as the player buckets her out. Extremes pushed per my own note
(SQUAT 0.30->0.46, DROOP 0.42->0.66, + a slump so she sags as she empties)."""
import bpy, math, sys
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=o.data
rest=[v.co.copy() for v in me.vertices]
zs=[c.z for c in rest]; Z0,Z1=min(zs),max(zs)
CORE_R,EDGE_R=0.085,0.26
SF=[max(0.0,min(1.0,(math.hypot(c.x,c.y)-CORE_R)/(EDGE_R-CORE_R))) for c in rest]
R0=[math.hypot(c.x,c.y) for c in rest]
TH0=[math.atan2(c.y,c.x) for c in rest]
H0=[(c.z-Z0)/(Z1-Z0) for c in rest]
TWIST=3.10; FLARE=0.55; DROOP=0.66; SQUAT=0.46; SLUMP=0.10
# --- TWO MOTION ZONES -------------------------------------------------
# Below the waist she is a VORTEX (rotational, flaring). Above it she only
# DRIFTS (a gentle lateral current) so the figure stays readable: the water
# rages, the woman above it is the still eye. Her waist (h=0.35) is already
# the narrowest point of the column, so it's the natural seam.
VTX_LO, VTX_HI = 0.30, 0.60      # full vortex below LO, none above HI
DRIFT_AMP = 0.028                # lateral drift of the upper strands
def smooth(e0,e1,x):
    t=max(0.0,min(1.0,(x-e0)/(e1-e0))); return t*t*(3-2*t)
VMASK=[1.0-smooth(VTX_LO,VTX_HI,h) for h in H0]      # vortex authority
DMASK=[smooth(VTX_LO,VTX_HI,h) for h in H0]          # drift authority

# --- CHURN vs SPIN (Khaled's catch) ------------------------------------
# The bug: rotation was scaled by the strand factor, which varies with
# RADIUS, so different parts of a leg rotated by different amounts and the
# difference ACCUMULATED with phase. That's shear growing over time — the
# loop was a dissolve-and-reform cycle, not a spin. Her legs came apart and
# grew back forever.
#
# Fix: split them.
#   CHURN  — fixed shear. Creates the vortex shape. She is ALWAYS in it.
#   SPIN   — uniform with height, so it turns the churned shape and adds no
#            new shear. Spins forever, never dissolves further.
#   WOBBLE — small per-vertex variation so it churns instead of rotating
#            like a solid disc.
# Bonus: CHURN scales with `water`, so draining her UN-churns her. At full
# power: a raging vortex with no legs. Drained: just a woman in a puddle.
BASE_CHURN=4.60
WOBBLE=0.30
SEED=[math.sin(c.x*37.1+c.y*61.7+c.z*23.3)*math.pi for c in rest]
def apply(water, phase):
    for i,c in enumerate(rest):
        s=SF[i]
        vm=VMASK[i]
        churn=(BASE_CHURN*s + TWIST*H0[i]*s)*vm*water      # FIXED shape
        spin=phase*vm*water                                 # uniform: no new shear
        wob=WOBBLE*math.sin(phase*1.7+SEED[i])*s*vm*water   # chaotic variation
        th=TH0[i]+churn+spin+wob
        rr=R0[i]*(1.0+FLARE*water*s*vm)
        zz=c.z-DROOP*(1.0-water)*s*(0.35+0.65*H0[i])
        zz=Z0+(zz-Z0)*(1.0-SQUAT*(1.0-water))
        x=rr*math.cos(th); y=rr*math.sin(th)
        # upper strands drift in a current instead of spinning
        dr=DRIFT_AMP*s*DMASK[i]*water
        x+=dr*math.sin(phase*0.55+H0[i]*4.1)
        y+=dr*math.cos(phase*0.47+H0[i]*3.3)*0.6
        # slump: as she empties the whole column leans (losing its spine)
        x+=SLUMP*(1.0-water)*H0[i]*H0[i]
        me.vertices[i].co=Vector((x,y,zz))
    me.update()
sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.06,.08,.12,1); sc.world=w
mat=bpy.data.materials.new('aqua'); mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value=(0.30,0.68,1.0,1); bs.inputs['Roughness'].default_value=0.10
try: bs.inputs['Transmission Weight'].default_value=0.25
except Exception: pass
me.materials.clear(); me.materials.append(mat)
ctr=Vector((0,0,0))
for nm,off,e in (('K',Vector((-1,-1.2,1.0)),3.6),('F',Vector((1.3,-.9,.3)),1.7),('B',Vector((0,1.4,.6)),1.5)):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e
    ob=bpy.data.objects.new(nm,d); ob.location=ctr+off*2
    ob.rotation_euler=(ctr-ob.location).to_track_quat('-Z','Y').to_euler(); sc.collection.objects.link(ob)
sc.render.resolution_x,sc.render.resolution_y=340,480
cd=bpy.data.cameras.new('C'); cd.lens=45
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=ctr+Vector((0.25,-1,0.05)).normalized()*1.85
cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
mode=sys.argv[-1]
if mode=='spin':
    N=90
    for f in range(N):
        apply(1.0, 2*math.pi*f/N)
        sc.render.filepath=r'C:\tmp\spin_%03d.png'%f
        bpy.ops.render.render(write_still=True)
    print('SPIN %d frames'%N)
else:
    N=150
    for f in range(N):
        t=f/(N-1)
        water=1.0-0.92*(t*t*(3-2*t))          # smoothstep drain
        apply(water, 2*math.pi*2.2*t*(0.35+0.65*water))   # spin SLOWS as she drains
        sc.render.filepath=r'C:\tmp\drain_%03d.png'%f
        bpy.ops.render.render(write_still=True)
    print('DRAIN %d frames'%N)
