"""3D-P 차례 1 — 플레이어 모양 밑그림 (제안서 docs/제안서_3DP_플레이어_모델.md, 09-29 승인).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/player_blockout.py
몸 바탕: Blender Studio "Human Base Meshes" v1.4.0 (CC0) 의 GEO-body_male_realistic — 저장소 밖
    MineTunnel/assets/human-base-meshes/ (09-29 사용자 승인으로 받음, 47 MB). 키 1.70 m(사용자 09-29 승인).
옷 = 몸을 부위마다 바깥으로 부풀린 껍데기 + 색(조사 13 치수) · 소품 = blender/props/make_player_props.py.
출력: build/player/player_blockout.blend · build/player/P1_*.png (판정 ① 그림, 소품 있음) · build/player/meshy_in_*.png (Meshy 입력 후보, 몸 · 옷만)
자세: 바탕 모형의 팔(수직에서 약 29°)을 A 자세 45° 로 벌린다 — Meshy · Mixamo 모두 받는 자세, T 자세보다 어깨 옷이 덜 찌그러진다.
자기 검사(FAIL 이면 종료 1): 키 · 장화 높이 · 윗도리 등길이 · 팔 각도 · 안전모가 머리에 안 파묻힘 · 챙이 눈 위 · 탄띠가 허리에
사보타주: SABOTAGE=oldpose(팔을 안 벌림) · lowboot(장화 20 cm) → 각각 FAIL
그림만 다시: RENDER=0 이면 그림을 안 찍는다(검사만)."""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "blender", "props"))
import make_player_props as P

SAB = os.environ.get("SABOTAGE", "")
HBM = os.path.join(os.path.dirname(ROOT), "MineTunnel", "assets", "human-base-meshes",
                   "human_base_meshes_bundle_v1.4.0", "human_base_meshes_bundle.blend")
OUT = os.path.join(ROOT, "build", "player"); os.makedirs(OUT, exist_ok=True)

# ── 치수 (m) — 조사 13, 제안서 근거 표 ──
STATURE = 1.70            # 맨발 키 (사용자 09-29 승인. 1979 20~24세 평균 167.7 cm)
ARM_DEG = 45.0            # 팔이 수직에서 벌어진 각 (A 자세)
BOOT_H_REF = 0.34         # 보령 장화 높이 34 cm
BOOT_H = 0.20 if SAB == "lowboot" else BOOT_H_REF
SOLE = 0.02               # 장화 밑창 (사진에서 잼)
BACK_LEN = 0.71           # 윗도리 등길이: 목 뒤 → 밑단 (보령 유물 70~72 cm)
OFF = dict(jacket=0.020, sleeve=0.018, trousers=0.016, boot=0.010, glove=0.005, hair=0.006, cuff=0.022)   # 부풀림(어림)

COL = dict(jacket=(0.030, 0.030, 0.032), trousers=(0.040, 0.040, 0.042), boot=(0.012, 0.012, 0.012),
           rubber=(0.23, 0.07, 0.04), cotton=(0.62, 0.60, 0.55), towel=(0.62, 0.61, 0.58), skin=(0.42, 0.31, 0.25),
           hair=(0.02, 0.018, 0.016), tag=(0.72, 0.72, 0.70), pocket=(0.045, 0.045, 0.048), button=(0.10, 0.10, 0.10))
# 바탕 모형의 부위 번호(sculpt face set). x<0 = 입은 사람의 오른쪽(앞 = −Y)
ARM = {"R": (20, 11, 10), "L": (21, 12, 9)}      # 윗팔 · 아래팔 · 손바닥
FS_HAND = {9, 10} | set(range(64, 104))
FS_LEG = {13, 14, 15, 16, 23, 24} | set(range(25, 64))
FS_FOOT = {13, 14} | set(range(25, 64))


def material(key, rough=0.85, metal=0.0):
    name = "PB_" + key
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*COL[key], 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; m.diffuse_color = (*COL[key], 1)
    return m


def check(fails, name, ok, msg):
    print(("PASS " if ok else "FAIL ") + name + " — " + msg)
    if not ok: fails.append(name)


# ───────────────────────── 1. 몸 바탕 · 자세 ─────────────────────────
def load_body():
    with bpy.data.libraries.load(HBM) as (src, dst):
        dst.objects = ["GEO-body_male_realistic", "GEO-body_male_realistic.eye.L", "GEO-body_male_realistic.eye.R"]
    body, eyes = dst.objects[0], dst.objects[1:]
    for o in dst.objects: bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    for e in eyes:
        mw = e.matrix_world.copy(); e.parent = None; e.matrix_world = mw
    off = body.matrix_world.translation.copy(); body.location = (0, 0, 0)
    for e in eyes: e.matrix_world = Matrix.Translation(-off) @ e.matrix_world
    bpy.context.view_layer.update()
    return body, eyes


