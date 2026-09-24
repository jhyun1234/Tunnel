"""부스 한 층(편) 맵 — MAP2 v4 (제안서 docs/제안서_MAP2_맵_5배.md, 승인 09-24 · 사용자 손그림을 옮긴 판). MAP1 은 git 244a8b9.
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/make_booth.py
표: blender/map/booth_table.py (평면도 map2_plan.py 와 같은 표 — 여기서는 읽기만 한다).
입력(안 고친다): Assets/Tunnel/Pieces/piece_straight.gltf — 재질(벽·바닥·갱목·돌·녹슨 쇠)만 가져다 쓴다.
출력: Assets/Tunnel/Pieces/booth_map.gltf(.bin) — 그림은 조각과 같은 textures/ 를 가리킨다.
      build/check_map2/booth_top.png(위에서 본 모양) · fp_*.png(1인칭 캡처, 헤드램프 + 켜진 전등).
좌표: 평면도 (x, y) = Blender (X, Y), 높이 = Blender Z. 단위 m.
만드는 법: 굴마다 중심선을 따라 쓸어 낸 "공기" 덩어리(바닥 평평·벽·낮은 아치) + 방은 상자 → 전부 합쳐 복셀 리메시(이음새 없는 한 그물)
  → 면 뒤집기(안에서 보는 동굴) → 벽만 바위 쪽으로 파는 잡음(바닥·개구멍·대피소는 조금) → 상자 투영 UV → 40 m 칸 덩어리로 나눔.
노드: SHL_Booth_<칸>(보임) · COL_Booth_<칸>(충돌, 같은 그물) · PRP_*(갱목·돌무더기·울타리) · BLK_<묶음>_<i>(부스 막힘 돌무더기, 묶음 1 서쪽 · 2 동쪽)
  · SLOT_Pocket_1..30 · SLOT_GapBig_1..8 · SLOT_GapSmall_* · SLOT_Light_* · SLOT_DeadLight_* · SLOT_Crawl_<i>_A/B · SLOT_Niche_<i>
  · SLOT_Mouth_<굴>_<0|1>(다른 굴·방에 붙은 끝) + SLOT_In_<굴>_<0|1>(그 끝에서 굴 따라 2.5 m 안) · SLOT_Mid_<굴>(굴 길이 절반) — Unity 검사가 입구·비탈·곁길 자리를 여기서 읽는다
  · SLOT_Home_A/B(정거장 광장 네모의 두 모서리) · SPAWN_Player · LOOK_Player · SPAWN_Stalker · LOOK_Stalker · SLOT_Prop_Cart · SLOT_Prop_Lunchbox.
자기 검사: 길 위 0.5 m 마다 폭 ≥ 1.9 · 천장 ≥ 2.7 · 바닥이 설계 ±0.2 m, 2 m 마다 26 방향 광선이 벽에 맞음(구멍 없음), 광맥 30곳이 벽에 붙음,
  개구멍 폭 0.75~1.15 · 대피소 폭 0.8~1.15 m(사람은 들어가고 괴물 1.2 m 는 못 들어감), 갈림 바닥 높이 맞음, 삼각형 ≤ 120만.
사보타주: SABOTAGE=holeroof(천장에 구멍) · narrow(①–② 아래 줄을 1.2 m 로) · step(비탈 갈림 받침 없앰) · widecrawl(개구멍 1.6 m) → FAIL.
  SABOTAGE=unitywide: 개구멍(1.6 × 2.4 m)·대피소(1.6 × 2.6 m)를 괴물이 들어가는 크기로 넓힌 맵을 자기 검사(폭)를 건너뛰고 내보낸다 — Unity 검사 booth_crawl · booth_niche 가 FAIL 하는지 보는 용도. 끝나면 진짜 맵으로 다시 만든다.
빠른 확인 FAST=1(렌더 안 함)."""
import bpy, bmesh, os, sys, math, random, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import booth_table as bt
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
OUT = os.path.join(PIECES, "booth_map.gltf")
CHECK = os.path.join(ROOT, "build", "check_map2")
SAB = os.environ.get("SABOTAGE", "")
FAST = os.environ.get("FAST", "") == "1"
VOXEL, CARVE, FLOOR_CARVE, NARROW_CARVE = 0.2, 0.30, 0.06, 0.03   # 복셀 · 벽을 바위 쪽으로 파는 깊이(최대) · 바닥 · 개구멍·대피소 (넓어지면 괴물이 들어간다)
MIN_W, MIN_H, SEAL_M, TRI_MAX = 1.9, 2.7, 200.0, 1_200_000   # 구멍 광선 200 m — 큰길이 130 m 로 거의 곧다
CHUNK_M = 40.0                                     # 덩어리 = 40 m 칸 (안 보이는 칸은 안 그린다)

