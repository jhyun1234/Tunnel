"""새 몸 m2 (Meshy, 2026-09-20) 를 지금 뼈대에 입히고 팔을 늘린다 — 손목이 무릎, 발톱이 정강이 (사용자 주문 09-20).
  blender -b --factory-startup -P blender/rig/m2_body.py
입력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend (안 고친다) + mesh/meshy_m2.glb (gen_meshy.py 산출, 기록은 MINER_ASSET_PIPELINE.md)
출력: Documents/MineTunnel/blender/miner_v5_stage17_m2.blend (새로) → SRC_BLEND 로 walk_knuckle.py 에 넘겨 GLB 를 굽는다
하는 일: ① m2 를 뼈대 크기로 맞춤(어깨 높이 기준) ② m2 팔을 뼈대 팔 자리에 맞춤 ③ 옛 몸·부위 그물에서 무게를 옮김(가까운 면 보간)
        ④ 어깨→손목을 ARM_K 배 — 살 점과 뼈에 같은 식 ⑤ 옛 몸·머리·갱목·못·끈을 뺌 (갱목은 새 몸 겉에 다시 맞춰야 한다 — 아직 안 함)
사보타주: ARM_K=1 -> "손목이 무릎 높이" FAIL · SABOTAGE=noinv -> "자세 잡은 살이 제 뼈 곁에" FAIL"""
import bpy, os, sys, numpy as np
from mathutils import Vector

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.path.join(MT, "blender", "miner_v4_stage16_neck.blend")
M2 = os.path.join(MT, "mesh", "meshy_m2.glb")
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage17_m2.blend"))
ARM_K = float(os.environ.get("ARM_K", "0"))      # 0 = 손목이 무릎에 오는 값을 뼈 길이에서 계산
M2_ARM_Z, M2_FLOOR, M2_WRIST_X, M2_SHOULDER_X = 0.415, -0.814, 0.64, 0.30 / 1.549   # m2 원본에서 잰 값 (팔 축 높이·발바닥·손목 x)

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
arm = bpy.data.objects["Miner_Rig"]
arm.data.pose_position = "REST"
W = lambda n: arm.matrix_world @ arm.data.bones["mixamorig:" + n].head_local
knee_z = W("LeftLeg").z

# ---- ① m2 들여와 크기 맞춤: 팔 축 높이 = 뼈대 어깨~손목 평균 높이가 아니라 어깨 높이 (팔은 ② 에서 기울인다)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=M2)
new = [o for o in bpy.data.objects if o not in before]
m2 = next(o for o in new if o.type == "MESH")
bpy.ops.object.select_all(action="DESELECT"); m2.select_set(True); bpy.context.view_layer.objects.active = m2
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in new:
    if o is not m2:
        bpy.data.objects.remove(o, do_unlink=True)
s = W("LeftArm").z / (M2_ARM_Z - M2_FLOOR)
V = np.array([v.co for v in m2.data.vertices]) * s
V[:, 2] -= M2_FLOOR * s
V[:, 1] += 0.04                                  # 뼈대 등뼈가 y +0.03~0.09 에 있다
print("m2 scale %.3f  height %.2f m" % (s, V[:, 2].max()))

# ---- ② 팔 맞춤 · ④ 팔 늘림: 어깨 S → 손목 Wr 선 위의 자리 t(0~1)만큼 밀기. 손은 t = 1 로 통째로
def arm_shift(P, side, vec_of_t):
    sx = 1 if side == "Left" else -1
    m = P[:, 0] * sx > xs
    t = np.clip((P[m, 0] * sx - xs) / (xw - xs), 0, 1)
    P[m] += np.outer(t, vec_of_t)
xs = M2_SHOULDER_X * s
for side in ("Left", "Right"):
    sx = 1 if side == "Left" else -1
    S, Wr = W(side + "Arm"), W(side + "Hand")
    xw = M2_WRIST_X * s
    arm_shift(V, side, np.array(Wr - S) - np.array([sx * (xw - xs), 0, 0]))
m2.data.vertices.foreach_set("co", V.ravel()); m2.data.update()

# ---- ③ 무게 옮기기: 옛 몸 + 부위(머리·손) 그물을 합친 사본에서
srcs = []
for n in ("Miner_Body", "Miner_Head"):
    o = bpy.data.objects[n]; c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c)
    for md in list(c.modifiers):
        c.modifiers.remove(md)
    srcs.append(c)
bpy.ops.object.select_all(action="DESELECT")
for c in srcs:
    c.select_set(True)
bpy.context.view_layer.objects.active = srcs[0]; bpy.ops.object.join(); src = bpy.context.active_object
bpy.ops.object.select_all(action="DESELECT"); m2.select_set(True); bpy.context.view_layer.objects.active = m2
dt = m2.modifiers.new("dt", "DATA_TRANSFER"); dt.object = src; dt.use_vert_data = True
dt.data_types_verts = {"VGROUP_WEIGHTS"}; dt.vert_mapping = "POLYINTERP_NEAREST"
dt.layers_vgroup_select_src = "ALL"; dt.layers_vgroup_select_dst = "NAME"
bpy.ops.object.datalayout_transfer(modifier="dt"); bpy.ops.object.modifier_apply(modifier="dt")
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)      # Unity 는 점마다 뼈 4개
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
bpy.data.objects.remove(src, do_unlink=True)
bones = {b.name for b in arm.data.bones}
unw = sum(1 for v in m2.data.vertices if sum(g.weight for g in v.groups if m2.vertex_groups[g.group].name in bones) < 0.99)
check(unw == 0, "모든 살 점의 뼈 무게 합 1 (모자란 점 %d / %d)" % (unw, len(m2.data.vertices)))

