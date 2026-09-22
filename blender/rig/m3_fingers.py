"""m3 손: 손가락 뼈를 새 손(Miner_Hands)의 손가락 다섯 개에 맞추고, 손 살을 손가락마다 제 뼈에 붙인다 (제안서 docs/제안서_m3_손가락_뼈.md, 09-20 승인).
  blender -b --factory-startup -P blender/rig/m3_fingers.py
입력: Documents/MineTunnel/blender/miner_v5_stage17_m3.blend (m2_body.py 산출 — 손은 손 뼈에 통짜, 손가락 뼈는 옛 손 자리. 안 고친다)
출력: Documents/MineTunnel/blender/miner_v5_stage18_m3_fingers.blend → SRC_BLEND 로 walk_knuckle.py 에 (tools/bake_m3.sh)
하는 일: ① 마디 자리 = 아래 표(왼손, 손 뼈 머리 기준, 그림 보고 찍음) → 가까운 살의 가운데로 조금 당김 · 발톱 끝은 살 점에 붙임. 오른손은 거울
        ② 손 뼈 + 손가락 뼈만 켜고 Blender 자동 무게(점을 붙인 사본에서) → 원래 점으로 옮김 ③ 발톱(셋째 마디 무게 0.75 넘는 점)은 셋째 마디에 통짜 — 발톱은 안 휜다. 손가락 사이를 딱 자르지 않는다(엄지·검지 살이 붙어 있어 경계 변이 찢긴다)
끝뼈(…4) 머리 = 발톱 끝: walk_knuckle.py 와 Unity 팔 들기 안전망이 이 점을 발톱 끝으로 쓴다.
사보타주: SABOTAGE=oldfingers(뼈 안 옮김) -> 검사 1 FAIL · solidhand(무게 안 바꿈) -> 검사 4 FAIL · nearweights(가까운 뼈에 그냥 붙임 — 09-20 리본) -> 검사 2·3 FAIL"""
import bpy, bmesh, os, sys, math, numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage17_m3.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage18_m3_fingers.blend"))
SHOTS = os.environ.get("SHOTS", "")               # 그림 폴더 (비우면 안 찍는다)
SABOTAGE = os.environ.get("SABOTAGE", "")
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
# 왼손 마디 자리 (m, 세계 좌표 − 왼손 뼈 머리). 손가락 뿌리 · 가운데 마디 · 발톱 뿌리 · 발톱 끝. 2 cm 눈금 그림(위·옆)에서 읽은 값 — 표가 틀리면 검사 1 이 잡는다
JOINTS = {
    "Thumb":  [(0.095, -0.095, 0.004), (0.195, -0.110, -0.006), (0.281, -0.128, -0.069), (0.221, -0.048, -0.175)],
    "Index":  [(0.155, -0.082, 0.004), (0.220, -0.095, -0.006), (0.301, -0.098, -0.016), (0.423, -0.058, -0.191)],
    "Middle": [(0.147, -0.048, 0.021), (0.221, -0.056, 0.021), (0.329, -0.052, 0.021), (0.509, -0.013, -0.139)],
    "Ring":   [(0.151, -0.026, 0.031), (0.222, -0.022, 0.034), (0.297, -0.002, 0.049), (0.512, 0.066, -0.051)],
    "Pinky":  [(0.135, 0.004, 0.009), (0.185, 0.032, -0.009), (0.223, 0.045, -0.041), (0.272, 0.036, -0.111)],
}

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
arm = bpy.data.objects["Miner_Rig"]; hands = bpy.data.objects["Miner_Hands"]
A = arm.matrix_world; Ai = A.inverted()
P = "mixamorig:"
def fb(side, f, i): return "%s%sHand%s%d" % (P, side, f, i)
def world_co(o, deformed=False):
    if deformed:
        ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
        V = np.array([o.matrix_world @ v.co for v in me.vertices]); ev.to_mesh_clear(); return V
    return np.array([o.matrix_world @ v.co for v in o.data.vertices])

arm.data.pose_position = "REST"; bpy.context.view_layer.update()
V0 = world_co(hands)
rest_before = world_co(hands, True)