# ---- 표 (booth_table.py)
if SAB == "step": bt.LANDING = 0.0                 # 사보타주: 비탈 갈림에 받침 없음
if SAB in ("widecrawl", "unitywide"): bt.CRAWL_W = 1.6
if SAB == "unitywide": bt.NICHE_W, bt.NICHE_H, bt.CRAWL_H = 1.6, 2.6, 2.4   # 괴물(1.2 × 2.1 m)이 들어가는 크기 — 넓히기만 하면 높이에 막혀 버그가 아니다
B = bt.build()
bad = bt.check_junction_floors(B)
assert not bad, "FAIL: 굴이 만나는 자리 바닥 높이가 어긋남 %s" % bad[:6]
TUNNELS = [(n, pts, h, tb, walk) for n, pts, h, tb, walk, lz, kind in B["T"]]
KIND = {t[0]: t[6] for t in B["T"]}
if SAB == "narrow":                                # 사보타주: ①–② 아래 줄 굴을 1.2 m 로 (막다른 끝 1.2 m 는 안 재므로 가운데 굴을 좁힌다)
    i = [t[0] for t in TUNNELS].index("link12b"); n, pts, *r = TUNNELS[i]
    TUNNELS[i] = (n, [(*p[:3], 1.2) for p in pts], *r)
ROOMS = [(n, x0, x1, y0, y1, fz, h) for n, x0, x1, y0, y1, fz, h, lz in B["R"]]
POCKETS = B["pockets"]
GAP_BIG, GAP_SMALL = B["gap_big"], B["gap_small"]
LIGHTS = [(x, y, fz, h) for (x, y), fz, h in B["lit"]]            # (x, y, 바닥, 그 자리 천장)
DEAD_LIGHTS = [(x, y, fz, h) for (x, y), fz, h in B["dead"]]
BLOCKS = B["blocks"]                                              # (묶음, x, y, 바닥, 굴 방향 °, 굴 폭, 천장)
Z2 = B["Z"]["Z2"]

def near_other(name, p, tol=0.5):
    """p 가 다른 굴 중심선 위(갈림)나 방 안인가 — 막다른 끝이 아니다"""
    if bt.room_of(B["R"], p): return True
    return any(n2 != name and bt.proj(pts2, p)[0] < max(pts2[0][3] / 2, tol) for n2, pts2, *_ in TUNNELS)

def slope_starts_at(name, p):
    """p 에서 다른 굴의 비탈이 시작하는가 — 거기로 평평한 받침을 늘리면 비탈 밑에 턱이 생긴다 (MAP1 09-24 노보리 밑)"""
    for n2, pts2, *_ in TUNNELS:
        if n2 == name: continue
        for i, v in enumerate(pts2):
            if abs(v[0] - p[0]) < 1e-6 and abs(v[1] - p[1]) < 1e-6:
                nb = [pts2[j] for j in (i - 1, i + 1) if 0 <= j < len(pts2)]
                if any(abs(w[2] - v[2]) > 1e-6 for w in nb): return True
    return False

def profile(w, h):
    hw = w / 2
    return [(-hw, 0.0), (hw, 0.0), (hw, 0.78 * h), (0.55 * hw, 0.95 * h), (0.0, h), (-0.55 * hw, 0.95 * h), (-hw, 0.78 * h)]

def prism(bm, A, B_, wa, wb, h, ea, eb):
    """A→B 로 쓸어 낸 닫힌 공기 덩어리. 양 끝을 수평으로 ea·eb 만큼 늘려 이음매를 겹친다(비탈 속 꺾임은 0 — 늘리면 바닥에 턱이 생긴다)"""
    d2 = Vector((B_.x - A.x, B_.y - A.y, 0)).normalized()
    lat = Vector((-d2.y, d2.x, 0)); up = Vector((0, 0, 1))
    centers = ([(A - d2 * ea, wa)] if ea > 0 else []) + [(A, wa), (B_, wb)] + ([(B_ + d2 * eb, wb)] if eb > 0 else [])
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

