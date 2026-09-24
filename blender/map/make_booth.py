"""부스 한 층(편) 맵 — MAP1 (제안서 docs/제안서_MAP1_부스_갱도_모양.md, 승인 09-24)
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/make_booth.py
입력(안 고친다): Assets/Tunnel/Pieces/piece_straight.gltf — 재질(벽·바닥·갱목·돌·녹슨 쇠)만 가져다 쓴다.
출력: Assets/Tunnel/Pieces/booth_map.gltf(.bin) — 그림은 조각과 같은 textures/ 를 가리킨다.
      build/check_map1/booth_top.png(위에서 본 모양) · fp_*.png(1인칭 캡처, 헤드램프 + 켜진 전등).
좌표: 평면도(docs/그림/MAP1_평면도_초안.svg)의 (x, z) = Blender (X, Y), 높이 = Blender Z. 단위 m.
만드는 법: 갱도마다 중심선을 따라 쓸어 낸 "공기" 덩어리(바닥 평평·벽·낮은 아치) + 방은 상자 → 전부 합쳐 복셀 리메시(이음새 없는 한 그물)
  → 면 뒤집기(안에서 보는 동굴) → 벽만 바위 쪽으로 파는 잡음(바닥은 조금) → 상자 투영 UV → 덩어리 다섯으로 나눔.
노드: SHL_Booth_<덩어리>(보임) · COL_Booth_<덩어리>(충돌, 같은 그물) · PRP_*(갱목·돌무더기·울타리·널문·철판) · BLK_1..4(부스 막힘 스위치 돌무더기)
  · SLOT_Pocket_1..12 · SLOT_GapBig_1..3 · SLOT_GapSmall_1..2 · SLOT_Light_* · SLOT_DeadLight_* · SPAWN_Player · LOOK_Player · SPAWN_Stalker · SLOT_Prop_Cart · SLOT_Prop_Lunchbox.
자기 검사: 길 위 0.5 m 마다 폭 ≥ 1.9 · 천장 ≥ 2.2 · 바닥 있음, 2 m 마다 26 방향 광선이 40 m 안에서 벽에 맞음(구멍 없음), 광맥 12곳이 벽에 붙음, 삼각형 ≤ 50만.
사보타주: SABOTAGE=holeroof(천장에 구멍) · narrow(연층 끝을 1.2 m 로) · plate(철판을 연층 안에) · step(노보리 밑 받침을 되살림) → FAIL 로 죽는다. 빠른 확인 FAST=1(렌더 안 함)."""
import bpy, bmesh, os, math, random, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
OUT = os.path.join(PIECES, "booth_map.gltf")
CHECK = os.path.join(ROOT, "build", "check_map1")
SAB = os.environ.get("SABOTAGE", "")
FAST = os.environ.get("FAST", "") == "1"
VOXEL, CARVE, FLOOR_CARVE = 0.15, 0.30, 0.06      # 복셀 크기 · 벽을 바위 쪽으로 파는 깊이(최대) · 바닥
MIN_W, MIN_H, SEAL_M, TRI_MAX = 1.9, 2.2, 100.0, 500_000   # 구멍 광선 100 m — 운반갱이 72 m 로 곧다