# ---- ④ 팔 늘림: 살 점과 뼈에 같은 식
up, fo = arm.data.bones["mixamorig:LeftArm"].length, arm.data.bones["mixamorig:LeftForeArm"].length
K = ARM_K or (W("LeftArm").z - knee_z) / (up + fo)
V = np.array([v.co for v in m2.data.vertices])
iw = np.array(arm.matrix_world.inverted())
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
for side in ("Left", "Right"):
    S, Wr = W(side + "Arm"), W(side + "Hand")
    xs, xw = abs(S.x), abs(Wr.x)
    add = np.array(Wr - S) * (K - 1)
    arm_shift(V, side, add)
    eb = [b for b in arm.data.edit_bones if b.name.startswith("mixamorig:" + side) and any(k in b.name for k in ("Arm", "Hand"))]
    for b in eb:
        b.use_connect = False
    for b in eb:                                   # 머리·꼬리를 세계 좌표로 옮겼다가 되돌린다 (뼈대는 x 축으로 90° 돌아 있다)
        for end in ("head", "tail"):
            p = np.array([arm.matrix_world @ getattr(b, end)]); arm_shift(p, side, add)
            setattr(b, end, Vector((iw @ np.append(p[0], 1))[:3]))
bpy.ops.object.mode_set(mode="OBJECT")
m2.data.vertices.foreach_set("co", V.ravel()); m2.data.update()
up2, fo2 = arm.data.bones["mixamorig:LeftArm"].length, arm.data.bones["mixamorig:LeftForeArm"].length
wrist_hang = W("LeftArm").z - (up2 + fo2)
hand_g = [g.index for g in m2.vertex_groups if g.name.startswith("mixamorig:LeftHand")]
hv = np.array([V[v.index] for v in m2.data.vertices if any(g.group in hand_g and g.weight > 0.5 for g in v.groups)])
tip_hang = wrist_hang - (hv[:, 0].max() - W("LeftHand").x)
print("ARM_K %.3f  팔 %.3f → %.3f m  늘어뜨리면 손목 %.2f m (무릎 %.2f) · 발톱 끝 %.2f m (발목 %.2f)" % (K, up + fo, up2 + fo2, wrist_hang, knee_z, tip_hang, W("LeftFoot").z))
check(abs(wrist_hang - knee_z) <= 0.03, "손목이 무릎 높이: 늘어뜨린 손목 %.3f m = 무릎 %.3f ± 0.03" % (wrist_hang, knee_z))
check(W("LeftFoot").z <= tip_hang <= knee_z, "발톱 끝이 정강이 안: %.3f m (발목 %.3f ~ 무릎 %.3f)" % (tip_hang, W("LeftFoot").z, knee_z))
check(abs(hv[:, 0].min() - W("LeftHand").x) <= 0.08, "손 살이 손 뼈를 따라감: 손 살 시작 x %.3f · 손목 뼈 x %.3f (≤ 0.08)" % (hv[:, 0].min(), W("LeftHand").x))

# ---- ⑤ 옛 것 빼고 새 몸을 Miner_Body 로
for o in list(bpy.data.objects):
    if o.name in ("Miner_Body", "Miner_Head") or o.name.split("_")[0] in ("Plank", "Nail", "Strap"):
        bpy.data.objects.remove(o, do_unlink=True)
m2.name = "Miner_Body"; m2.data.name = "Miner_Body_m2"; m2.data.materials[0].name = "살"
m2.parent = arm
if os.environ.get("SABOTAGE") != "noinv":
    m2.matrix_parent_inverse = arm.matrix_world.inverted()      # 뼈대가 x 축으로 90° 돌아 있다 — 안 하면 살이 같이 돈다
m2.modifiers.new("Armature", "ARMATURE").object = arm
arm.data.pose_position = "POSE"

# 자세를 잡았을 때 살이 뼈를 따라가는가 (09-20: 부모 역행렬을 빼먹어 살이 산산이 흩어진 것을 위 검사들이 못 잡았다)
ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
act = bpy.data.actions["idle_crouch"]; ad.action = act
if hasattr(ad, "action_slot") and act.slots:
    ad.action_slot = act.slots[0]
bpy.context.scene.frame_set(30)
dg = bpy.context.evaluated_depsgraph_get(); ev = m2.evaluated_get(dg); me = ev.to_mesh()
P = np.array([m2.matrix_world @ v.co for v in me.vertices]); ev.to_mesh_clear()
gname = [g.name for g in m2.vertex_groups]
far = 0.0
for i in range(0, len(P), 37):
    v = m2.data.vertices[i]; g = max(v.groups, key=lambda g: g.weight); pb = arm.pose.bones[gname[g.group]]
    a, b = arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail; p = Vector(P[i])
    t = max(0.0, min(1.0, (p - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
    far = max(far, (p - (a + (b - a) * t)).length)
check(far <= 0.45, "자세 잡은 살이 제 뼈 곁에 있다: idle_crouch 30프레임, 가장 먼 점 %.2f m (≤ 0.45)" % far)
ad.action = None
for tr in ad.nla_tracks:
    tr.mute = False
bpy.context.scene.frame_set(0)

if fails:
    sys.exit("m2_body FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m2_body ALL PASS →", OUT)
