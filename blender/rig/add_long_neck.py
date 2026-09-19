"""add_long_neck — 몸 속에 등뼈를 따라 누운 긴 목(마디 7개 관)을 넣는다 (제안서 docs/제안서_3D3b_M1e_목_길게_빼기.md, 승인 2026-09-19).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/add_long_neck.py
입력: Documents/MineTunnel/blender/miner_v4_stage15_timber.blend — 안 고친다
출력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend → blender/anim/walk_knuckle.py 가 이것을 읽어 GLB 를 굽는다
하는 일: ① 머리 뼈와 몸 뼈 양쪽에 걸쳐 붙은 살 점을 더 센 쪽 한 곳으로 (머리를 밀면 고무막처럼 늘어나던 것)
        ② 머리 쪽 점과 몸 쪽 점을 잇는 면: 머리 쪽 점을 복사해 몸 쪽에 붙인다 → 면이 몸에 남아 목 나오는 곳의 살 옷깃이 된다 (쉬는 모양은 그대로)
        ③ 뼈 mixamorig:NeckExt_0~6 (부모 Spine2, 서로 안 이음 — Unity StalkerAnim.NeckOut 이 매 프레임 "머리 → 나오는 곳 → 등뼈" 길 위에 놓는다)
        ④ 목 관 Miner_Neck: 머리 속 3 cm 에서 등뼈를 따라 아래로 83 cm, 굵기 8.5 → 11 cm, 등 쪽 등뼈 돌기·앞쪽 힘줄 줄·마디 잘록함,
           머리 밑 마개·살 소매(머리 뼈)와 목구멍 마개·살 옷깃(가슴 뼈). 재질 = 목_근육: 셈으로 만든 근육 그림 2장(blender/stage16_tex, 받은 그림 없음)
        ⑤ 자기 검사
쉬는 자세 = 목을 안 뺀 자세 (관 전체가 몸 속). 길·마디 자리 셈은 Unity 와 같다: 관 꼭대기에서 잰 길이 s, 마디 i 는 s = TOP_IN + i × LINK
사보타주: SABOTAGE=hose -> 둥근 관 + 회색 등 살 (검사 "둥글지 않다" FAIL). SABOTAGE=flip -> 관 면을 거꾸로 감는다 (검사 "뒤집힌 면" FAIL). SABOTAGE=nocut -> ①② 를 안 한다 (검사 "머리를 밀어도 살이 안 늘어남" FAIL). SABOTAGE=nocap -> 마개를 안 만든다 (검사 "밑에서 올려다본 광선" FAIL). 사보타주 실행은 blend 를 저장하지 않는다"""
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
SIDES, STEP = 30, 0.01
CORDS, CORD_DEPTH, CORD_TWIST = 5, 0.10, 7.0   # 사용자 판정 09-19 "호스 같아 보인다" → 둥근 관 대신 힘줄 다섯 가닥이 꼬인 다발 (깊이 = 반지름 몫, 꼬임 = rad/m)
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
            if SABOTAGE != "hose":
                r *= 1 - 0.06 * sum(math.exp(-((s - bs) / 0.012) ** 2) for bs in bone_s[1:])                   # 마디 잘록함
                r *= 1 - CORD_DEPTH * (0.5 - 0.5 * math.cos(CORDS * a + CORD_TWIST * s)) ** 0.6                  # 힘줄 가닥 사이 골 (꼬이며 내려간다)
                r *= 1 + 0.05 * math.sin(3 * a + 41 * s) * math.sin(17 * s + 1.3)                                # 고르지 않게
                r += 0.013 * math.exp(-(ang / 24.0) ** 2) * (0.5 + 0.5 * math.cos(2 * math.pi * s / 0.038)) ** 2   # 등 쪽 등뼈 돌기 (3.8 cm 마다)
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
# 살 소매(머리 뼈: 머리 밑 구멍 → 아래로 9 cm, 목 굵기까지 좁아짐)와 살 옷깃(가슴 뼈: 목구멍 → 위로 5 cm). 사용자 판정 09-19
# "뚝 생겨난다 · 머리 밑이 뚫려 보인다" — 목이 소매·옷깃 속에서 미끄러져 나오게, 턱 밑 빈 곳을 막게. 끝은 찢긴 살처럼 들쭉날쭉
def axis_xy(z):
    p = line[int(np.argmin(np.abs(line[:, 2] - z)))]; return Vector((p[0], p[1]))
