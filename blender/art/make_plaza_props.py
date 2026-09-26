"""ART-1 차례 3 — 케이지 광장 물건을 게임에 넣는다 (제안서 docs/제안서_ART1_현실감_광장_시험.md · 승인 배치 docs/그림/ART1_광장_배치.png).
  python blender/art/prop_textures.py      (먼저 — Blender 물건 질감 props_tex)
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/make_plaza_props.py
입력: Assets/Tunnel/Pieces/booth_map.gltf(읽기만 — 광선으로 벽·바닥·천장을 찾고, SLOT_Light_* · SLOT_TimberSet_* 자리를 읽는다)
      build/art/props_cand/<Poly Haven id>/(받아 둔 CC0 모델, 커밋 안 함 — 쓰는 것의 그림만 Assets/Tunnel/Art/plaza_src/<id>/ 로 복사)
출력: Assets/Tunnel/Art/plaza_props.gltf(.bin) — 노드: 물건(보임) · COLP_<이름>(부딪힘 상자, Unity 가 BoxCollider 로) · TMB_<칸>(굴 안 둥근 통나무 동발, 40 m 칸)
      build/art/plaza_check/*.png(확인 그림, FAST=1 이면 안 찍음)
좌표: Blender = booth_table (x, y) m, Z 위. 광장 x −7.7..7.7 · y −5.46..4.34 · 바닥 0 · 천장 4.5 (벽은 파낸 잡음이라 광선으로 붙인다)."""
import bpy, bmesh, os, sys, math, glob, shutil, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(ROOT, "Assets", "Tunnel", "Art"); OUT = os.path.join(ART, "plaza_props.gltf")
PH = os.path.join(ROOT, "build", "art", "props_cand"); SRC = os.path.join(ART, "plaza_src")
CHECK = os.path.join(ROOT, "build", "art", "plaza_check"); FONT = os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf")
FAST = os.environ.get("FAST", "") == "1"
TRI_MAX = 250_000                                    # 광장 물건 삼각형 한도 (동발 TMB_ 는 따로 센다)
CHUNK_M = 40.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "booth_map.gltf"))
MAP = list(sc.objects)
SLOT = {o.name: o for o in MAP if o.type == "EMPTY"}

# ---------- 광선 (충돌 그물 COL_ + 바위 틈 입구 바위)
vs, fs = [], []
for o in MAP:
    if o.type == "MESH" and o.name.startswith(("COL_", "PRP_Crevice_")):
        mw = o.matrix_world; k = len(vs)
        vs += [mw @ v.co for v in o.data.vertices]; fs += [[k + i for i in p.vertices] for p in o.data.polygons]
BVH = BVHTree.FromPolygons(vs, fs); del vs, fs
def ray(p, d, far=30.0):
    hit = BVH.ray_cast(Vector(p), Vector(d).normalized(), far)
    return hit[3] if hit[0] is not None else far
def floor_z(x, y, z0=2.0): return z0 - ray((x, y, z0), (0, 0, -1))
def ceil_z(x, y, z0=2.0): return z0 + ray((x, y, z0), (0, 0, 1))

M = mp.game_materials(ROOT)
PROPS = bpy.data.collections.new("PLAZA"); sc.collection.children.link(PROPS)
def own(roots):                                      # 새로 만든 것을 PLAZA 모음으로 (내보낼 것)
    def walk(o):
        for c in list(o.users_collection): c.objects.unlink(o)
        PROPS.objects.link(o)
        for ch in o.children: walk(ch)
    for r in roots: walk(r)
    return roots[0] if len(roots) == 1 else roots
def place(o, loc, yaw=0.0):
    o.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(yaw, 4, "Z"); return o

# ---------- Poly Haven 부품 (부품 하나 = 그물 하나, 회전·크기를 그물에 굽고 원점 = 제자리)
_ph = {}
def ph_load(pid):
    if pid in _ph: return _ph[pid]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glob.glob(os.path.join(PH, pid, "*.gltf"))[0])
    parts = {}
    for o in set(bpy.data.objects) - before:          # 모델 좌표 그대로 굽는다 (여러 부품 모델은 부품끼리 자리가 맞는다)
        if o.type == "MESH":
            me = o.data.copy(); me.transform(o.matrix_world); parts[o.name] = me
        bpy.data.objects.remove(o, do_unlink=True)
    _ph[pid] = parts; return parts
