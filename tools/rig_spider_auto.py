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
    add_bone(arm, "leg_FL_coxa", (0.037313, -0.152623, 0.085042), (0.214195, -0.292958, 0.139608), "cephalothorax", False)
    add_bone(arm, "leg_FL_femur", (0.214195, -0.292958, 0.139608), (0.442575, -0.533413, 0.000518), "leg_FL_coxa", True)
    add_bone(arm, "leg_FL_tibia", (0.442575, -0.533413, 0.000518), (0.527826, -0.645085, -0.219106), "leg_FL_femur", True)
    add_bone(arm, "leg_FL_tarsus", (0.527826, -0.645085, -0.219106), (0.696000, -0.855000, -0.297000), "leg_FL_tibia", True)

    # Leg FR
    add_bone(arm, "leg_FR_coxa", (-0.110665, -0.066143, 0.080080), (-0.111371, -0.073071, 0.081563), "cephalothorax", False)
    add_bone(arm, "leg_FR_femur", (-0.111371, -0.073071, 0.081563), (-0.393105, -0.257202, 0.130023), "leg_FR_coxa", True)
    add_bone(arm, "leg_FR_tibia", (-0.393105, -0.257202, 0.130023), (-0.637462, -0.510697, 0.034383), "leg_FR_femur", True)
    add_bone(arm, "leg_FR_tarsus", (-0.637462, -0.510697, 0.034383), (-0.767792, -0.673644, -0.260669), "leg_FR_tibia", True)
    add_bone(arm, "leg_FR_seg4", (-0.767792, -0.673644, -0.260669), (-0.885436, -0.814759, -0.291117), "leg_FR_tarsus", True)

    # Leg ML
    add_bone(arm, "leg_ML_coxa", (-0.102573, -0.076757, 0.080433), (-0.017500, -0.082671, 0.107126), "cephalothorax", False)
    add_bone(arm, "leg_ML_femur", (-0.017500, -0.082671, 0.107126), (0.189643, -0.050649, 0.104349), "leg_ML_coxa", True)
    add_bone(arm, "leg_ML_tibia", (0.189643, -0.050649, 0.104349), (0.497170, -0.071116, -0.046345), "leg_ML_femur", True)
    add_bone(arm, "leg_ML_tarsus", (0.497170, -0.071116, -0.046345), (0.843000, -0.084000, -0.312000), "leg_ML_tibia", True)

    # Leg MR
    add_bone(arm, "leg_MR_coxa", (-0.110665, -0.066143, 0.080080), (-0.111452, -0.052403, 0.076857), "cephalothorax", False)
    add_bone(arm, "leg_MR_femur", (-0.111452, -0.052403, 0.076857), (-0.438069, -0.052527, 0.088706), "leg_MR_coxa", True)
    add_bone(arm, "leg_MR_tibia", (-0.438069, -0.052527, 0.088706), (-0.717268, -0.074263, -0.048832), "leg_MR_femur", True)
    add_bone(arm, "leg_MR_tarsus", (-0.717268, -0.074263, -0.048832), (-1.034252, -0.083002, -0.304438), "leg_MR_tibia", True)

    # Leg RL
    add_bone(arm, "leg_RL_coxa", (-0.105237, 0.193772, 0.058956), (-0.108357, 0.147016, 0.073565), "cephalothorax", False)
    add_bone(arm, "leg_RL_femur", (-0.108357, 0.147016, 0.073565), (0.152510, 0.266178, 0.165641), "leg_RL_coxa", True)
    add_bone(arm, "leg_RL_tibia", (0.152510, 0.266178, 0.165641), (0.430004, 0.359555, 0.042231), "leg_RL_femur", True)
    add_bone(arm, "leg_RL_tarsus", (0.430004, 0.359555, 0.042231), (0.568608, 0.540788, -0.249031), "leg_RL_tibia", True)
    add_bone(arm, "leg_RL_seg4", (0.568608, 0.540788, -0.249031), (0.638760, 0.827292, -0.311435), "leg_RL_tarsus", True)

    # Leg RR
    add_bone(arm, "leg_RR_coxa", (-0.108641, 0.181001, 0.059200), (-0.108759, 0.183868, 0.058457), "cephalothorax", False)
    add_bone(arm, "leg_RR_femur", (-0.108759, 0.183868, 0.058457), (-0.659861, 0.367471, 0.026802), "leg_RR_coxa", True)
    add_bone(arm, "leg_RR_tibia", (-0.659861, 0.367471, 0.026802), (-0.783129, 0.524928, -0.248361), "leg_RR_femur", True)
    add_bone(arm, "leg_RR_tarsus", (-0.783129, 0.524928, -0.248361), (-0.864000, 0.852000, -0.312000), "leg_RR_tibia", True)

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

    print("Computing two-layer weights...")
    print("  Layer 1: Branch segmentation (medial axis paths)")
    print("  Layer 2: Rigid plate + joint blend (chitin physics)")
    bpy.context.view_layer.objects.active = mesh

    BRANCH_PATHS = {"leg_RR": [[-0.864, 0.852, -0.312], [-0.8328, 0.7223, -0.2895], [-0.8118, 0.6454, -0.2742], [-0.7898, 0.5541, -0.2532], [-0.7636, 0.4905, -0.2071], [-0.723, 0.4445, -0.1164], [-0.7018, 0.4181, -0.0696], [-0.6713, 0.3827, -0.0049], [-0.6347, 0.3528, 0.0482], [-0.5816, 0.3319, 0.079], [-0.5279, 0.3104, 0.1062], [-0.4108, 0.2732, 0.1642], [-0.3033, 0.2291, 0.1204], [-0.2367, 0.1896, 0.077], [-0.1086, 0.181, 0.0592]], "leg_RL": [[0.6388, 0.8273, -0.3114], [0.6124, 0.7196, -0.2888], [0.593, 0.6351, -0.271], [0.5688, 0.548, -0.2509], [0.5524, 0.4955, -0.213], [0.5171, 0.4557, -0.1412], [0.4757, 0.4078, -0.0511], [0.4394, 0.3658, 0.0187], [0.4051, 0.3482, 0.0577], [0.341, 0.3232, 0.0885], [0.2982, 0.3054, 0.1103], [0.2065, 0.2739, 0.1519], [0.0837, 0.2275, 0.1201], [0.0321, 0.1995, 0.0863], [-0.1052, 0.1938, 0.059]], "leg_FR": [[-0.8854, -0.8148, -0.2911], [-0.7962, -0.7065, -0.2671], [-0.7612, -0.6764, -0.2643], [-0.7197, -0.6124, -0.1583], [-0.6893, -0.5728, -0.0829], [-0.6601, -0.5373, -0.0135], [-0.6026, -0.4767, 0.0534], [-0.5487, -0.4202, 0.0808], [-0.5101, -0.3788, 0.0994], [-0.474, -0.3384, 0.119], [-0.3897, -0.2547, 0.1302], [-0.3425, -0.2197, 0.1114], [-0.2844, -0.1747, 0.0944], [-0.2144, -0.13, 0.0838], [-0.1107, -0.0661, 0.0801]], "leg_FL": [[0.696, -0.855, -0.297], [0.6369, -0.7818, -0.2846], [0.5771, -0.7061, -0.2676], [0.5459, -0.6605, -0.2551], [0.5169, -0.632, -0.197], [0.4871, -0.5956, -0.1244], [0.4663, -0.5692, -0.0754], [0.4426, -0.5334, 0.0005], [0.3689, -0.4617, 0.0603], [0.3136, -0.4023, 0.0886], [0.2638, -0.3465, 0.1152], [0.2283, -0.3087, 0.1319], [0.1549, -0.241, 0.1234], [0.0951, -0.1959, 0.1035], [0.0373, -0.1526, 0.085]], "leg_MR": [[-1.0343, -0.083, -0.3044], [-0.9657, -0.0805, -0.2882], [-0.8996, -0.0809, -0.2739], [-0.8377, -0.0777, -0.2349], [-0.786, -0.0762, -0.1557], [-0.7424, -0.0747, -0.0854], [-0.7173, -0.0743, -0.0488], [-0.6627, -0.073, 0.0059], [-0.6055, -0.0682, 0.0289], [-0.522, -0.0608, 0.0612], [-0.4768, -0.0584, 0.0788], [-0.4101, -0.0518, 0.1007], [-0.2957, -0.0791, 0.0962], [-0.114, -0.0495, 0.0776], [-0.1107, -0.0661, 0.0801]], "leg_ML": [[0.843, -0.084, -0.312], [0.7829, -0.0808, -0.2997], [0.7049, -0.0805, -0.2816], [0.622, -0.0775, -0.239], [0.5575, -0.0757, -0.1379], [0.5337, -0.0745, -0.102], [0.4995, -0.0725, -0.0467], [0.4543, -0.0737, 0.0027], [0.4283, -0.0711, 0.0109], [0.3598, -0.0664, 0.039], [0.3111, -0.0621, 0.0588], [0.2215, -0.0544, 0.0933], [0.1887, -0.0656, 0.0991], [0.075, -0.0766, 0.095], [-0.1026, -0.0768, 0.0804]], "body": [[-0.0834, 0.0022, 0.074]], "abdomen": [[-0.108, 0.552, -0.048], [-0.108, 0.504, -0.012], [-0.108, 0.456, 0.0], [-0.108, 0.408, 0.0], [-0.108, 0.36, 0.012], [-0.108, 0.312, 0.036], [-0.108, 0.264, 0.06], [-0.108, 0.204, 0.072]], "pedipalp_L": [[-0.267, -0.516, 0.114], [-0.249, -0.444, 0.12], [-0.234, -0.36, 0.141], [-0.216, -0.273, 0.153], [-0.201, -0.216, 0.105], [-0.126, -0.138, 0.093]], "pedipalp_R": [[0.051, -0.528, 0.111], [0.033, -0.462, 0.12], [0.021, -0.396, 0.132], [0.012, -0.333, 0.15], [-0.003, -0.27, 0.153], [-0.018, -0.213, 0.102]], "fang_L": [[-0.072, -0.261, 0.054], [-0.069, -0.258, 0.06], [-0.069, -0.252, 0.072], [-0.072, -0.243, 0.081], [-0.078, -0.231, 0.087], [-0.081, -0.222, 0.09], [-0.093, -0.21, 0.093], [-0.102, -0.192, 0.099], [-0.108, -0.18, 0.102]], "fang_R": [[-0.15, -0.258, 0.069], [-0.147, -0.246, 0.078], [-0.144, -0.24, 0.084], [-0.141, -0.228, 0.087], [-0.135, -0.213, 0.093], [-0.129, -0.207, 0.096], [-0.117, -0.195, 0.099], [-0.108, -0.18, 0.102]]}

    JOINT_BLEND_WIDTH = 0.025
    BRANCH_BLEND_WIDTH = 0.04  # blend zone at leg-body junction

    def dist_to_path(p, path_points):
        """Minimum distance from point p to a polyline path."""
        min_d = float("inf")
        for i in range(len(path_points)):
            pt = Vector(path_points[i])
            d = (p - pt).length
            if d < min_d:
                min_d = d
        # Also check segments between consecutive points
        for i in range(len(path_points) - 1):
            a = Vector(path_points[i])
            b = Vector(path_points[i+1])
            ab = b - a
            ab_sq = ab.dot(ab)
            if ab_sq < 1e-10:
                continue
            t = max(0, min(1, (p - a).dot(ab) / ab_sq))
            closest = a + ab * t
            d = (p - closest).length
            if d < min_d:
                min_d = d
        return min_d

    def project_onto_bone(p, a, b):
        ab = b - a
        ab_sq = ab.dot(ab)
        if ab_sq < 1e-10:
            return (p - a).length, 0.5
        t = max(0, min(1, (p - a).dot(ab) / ab_sq))
        closest = a + ab * t
        return (p - closest).length, t

    # Build bone chain data
    bone_data = []
    bone_chains = {}
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

    mesh_world = mesh.matrix_world
    for v in mesh.data.vertices:
        v_world = mesh_world @ v.co

        # === LAYER 1: Branch segmentation ===
        # Find closest branch path for this vertex
        branch_dists = {}
        for branch_name, path_pts in BRANCH_PATHS.items():
            branch_dists[branch_name] = dist_to_path(v_world, path_pts)

        sorted_branches = sorted(branch_dists.items(), key=lambda x: x[1])
        best_branch = sorted_branches[0][0]
        best_branch_dist = sorted_branches[0][1]

        # Map branch name to bone group
        if best_branch == "body":
            assigned_group = "body"
        elif best_branch == "abdomen":
            assigned_group = "body"  # abdomen is a body bone
        else:
            assigned_group = best_branch

        # Check for branch junction blend (leg meets body)
        branch_blend = None
        if len(sorted_branches) > 1:
            second_branch = sorted_branches[1][0]
            second_dist = sorted_branches[1][1]
            gap = second_dist - best_branch_dist
            if gap < BRANCH_BLEND_WIDTH:
                # At junction — check if it is a leg-body boundary
                is_leg_body = (best_branch.startswith("leg_") and second_branch in ("body", "abdomen")) or \
                              (second_branch.startswith("leg_") and best_branch in ("body", "abdomen"))
                if is_leg_body:
                    blend_factor = gap / BRANCH_BLEND_WIDTH  # 0=at junction, 1=at edge
                    branch_blend = (best_branch, second_branch, blend_factor)

        # === LAYER 2: Within-branch bone weighting ===
        if assigned_group not in bone_chains:
            assigned_group = "body"

        # Find closest bone WITHIN the assigned group
        best_dist = float("inf")
        best_bone = None
        best_t = 0
        best_cidx = 0
        for bname, bh, bt, bgroup, cidx in bone_data:
            if bgroup != assigned_group:
                continue
            d, t = project_onto_bone(v_world, bh, bt)
            if d < best_dist:
                best_dist = d
                best_bone = bname
                best_t = t
                best_cidx = cidx

        if best_bone is None:
            # Fallback: closest bone of any group
            for bname, bh, bt, bgroup, cidx in bone_data:
                d, t = project_onto_bone(v_world, bh, bt)
                if d < best_dist:
                    best_dist = d
                    best_bone = bname
                    best_t = t
                    best_cidx = cidx
                    assigned_group = bgroup

        chain = bone_chains.get(assigned_group, [best_bone])
        bone_head = bone_tail = None
        for bname, bh, bt, bg, ci in bone_data:
            if bname == best_bone:
                bone_head, bone_tail = bh, bt
                break
        bone_length = (bone_tail - bone_head).length if bone_head and bone_tail else 0.1
        blend_t = min(JOINT_BLEND_WIDTH / max(bone_length, 0.01), 0.4)

        weights = {}

        # Joint blend within the bone chain
        if best_t < blend_t and best_cidx > 0:
            prev_bone = chain[best_cidx - 1]
            factor = best_t / blend_t
            weights[best_bone] = factor
            weights[prev_bone] = 1.0 - factor
        elif best_t > (1.0 - blend_t) and best_cidx < len(chain) - 1:
            next_bone = chain[best_cidx + 1]
            factor = (1.0 - best_t) / blend_t
            weights[best_bone] = factor
            weights[next_bone] = 1.0 - factor
        else:
            weights[best_bone] = 1.0

        # Apply branch junction blend (leg ↔ body)
        if branch_blend:
            _, _, bf = branch_blend
            # bf=0 at junction (50/50), bf=1 at edge (100% assigned branch)
            body_weight = (1.0 - bf) * 0.5
            leg_weight = 1.0 - body_weight
            body_bone_name = "cephalothorax"
            adjusted = {}
            for bname, w in weights.items():
                adjusted[bname] = w * leg_weight
            adjusted[body_bone_name] = adjusted.get(body_bone_name, 0) + body_weight
            weights = adjusted

        for bname, w in weights.items():
            if w < 0.001:
                continue
            if bname not in mesh.vertex_groups:
                mesh.vertex_groups.new(name=bname)
            mesh.vertex_groups[bname].add([v.index], w, "REPLACE")

    print("=" * 50)
    print("RIGGING COMPLETE")
    print("  Two-layer weights: branch segmentation + rigid plates")
    print(f"  Bones: {len(arm.data.bones)}")
    print("=" * 50)

try:
    build()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()