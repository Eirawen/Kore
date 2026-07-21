# Probe the earth fist thumb: render the right hand at the CHAMBER-roll
# orientation (the raking palm-side view where the thumb-hook artifact
# shows) with several thumb curl triples, one still each.
#   blender --background cgtrader_hand_wristed.blend --python probe_fist_thumb.py
import bpy  # noqa: F401

_CASTS = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\animate_casts.py'
_code = open(_CASTS).read()
exec(_code[:_code.rfind('def main')])

VARIANTS = {
    'gripT_45_55_32':  [45, 55, 32],
    'mid_55_60_40':    [55, 60, 40],
    'firm_62_68_45':   [62, 68, 45],
    'hard_75_80_55':   [75, 80, 55],
}
FINGERS = [95, 105, 78]

# axis hunt: which root-bone euler channel ADDUCTS the thumb across the
# palm (X-curl alone only flexes it in its own out-jutting plane)?
AXIS_VARIANTS = {  # name: (thumb_x_triple, bone001_extra_euler_deg (y, z))
    'y+35': ([55, 60, 40], (35, 0)),
    'y-35': ([55, 60, 40], (-35, 0)),
    'z+35': ([55, 60, 40], (0, 35)),
    'z-35': ([55, 60, 40], (0, -35)),
}

strip_scene()
stage_hands()
apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
setup_camera_lights_world()

right = bpy.data.objects[RIGHT_ARM]
left = bpy.data.objects[LEFT_ARM]
clear_anim(left)
# park the left hand out of frame
left.location = (-4.5, 0.0, -4.0)

scene = bpy.context.scene
for name, thumb in VARIANTS.items():
    clear_anim(right)
    POSES['probe'] = {'f': FINGERS, 'thumb': thumb}
    # mid-roll chamber view (the artifact angle) and the windup-top view
    for tag, loc, rot in (
            ('chamber', (2.25, -0.5, -0.52), (2, 5, 130)),
            ('roll',    (2.35, -0.85, -0.5), (-15, 0, 91))):
        key_obj(right, 1, loc, rot)
        key_pose(right, 1, 'probe')
        scene.frame_set(1)
        scene.render.filepath = r'C:\tmp\fistprobe_%s_%s.png' % (tag, name)
        bpy.ops.render.render(write_still=True)
        print('rendered', scene.render.filepath)

for name, (thumb, (ey, ez)) in AXIS_VARIANTS.items():
    clear_anim(right)
    POSES['probe'] = {'f': FINGERS, 'thumb': thumb}
    key_obj(right, 1, (2.35, -0.85, -0.5), (-15, 0, 91))
    key_pose(right, 1, 'probe')
    pb = right.pose.bones['Bone.001']
    pb.rotation_euler.y = math.radians(ey)
    pb.rotation_euler.z = math.radians(ez)
    pb.keyframe_insert('rotation_euler', frame=1)
    scene.frame_set(1)
    scene.render.filepath = r'C:\tmp\fistaxis_%s.png' % name
    bpy.ops.render.render(write_still=True)
    print('rendered', scene.render.filepath)
