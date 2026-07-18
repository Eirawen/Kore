"""Contact sheet: sword-in-fist at a lattice of authored eulers, FP camera.
Renders C:\tmp\gripor_NN.png + manifest with the euler per frame.
"""
import bpy
import sys
import math
import json
sys.path.append(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools')

# reuse the harness by exec-ing animate_sword up to (not including) main()
SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\animate_sword.py'
code = open(SRC).read()
code = code[:code.rfind('def main')]
exec(code)

CANDS = [
    (0,   55, -90), (0,   55, 90),
    (90,  55, -90), (90,  55, 90),
    (180, 55, -90), (180, 55, 90),
    (-90, 55, -90), (-90, 55, 90),
    (0,  -55, -90), (180, -55, 90),
    (90,   0,  0),  (-90,  0,  0),
]
LOC = (2.05, 0.3, -0.6)

strip_scene()
stage_hands()
apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
setup_camera_lights_world()
attach_sword()

right = bpy.data.objects[RIGHT_ARM]
left = bpy.data.objects[LEFT_ARM]
clear_anim(left)
key_obj(left, 1, (-2.05, 0.0, -0.7), (14, -9, -172))
key_pose(left, 1, 'idle')

scene = bpy.context.scene
manifest = []
for i, rot in enumerate(CANDS):
    clear_anim(right)
    key_obj(right, 1, LOC, rot)
    key_pose(right, 1, 'grip')
    scene.frame_set(1)
    path = OUT_DIR + '\\gripor_%02d.png' % (i + 1)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({'index': i + 1, 'frame': i + 1, 'time': 0.0,
                     'phase': 'rot=%s' % (rot,)})
    print('rendered', path)

with open(OUT_DIR + '\\gripor_sheet_manifest.json', 'w') as fh:
    json.dump({'name': 'sheet', 'frames': len(CANDS), 'fps': 1,
               'samples': manifest}, fh, indent=1)
