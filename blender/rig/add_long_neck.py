"""add_long_neck — 몸 속에 등뼈를 따라 누운 긴 목(마디 7개 관)을 넣는다 (제안서 docs/제안서_3D3b_M1e_목_길게_빼기.md, 승인 2026-09-19).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/add_long_neck.py
입력: Documents/MineTunnel/blender/miner_v4_stage15_timber.blend — 안 고친다
출력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend → blender/anim/walk_knuckle.py 가 이것을 읽어 GLB 를 굽는다
하는 일: ① 머리 뼈와 몸 뼈 양쪽에 걸쳐 붙은 살 점을 더 센 쪽 한 곳으로 (머리를 밀면 고무막처럼 늘어나던 것)
        ② 머리 쪽 점과 몸 쪽 점을 잇는 면: 머리 쪽 점을 복사해 몸 쪽에 붙인다 → 면이 몸에 남아 목 나오는 곳의 살 옷깃이 된다 (쉬는 모양은 그대로)
        ③ 뼈 mixamorig:NeckExt_0~6 (부모 Spine2, 서로 안 이음 — Unity StalkerAnim.NeckOut 이 매 프레임 "머리 → 나오는 곳 → 등뼈" 길 위에 놓는다)
        ④ 목 관 Miner_Neck: 머리 속 3 cm 에서 등뼈를 따라 아래로 83 cm, 굵기 8.5 → 11 cm, 등 쪽 등뼈 돌기·앞쪽 힘줄 줄·마디 잘록함,
           머리 밑 마개(머리 뼈)와 목구멍 마개(가슴 뼈). 재질 = 몸 살 그대로(새 그림 없음), UV 는 등 살 한 조각을 접어 가며 빌린다
        ⑤ 자기 검사
쉬는 자세 = 목을 안 뺀 자세 (관 전체가 몸 속). 길·마디 자리 셈은 Unity 와 같다: 관 꼭대기에서 잰 길이 s, 마디 i 는 s = TOP_IN + i × LINK
사보타주: SABOTAGE=flip -> 관 면을 거꾸로 감는다 (검사 "뒤집힌 면" FAIL). SABOTAGE=nocut -> ①② 를 안 한다 (검사 "머리를 밀어도 살이 안 늘어남" FAIL). SABOTAGE=nocap -> 마개를 안 만든다 (검사 "밑에서 올려다본 광선" FAIL). 사보타주 실행은 blend 를 저장하지 않는다"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.path.join(MT, "blender", "miner_v4_stage15_timber.blend")
OUT = os.path.join(MT, "blender", "miner_v4_stage16_neck.blend")
SABOTAGE = os.environ.get("SABOTAGE", "")
P = "mixamorig:"
JOINTS = 7                               # Tuning.STALKER_NECK_JOINTS
NECK_LEN = 0.80                          # Tuning.STALKER_NECK_LEN_M (모델 크기 1 기준 m)
TOP_IN = 0.03                            # 관 꼭대기는 머리 뼈 뿌리에서 머리 속으로 이만큼 (Tuning.STALKER_NECK_TOP_IN_M)
LINK = NECK_LEN / JOINTS
R_HEAD, R_BASE = 0.0425, 0.055           # 관 반지름: 머리 쪽 → 몸 속 끝
SIDES, STEP = 20, 0.01
PATCH = dict(x0=-0.17, z0=1.45, w=0.10, h=0.25)   # UV 를 빌릴 등 살 조각 (판자 x 0~0.47 을 피해 왼쪽 등)
NECK_SHARE = 0.4                         # Tuning.STALKER_HEAD_NECK_SHARE
CAP_K = float(os.environ.get("CAP_K", "1.3"))   # 머리 밑 마개 반지름 = 구멍(잇는 면 고리 90 %) × 이 값 — 구멍이 둥글지 않아 1.0 은 비스듬히 보면 192 중 20 이 샜다
AUTO_OUT = 0.25                          # Tuning.STALKER_NECK_TILT_OUT_M — 갸웃 110° 에서 파고듦 0 이 되는 길이 (09-19: 얼굴 쪽 + 위 0.4 방향으로 20 cm 는 옆 90° 에서 12점 남음, 25 cm 는 다섯 자세 0)
OUT_UP = 0.4                             # Tuning.STALKER_NECK_UP — 빼는 방향 = 얼굴이 보는 쪽 + 위 × 이 값 (위로만 빼면 갱도 천장을 뚫는다, 09-19 게임 그림)

fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
arm = bpy.data.objects["Miner_Rig"]; body = bpy.data.objects["Miner_Body"]; head = bpy.data.objects["Miner_Head"]
M, Mi = arm.matrix_world.copy(), arm.matrix_world.inverted()
ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
ad.action = None
arm.data.pose_position = "POSE"
def reset_pose():
    for p in arm.pose.bones:
        p.rotation_mode = "QUATERNION"; p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0); p.scale = (1, 1, 1)
    bpy.context.view_layer.update()
reset_pose()
def eval_co(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh(); co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    return (np.array(o.matrix_world) @ np.c_[co, np.ones(len(co))].T).T[:, :3]
before = {o.name: eval_co(o) for o in (head, body)}
n_bones0 = len(arm.data.bones)

# ---- ①② 걸친 살 나누기 + 잇는 면을 몸 쪽에 남기기
HEADSIDE = ("Head", "Jaw", "JawTip", "HeadTop_End")
ring_head, ring_body = [], []            # 잇는 면의 머리 쪽 점·몸 쪽 점 (쉬는 자세 세상 좌표) — 마개 크기
stats = {}
for ob in (head, body):
    hgs = {ob.vertex_groups[P + n].index for n in HEADSIDE if ob.vertex_groups.get(P + n)}
    if SABOTAGE == "nocut":
        break
    to_head, to_body = [], []
    for v in ob.data.vertices:
        wh = sum(g.weight for g in v.groups if g.group in hgs); wb = sum(g.weight for g in v.groups if g.group not in hgs)
        if wh > 1e-6 and wb > 1e-6:                                                       # 조금이라도 걸쳐 있으면 (0.9 % 만 걸쳐도 60 cm 밀면 5 mm 끌려간다)
            (to_head if wh >= wb else to_body).append(v.index)
    for vg in ob.vertex_groups:
        vg.remove(to_body if vg.index in hgs else to_head)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    dl = bm.verts.layers.deform.verify()
    is_head = lambda v: sum(w for g, w in v[dl].items() if g in hgs) >= 0.5
    side = {v.index: is_head(v) for v in bm.verts}
    bridge = [f for f in bm.faces if len({side[v.index] for v in f.verts}) == 2]
    dup = {}; old_edges = {e for f in bridge for e in f.edges}
    for f in bridge:
        src = min((v for v in f.verts if not side[v.index]), key=lambda v: v.index)      # 이 면의 몸 쪽 점 — 무게를 빌린다
        new_vs = []
        for v in f.verts:
            if side[v.index]:
                ring_head.append(ob.matrix_world @ v.co)
                if v.index not in dup:
                    nv = bm.verts.new(v.co, v); nv[dl].clear()
                    for g, w in src[dl].items():
                        nv[dl][g] = w
                    dup[v.index] = nv
                new_vs.append(dup[v.index])
            else:
                ring_body.append(ob.matrix_world @ v.co); new_vs.append(v)
        try:
            nf = bm.faces.new(new_vs, f)
        except ValueError:
            continue                                                                       # 같은 점 셋으로 이미 있는 면
        for ln, lo in zip(nf.loops, f.loops):
            ln.copy_from(lo)
        bm.faces.remove(f)
    for e in [e for e in old_edges if e.is_valid and e.is_wire]:                           # 옮긴 면이 남긴 빈 변만 (원래 있던 빈 변은 그대로)
        bm.edges.remove(e)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    stats[ob.name] = (len(to_head), len(to_body), len(bridge), len(dup))
    print("%s: 걸친 살 점 %d (머리 쪽 %d · 몸 쪽 %d) · 잇는 면 %d 개를 몸 쪽에 남김 (복사한 점 %d)" % (ob.name, len(to_head) + len(to_body), len(to_head), len(to_body), len(bridge), len(dup)))

# ---- 길: 관 꼭대기(머리 속) → 머리 뼈 뿌리 → 목 나오는 곳 → 등뼈 → 엉덩이 아래
def pbw(n): return M @ arm.pose.bones[P + n].matrix
def rest_path():
    hm = pbw("Head"); up = (hm.to_3x3() @ Vector((0, 1, 0))).normalized()
    pts = [hm.translation + up * TOP_IN] + [pbw(n).translation.copy() for n in ("Head", "Neck", "Spine2", "Spine1", "Spine", "Hips")]
    pts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.6)
    return pts
def resample(pts, step):
    out = [pts[0].copy()]; acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = (b - a).length
        if L < 1e-9:
            continue
        t = step - acc
        while t <= L + 1e-9:
            out.append(a + (b - a) * (t / L)); t += step
        acc = (acc + L) % step
    return out
TOTAL = TOP_IN + NECK_LEN
line = np.array(resample(rest_path(), STEP)[:int(round(TOTAL / STEP)) + 1])
# 꺾이는 곳(머리 뼈 → 목 → 가슴, 24° 쯤)에서 고리끼리 겹쳐 안쪽 면이 뒤집힌다 → 길을 ±3 cm 로 둥글린다 (양 끝은 그대로)
_pad = np.vstack([np.repeat(line[:1], 3, 0), line, np.repeat(line[-1:], 3, 0)])
line = np.stack([np.convolve(_pad[:, i], np.ones(7) / 7, "valid") for i in range(3)], 1)
s_arr = np.arange(len(line)) * STEP
bone_s = [TOP_IN + i * LINK for i in range(JOINTS)]
def at(s):
    i = min(int(s / STEP), len(line) - 2); f = s / STEP - i
    return Vector(line[i] * (1 - f) + line[i + 1] * f)

# ---- ③ 뼈
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects:
    o.select_set(o == arm)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for i, s in enumerate(bone_s):
    b = eb.new(P + "NeckExt_%d" % i); b.head = Mi @ at(s); b.tail = Mi @ at(max(0.0, s - 0.05)); b.roll = 0.0
    b.parent = eb[P + "Spine2"]; b.use_connect = False; b.use_deform = True
bpy.ops.object.mode_set(mode="OBJECT")
reset_pose()

# ---- ④ 관
def rings():
    out = []; nrm = Vector((1, 0, 0))
    for i in range(len(line)):
        t = Vector(line[min(i + 1, len(line) - 1)] - line[max(i - 1, 0)]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized(); bn = t.cross(nrm)      # nrm ≈ +x, bn ≈ ±y
        back = Vector((0, 1, 0)); back = (back - t * back.dot(t)).normalized()
        s = s_arr[i]; r0 = R_HEAD + (R_BASE - R_HEAD) * (s / TOTAL)
        ring = []
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES; d = nrm * math.cos(a) + bn * math.sin(a)
            ang = math.degrees(d.angle(back)); r = r0
            r *= 1 - 0.06 * sum(math.exp(-((s - bs) / 0.012) ** 2) for bs in bone_s[1:])                       # 마디 잘록함
            r += 0.008 * math.exp(-(ang / 28.0) ** 2) * (0.5 + 0.5 * math.cos(2 * math.pi * s / 0.038))            # 등 쪽 등뼈 돌기 (3.8 cm 마다)
            r += 0.003 * sum(math.exp(-((ang - c) / 9.0) ** 2) for c in (140.0, 165.0))                     # 앞쪽 힘줄 줄
            ring.append(Vector(line[i]) + d * r)
        out.append(ring)
    return out
rg = rings()
verts = [p for r in rg for p in r]; faces = []; arc = [s_arr[i] for i in range(len(rg)) for _ in range(SIDES)]; ang_k = [k for _ in rg for k in range(SIDES)]
for i in range(len(rg) - 1):
    for k in range(SIDES):
        faces.append((i * SIDES + k, i * SIDES + (k + 1) % SIDES, (i + 1) * SIDES + (k + 1) % SIDES, (i + 1) * SIDES + k))   # 겉면이 밖을 보게 (거꾸로 감으면 게임에서 새까맣다, 09-19)
if SABOTAGE == "flip":
    faces = [tuple(reversed(f)) for f in faces]
n_tube = len(verts)
# 몸 속 끝 막기
verts.append(Vector(line[-1])); arc.append(s_arr[-1]); ang_k.append(0)
for k in range(SIDES):
    faces.append((n_tube, (len(rg) - 1) * SIDES + k, (len(rg) - 1) * SIDES + (k + 1) % SIDES))
# 마개 둘: 머리 밑(머리 뼈, 아래를 봄) · 목구멍(가슴 뼈, 위를 봄)
def ring_stats(pts, fallback_z):
    pts = [p for p in pts if abs(p.x) < 0.2 and 1.9 < p.z < 2.2]
    if len(pts) < 8:
        return Vector((0, 0.07, fallback_z)), 0.08
    a = np.array(pts); c = a.mean(0); r = float(np.percentile(np.linalg.norm(a[:, :2] - c[:2], axis=1), 90))
    return Vector(c), r
hc, hr = ring_stats(ring_head, 2.04); bc, br = ring_stats(ring_body, 2.0)
caps = []                                 # (시작 번호, 점 수, 뼈)
for c, r, z, downward, bone in (() if SABOTAGE == "nocap" else ((hc, hr * CAP_K, hc.z + 0.02, True, "Head"), (bc, br, bc.z - 0.015, False, "Spine2"))):
    i0 = len(verts); verts.append(Vector((c.x, c.y, z + (0.01 if downward else -0.01)))); arc.append(0.0); ang_k.append(0)
    for k in range(24):
        a = 2 * math.pi * k / 24; verts.append(Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), z))); arc.append(r); ang_k.append(k)
    for k in range(24):
        a_, b_ = i0 + 1 + k, i0 + 1 + (k + 1) % 24
        faces.append((i0, b_, a_) if downward else (i0, a_, b_))
    caps.append((i0, 25, bone))
print("마개: 머리 밑 가운데 %s 반지름 %.3f · 목구멍 가운데 %s 반지름 %.3f" % (tuple(round(x, 3) for x in hc), hr, tuple(round(x, 3) for x in bc), br))

me = bpy.data.meshes.new("Miner_Neck"); me.from_pydata(verts, [], faces); me.update()
for p in me.polygons:
    p.use_smooth = True
neck = bpy.data.objects.new("Miner_Neck", me); scene.collection.objects.link(neck)
neck.parent = arm; neck.matrix_parent_inverse = body.matrix_parent_inverse.copy(); neck.matrix_basis = body.matrix_basis.copy()
bpy.context.view_layer.update()
me.transform(neck.matrix_world.inverted()); me.update()            # 점은 세상 좌표로 만들었다 → 몸 살과 같은 물체 공간으로
me.materials.append(body.data.materials[0])
# 무게: 마디 자리 사이를 곧게 섞는다
for i in range(JOINTS):
    neck.vertex_groups.new(name=P + "NeckExt_%d" % i)
for n in ("Head", "Spine2"):
    neck.vertex_groups.new(name=P + n)
cap_v = {}
for i0, n, bone in caps:
    for vi in range(i0, i0 + n):
        cap_v[vi] = bone
for vi in range(len(verts)):
    if vi in cap_v:
        neck.vertex_groups[P + cap_v[vi]].add([vi], 1.0, "REPLACE"); continue
    f = min(max((arc[vi] - TOP_IN) / LINK, 0.0), JOINTS - 1.0); lo = int(math.floor(f)); hi = min(lo + 1, JOINTS - 1); w = f - lo
    neck.vertex_groups[P + "NeckExt_%d" % lo].add([vi], 1.0 - w, "ADD")
    if w > 1e-6:
        neck.vertex_groups[P + "NeckExt_%d" % hi].add([vi], w, "ADD")
mod = neck.modifiers.new("Armature", "ARMATURE"); mod.object = arm

# UV: 등 살 조각을 좌우·위아래로 접어 가며(이음매 없이 되풀이) 빌린다 — 관 둘레·길이 → 조각 위 한 점 → 뒤에서 쏜 광선이 맞은 몸 살의 UV
bme = body.data; bme.calc_loop_triangles()
bco = [body.matrix_world @ v.co for v in bme.vertices]
tris = [tuple(t.vertices) for t in bme.loop_triangles]
tbvh = BVHTree.FromPolygons(bco, tris)
buv = bme.uv_layers.active.data
def pingpong(x, w):
    x = x % (2 * w); return x if x <= w else 2 * w - x
def patch_uv(u_m, v_m):
    px = PATCH["x0"] + pingpong(u_m, PATCH["w"]); pz = PATCH["z0"] + pingpong(v_m, PATCH["h"])
    loc, nor, ti, dist = tbvh.ray_cast(Vector((px, 1.0, pz)), Vector((0, -1, 0)))
    if loc is None:
        return None
    t = bme.loop_triangles[ti]; a, b, c = (bco[i] for i in t.vertices)
    n = (b - a).cross(c - a); den = n.dot(n)
    wa = (b - loc).cross(c - loc).dot(n) / den; wb = (c - loc).cross(a - loc).dot(n) / den; wc = 1 - wa - wb
    ua, ub, uc = (Vector(buv[l].uv) for l in t.loops)
    return ua * wa + ub * wb + uc * wc
uvl = me.uv_layers.new(name=bme.uv_layers.active.name)
circ = 2 * math.pi * R_BASE
miss = 0
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index
        if vi in cap_v:
            u_m, v_m = verts[vi].x - hc.x + 0.1, verts[vi].y - hc.y + 0.1
        else:
            k = ang_k[vi]
            if k == 0 and any(ang_k[me.loops[l2].vertex_index] > SIDES // 2 for l2 in poly.loop_indices):
                k = SIDES                                                                   # 둘레 이음매: 끝 칸은 0 이 아니라 한 바퀴
            u_m, v_m = circ * k / SIDES, arc[vi]
        uv = patch_uv(u_m, v_m)
        if uv is None:
            miss += 1; uv = Vector((0.5, 0.5))
        uvl.data[li].uv = uv
# UV 가 찢어진 면(살 그림의 다른 섬으로 건너뜀) 세기: 면의 UV 변 길이 ÷ 3D 변 길이가 가운데값의 6배 넘음
ratios = []
for poly in me.polygons:
    ls = list(poly.loop_indices); worst = 0.0
    for a_, b_ in zip(ls, ls[1:] + ls[:1]):
        d3 = (me.vertices[me.loops[a_].vertex_index].co - me.vertices[me.loops[b_].vertex_index].co).length
        if d3 > 1e-5:
            worst = max(worst, (Vector(uvl.data[a_].uv) - Vector(uvl.data[b_].uv)).length / d3)
    ratios.append(worst)
ratios = np.array(ratios); torn = int((ratios > 6 * np.median(ratios)).sum())

# ---- ⑤ 검사
check(len(arm.data.bones) == n_bones0 + JOINTS == 74, "뼈 %d → %d (74)" % (n_bones0, len(arm.data.bones)))
check(all(arm.data.bones[P + "NeckExt_%d" % i].parent.name == P + "Spine2" for i in range(JOINTS)), "목 마디 뼈 %d 개의 부모 = Spine2" % JOINTS)
after = {o.name: eval_co(o) for o in (head, body)}
d0 = max(float(np.abs(after[n][:len(before[n])] - before[n]).max()) for n in before)
check(d0 < 1e-4, "쉬는 자세에서 머리·몸 살 점 위치 그대로 (최대 차 %.6f m < 0.0001)" % d0)
# 관 겉면이 밖을 본다: 면 법선 · (면 가운데 − 가장 가까운 길 점) > 0
me.update(); flipped = 0; n_side = 0
nw = neck.matrix_world
for poly in me.polygons:
    if any(vi >= n_tube for vi in poly.vertices):
        continue
    c = nw @ poly.center; nrm_w = (nw.to_3x3() @ poly.normal).normalized()
    ax = Vector(line[int(np.argmin(np.linalg.norm(line - np.array(c), axis=1)))])
    n_side += 1; flipped += 1 if nrm_w.dot(c - ax) <= 0 else 0
check(flipped == 0, "목 관 겉면 %d 개 중 안쪽을 보는(뒤집힌) 면 %d" % (n_side, flipped))
check(miss == 0 and torn <= 0.02 * len(ratios), "목 관 UV: 몸 살에서 못 빌린 꼭짓점 %d · 찢어진 면 %d / %d (≤ 2 %%)" % (miss, torn, len(ratios)))

DIRS = [Vector(d).normalized() for d in ((1, .013, .007), (-1, .013, .007), (.013, 1, .007), (.013, -1, .007), (.013, .007, 1), (.013, .007, -1))]
def body_bvh():
    dg = bpy.context.evaluated_depsgraph_get(); dg.update(); return BVHTree.FromObject(body, dg)
def inside(bvh, p):
    """몸 살이 닫힌 껍질이 아니라(뚫린 가장자리 10만) 광선이 뚫은 횟수로는 못 센다 — 여섯 방향에 다 몸 살이 있으면 속"""
    return all(bvh.ray_cast(Vector(p), d)[0] is not None for d in DIRS)
bv = body_bvh()
nc = eval_co(neck)[:n_tube]; low = nc[np.array(arc[:n_tube]) > 0.11]          # 위 11 cm = 머리 속·끈 밑
hid = sum(1 for p in low if inside(bv, p))
check(hid >= 0.95 * len(low), "안 뺐을 때 목 관 겉 점 %d 중 몸 속 %d (%.1f %% ≥ 95)" % (len(low), hid, 100.0 * hid / len(low)))

hgi = head.vertex_groups[P + "Head"].index
hidx = np.array([v.index for v in head.data.vertices if any(g.group == hgi and g.weight > 0.5 for g in v.groups)])
def rot(n, R):
    pb = arm.pose.bones[P + n]; W = M @ pb.matrix; h = W.translation
    pb.matrix = Mi @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W); bpy.context.view_layer.update()
def pose(yaw, tilt, ext, up_only=False):
    reset_pose()
    for b, k in (("Neck", NECK_SHARE), ("Head", 1 - NECK_SHARE)):
        fwd = Matrix.Rotation(math.radians(yaw * k), 3, "Z") @ Vector((0, -1, 0))
        rot(b, Matrix.Rotation(math.radians(tilt * k), 4, fwd) @ Matrix.Rotation(math.radians(yaw * k), 4, "Z"))
    if ext > 0:
        pb = arm.pose.bones[P + "Head"]
        face = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Vector((0, -1, 0))                       # Unity NeckOut 과 같은 방향
        d = Vector((0, 0, 1)) if up_only else (face + Vector((0, 0, OUT_UP))).normalized()
        pb.matrix = Mi @ (Matrix.Translation(d * ext) @ (M @ pb.matrix)); bpy.context.view_layer.update()
# 머리를 60 cm 밀어도 머리·몸 살이 안 늘어남 (5 mm 넘는 변)
worst = 0.0
for ob in (head, body):
    ed = np.array(sorted({k for p_ in ob.data.polygons for k in p_.edge_keys})); c0 = eval_co(ob)      # 면에 속한 변만 (원래 있던 빈 변은 안 그려진다)
    l0 = np.linalg.norm(c0[ed[:, 0]] - c0[ed[:, 1]], axis=1); keep = l0 >= 0.005
    pose(0, 0, 0.6); c1 = eval_co(ob); reset_pose()
    l1 = np.linalg.norm(c1[ed[:, 0]] - c1[ed[:, 1]], axis=1)
    worst = max(worst, float((l1[keep] / l0[keep]).max()))
check(worst <= 1.5, "머리를 60 cm 밀어도 살이 안 늘어남: 가장 많이 늘어난 변 %.1f 배 (≤ 1.5)" % worst)
# 갸웃 110° + 저절로 나오는 길이에서 머리가 몸 속 0
if SABOTAGE != "nocut":
    bad = []
    for yaw, tilt in ((0, 110), (0, -110), (90, 110), (180, 110), (135, -110)):
        pose(yaw, tilt, AUTO_OUT); c = eval_co(head)[hidx[::3]]
        n_in = sum(1 for p in c if inside(bv, p))
        if n_in: bad.append((yaw, tilt, n_in))
    reset_pose()
    check(not bad, "갸웃 110° + 목 %.0f cm: 머리 살 점이 몸 속 0 (다섯 자세) %s" % (AUTO_OUT * 100, bad))
    # 머리 밑 마개: 머리를 밀고 아래에서 올려다본 광선이 머리 속으로 안 샌다 (처음 맞는 게 목 물체)
    pose(0, 0, 0.6, up_only=True); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    hp = (M @ arm.pose.bones[P + "Head"].matrix).translation; head_rest = M @ arm.data.bones[P + "Head"].head_local
    hits, n = 0, 0
    cen = Vector((hp.x + hc.x - head_rest.x, hp.y + hc.y - head_rest.y, hp.z + hc.z - head_rest.z))     # 밀린 머리의 밑 구멍 가운데
    for phi in np.linspace(0, 2 * math.pi, 12, endpoint=False):                                         # 비스듬히 아래 45° 에서 (사람은 3 m 괴물을 올려다본다)
        o0 = cen + Vector((0.35 * math.cos(phi), 0.35 * math.sin(phi), -0.35))
        for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
            for rr in (0.5, 0.85):
                d = (cen + Vector((hr * rr * math.cos(a), hr * rr * math.sin(a), 0)) - o0).normalized(); o = o0.copy()
                # 게임은 살의 속면(뒤집힌 면)을 안 그린다 → 속면은 뚫고 지나가고, 겉면이나 목에 막히면 안 샌 것. 끝까지 아무것도 없으면 머리 속이 뚫려 보인다
                blocked = False
                for _ in range(30):
                    ok, loc, nor, idx, ob, mat = scene.ray_cast(dg, o, d)
                    if not ok:
                        break
                    if ob.name == "Miner_Neck" or nor.dot(d) < 0:
                        blocked = True; break
                    o = loc + d * 1e-4
                n += 1; hits += 1 if blocked else 0
    reset_pose()
    check(hits >= 0.97 * n, "머리를 60 cm 밀고 비스듬히 밑에서 올려다본 광선 %d 중 목(마개·관)이나 살 겉면에 막힌 것 %d (≥ 97 %% — 나머지는 머리 속이 뚫려 보임)" % (n, hits))

if SABOTAGE:
    print("add_long_neck SABOTAGE=%s %s fails=%d (저장 안 함)" % (SABOTAGE, "ALL PASS" if not fails else "FAIL", len(fails)))
    sys.exit(0 if not fails else 2)
if fails:
    print("add_long_neck FAIL fails=%d %s (저장 안 함)" % (len(fails), fails))
    sys.exit(2)
for tr in ad.nla_tracks:
    tr.mute = False
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
print("add_long_neck ALL PASS")