# ---- 표: 갱도 = (이름, [(x, y, 바닥 높이, 폭)], 천장 높이, 갱목?, 걷는 길?)  — 평면도 v2 그대로
SEAM = 1.0                                         # 탄층 쪽 바닥 (운반갱보다 1 m 높다 — 크로스컷이 완만히 오른다)
W2 = 1.2 if SAB == "narrow" else 2.1               # 연층 끝 폭 (설계 2.1 → 복셀 뒤 ≥ 1.9)
TUNNELS = [
    ("station",   [(0, 0, 0, 5.0), (8, 0, 0, 5.0)], 3.5, False, True),
    ("haulage",   [(8, 0, 0, 3.3), (72.5, 0, 0, 3.3)], 2.7, True, True),
    ("siding",    [(9, 0, 0, 3.0), (12, -3.2, 0, 3.0), (22, -3.2, 0, 3.0), (25, 0, 0, 3.0)], 2.7, True, True),
    ("refuge",    [(40, 0, 0, 1.6), (40, -2.6, 0, 1.6)], 2.2, False, False),
    ("pump_pass", [(60, 0, 0, 2.4), (60, -3.2, 0, 2.4)], 2.4, False, True),
    ("xcut1",     [(16, 0, 0, 3.0), (17.21, 1.56, 0, 3.0), (23, 9, SEAM, 3.0)], 2.5, True, True),   # 비탈은 운반갱 벽선에서 시작 (가운데서 시작하면 벽선에 0.2 m 턱)
    ("xcut2",     [(50, 0, 0, 3.0), (51.09, 1.56, 0, 3.0), (57, 10, SEAM, 3.0)], 2.5, True, True),
    ("xcut3",     [(30, 0, 0, 3.0), (35, -6, 0, 3.0)], 2.5, True, True),
    ("door_pass", [(33, -3.6, 0, 2.4), (28.4, -7.6, 0, 2.4)], 2.4, True, True),
    ("noburi",    [(35, -6, 0, 2.4), (41, -7, 2.8, 2.4), (48, -8.5, 6.2, 2.4)], 2.4, True, True),
    ("seamW1",    [(23, 9, SEAM, 2.4), (18, 10.2, SEAM, 2.4), (13, 9.6, SEAM, 2.3)], 2.5, True, True),
    ("seamW2",    [(13, 9.6, SEAM, 2.3), (8, 11, SEAM, 2.2), (3, 11.5, SEAM, W2)], 2.35, True, True),
    ("stub1",     [(18, 10.2, SEAM, 2.2), (18.3, 14.4, SEAM, 2.2)], 2.35, True, True),
    ("stub2",     [(9, 10.8, SEAM, 2.1), (9.6, 14.8, SEAM, 2.1)], 2.35, True, True),
    ("oldnoburi", [(21, 9.4, SEAM, 1.4), (21.2, 11.0, SEAM, 1.4)], 2.0, False, False),
    ("seamE1",    [(23, 9, SEAM, 2.4), (28, 9.6, SEAM, 2.4), (32.5, 9.5, SEAM, 2.4)], 2.5, True, True),
    ("seamE2",    [(47, 10, SEAM, 2.4), (52, 10.8, SEAM, 2.4), (57, 10, SEAM, 2.4), (62, 11, SEAM, 2.4), (66, 10.6, SEAM, 2.4)], 2.5, True, True),
]
# 방 = (이름, x0, x1, y0, y1, 바닥, 천장) — 기둥 사이는 통로 줄 상자들의 합(기둥 자리만 빈다)
RX0, RX1, RY0, RY1, PIL, AIS = 32.0, 47.6, 5.0, 16.1, 2.4, 2.1
PILLARS = [(35.3, 8.3), (39.8, 8.3), (44.3, 8.3), (35.3, 12.8), (39.8, 12.8), (44.3, 12.8)]
ROOMS = [("cage", -3, 0, -1.5, 1.5, 0, 3.0), ("pump", 57, 64, -8, -3, 0, 3.0), ("goaf", RX0, RX1, RY1 - 0.2, 17.8, SEAM, 2.4)]
for i, cx in enumerate((RX0, 36.5, 41.0, 45.5)):                     # 세로 통로 넷
    ROOMS.append(("room_c%d" % i, cx, cx + AIS, RY0, RY1, SEAM, 2.4))
for i, cy in enumerate((RY0, 9.5, 14.0)):                             # 가로 통로 셋
    ROOMS.append(("room_r%d" % i, RX0, RX1, cy, cy + AIS, SEAM, 2.4))

# ---- 자리들
POCKETS = [((18.25, 13.2, SEAM), (0.05, 1)), ((9.5, 13.6, SEAM), (0.15, 1)), ((4.0, 11.4, SEAM), (-1, 0.1)),
           ((27, 9.6, SEAM), (0, 1)), ((35.3, 10.5, SEAM), (0, -1)), ((39.8, 10.5, SEAM), (0, 1)), ((44.3, 10.5, SEAM), (0, -1)),
           ((54, 10.5, SEAM), (0, 1)), ((61.5, 11.0, SEAM), (0, 1)), ((65, 10.7, SEAM), (1, 0)),
           ((41.5, -7.1, 2.95), (0.15, 1)), ((47.0, -8.3, 5.8), (1, -0.2))]
GAP_BIG = [(4.2, 12.2, SEAM), (40.0, 15.6, SEAM), (47.0, -9.0, 5.9)]
GAP_SMALL = [(13.0, 8.7, SEAM), (63.3, -7.3, 0)]
LIGHTS = [(-1.5, 0, 0, 3.0), (4, 0, 0, 3.5), (12, 0, 0, 2.7), (18, 0, 0, 2.7), (17, -3.2, 0, 2.7)]
DEAD_LIGHTS = [(26, 0, 0, 2.7), (32, 0, 0, 2.7), (38, 0, 0, 2.7), (44, 0, 0, 2.7), (18.5, 3.2, 0.4, 2.5), (32.5, -3.0, 0, 2.5)]
BLOCKS = [(51.3, 1.9, 0, 55.0), (31.3, -1.6, 0, -50.2), (48.4, 10.1, SEAM, 10.0), (45.5, 0, 0, 90.0)]   # (x, y, 바닥, 갱도 방향 °)