def face_sets(me):
    return np.array([a.value for a in me.attributes[".sculpt_face_set"].data])


def vert_face_set(me, fs):
    vf = np.zeros(len(me.vertices), dtype=np.int32)
    for p, f in zip(me.polygons, fs):
        for v in p.vertices: vf[v] = f
    return vf


def boundary_center(me, vf, a, b):
    """두 부위(face set a · b)가 만나는 모서리들의 가운데 = 관절 자리."""
    pts = [(me.vertices[e.vertices[0]].co + me.vertices[e.vertices[1]].co) / 2
           for e in me.edges if {int(vf[e.vertices[0]]), int(vf[e.vertices[1]])} == {a, b}]
    if not pts:   # 경계 모서리가 없으면(부위가 한 점씩 떨어져 있음) 가장 가까운 점 쌍 20 개의 가운데
        A = [v.co.copy() for v in me.vertices if vf[v.index] == a]; B = [v.co.copy() for v in me.vertices if vf[v.index] == b]
        kd = KDTree(len(B)); [kd.insert(c, i) for i, c in enumerate(B)]; kd.balance()
        near = sorted(((kd.find(c)[2], (c + kd.find(c)[0]) / 2) for c in A), key=lambda t: t[0])[:20]
        return sum((m for _, m in near), Vector()) / len(near)
    return sum(pts, Vector()) / len(pts)


def arm_joints(me, vf):
    j = {}
    for sd, (up, fo, pa) in ARM.items():
        pts = [v.co.copy() for v in me.vertices if vf[v.index] == up]; topz = max(p.z for p in pts)
        top = [p for p in pts if p.z > topz - 0.03]
        sh = sum(top, Vector()) / len(top); sh.z = topz - 0.045          # 어깨 관절 = 윗팔 꼭대기에서 4.5 cm 아래(어림)
        el = boundary_center(me, vf, up, fo); wr = boundary_center(me, vf, fo, pa)
        hand = [v.co.copy() for v in me.vertices if vf[v.index] in FS_HAND and (v.co.x < 0) == (sd == "R")]
        j[sd] = (sh, el, wr, min(hand, key=lambda p: p.z))
    return j


def arm_angle(j):
    return {sd: math.degrees(math.atan2(abs((wr - sh).x), -(wr - sh).z)) for sd, (sh, el, wr, tip) in j.items()}


def pose_arms(body):
    """팔을 A 자세로: 어깨 · 팔꿈치 · 손목 뼈를 부위 경계에서 잡고 자동 무게로 붙여 윗팔을 돌린 뒤 굳힌다.
    바탕 그물(약 1만 점)에서 하고 → 멀티레스(잔 근육)는 그 위에 다시 얹힌다."""
    me = body.data; vf = vert_face_set(me, face_sets(me)); joints = arm_joints(me, vf)
    tmp = body.copy(); tmp.data = me.copy(); tmp.modifiers.clear(); bpy.context.scene.collection.objects.link(tmp)
    arm_d = bpy.data.armatures.new("A"); arm = bpy.data.objects.new("A", arm_d); bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm_d.edit_bones.new("root"); root.head = (0, 0, 0.9); root.tail = (0, 0, 1.45)
    for sd, (sh, el, wr, tip) in joints.items():
        b1 = arm_d.edit_bones.new("up" + sd); b1.head, b1.tail = sh, el; b1.parent = root
        b2 = arm_d.edit_bones.new("fo" + sd); b2.head, b2.tail = el, wr; b2.parent = b1; b2.use_connect = True
        b3 = arm_d.edit_bones.new("ha" + sd); b3.head, b3.tail = wr, tip; b3.parent = b2; b3.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in bpy.context.view_layer.objects: o.select_set(False)
    tmp.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    # 손이 허벅지 옆이라 자동 무게가 다리까지 팔 뼈에 붙인다 → 팔 부위 + 어깨 둘레(몸통 · 목, 어깨에서 12 cm 안)만 남긴다
    for sd, (sh, el, wr, tip) in joints.items():
        keep = {v.index for v in me.vertices if (v.co.x < 0) == (sd == "R") and
                (vf[v.index] in set(ARM[sd]) | FS_HAND or (vf[v.index] in (1, 22) and (v.co - sh).length < 0.12))}
        drop = [i for i in range(len(me.vertices)) if i not in keep]
        for g in ("up", "fo", "ha"):
            vg = tmp.vertex_groups.get(g + sd)
            if vg: vg.remove(drop)
    before = arm_angle(joints)
    if SAB != "oldpose":
        for sd, (sh, el, wr, tip) in joints.items():
            rot = math.radians(ARM_DEG - before[sd]) * (-1 if sd == "L" else 1)   # 세계 Y 축 둘레: 왼팔(+x)은 − 로 돌려야 올라간다
            pb = arm.pose.bones["up" + sd]
            pb.matrix = Matrix.Translation(sh) @ Matrix.Rotation(rot, 4, "Y") @ Matrix.Translation(-sh) @ pb.matrix
            bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = tmp.evaluated_get(dg); pm = ev.to_mesh(); co = [v.co.copy() for v in pm.vertices]; ev.to_mesh_clear()
    for v, c in zip(me.vertices, co): v.co = c
    me.update()
    for o in (tmp, arm): bpy.data.objects.remove(o)
    return before


