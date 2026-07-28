"""Water elemental clips. Component tracks, aimed bones, integrated physics.
Author with codex/humanoid-animation.md's laws:
  - aim bones at targets, never hand-author eulers
  - every component on its own clock, with a REASON
  - hesitation is deceleration, never cessation
  - AUTO_CLAMPED only on first/last key of an fcurve
"""
import bpy, math, sys, json
from mathutils import Vector, Quaternion
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
ao=bpy.data.objects['WaterRig']; o=bpy.data.objects['WaterBody']
sc=bpy.context.scene
bpy.context.view_layer.objects.active=ao
bpy.ops.object.mode_set(mode='POSE')
mw=ao.matrix_world
COL=['col%d'%i for i in range(7)]
HAIR=['hair%d'%i for i in range(4)]
ARM=['arm0','arm1','arm_hand']
for pb in ao.pose.bones: pb.rotation_mode='QUATERNION'

def upd(): bpy.context.view_layer.update()
def clear():
    for pb in ao.pose.bones:
        pb.rotation_quaternion=Quaternion(); pb.location=(0,0,0)
    ao.location=(0,0,0); upd()

def aim(name, want_world):
    """Point a bone along a world direction using its LIVE matrix, so posed
    ancestors are respected (codex law 2: M0^-1 . D . M0)."""
    pb=ao.pose.bones[name]
    R=mw.to_3x3(); Ri=R.inverted()
    pb.rotation_quaternion=Quaternion(); upd()
    cur=(Ri@((mw@pb.tail)-(mw@pb.head))).normalized()
    des=(Ri@Vector(want_world)).normalized()
    M0=pb.matrix.to_quaternion()
    pb.rotation_quaternion=M0.inverted()@cur.rotation_difference(des)@M0
    upd()

def bend(name, axis, deg):
    pb=ao.pose.bones[name]
    m=pb.bone.matrix_local.to_3x3().inverted()
    a=(m@Vector(axis)).normalized()
    pb.rotation_quaternion=pb.rotation_quaternion@Quaternion(a, math.radians(deg))
    upd()

def slosh(lean, orbit, c, t):
    """THE BASE IS NOT A STAND.

    Khaled: "she reminds me of a figurine on a stand, that bobbles around."
    Exactly right, and it was structural: every bend was weighted
    0.25+0.75*height, so the top swung while col0 (which carries the POOL)
    barely moved. Fixed stand, wobbling figure — a bobblehead.

    The conceptual error: I was animating a woman STANDING ON a base. The
    pool is not furniture, it is the heaviest part of her BODY. In water the
    mass leads from the BOTTOM — a wave is driven by what is underneath, not
    by the tip. So the base must slosh: shift with the motion, spread under
    load, and lag behind the direction change.
    """
    # the whole mass SHIFTS — water does not pivot about a fixed foot
    ao.location.x += -0.055*math.radians(orbit)*14.0*c
    ao.location.y +=  0.045*math.radians(lean)*10.0*c
    # and the lowest segments carry REAL motion, lagged behind the top
    lag = math.sin(t*math.tau - 0.9)
    bend('col0',(1,0,0), lean*0.55 + 3.2*lag*c)
    bend('col0',(0,1,0), orbit*0.65 - 2.6*lag*c)
    bend('col1',(1,0,0), lean*0.70 + 2.2*lag*c)
    bend('col1',(0,1,0), orbit*0.78 - 1.8*lag*c)

def key(names, f):
    for nm in names:
        ao.pose.bones[nm].keyframe_insert('rotation_quaternion', frame=f)

def key_root(f):
    ao.keyframe_insert('location', frame=f)