def floor_at(pts, x, y):
    """중심선에서 가장 가까운 점의 바닥 높이"""
    best = (1e9, 0.0)
    for (a, b) in zip(pts, pts[1:]):
        A, B = Vector((a[0], a[1])), Vector((b[0], b[1])); d = B - A; L2 = max(d.length_squared, 1e-9)
        t = max(0.0, min(1.0, (Vector((x, y)) - A).dot(d) / L2)); p = A + d * t
        dist = (Vector((x, y)) - p).length
        if dist < best[0]: best = (dist, a[2] + (b[2] - a[2]) * t)
    return best[1]

def near_other(name, p, tol=0.5):
    """p 가 다른 갱도 중심선 위(갈림)인가 — 막다른 끝이 아니다"""
    q = Vector((p[0], p[1]))
    for n2, pts2, _, _, _ in TUNNELS:
        if n2 == name: continue
        for a2, b2 in zip(pts2, pts2[1:]):
            A2, B2 = Vector(a2[:2]), Vector(b2[:2]); d = B2 - A2
            t = max(0.0, min(1.0, (q - A2).dot(d) / max(d.length_squared, 1e-9)))
            if (q - (A2 + d * t)).length < tol: return True
    return False

def slope_starts_at(name, p):
    """p 에서 다른 갱도의 비탈이 시작하는가 — 거기로 평평한 받침을 늘리면 비탈 밑에 턱(최대 0.37 m)이 생긴다 (09-24 노보리 밑에서 괴물이 걸렸다)"""
    for n2, pts2, _, _, _ in TUNNELS:
        if n2 == name: continue
        for i, v in enumerate(pts2):
            if abs(v[0] - p[0]) < 1e-6 and abs(v[1] - p[1]) < 1e-6:
                nb = [pts2[j] for j in (i - 1, i + 1) if 0 <= j < len(pts2)]
                if any(abs(w[2] - v[2]) > 1e-6 for w in nb): return True
    return False

def profile(w, h):
    hw = w / 2
    return [(-hw, 0.0), (hw, 0.0), (hw, 0.78 * h), (0.55 * hw, 0.95 * h), (0.0, h), (-0.55 * hw, 0.95 * h), (-hw, 0.78 * h)]

def prism(bm, A, B, wa, wb, h, ea, eb):
    """A→B 로 쓸어 낸 닫힌 공기 덩어리. 양 끝을 수평으로 ea·eb 만큼 늘려 이음매를 겹친다(비탈 속 꺾임은 0 — 늘리면 바닥에 턱이 생긴다)"""
    d2 = Vector((B.x - A.x, B.y - A.y, 0)).normalized()
    lat = Vector((-d2.y, d2.x, 0)); up = Vector((0, 0, 1))
    centers = ([(A - d2 * ea, wa)] if ea > 0 else []) + [(A, wa), (B, wb)] + ([(B + d2 * eb, wb)] if eb > 0 else [])   # 늘린 끝은 평평한 받침
    rings = [[bm.verts.new(c + lat * u + up * v) for u, v in profile(w, h)] for c, w in centers]
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])

def cylinder(bm, C, w, h, sides=16):
    b0 = [bm.verts.new(C + Vector((math.cos(a) * w / 2, math.sin(a) * w / 2, 0))) for a in (2 * math.pi * i / sides for i in range(sides))]
    b1 = [bm.verts.new(v.co + Vector((0, 0, h * 0.95))) for v in b0]
    for i in range(sides):
        bm.faces.new((b0[i], b0[(i + 1) % sides], b1[(i + 1) % sides], b1[i]))
    bm.faces.new(list(reversed(b0))); bm.faces.new(b1)