def apply_multires(body, level=2):
    m = body.modifiers[0]; m.levels = level
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    base = body.data
    new = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    body.modifiers.clear(); body.data = new
    return base


# ───────────────────────── 2. 옷 ─────────────────────────
def hull2d(pts):
    pts = sorted(set(map(tuple, np.round(np.asarray(pts), 5))))
    if len(pts) < 3: return pts
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def ring(pts2d, offset, n=72):
    """점들의 볼록 껍질을 둘레 n 점으로 다시 뽑고 바깥으로 offset. 0 번 = 앞(−Y)."""
    h = np.array(hull2d(pts2d)); c = h.mean(axis=0); out = []
    for k in range(n):
        a = 2 * math.pi * k / n; d = np.array([-math.sin(a), -math.cos(a)]); best = 0.0
        for i in range(len(h)):
            p, q = h[i] - c, h[(i + 1) % len(h)] - c
            m = np.array([[d[0], p[0] - q[0]], [d[1], p[1] - q[1]]])
            if abs(np.linalg.det(m)) < 1e-12: continue
            t, u = np.linalg.solve(m, p)
            if t > 0 and -1e-9 <= u <= 1 + 1e-9: best = max(best, t)
        out.append(tuple(c + d * (best + offset)))
    return out


def loft(name, rings, key, solid=0.004):
    bm = bmesh.new(); vs = [[bm.verts.new(p) for p in r] for r in rings]; n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(material(key)); [setattr(p, "use_smooth", True) for p in me.polygons]
    if solid:
        m = o.modifiers.new("t", "SOLIDIFY"); m.thickness = solid; m.offset = 0
    return o


def patch(name, bvh, origin, direction, size, key, lift=0.002):
    """몸 겉에 붙는 납작한 상자(주머니 · 번호표 · 단추) — origin 에서 direction 으로 쏜 선이 닿는 곳. size = (가로, 세로, 두께)."""
    p, n, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
    if p is None: return None
    if n.dot(Vector(direction)) > 0: n = -n
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=(size[0], size[2], size[1]), verts=bm.verts)
    side = Vector((0, 0, 1)).cross(n).normalized(); up = n.cross(side).normalized()
    m = Matrix((side, -n, up)).transposed().to_4x4(); m.translation = p + n * (size[2] / 2 + lift)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); me.materials.append(material(key))
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(size) * 0.35; bv.segments = 2
    return o


def neighbours(me):
    e = np.array([ed.vertices[:] for ed in me.edges]); n = len(me.vertices)
    deg = np.bincount(e.ravel(), minlength=n).astype(float)
    return e, np.maximum(deg, 1)


def smooth(co, e, deg, mask, iters, lam=0.5, mu=-0.53):
    """Taubin 매끈하게(부피가 덜 줄어든다). mask 밖 점은 그대로 — 경계가 이어진다."""
    co = co.copy()
    for k in range(iters * 2):
        acc = np.zeros_like(co); np.add.at(acc, e[:, 0], co[e[:, 1]]); np.add.at(acc, e[:, 1], co[e[:, 0]])
        d = acc / deg[:, None] - co
        co[mask] += (lam if k % 2 == 0 else mu) * d[mask]
    return co


def blur(val, e, deg, iters):
    for _ in range(iters):
        acc = np.zeros_like(val); np.add.at(acc, e[:, 0], val[e[:, 1]]); np.add.at(acc, e[:, 1], val[e[:, 0]])
        val = 0.5 * val + 0.5 * acc / deg
    return val