def smooth_handles(act):
    """AUTO_CLAMPED on EVERY key flattens velocity at each key -> a chain of
    stop-starts. Clamp only the ends (codex smoothness law 3)."""
    try: curves=act.fcurves
    except Exception:
        curves=[fc for l in act.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
    for fc in curves:
        kps=fc.keyframe_points
        for i,kp in enumerate(kps):
            kp.interpolation='BEZIER'
            e = (i==0 or i==len(kps)-1)
            kp.handle_left_type=kp.handle_right_type=('AUTO_CLAMPED' if e else 'AUTO')

def new_action(name):
    # GOTCHA: actions.new() does NOT overwrite. A same-named action saved
    # with use_fake_user survives, so every rebuild silently produced
    # 'waveform.001', '.002', ... and all my fixes landed in orphaned
    # duplicates while the ORIGINAL kept rendering. Purge first.
    for old in [x for x in bpy.data.actions if x.name==name or x.name.startswith(name+'.')]:
        old.use_fake_user=False
        bpy.data.actions.remove(old)
    a=bpy.data.actions.new(name)
    ao.animation_data_create(); ao.animation_data.action=a
    return a

FRONT=Vector((0,-1,0))      # she faces -Y; attacks go downrange
UP=Vector((0,0,1))
events={}

# ══════════════════════════════════════════════════════════════════
# 1. WAVE_RISE — arm gathers LOW, sweeps up, the wave follows its arc
# ══════════════════════════════════════════════════════════════════
def clip_wave_rise():
    a=new_action('atk_wave_rise'); clear()
    # component clocks: the GATHER is the anticipation; the column follows
    # the arm a beat late because a body follows its own limb.
    # THE BODY SELLS IT, THE ARM AIMS IT. Her silhouette is too busy for an
    # arm gesture to telegraph on its own (proved by v1 of this clip: all a
    # viewer read was a lean and some hair). So the COLUMN commits hard —
    # a deep rear-back then a surge — and the arm rides on top as the
    # precise origin the VFX spawns from.
    KEYS=[
        # f,   arm dir,                    col lean(deg), hair lag
        (0,   Vector(( 0.75,-0.55,-0.10)),   0,   0),
        (16,  Vector(( 0.45,-0.20,-0.86)), -26,   8),   # COIL: deep rear-back
        (26,  Vector(( 0.42,-0.26,-0.90)), -32,  13),   # settle into the coil
        (36,  Vector(( 0.60,-0.72, 0.30)),  10, -10),   # uncoil begins
        (43,  Vector(( 0.34,-0.55, 0.95)),  40, -26),   # SURGE — wave leaves
        (50,  Vector(( 0.32,-0.52, 0.97)),  34, -20),   # peak, held
        (66,  Vector(( 0.62,-0.58, 0.18)),   6,  -4),   # recover
        (84,  Vector(( 0.75,-0.55,-0.10)),   0,   0),
    ]
    for f,ad,lean,hl in KEYS:
        clear()
        aim('arm0', ad); aim('arm1', ad*0.9+UP*0.25); aim('arm_hand', ad*0.7+UP*0.5)
        for i,nm in enumerate(COL):
            bend(nm,(0,1,0), lean*(0.60+0.40*i/6.0))
        for i,nm in enumerate(HAIR):
            bend(nm,(0,1,0), hl*(0.4+0.6*i/3.0))
        slosh(lean, 0.0, 1.0, f/84.0)
        key(ARM+COL+HAIR, f); key_root(f)
    smooth_handles(a)
    events['atk_wave_rise']={'duration_f':84,'fps':60,
        'events':{'gather':22,'release':42,'impact_window':[42,58]},
        'vfx_todo':'rising wave travels downrange along the arm arc from f42'}
    return a

# ══════════════════════════════════════════════════════════════════
# 2. SCOOP_REACT — NOT a flinch. Water has no nerves: it COLLAPSES
#    toward the void and redistributes. A wave travels up her column.
# ══════════════════════════════════════════════════════════════════
def clip_scoop_react():
    a=new_action('react_scoop'); clear()
    # the wave travels UP her column, each segment peaking later than the
    # one below it — that propagation IS the read
    N=54
    for f in range(0,N+1,3):
        clear()
        t=f/float(N)
        for i,nm in enumerate(COL):
            phase=t*3.4 - i*0.42                    # travels upward
            amp=math.exp(-max(phase,0.0)*1.1)*math.sin(max(phase,0.0)*3.2)
            bend(nm,(1,0,0), -11.0*amp)             # sag toward the scoop
            bend(nm,(0,1,0),  -5.5*amp)
        for i,nm in enumerate(HAIR):
            phase=t*3.4 - (7+i)*0.42
            amp=math.exp(-max(phase,0.0)*1.1)*math.sin(max(phase,0.0)*3.2)
            bend(nm,(1,0,0), -16.0*amp)             # loose water whips hardest
        # the arm goes slack for a moment — she does not brace, she sags
        slack=math.exp(-t*3.0)*math.sin(t*7.0)
        bend('arm0',(0,1,0), -9.0*slack)
        bend('arm1',(0,1,0), -6.0*slack)
        key(ARM+COL+HAIR, f)
    smooth_handles(a)
    events['react_scoop']={'duration_f':N,'fps':60,
        'events':{'impact':0,'wave_crest_top':22},
        'uWater_step':'game lowers uWater at f0; the wave is the redistribution',
        'note':'no flinch — collapse toward the void, then re-cohere smaller'}
    return a

# ══════════════════════════════════════════════════════════════════
# 3. WAVEFORM — lose form, surge, re-form with overshoot.
#    The visual contract for INVULNERABLE is: no woman, no target.
# ══════════════════════════════════════════════════════════════════
def clip_waveform():
    """WAVEFORM v2.

    v1 read as a SNOWMOBILE (Khaled) — a hunched figure travelling, not a
    wave. Diagnosis: I ROTATED her. Rotation preserves proportion, so a
    humanoid stays humanoid however you bend it. Three tells survived: the
    HEAD was still readable at the front (a wave has no head, and the moment
    a brain finds one it reads 'creature'), she stayed TALL (a wave is low
    and wide), and limbs stuck out like handlebars.

    A dissolve must DESTROY THE PROPORTIONS. That is the slime lesson: you
    do not rig a liquid, you deform it — squash and stretch. So the object
    scale IS the dissolve:
        height  -> 0.28   (a wave is LOW)
        travel  -> 2.55   (a wave is LONG)
        width   -> 1.18   (and it spreads)
    plus the head buried into the mass and a crest riding the front.
    """
    a=new_action('waveform'); clear()
    N=96
    DIST=2.6
    SQ_Z, ST_Y, ST_X = 0.28, 2.55, 1.18
    BASE_Z = -0.5                     # her lowest vert in object space
    dissolve=[]
    for f in range(0,N+1,2):
        clear()
        t=f/float(N)
        # LUNGE: she commits to the direction BEFORE she loses form. v2 just
        # folded, with no moment of decision, and the collapse frame read as
        # leaning BACK. Anticipation must point where she is going.
        lunge = math.sin(min(t/0.12,1.0)*math.pi) if t<0.20 else 0.0
        if t<0.12:   d=t/0.12*0.0;             crouch=t/0.12
        elif t<0.26: d=(t-0.12)/0.14;          crouch=1.0
        elif t<0.62: d=1.0;                    crouch=1.0
        elif t<0.88: d=1.0-(t-0.62)/0.26;      crouch=1.0-(t-0.62)/0.26
        else:        d=0.0;                    crouch=0.0
        d=max(0.0,min(1.0,d))
        dissolve.append((f, round(d,3)))

        # ── THE DISSOLVE IS A SCALE, NOT A POSE ──────────────────
        sz = 1.0 + (SQ_Z-1.0)*d
        sy = 1.0 + (ST_Y-1.0)*d
        sx = 1.0 + (ST_X-1.0)*d
        ao.scale=(sx, sy, sz)
        # squashing about the origin would lift her off the floor; drop her
        # so her base stays planted
        drop = BASE_Z*(1.0-sz)

        if t<0.26: s=0.0
        elif t<0.62: u=(t-0.26)/0.36; s=u*u*(3-2*u)
        else: s=1.0
        ao.location=(0.0, -DIST*s, drop)

        # ── BURY THE HEAD ────────────────────────────────────────
        # The single strongest anti-wave cue is a readable head leading the
        # mass. Fold the upper column hard so it sinks INTO the body.
        # A BREAKING WAVE'S CREST IS AT THE LEADING EDGE — high in front,
        # tapering behind. v2 had it backwards (high at the tail), which is
        # exactly what reads as "leaning back". The collapse lays her out
        # head-first, so her TOP segments are the front: they must curl UP
        # into a crest while the mid-body stays flat and the tail thins.
        for i,nm in enumerate(COL):
            up = i/6.0
            bury  = -70.0*d*up*up                    # fold her flat...
            crest =  46.0*d*max(0.0, (up-0.62)/0.38) # ...then curl the FRONT up
            und   = 6.0*d*math.sin(t*20.0 - up*2.4)
            bend(nm,(1,0,0), -20.0*crouch*(0.25+0.75*up) + bury + crest + und
                             - 30.0*lunge*(0.2+0.8*up))   # dive forward first
        for i,nm in enumerate(HAIR):
            bend(nm,(1,0,0), -34.0*crouch - 30.0*d
                             + 8.0*d*math.sin(t*20.0-(7+i)*0.6))
        # the arm reaches AHEAD during the lunge — it points where she goes
        if lunge>0.01: bend('arm0',(1,0,0), -34.0*lunge)
        # arms fold flat into the mass, then get thrown out on the reform
        if t<0.62:
            bend('arm0',(0,1,0), -70.0*d); bend('arm1',(0,1,0), -60.0*d)
            bend('arm0',(1,0,0), -40.0*d)
        else:
            u=(t-0.62)/0.38; over=math.sin(u*math.pi)
            bend('arm0',(0,1,0), -70.0*d + 30.0*over)
            bend('arm1',(0,1,0), -60.0*d + 22.0*over)
        key(ARM+COL+HAIR, f); key_root(f)
        _r=ao.keyframe_insert('scale', frame=f)

    smooth_handles(a)
    if ao.animation_data.action: smooth_handles(ao.animation_data.action)
    events['waveform']={'duration_f':N,'fps':60,'travel_m':DIST,
        'events':{'dissolve_start':12,'formless':25,'reform_start':60,'landed':85},
        'uDissolve_envelope':dissolve,
        'scale_at_peak':{'x':ST_X,'y':ST_Y,'z':SQ_Z},
        'note':'invulnerable while formless — no readable figure IS the contract',
        'vfx_todo':('THE MESH ONLY GETS YOU TO "low fast formless mass". '
                    'Everything that reads as WATER is the layer on top: '
                    'crest spray along the leading edge, a foam sheet trailing '
                    'the tail, churn where it meets the floor, and a splash '
                    'ring on reform. Dedicated VFX session.'),
        'anticipation':'forward LUNGE at f0-12 before form is lost'}
    return a

mode=sys.argv[-1]
made=[]
for fn,nm in ((clip_wave_rise,'atk_wave_rise'),(clip_scoop_react,'react_scoop'),(clip_waveform,'waveform')):
    act=fn(); act.use_fake_user=True; made.append((nm,act.name))
    print('CLIP %-16s frames=%d'%(nm, int(act.frame_range[1])))
with open(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\assets\water_events.json','w') as fh: json.dump(events,fh,indent=1)
bpy.ops.wm.save_as_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
print('SAVED %d clips'%len(made))

# ══════════════════════════════════════════════════════════════════
# 4/5. TORRENTS — the CIRCLE is the telegraph. Overhead = from the
#      ceiling; traced on the floor = from beneath. Mirror images, so a
#      player who learns one reads the other instantly.
# ══════════════════════════════════════════════════════════════════
def clip_torrent(low):
    """The torrents, v2.

    v1's floor version read as "a model that's falling over" (Khaled) —
    because a humanoid bending 30 degrees forward MEANS toppling; that is
    what a body doing that signifies. Same family as the snowmobile: I posed
    a person instead of behaving like water.

    SHE IS WATER. She does not BEND DOWN to reach the floor, she SINKS —
    height collapses, base spreads, and one arm traces a circle on the
    stone. And that makes the pair properly mirrored, in the squash-stretch
    vocabulary that fixed waveform:

        FLOOR   : sink and spread (z 0.55, xy 1.30)
        CEILING : rise and narrow  (z 1.35, xy 0.88)

    The CIRCLE is the telegraph and the whole upper body orbits with the
    arm, because an arm circling inside that silhouette is invisible.
    """
    name='atk_torrent_floor' if low else 'atk_torrent_ceiling'
    a=new_action(name); clear()
    N=108
    SZ, SXY = (0.55, 1.30) if low else (1.35, 0.88)
    BASE_Z=-0.5
    for f in range(0,N+1,3):
        clear(); t=f/float(N)
        if t<0.22:      ph,u='raise',   t/0.22
        elif t<0.72:    ph,u='circle',  (t-0.22)/0.50
        elif t<0.80:    ph,u='snap',    (t-0.72)/0.08
        else:           ph,u='recover', (t-0.80)/0.20
        # commit envelope: how far into the sink/rise she is
        if ph=='raise':      c=u*u*(3-2*u)
        elif ph=='circle':   c=1.0
        elif ph=='snap':     c=1.0
        else:                c=1.0-u*u*(3-2*u)

        sz  = 1.0+(SZ-1.0)*c
        sxy = 1.0+(SXY-1.0)*c
        ao.scale=(sxy, sxy, sz)
        ao.location=(0.0, 0.0, BASE_Z*(1.0-sz))

        base=Vector((0.35,-0.30, -0.80 if low else 0.92)).normalized()
        # a gentle settle, NOT a topple — the sink does the work now
        stoop=(-9.0 if low else 7.0)
        orbit=0.0
        if ph=='raise':
            k=u*u*(3-2*u); d=Vector((0.75,-0.55,-0.10)).lerp(base,k); lean=stoop*k
        elif ph=='circle':
            ang=u*2.0*math.tau; r=0.42
            d=(base+Vector((math.cos(ang)*r, math.sin(ang)*r*0.6, 0))).normalized()
            lean=stoop+9.0*math.sin(ang)
            orbit=13.0*math.cos(ang)      # the telegraph, felt through the body
        elif ph=='snap':
            d=Vector((0.30,-0.42,-1.0 if low else 1.0)).normalized()
            lean=stoop+(-14.0 if low else 14.0)*u
        else:
            k=u*u*(3-2*u); d=base.lerp(Vector((0.75,-0.55,-0.10)),k); lean=stoop*(1-k)

        aim('arm0',d); aim('arm1',d); aim('arm_hand',d)
        # weight now runs 0.55 -> 1.0 instead of 0.25 -> 1.0: the base is
        # part of her body, not a plinth she stands on
        for i,nm in enumerate(COL):
            w=0.55+0.45*i/6.0
            bend(nm,(1,0,0), lean*w)
            bend(nm,(0,1,0), orbit*w)
        for i,nm in enumerate(HAIR):
            bend(nm,(1,0,0), -lean*0.5); bend(nm,(0,1,0), -orbit*0.7)
        slosh(lean, orbit, c, t)
        key(ARM+COL+HAIR, f); key_root(f)
        ao.keyframe_insert('scale', frame=f)
    smooth_handles(a)
    events[name]={'duration_f':N,'fps':60,
        'events':{'circle_start':24,'circle_end':78,'snap':82,'impact_window':[86,100]},
        'scale_at_peak':{'xy':SXY,'z':SZ},
        'telegraph':'the CIRCLE is the tell; its speed tells the player how long they have',
        'silhouette':('SINKS and spreads — a low broad pool tracing the floor' if low
                      else 'RISES and narrows — a tall column reaching the ceiling'),
        'vfx_todo':('torrent erupts from BENEATH the target' if low
                    else 'torrent falls from the CEILING onto the target')}
    return a

# ══════════════════════════════════════════════════════════════════
# 6. LANCE — her quick poke. No gather, no arc. Deliberately the
#    opposite of the big ones: its shortness makes them feel big.
# ══════════════════════════════════════════════════════════════════
def clip_lance():
    a=new_action('atk_lance'); clear()
    KEYS=[(0,Vector((0.75,-0.55,-0.10)),0),
          (7,Vector((0.85,-0.20,0.05)),-7),      # tiny cock back
          (13,Vector((0.28,-0.95,0.02)),9),      # JAB straight downrange
          (19,Vector((0.26,-0.97,0.01)),7),      # held — the lance flies
          (30,Vector((0.75,-0.55,-0.10)),0)]
    for f,d,lean in KEYS:
        clear()
        aim('arm0',d); aim('arm1',d); aim('arm_hand',d)
        for i,nm in enumerate(COL): bend(nm,(1,0,0), lean*(0.3+0.7*i/6.0))
        for i,nm in enumerate(HAIR): bend(nm,(1,0,0), -lean*0.7)
        key(ARM+COL+HAIR,f)
    smooth_handles(a)
    events['atk_lance']={'duration_f':30,'fps':60,
        'events':{'release':13,'impact_window':[13,22]},
        'vfx_todo':'straight water lance from the hand, hitscan-fast'}
    return a

# ══════════════════════════════════════════════════════════════════
# 7. GLIDE — no legs, so no gait, no plants, no IK. What sells liquid
#    is LAG: base leads, torso trails, head trails more, hair furthest.
# ══════════════════════════════════════════════════════════════════
def clip_glide():
    a=new_action('glide'); clear()
    N=60
    for f in range(0,N+1,3):
        clear(); t=f/float(N)
        ph=t*math.tau
        for i,nm in enumerate(COL):
            lag=i*0.30                            # each segment trails the one below
            bend(nm,(1,0,0), -6.5*(i/6.0) + 2.6*math.sin(ph-lag))
            bend(nm,(0,1,0),  1.8*math.sin(ph*0.5-lag))
        for i,nm in enumerate(HAIR):
            lag=(7+i)*0.30
            bend(nm,(1,0,0), -9.0 + 4.2*math.sin(ph-lag))
        bend('arm0',(0,1,0), 3.0*math.sin(ph-2.1))
        bend('arm1',(0,1,0), 2.2*math.sin(ph-2.5))
        key(ARM+COL+HAIR,f)
    smooth_handles(a)
    events['glide']={'duration_f':N,'fps':60,'loop':True,
        "note":"lag cascade: base leads, head trails, hair furthest. Root translation is the GAME's job."}
    return a

for fn,nm in ((lambda: clip_torrent(False),'atk_torrent_ceiling'),
              (lambda: clip_torrent(True),'atk_torrent_floor'),
              (clip_lance,'atk_lance'), (clip_glide,'glide')):
    act=fn(); act.use_fake_user=True
    print('CLIP %-20s frames=%d'%(nm,int(act.frame_range[1])))
with open(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\assets\water_events.json','w') as fh:
    json.dump(events,fh,indent=1)
bpy.ops.wm.save_as_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
print('SAVED ALL')