def box_uv_np(me, uv_per_m):
    """box_uv 와 같은 것을 한꺼번에 (맵 그물은 100만 면이라 한 면씩 돌면 느리다)"""
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    npo, nl = len(me.polygons), len(me.loops)
    nrm = np.empty(npo * 3); me.polygons.foreach_get("normal", nrm); nrm = np.abs(nrm.reshape(-1, 3))
    tot = np.empty(npo, int); me.polygons.foreach_get("loop_total", tot)
    vi = np.empty(nl, int); me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)[vi]
    ax = np.repeat(np.argmax(nrm, axis=1), tot)
    uv = np.where(ax[:, None] == 0, co[:, [1, 2]], np.where(ax[:, None] == 1, co[:, [0, 2]], co[:, [0, 1]])) * uv_per_m
    me.uv_layers.active.data.foreach_set("uv", uv.ravel())

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

def chunk_of(x, y): return "g%d_%d" % (math.floor(x / CHUNK_M), math.floor(y / CHUNK_M))

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
    ext = lambda w: 0.0 if KIND[name] != "tunnel" else min(w / 2, 0.8)           # 개구멍·대피소는 늘리지 않는다 (굴 안에서 시작한다)
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        prism(bm, Vector(a[:3]), Vector(b[:3]), a[3], b[3], h, ext(a[3]) if flat[i] else 0.0, ext(b[3]) if flat[i + 1] else 0.0)
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
if SAB == "holeroof":                                        # 사보타주: 큰길 천장에 구멍
    mp = next(t for t in TUNNELS if t[0] == "main")[1][4]
    kill = [f for f in bm.faces if (f.calc_center_median() - Vector((mp[0], mp[1], mp[2] + 3.4))).length < 0.9 and f.normal.z < -0.5]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
bm.to_mesh(cave_me); bm.free()
cave = bpy.data.objects.new("CAVE", cave_me); bpy.context.scene.collection.objects.link(cave)
vg = cave.vertex_groups.new(name="carve")
co = np.empty(len(cave_me.vertices) * 3); cave_me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
nz = np.empty(len(cave_me.vertices) * 3); cave_me.vertices.foreach_get("normal", nz); nz = nz.reshape(-1, 3)[:, 2]
weight = np.where(nz > 0.6, FLOOR_CARVE / CARVE, 1.0)
for n, pts, h, _, _ in TUNNELS:                               # 개구멍·대피소 둘레는 거의 안 판다 — 넓어지면 괴물(1.2 m)이 들어간다
    if KIND[n] == "tunnel": continue
    for a, b in zip(pts, pts[1:]):
        A, Bv = np.array(a[:2]), np.array(b[:2]); d = Bv - A; L2 = max(float(d @ d), 1e-9)
        t = np.clip(((co[:, :2] - A) @ d) / L2, 0, 1); dist = np.linalg.norm(co[:, :2] - (A + t[:, None] * d), axis=1)
        zf = a[2] + (b[2] - a[2]) * t
        weight = np.where((dist < a[3] / 2 + 0.35) & (co[:, 2] < zf + h + 0.3), np.minimum(weight, NARROW_CARVE / CARVE), weight)