# 점을 붙인 사본 (Meshy 그물은 면마다 점이 따로다 — 붙이면 좌우 한 덩어리씩)
weld = hands.copy(); weld.data = hands.data.copy(); bpy.context.scene.collection.objects.link(weld)
for md in list(weld.modifiers):
    weld.modifiers.remove(md)
weld.parent = None; weld.matrix_world = hands.matrix_world
bm = bmesh.new(); bm.from_mesh(weld.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(weld.data); bm.free()
weld.vertex_groups.clear()
VW = world_co(weld)
kd = KDTree(len(VW))
for i, p in enumerate(VW):
    kd.insert(p, i)
kd.balance()
bvh = BVHTree.FromObject(weld, bpy.context.evaluated_depsgraph_get())      # 사본은 세계 = 제 좌표 (부모 없음, 변환은 hands 것) — 아래에서 세계 좌표로 묻는다
Wi = weld.matrix_world.inverted()

# ---- ① 마디 자리
joints = {}
for side in ("Left", "Right"):
    sx = 1 if side == "Left" else -1
    h0 = A @ arm.data.bones[P + side + "Hand"].head_local
    for f in FINGERS:
        pts = [h0 + Vector((sx * x, y, z)) for x, y, z in JOINTS[f]]
        for k in range(3):                         # 살 가운데로: 반지름 1.5 cm 안 점들의 평균 쪽으로 두 번, 모두 합쳐 1 cm 까지만
            p = pts[k].copy()
            for _ in range(2):
                near = [VW[i] for _, i, _ in kd.find_range(p, 0.015)]
                if len(near) >= 8:
                    p = Vector(np.mean(near, axis=0))
            d = p - pts[k]
            pts[k] = pts[k] + d * min(1.0, 0.01 / max(d.length, 1e-9))
        near = [Vector(VW[i]) for _, i, _ in kd.find_range(pts[3], 0.03)]   # 발톱 끝 = 찍은 자리 3 cm 안에서 발톱 뿌리로부터 가장 먼 살 점
        if near:
            pts[3] = max(near, key=lambda q: (q - pts[2]).length)
        joints[side, f] = pts

if SABOTAGE != "oldfingers":
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for (side, f), pts in joints.items():
        chain = [eb[fb(side, f, i)] for i in (1, 2, 3, 4)]
        old = [(b.y_axis.copy(), b.z_axis.copy()) for b in chain]
        for b in chain:
            b.use_connect = False
        ends = pts + [pts[3] + (pts[3] - pts[2]).normalized() * 0.03]
        for i, b in enumerate(chain):
            b.head, b.tail = Ai @ ends[i], Ai @ ends[i + 1]
            # 옛 축을 새 방향으로 가장 짧게 돌린 자리에 맞춘다 — 모션캡처 클립의 손가락 키(옛 뼈 축 기준)가 되도록 같은 쪽으로 굽게
            b.align_roll(old[i][0].rotation_difference(b.y_axis) @ old[i][1])
    bpy.ops.object.mode_set(mode="OBJECT")

# ---- ② ③ 무게
hand_bones = [P + s + "Hand" for s in ("Left", "Right")] + [fb(s, f, i) for s in ("Left", "Right") for f in FINGERS for i in (1, 2, 3)]
if SABOTAGE != "solidhand":
    deform = {b.name: b.use_deform for b in arm.data.bones}
    for b in arm.data.bones:
        b.use_deform = b.name in hand_bones
    if SABOTAGE == "nearweights":                 # 가까운 뼈 선분에 통째로 (옆 손가락 뼈를 잡는다)
        seg = [(n, A @ arm.data.bones[n].head_local, A @ arm.data.bones[n].tail_local) for n in hand_bones]
        for n in hand_bones:
            weld.vertex_groups.new(name=n)
        for i, p in enumerate(VW):
            p = Vector(p)
            def dist(s):
                a, b = s[1], s[2]; t = max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared)); return (p - (a + (b - a) * t)).length
            weld.vertex_groups[min(seg, key=dist)[0]].add([i], 1.0, "REPLACE")
    else:
        bpy.ops.object.select_all(action="DESELECT"); weld.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for b in arm.data.bones:
        b.use_deform = deform[b.name]
    gi = {g.index: g.name for g in weld.vertex_groups}
    Wt = np.zeros((len(VW), len(hand_bones))); col = {n: k for k, n in enumerate(hand_bones)}
    for v in weld.data.vertices:
        for g in v.groups:
            if gi[g.group] in col:
                Wt[v.index, col[gi[g.group]]] = g.weight
    check((Wt.sum(1) > 0.5).all(), "자동 무게가 모든 손 점에 닿았다 (무게 없는 점 %d / %d)" % ((Wt.sum(1) <= 0.5).sum(), len(VW)))
    digit = np.array([-1, -1] + [d for d in range(10) for _ in range(3)])          # 열 → 손가락 번호 (손 뼈 −1)
    third = np.array([n[-1] == "3" and "Hand" in n[:-1] and n not in hand_bones[:2] for n in hand_bones])
    if SABOTAGE != "nearweights":
        for k in np.where(third)[0]:              # ③ 발톱은 단단하다: 셋째 마디 무게 0.25~0.75 를 0~1 로 편다 (딱 자르면 경계 변이 17배 늘어났다)
            w = Wt[:, k].copy(); w2 = np.clip((w - 0.25) / 0.5, 0, 1); m = w < 1
            Wt[m] *= ((1 - w2[m]) / (1 - w[m]))[:, None]; Wt[:, k] = w2
        # 엄지·검지 살이 붙은 자리는 자동 무게가 이웃 점끼리 크게 달라 변이 3~4배 늘어난다 → 이웃 평균으로 몇 번 고르게 (단단한 발톱 점은 그대로)
        we = np.array([e.vertices[:] for e in weld.data.edges]); hard = Wt[:, third].max(1) >= 1.0
        for _ in range(int(os.environ.get("SMOOTH", "4"))):
            acc = np.zeros_like(Wt); cnt = np.zeros(len(Wt))
            np.add.at(acc, we[:, 0], Wt[we[:, 1]]); np.add.at(acc, we[:, 1], Wt[we[:, 0]]); np.add.at(cnt, we[:, 0], 1); np.add.at(cnt, we[:, 1], 1)
            new = 0.5 * Wt + 0.5 * acc / np.maximum(cnt, 1)[:, None]; new[hard] = Wt[hard]; Wt = new
    top = np.argsort(-Wt, axis=1)[:, 4:]          # Unity 는 점마다 뼈 4개
    np.put_along_axis(Wt, top, 0, axis=1)
    Wt /= Wt.sum(1, keepdims=True)
    hands.vertex_groups.clear()
    groups = [hands.vertex_groups.new(name=n) for n in hand_bones]
    src = np.array([kd.find(Vector(p))[1] for p in V0])
    for k, g in enumerate(groups):
        w = Wt[src, k]
        for val in np.unique(w[w > 1e-4].round(3)):
            g.add([int(i) for i in np.where(w.round(3) == val)[0]], float(val), "REPLACE")
    bpy.ops.object.select_all(action="DESELECT"); hands.select_set(True); bpy.context.view_layer.objects.active = hands
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
bpy.data.objects.remove(weld, do_unlink=True)