def ph(pid, part, R=Matrix.Identity(3), at=(0, 0, 0), align=(0.5, 0.5, 0.5), name=None):
    """부품을 R 로 돌린 뒤, 그 상자의 align 자리(0 = 최소 · 1 = 최대, 축마다)가 at 에 오게. 그물은 같이 쓴다"""
    me = ph_load(pid)[next(k for k in ph_load(pid) if k == part or k.endswith("_" + part))]
    o = bpy.data.objects.new(name or part, me); sc.collection.objects.link(o)
    R4 = R.to_4x4(); ws = [R4 @ v.co for v in me.vertices]
    lo = Vector(map(min, *ws)); hi = Vector(map(max, *ws))
    anchor = Vector([lo[i] + (hi[i] - lo[i]) * align[i] for i in range(3)])
    o.matrix_world = Matrix.Translation(Vector(at) - anchor) @ R4
    own([o]); return o
def assembly(pid, parts, mw):
    """여러 부품 모델을 모델 좌표 그대로 한 행렬로 (상자 · 사다리 · 양동이)"""
    for part in parts:
        o = bpy.data.objects.new(part, ph_load(pid)[part]); sc.collection.objects.link(o); o.matrix_world = mw; own([o])
def extent(pid, part, R=Matrix.Identity(3)):
    me = ph_load(pid)[next(k for k in ph_load(pid) if k == part or k.endswith("_" + part))]
    ws = [R @ v.co for v in me.vertices]; return Vector(map(max, *ws)) - Vector(map(min, *ws))
RX = lambda a: Matrix.Rotation(math.radians(a), 3, "X"); RY = lambda a: Matrix.Rotation(math.radians(a), 3, "Y"); RZ = lambda a: Matrix.Rotation(math.radians(a), 3, "Z")