for w in np.unique(weight): vg.add(np.nonzero(weight == w)[0].tolist(), float(w), "REPLACE")
tex = bpy.data.textures.new("rocknoise", type="CLOUDS"); tex.noise_scale = 0.9; tex.noise_depth = 3
dm = cave.modifiers.new("carve", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"
dm.strength = CARVE; dm.mid_level = 1.0; dm.direction = "NORMAL"; dm.vertex_group = "carve"   # 0 ~ −CARVE: 법선(공기 쪽) 반대로만 = 넓어지기만
deps = bpy.context.evaluated_depsgraph_get()
final_me = bpy.data.meshes.new_from_object(cave.evaluated_get(deps)); final_me.name = "CAVE_F"
bpy.data.objects.remove(cave, do_unlink=True)

# ================= 3. 재질 · UV · 부드럽게
def wall_floor(me):
    me.materials.clear(); me.materials.append(M_WALL); me.materials.append(M_FLOOR)
    nrm = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", nrm)
    me.polygons.foreach_set("material_index", (nrm.reshape(-1, 3)[:, 2] > 0.55).astype(np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
wall_floor(final_me)
box_uv_np(final_me, UV_WALL)

# ================= 4. 자기 검사 (나누기 전 한 그물로)
bm = bmesh.new(); bm.from_mesh(final_me); bm.faces.ensure_lookup_table()
tris = sum(len(f.verts) - 2 for f in bm.faces)
bvh = BVHTree.FromBMesh(bm); bm.free()
def ray(o, d, far=SEAL_M):
    hit = bvh.ray_cast(o, d.normalized(), far); return hit[3] if hit[0] is not None else None
dirs = [Vector((i, j, k)).normalized() for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)]
worst_w, worst_h, no_floor, leaks, samples = (99, None), (99, None), [], [], 0
narrow_bad = []
for name, pts, h, _, walk in TUNNELS:
    kind = KIND[name]
    for a, b in zip(pts, pts[1:]):
        A, B_ = Vector(a[:3]), Vector(b[:3]); L = (Vector((B_.x - A.x, B_.y - A.y))).length
        d2 = Vector((B_.x - A.x, B_.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0))
        n = max(1, int(L / 0.5))
        for i in range(n + 1):
            t = i / n
            if kind == "tunnel" and L * min(t, 1 - t) < 1.2 and (t < 0.5 and a is pts[0] and not near_other(name, a) or t > 0.5 and b is pts[-1] and not near_other(name, b)): continue   # 진짜 막다른 끝 1.2 m 만 뺀다
            P = A.lerp(B_, t); zo = 0.6 if kind == "crawl" else 1.0; o = P + Vector((0, 0, zo)); samples += 1
            if kind != "tunnel":                                 # 개구멍·대피소: 바위 속 구간의 폭이 사람은 들어가고 괴물은 못 들어가는가
                inside = bt.room_of(B["R"], (P.x, P.y)) or any(bt.proj(pts2, (P.x, P.y))[0] < pts2[0][3] / 2 + 0.5 for n2, pts2, _, _, wk in TUNNELS if wk)
                if not inside and L * t < L - 0.3:
                    w = (ray(o, lat, 3) or 9) + (ray(o, -lat, 3) or 9)
                    lo, hi = (0.75, 1.15) if kind == "crawl" else (0.8, 1.15)
                    if not lo <= w <= hi: narrow_bad.append((name, round(P.x, 1), round(P.y, 1), round(w, 2)))
                continue
            dl, dr = ray(o, lat, 10), ray(o, -lat, 10)
            up = ray(P + Vector((0, 0, 0.2)), Z, 10); dn = ray(o, -Z, 3)
            if dn is None or abs(dn - zo) > 0.2: no_floor.append((name, round(P.x, 1), round(P.y, 1), None if dn is None else round(zo - dn, 2)))   # 바닥이 설계 높이 ±0.2 m 안 (턱·구덩이 없음)
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
print("CHECK booth mesh: %d tris · uv/m wall %.3f floor %.3f · samples %d · narrowest %.2f m at %s · lowest %.2f m at %s · no floor %d · leaks %d · pockets on wall %d/%d · crawl/niche width bad %d"
      % (tris, UV_WALL, UV_FLOOR, samples, worst_w[0], worst_w[1], worst_h[0], worst_h[1], len(no_floor), len(leaks), sum(p is not None for p in pocket_pts), len(POCKETS), len(narrow_bad)))
if leaks: print("  leaks:", leaks[:6])
if no_floor: print("  no floor:", no_floor[:6])
if narrow_bad: print("  crawl/niche width:", narrow_bad[:6])
assert tris <= TRI_MAX, "FAIL: 삼각형 %d > %d" % (tris, TRI_MAX)
assert not leaks, "FAIL: 맵에 구멍 (광선이 %d m 안에서 벽에 안 맞음)" % SEAL_M
assert not no_floor, "FAIL: 바닥이 없거나 설계 높이에서 0.2 m 넘게 어긋난 곳 (턱·구덩이)"
assert worst_w[0] >= MIN_W, "FAIL: 가장 좁은 곳 %.2f m < %.1f" % (worst_w[0], MIN_W)
assert worst_h[0] >= MIN_H, "FAIL: 가장 낮은 천장 %.2f m < %.1f" % (worst_h[0], MIN_H)
assert not narrow_bad or SAB == "unitywide", "FAIL: 개구멍·대피소 폭이 사람/괴물 기준 밖 %s" % narrow_bad[:4]
assert all(p is not None for p in pocket_pts), "FAIL: 벽에 안 붙은 광맥 자리 %s" % [i + 1 for i, p in enumerate(pocket_pts) if p is None]

# ================= 5. 덩어리로 나눔 (SHL · COL 은 같은 그물) — 40 m 칸. 칸마다 임시 재질을 붙여 "재질로 나누기"(한 번에)
ctr = np.empty(len(final_me.polygons) * 3); final_me.polygons.foreach_get("center", ctr); ctr = ctr.reshape(-1, 3)
cid = np.floor(ctr[:, 0] / CHUNK_M).astype(int) * 1000 + np.floor(ctr[:, 1] / CHUNK_M).astype(int)
ucid = np.unique(cid)
cells = ["g%d_%d" % (math.floor(ctr[cid == c][0, 0] / CHUNK_M), math.floor(ctr[cid == c][0, 1] / CHUNK_M)) for c in ucid]
final_me.materials.clear()
for c in cells: final_me.materials.append(bpy.data.materials.new("cell_" + c))
final_me.polygons.foreach_set("material_index", np.searchsorted(ucid, cid).astype(np.int32))
big = bpy.data.objects.new("BIG", final_me); bpy.context.scene.collection.objects.link(big)
bpy.context.view_layer.objects.active = big; big.select_set(True)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="MATERIAL"); bpy.ops.object.mode_set(mode="OBJECT")
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and (o.name == "BIG" or o.name.startswith("BIG."))]:
    me = o.data; c = me.materials[me.polygons[0].material_index].name[len("cell_"):]
    wall_floor(me); me.name = "Booth_" + c; o.name = "SHL_Booth_" + c
    col = bpy.data.objects.new("COL_Booth_" + c, me); bpy.context.scene.collection.objects.link(col)