# ---- 검사
bones = arm.data.bones
# 1. 마디가 살 안에
worst_out = worst_tip = 0.0
for side in ("Left", "Right"):
    for f in FINGERS:
        for i in (1, 2, 3, 4):
            p = A @ bones[fb(side, f, i)].head_local
            loc, nor, _, d = bvh.find_nearest(Wi @ p)
            if i == 4:
                worst_tip = max(worst_tip, d)
            elif (Wi @ p - loc).dot(nor) > 0:      # 겉 밖
                worst_out = max(worst_out, d)
check(worst_out <= 0.005 and worst_tip <= 0.005, "마디 30점이 손 살 안(밖으로 가장 많이 나간 %.4f m ≤ 0.005) · 발톱 끝 10점이 살 점에(가장 먼 %.4f m ≤ 0.005)" % (worst_out, worst_tip))

gname = [g.name for g in hands.vertex_groups]
Wh = np.zeros((len(V0), len(gname)))
for v in hands.data.vertices:
    for g in v.groups:
        Wh[v.index, g.group] = g.weight
def cols(side, f, which=(1, 2, 3)):
    return [gname.index(fb(side, f, i)) for i in which if fb(side, f, i) in gname]
# 2. 발톱(셋째 마디 주인)에 다른 손가락 무게가 없다
leak = n_claw = 0
claw_v = {}
for side in ("Left", "Right"):
    for f in FINGERS:
        c3 = cols(side, f, (3,))
        m = Wh[:, c3].sum(1) > 0.5 if c3 else np.zeros(len(V0), bool)
        claw_v[side, f] = m; n_claw += m.sum()
        other = [c for s2 in ("Left", "Right") for f2 in FINGERS if (s2, f2) != (side, f) for c in cols(s2, f2)]
        leak += (Wh[np.ix_(m, other)].sum(1) > 0.05).sum() if other else 0
