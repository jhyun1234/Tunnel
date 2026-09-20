"""Meshy 새 몸을 지금 뼈대에 입히고 팔을 늘린다 — 손목이 무릎, 발톱이 정강이 (사용자 주문 09-20).
  blender -b --factory-startup -P blender/rig/m2_body.py                       # m3 (부위 조립, 기본)
  BODY=m2 blender -b --factory-startup -P blender/rig/m2_body.py               # 전신 한 장으로 뽑은 m2 (09-20 게임에서 본 것 — 머리·손이 뭉개져 불통과)
입력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend (안 고친다) + mesh/meshy_<BODY>.glb (m3 는 m3_assemble.py 산출, m2 좌표계 그대로)
출력: Documents/MineTunnel/blender/miner_v5_stage17_<BODY>.blend (새로) → SRC_BLEND 로 walk_knuckle.py 에 넘겨 GLB 를 굽는다
하는 일: ① 뼈대 크기로 맞춤(어깨 높이 기준) ② 팔을 뼈대 팔 자리에 맞춤 ③ 옛 몸·부위 그물에서 무게를 옮김(가까운 면 보간)
        ④ 어깨→손목을 ARM_K 배 — 살 점과 뼈에 같은 식 ⑤ 옛 몸·머리·갱목·못·끈을 뺌 (갱목은 새 몸 겉에 다시 맞춰야 한다 — 아직 안 함)
그물이 여럿이어도(m3: 몸·머리·손·속 몸통) 하나씩 같은 식으로 — glTFast 는 스킨 그물 하나에 재질 둘을 못 읽어 합치지 않는다.
사보타주: ARM_K=1 -> "손목이 무릎 높이" FAIL · SABOTAGE=noinv -> "자세 잡은 살이 제 뼈 곁에" FAIL · SABOTAGE=nodetail -> "늘린 팔 겉에 잔결이 있다" FAIL"""
import bpy, os, sys, numpy as np
from mathutils import Vector

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
BODY = os.environ.get("BODY", "m3")
SRC = os.path.join(MT, "blender", "miner_v4_stage16_neck.blend")
GLB = os.path.join(MT, "mesh", "meshy_%s.glb" % BODY)
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage17_%s.blend" % BODY))
ARM_K = float(os.environ.get("ARM_K", "0"))      # 0 = 손목이 무릎에 오는 값을 뼈 길이에서 계산
M2_ARM_Z, M2_FLOOR, M2_WRIST_X, M2_SHOULDER_X = 0.415, -0.814, 0.64, 0.30 / 1.549   # m2 원본에서 잰 값 (팔 축 높이·발바닥·손목 x)

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)
def co(o):
    a = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get("co", a); return a.reshape(-1, 3).astype(np.float64)
def put(o, V):
    o.data.vertices.foreach_set("co", V.astype(np.float32).ravel()); o.data.update()

bpy.ops.wm.open_mainfile(filepath=SRC)
for m_ in bpy.data.materials:                     # 새 그물의 재질이 옛 이름(살·살_머리)을 그대로 쓴다 — 옛 것을 비켜 두지 않으면 '.001' 이 붙는다
    if m_.name.startswith('살'):                   # 목_근육 은 그대로 (Unity 가 '목' 으로 찾는다)
        m_.name = 'old_' + m_.name
arm = bpy.data.objects["Miner_Rig"]
arm.data.pose_position = "REST"
W = lambda n: arm.matrix_world @ arm.data.bones["mixamorig:" + n].head_local
knee_z = W("LeftLeg").z

# ---- ① 들여와 크기 맞춤: 팔 축 높이 = 뼈대 어깨 높이 (팔은 ② 에서 기울인다)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in before]
parts = [o for o in new if o.type == "MESH"]
for o in parts:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in new:
    if o not in parts:
        bpy.data.objects.remove(o, do_unlink=True)
want = {o: (o.name.split(".")[0] if BODY != "m2" else "Miner_Body", o.data.materials[0].name.split(".")[0] if BODY != "m2" else "살") for o in parts}
s = W("LeftArm").z / (M2_ARM_Z - M2_FLOOR)
print("scale %.3f  parts %s" % (s, [want[o][0] for o in parts]))

def arm_shift(P, side, vec_of_t):
    """어깨 S → 손목 Wr 선 위의 자리 t(0~1)만큼 밀기. 손은 t = 1 로 통째로"""
    sx = 1 if side == "Left" else -1
    m = P[:, 0] * sx > xs
    t = np.clip((P[m, 0] * sx - xs) / (xw - xs), 0, 1)
    P[m] += np.outer(t, vec_of_t)