def box_verts(bm, c, dx, dy, dz, sx, sy, sz):
    """c 가운데, 축 dx·dy·dz(단위), 반크기 sx·sy·sz 인 닫힌 상자"""
    vs = [bm.verts.new(c + dx * (i * sx) + dy * (j * sy) + dz * (k * sz)) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

def new_obj(name, bm, mat=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if mat is not None: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def empty(name, p):
    o = bpy.data.objects.new(name, None); o.location = p; o.empty_display_size = 0.3
    bpy.context.scene.collection.objects.link(o); return o

def box_uv(me, uv_per_m):
    """상자 투영: 면마다 가장 큰 법선 축을 빼고 나머지 두 축으로"""
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        n = poly.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            uv[li].uv = (a * uv_per_m, b * uv_per_m)

def chunk_of(x, y):
    if y < -4.2 and x < 50: return "south"
    if y < -2.4 and x >= 50: return "haulB"
    if y <= 4.5: return "haulA" if x < 36 else "haulB"
    return "seamW" if x < 30 else "seamE"

# ================= 시작: 조각에서 재질만
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(PIECES, "piece_straight.gltf"))
MAT = {m.name: m for m in bpy.data.materials}
M_WALL, M_FLOOR, M_TIMB, M_ROCK, M_RUST = (MAT[n] for n in ("MAT_RockWall_EXPORT", "MAT_Floor_EXPORT", "MAT_Timber_EXPORT", "MAT_Rock_EXPORT", "MAT_RustyMetal_EXPORT"))
shl = bpy.data.objects["SHL_straight"]
def uv_density(obj, mat):                                   # 조각의 그림 촘촘함 (UV / m) — 같은 촘촘함으로 입힌다
    me = obj.data; uv = me.uv_layers.active.data; mi = [i for i, m in enumerate(me.materials) if m == mat][0]; r = []
    for p in me.polygons:
        if p.material_index != mi: continue
        li = list(p.loop_indices)
        for a, b in zip(li, li[1:] + li[:1]):
            L = (me.vertices[me.loops[a].vertex_index].co - me.vertices[me.loops[b].vertex_index].co).length
            if L > 1e-4: r.append((uv[a].uv - uv[b].uv).length / L)
    return sorted(r)[len(r) // 2]
UV_WALL, UV_FLOOR = uv_density(shl, M_WALL), uv_density(shl, M_FLOOR)
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0: bpy.data.meshes.remove(m)

# ================= 1. 공기 덩어리
bm = bmesh.new()
for name, pts, h, _, _ in TUNNELS:
    flat = [(i == 0 or i == len(pts) - 1 or pts[i - 1][2] == pts[i][2] == pts[i + 1][2]) and (SAB == "step" or not slope_starts_at(name, pts[i])) for i in range(len(pts))]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        prism(bm, Vector(a[:3]), Vector(b[:3]), a[3], b[3], h, min(a[3] / 2, 0.8) if flat[i] else 0.0, min(b[3] / 2, 0.8) if flat[i + 1] else 0.0)
    for i, p in enumerate(pts[1:-1], 1):
        if flat[i]: cylinder(bm, Vector(p[:3]), p[3], h)
for name, x0, x1, y0, y1, fz, h in ROOMS:
    box_verts(bm, Vector(((x0 + x1) / 2, (y0 + y1) / 2, fz + h / 2)), X, Y, Z, (x1 - x0) / 2, (y1 - y0) / 2, h / 2)
air = new_obj("AIR", bm)
rm = air.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
deps = bpy.context.evaluated_depsgraph_get()
cave_me = bpy.data.meshes.new_from_object(air.evaluated_get(deps)); cave_me.name = "CAVE"
bpy.data.objects.remove(air, do_unlink=True)

# ================= 2. 뒤집기 → 벽을 바위 쪽으로만 파는 잡음
bm = bmesh.new(); bm.from_mesh(cave_me)
bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.normal_update()
if SAB == "holeroof":                                        # 사보타주: 운반갱 x=30 천장에 구멍
    kill = [f for f in bm.faces if (f.calc_center_median() - Vector((30, 0, 2.7))).length < 0.8 and f.normal.z < -0.5]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
bm.to_mesh(cave_me); bm.free()
cave = bpy.data.objects.new("CAVE", cave_me); bpy.context.scene.collection.objects.link(cave)
vg = cave.vertex_groups.new(name="carve")
for v in cave_me.vertices:
    vg.add([v.index], FLOOR_CARVE / CARVE if v.normal.z > 0.6 else 1.0, "REPLACE")
tex = bpy.data.textures.new("rocknoise", type="CLOUDS"); tex.noise_scale = 0.9; tex.noise_depth = 3
dm = cave.modifiers.new("carve", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"
dm.strength = CARVE; dm.mid_level = 1.0; dm.direction = "NORMAL"; dm.vertex_group = "carve"   # 0 ~ −CARVE: 법선(공기 쪽) 반대로만 = 넓어지기만
deps = bpy.context.evaluated_depsgraph_get()
final_me = bpy.data.meshes.new_from_object(cave.evaluated_get(deps)); final_me.name = "CAVE_F"
bpy.data.objects.remove(cave, do_unlink=True)

# ================= 3. 재질 · UV · 부드럽게
final_me.materials.append(M_WALL); final_me.materials.append(M_FLOOR)
for p in final_me.polygons:
    p.material_index = 1 if p.normal.z > 0.55 else 0
    p.use_smooth = True
box_uv(final_me, UV_WALL)

# ================= 4. 자기 검사 (나누기 전 한 그물로)
bm = bmesh.new(); bm.from_mesh(final_me); bm.faces.ensure_lookup_table()
tris = sum(len(f.verts) - 2 for f in bm.faces)
bvh = BVHTree.FromBMesh(bm); bm.free()
def ray(o, d, far=SEAL_M):
    hit = bvh.ray_cast(o, d.normalized(), far); return hit[3] if hit[0] is not None else None
dirs = [Vector((i, j, k)).normalized() for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)]
worst_w, worst_h, no_floor, leaks, samples = (99, None), (99, None), [], [], 0
for name, pts, h, _, walk in TUNNELS:
    for a, b in zip(pts, pts[1:]):
        A, B = Vector(a[:3]), Vector(b[:3]); L = (Vector((B.x - A.x, B.y - A.y))).length
        d2 = Vector((B.x - A.x, B.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0))
        n = max(1, int(L / 0.5))
        for i in range(n + 1):
            t = i / n
            if L * min(t, 1 - t) < 1.2 and (t < 0.5 and a is pts[0] and not near_other(name, a) or t > 0.5 and b is pts[-1] and not near_other(name, b)): continue   # 진짜 막다른 끝 1.2 m 만 뺀다(둥글게 좁아진다) — 갈림에 붙은 끝은 잰다
            P = A.lerp(B, t); o = P + Vector((0, 0, 1.0)); samples += 1
            dl, dr = ray(o, lat, 10), ray(o, -lat, 10)
            up = ray(P + Vector((0, 0, 0.2)), Z, 10); dn = ray(o, -Z, 3)
            if dn is None or abs(dn - 1.0) > 0.2: no_floor.append((name, round(P.x, 1), round(P.y, 1), None if dn is None else round(1.0 - dn, 2)))   # 바닥이 설계 높이 ±0.2 m 안 (턱·구덩이 없음)
            if walk:
                w = (dl or 99) + (dr or 99); hh = (up or 99) + 0.2
                if w < worst_w[0]: worst_w = (w, (name, round(P.x, 1), round(P.y, 1)))
                if hh < worst_h[0]: worst_h = (hh, (name, round(P.x, 1), round(P.y, 1)))
            if i % 4 == 0:
                for d in dirs:
                    if ray(o, d) is None: leaks.append((name, round(P.x, 1), round(P.y, 1), tuple(round(c) for c in d))); break
pocket_pts = []
for (o, d) in POCKETS:
    O = Vector((o[0], o[1], o[2] + 1.4)); D = Vector((d[0], d[1], 0)).normalized(); dist = ray(O, D, 4.0)
    pocket_pts.append(None if dist is None else O + D * dist)
print("CHECK booth mesh: %d tris · uv/m wall %.3f floor %.3f · samples %d · narrowest %.2f m at %s · lowest %.2f m at %s · no floor %d · leaks %d · pockets on wall %d/12"
      % (tris, UV_WALL, UV_FLOOR, samples, worst_w[0], worst_w[1], worst_h[0], worst_h[1], len(no_floor), len(leaks), sum(p is not None for p in pocket_pts)))
if leaks: print("  leaks:", leaks[:6])
if no_floor: print("  no floor:", no_floor[:6])
assert tris <= TRI_MAX, "FAIL: 삼각형 %d > %d" % (tris, TRI_MAX)
assert not leaks, "FAIL: 맵에 구멍 (광선이 %d m 안에서 벽에 안 맞음)" % SEAL_M
assert not no_floor, "FAIL: 바닥이 없거나 설계 높이에서 0.2 m 넘게 어긋난 곳 (턱·구덩이)"
assert worst_w[0] >= MIN_W, "FAIL: 가장 좁은 곳 %.2f m < %.1f" % (worst_w[0], MIN_W)
assert worst_h[0] >= MIN_H, "FAIL: 가장 낮은 천장 %.2f m < %.1f" % (worst_h[0], MIN_H)
assert all(p is not None for p in pocket_pts), "FAIL: 벽에 안 붙은 광맥 자리"

# ================= 5. 덩어리 다섯으로 나눔 (SHL · COL 은 같은 그물)
base = bmesh.new(); base.from_mesh(final_me)
for c in ("haulA", "haulB", "south", "seamW", "seamE"):
    bm = base.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if chunk_of(f.calc_center_median().x, f.calc_center_median().y) != c], context="FACES")
    me = bpy.data.meshes.new("Booth_" + c); bm.to_mesh(me); bm.free()
    for m in final_me.materials: me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    for nm in ("SHL_Booth_" + c, "COL_Booth_" + c):
        o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o)
