"""
Auto-generated Spider Rig — Multi-Resolution Medial Axis
by Kore — coarse topology + fine precision
"""

import bpy
import mathutils
from mathutils import Vector

def find_mesh():
    for obj in bpy.data.objects:
        if obj.type == "MESH" and "Mesh" in obj.name:
            return obj
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            return obj
    return None

def add_bone(arm, name, head, tail, parent=None, connect=False):
    bone = arm.data.edit_bones.new(name)
    bone.head = Vector(head)
    bone.tail = Vector(tail)
    if parent and parent in arm.data.edit_bones:
        bone.parent = arm.data.edit_bones[parent]
        bone.use_connect = connect
    return bone

def build():
    mesh = find_mesh()
    if not mesh:
        print("No mesh found!")
        return

    # Clean up old rigs
    for obj in list(bpy.data.objects):
        if "SpiderRig" in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
    for arm in list(bpy.data.armatures):
        if "SpiderArmature" in arm.name:
            bpy.data.armatures.remove(arm)

    # Clear parent and APPLY ALL TRANSFORMS
    # This bakes location+rotation into vertices so everything is in world space
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")
    print(f"Mesh after apply: loc={mesh.location}, rot={mesh.rotation_euler}")

    # After transform_apply, mesh.location should be (0,0,0)
    # Create armature at origin — same space as mesh vertices now
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "SpiderRig"
    arm.data.name = "SpiderArmature"
    default = arm.data.edit_bones.get("Bone")
    if default:
        arm.data.edit_bones.remove(default)

    add_bone(arm, "root", (-0.083411, 0.002185, 0.073965), (-0.083411, 0.002185, 0.153965))
    add_bone(arm, "cephalothorax", (-0.083411, 0.002185, 0.073965), (-0.083411, 0.002185, 0.193965), "root")
    add_bone(arm, "abdomen", (-0.087796, 0.099692, 0.052216), (-0.108000, 0.549000, -0.048000), "root")

    # Leg FL
    add_bone(arm, "leg_FL_coxa", (0.696000, -0.855000, -0.297000), (0.527826, -0.645085, -0.219106), "cephalothorax", False)
    add_bone(arm, "leg_FL_femur", (0.527826, -0.645085, -0.219106), (0.442575, -0.533413, 0.000518), "leg_FL_coxa", True)
    add_bone(arm, "leg_FL_tibia", (0.442575, -0.533413, 0.000518), (0.214195, -0.292958, 0.139608), "leg_FL_femur", True)
    add_bone(arm, "leg_FL_tarsus", (0.214195, -0.292958, 0.139608), (0.037313, -0.152623, 0.085042), "leg_FL_tibia", True)

    # Leg FR
    add_bone(arm, "leg_FR_coxa", (-0.885436, -0.814759, -0.291117), (-0.767792, -0.673644, -0.260669), "cephalothorax", False)
    add_bone(arm, "leg_FR_femur", (-0.767792, -0.673644, -0.260669), (-0.637462, -0.510697, 0.034383), "leg_FR_coxa", True)
    add_bone(arm, "leg_FR_tibia", (-0.637462, -0.510697, 0.034383), (-0.393105, -0.257202, 0.130023), "leg_FR_femur", True)
    add_bone(arm, "leg_FR_tarsus", (-0.393105, -0.257202, 0.130023), (-0.110665, -0.066143, 0.080080), "leg_FR_tibia", True)

    # Leg ML
    add_bone(arm, "leg_ML_coxa", (0.843000, -0.084000, -0.312000), (0.497170, -0.071116, -0.046345), "cephalothorax", False)
    add_bone(arm, "leg_ML_femur", (0.497170, -0.071116, -0.046345), (0.189643, -0.050649, 0.104349), "leg_ML_coxa", True)
    add_bone(arm, "leg_ML_tibia", (0.189643, -0.050649, 0.104349), (-0.102573, -0.076757, 0.080433), "leg_ML_femur", True)

    # Leg MR
    add_bone(arm, "leg_MR_coxa", (-1.034252, -0.083002, -0.304438), (-0.717268, -0.074263, -0.048832), "cephalothorax", False)
    add_bone(arm, "leg_MR_femur", (-0.717268, -0.074263, -0.048832), (-0.438069, -0.052527, 0.088706), "leg_MR_coxa", True)
    add_bone(arm, "leg_MR_tibia", (-0.438069, -0.052527, 0.088706), (-0.110665, -0.066143, 0.080080), "leg_MR_femur", True)

    # Leg RL
    add_bone(arm, "leg_RL_coxa", (0.638760, 0.827292, -0.311435), (0.568608, 0.540788, -0.249031), "cephalothorax", False)
    add_bone(arm, "leg_RL_femur", (0.568608, 0.540788, -0.249031), (0.430004, 0.359555, 0.042231), "leg_RL_coxa", True)
    add_bone(arm, "leg_RL_tibia", (0.430004, 0.359555, 0.042231), (0.152510, 0.266178, 0.165641), "leg_RL_femur", True)
    add_bone(arm, "leg_RL_tarsus", (0.152510, 0.266178, 0.165641), (-0.105237, 0.193772, 0.058956), "leg_RL_tibia", True)

    # Leg RR
    add_bone(arm, "leg_RR_coxa", (-0.864000, 0.852000, -0.312000), (-0.783129, 0.524928, -0.248361), "cephalothorax", False)
    add_bone(arm, "leg_RR_femur", (-0.783129, 0.524928, -0.248361), (-0.659861, 0.367471, 0.026802), "leg_RR_coxa", True)
    add_bone(arm, "leg_RR_tibia", (-0.659861, 0.367471, 0.026802), (-0.108641, 0.181001, 0.059200), "leg_RR_femur", True)

    add_bone(arm, "pedipalp_L_base", (-0.126000, -0.138000, 0.093000), (-0.225000, -0.312000, 0.153000), "cephalothorax")
    add_bone(arm, "pedipalp_L_tip", (-0.225000, -0.312000, 0.153000), (-0.267000, -0.516000, 0.114000), "pedipalp_L_base", True)

    add_bone(arm, "pedipalp_R_base", (-0.018000, -0.213000, 0.102000), (0.018000, -0.360000, 0.141000), "cephalothorax")
    add_bone(arm, "pedipalp_R_tip", (0.018000, -0.360000, 0.141000), (0.051000, -0.528000, 0.111000), "pedipalp_R_base", True)

    add_bone(arm, "fang_L", (-0.108000, -0.180000, 0.102000), (-0.072000, -0.261000, 0.054000), "cephalothorax")

    add_bone(arm, "fang_R", (-0.108000, -0.180000, 0.102000), (-0.150000, -0.258000, 0.069000), "cephalothorax")

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_NAME")

    print("Computing physics-based arthropod weights...")
    print("  Chitin plates: rigid (weight 1.0)")
    print("  Articular membranes: linear blend at joints")
    bpy.context.view_layer.objects.active = mesh

    JOINT_BLEND_WIDTH = 0.02  # meters — width of articular membrane

    # Build bone chain data
    bone_data = []  # [(name, head_world, tail_world, group, chain_index)]
    bone_chains = {}  # group -> ordered list of bone names
    for bone in arm.data.bones:
        h = arm.matrix_world @ bone.head_local
        t = arm.matrix_world @ bone.tail_local
        name = bone.name
        if name.startswith("leg_"):
            group = "_".join(name.split("_")[:2])
        elif "pedipalp" in name:
            group = "pedipalp_" + name.split("_")[1]
        elif "fang" in name:
            group = "fang_" + name.split("_")[1]
        else:
            group = "body"
        if group not in bone_chains:
            bone_chains[group] = []
        chain_idx = len(bone_chains[group])
        bone_chains[group].append(name)
        bone_data.append((name, h, t, group, chain_idx))

    def project_onto_bone(p, a, b):
        """Project point p onto bone segment a→b. Returns (distance, t_parameter)."""
        ab = b - a
        ab_len_sq = ab.dot(ab)
        if ab_len_sq < 1e-10:
            return (p - a).length, 0.5
        t = max(0, min(1, (p - a).dot(ab) / ab_len_sq))
        closest = a + ab * t
        return (p - closest).length, t

    mesh_world = mesh.matrix_world
    for v in mesh.data.vertices:
        v_world = mesh_world @ v.co

        # Step 1: Find closest bone per group, with body priority
        all_dists = []
        body_dist = float("inf")
        body_bone = None
        body_t = 0
        for bname, bh, bt, bgroup, cidx in bone_data:
            d, t = project_onto_bone(v_world, bh, bt)
            all_dists.append((d, bname, bgroup, cidx, t))
            if bgroup == "body" and d < body_dist:
                body_dist = d
                body_bone = bname
                body_t = t

        all_dists.sort()
        best_dist, best_bone, best_group, best_chain_idx, best_t = all_dists[0]

        # BODY PRIORITY: if a body bone is within 2x the closest bone distance,
        # this vertex belongs to the body, not a leg.
        # Chitin body plates are large — they win ties against nearby leg coxa bones.
        if best_group != "body" and body_bone and body_dist < best_dist * 2.5:
            best_bone = body_bone
            best_group = "body"
            best_chain_idx = 0
            best_t = body_t
            best_dist = body_dist

        # Step 2: Rigid plate or joint membrane?
        chain = bone_chains[best_group]
        bone_head = None
        bone_tail = None
        for bname, bh, bt, bg, ci in bone_data:
            if bname == best_bone:
                bone_head = bh
                bone_tail = bt
                break
        bone_length = (bone_tail - bone_head).length if bone_head and bone_tail else 0.1
        blend_t = min(JOINT_BLEND_WIDTH / max(bone_length, 0.01), 0.4)

        weights = {}

        # Check if near the HEAD of the bone (joint with previous bone in chain)
        if best_t < blend_t and best_chain_idx > 0:
            prev_bone = chain[best_chain_idx - 1]
            factor = best_t / blend_t  # 0 at joint, 1 at blend edge
            weights[best_bone] = factor
            weights[prev_bone] = 1.0 - factor

        # Check if near the TAIL of the bone (joint with next bone in chain)
        elif best_t > (1.0 - blend_t) and best_chain_idx < len(chain) - 1:
            next_bone = chain[best_chain_idx + 1]
            factor = (1.0 - best_t) / blend_t  # 0 at joint, 1 at blend edge
            weights[best_bone] = factor
            weights[next_bone] = 1.0 - factor

        # Check if coxa near body (blend with cephalothorax)
        elif best_t > (1.0 - blend_t) and best_chain_idx == len(chain) - 1 and best_group.startswith("leg_"):
            factor = (1.0 - best_t) / blend_t
            weights[best_bone] = factor
            weights["cephalothorax"] = 1.0 - factor

        else:
            # RIGID PLATE — 100% to this bone
            weights[best_bone] = 1.0

        # Assign weights
        for bname, w in weights.items():
            if w < 0.001:
                continue
            if bname not in mesh.vertex_groups:
                mesh.vertex_groups.new(name=bname)
            mesh.vertex_groups[bname].add([v.index], w, "REPLACE")

    print("=" * 50)
    print("RIGGING COMPLETE")
    print("Physics-based arthropod weights:")
    print("  Rigid plates + linear blend at joints")
    print(f"  Bones: {len(arm.data.bones)}")
    print(f"  Joint blend width: {JOINT_BLEND_WIDTH}m")
    print("=" * 50)

try:
    build()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()