# ---- ② 팔 맞춤
for o in parts:
    V = co(o) * s
    V[:, 2] -= M2_FLOOR * s
    V[:, 1] += 0.04                              # 뼈대 등뼈가 y +0.03~0.09 에 있다
    xs, xw = M2_SHOULDER_X * s, M2_WRIST_X * s
    for side in ("Left", "Right"):
        sx = 1 if side == "Left" else -1
        arm_shift(V, side, np.array(W(side + "Hand") - W(side + "Arm")) - np.array([sx * (xw - xs), 0, 0]))
    put(o, V)

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
bones = {b.name for b in arm.data.bones}
unw = total = 0
for o in parts:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    dt = o.modifiers.new("dt", "DATA_TRANSFER"); dt.object = src; dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}; dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"; dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.datalayout_transfer(modifier="dt"); bpy.ops.object.modifier_apply(modifier="dt")
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)      # Unity 는 점마다 뼈 4개
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    if want[o][0] == "Miner_Hands":
        # 손은 통짜로 손 뼈에만: 옛 손가락 무게를 가까운 면으로 옮기면 새 발톱 다섯과 어긋나 굽힐 때 발톱이 리본처럼 찢긴다(09-20 자세 렌더).
        # 값: 발톱 모양이 산다. 잃는 것: 손가락 굽힘(Unity 가 얹는 것 포함)이 안 먹는다 — 발톱마다 뼈를 다시 맞추는 것은 다음 일
        o.vertex_groups.clear()
        X = co(o)[:, 0]
        for side, idx in (("Left", np.where(X > 0)[0]), ("Right", np.where(X <= 0)[0])):
            o.vertex_groups.new(name="mixamorig:%sHand" % side).add([int(i) for i in idx], 1.0, "REPLACE")
    unw += sum(1 for v in o.data.vertices if sum(g.weight for g in v.groups if o.vertex_groups[g.group].name in bones) < 0.99)
    total += len(o.data.vertices)
bpy.data.objects.remove(src, do_unlink=True)
check(unw == 0, "모든 살 점의 뼈 무게 합 1 (모자란 점 %d / %d)" % (unw, total))

# ---- ④ 팔 늘림: 살 점과 뼈에 같은 식
up, fo = arm.data.bones["mixamorig:LeftArm"].length, arm.data.bones["mixamorig:LeftForeArm"].length
K = ARM_K or (W("LeftArm").z - knee_z) / (up + fo)
Vs = {o: co(o) for o in parts}
iw = np.array(arm.matrix_world.inverted())
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
for side in ("Left", "Right"):
    S, Wr = W(side + "Arm"), W(side + "Hand")
    xs, xw = abs(S.x), abs(Wr.x)
    add = np.array(Wr - S) * (K - 1)
    for o in parts:
        arm_shift(Vs[o], side, add)
    eb = [b for b in arm.data.edit_bones if b.name.startswith("mixamorig:" + side) and any(k in b.name for k in ("Arm", "Hand"))]
    for b in eb:
        b.use_connect = False
    for b in eb:                                   # 머리·꼬리를 세계 좌표로 옮겼다가 되돌린다 (뼈대는 x 축으로 90° 돌아 있다)
        for end in ("head", "tail"):
            p = np.array([arm.matrix_world @ getattr(b, end)]); arm_shift(p, side, add)
            setattr(b, end, Vector((iw @ np.append(p[0], 1))[:3]))
bpy.ops.object.mode_set(mode="OBJECT")
for o in parts:
    put(o, Vs[o])
up2, fo2 = arm.data.bones["mixamorig:LeftArm"].length, arm.data.bones["mixamorig:LeftForeArm"].length
wrist_hang = W("LeftArm").z - (up2 + fo2)
hv = []
for o in parts:
    hand_g = [g.index for g in o.vertex_groups if g.name.startswith("mixamorig:LeftHand")]
    hv += [Vs[o][v.index] for v in o.data.vertices if any(g.group in hand_g and g.weight > 0.5 for g in v.groups)]