base.free(); bpy.data.meshes.remove(final_me)

# ================= 6. 갱목 · 돌무더기 · 울타리 · 널문 · 철판
rnd = random.Random(20260924)
def inside_other(name, p, margin=0.1):
    """갈림길: 다른 갱도·방 안에 서는 갱목은 뺀다 (안 그러면 크로스컷 갱목이 운반갱 한가운데 선다)"""
    q = Vector((p.x, p.y))
    for n2, pts2, _, _, _ in TUNNELS:
        if n2 == name: continue
        for a2, b2 in zip(pts2, pts2[1:]):
            A2, B2 = Vector(a2[:2]), Vector(b2[:2]); d = B2 - A2
            t = max(0.0, min(1.0, (q - A2).dot(d) / max(d.length_squared, 1e-9)))
            if (q - (A2 + d * t)).length < max(a2[3], b2[3]) / 2 + margin: return True
    return any(x0 - margin < p.x < x1 + margin and y0 - margin < p.y < y1 + margin for _, x0, x1, y0, y1, _, _ in ROOMS)
tmb = {c: bmesh.new() for c in ("haulA", "haulB", "south", "seamW", "seamE")}
for name, pts, h, timber, _ in TUNNELS:
    if not timber: continue
    for a, b in zip(pts, pts[1:]):
        A, B = Vector(a[:3]), Vector(b[:3]); L = (Vector((B.x - A.x, B.y - A.y))).length
        d2 = Vector((B.x - A.x, B.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0))
        s = 0.9
        while s < L - 0.9:
            t = s / L; P = A.lerp(B, t); w = a[3] + (b[3] - a[3]) * t; hw = w / 2 - 0.16; ph = 0.78 * h
            if any(inside_other(name, P + lat * (sgn * (hw + 0.1))) for sgn in (-1, 1)): s += 1.5; continue
            bmx = tmb[chunk_of(P.x, P.y)]
            for sgn in (-1, 1):
                box_verts(bmx, P + lat * (sgn * hw) + Z * (ph / 2), d2, lat, Z, 0.1, 0.1, ph / 2)
            box_verts(bmx, P + Z * (ph + 0.09), d2, lat, Z, 0.1, hw + 0.12, 0.09)
            s += 1.5