for m in [m for m in bpy.data.materials if m.name.startswith("cell_")]: bpy.data.materials.remove(m)

# ================= 6. 갱목 · 돌무더기 · 울타리
rnd = random.Random(20260924)
def inside_other(name, p, margin=0.1):
    """갈림길: 다른 굴·방 안에 서는 갱목은 뺀다"""
    q = (p.x, p.y)
    if any(x0 - margin < p.x < x1 + margin and y0 - margin < p.y < y1 + margin for _, x0, x1, y0, y1, _, _ in ROOMS): return True
    return any(n2 != name and bt.proj(pts2, q)[0] < max(pts2[0][3], pts2[-1][3]) / 2 + margin for n2, pts2, *_ in TUNNELS if KIND[n2] == "tunnel")
tmb = {}
MOUTHS = [Vector((pts[0][0], pts[0][1], 0)) for n, pts, *_ in TUNNELS if KIND[n] != "tunnel"] +          [Vector((pts[-1][0], pts[-1][1], 0)) for n, pts, *_ in TUNNELS if KIND[n] == "crawl"]      # 개구멍·대피소 입구 — 앞에 갱목을 세우지 않는다 (09-24 캡처: 대피소를 기둥이 가렸다)
for name, pts, h, timber, _ in TUNNELS:
    if not timber: continue
    for a, b in zip(pts, pts[1:]):
        A, B_ = Vector(a[:3]), Vector(b[:3]); L = (Vector((B_.x - A.x, B_.y - A.y))).length
        d2 = Vector((B_.x - A.x, B_.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0))
        s = 0.9
        while s < L - 0.9:
            t = s / L; P = A.lerp(B_, t); w = a[3] + (b[3] - a[3]) * t; hw = w / 2 - 0.16; ph = 0.78 * h
            if any(inside_other(name, P + lat * (sgn * (hw + 0.1))) for sgn in (-1, 1)) or any((Vector((P.x, P.y, 0)) - mo).length < w / 2 + 1.0 for mo in MOUTHS): s += 1.5; continue
            bmx = tmb.setdefault(chunk_of(P.x, P.y), bmesh.new())
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
            vv.co = Vector((vv.co.x * (0.8 + rnd.random() * 0.5), vv.co.y * (0.8 + rnd.random() * 0.5), vv.co.z * 0.7)) + C + d * v + lat * u + Z * z
    o = new_obj(name, bm, mat); box_uv(o.data, UV_WALL * 2); return o