hv = np.array(hv)
tip_hang = wrist_hang - (hv[:, 0].max() - W("LeftHand").x)
print("ARM_K %.3f  팔 %.3f → %.3f m  늘어뜨리면 손목 %.2f m (무릎 %.2f) · 발톱 끝 %.2f m (발목 %.2f)" % (K, up + fo, up2 + fo2, wrist_hang, knee_z, tip_hang, W("LeftFoot").z))
check(abs(wrist_hang - knee_z) <= 0.03, "손목이 무릎 높이: 늘어뜨린 손목 %.3f m = 무릎 %.3f ± 0.03" % (wrist_hang, knee_z))
check(W("LeftFoot").z <= tip_hang <= knee_z, "발톱 끝이 정강이 안: %.3f m (발목 %.3f ~ 무릎 %.3f)" % (tip_hang, W("LeftFoot").z, knee_z))
check(abs(hv[:, 0].min() - W("LeftHand").x) <= 0.08, "손 살이 손 뼈를 따라감: 손 살 시작 x %.3f · 손목 뼈 x %.3f (≤ 0.08)" % (hv[:, 0].min(), W("LeftHand").x))

# ---- ④b 늘린 뒤의 겉에 잔금·잔결을 입히고 어둡게 (몸 그물만 굽고, 나머지는 색만 곱한다)
# 까닭(사용자 09-20): 팔을 1.47배 늘리니 가슴·팔·전완의 그림이 늘어져 밋밋하다 + 비늘을 지우며 피부 잔금도 사라졌다(배포물 구조값 24.8 < 28) + 램프에 하얗게 탄다(4.84 %).
# 무늬를 UV 가 아니라 **늘린 뒤의 3D 자리**(물체 좌표)에서 만들어 구우면 늘어나지 않는다.
DARK = float(os.environ.get("DARK", "0.45")); DETAIL = os.environ.get("SABOTAGE") != "nodetail"
def principled(m): return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 4
try:
    cp = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        cp.compute_device_type = kind; cp.get_devices()
        if any(d.type == kind for d in cp.devices):
            for d in cp.devices:
                d.use = True
            sc.cycles.device = "GPU"; break
except Exception as e:
    print("GPU 없음 — CPU 로 굽는다", e)