for c, b_ in tmb.items():
    o = new_obj("PRP_Timber_" + c, b_, M_TIMB); box_uv(o.data, UV_WALL * 2)

def rubble(name, C, d_deg, width, depth, height, mat=M_ROCK, n=40):
    d = Vector((math.cos(math.radians(d_deg)), math.sin(math.radians(d_deg)), 0)); lat = Vector((-d.y, d.x, 0))
    bm = bmesh.new()
    for i in range(n):
        u = (rnd.random() - 0.5) * width; v = (rnd.random() - 0.5) * depth
        z = rnd.random() ** 0.7 * height * (1.0 - 0.5 * abs(u) / max(width / 2, 0.1))
        r = 0.3 + rnd.random() * 0.5
        m = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        for vv in m["verts"]:
            vv.co = Vector((vv.co.x * (0.8 + rnd.random() * 0.5), vv.co.y * (0.8 + rnd.random() * 0.5), vv.co.z * 0.7)) + C + lat * u + d * v + Z * z
    o = new_obj(name, bm, mat); box_uv(o.data, UV_WALL * 2); return o

rubble("PRP_Rubble_End", Vector((72.0, 0, 0)), 0, 3.6, 1.4, 2.7)
for i, (bx, by, bz, deg) in enumerate(BLOCKS, 1):
    rubble("BLK_%d" % i, Vector((bx, by, bz)), deg, 3.6, 1.6, 2.7)
rubble("PRP_Rubble_Goaf", Vector(((RX0 + RX1) / 2, 17.1, SEAM)), 90, RX1 - RX0, 1.4, 2.4, n=90)
bm = bmesh.new()                                             # 채굴적 앞 울타리 + 경고판
x = RX0 + 0.4
while x < RX1 - 0.3:
    box_verts(bm, Vector((x, 16.0, SEAM + 0.65)), X, Y, Z, 0.06, 0.06, 0.65); x += 1.2
for zz in (0.5, 1.1):
    box_verts(bm, Vector(((RX0 + RX1) / 2, 15.95, SEAM + zz)), X, Y, Z, (RX1 - RX0) / 2 - 0.3, 0.03, 0.06)