def colp(name, center, size, yaw=0.0):
    """부딪힘 상자 (Unity: BoxCollider, 안 보임)"""
    bm = bmesh.new(); mp.box(bm, (0, 0, 0), size)
    me = bpy.data.meshes.new("COLP_" + name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("COLP_" + name, me); sc.collection.objects.link(o)
    place(o, center, yaw); own([o]); return o

def smooth(pts, it=3):                               # 꺾은 선 모서리 깎기 (Chaikin, 끝점 고정)
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        pts = q[:1] + q[2:-1] + [pts[-1]]
    return pts
def ext(p, toward, L):                               # p 에서 toward 쪽으로 L m (굴 안으로 늘리기)
    d = (Vector(toward) - Vector(p)).normalized(); return (p[0] + d.x * L, p[1] + d.y * L)

# ================= B1 레일 (배치 평면: 케이지를 동서로 지남 + 서쪽 갈림 → 서쪽 굴. 케이지 틀 밖에서 멈춤 · 굴 안으로 3 m 더)
RAIL_W = smooth([(-1.45, 0.0), (-3.0, 0.0), (-5.5, 0.3), (-7.7, 1.4), ext((-7.7, 1.4), (-14.7, 2.8), 3.0)])
RAIL_B = smooth([(-2.2, 0.0), (-3.0, 0.0), (-4.6, -0.6), (-6.4, -1.7), (-7.7, -2.1), (-10.7, -2.1)])
RAIL_E = smooth([(1.45, 0.0), (3.0, 0.0), (5.5, 0.3), (7.7, 0.7), ext((7.7, 0.7), (13.3, 2.8), 3.0)])
for nm, path in (("RailWest", RAIL_W), ("RailBranch", RAIL_B), ("RailEast", RAIL_E)): own([mp.rails_path(M, path, floor_z, name=nm)])

# ================= B3 케이지 (가운데 (0, 0) — 기둥은 천장 바위에 박히게, 위 보는 가장 낮은 천장 밑)
posts = [(sx * 1.3, sy * 1.1) for sx in (-1, 1) for sy in (-1, 1)]
cz = [ceil_z(x, y) for x, y in posts] + [ceil_z(0, 0)]
cage = own([mp.cage(M, H=max(cz) + 0.25, top=min(cz) - 0.2)])
place(cage, (0, 0, sum(floor_z(x, y) for x, y in posts) / 4))
colp("Cage", (0, 0, 1.5), (2.8, 2.4, 3.0))

# ================= B2 광차 — Meshy 광차(사용자 09-27 58차 선택): 조사 10 공통점으로 만든 mine_car_v2 세 방향 그림 → Meshy 그림 → 3D (MINER_ASSET_PIPELINE.md 기록)
#   원본 glb 는 저장소 밖(Documents/MineTunnel). 그물은 plaza_props.bin 으로, 그림 셋은 glb 에서 그대로 꺼내 plaza_src/meshy_car2/ 로 (이름 = 규칙 _diff · _arm · _nor_gl)
MESHY_CAR = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel", "mesh", "props", "meshy_car2.glb")
def meshy_car(path, length=2.05, width=1.0):
    import struct
    raw = open(path, "rb").read(); n = struct.unpack("<I", raw[12:16])[0]; doc = json.loads(raw[20:20 + n]); binc = raw[20 + n + 8:]
    mat = doc["materials"][0]; pbr = mat["pbrMetallicRoughness"]; tex = lambda k: doc["textures"][k["index"]]["source"]
    role = {tex(pbr["baseColorTexture"]): "diff", tex(pbr["metallicRoughnessTexture"]): "arm", tex(mat["normalTexture"]): "nor_gl"}
    dst = os.path.join(SRC, "meshy_car2", "textures"); os.makedirs(dst, exist_ok=True); files = {}
    for i, im in enumerate(doc["images"]):                                      # 그림을 풀지 않고 바이트 그대로 (glTF 노멀 = OpenGL · 금속거칠기 = G 거칠기 · B 쇠 — 우리 _arm 과 같다)
        bv = doc["bufferViews"][im["bufferView"]]; data = binc[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]
        f = os.path.join(dst, "meshy_car2_%s.%s" % (role[i], "png" if im["mimeType"] == "image/png" else "jpg")); open(f, "wb").write(data); files[role[i]] = f
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in set(bpy.data.objects) - before]; o = next(x for x in new if x.type == "MESH")
    me = o.data.copy(); me.transform(o.matrix_world)
    for x in new: bpy.data.objects.remove(x, do_unlink=True)
    ws = [v.co for v in me.vertices]; lo = Vector(map(min, *ws)); hi = Vector(map(max, *ws))
    if hi.y - lo.y > hi.x - lo.x: me.transform(Matrix.Rotation(math.pi / 2, 4, "Z")); ws = [v.co for v in me.vertices]; lo = Vector(map(min, *ws)); hi = Vector(map(max, *ws))
    k = length / (hi.x - lo.x)                                                   # 길이를 새 광차 2.05 m 에 · 폭은 Meshy 가 0.89 로 좁혀서 1.0 으로 늘림(사용자 선택 때 말함)
    me.transform(Matrix.Diagonal((k, width / ((hi.y - lo.y) * k), k, 1)) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
    m = bpy.data.materials.new("PM_meshy_car2"); m.use_nodes = True; nt = m.node_tree; b = next(n_ for n_ in nt.nodes if n_.type == "BSDF_PRINCIPLED")
    def img(r, data):
        n_ = nt.nodes.new("ShaderNodeTexImage"); n_.image = bpy.data.images.load(files[r]); n_.image.colorspace_settings.name = "Non-Color" if data else "sRGB"; return n_
    nt.links.new(img("diff", False).outputs["Color"], b.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(img("arm", True).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img("nor_gl", True).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    me.materials.clear(); me.materials.append(m)
    car = bpy.data.objects.new("MineCar", me); sc.collection.objects.link(car); own([car]); return car
def on_path(path, x):                                 # 꺾은 선에서 x 자리의 (점, 방향)
    for a, b in zip(path, path[1:]):
        if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
            t = (x - a[0]) / (b[0] - a[0]); return Vector((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0)), (Vector(b) - Vector(a)).normalized()
car_p, car_d = on_path(RAIL_W, -4.85); car_yaw = math.atan2(car_d.y, car_d.x)
rail_top = sum(floor_z(car_p.x + car_d.x * s, car_p.y + car_d.y * s) for s in (-0.6, 0, 0.6)) / 3 - 0.03 + 0.19   # 침목(묻힘 0.03 · 두께 0.1) + 레일 0.09
place(meshy_car(MESHY_CAR), (car_p.x, car_p.y, rail_top - 0.02), car_yaw)          # 밑 = 바퀴 테 (레일 윗면보다 조금 아래, 레일 안쪽)
colp("Cart", (car_p.x, car_p.y, rail_top + 0.6), (2.1, 1.02, 1.2), car_yaw)

# ================= B4 강철 아치 + 판자 — 출구 다섯, 광장 경계에서 굴 안으로 0.3 · 1.4 m. 바위를 광선으로 재서 다리·아치를 안쪽으로 맞춘다
EXITS = [("NW", (-7.7, 1.4), (-14.7, 2.8)), ("NE", (7.7, 0.7), (13.3, 2.8)), ("W", (-7.7, -2.1), (-16.8, -2.1)),
         ("E", (7.7, -3.64 + (7.7 - 5.6) / (13.3 - 5.6) * (-5.6 + 3.64)), (13.3, -5.6)), ("S", (0.0, -5.46), (1.05, -18.2))]
def arch_pair(tag, mouth, toward, width=3.1, height=3.15, gap=1.1):
    d = Vector((toward[0] - mouth[0], toward[1] - mouth[1], 0)).normalized(); lat = Vector((-d.y, d.x, 0))
    r = width / 2; leg = height - r
    shape = [(-r, 0.0), (-r, leg)] + [(-r * math.cos(t), leg + r * math.sin(t)) for t in [math.pi * k / 10 for k in range(1, 10)]] + [(r, leg), (r, 0.0)]
    bm = bmesh.new(); pb = bmesh.new(); arches = []
    for s_ in (0.3, 0.3 + gap):
        c = Vector((mouth[0], mouth[1], 0)) + d * s_; fz = floor_z(c.x, c.y); o = Vector((c.x, c.y, fz + 1.5))
        pts = []
        for u, v in shape:
            p = Vector((c.x, c.y, fz)) + lat * u + Vector((0, 0, v))
            if v < 0.01: p.z = floor_z(p.x, p.y) - 0.03                         # 다리 밑 = 그 자리 바닥
            else:
                dv = p - o; hitd = ray(o, dv, dv.length + 1.0)
                if hitd < dv.length + 0.08: p = o + dv.normalized() * (hitd - 0.08)   # 바위에 박히면 안쪽으로 당김
            pts.append(p)
        for a, b in zip(pts, pts[1:]): mp.ibeam(bm, a, b)
        arches.append((pts, o))
    (pa, oa), (pb_, ob) = arches
    for k in range(2, len(shape) - 2):                                         # 판자: 두 아치의 같은 점 사이, 바깥쪽 0.1 m
        m_ = (pa[k] + pb_[k]) / 2; out = (m_ - (oa + ob) / 2); out.z = max(out.z, 0.0); out = out.normalized()
        mp.box(pb, m_ + out * 0.1, (0.2, gap + 0.1, 0.035), Matrix((d.cross(out), d, out)).transposed())   # 판자 축: 아치 따라 · 굴 따라 · 바깥 — 끝은 아치 날개 뒤에 숨는다(더 길면 광장 쪽 바위에서 이빨처럼 삐져나왔다)
    own([mp.group("PROP_Arch_" + tag, [mp.obj("Arch_" + tag, bm, M["steel"]), mp.obj("Lagging_" + tag, pb, M["plank"])])])
for tag, mouth, toward in EXITS: arch_pair(tag, mouth, toward)

# ================= P1 관 · 밸브 — 북쪽 벽 3.6 m, 서쪽 벽에서 동쪽 벽까지 (pipe02 1.95 m × 8 + 가운데 밸브 pipe08), 이음매마다 벽 받침
def wall_y(x, z, y0, sgn):                           # 북(+1)·남(−1) 벽까지 y
    return y0 + sgn * ray((x, y0, z), (0, sgn, 0))
def wall_x(y, z, x0, sgn):
    return x0 + sgn * ray((x0, y, z), (sgn, 0, 0))
PZ = 3.6; PL = extent("modular_industrial_pipes_01", "pipe02").z; VL = extent("modular_industrial_pipes_01", "pipe08").z
xs = [-7.2 + k * 0.25 for k in range(58)]
py = min(wall_y(x, PZ, 2.0, 1) for x in xs) - 0.14
x = -(4 * PL + VL / 2)
for k in range(9):
    part, L = ("pipe08", VL) if k == 4 else ("pipe02", PL)
    ph("modular_industrial_pipes_01", part, RY(90), (x, py, PZ), (0, 0.5, 0.5), name="Pipe_%d" % k)
    if abs(x) < 7.3 and k != 5:                                               # 이음매 받침 (벽까지 납작한 쇠 + 관 둘레 띠)
        wy = wall_y(x, PZ, py, 1)
        br = bmesh.new(); mp.box(br, (x, (py + wy) / 2 + 0.03, PZ), (0.05, wy - py + 0.06, 0.05)); mp.box(br, (x, py, PZ), (0.06, 0.24, 0.24))
        own([mp.obj("PipeBracket_%d" % k, br, M["dark_steel"])])
    x += L

# ================= P2 전선 — 남쪽 벽 2.8 m (x −7.55..−3 · 3..6): 곧은 줄(벽이 가장 튀어나온 자리 앞) · 0.61 m 토막 이음매마다 고정쇠 + 벽까지 받침
#   (토막마다 벽 굴곡을 따르게 했더니 토막끼리 어긋나 멀리서 점선처럼 보였다 — 09-27 캡처)
CZ = 2.8; CL = extent("modular_electric_cables", "cable_straight_long").z; R = RZ(180) @ RY(90)
for a, b in ((-7.55, -3.0), (3.0, 6.0)):
    cy = max(wall_y(a + t * (b - a) / 20, CZ, -3.5, -1) for t in range(21)) + 0.006
    x = a; k = 0
    while x < b - 0.05:
        ph("modular_electric_cables", "cable_straight_long", R, (x, cy, CZ), (0, 0, 0.5), name="Cable_%d_%d" % (int(a), k))
        ph("modular_electric_cables", "cable_mount", R, (x, cy - 0.002, CZ), (0.5, 0, 0.5), name="CableMount_%d_%d" % (int(a), k))
        wy = wall_y(x, CZ, cy, -1)
        if cy - wy > 0.03:
            br = bmesh.new(); mp.box(br, (x, (cy + wy) / 2 - 0.02, CZ + 0.03), (0.03, cy - wy + 0.04, 0.02)); own([mp.obj("CableHook_%d_%d" % (int(a), k), br, M["dark_steel"])])
        x += CL; k += 1

# ================= P8 통풍관 — 동북 모서리 천장 밑: 북쪽 벽 따라 x 4.5 → 동쪽 벽, 동쪽 벽 따라 → y 2.4. 시작에 선풍기, 이음매마다 걸이
DL = extent("modular_airduct_circular_01", "circular_triple").y; DR = 0.185
dy = min(wall_y(xx, 4.0, 2.0, 1) for xx in (4.5, 5.5, 6.5, 7.3)) - DR - 0.08
dx = min(wall_x(yy, 4.0, 5.0, 1) for yy in (2.4, 3.0, 3.6, dy)) - DR - 0.08
cmin = min(ceil_z(xx, yy) for xx, yy in ((4.5, dy), (5.8, dy), (dx, dy), (dx, 3.2), (dx, 2.4)))
DZ = cmin - 0.45
def hang(tag, p, R):                                 # 걸이 (고리 + 위로 0.49 m) — 천장이 더 높으면 줄을 더한다
    ph("modular_airduct_circular_01", "circular_brace", R, p, (0.5, 0.5, 0.186 / 0.672), name="DuctBrace_" + tag)   # 고리 가운데 = 관 가운데 (고리 −0.186 .. 걸이 +0.486)
    if ceil_z(p[0], p[1]) > p[2] + 0.5:
        ph("modular_airduct_circular_01", "brace_extention_wires", R, (p[0], p[1], p[2] + 0.45), (0.5, 0.5, 0), name="DuctWires_" + tag)
x = 4.5; k = 0
ph("modular_airduct_circular_01", "circular_fan", RZ(90), (x, dy, DZ), (1, 0.5, 0.5), name="DuctFan")
while x < dx + DR:
    ph("modular_airduct_circular_01", "circular_triple", RZ(90), (x, dy, DZ), (0, 0.5, 0.5), name="DuctN_%d" % k)
    hang("N%d" % k, (x + 0.1, dy, DZ), RZ(90)); x += DL; k += 1
y = dy + DR
for k in range(max(1, round((y - 2.4) / DL))):                               # 동북 굴 입구(y 2.35 까지) 위로는 안 내려간다
    ph("modular_airduct_circular_01", "circular_triple", Matrix.Identity(3), (dx, y, DZ), (0.5, 1, 0.5), name="DuctE_%d" % k)
    hang("E%d" % k, (dx, y - 0.3, DZ), Matrix.Identity(3)); y -= DL

# ================= P4 광장 전등 둘 — 철망 벽 등(sconce_a)을 거꾸로: 전구가 게임 전등 자리(SLOT_Light)에, 판은 그 위, 판에서 천장까지 쇠관
for nm, o in sorted(SLOT.items()):
    if not nm.startswith("SLOT_Light_"): continue
    p = o.matrix_world.translation
    if not (-7.7 < p.x < 7.7 and -5.46 < p.y < 4.34): continue
    plate = p.z + 0.12
    ph("industrial_caged_sconce", "sconce_a", RX(90), (p.x, p.y, plate), (0.5, 0.5, 1), name="Lamp_" + nm[5:])
    tube = bmesh.new(); mp.rod(tube, (p.x, p.y, plate), (p.x, p.y, ceil_z(p.x, p.y, plate - 0.2) + 0.1), 0.02, seg=8)
    own([mp.obj("LampTube_" + nm[5:], tube, M["dark_steel"])])

# ================= 판 셋 · 형광등
def sign_at(lines, loc, yaw, **kw):
    s_ = own([mp.sign(M, lines, font=FONT, **kw)]); place(s_, loc, yaw); return s_
yw = min(wall_y(xx, 2.0, 2.0, 1) for xx in (-3.45, -3.0, -2.55))
sign_at(["안전제일"], (-3.0, yw - 0.03, 2.0), 0.0, size=(0.9, 0.35), text_h=0.18)                                     # B7 북쪽 벽
sign_at(["케이지 승강장", "신호 전 승차 금지"], (-1.3, -1.1 - 0.13, 1.6), 0.0, size=(0.9, 0.5), board=(0.95, 0.8, 0.1), ink=(0.05, 0.05, 0.05), text_h=0.1)   # B8 케이지 서남 기둥 (글자 지어냄)
xe = min(wall_x(yy, 1.5, 5.0, 1) for yy in (-2.3, -1.8, -1.3))
sign_at(["작업현황", "1편 ___  2편 ___", "화약 ___"], (xe - 0.03, -1.8, 1.5), -math.pi / 2, size=(1.0, 0.7), ink=(0.1, 0.15, 0.45), text_h=0.09)   # B9 동쪽 벽
fl = ph("caged_hanging_light", "caged_hanging_light", RZ(90), (xe - 0.35, -1.8, ceil_z(xe - 0.35, -1.8) + 0.02), (0.5, 0.5, 1), name="Fluorescent")   # P3 — 빛 없는 등(꺼진 형광등): 빛나는 그림을 뺀다
for m in fl.data.materials:
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b: b.inputs["Emission Strength"].default_value = 0.0
    for l in [l for l in m.node_tree.links if l.to_socket.name.startswith("Emission")]: m.node_tree.links.remove(l)

# ================= 공구 모퉁이 (남서) — 벽에 기대 둔 공구 넷 · 선반 · 상자 · 양동이 · 사다리
def lean(pid, part, x, yaw_extra=0.0, tilt=14):
    """남쪽 벽에 기대기: 세운 채로 벽 쪽(−Y)으로 tilt° 눕혀, 밑은 바닥 · 위는 벽"""
    R = RX(tilt) @ RZ(yaw_extra); h = extent(pid, part, R)                  # X 로 +tilt° = 위 끝이 −Y(벽) 쪽
    wy = wall_y(x, 1.0, -3.5, -1)
    o = ph(pid, part, R, (x, wy + 0.03, floor_z(x, wy + h.y) - 0.01), (0.5, 0, 0), name=part)
    return o
for x, (pid, part, yx) in zip((-5.7, -5.35, -5.0, -4.65), (("rusted_spade_01", "rusted_spade_01", 0), ("crowbar_01", "crowbar_01", 90),
                                                          ("sledgehammer_01", "sledgehammer_01", 0), ("picke_dirty_01", "picke_dirty_01", 0))):
    lean(pid, part, x, yx)
ys = wall_y(-6.8, 1.0, -3.5, -1)
ph("worn_metal_rack", "worn_metal_rack", Matrix.Identity(3), (-6.8, ys + 0.03, floor_z(-6.8, ys + 0.33)), (0.5, 0, 0), name="Rack")
colp("Rack", (-6.8, ys + 0.33, floor_z(-6.8, ys + 0.33) + 0.95), (0.95, 0.62, 1.9))
xw = wall_x(-4.3, 0.3, -5.0, -1)                                            # 상자: 긴 쪽을 서쪽 벽 따라 (서쪽 굴 비우는 띠 y −3.75 밖)
crate_at = Vector((xw + 0.03 + 0.21, -4.3, floor_z(xw + 0.25, -4.3)))
assembly("wooden_crate_01", ("wooden_crate_01", "wooden_crate_01_lid", "wooden_crate_01_latch"), Matrix.Translation(crate_at) @ RZ(90).to_4x4())
colp("Crate", (crate_at.x, crate_at.y, crate_at.z + 0.17), (0.42, 0.84, 0.34))
assembly("wooden_bucket_01", ("wooden_bucket_01", "wooden_bucket_01_handle"), Matrix.Translation((-4.0, -4.9, floor_z(-4.0, -4.9))) @ RZ(20).to_4x4())
yl = wall_y(-2.5, 1.0, -3.5, -1)
assembly("wooden_ladder", ("wooden_ladder_steps", "wooden_ladder_supports"), Matrix.Translation((-2.5, yl + 0.3, floor_z(-2.5, yl + 0.3))))

# ================= B5 굴 안 둥근 통나무 동발 — make_booth 의 SLOT_TimberSet_<i>(X = 가로 · 크기 = (기둥 반간격, 1, 기둥 높이)) 마다, 40 m 칸으로 묶음
tmb = {}
for nm, o in SLOT.items():
    if not nm.startswith("SLOT_TimberSet_"): continue
    mw = o.matrix_world; P = mw.translation.copy(); lat = (mw.to_3x3() @ Vector((1, 0, 0))); hw = lat.length; lat.normalize()
    ph_ = (mw.to_3x3() @ Vector((0, 0, 1))).length
    key = "g%d_%d" % (math.floor(P.x / CHUNK_M), math.floor(P.y / CHUNK_M)); bm = tmb.setdefault(key, bmesh.new())
    for s_ in (-1, 1):                                                       # 기둥 둘 (지름 0.22, 안쪽으로 조금 기욺) + 위 통나무(지름 0.24, 양 끝이 바위에 조금 박힘)
        mp.rod(bm, P + lat * (s_ * hw) - Vector((0, 0, 0.05)), P + lat * (s_ * (hw - 0.06)) + Vector((0, 0, ph_)), 0.11, seg=10)
    mp.rod(bm, P + lat * -(hw + 0.2) + Vector((0, 0, ph_ + 0.12)), P + lat * (hw + 0.2) + Vector((0, 0, ph_ + 0.12)), 0.12, seg=10)
n_sets = sum(1 for nm in SLOT if nm.startswith("SLOT_TimberSet_"))
for key, bm in tmb.items():
    me = bpy.data.meshes.new("TMB_" + key); bm.to_mesh(me); bm.free(); me.materials.append(M["log"])
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new("TMB_" + key, me); sc.collection.objects.link(o); own([o])

# ================= 마무리: 글자 → 그물 · UV · 세기 · 내보내기
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in PROPS.objects if o.type == "FONT"]:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); n = bpy.data.objects.new(o.name, me); PROPS.objects.link(n)
    n.parent = o.parent; n.matrix_parent_inverse = o.matrix_parent_inverse.copy(); n.matrix_basis = o.matrix_basis.copy()
    bpy.data.objects.remove(o, do_unlink=True)
for o in PROPS.objects:
    if o.type == "MESH" and o.data.materials and o.data.materials[0] and "uv_m" in o.data.materials[0]:
        mp.box_uv(o.data, 1.0 / o.data.materials[0]["uv_m"])
def tris(objs):
    n = 0
    for o in objs:
        if o.type == "MESH": n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n
props = [o for o in PROPS.objects if o.type == "MESH" and not o.name.startswith(("COLP_", "TMB_"))]
n_props, n_tmb = tris(props), tris([o for o in PROPS.objects if o.name.startswith("TMB_")])
print("CHECK plaza props: %d objects · %d tris (max %d) · colliders %s · timber sets %d in %d chunks (%d tris)"
      % (len(props), n_props, TRI_MAX, sorted(o.name for o in PROPS.objects if o.name.startswith("COLP_")), n_sets, len(tmb), n_tmb))
assert n_props <= TRI_MAX, "FAIL: 광장 물건 삼각형 %d > %d" % (n_props, TRI_MAX)
assert n_sets > 300, "FAIL: SLOT_TimberSet 이 booth_map 에 없다 (make_booth.py 다시)"

for im in {n.image for o in PROPS.objects if o.type == "MESH" for m in o.data.materials if m and m.node_tree for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}:
    f = os.path.normpath(bpy.path.abspath(im.filepath))
    if not f.startswith(os.path.normpath(PH)): continue                         # 쓰는 Poly Haven 그림만 Assets 안 복사본으로 (glTF 가 그 파일을 가리킨다)
    pid = os.path.relpath(f, PH).split(os.sep)[0]; dst = os.path.join(SRC, pid, "textures"); os.makedirs(dst, exist_ok=True)
    nf = os.path.join(dst, os.path.basename(f))
    if not os.path.exists(nf): shutil.copy(f, nf)
    im.filepath = nf
for o in bpy.context.view_layer.objects: o.select_set(False)
for o in PROPS.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLTF_SEPARATE", use_selection=True, export_keep_originals=True, export_apply=True, export_yup=True)
doc = json.load(open(OUT, encoding="utf-8"))
uris = [im.get("uri", "") for im in doc.get("images", [])]
bad = [u for u in uris if not os.path.exists(os.path.join(ART, u.replace("%20", " "))) or u.startswith("..")]
print("CHECK plaza export: %s (%d KB bin) · nodes %d · images %d outside/missing %d %s"
      % (os.path.basename(OUT), os.path.getsize(OUT[:-5] + ".bin") // 1024, len(doc["nodes"]), len(uris), len(bad), bad[:4]))
assert not bad, "FAIL: 그림 경로"

# ================= 확인 그림 (게임 빛 아님: EEVEE · 전등 500 W · 헤드램프)
if not FAST:
    os.makedirs(CHECK, exist_ok=True)
    for o in MAP + list(PROPS.objects):                                        # 새 모습만: 옛 네모 갱목 · 부딪힘 상자는 안 보인다 (Unity 와 같게)
        if o.name.startswith(("COL_", "NAV", "PRP_Timber_", "COLP_")): o.hide_render = True
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
    next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0.02, 0.02, 0.02, 1)
    for nm in ("SLOT_Light_1", "SLOT_Light_2"):
        L = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); L.data.energy = 500; L.data.color = (1.0, 0.72, 0.42)
        L.location = SLOT[nm].matrix_world.translation - Vector((0, 0, 0.3)); sc.collection.objects.link(L)
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
    head = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(head)
    head.data.energy = 900; head.data.spot_size = math.radians(80); head.data.color = (1.0, 0.93, 0.82)
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    def shot(name, eye, look, lens=18):
        eye, look = Vector(eye), Vector(look); q = (look - eye).to_track_quat("-Z", "Y")
        cam.location = eye; cam.rotation_euler = q.to_euler(); cam.data.lens = lens; cam.data.clip_start = 0.05
        head.location = eye + Vector((0, 0, 0.1)); head.rotation_euler = q.to_euler()
        sc.render.filepath = os.path.join(CHECK, name + ".png"); bpy.ops.render.render(write_still=True)
    shot("1_spawn_n", (0, -3.15, 1.7), (0, 4, 1.8))
    shot("2_west", (2.0, -1.5, 1.7), (-7.7, 0.5, 1.2))
    shot("3_east", (-2.0, -1.5, 1.7), (7.7, 0.5, 1.8))
    shot("4_south", (0, 2.5, 1.7), (-3, -5.4, 1.0))
    shot("5_ne_duct", (2.0, 0.5, 1.7), (7.0, 3.5, 3.8))
    shot("6_tunnel_timber", (-14.7, 2.9, 1.7), (-24, 4.8, 1.6))
    head.data.energy = 0
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 19; cam.location = (0, -0.5, 30); cam.rotation_euler = (0, 0, 0)
    for o in MAP:
        if o.type == "MESH" and o.name.startswith("SHL_"): o.hide_render = True
    next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0.35, 0.33, 0.3, 1)
    sc.render.filepath = os.path.join(CHECK, "0_top.png"); bpy.ops.render.render(write_still=True)
    print("CHECK plaza renders -> %s" % CHECK)