def slim(co, reg, e, deg, jn):
    """바탕 모형은 보디빌더 몸 — 1980년대 광부(마른 몸)로 줄인다. ✎ 비율은 어림(기록 없음):
    팔 둘레 × 0.82(팔 축 쪽으로) · 몸통 폭 × 0.92 · 몸통 앞뒤 × 0.90 · 다리 둘레 × 0.90. 부위 무게를 흐려 이음매 없이."""
    co = co.copy()
    def w_of(sel): return blur(sel.astype(float), e, deg, 8)
    for sd, (sh, el, wr, tip) in jn.items():
        w = w_of(np.isin(reg, [ARM[sd][0], ARM[sd][1]]) & ((co[:, 0] < 0) == (sd == "R")))
        a, b = np.array(sh[:]), np.array(wr[:]); d = (b - a) / np.linalg.norm(b - a)
        t = np.clip((co - a) @ d, 0, None); foot = a + t[:, None] * d
        co += (w * -0.18)[:, None] * (co - foot)
    trunk = w_of(np.isin(reg, [1, 19, 18]))
    zc = co[np.isin(reg, [1, 19]), 2]
    cy = co[np.isin(reg, [1, 19]), 1].mean()
    co[:, 0] += trunk * -0.08 * co[:, 0]
    co[:, 1] += trunk * -0.10 * (co[:, 1] - cy)
    for sd in (-1, 1):
        w = w_of(np.isin(reg, [15, 16, 23, 24]) & (np.sign(co[:, 0]) == sd))
        leg = co[(w > 0.5)]
        hip = leg[leg[:, 2] > np.percentile(leg[:, 2], 95)].mean(axis=0); ank = leg[leg[:, 2] < np.percentile(leg[:, 2], 5)].mean(axis=0)
        d = (hip - ank) / np.linalg.norm(hip - ank); t = (co - ank) @ d; foot = ank + t[:, None] * d
        co += (w * -0.10)[:, None] * (co - foot)
    return co


def boot_shell(name, co, reg, sd):
    """고무장화 한 짝: 발 · 정강이를 1 cm 층마다 볼록 껍질로 감싼 통 + 밑창(발바닥 아래 SOLE) — 발가락 홈이 없다."""
    sel = np.isin(reg, list(FS_FOOT) + [15, 16]) & (np.sign(co[:, 0]) == sd)
    rings_ = []
    for z0 in np.arange(0.0, BOOT_H - 0.004, 0.01):
        pts = co[sel & (np.abs(co[:, 2] - z0) < 0.008)][:, :2]
        if len(pts) < 6: continue
        o_ = 0.016 if z0 < 0.10 else 0.012
        r = ring(pts, o_)
        if not rings_: rings_.append([(px, py, -SOLE) for px, py in r])      # 밑창 바닥
        rings_.append([(px, py, z0) for px, py in r])
    o = loft(name, rings_, "boot", solid=0)
    bm = bmesh.new(); bm.from_mesh(o.data)
    low = sorted(bm.verts, key=lambda v: v.co.z)[:len(rings_[0])]
    bmesh.ops.contextual_create(bm, geom=low); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    for p_ in o.data.polygons: p_.use_smooth = True
    return o


def towel(bvh, co, reg, neck_back_z):
    """목수건(흰 광목, 조사 13): 목 둘레를 돌며 몸 겉면을 찾아 그 위에 붙는 납작한 띠 — 뒤는 목 뒤 높이, 앞은 가슴 위로 내려온다(✎ 모양은 어림).
    돌려받는 것: (물체, 목 가운데 x, y). Meshy 몸 손질(player_meshy_fix.py)도 towel_ring 을 같이 쓴다."""
    nk = co[reg == 22]; low = nk[nk[:, 2] < nk[:, 2].min() + 0.03]; cx, cy = float(low[:, 0].mean()), float(low[:, 1].mean())
    return towel_ring(bvh, cx, cy, neck_back_z, neck_back_z - 0.055), cx, cy


def towel_ring(bvh, cx, cy, zb, zf):
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48; zz = zf + (zb - zf) * (1 - math.cos(t)) / 2
        d = Vector((-math.sin(t), math.cos(t), 0))                                   # 바깥 → 목 쪽
        hit, nrm, _, _ = bvh.ray_cast(Vector((cx, cy, zz)) - d * 0.4, d)
        if hit is not None: pts.append(hit - d * 0.013)
    prof = bpy.data.curves.new("TowelProfile", "CURVE"); ps = prof.splines.new("POLY"); ps.points.add(23)   # 납작한 단면 4.4 × 2.4 cm
    for i, pt in enumerate(ps.points):
        a_ = 2 * math.pi * i / 24; pt.co = (0.012 * math.cos(a_), 0.022 * math.sin(a_), 0, 1)
    ps.use_cyclic_u = True
    po = bpy.data.objects.new("TowelProfile", prof); bpy.context.scene.collection.objects.link(po); po.hide_render = True
    cu = bpy.data.curves.new("Towel", "CURVE"); cu.dimensions = "3D"; cu.bevel_mode = "OBJECT"; cu.bevel_object = po
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts): p_.co = (*q, 1)
    sp.use_cyclic_u = True; sp.order_u = 4
    o = bpy.data.objects.new("Towel", cu); bpy.context.scene.collection.objects.link(o); cu.materials.append(material("towel"))
    return o