fe = B["fake_end"]; fp = next(t for t in TUNNELS if t[0] == "fake_exit")[1]
fdeg = math.degrees(math.atan2(fe[1] - fp[-2][1], fe[0] - fp[-2][0]))
rubble("PRP_Rubble_FakeExit", Vector((fe[0], fe[1], fe[2])), fdeg, 3.6, 1.8, 3.2)               # 가짜 출구 끝 — 무너짐 (방향 = 굴 방향, 폭은 가로)
for i, (g, bx, by, bz, deg, bw, bh) in enumerate(BLOCKS, 1):
    rubble("BLK_%d_%d" % (g, i), Vector((bx, by, bz)), deg, bw + 0.6, 1.6, bh)
rubble("PRP_Rubble_Goaf", Vector(((Z2["x0"] + Z2["x1"]) / 2, Z2["y1"] + 3.2, bt.SEAM)), 90, Z2["x1"] - Z2["x0"], 3.0, 3.4, n=90)
bm = bmesh.new()                                             # 채굴적 앞 울타리 + 경고판
x = Z2["x0"] + 0.4
while x < Z2["x1"] - 0.3:
    box_verts(bm, Vector((x, Z2["y1"] - 0.1, bt.SEAM + 0.65)), X, Y, Z, 0.06, 0.06, 0.65); x += 1.2
for zz in (0.5, 1.1):
    box_verts(bm, Vector(((Z2["x0"] + Z2["x1"]) / 2, Z2["y1"] - 0.15, bt.SEAM + zz)), X, Y, Z, (Z2["x1"] - Z2["x0"]) / 2 - 0.3, 0.03, 0.06)
box_verts(bm, Vector(((Z2["x0"] + Z2["x1"]) / 2, Z2["y1"] - 0.2, bt.SEAM + 1.25)), X, Y, Z, 0.45, 0.02, 0.28)
o = new_obj("PRP_Fence", bm, M_TIMB); box_uv(o.data, UV_WALL * 2)

# 울타리 충돌까지 넣고 걷는 길 폭을 다시 잰다 — Unity 는 울타리에 충돌을 붙인다
deps = bpy.context.evaluated_depsgraph_get()
def world_bvh(o_):
    b_ = bmesh.new(); b_.from_object(o_, deps); b_.transform(o_.matrix_world); t_ = BVHTree.FromBMesh(b_); b_.free(); return t_
prop_bvh = [world_bvh(bpy.data.objects["PRP_Fence"])]
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
        A, B_ = Vector(a[:3]), Vector(b[:3]); L = (Vector((B_.x - A.x, B_.y - A.y))).length
        d2 = Vector((B_.x - A.x, B_.y - A.y, 0)).normalized(); lat = Vector((-d2.y, d2.x, 0)); n = max(1, int(L / 0.5))
        for i in range(n + 1):
            t = i / n
            if L * min(t, 1 - t) < 1.2 and (t < 0.5 and a is pts[0] and not near_other(name, a) or t > 0.5 and b is pts[-1] and not near_other(name, b)): continue
            o = A.lerp(B_, t) + Vector((0, 0, 1.0)); w = (ray_all(o, lat, 10) or 99) + (ray_all(o, -lat, 10) or 99)
            if w < worst_p[0]: worst_p = (w, (name, round(o.x, 1), round(o.y, 1)))
print("CHECK booth props: narrowest with fence %.2f m at %s" % worst_p)
assert worst_p[0] >= MIN_W, "FAIL: 소품이 길을 좁힌다 %.2f m at %s" % worst_p