box_verts(bm, Vector((40.0, 15.9, SEAM + 1.25)), X, Y, Z, 0.45, 0.02, 0.28)
o = new_obj("PRP_Fence", bm, M_TIMB); box_uv(o.data, UV_WALL * 2)
dd = (Vector((28.4, -7.6, 0)) - Vector((33, -3.6, 0))).normalized(); dl = Vector((-dd.y, dd.x, 0))   # 바람 문 = 널문
bm = bmesh.new(); box_verts(bm, Vector((28.4, -7.6, 1.15)) - dd * 0.25, dd, dl, Z, 0.05, 1.15, 1.15)
o = new_obj("PRP_WindDoor", bm, M_TIMB); box_uv(o.data, UV_WALL * 2)
bm = bmesh.new(); box_verts(bm, Vector((0, 0, 0)), X, Y, Z, 0.75, 0.015, 1.0)                         # 옛 노보리 입구의 매달린 철판 — 제 가운데로 돌린다
o = new_obj("PRP_Plate", bm, M_RUST); o.location = (21.15, 10.0 if SAB == "plate" else 10.95, SEAM + 1.0);   # 사보타주 plate = 옛 자리(연층 안) o.rotation_euler = (math.radians(4), 0, math.radians(-7)); box_uv(o.data, UV_WALL * 2)   # (09-24: 원점 기준으로 돌려 크로스컷 1 한가운데 섰다)

# 소품 충돌까지 넣고 걷는 길 폭을 다시 잰다 — Unity 는 철판·널문·울타리에 충돌을 붙인다 (09-24: 연층 한가운데 선 철판이 길을 막았는데 동굴만 재서 못 잡았다)
deps = bpy.context.evaluated_depsgraph_get()
def world_bvh(o_):                                            # 세상 좌표로 (철판은 제 자리·돌림이 있다 — 물체 좌표 BVH 는 광선과 어긋난다)
    b_ = bmesh.new(); b_.from_object(o_, deps); b_.transform(o_.matrix_world); t_ = BVHTree.FromBMesh(b_); b_.free(); return t_
prop_bvh = [world_bvh(bpy.data.objects[n]) for n in ("PRP_Plate", "PRP_WindDoor", "PRP_Fence")]
def ray_all(o, d, far):
    best = ray(o, d, far)
    for t_ in prop_bvh:
        h_ = t_.ray_cast(o, d.normalized(), far)
        if h_[0] is not None and (best is None or h_[3] < best): best = h_[3]
    return best
worst_p = (99, None)
for name, pts, h, _, walk in TUNNELS:
    if not walk: continue
    for a, b in zip(pts, pts[1:]):
        A, B = Vector(a[:3]), Vector(b[:3]); L = (Vector((B.x - A.x, B.y - A.y))).length
        d2 = Vector((B.x - A.x, B.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0)); n = max(1, int(L / 0.5))
        for i in range(n + 1):
            t = i / n
            if L * min(t, 1 - t) < 1.2 and (t < 0.5 and a is pts[0] and not near_other(name, a) or t > 0.5 and b is pts[-1] and not near_other(name, b)): continue
            o = A.lerp(B, t) + Vector((0, 0, 1.0)); w = (ray_all(o, lat, 10) or 99) + (ray_all(o, -lat, 10) or 99)
            if w < worst_p[0]: worst_p = (w, (name, round(o.x, 1), round(o.y, 1)))
print("CHECK booth props: narrowest with plate/door/fence %.2f m at %s" % worst_p)
assert worst_p[0] >= MIN_W, "FAIL: 소품이 길을 좁힌다 %.2f m at %s" % worst_p

# ================= 7. 자리 (빈 노드)
for i, p in enumerate(pocket_pts, 1): empty("SLOT_Pocket_%d" % i, p)
for i, p in enumerate(GAP_BIG, 1): empty("SLOT_GapBig_%d" % i, p)
for i, p in enumerate(GAP_SMALL, 1): empty("SLOT_GapSmall_%d" % i, p)
for i, (x, y, fz, h) in enumerate(LIGHTS, 1): empty("SLOT_Light_%d" % i, (x, y, fz + h - 0.35))
for i, (x, y, fz, h) in enumerate(DEAD_LIGHTS, 1): empty("SLOT_DeadLight_%d" % i, (x, y, fz + h - 0.35))
empty("SPAWN_Player", (-1.5, 0, 0.05)); empty("LOOK_Player", (6, 0, 1.6))
empty("SPAWN_Stalker", (37.55, 15.05, SEAM + 0.05)); empty("LOOK_Stalker", (46.0, 15.05, SEAM + 1.0))   # 기둥 사이 네거리, 통로 따라 동쪽을 본다 (기둥을 보고 서면 숙인 머리가 기둥 속)
empty("SLOT_Prop_Cart", (4, -1.3, 0)); empty("SLOT_Prop_Lunchbox", (62.3, 10.6, SEAM))