def dress(body, base, jn):
    """몸을 부위마다 부풀려 옷을 입히고 윗도리 밑단 · 목수건 · 장화 윗단 · 주머니 · 번호표 · 단추를 더한다.
    바탕 모형은 근육이 도드라진 몸이라 옷 부위는 먼저 매끈하게 편다(헐렁한 면 작업복 — 근육 · 발가락이 비치지 않게)."""
    me = body.data; vfb = vert_face_set(base, face_sets(base))
    kd = KDTree(len(base.vertices)); [kd.insert(v.co, v.index) for v in base.vertices]; kd.balance()
    reg = np.array([vfb[kd.find(v.co)[1]] for v in me.vertices])
    co = np.array([v.co[:] for v in me.vertices]); e, deg = neighbours(me)
    cloth = ~np.isin(reg, [17, 2, 3, 4, 5, 7, 8, 22])
    co = slim(co, reg, e, deg, jn)                                            # 보디빌더 몸 → 마른 광부(✎ 비율 어림)
    co = smooth(co, e, deg, cloth, 25)                                        # 옷 전체: 근육 결을 편다
    for v, c in zip(me.vertices, co): v.co = c
    me.update()
    nor = np.array([v.normal[:] for v in me.vertices])
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    head = reg == 17; head_top0 = z[head].max(); head_cy = co[head & (z > head_top0 - 0.1), 1].mean()
    nk = co[reg == 22]; neck_back_z = float(nk[nk[:, 1] > np.median(nk[:, 1]), 2].min())
    hem_z = neck_back_z - BACK_LEN
    belt_z = float(co[reg == 19, 2].mean())
    cut = {sd: (np.array(jn[sd][2][:]), np.array((jn[sd][2] - jn[sd][1]).normalized()[:])) for sd in "RL"}   # 손목 자르는 면(아래팔 축에 수직)
    off = np.zeros(len(co)); kind = np.full(len(co), "skin", dtype=object)
    for i in range(len(co)):
        r = int(reg[i]); zi = z[i]
        if r in FS_HAND or r in (11, 12, 20, 21):
            w0, d0 = cut["R" if x[i] < 0 else "L"]; t = float(np.dot(co[i] - w0, d0))
            if t > 0.005: off[i], kind[i] = OFF["glove"], "rubber"                 # 손목 너머 = 고무
            elif t > -0.065: off[i], kind[i] = OFF["cuff"], "cotton"              # 손목 6.5 cm = 면(근로장갑)
            else: off[i], kind[i] = OFF["sleeve"], "jacket"
        elif r in FS_LEG or r == 18:
            if zi < BOOT_H:
                kind[i] = "boot"                                                  # 장화 껍데기 속(안 보임)
            else:
                off[i], kind[i] = OFF["trousers"] + 0.010 * max(0.0, 1 - (zi - BOOT_H) / 0.07), "trousers"   # 장화 위로 부푼 바지
        elif r in (1, 19):
            off[i], kind[i] = OFF["jacket"], "jacket"
        elif r == 17:
            back = y[i] > head_cy + 0.01
            if zi > head_top0 - 0.075 or (back and zi > head_top0 - 0.20): off[i], kind[i] = OFF["hair"], "hair"
    off = blur(off, e, deg, 12)                                               # 부위 경계의 톱니를 없앤다
    kinds_ = ["jacket", "trousers", "boot", "rubber", "cotton", "skin", "hair"]   # 색 경계도 흐려서 다수결
    score = np.stack([blur((kind == k).astype(float), e, deg, 8) for k in kinds_], axis=1)
    kind = np.array(kinds_, dtype=object)[score.argmax(axis=1)]
    co = co + nor * off[:, None]
    for v, c in zip(me.vertices, co): v.co = c
    keys = ["jacket", "trousers", "boot", "rubber", "cotton", "skin", "hair"]
    me.materials.clear()
    for k in keys: me.materials.append(material(k, 0.35 if k in ("boot", "rubber") else 0.85))
    idx = {k: i for i, k in enumerate(keys)}
    for p in me.polygons:
        ks = [kind[v] for v in p.vertices]; p.material_index = idx[max(set(ks), key=ks.count)]; p.use_smooth = True
    me.update()
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    extra = []
    # 윗도리 밑단: 허리 → 밑단까지 늘어진 껍데기(다리 사이를 따라가지 않는다)
    trunk = np.isin(reg, [1, 19, 18, 23, 24]) & (np.abs(x) < 0.26)
    rings_ = []
    for zz in np.linspace(belt_z + 0.01, hem_z, 9):                          # 윗 끝은 탄띠 속에 숨긴다
        band = co[trunk & (np.abs(z - zz) < 0.012)][:, :2]
        rings_.append([(px, py, zz) for px, py in ring(band, 0.004 + 0.006 * (belt_z + 0.01 - zz) / (belt_z + 0.01 - hem_z))])
    extra.append(loft("Jacket_Hem", rings_, "jacket"))
    # 목수건: 목 밑동에 두툼한 흰 고리(흰 광목 — 조사 13 [A] [F], 1981 k23)
    # 장화(따로 껍데기) + 윗단: 두 다리 각각
    for sd in (-1, 1):
        extra.append(boot_shell("Boot" + ("R" if sd < 0 else "L"), co, reg, sd))
        leg = co[np.isin(reg, [15, 16]) & (np.sign(x) == sd) & (np.abs(z - BOOT_H) < 0.015)][:, :2]
        if len(leg) > 3:
            extra.append(loft("Boot_Rim" + ("R" if sd < 0 else "L"),
                              [[(px, py, BOOT_H - 0.014 + dz) for px, py in ring(leg, o_)] for dz, o_ in ((0, 0.002), (0.012, 0.007), (0.022, 0.001))],
                              "boot", solid=0))
    # 가슴 주머니 2 · 덮개 · 왼쪽 가슴 흰 번호표(1981 k18 k19) · 단추(앞 가운데)
    bvh = BVHTree.FromPolygons([tuple(c) for c in co], [tuple(p.vertices) for p in me.polygons])
    tw, ncx, ncy = towel(bvh, co, reg, neck_back_z); extra.append(tw)
    chest_z = neck_back_z - 0.20
    for sx in (-1, 1):
        extra.append(patch("Pocket" + ("R" if sx < 0 else "L"), bvh, (sx * 0.095, -1, chest_z - 0.02), (0, 1, 0), (0.12, 0.14, 0.006), "pocket"))
        extra.append(patch("PocketFlap" + ("R" if sx < 0 else "L"), bvh, (sx * 0.095, -1, chest_z + 0.045), (0, 1, 0), (0.125, 0.045, 0.012), "pocket"))
    extra.append(patch("ChestTag", bvh, (0.095, -1, chest_z + 0.085), (0, 1, 0), (0.07, 0.032, 0.012), "tag"))
    for k in range(5):
        extra.append(patch("Button%d" % k, bvh, (0.0, -1, chest_z + 0.07 - k * 0.11), (0, 1, 0), (0.015, 0.015, 0.006), "button"))
    return dict(neck_back_z=neck_back_z, hem_z=hem_z, belt_z=belt_z, reg=reg, co=co, bvh=bvh, extra=[e for e in extra if e], neck_cx=ncx, neck_cy=ncy)