check(n_claw >= 10000 and leak == 0, "발톱 살은 제 손가락 뼈에만: 발톱 점 %d개(≥ 10000) 중 다른 손가락 무게가 0.05 넘는 점 %d개" % (n_claw, leak))

# 굽힘 시험 자세: 마디마다 30°, 손 뼈의 X 축으로 (walk_knuckle.py 와 같은 축) — 끝이 내려가는 쪽
arm.data.pose_position = "POSE"
ad = arm.animation_data; keep = ad.action if ad else None
if ad:
    ad.action = None
    for tr in ad.nla_tracks:
        tr.mute = True
def reset():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
def bend(side, f, deg, ax):
    for i in (1, 2, 3):
        pb = arm.pose.bones[fb(side, f, i)]; Wm = A @ pb.matrix; h = Wm.translation
        pb.matrix = Ai @ (Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, ax) @ Matrix.Translation(-h) @ Wm)
        bpy.context.view_layer.update()
def curl(deg):
    """모든 손가락을 같은 쪽으로 — 쪽은 walk_knuckle.py 처럼 가운뎃손가락 끝이 내려가는 쪽 (엄지·새끼 발톱은 뒤로 말려 있어 제 끝으로는 못 정한다)"""
    reset()
    for side in ("Left", "Right"):
        ax = (A @ arm.pose.bones[P + side + "Hand"].matrix).to_3x3().col[0]
        tip = arm.pose.bones[fb(side, "Middle", 4)]; z0 = (A @ tip.head).z
        bend(side, "Middle", 20, ax); sg = 1 if (A @ tip.head).z < z0 else -1
        for i in (1, 2, 3):
            arm.pose.bones[fb(side, "Middle", i)].matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for f in FINGERS:
            bend(side, f, sg * deg, ax)
reset()
rest_after = world_co(hands, True)
tip_v = {k: int(np.argmin(np.linalg.norm(rest_after - np.array(A @ bones[fb(k[0], k[1], 4)].head_local), axis=1))) for k in joints}
curl(30)
bent = world_co(hands, True)
ed = np.array([e.vertices[:] for e in hands.data.edges])
L0 = np.linalg.norm(rest_after[ed[:, 0]] - rest_after[ed[:, 1]], axis=1); L1 = np.linalg.norm(bent[ed[:, 0]] - bent[ed[:, 1]], axis=1)
long_ = L0 > 0.002                                # 아주 짧은 변은 비가 튄다
stretch = float((L1[long_] / L0[long_]).max())
print("2.5배 넘게 늘어난 변 %d / %d" % ((L1[long_] / L0[long_] > 2.5).sum(), long_.sum()))
print("발톱 끝이 움직인 거리", {k: round(float(np.linalg.norm(bent[tip_v[k]] - rest_after[tip_v[k]])), 3) for k in joints})
# Meshy 그물은 면마다 점이 따로 — 같은 자리 점들이 굽힌 뒤 벌어지면 그것이 찢김이다
src_all = {}
for i, p in enumerate(np.round(rest_after, 5)):
    src_all.setdefault(tuple(p), []).append(i)