# ================= 8. 내보내기
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLTF_SEPARATE", export_keep_originals=True, export_apply=True, export_yup=True)
doc = json.load(open(OUT, encoding="utf-8"))
uris = [im["uri"] for im in doc.get("images", [])]
missing = [u for u in uris if not os.path.exists(os.path.join(PIECES, u.replace("%20", " ")))]
names = [n_.get("name", "") for n_ in doc["nodes"]]
cnt = lambda pre: sum(n_.startswith(pre) for n_ in names)
print("CHECK booth export: %s (%d KB bin) · images %d missing %d · SHL %d COL %d pockets %d gapBig %d gapSmall %d lights %d dead %d blocks %d"
      % (os.path.basename(OUT), os.path.getsize(OUT[:-5] + ".bin") // 1024, len(uris), len(missing), cnt("SHL_"), cnt("COL_"), cnt("SLOT_Pocket_"),
         cnt("SLOT_GapBig_"), cnt("SLOT_GapSmall_"), cnt("SLOT_Light_"), cnt("SLOT_DeadLight_"), cnt("BLK_")))
assert not missing and all(u.startswith("textures/") for u in uris), "FAIL: 그림 경로: %s" % uris
assert (cnt("SHL_"), cnt("COL_"), cnt("SLOT_Pocket_"), cnt("BLK_")) == (5, 5, 12, 4), "FAIL: 노드 수"

# ================= 9. 그림: 위에서 본 모양 · 1인칭
if not FAST:
    os.makedirs(CHECK, exist_ok=True)
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH": o.color = (0.62, 0.59, 0.53, 1) if o.name.startswith("SHL_") else (0.35, 0.24, 0.14, 1)
        if o.name.startswith("COL_"): o.hide_render = True
    def marker(p, col, r=0.45):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
        for v in bm.verts: v.co += Vector(p) + Vector((0, 0, 3.5))
        o = new_obj("MARK", bm); o.color = col; return o
    marks = [marker(p, (0.95, 0.5, 0.1, 1)) for p in pocket_pts] + [marker(p, (0.85, 0.15, 0.1, 1), 0.6) for p in GAP_BIG] \
        + [marker(p, (0.2, 0.45, 0.9, 1), 0.6) for p in GAP_SMALL] + [marker((x, y, fz), (1.0, 0.85, 0.3, 1), 0.35) for x, y, fz, _ in LIGHTS]
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_backface_culling = True; sh.show_cavity = True
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 80; cam.location = (35, 4.5, 60); cam.rotation_euler = (0, 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1100
    sc.render.filepath = os.path.join(CHECK, "booth_top.png"); bpy.ops.render.render(write_still=True)
    for o in marks: bpy.data.objects.remove(o, do_unlink=True)
    # 1인칭 — 헤드램프(스포트) + 켜진 전등(점광원). 조명 세기는 게임이 아니다
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.world.use_nodes = True; bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (0, 0, 0, 1)
    for x, y, fz, h in LIGHTS:
        L_ = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); L_.data.energy = 120; L_.data.color = (1.0, 0.72, 0.42)
        L_.location = (x, y, fz + h - 0.4); sc.collection.objects.link(L_)
    lamp = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(lamp)
    lamp.data.energy = 500; lamp.data.spot_size = math.radians(70); lamp.data.spot_blend = 0.5; lamp.data.color = (1.0, 0.93, 0.82)
    cam.data.type = "PERSP"; cam.data.lens = 18
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    SHOTS = [("fp_1_station", (-1.0, 0.3, 1.7), (14, 0, 1.4)), ("fp_2_xcut1", (14.6, -0.9, 1.7), (23, 9, 2.4)),
             ("fp_3_seamW", (19.5, 9.8, SEAM + 1.7), (3, 11.5, SEAM + 1.2)), ("fp_4_pillars", (33.0, 10.5, SEAM + 1.7), (47, 6.5, SEAM + 1.0)),
             ("fp_5_goaf", (33.6, 14.9, SEAM + 1.7), (46, 16.9, SEAM + 1.0)), ("fp_6_noburi", (35.4, -6.3, 1.7), (48, -8.5, 7.3))]
    for nm, eye, at in SHOTS:
        cam.location = eye; q = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
        lamp.location = Vector(eye) + Vector((0, 0, 0.1)); lamp.rotation_euler = q.to_euler()
        sc.render.filepath = os.path.join(CHECK, nm + ".png"); bpy.ops.render.render(write_still=True)
    print("CHECK booth renders -> %s" % CHECK)
print("CHECK booth ALL OK")