# ───────────────────────── 3. 소품 달기 ─────────────────────────
def along(ring_pts, direction):
    c = np.mean(np.array(ring_pts), axis=0); d = np.array(direction) / np.linalg.norm(direction)
    p = max(ring_pts, key=lambda q: np.dot(np.array(q) - c, d))
    o = np.array(p) - c; o /= np.linalg.norm(o)
    return Vector((p[0], p[1], 0)), Vector((o[0], o[1], 0))


def place(root, point, outward, z):
    """물건의 −Y(바깥) 를 outward 로 돌려 point 에 붙인다."""
    th = math.atan2(outward.x, -outward.y)
    root.matrix_world = Matrix.Translation((point.x, point.y, z)) @ Matrix.Rotation(th, 4, "Z")


def gear(body_info, eyes):
    reg, co, bvh = body_info["reg"], body_info["co"], body_info["bvh"]
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    head = reg == 17; head_top = float(z[head].max())
    rim_z = head_top - 0.08                          # 챙 = 정수리에서 8 cm 아래 — 이마, 눈보다 2 cm 위(안 틀이 3~4 cm 띄움 — 어림)
    sec = co[head & (np.abs(z - rim_z - 0.01) < 0.012)]                    # 챙 높이의 머리 단면 가운데에 맞춘다
    cx, cy = float((sec[:, 0].min() + sec[:, 0].max()) / 2), float((sec[:, 1].min() + sec[:, 1].max()) / 2)
    h = P.build_helmet()
    h["root"].matrix_world = Matrix.Translation((cx, cy, rim_z))
    belt_z = body_info["belt_z"]
    band = co[np.isin(reg, [1, 19, 18]) & (np.abs(z - belt_z) < 0.012) & (np.abs(x) < 0.26)][:, :2]
    wr = ring(band, 0.004, n=96)
    belt = P.build_belt(wr, belt_z)
    bat = P.build_battery(); p, o = along(wr, (-0.72, 0.70))          # 오른쪽 허리 뒤(1981 k17 · 1992 k25)
    place(bat["root"], p + o * 0.005, o, belt_z + P.BELT_W / 2)
    can = P.build_canteen(); p2, o2 = along(wr, (0.95, 0.30))          # ✎ 왼쪽 옆(수통 자리 기록 없음)
    place(can["root"], p2 + o2 * 0.005, o2, belt_z + P.BELT_W / 2 - 0.01)
    bpy.context.view_layer.update()
    # 램프 줄: 램프 뒤 → 안전모 오른쪽 → 뒤 걸이 → 목 뒤 → 등 → 허리 뒤 배터리(사용자 09-29 승인, 1981 k21)
    Wh = h["root"].matrix_world
    pts = [Wh @ h["lamp_back"], Wh @ (P.dome_point(-math.pi * 0.55, 0.62) + P.dome_normal(-math.pi * 0.55, 0.62) * 0.012),
           Wh @ h["clip"], Wh @ h["clip"] + Vector((0, 0.03, -0.07))]
    for zz, xx in ((body_info["neck_back_z"] - 0.10, -0.02), (belt_z + 0.25, -0.04), (belt_z + 0.12, -0.07)):
        hit = bvh.ray_cast(Vector((xx, 1.0, zz)), Vector((0, -1, 0)))[0]
        if hit: pts.append(hit + Vector((0, 0.014, 0)))
    pts.append(bat["root"].matrix_world @ bat["cord_out"] + Vector((0, 0, 0.01)))
    cord = P.cord([tuple(q) for q in pts])
    return dict(helmet=h, rim_z=rim_z, head_top=head_top, cx=cx, cy=cy, belt=belt, bat=bat, can=can, cord=cord)