def funnel(c, r_from, z_from, dz, r_to, n_rings, bone, seed):
    i0 = len(verts)
    for j in range(n_rings):
        t = j / (n_rings - 1.0); z = z_from + dz * t; cen = Vector((c.x, c.y)).lerp(axis_xy(z), t)
        for k in range(24):
            a = 2 * math.pi * k / 24
            r = (r_from + (r_to - r_from) * t ** 0.7) * (1 + 0.04 * math.sin(3 * a + j + seed))
            zz = z + (0.008 * math.sin(5 * a + seed) * (1 if dz < 0 else -1) if j == n_rings - 1 else 0.0)
            verts.append(Vector((cen.x + r * math.cos(a), cen.y + r * math.sin(a), zz))); arc.append(0.3 + 0.025 * j); ang_k.append(k)
    for j in range(n_rings - 1):
        for k in range(24):
            f = (i0 + j * 24 + k, i0 + j * 24 + (k + 1) % 24, i0 + (j + 1) * 24 + (k + 1) % 24, i0 + (j + 1) * 24 + k)
            cen3 = sum((verts[v] for v in f), Vector()) / 4; ax = axis_xy(cen3.z)
            nrm_f = (verts[f[1]] - verts[f[0]]).cross(verts[f[3]] - verts[f[0]])
            if nrm_f.dot(Vector((cen3.x - ax.x, cen3.y - ax.y, 0))) < 0:
                f = tuple(reversed(f))
            faces.append(f)
    caps.append((i0, n_rings * 24, bone))
if SABOTAGE not in ("nocap", "nosleeve"):
    # 2차 판정 09-19 "노이즈가 있는 것처럼 보인다 · 약간 어색하다": 소매 윗고리가 머리 살 겉면과 같은 자리라 두 면이 번갈아 비쳤다 → 속(구멍의 0.9배, 3 cm 안)에서 시작
    funnel(hc, hr * 0.90, hc.z + 0.03, -0.10, R_HEAD + 0.006, 5, "Head", 0.0)
    funnel(bc, br * 0.90, bc.z - 0.03, 0.07, R_BASE + 0.004, 4, "Spine2", 1.7)
print("마개: 머리 밑 가운데 %s 반지름 %.3f · 목구멍 가운데 %s 반지름 %.3f" % (tuple(round(x, 3) for x in hc), hr, tuple(round(x, 3) for x in bc), br))

me = bpy.data.meshes.new("Miner_Neck"); me.from_pydata(verts, [], faces); me.update()
for p in me.polygons:
    p.use_smooth = True