split = max((float(np.ptp(bent[ix], axis=0).max()) for ix in src_all.values() if len(ix) > 1), default=0.0)
grow = float((L1 - L0).max())
# 잣대는 늘어난 **길이**: 엄지·검지 살이 붙은 자리의 2~3 mm 변은 3~4배 늘어도 1 cm 가 안 된다(그림 03_curl_30 에서 안 보임). 리본 찢김(nearweights)은 수 cm
check(grow <= 0.015 and split <= 0.001, "30° 굽혀도 안 찢긴다: 가장 많이 늘어난 변 +%.4f m (≤ 0.015; 비로는 %.2f배) · 같은 자리 점이 벌어진 거리 %.4f m (≤ 0.001)" % (grow, stretch, split))
follow = max(abs(float(np.linalg.norm(bent[tip_v[k]] - np.array(A @ arm.pose.bones[fb(k[0], k[1], 4)].head))) - float(np.linalg.norm(rest_after[tip_v[k]] - np.array(A @ bones[fb(k[0], k[1], 4)].head_local)))) for k in joints)
moved = min(float(np.linalg.norm(bent[tip_v[k]] - rest_after[tip_v[k]])) for k in joints)
check(follow <= 0.01 and moved >= 0.03, "손가락이 실제로 굽는다: 30° 에서 발톱 끝 살이 끝뼈를 따라감(어긋남 %.4f m ≤ 0.01) · 가장 덜 움직인 발톱 끝 %.3f m (≥ 0.03)" % (follow, moved))
check(float(np.abs(rest_after - rest_before).max()) < 1e-4, "쉬는 자세의 손 모양이 그대로: 가장 많이 움직인 점 %.6f m (< 0.0001)" % float(np.abs(rest_after - rest_before).max()))

if SHOTS:
    os.makedirs(SHOTS, exist_ok=True)
    ns = bpy.data.scenes.new("shots"); bpy.context.window.scene = ns
    ns.collection.objects.link(hands); ns.collection.objects.link(arm)
    hm = bpy.data.materials.new("shot_hand"); hm.diffuse_color = (0.8, 0.8, 0.75, 1)
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam")); ns.collection.objects.link(cam); ns.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.75
    ns.render.engine = "BLENDER_WORKBENCH"; ns.render.resolution_x = 1100; ns.render.resolution_y = 700
    ns.display.shading.light = "STUDIO"; ns.display.shading.color_type = "SINGLE"; ns.display.shading.single_color = (0.8, 0.8, 0.75); ns.display.shading.show_cavity = True
    views = (("top", (1.78, -0.05, 4), (0, 0, 0)), ("side", (1.78, -4, 1.70), (math.pi / 2, 0, 0)))
    sticks = []
    palette = dict(Thumb=(1, 0, 0, 1), Index=(1, 0.5, 0, 1), Middle=(1, 1, 0, 1), Ring=(0, 1, 0, 1), Pinky=(0, 0.5, 1, 1))
    for f in FINGERS:
        cu = bpy.data.curves.new("stick", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.004
        sp = cu.splines.new("POLY"); sp.points.add(3)
        for p, i in zip(sp.points, (1, 2, 3, 4)):
            p.co = (*(A @ bones[fb("Left", f, i)].head_local), 1)
        ob = bpy.data.objects.new("stick", cu); ns.collection.objects.link(ob); ob.color = palette[f]; sticks.append(ob)
    reset()
    ns.display.shading.show_xray = True; ns.display.shading.xray_alpha = 0.45; ns.display.shading.color_type = "OBJECT"; hands.color = (0.8, 0.8, 0.75, 1)
    for nm, loc, rot in views:
        cam.location, cam.rotation_euler = loc, rot
        ns.render.filepath = os.path.join(SHOTS, "02_hand_bones_after_%s.png" % nm); bpy.ops.render.render(write_still=True, scene=ns.name)
    ns.display.shading.show_xray = False
    for ob in sticks:
        ob.hide_render = True
    for deg in (0, 30, 60):
        curl(deg)
        for nm, loc, rot in views:
            cam.location, cam.rotation_euler = loc, rot
            ns.render.filepath = os.path.join(SHOTS, "03_curl_%02d_%s.png" % (deg, nm)); bpy.ops.render.render(write_still=True, scene=ns.name)
    for ob in sticks:
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.context.window.scene = next(s for s in bpy.data.scenes if s != ns)
    bpy.data.scenes.remove(ns)

reset()
if ad:
    ad.action = keep
    for tr in ad.nla_tracks:
        tr.mute = False
if fails:
    sys.exit("m3_fingers FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_fingers ALL PASS →", OUT)