# ───────────────────────── 4. 그림 ─────────────────────────
def setup_render(bg, strength):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.view_settings.view_transform = "Standard"
    if sc.world is None: sc.world = bpy.data.worlds.new("w")
    try: sc.world.use_nodes = True
    except Exception: pass
    b = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    b.inputs["Color"].default_value = (*bg, 1); b.inputs["Strength"].default_value = strength
    if not bpy.data.objects.get("KeySun"):
        for nm, rot, e in (("KeySun", (50, 0, -35), 3.2), ("FillSun", (65, 0, 150), 1.3), ("RimSun", (20, 0, 90), 0.8)):
            s = bpy.data.objects.new(nm, bpy.data.lights.new(nm, "SUN")); s.data.energy = e
            s.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(s)


VIEWS = {"front": ((0, -6, 0), (90, 0, 0)), "back": ((0, 6, 0), (90, 0, 180)), "right": ((-6, 0, 0), (90, 0, -90)),
         "left": ((6, 0, 0), (90, 0, 90)), "quarter": ((4.3, -4.3, 0), (90, 0, 45))}


def shoot(path, view, zc, scale, res=(1024, 1536), xc=0.0):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("Cam") or bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"; cam.data.ortho_scale = scale
    (lx, ly, _), rot = VIEWS[view]
    cam.location = (lx + xc, ly, zc); cam.rotation_euler = [math.radians(a) for a in rot]
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)


def flatten_white(path):
    """투명 바탕 그림을 흰 바탕으로(사람 밝기는 그대로)."""
    im = bpy.data.images.load(path); px = np.array(im.pixels[:]).reshape(-1, 4); a = px[:, 3:4]
    px[:, :3] = px[:, :3] * a + (1 - a); px[:, 3] = 1; im.pixels[:] = px.ravel(); im.save(); bpy.data.images.remove(im)


