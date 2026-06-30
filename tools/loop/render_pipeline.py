"""
Blender Render Pipeline — Headless Import → Rig → Animate → Render
by Kore

Runs inside Blender via: blender.exe --background --python render_pipeline.py

Expects these environment variables (set by the outer loop):
  KORE_ANIMATION   — which animation to run: "walk", "feel", "threat" (default: "walk")
  KORE_RENDER_DIR  — Windows path for render output (default: C:/Users/kmessai/Downloads/spider_render)
  KORE_FRAME_RATE  — fps for the render (default: 24)
  KORE_RESOLUTION  — render resolution as WxH (default: 960x720)

All file paths inside this script use Windows UNC paths for \\wsl.localhost
because this runs inside Windows Blender, not Linux Python.
"""

import bpy
import mathutils
from mathutils import Vector
import os
import sys
import math
import shutil

# ============================================================
# CONFIGURATION
# ============================================================

# Read config from file (env vars unreliable across WSL→Windows boundary)
_config = {}
for _config_path in [
    r"\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\loop\.render_config",
    "/home/khaled/Kore/tools/loop/.render_config",
]:
    try:
        with open(_config_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _config[_k] = _v
        break
    except:
        continue

ANIMATION = _config.get("KORE_ANIMATION", os.environ.get("KORE_ANIMATION", "walk"))
CAMERA_VIEW = _config.get("KORE_CAMERA", os.environ.get("KORE_CAMERA", "3/4"))
RENDER_DIR = _config.get("KORE_RENDER_DIR", os.environ.get("KORE_RENDER_DIR", "C:/Users/kmessai/Downloads/spider_render"))
FRAME_RATE = int(os.environ.get("KORE_FRAME_RATE", "24"))
RESOLUTION = os.environ.get("KORE_RESOLUTION", "960x720")

# WSL UNC paths — Blender (Windows) reads WSL files via this prefix.
# IMPORTANT: Use backslash UNC format (\\wsl.localhost\Ubuntu\...) for file I/O.
# The forward-slash //wsl.localhost format gets mangled by bpy.path.abspath().
WSL_PREFIX = r"\\wsl.localhost\Ubuntu"

# Source files (WSL absolute paths, converted to Windows UNC)
GLB_PATH = WSL_PREFIX + r"\home\khaled\Kore\spider.glb"
RIG_SCRIPT = WSL_PREFIX + r"\home\khaled\Kore\tools\rig_spider_auto.py"

ANIMATION_SCRIPTS = {
    "walk": WSL_PREFIX + r"\home\khaled\Kore\tools\animate_walk.py",
    "feel": WSL_PREFIX + r"\home\khaled\Kore\tools\animate_feel.py",
    "threat": WSL_PREFIX + r"\home\khaled\Kore\tools\animate_threat.py",
    "prowl": WSL_PREFIX + r"\home\khaled\Kore\tools\animate_prowl.py",
}

res_w, res_h = RESOLUTION.split("x")
RES_X = int(res_w)
RES_Y = int(res_h)

print("=" * 60)
print("KORE RENDER PIPELINE")
print(f"  Animation: {ANIMATION}")
print(f"  Render dir: {RENDER_DIR}")
print(f"  Resolution: {RES_X}x{RES_Y} @ {FRAME_RATE}fps")
print("=" * 60)


# ============================================================
# STEP 1: CLEAR SCENE
# ============================================================

print("\n[1/6] Clearing scene...")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Remove orphan data
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.armatures:
    if block.users == 0:
        bpy.data.armatures.remove(block)
for block in bpy.data.actions:
    if block.users == 0:
        bpy.data.actions.remove(block)

print("  Scene cleared.")


# ============================================================
# STEP 2: IMPORT MESH
# ============================================================

print("\n[2/6] Importing spider mesh...")
# Use backslash UNC path — forward slashes with // trigger Blender's
# blend-relative path interpretation
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

mesh_obj = None
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
        break

if not mesh_obj:
    print("ERROR: No mesh found after import!")
    sys.exit(1)

print(f"  Imported: {mesh_obj.name} ({len(mesh_obj.data.vertices)} verts)")


# ============================================================
# STEP 3: RIG
# ============================================================

print("\n[3/6] Running rig script...")
with open(RIG_SCRIPT, 'r') as f:
    rig_code = f.read()
exec(rig_code)
print("  Rig complete.")


# ============================================================
# STEP 4: ANIMATE
# ============================================================

anim_script = ANIMATION_SCRIPTS.get(ANIMATION)
if not anim_script:
    print(f"ERROR: Unknown animation '{ANIMATION}'. Options: {list(ANIMATION_SCRIPTS.keys())}")
    sys.exit(1)

print(f"\n[4/6] Running animation: {ANIMATION}...")
with open(anim_script, 'r') as f:
    anim_code = f.read()
exec(anim_code)

# Smooth all keyframe interpolation (Blender 5.1 layered action API)
arm = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        arm = obj
        break
if arm and arm.animation_data and arm.animation_data.action:
    action = arm.animation_data.action
    smoothed = 0
    for layer in action.layers:
        for strip in layer.strips:
            if hasattr(strip, 'channelbags'):
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'BEZIER'
                            kp.handle_left_type = 'AUTO_CLAMPED'
                            kp.handle_right_type = 'AUTO_CLAMPED'
                            smoothed += 1
    print(f"  Smoothed {smoothed} keyframe handles.")

print("  Animation complete.")

# Ensure we're back in OBJECT mode for camera/light setup
bpy.ops.object.mode_set(mode='OBJECT')


# ============================================================
# STEP 5: SET UP CAMERA + LIGHTING
# ============================================================

print("\n[5/6] Setting up camera and lighting...")

# Make sure we're in object mode and nothing is selected
try:
    bpy.ops.object.mode_set(mode='OBJECT')
except:
    pass
bpy.ops.object.select_all(action='DESELECT')

# Find the spider's bounding box center
if mesh_obj:
    bbox = [mesh_obj.matrix_world @ mathutils.Vector(corner) for corner in mesh_obj.bound_box]
    center = sum(bbox, mathutils.Vector()) / 8
    # Bounding box dimensions
    mins = mathutils.Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    maxs = mathutils.Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    size = maxs - mins
    max_dim = max(size.x, size.y, size.z)
else:
    center = mathutils.Vector((0, 0, 0))
    max_dim = 1.0

# Camera — configurable view
cam_distance = max_dim * 2.5
if CAMERA_VIEW == "side":
    cam_x = center.x + cam_distance
    cam_y = center.y
    cam_z = center.z + cam_distance * 0.3
elif CAMERA_VIEW == "front":
    cam_x = center.x
    cam_y = center.y - cam_distance
    cam_z = center.z + cam_distance * 0.3
elif CAMERA_VIEW == "top":
    cam_x = center.x
    cam_y = center.y
    cam_z = center.z + cam_distance * 1.5
else:  # 3/4
    cam_x = center.x + cam_distance * 0.6
    cam_y = center.y - cam_distance * 0.8
    cam_z = center.z + cam_distance * 0.5

bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
camera = bpy.context.object
camera.name = "RenderCam"
bpy.context.scene.camera = camera

# Point camera at spider center
direction = center - camera.location
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

# Adjust lens for nice framing
camera.data.lens = 50  # 50mm — natural perspective
camera.data.clip_start = 0.01
camera.data.clip_end = 100

# Key light — main illumination from upper-left-front
bpy.ops.object.light_add(
    type='SUN',
    location=(center.x + 2, center.y - 2, center.z + 3)
)
key_light = bpy.context.object
key_light.name = "KeyLight"
key_light.data.energy = 3.0

# Fill light — softer, from the opposite side
bpy.ops.object.light_add(
    type='SUN',
    location=(center.x - 2, center.y + 1, center.z + 1)
)
fill_light = bpy.context.object
fill_light.name = "FillLight"
fill_light.data.energy = 1.0

# Rim light — from behind for edge definition
bpy.ops.object.light_add(
    type='SUN',
    location=(center.x - 1, center.y + 3, center.z + 2)
)
rim_light = bpy.context.object
rim_light.name = "RimLight"
rim_light.data.energy = 1.5

# Set world background to neutral gray
world = bpy.data.worlds.get("World")
if not world:
    world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)  # dark neutral gray