neck = bpy.data.objects.new("Miner_Neck", me); scene.collection.objects.link(neck)
neck.parent = arm; neck.matrix_parent_inverse = body.matrix_parent_inverse.copy(); neck.matrix_basis = body.matrix_basis.copy()
bpy.context.view_layer.update()
me.transform(neck.matrix_world.inverted()); me.update()            # 점은 세상 좌표로 만들었다 → 몸 살과 같은 물체 공간으로
# 재질: 몸 살 그림은 UV 가 잘게 조각나 있어(이웃 점 사이 UV 가 0.24 넘게 뛴다 — 어느 10 × 25 cm 조각이든) 빌리면 얼룩덜룩하다(09-19 게임 그림,
# 사용자 "호스 같아 보인다"). 목 전용 근육 그림 2장(색·요철)을 셈으로 만든다 — 받은 그림 없음(출처 문제 없음). 이름이 "살" 로 시작하면
# Unity StalkerLook 이 눈 발광 색을 입혀 목 전체가 빛난다 → "목_근육"
TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "blender", "stage16_tex"); os.makedirs(TEX, exist_ok=True)
def make_textures():
    """3차 판정 09-19 "목과 쇄골 부분의 차이가 심하다 · 노이즈": 셈으로 만든 줄무늬는 몸 살(울퉁불퉁한 허연 살 + 갈색 근육)과 결이 다르다.
    → 몸통 살을 목에 입힌다: 목 그림의 점마다 (둘레 각도, 길이) → 몸통 가운데 축에서 그 각도로 바깥을 본 자리의 몸 살 색을 그대로 가져온다.
    몸 살 UV 가 잘게 조각나 있어도 점 하나하나를 따로 찾으니 상관없다. 둘레는 몸통 한 바퀴라 이음매가 없고, 길이는 가슴 1.45 ~ 1.85 m 를
    올라갔다 내려오며(거울) 되풀이한다. 같은 출처(우리 괴물 살 그림)에서 다시 뽑은 그림이라 받은 그림은 없다.
    요철은 가져온 색의 밝기를 높이로 보고 만든다 (몸 살 요철 그림은 조각마다 방향이 달라 그대로 못 가져온다)"""
    Wt, half = 512, 512
    bsdf_b = next(n for n in body.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bimg = bsdf_b.inputs["Base Color"].links[0].from_node.image
    Wb, Hb = bimg.size; bp = np.empty(Wb * Hb * 4, np.float32); bimg.pixels.foreach_get(bp); bp = bp.reshape(Hb, Wb, 4)
    bme_ = body.data; bme_.calc_loop_triangles()
    bco_ = [body.matrix_world @ v.co for v in bme_.vertices]
    tb = BVHTree.FromPolygons(bco_, [tuple(t.vertices) for t in bme_.loop_triangles])
    uvd = bme_.uv_layers.active.data
    # 몸 살의 울퉁불퉁함은 색이 아니라 요철 그림에 있다 → 같은 자리의 요철 그림에서 "얼마나 기울었나"(1 − z)만 가져와 높이로 쓴다
    nlink = bsdf_b.inputs["Normal"].links
    nimg = nlink[0].from_node.inputs["Color"].links[0].from_node.image if nlink and nlink[0].from_node.type == "NORMAL_MAP" else None
    if nimg:
        Wn, Hn = nimg.size; npx = np.empty(Wn * Hn * 4, np.float32); nimg.pixels.foreach_get(npx); npx = npx.reshape(Hn, Wn, 4)
    bump = np.zeros((half, Wt), np.float32); lastb = 0.0
    rows = np.zeros((half, Wt, 3), np.float32); last = np.array([0.3, 0.25, 0.22], np.float32); missed = 0
    for r_ in range(half):
        z = 1.45 + 0.40 * r_ / (half - 1.0)
        for c_ in range(Wt):
            th = 2 * math.pi * c_ / Wt; d = Vector((math.cos(th), math.sin(th), 0))
            loc, nor, ti, dist = tb.ray_cast(Vector((0, 0.05, z)) + d * 1.0, -d)
            if loc is None:
                missed += 1; rows[r_, c_] = last; bump[r_, c_] = lastb; continue
            t = bme_.loop_triangles[ti]; pa, pb_, pc = (bco_[i] for i in t.vertices)
            n = (pb_ - pa).cross(pc - pa); den = n.dot(n)
            if den < 1e-18:
                rows[r_, c_] = last; continue
            wa = (pb_ - loc).cross(pc - loc).dot(n) / den; wb = (pc - loc).cross(pa - loc).dot(n) / den
            uv = Vector(uvd[t.loops[0]].uv) * wa + Vector(uvd[t.loops[1]].uv) * wb + Vector(uvd[t.loops[2]].uv) * (1 - wa - wb)
            last = bp[int(uv.y % 1.0 * (Hb - 1)), int(uv.x % 1.0 * (Wb - 1)), :3]; rows[r_, c_] = last
            if nimg:
                q = npx[int(uv.y % 1.0 * (Hn - 1)), int(uv.x % 1.0 * (Wn - 1)), :3] * 2 - 1
                lastb = float(math.hypot(q[0], q[1])); bump[r_, c_] = lastb
    col = np.concatenate([rows, rows[::-1]], 0)                                              # 올라갔다 내려온다 → 위아래로도 이어진다
    Ht = col.shape[0]
    lum = 0.3 * col.mean(2) + np.concatenate([bump, bump[::-1]], 0)
    print("몸 살 요철에서 가져온 기울기 평균 %.3f · 최대 %.3f" % (float(bump.mean()), float(bump.max())))
    for _ in range(2):                                                                       # 높이를 조금 뭉갠다 (점 하나짜리 튐 = 노이즈)
        lum = (lum + np.roll(lum, 1, 0) + np.roll(lum, -1, 0) + np.roll(lum, 1, 1) + np.roll(lum, -1, 1)) / 5
    gx = np.roll(lum, -1, 1) - np.roll(lum, 1, 1); gy = np.roll(lum, -1, 0) - np.roll(lum, 1, 0)
    nrm = np.dstack([-gx * float(os.environ.get("NECK_BUMP", "6")), -gy * float(os.environ.get("NECK_BUMP", "6")), np.ones_like(lum)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    print("목 살 그림: 몸통에서 가져온 점 %d, 못 찾은 점 %d" % (half * Wt - missed, missed))
    out = {}
    for name, arr, cs in (("neck_muscle_color", np.clip(col, 0, 1), "sRGB"), ("neck_muscle_normal", nrm * 0.5 + 0.5, "Non-Color")):
        im = bpy.data.images.new(name, Wt, Ht, alpha=False); im.colorspace_settings.name = cs
        im.pixels.foreach_set(np.dstack([arr, np.ones((Ht, Wt))]).astype(np.float32).ravel())
        im.filepath_raw = os.path.join(TEX, name + ".png"); im.file_format = "PNG"; im.save(); im.pack()
        out[name] = im
    return out, float(np.clip(col, 0, 1).mean())
tex, tex_mean = make_textures()
nm = bpy.data.materials.new("목_근육"); nm.use_nodes = True
nt = nm.node_tree; bs_n = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = tex["neck_muscle_color"]; nt.links.new(tc.outputs["Color"], bs_n.inputs["Base Color"])
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = tex["neck_muscle_normal"]
nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], bs_n.inputs["Normal"])
bs_n.inputs["Roughness"].default_value = 0.55; bs_n.inputs["Metallic"].default_value = 0.0      # 젖은 근육 — 몸 살(0.6)보다 조금 반들
me.materials.append(nm)
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

# UV: 둘레 한 바퀴 = 그림 가로 한 번, 길이 80 cm = 세로 한 번(가슴 40 cm 를 올라갔다 내려옴) (그림은 가로·세로 다 이어진다). 소매·옷깃·마개도 같은 식
uvl = me.uv_layers.new(name="UVMap")
miss = 0
for poly in me.polygons:
    ks = [ang_k[me.loops[l2].vertex_index] for l2 in poly.loop_indices]
    n_side = SIDES if all(me.loops[l2].vertex_index < n_tube for l2 in poly.loop_indices) else 24
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index; k = ang_k[vi]
        if k == 0 and max(ks) > n_side // 2:
            k = n_side                                                                      # 둘레 이음매: 끝 칸은 0 이 아니라 한 바퀴
        uvl.data[li].uv = (k / float(n_side), arc[vi] / 0.8)
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
# 호스가 아니다: 고리마다 (가장 큰 반지름 − 가장 작은) ÷ 평균 의 가운데값
rv = np.array([[ (rg[i][k] - Vector(line[i])).length for k in range(SIDES)] for i in range(len(rg))])
lump = float(np.median((rv.max(1) - rv.min(1)) / rv.mean(1)))
check(lump >= 0.15, "목 관이 둥근 호스가 아니다: 고리의 (가장 굵은 곳 − 가장 가는 곳) ÷ 평균 = %.2f (≥ 0.15, 둥근 관 0)" % lump)
check(torn <= 0.02 * len(ratios), "목 관 UV: 찢어진 면 %d / %d (≤ 2 %%)" % (torn, len(ratios)))
check(0.08 <= tex_mean <= 0.40, "목 근육 색 그림 평균 밝기 %.3f (0.08 ~ 0.40 — 몸 살 색에서 만든다)" % tex_mean)

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