# ================= 7. 자리 (빈 노드)
for i, p in enumerate(pocket_pts, 1): empty("SLOT_Pocket_%d" % i, p)
for i, p in enumerate(GAP_BIG, 1): empty("SLOT_GapBig_%d" % i, p)
for i, p in enumerate(GAP_SMALL, 1): empty("SLOT_GapSmall_%d" % i, p)
for i, (x, y, fz, h) in enumerate(LIGHTS, 1): empty("SLOT_Light_%d" % i, (x, y, fz + h - 0.35))
for i, (x, y, fz, h) in enumerate(DEAD_LIGHTS, 1): empty("SLOT_DeadLight_%d" % i, (x, y, fz + h - 0.35))
ci = ni = 0
for name, pts, h, _, _ in TUNNELS:
    if KIND[name] == "crawl":
        ci += 1; empty("SLOT_Crawl_%d_A" % ci, pts[0][:3]); empty("SLOT_Crawl_%d_B" % ci, pts[-1][:3])
    elif KIND[name] == "niche":
        ni += 1; a, b = pts[0], pts[-1]; empty("SLOT_Niche_%d" % ni, (a[0] + (b[0] - a[0]) * 0.8, a[1] + (b[1] - a[1]) * 0.8, a[2]))
for name, pts, h, _, _ in TUNNELS:                              # 검사용: 붙은 끝 · 2.5 m 안 · 가운데
    if KIND[name] != "tunnel": continue
    L = bt.seg_len(pts)
    for k, (end, s_in) in enumerate(((pts[0], min(2.5, L)), (pts[-1], max(L - 2.5, 0.0)))):
        if not near_other(name, end): continue
        empty("SLOT_Mouth_%s_%d" % (name, k), end[:3])
        q = bt.point_at(pts, s_in); empty("SLOT_In_%s_%d" % (name, k), (*q, bt.proj(pts, q)[2]))
    q = bt.point_at(pts, L / 2); empty("SLOT_Mid_%s" % name, (*q, bt.proj(pts, q)[2]))
empty("SPAWN_Player", B["spawn_player"]); empty("LOOK_Player", B["look_player"])
hx0_, hx1_, hy0_, hy1_ = B["home_rect"]; empty("SLOT_Home_A", (hx0_, hy0_, 0.0)); empty("SLOT_Home_B", (hx1_, hy1_, 0.0))   # 정거장 광장 네모 (검사 booth_return 의 "집")
empty("SPAWN_Stalker", B["spawn_stalker"]); empty("LOOK_Stalker", B["look_stalker"])
empty("SLOT_Prop_Cart", B["cart"]); empty("SLOT_Prop_Lunchbox", B["lunchbox"])