def show(objs, on):
    for o in objs: o.hide_render = not on


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body, eyes = load_body()
    before = pose_arms(body)
    base = apply_multires(body, 2)
    zs = np.array([v.co.z for v in body.data.vertices]); s = STATURE / (zs.max() - zs.min())
    M = Matrix.Scale(s, 4) @ Matrix.Translation((0, 0, -zs.min()))
    body.data.transform(M); base.transform(M)
    for e in eyes: e.matrix_world = M @ e.matrix_world
    body.name = "Player_Body"
    COL["eye"] = (0.035, 0.025, 0.02)                                   # 바탕 모형 눈은 재질이 없어 하얗게 나온다
    for e_ in eyes: e_.data.materials.clear(); e_.data.materials.append(material("eye", 0.2))
    stature = float(np.ptp([v.co.z for v in body.data.vertices]))
    jn = arm_joints(base, vert_face_set(base, face_sets(base)))
    after = arm_angle(jn)
    info = dress(body, base, jn)
    # 밑창만큼 들어 올려 장화 바닥 = 0
    lift = -min((o.matrix_world @ v.co).z for o in [body] + info["extra"] if o.type == "MESH" for v in o.data.vertices)
    for o in [body] + eyes + info["extra"]: o.matrix_world = Matrix.Translation((0, 0, lift)) @ o.matrix_world
    info["co"] = info["co"] + np.array([0, 0, lift]); info["neck_back_z"] += lift; info["hem_z"] += lift; info["belt_z"] += lift
    info["bvh"] = BVHTree.FromPolygons([tuple(c) for c in info["co"]], [tuple(p.vertices) for p in body.data.polygons])
    g = gear(info, eyes)
    bpy.context.scene["player_info"] = dict(neck_back_z=info["neck_back_z"], neck_cx=info["neck_cx"], neck_cy=info["neck_cy"],   # Meshy 몸 손질이 읽는다
                                            rim_z=g["rim_z"], helmet_cx=g["cx"], helmet_cy=g["cy"], belt_z=info["belt_z"])
    P.bake_all(list(bpy.data.objects))
    bpy.context.view_layer.update()

    # ── 자기 검사 ──
    fails = []
    check(fails, "stature", abs(stature - STATURE) < 0.005, f"맨발 키 {stature*100:.1f} cm (기준 170 ±0.5)")
    check(fails, "arm_angle", all(abs(a - ARM_DEG) < 3 for a in after.values()),
          f"팔 각도(수직에서) 오른 {after['R']:.1f}° · 왼 {after['L']:.1f}° (기준 45 ±3, 바탕 모형 {before['R']:.1f}°)")
    boot_top = max((o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.name.startswith("Boot_Rim") for c in o.bound_box)
    check(fails, "boot_height", abs(boot_top - lift - BOOT_H_REF) < 0.015,
          f"장화 윗단 {(boot_top - lift)*100:.1f} cm (밑창 {lift*100:.1f} cm 빼고, 기준 34 ±1.5)")
    hem = bpy.data.objects["Jacket_Hem"]; hem_min = min((hem.matrix_world @ v.co).z for v in hem.data.vertices)
    back_len = info["neck_back_z"] - hem_min
    check(fails, "jacket_back_length", abs(back_len - BACK_LEN) < 0.015, f"윗도리 등길이 {back_len*100:.1f} cm (기준 71 ±1.5)")
    co, reg = info["co"], info["reg"]; rim = g["rim_z"]
    hv = co[(reg == 17) & (co[:, 2] > rim)]
    a_, b_, c_ = P.SHELL_W / 2 - 0.012, P.SHELL_L / 2 - 0.012, P.DOME_H - 0.012   # 껍데기 4 mm + 틈 8 mm
    q = ((hv[:, 0] - g["cx"]) / a_) ** 2 + ((hv[:, 1] - g["cy"]) / b_) ** 2 + ((hv[:, 2] - rim) / c_) ** 2
    check(fails, "helmet_clears_head", q.max() < 1.0, f"머리가 안전모 안쪽(8 mm 틈)에 들어감 — 가장 큰 값 {q.max():.2f} (< 1)")
    eye_z = max(e.matrix_world.translation.z for e in eyes)
    check(fails, "brim_above_eyes", rim - P.BRIM_DROP > eye_z + 0.015, f"챙 앞끝 {(rim - P.BRIM_DROP)*100:.1f} cm · 눈 {eye_z*100:.1f} cm (챙이 1.5 cm 이상 위)")
    bz = co[reg == 19, 2]
    check(fails, "belt_at_waist", bz.min() <= info["belt_z"] <= bz.max(), f"탄띠 {info['belt_z']*100:.1f} cm · 배 {bz.min()*100:.1f}~{bz.max()*100:.1f} cm")
    total = max((o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == "MESH" for c in o.bound_box)
    print(f"INFO 안전모까지 전체 높이 {total*100:.1f} cm · 장화 신은 키 {(stature + lift)*100:.1f} cm")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "player_blockout.blend"))

    # ── 그림 ──
    if os.environ.get("RENDER", "1") != "0":
        props = [o for o in bpy.data.objects if o.name.startswith(("Helmet", "Lamp", "Battery", "Canteen", "Belt"))]
        props = [o for o in props if o.type == "MESH"]
        setup_render((0.30, 0.30, 0.31), 0.9)
        zc = 0.93
        for v, nm in (("front", "앞"), ("right", "옆"), ("back", "뒤"), ("quarter", "비스듬히")):
            shoot(os.path.join(OUT, f"P1_{nm}.png"), v, zc, 2.05)
        hz = g["rim_z"] + 0.02
        shoot(os.path.join(OUT, "P1_머리_앞.png"), "front", hz, 0.42, (900, 900))
        shoot(os.path.join(OUT, "P1_머리_뒤.png"), "back", hz, 0.42, (900, 900))
        shoot(os.path.join(OUT, "P1_머리_옆.png"), "right", hz, 0.42, (900, 900))
        shoot(os.path.join(OUT, "P1_허리_뒤.png"), "back", info["belt_z"] - 0.02, 0.62, (900, 900))
        rw = jn["R"][2]
        shoot(os.path.join(OUT, "P1_손.png"), "front", rw.z + lift - 0.06, 0.34, (900, 900), xc=rw.x)
        # Meshy 입력: 소품 빼고 흰 바탕(사용자 09-29 승인 — 안전모 · 소품은 Blender 코드)
        show(props, False)
        bpy.context.scene.render.film_transparent = True
        for v in ("front", "back", "left", "right"):
            f = os.path.join(OUT, f"meshy_in_{v}.png"); shoot(f, v, zc, 2.05, (1024, 1280)); flatten_white(f)
        bpy.context.scene.render.film_transparent = False
        show(props, True)
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
