"""Where is the void inside the curled 'grip' fist, in hand-local coords?
Prints posed joint positions of each finger chain (armature-local space).
"""
import bpy
import math

SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\animate_sword.py'
code = open(SRC).read()
code = code[:code.rfind('def main')]
exec(code)

strip_scene()
stage_hands()
right = bpy.data.objects[RIGHT_ARM]
clear_anim(right)
key_pose(right, 1, 'grip')
bpy.context.scene.frame_set(1)

deps = bpy.context.evaluated_depsgraph_get()
ev = right.evaluated_get(deps)
inv = ev.matrix_world.inverted()
for finger, chain in CHAINS.items():
    pts = []
    for bn in chain:
        pb = ev.pose.bones[bn]
        head = inv @ (ev.matrix_world @ pb.head)
        pts.append('(%5.2f,%5.2f,%5.2f)' % tuple(head))
    tip = inv @ (ev.matrix_world @ ev.pose.bones[chain[-1]].tail)
    pts.append('tip(%5.2f,%5.2f,%5.2f)' % tuple(tip))
    print('VOID %-6s %s' % (finger, ' '.join(pts)))
root = ev.pose.bones['Bone']
print('VOID root tail (%5.2f,%5.2f,%5.2f)' % tuple(inv @ (ev.matrix_world @ root.tail)))