print(f"  Camera at ({cam_x:.2f}, {cam_y:.2f}, {cam_z:.2f})")
print(f"  Looking at ({center.x:.2f}, {center.y:.2f}, {center.z:.2f})")
print(f"  Three-point lighting set up.")


# ============================================================
# STEP 6: RENDER
# ============================================================

print(f"\n[6/6] Rendering animation...")

scene = bpy.context.scene

# Render settings
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100
scene.render.fps = FRAME_RATE

# Use EEVEE for speed (not Cycles)
scene.render.engine = 'BLENDER_EEVEE'

# Low samples for fast iteration
scene.eevee.taa_render_samples = 16

# Output as PNG image sequence (safest — we'll ffmpeg to MP4 in WSL)
os.makedirs(RENDER_DIR, exist_ok=True)

# Clean old frames
for f in os.listdir(RENDER_DIR):
    if f.startswith("frame_") and f.endswith(".png"):
        os.remove(os.path.join(RENDER_DIR, f))

scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = RENDER_DIR + "/frame_"

# Frame range from animation
print(f"  Frame range: {scene.frame_start} to {scene.frame_end}")
print(f"  Output: {RENDER_DIR}/frame_XXXX.png")
print(f"  Engine: EEVEE ({scene.eevee.taa_render_samples} samples)")

# Render all frames
bpy.ops.render.render(animation=True)

# Count rendered frames
rendered = [f for f in os.listdir(RENDER_DIR) if f.startswith("frame_") and f.endswith(".png")]
print(f"\n  Rendered {len(rendered)} frames to {RENDER_DIR}")

print("\n" + "=" * 60)
print("RENDER PIPELINE COMPLETE")
print("=" * 60)