for o in parts:
    m = o.data.materials[0]; nt = m.node_tree; bs = principled(m)
    base_link = bs.inputs["Base Color"].links[0] if bs.inputs["Base Color"].links else None
    if want[o][0] != "Miner_Body" or base_link is None:
        if base_link is not None:                 # 색만 곱한다 — glTF 내보내기가 baseColorFactor 로 옮긴다
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
            nt.links.new(base_link.from_socket, mix.inputs[6]); mix.inputs[7].default_value = (DARK, DARK, DARK, 1); nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
        continue
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.feature = "DISTANCE_TO_EDGE"; vor.inputs["Scale"].default_value = 38.0      # 잔금 칸 2.6 cm 쯤 (모델 m)
    noi = nt.nodes.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 260.0; noi.inputs["Detail"].default_value = 4.0
    warp = nt.nodes.new("ShaderNodeTexNoise"); warp.inputs["Scale"].default_value = 9.0
    wmix = nt.nodes.new("ShaderNodeMix"); wmix.data_type = "VECTOR"; wmix.inputs[0].default_value = 0.06
    nt.links.new(tc.outputs["Object"], wmix.inputs[4]); nt.links.new(warp.outputs["Color"], wmix.inputs[5]); nt.links.new(tc.outputs["Object"], warp.inputs["Vector"])
    nt.links.new(wmix.outputs[1], vor.inputs["Vector"]); nt.links.new(tc.outputs["Object"], noi.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs[1].default_value = 0.0; ramp.inputs[2].default_value = 0.035; ramp.clamp = True   # 0 = 금 속, 1 = 칸 안
    nt.links.new(vor.outputs["Distance"], ramp.inputs[0])
    h = nt.nodes.new("ShaderNodeMath"); h.operation = "ADD"; nt.links.new(ramp.outputs[0], h.inputs[0])
    hn = nt.nodes.new("ShaderNodeMath"); hn.operation = "MULTIPLY"; hn.inputs[1].default_value = 0.35; nt.links.new(noi.outputs["Fac"], hn.inputs[0]); nt.links.new(hn.outputs[0], h.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8 if DETAIL else 0.0; bump.inputs["Distance"].default_value = 0.004
    nt.links.new(h.outputs[0], bump.inputs["Height"])
    nmap = next((n for n in nt.nodes if n.type == "NORMAL_MAP"), None)
    if nmap:
        nt.links.new(nmap.outputs[0], bump.inputs["Normal"])
    nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    dk = nt.nodes.new("ShaderNodeMapRange"); dk.inputs[3].default_value = DARK * (0.45 if DETAIL else 1.0); dk.inputs[4].default_value = DARK   # 금 속은 더 어둡게
    nt.links.new(ramp.outputs[0], dk.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
    nt.links.new(base_link.from_socket, mix.inputs[6]); nt.links.new(dk.outputs[0], mix.inputs[7]); nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    baked = {}
    for kind, cs in (("NORMAL", "Non-Color"), ("DIFFUSE", "sRGB")):
        im = bpy.data.images.new("skin_body_%s_detail" % kind.lower(), 2048, 2048, alpha=False); im.colorspace_settings.name = cs
        for n in nt.nodes:
            n.select = False
        node = nt.nodes.new("ShaderNodeTexImage"); node.image = im; node.select = True; nt.nodes.active = node   # 고른 뒤에 활성으로 — 순서가 바뀌면 "No active and selected image texture node"
        if kind == "DIFFUSE":
            bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=16)
        else:
            bpy.ops.object.bake(type="NORMAL", margin=16)
        px = np.empty(2048 * 2048 * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4); print("baked", kind, "min", px.min(0).round(3), "max", px.max(0).round(3), "engine", sc.render.engine, "device", sc.cycles.device)
        im.filepath_raw = os.path.join(MT, "mesh", "meshy_%s_body_%s_detail.png" % (BODY, kind.lower())); im.file_format = "PNG"; im.save(); im.pack()
        baked[kind] = node
    if nmap is None:
        nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(baked["NORMAL"].outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs[0], bs.inputs["Normal"])
    nt.links.new(baked["DIFFUSE"].outputs["Color"], bs.inputs["Base Color"])
    # 검사: 늘린 위팔 자리의 노멀맵에 잔결이 있는가 — 위팔 면들의 UV 가운데에서 노멀 픽셀을 뽑아 흩어짐을 잰다
    a = np.empty(2048 * 2048 * 4, np.float32); baked["NORMAL"].image.pixels.foreach_get(a); a = a.reshape(2048, 2048, 4)
    V0 = co(o); uvd = o.data.uv_layers.active.data; smp = []
    for poly in o.data.polygons:
        c = V0[list(poly.vertices)].mean(0)
        if 0.55 < c[0] < 1.2:                     # 왼 위팔~전완 (늘린 자리)
            u = np.mean([uvd[i].uv for i in poly.loop_indices], axis=0); smp.append(a[int(u[1] % 1 * 2047), int(u[0] % 1 * 2047), :2])
    spread = float(np.std(np.array(smp), axis=0).mean())
    check(spread >= 0.03, "늘린 팔 겉에 잔결이 있다: 팔 면 %d 개의 노멀 픽셀 흩어짐 %.3f (≥ 0.03)" % (len(smp), spread))

# ---- ⑤ 옛 것 빼고 새 그물들을 제 이름으로
for o in list(bpy.data.objects):
    if o not in parts and (o.name in ("Miner_Body", "Miner_Head") or o.name.split("_")[0] in ("Plank", "Nail", "Strap")):
        bpy.data.objects.remove(o, do_unlink=True)
for o in parts:
    o.name, o.data.materials[0].name = want[o]; o.data.name = o.name + "_" + BODY
    o.parent = arm
    if os.environ.get("SABOTAGE") != "noinv":
        o.matrix_parent_inverse = arm.matrix_world.inverted()      # 뼈대가 x 축으로 90° 돌아 있다 — 안 하면 살이 같이 돈다
    o.modifiers.new("Armature", "ARMATURE").object = arm
    o.data.materials[0].use_backface_culling = True               # 한 면만 — 뒷면은 안감 그물이 맡는다
arm.data.pose_position = "POSE"

# 자세를 잡았을 때 살이 뼈를 따라가는가 (09-20: 부모 역행렬을 빼먹어 살이 산산이 흩어진 것을 위 검사들이 못 잡았다)
ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
act = bpy.data.actions["idle_crouch"]; ad.action = act
if hasattr(ad, "action_slot") and act.slots:
    ad.action_slot = act.slots[0]
bpy.context.scene.frame_set(30)
dg = bpy.context.evaluated_depsgraph_get(); far = 0.0
for o in parts:
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    P = np.array([o.matrix_world @ v.co for v in me.vertices]); ev.to_mesh_clear()
    gname = [g.name for g in o.vertex_groups]
    for i in range(0, len(P), 37):
        v = o.data.vertices[i]; g = max(v.groups, key=lambda g: g.weight); pb = arm.pose.bones[gname[g.group]]
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