# ================= 8. 내보내기
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLTF_SEPARATE", export_keep_originals=True, export_apply=True, export_yup=True)
doc = json.load(open(OUT, encoding="utf-8"))
uris = [im["uri"] for im in doc.get("images", [])]
missing = [u for u in uris if not os.path.exists(os.path.join(PIECES, u.replace("%20", " ")))]
names = [n_.get("name", "") for n_ in doc["nodes"]]
cnt = lambda pre: sum(n_.startswith(pre) for n_ in names)
print("CHECK booth export: %s (%d KB bin) · images %d missing %d · SHL %d COL %d pockets %d gapBig %d gapSmall %d lights %d dead %d blocks %d crawls %d niches %d"
      % (os.path.basename(OUT), os.path.getsize(OUT[:-5] + ".bin") // 1024, len(uris), len(missing), cnt("SHL_"), cnt("COL_"), cnt("SLOT_Pocket_"),
         cnt("SLOT_GapBig_"), cnt("SLOT_GapSmall_"), cnt("SLOT_Light_"), cnt("SLOT_DeadLight_"), cnt("BLK_"), cnt("SLOT_Crawl_") // 2, cnt("SLOT_Niche_")) + " mouths %d" % cnt("SLOT_Mouth_"))
assert not missing and all(u.startswith("textures/") for u in uris), "FAIL: 그림 경로: %s" % uris
assert cnt("SHL_") == cnt("COL_") == len(cells) and cnt("SLOT_Pocket_") == 30 and cnt("BLK_") == len(BLOCKS), "FAIL: 노드 수"

# ================= 9. 그림: 위에서 본 모양 · 1인칭
if not FAST:
    os.makedirs(CHECK, exist_ok=True)
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH": o.color = (0.62, 0.59, 0.53, 1) if o.name.startswith("SHL_") else (0.35, 0.24, 0.14, 1)
        if o.name.startswith("COL_"): o.hide_render = True
    def marker(p, col, r=0.8):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
        for v in bm.verts: v.co += Vector(p) + Vector((0, 0, 14))
        o = new_obj("MARK", bm); o.color = col; return o
    marks = [marker(p, (0.95, 0.5, 0.1, 1)) for p in pocket_pts] + [marker(p, (0.85, 0.15, 0.1, 1), 1.1) for p in GAP_BIG] \
        + [marker((x, y, fz), (1.0, 0.85, 0.3, 1), 0.6) for x, y, fz, _ in LIGHTS] + [marker(B["spawn_player"], (0.3, 0.9, 0.4, 1), 1.3)]         + [marker((bx, by, bz), (0.2, 0.45, 0.95, 1) if g == 1 else (0.7, 0.25, 0.85, 1), 1.2) for g, bx, by, bz, *_ in BLOCKS]   # 막힘: 파랑 = 묶음 1(F5) · 보라 = 묶음 2(F6)
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_backface_culling = True; sh.show_cavity = True
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 165; cam.location = (7, 11, 80); cam.rotation_euler = (0, 0, 0); cam.data.clip_end = 200
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1760
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
    T_ = {t[0]: t[1] for t in TUNNELS}; Z1, Z3 = B["Z"]["Z1"], B["Z"]["Z3"]
    def eye(p, dz=1.7): return (p[0], p[1], p[2] + dz)
    sp = B["spawn_player"]; mn = T_["main"]; arc = T_["T_arc"]
    crawl0 = next(t for t in TUNNELS if t[0] == "c_link12")[1]; niche0 = next(t for t in TUNNELS if KIND[t[0]] == "niche" and t[1][0][0] > 20)[1]
    SHOTS = [("fp_1_plaza", eye(sp), (sp[0], sp[1] + 12, 1.4)),                                           # 광장에서 북쪽(큰길 쪽)
             ("fp_2_main", eye(mn[2]), (mn[5][0], mn[5][1], 1.8)),                                        # 큰길을 동쪽으로
             ("fp_3_z1_slope", eye((Z1["xs"][1], Z1["ys"][0] + 1.4, Z1["zs"][0])), (Z1["xs"][1], Z1["ys"][-1], Z1["zs"][-1] + 1.2)),   # 채탄장 15° 오르막
             ("fp_4_pillars", eye((Z2["cx"][0], Z2["cy"][0], bt.SEAM)), (Z2["cx"][-1], Z2["cy"][0], bt.SEAM + 1.0)),                  # 기둥 사이 아래 통로를 동쪽으로 (기둥이 왼쪽에 줄지어)
             ("fp_5_noburi", eye((Z3["xs"][1], Z3["ys"][0] + 1.4, Z3["zs"][0])), (Z3["xs"][1], Z3["ys"][-1], Z3["zs"][-1] + 1.2)),    # 노보리 25°
             ("fp_6_arc_fake_exit", eye(arc[3]), (fe[0], fe[1], fe[2] + 1.5)),                             # 활 굴 위에서 가짜 출구 쪽
             ("fp_7_crawl", eye((crawl0[0][0] - 3.0, crawl0[0][1], crawl0[0][2] + 0.4)), (crawl0[0][0], crawl0[0][1] - 1.6, crawl0[0][2] + 0.5)),   # ①–② 윗줄에서 아랫줄로 가는 개구멍 입구
             ("fp_8_niche", eye(((niche0[0][0] * 3 - niche0[-1][0] * 1) / 2, (niche0[0][1] * 3 - niche0[-1][1]) / 2, niche0[0][2])), (niche0[-1][0], niche0[-1][1], niche0[0][2] + 1.2)),   # 좁은 대피소
             ("fp_9_south_lit", eye((sp[0], sp[1] - 8, 0)), (0.0, -30.0, 1.2))]                                # 불 켜진 아랫길 → 펌프실
    for nm, eye_, at in SHOTS:
        cam.location = eye_; q = (Vector(at) - Vector(eye_)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
        lamp.location = Vector(eye_) + Vector((0, 0, 0.1)); lamp.rotation_euler = q.to_euler()
        sc.render.filepath = os.path.join(CHECK, nm + ".png"); bpy.ops.render.render(write_still=True)
    print("CHECK booth renders -> %s" % CHECK)
print("CHECK booth ALL OK")
