"""MAP4 장면 시안 — 장면 하나를 블록아웃으로 짓고 눈높이 1인칭 그림을 뽑는다 (제안서 docs/제안서_MAP4_장면부터_짠_맵.md 6절 차례 2).
  SCENE=9 "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/scene_mock.py
  SCENE = 9 (거대한 빈 공간 = 1편 그것의 굴) · 6 (케이지 승강장) · 1 (쇠동발 숲) · 3 (광차 싣는 곳, Fab 모델 — build/tex_test/fab 필요) · 7 (바람문 두 짝, Fab) · 8 (무너진 기둥 굴, Fab) · 2 (낮은 채탄 막장, Fab) · t (질감 시험 벽) · f (Fab 갱도 조각)
재질은 부스 맵과 같다(Assets/Tunnel/Pieces/piece_straight.gltf 에서 가져옴 — 안 고친다). 칠 · 콘크리트 · 전구는 여기서 만든 단색 재질.
동굴 만드는 법도 make_booth.py 와 같다: 공기 덩어리 → 복셀 리메시 → 면 뒤집기 → 벽을 바위 쪽으로만 파는 잡음.
출력: build/check_map4/scene<번호>/ — fp_*_lamp.png(머리등 + 그 장면의 전등 + 눈이 어둠에 익은 정도, 게임에 가깝게) · fp_*_shape.png(모양을 보려고 밝힘)
  · side.png · top.png(1.7 m 사람 크기 막대).
카메라 = 게임과 같은 세로 화각 80° · 눈 1.7 m. 머리등 = 스포트 60° · 14 m (Tuning.LAMP_ANGLE_DEG · LAMP_RANGE)."""
import bpy, bmesh, os, math, random, json
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
SCENE = os.environ.get("SCENE", "9")
OUT = os.path.join(ROOT, "build", "check_map4", "scene" + SCENE)
VOXEL, EYE, FOV, LAMP_DEG, LAMP_M = 0.25, 1.7, 80.0, 60.0, 14.0
random.seed(int(SCENE) if SCENE.isdigit() else SCENE)
MAP = SCENE == "m"                                                    # 맵 모드 (SCENE=m) — 통과한 장면들을 한 맵에 놓고 굴로 잇는다. 맨 아래 map4() 참고
LOWEST = 2.1 if MAP else 0.0                                          # 맵 모드: 천장 최소 (사용자 10-01 "높낮이를 낮게 구성하지 말아라" — 저절로 숙이며 지나가면 짜증) · 시안 그림은 옛 높이 그대로
ZT, PASS, AIR, SHELL = Matrix.Identity(4), None, [], None             # 지금 짓는 구역의 자리 · 단계("air" 바위 공기만 모음 / "dress" 소품) · 모은 공기 · 합친 바위 굴
class ZoneAir(Exception): pass

# ================= 재질 (부스 맵과 같은 것 + 단색)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(PIECES, "piece_straight.gltf"))
MAT = {m.name: m for m in bpy.data.materials}
M_WALL, M_FLOOR, M_TIMB, M_ROCK, M_RUST = (MAT[n] for n in ("MAT_RockWall_EXPORT", "MAT_Floor_EXPORT", "MAT_Timber_EXPORT", "MAT_Rock_EXPORT", "MAT_RustyMetal_EXPORT"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene

METAL = {"new": None, "old": None, "wet": False}                         # 맵 모드의 쇠 사진 재질 (map4() 가 채운다) · wet = 물 가까운 방을 짓는 중
def paint(name, rgb, rough=0.7, metal=0.0, emit=0.0):
    if metal > 0 and not emit and METAL["new"]:                          # 쇠 칠 → 사진 (사용자 10-01: 쇠 = 이어 붙인 철판, 물 가까운 곳 · 깊은 층 = 칠 벗겨지고 녹슨 쇠)
        base = METAL["old"] if METAL["wet"] and METAL["old"] else METAL["new"]; k = max(rgb)
        if k > 0 and (k - min(rgb)) / k > 0.5:                           # 색이 진한 칠(노란 문 · 빨간 관 · 사다리): 색은 그대로 두고 사진의 결(노멀 · 거칠기)만 — 색을 곱하면 어두운 철판에 묻혀 칠 색이 죽는다
            t = base.copy(); t.name = name; b = next(n for n in t.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            for l in list(b.inputs["Base Color"].links): t.node_tree.links.remove(l)
            b.inputs["Base Color"].default_value = (*rgb, 1); return t
        return tint(base, tuple(c / k for c in rgb) if k > 0 else (1, 1, 1), name)   # 회색 · 풀색 칠: 사진에 색조만 곱한다
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*rgb, 1); p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metal
    if emit: p.inputs["Emission Color"].default_value = (*rgb, 1); p.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*rgb, 1); return m

def box(bm, c, s, rot=None):
    """c = 가운데, s = 크기 (x, y, z), rot = 회전 행렬(선택)"""
    vs = []
    for dx in (-1, 1):
        for dy in (-1, 1):
            for dz in (-1, 1):
                p = Vector((dx * s[0] / 2, dy * s[1] / 2, dz * s[2] / 2))
                vs.append(bm.verts.new(Vector(c) + (rot @ p if rot else p)))
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])

def blob(bm, c, r, sub=3):
    """찌그러진 공 (타원체)"""
    g = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    for v in g["verts"]: v.co = Vector((v.co.x * r[0] + c[0], v.co.y * r[1] + c[1], v.co.z * r[2] + c[2]))

def obj(name, bm, mat):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(mat); return o

def box_uv(me, per_m=0.5):
    """상자 투영 UV — 면이 가장 많이 향한 축을 버리고 나머지 두 축을 m 단위로"""
    if not me.uv_layers: me.uv_layers.new()
    uv = me.uv_layers.active.data
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i])); a, b = [i for i in range(3) if i != ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (co[a] * per_m, co[b] * per_m)

def column(bm, cx, cy, r, z0=-1.0, z1=19.0, seg=14, ring=0.8):
    """바닥에서 천장까지 선 바위 기둥 — 고리를 쌓고 반지름을 흔든다 (아래·위가 조금 넓다)"""
    rings = []
    for j in range(int((z1 - z0) / ring) + 1):
        z = z0 + j * ring; flare = 1 + 0.35 * (abs(z - 7) / 9) ** 2
        rings.append([bm.verts.new((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 1.2, z))
                      for a, rr in ((2 * math.pi * i / seg, r * flare * random.uniform(0.82, 1.12)) for i in range(seg))])
    for A, B_ in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B_[(i + 1) % seg], B_[i]))

def shell(bm, carve, big=None, big_m=1.6):
    """공기 덩어리 → 안에서 보는 바위 동굴. big = (반폭 x, 반폭 y) 안의 벽 · 천장만 크게 굴곡 (굴 · 바닥은 안 넓힌다)"""
    if MAP:                                                           # 맵 모드: 공기는 맵 전체 한 덩어리로 모으고(이음새 · 막힌 끝이 없게), 소품 단계엔 합친 굴을 돌려준다
        if PASS == "air": bm.transform(ZT); AIR.append((bm, carve, (ZT.copy(), big, big_m) if big else None)); raise ZoneAir
        return SHELL
    air = obj("AIR", bm, M_WALL)
    rm = air.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
    cave_me = bpy.data.meshes.new_from_object(air.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(air, do_unlink=True)
    b = bmesh.new(); b.from_mesh(cave_me); bmesh.ops.reverse_faces(b, faces=b.faces); b.normal_update(); b.to_mesh(cave_me); b.free()
    cave = bpy.data.objects.new("CAVE", cave_me); sc.collection.objects.link(cave)
    nz = np.empty(len(cave_me.vertices) * 3); cave_me.vertices.foreach_get("normal", nz); nz = nz.reshape(-1, 3)[:, 2]
    w = np.where(nz > 0.6, 0.1, 1.0); vg = cave.vertex_groups.new(name="carve")
    for v in np.unique(w): vg.add(np.nonzero(w == v)[0].tolist(), float(v), "REPLACE")
    tex = bpy.data.textures.new("rocknoise", type="CLOUDS"); tex.noise_scale = 1.6; tex.noise_depth = 3
    dm = cave.modifiers.new("carve", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"
    dm.strength = carve; dm.mid_level = 1.0; dm.direction = "NORMAL"; dm.vertex_group = "carve"
    if big:
        co = np.empty(len(cave_me.vertices) * 3); cave_me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        sel = (np.abs(co[:, 0]) < big[0]) & (np.abs(co[:, 1]) < big[1]) & (nz <= 0.6) & (co[:, 2] > 0.4)
        vg2 = cave.vertex_groups.new(name="big"); vg2.add(np.nonzero(sel)[0].tolist(), 1.0, "REPLACE")
        tex2 = bpy.data.textures.new("bignoise", type="CLOUDS"); tex2.noise_scale = 5.0; tex2.noise_depth = 2
        dm2 = cave.modifiers.new("carve_big", "DISPLACE"); dm2.texture = tex2; dm2.texture_coords = "GLOBAL"
        dm2.strength = big_m; dm2.mid_level = 1.0; dm2.direction = "NORMAL"; dm2.vertex_group = "big"
    me = bpy.data.meshes.new_from_object(cave.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(cave, do_unlink=True)
    me.materials.append(M_WALL); me.materials.append(M_FLOOR)
    nrm = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", nrm)
    me.polygons.foreach_set("material_index", (nrm.reshape(-1, 3)[:, 2] > 0.55).astype(np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    box_uv(me, 0.35)
    o = bpy.data.objects.new("SHELL", me); sc.collection.objects.link(o); return o

def text(body, loc, size, mat, rot=(math.radians(90), 0, 0)):
    """벽에 칠한 글자 — 한글은 맑은 고딕 (기본 글꼴엔 한글이 없다)"""
    cu = bpy.data.curves.new("T", "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.extrude = 0.005
    cu.font = bpy.data.fonts.load("C:/Windows/Fonts/malgunbd.ttf")
    o = bpy.data.objects.new("TEXT", cu); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o); cu.materials.append(mat); return o

# ================= 장면 9 — 거대한 채굴 빈 공간 = 1편 그것의 굴
# 장면 카드 9. 참고(09-30): 스톱의 나무 버팀목 · 벽 따라 발판·계단 · 돌 더미 · 남은 바위 기둥 + 한국 탄광 급경사 탄층 → 천장 위 비스듬한 틈 = 그것이 내려오는 곳.
def scene9():
    bm = bmesh.new()
    box(bm, (0, 0, 6), (40, 26, 12))                          # 큰 방 40 × 26, 천장 12 (09-30 사용자 "더 크게" — 처음 26 × 18 · 10)
    blob(bm, (-6, 1, 11), (13, 9, 5.5))                       # 둥근 천장 — 가운데가 16 m 까지
    blob(bm, (10, -4, 10), (9, 7, 5))
    for i in range(20):                                       # 벽의 들쭉날쭉한 굴곡 — 네모 방으로 안 보이게
        t = i / 20 * 2 * math.pi; x, y = 20 * math.cos(t), 13 * math.sin(t)
        blob(bm, (x * random.uniform(0.9, 1.05), y * random.uniform(0.9, 1.05), random.uniform(2.5, 7)), (random.uniform(3, 5), random.uniform(2.5, 4), random.uniform(3.5, 6)), 2)
    for k in range(9):                                        # 급경사 탄층 틈: 천장에서 북쪽으로 비스듬히 위로 — 공을 이어 울퉁불퉁하게
        t = k / 8; blob(bm, (4 + random.uniform(-0.6, 0.6), 7 + 17 * t, 10.5 + 12 * t), (3 - t, 2, 2.4), 2)
    box(bm, (-26, 4, 3 + 1.3), (13, 2.8, 2.6))                # 들어오는 옛 굴 — 발판 높이 3 m 에서 방으로 나온다
    box(bm, (26, -8, 1.3), (13, 3.0, 2.6))                    # 나가는 굴 — 바닥 높이, 반대편 (막다른 방이 아니다)
    box(bm, (-4, 14.2, 1.3), (1.35, 3.0, 2.6))                # 그것이 드나드는 큰 틈 (2.6 × 1.35 m) 둘
    box(bm, (20.2, 5, 1.3), (3.0, 1.35, 2.6))
    shell(bm, 0.6, big=(22, 15))

    bm = bmesh.new()                                          # 남은 바위 기둥 셋 — 시야를 끊는다
    for c, r in (((-5, -4), 1.8), ((6, 5), 1.6), ((12, -6), 1.5)): column(bm, c[0], c[1], r)
    for i in range(55):                                       # 무너진 돌 더미 — 벽 밑과 가운데 한 무더기
        c = (random.uniform(-6, 9), random.uniform(-10, -2)) if i < 20 else (random.uniform(-18, 18), random.choice((-11.5, 11.5)) + random.uniform(-1, 1))
        s = random.uniform(0.4, 1.3); blob(bm, (c[0], c[1], s * 0.3), (s, s * random.uniform(0.7, 1.3), s * 0.6), 1)
    box_uv(obj("ROCKS", bm, M_ROCK).data, 0.5)

    bm = bmesh.new()
    box(bm, (-18, 4, 2.85), (4.4, 3.0, 0.3))                  # 옛 굴 입구의 나무 발판 (높이 3 m)
    for k in range(4): box(bm, (-19.9 + (k % 2) * 3.8, 2.8 + (k // 2) * 2.4, 1.35), (0.25, 0.25, 2.7))
    for s in range(15): box(bm, (-19.4, 2.3 - s * 0.5, 3.0 - (s + 1) * 0.2 + 0.1), (1.2, 0.5, 0.2))   # 벽 따라 내려가는 계단 (3 m 를 7.5 m 에)
    box(bm, (-18.8, -1.2, 2.4), (0.08, 8.1, 0.08), Matrix.Rotation(math.atan2(3, 7.5), 3, "X"))       # 난간
    for x, z, a in ((-14, 7.5, 8), (-6, 9.0, -6), (2, 8.0, 5), (10, 9.5, -4), (16, 7.0, 7)):         # 벽 사이에 걸친 나무 버팀목
        box(bm, (x, 0, z), (0.35, 27, 0.35), Matrix.Rotation(math.radians(a), 3, "Y") @ Matrix.Rotation(math.radians(a * 0.4), 3, "X"))
    box_uv(obj("TIMBER", bm, M_TIMB).data, 0.8)
    bm = bmesh.new()                                          # 넘어진 광차 하나
    box(bm, (12, -9.5, 0.5), (1.6, 0.9, 0.9), Matrix.Rotation(math.radians(70), 3, "X") @ Matrix.Rotation(math.radians(25), 3, "Z"))
    box_uv(obj("CART", bm, M_RUST).data, 1.0)
    return dict(
        lights=[("FAR", (30, -8, 2.3), 150, (1.0, 0.62, 0.3), 0.1, True)],   # 나가는 굴 저편의 운반갱도 전등 — 돌아갈 곳이 멀리 작게
        adapt=((0, 0, 8), 400, 16), fills=([(-13, -7), (-13, 7), (13, -7), (13, 7)], 9, 6000, 5),
        shots=[("fp_1_entrance", (-20.8, 4, 3 + EYE), (6, -4, 1.5)),           # 옛 굴에서 나와 발판 위 — 처음 보는 모습
               ("fp_2_floor_back", (4, -2, EYE), (-18, 3, 5)),                 # 바닥 가운데에서 들어온 쪽을 되돌아봄
               ("fp_3_pillar_exit", (-7.5, -6.8, EYE), (21, -8, 1.6)),         # 기둥 옆에서 나가는 굴 쪽 — 가로지를까 벽을 따라 돌까
               ("fp_4_look_up", (3, 8, EYE), (4, 17, 15))],                    # 천장 위 비스듬한 탄층 틈을 올려다봄
        people=[(-18, 4, 3), (4, -2, 0)], ortho=80, side_z=6)

# ================= 장면 6 — 케이지 승강장 (갱저) = 모든 층의 시작 · 끝
# 장면 카드 6 · 15 + ART-1 실제 갱도 사진 13장의 공통점(09-27): 강철 틀 + 판자 덧댐(한국 사진엔 벽돌 · 흰 칠이 없다) · 철망 케이지 문 + 강철 틀
# · 천장을 가로지르는 관 · 벽을 따라 늘어진 케이블 · 젖은 바닥 · 고정 등은 케이지 앞 1~2개 · 레일 · 광차 · 경고판 · 매달린 쇠사슬.
# 일어나는 일: 벨을 누르면 케이지가 올 때까지(제안 20 s) 등 뒤 어두운 굴 셋을 버틴다. 층 번호를 크게 칠해 어느 층인지 안다.
def scene6():
    M_STEEL = paint("steel", (0.18, 0.19, 0.2), 0.45, 0.9); M_YEL = paint("yellow", (0.85, 0.62, 0.05), 0.5, 0.3)
    M_RED = paint("red", (0.55, 0.06, 0.04), 0.5, 0.3)
    M_WET = paint("puddle", (0.03, 0.03, 0.03), 0.04); M_BLK = paint("black", (0.02, 0.02, 0.02), 0.6)
    M_BULB = paint("bulb", (1.0, 0.8, 0.5), 0.3, 0, 30.0); M_PAINT = paint("wallpaint", (0.9, 0.75, 0.1), 0.8)
    bm = bmesh.new()
    box(bm, (0, 0, 1.8), (16, 10, 3.6))                        # 승강장 16 × 10, 천장 4.6 (MAP2 광장 15 × 10 · 4.5 와 같은 크기)
    blob(bm, (0, 0, 3.4), (8.6, 5.2, 1.2), 3)
    box(bm, (0, 6.5, 5), (3.4, 3.0, 30))                       # 수갱 — 위아래로 뚫린 네모 구멍 (케이지가 다닌다)
    box(bm, (0, -12.5, 1.35), (3.3, 15, 2.7))                  # 운반갱도 셋 — 남 · 서 · 동 (폭 3.3 · 높이 2.7, 조사 03)
    box(bm, (-15, 1, 1.35), (14, 3.3, 2.7))
    box(bm, (15, -1, 1.35), (14, 3.3, 2.7))
    shell(bm, 0.25)

    bm = bmesh.new()                                           # 강철 틀: 벽 기둥 + 천장 들보 (2 m 마다) — 바위 굴과 다른 "지은 곳"
    for x in range(-7, 8, 2):
        for y in (-4.7, 4.7):
            if abs(x) >= 2: box(bm, (x, y, 1.9), (0.2, 0.2, 3.8))           # 수갱 문 · 남쪽 굴 입구 자리는 비운다
        box(bm, (x, 0, 3.85), (0.2, 9.6, 0.25))
    for y in (-4.1, 4.1):                                       # 천장을 가로지르는 관 둘 · 벽의 케이블 묶음
        box(bm, (0, y, 4.1), (16, 0.22, 0.22))
    obj("STEEL", bm, M_STEEL)
    bm = bmesh.new()                                           # 판자 덧댐 (벽 기둥 사이)
    for x in range(-7, 7, 2):
        for y in (-4.85, 4.85):
            if abs(x + 1) < 2: continue                                   # 수갱 문(북) · 남쪽 굴 입구(남)
            for z in (0.6, 1.3, 2.0, 2.7, 3.4): box(bm, (x + 1, y, z), (1.9, 0.06, 0.5))
    for i in range(28): box(bm, (0, 4.4 - i * 0.8, 0.04), (1.4, 0.18, 0.08))        # 레일 침목
    box_uv(obj("BOARDS", bm, M_TIMB).data, 0.8)
    bm = bmesh.new()
    for y in (-4.6, 4.6): box(bm, (0, y, 2.9), (16, 0.08, 0.12))   # 케이블
    obj("CABLE", bm, M_BLK)
    bm = bmesh.new()
    for c, s in (((1.5, 3.4), (2.2, 1.4)), ((-3, -1.5), (1.6, 2.4)), ((0.3, -4.2), (1.1, 1.0))): box(bm, (c[0], c[1], 0.02), (s[0], s[1], 0.005))
    obj("PUDDLE", bm, M_WET)                                     # 젖은 바닥 — 전등이 비친다
    bm = bmesh.new()                                           # 레일 둘 (남쪽 운반갱도 → 케이지)
    for x in (-0.45, 0.45): box(bm, (x, -6.5, 0.13), (0.07, 26, 0.1))
    obj("RAIL", bm, M_STEEL)

    bm = bmesh.new()                                           # 케이지: 강철 틀 + 철망 옆면 (수갱 안, 승강장 바닥 높이에 섰다)
    for x in (-1.25, 1.25):
        for y in (5.6, 7.4): box(bm, (x, y, 1.4), (0.12, 0.12, 2.8))
    for z in (0.05, 2.8): box(bm, (0, 6.5, z), (2.6, 1.9, 0.08))
    for i in range(21):
        box(bm, (-1.25, 5.6 + i * 0.09, 1.4), (0.02, 0.02, 2.7)); box(bm, (1.25, 5.6 + i * 0.09, 1.4), (0.02, 0.02, 2.7))
    for k in range(4): box(bm, (0.6 * (k - 1.5), 6.5, 2.8 + (4 - k) * 1.6), (0.05, 0.05, 3.2))   # 매달린 쇠사슬 · 줄
    obj("CAGE", bm, M_STEEL)
    bm = bmesh.new()                                           # 케이지 문(빨강) — 철망
    for i in range(26): box(bm, (-1.2 + i * 0.096, 5.55, 1.2), (0.025, 0.025, 2.2))
    for z in (0.15, 1.2, 2.3): box(bm, (0, 5.55, z), (2.5, 0.04, 0.06))
    obj("CAGEDOOR", bm, M_RED)
    bm = bmesh.new()                                           # 수갱 문(노랑) — 승강장 쪽 철망 미닫이 + 틀
    for i in range(30): box(bm, (-1.6 + i * 0.11, 5.05, 1.05), (0.03, 0.03, 1.9))
    for z in (0.12, 1.05, 2.0): box(bm, (0, 5.05, z), (3.3, 0.05, 0.07))
    for x in (-1.75, 1.75): box(bm, (x, 5.05, 1.6), (0.14, 0.14, 3.2))
    box(bm, (0, 5.05, 3.2), (3.6, 0.16, 0.16))
    for i in range(10):                                        # 바닥의 노랑·검정 경계 줄
        box(bm, (-1.8 + i * 0.4, 4.7, 0.07), (0.2, 0.3, 0.01))
    obj("GATE", bm, M_YEL)
    bm = bmesh.new()                                           # 신호벨 상자 · 신호판 (문 오른쪽 벽)
    box(bm, (2.6, 4.75, 1.55), (0.35, 0.18, 0.45)); blob(bm, (2.6, 4.62, 1.95), (0.14, 0.08, 0.14), 2)
    box(bm, (3.9, 4.8, 1.7), (1.1, 0.04, 0.8))
    obj("SIGNAL", bm, M_RED)
    bm = bmesh.new()                                           # 광차 하나 (케이지에 실을 차례)
    box(bm, (0, -1.5, 0.75), (1.0, 1.7, 0.9))
    for x in (-0.4, 0.4):
        for y in (-2.1, -0.9): blob(bm, (x, y, 0.22), (0.05, 0.2, 0.2), 1)
    box_uv(obj("CART", bm, M_RUST).data, 1.0)
    bm = bmesh.new()                                           # 전구 둘 (유리갓) — 케이지 앞만 밝다
    for x in (-2.2, 2.2): blob(bm, (x, 4.0, 3.55), (0.12, 0.12, 0.16), 2)
    obj("BULB", bm, M_BULB).visible_shadow = False               # 전구가 제 빛을 가리지 않게
    bm = bmesh.new()
    for x in (-2.2, 2.2): blob(bm, (x, 4.0, 3.72), (0.28, 0.28, 0.1), 2)
    obj("SHADE", bm, M_STEEL).visible_shadow = False
    text("1편", (-4.2, 4.7, 1.5), 1.3, M_PAINT)                 # 층 번호를 벽에 크게 — 어느 층인지 한눈에
    text("케이지 부르기 — 벨", (3.9, 4.75, 2.25), 0.16, paint("white", (0.85, 0.85, 0.8), 0.8))
    text("← 서 운반갱도", (-6.2, 4.7, 3.0), 0.3, M_PAINT); text("동 운반갱도 →", (6.2, 4.7, 3.0), 0.3, M_PAINT)
    return dict(
        lights=[("BULB_W", (-2.2, 4.0, 3.25), 180, (1.0, 0.75, 0.45), 0.15, True), ("BULB_E", (2.2, 4.0, 3.25), 180, (1.0, 0.75, 0.45), 0.15, True),
                ("DIM_S", (0, -9, 2.4), 25, (1.0, 0.6, 0.3), 0.1, True)],   # 남쪽 운반갱도 입구의 흐린 전등
        adapt=((0, 0, 3), 60, 8), fills=([(-5, -2), (5, -2), (0, 3), (0, -12)], 3.8, 900, 3),
        shots=[("fp_1_arrive", (0, -11, EYE), (0, 6, 1.4)),              # 남쪽 운반갱도에서 승강장으로 — 끝에 불 켜진 케이지 앞
               ("fp_2_gate", (-0.8, 1.2, EYE), (-0.9, 5, 1.7)),          # 케이지 문 앞 — 문 · 벨 · 층 번호 (셋이 한 화면에)
               ("fp_3_wait_back", (0.2, 4.0, EYE), (-2, -8, 1.3)),        # 벨을 누르고 뒤돌아봄 — 어두운 굴 셋 (기다리는 동안 괴물이 오는 쪽)
               ("fp_4_inside_cage", (0.3, 6.9, EYE), (0, -4, 1.4))],      # 케이지 안에서 철망 너머로
        people=[(0, 2.6, 0), (-6, -2, 0)], ortho=44, side_z=2)

# ================= 장면 1 — 쇠동발 숲 = 새로 판 막장 가는 길 (1편)
# 장면 카드 1(한국광물자원공사 사진 · "나무동발에서 쇠동발로"): 천장이 낮은 통로 양쪽에 은색 쇠기둥이 빽빽, 기둥 위 나무 받침, 바닥 널빤지.
# 일어나는 일: 기둥이 시야를 잘게 끊는다 — 기둥 틈으로 괴물(눈 두 점)이 언뜻 보였다 사라진다. 가운데 널빤지 길만 곧고, 양옆은 기둥 사이로 비집어야 한다.
def scene1():
    M_PROP = paint("steelprop", (0.5, 0.52, 0.54), 0.4, 0.7); M_CLAMP = paint("clamp", (0.25, 0.26, 0.27), 0.5, 0.9)
    M_EYE = paint("eye", (1.0, 0.85, 0.6), 0.3, 0, 25.0)
    L, W, H = 24.0, 10.0, 2.3                                   # 쇠동발 구역 24 × 10 m, 천장 2.3 (가운데 널빤지 길) — 양옆은 조금 낮다
    bm = bmesh.new()
    box(bm, (0, 0, H / 2), (L, W, H))
    SIDE = max(1.9, LOWEST)
    for y in (-3.5, 3.5): box(bm, (0, y, SIDE / 2), (L, 3, SIDE))     # 양옆 가장자리는 1.9 m 로 낮아진다 (탄층 따라, 맵 모드는 2.1)
    box(bm, (-L / 2 - 5, 0, 1.2), (10, 2.6, 2.4))               # 들어오는 곁갱도 (나무동발)
    FACE = max(1.6, LOWEST + 0.1); box(bm, (L / 2 + 4, 0, FACE / 2), (8, 5, FACE))   # 새로 판 막장 쪽 — 더 낮다 (1.6 m, 숙여야 한다 · 맵 모드는 선 채로 2.2)
    shell(bm, 0.25)
    bm = bmesh.new(); bmc = bmesh.new(); bmt = bmesh.new()
    for i, x in enumerate(np.arange(-L / 2 + 0.8, L / 2 - 0.5, 1.1)):
        for y in (-4.3, -3.2, -2.1, -1.0, 1.0, 2.1, 3.2, 4.3):
            px, py = x + random.uniform(-0.15, 0.15), y + random.uniform(-0.12, 0.12)
            top = (H if abs(y) < 2.5 else SIDE) - 0.12
            tilt = Matrix.Rotation(math.radians(random.uniform(-3, 3)), 3, "X") @ Matrix.Rotation(math.radians(random.uniform(-3, 3)), 3, "Y")
            if MAP:                                                                                                          # 맵 모드: Fab 늘어나는 쇠동발 (사용자 09-30 "쇠동발 길 = Fab 쇠동발" — 우리 원통은 게임에서 플라스틱처럼 번쩍였다)
                put("ugfmehgfa", Matrix.Translation((px, py, 0)) @ tilt.to_4x4() @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z") @ Matrix.Diagonal((1, 1, top / 2.55, 1)))
            else:
                g = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.075, radius2=0.075, depth=top * 0.55)          # 아래 통
                for v in g["verts"]: v.co = tilt @ (v.co + Vector((0, 0, top * 0.275))) + Vector((px, py, 0))
                g = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.058, radius2=0.058, depth=top * 0.5)           # 위 통 (늘어나는 쇠동발)
                for v in g["verts"]: v.co = tilt @ (v.co + Vector((0, 0, top * 0.75))) + Vector((px, py, 0))
                box(bmc, tilt @ Vector((0, 0, top * 0.55)) + Vector((px, py, 0)), (0.2, 0.2, 0.14), tilt)                         # 조임쇠
            box(bmt, tilt @ Vector((0, 0, top + 0.06)) + Vector((px, py, 0)), (0.55, 0.16, 0.12), tilt)                           # 나무 받침
    if bm.verts: props = obj("PROPS", bm, M_PROP); props.data.polygons.foreach_set("use_smooth", np.ones(len(props.data.polygons), dtype=bool)); obj("CLAMPS", bmc, M_CLAMP)
    for k in (-1, 0, 1): box(bmt, (0, k * 0.32, 0.04), (L + 6, 0.28, 0.05))   # 가운데 널빤지 길
    for i in range(10): box(bmt, (random.uniform(-10, 10), random.choice((-3, 3)) + random.uniform(-1, 1), 0.06), (random.uniform(0.8, 1.8), 0.25, 0.05), Matrix.Rotation(random.uniform(0, 3.1), 3, "Z"))   # 흩어진 널빤지
    box_uv(obj("TIMBER", bmt, M_TIMB).data, 0.8)
    cam3 = Vector((-1.5, -0.2, EYE)); deps = bpy.context.evaluated_depsgraph_get()
    def clear(p):                                               # 카메라에서 그 점까지 가리는 것이 없나
        d = Vector(p) - cam3; hit, loc, *_ = sc.ray_cast(deps, cam3, d.normalized(), distance=d.length)
        return not hit
    ex = next(x for x in np.arange(2.0, 9.0, 0.05) if all(clear((x + dx, 3.7, 1.72)) for dx in (-0.1, -0.065, 0, 0.065, 0.1)))   # 기둥 틈으로 실제로 보이는 자리
    bm = bmesh.new()
    for dx in (-0.065, 0.065): blob(bm, (ex + dx, 3.7, 1.72), (0.028, 0.02, 0.022), 2)   # 기둥 틈의 눈 두 점 (③ 한 장에만)
    obj("EYES", bm, M_EYE).visible_shadow = False
    print("CHECK scene1 eyes at x %.2f (clear from the glimpse camera)" % ex)
    return dict(
        lights=[], adapt=((0, 0, 2), 90, 10), fills=([(-8, 0), (0, 0), (8, 0), (0, -3.5), (0, 3.5)], 2.0, 700, 3),
        shots=[("fp_1_enter", (-L / 2 - 2.5, 0, EYE), (6, 0, 1.3)),          # 곁갱도에서 쇠동발 숲으로 — 은색 기둥이 빽빽
               ("fp_2_side", (-2, 0, EYE), (-1, 6, 1.3)),                     # 널빤지 길 가운데서 옆을 봄 — 기둥 사이로 어둠
               ("fp_3_glimpse", tuple(cam3), (ex, 3.7, 1.6)),         # 기둥 틈으로 눈 두 점 (그것이 언뜻 보인다)
               ("fp_4_ahead_face", (8, 0.1, EYE), (L / 2 + 6, 0, 0.8))],      # 끝에서 새로 판 막장 쪽 — 천장이 더 낮아진다
        shot_only={"EYES": "fp_3_glimpse"},
        people=[(-6, 0, 0), (6, 3.2, 0)], ortho=40, side_z=1)

# ================= 시험 벽 — 질감 비교 (MAP4 규칙 6, 사용자 09-30 "셋 다 실제로 해 보고 비교")
# 곁갱도 12 m (폭 2.6 · 높이 2.4, 나무동발 넷). 벽 질감만 바꾼다: TEX=now(지금 게임 rock_face_04) · <폴더>(색 · 노멀 · 거칠기 그림, TEXM = 한 장이 덮는 m)
#   · meshy:<glb>(Meshy 가 입힌 모델 — 우리 모양에 크기 · 자리를 맞춰 끼운다). EXPORT=<glb> 면 칠하기 전 모양(재질 하나)을 내보낸다 (Meshy 에 올릴 것).
def tex_mat(d, tile_m):
    fs = {f.lower(): os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg"))}
    pick = lambda keys, bad=(): next((p for f, p in sorted(fs.items()) if any(k in f for k in keys) and not any(b in f for b in bad)), None)
    col, nor, rou = pick(("color", "albedo", "basecolor", "diff")), pick(("normalgl", "normal_gl", "nor_gl", "normal"), ("dx",)), pick(("rough",))
    m = bpy.data.materials.new("TEX"); m.use_nodes = True; nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = ((1 / 0.35) / tile_m,) * 3
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    def img(p, color):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p); n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    nt.links.new(img(col, True).outputs["Color"], bsdf.inputs["Base Color"])
    if rou: nt.links.new(img(rou, False).outputs["Color"], bsdf.inputs["Roughness"])
    if nor:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img(nor, False).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    print("TEX color %s | normal %s | rough %s | tile %.2f m" % (tuple(os.path.basename(p) if p else None for p in (col, nor, rou)) + (tile_m,))); return m

def scene_t():
    bm = bmesh.new(); box(bm, (0, 0, 1.2), (12, 2.6, 2.4))
    sh = shell(bm, 0.3)
    tex = os.environ.get("TEX", "now")
    if os.environ.get("EXPORT"):
        sh.data.materials.clear(); sh.data.materials.append(M_WALL)
        bpy.ops.object.select_all(action="DESELECT"); sh.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.environ["EXPORT"], use_selection=True, export_format="GLB", export_image_format="NONE")   # 그림은 빼고 모양 · UV 만
        print("CHECK export %s faces %d" % (os.environ["EXPORT"], len(sh.data.polygons))); raise SystemExit
    if tex.startswith("meshy:"):
        before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=tex[6:])
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        def bb(objs):
            ps = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
            return Vector([min(p[i] for p in ps) for i in range(3)]), Vector([max(p[i] for p in ps) for i in range(3)])
        a0, a1 = bb([sh]); b0, b1 = bb(new)
        for o in new:                                           # Meshy 가 모델을 옮기거나 키웠으면 우리 자리에 다시 맞춘다
            s_ = Vector([(a1[i] - a0[i]) / max(b1[i] - b0[i], 1e-6) for i in range(3)])
            o.matrix_world = Matrix.Translation(a0) @ Matrix.Diagonal((*s_, 1)) @ Matrix.Translation(-b0) @ o.matrix_world
        bpy.data.objects.remove(sh, do_unlink=True)
    elif tex != "now":
        m = tex_mat(tex, float(os.environ.get("TEXM", "2.0"))); sh.data.materials[0] = m
    if os.environ.get("TEXF"): sh.data.materials[1] = tex_mat(os.environ["TEXF"], float(os.environ.get("TEXFM", "2.0")))   # 바닥 질감 (TEXF 폴더 · TEXFM m)
    bm = bmesh.new()                                            # 나무동발 넷 (비교마다 같다)
    for x in (-4, -1, 2, 5):
        for y in (-1.1, 1.1): box(bm, (x, y, 1.12), (0.2, 0.2, 2.25))
        box(bm, (x, 0, 2.3), (0.2, 2.5, 0.2))
    box_uv(obj("TIMBER", bm, M_TIMB).data, 0.8)
    return dict(
        lights=[], adapt=((0, 0, 1.8), 25, 4), fills=([(-4, 0), (0, 0), (4, 0)], 2.0, 250, 1.5),
        shots=[("fp_1_along", (-5.3, 0, EYE), (6, 0, 1.4)),              # 굴을 따라 — 게임에서 가장 많이 보는 모습
               ("fp_2_wall_close", (0.6, -0.1, EYE), (0.8, 1.3, 1.2)),     # 벽 1.2 m 앞 — 가까이서 본 질감
               ("fp_3_oblique", (-2, 0.4, EYE), (3, -1.3, 1.0))],          # 비스듬히 — 반복 무늬가 보이나
        people=[(0, 0, 0)], ortho=16, side_z=1.2)

# ================= Fab 갱도 조각 모델 — 같은 카메라 · 머리등으로 (사용자가 받은 Megascans 광산 묶음, build/tex_test/fab/ — git 금지)
# FAB=<조각 폴더>(FBX + Albedo · Normal · Roughness) · FABN=이어 붙일 수(기본 2). 조각의 가장 긴 수평 쪽을 굴 방향으로 보고 그쪽으로 잇는다.
def scene_f():
    d = os.environ["FAB"]; fbx = next(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".fbx") and "lod1" not in f.lower())
    m = tex_mat(d, 1 / 0.35)                                     # 조각 자기 UV 그대로 (배율 1)
    ob, lo, hi = [], None, None
    for k in range(int(os.environ.get("FABN", "2"))):
        before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=fbx)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for o in new: o.data.materials.clear(); o.data.materials.append(m)
        ps = [o.matrix_world @ Vector(c) for o in new for c in o.bound_box]
        a = Vector([min(p[i] for p in ps) for i in range(3)]); b = Vector([max(p[i] for p in ps) for i in range(3)])
        if lo is None:                                           # 굴 방향 = 가운데 눈높이에서 광선이 조각 밖까지 안 막히는 수평 축 (재서 고른다)
            lo, hi = a, b; cc = (a + b) / 2; cc.z = a.z + EYE; deps = bpy.context.evaluated_depsgraph_get()
            def open_len(i):
                t = 0.0
                for sg in (1, -1):
                    dv = Vector((0, 0, 0)); dv[i] = sg; hit, loc, *_ = sc.ray_cast(deps, cc, dv, distance=50)
                    t += (loc - cc).length if hit else 50
                return t
            ax = max((0, 1), key=open_len); print("CHECK fab axis %s open %.1f / %.1f m" % ("xy"[ax], open_len(0), open_len(1)))
        step = Vector((0, 0, 0)); step[ax] = (hi[ax] - lo[ax]) * k
        for o in new: o.location += step
        ob += new
    L = (hi[ax] - lo[ax]) * int(os.environ.get("FABN", "2")); c = (lo + hi) / 2
    bm = bmesh.new(); fc = lo + (hi - lo) / 2; fc[ax] = lo[ax] + L / 2; box(bm, (fc.x, fc.y, lo.z - 0.02), ((L if ax == 0 else hi.x - lo.x) + 1, (L if ax == 1 else hi.y - lo.y) + 1, 0.04))
    fl = obj("FLOOR", bm, M_FLOOR); box_uv(fl.data, 0.35)
    if os.environ.get("TEXF"): fl.data.materials[0] = tex_mat(os.environ["TEXF"], float(os.environ.get("TEXFM", "2.0")))   # 조각에 바닥이 없으면 까맣다 — 석탄 바닥
    along = Vector((0, 0, 0)); along[ax] = 1; side = Vector((0, 0, 0)); side[1 - ax] = 1
    start = lo.copy(); start[1 - ax] = c[1 - ax]; start.z = lo.z
    eye = lambda s, t=0.0: tuple(start + along * s + side * t + Vector((0, 0, EYE)))
    at = lambda s, t=0.0, z=1.4: tuple(start + along * s + side * t + Vector((0, 0, z)))
    w = hi[1 - ax] - lo[1 - ax]
    return dict(
        lights=[], adapt=(at(L / 2, 0, 2), 25, 4), fills=([tuple((start + along * s)[:2]) for s in (L * 0.2, L * 0.5, L * 0.8)], lo.z + 2.2, 250, 1.5),
        shots=[("fp_1_along", eye(0.7), at(L)),
               ("fp_2_wall_close", eye(L / 2, -w / 2 + 1.6), at(L / 2 + 0.2, -w / 2, 1.2)),
               ("fp_3_oblique", eye(L * 0.25, w / 4), at(L * 0.7, -w / 2, 1.0))],
        people=[at(L / 2, 0, 0)], ortho=max(L, w) + 4, side_z=lo.z + 2)

# ================= Fab 모델 하나를 놓기 (build/tex_test/fab/mine_high/<ID>/ — git 금지). 밑면 가운데를 at 에, yaw 만큼 돌려서. along=True 면 긴 쪽을 X 로 먼저 돌린다
FABDIR = os.environ.get("FABDIR", os.path.join(ROOT, "build", "tex_test", "fab", "mine_high"))
def fab(fid, at, yaw=0.0, along=False, rails=False):
    d = os.path.join(FABDIR, fid); fbx = next(os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".fbx") and "lod1" not in f.lower() and "lod2" not in f.lower() and "lod3" not in f.lower())
    before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    m = FABMAT.get(fid) or tex_mat(d, 1 / 0.35); FABMAT[fid] = m
    for o in new:
        o.data.materials.clear(); o.data.materials.append(m)
        mw = o.matrix_world.copy(); o.parent = None
        o.data.transform(mw); o.matrix_world = Matrix.Identity(4)                    # 조각의 변환을 그물에 굽는다 (돌리고 옮기기 쉽게) — 부모를 지우기 전에
    for o in [o for o in bpy.data.objects if o not in before and o.type != "MESH"]: bpy.data.objects.remove(o, do_unlink=True)
    if MAP:                                                                           # 맵 모드: 삼각형 줄이기 (조각 하나 2.5만~6.5만 — 맵 전체면 수백 개). 노멀 그림이 결을 살린다
        for o in new:
            if len(o.data.polygons) > 3000:
                dm = o.modifiers.new("dec", "DECIMATE"); dm.ratio = 0.3
                me_ = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); o.modifiers.clear(); o.data = me_
    co = np.array([v.co[:] for o in new for v in o.data.vertices])
    if rails:                                                                         # 레일 = 위쪽 점들이 길게 퍼진 쪽
        top = co[co[:, 2] > co[:, 2].min() + 0.7 * (co[:, 2].max() - co[:, 2].min())]
        if np.ptp(top[:, 1]) > np.ptp(top[:, 0]): yaw += 90
    elif along and np.ptp(co[:, 1]) > np.ptp(co[:, 0]): yaw += 90
    R = Matrix.Rotation(math.radians(yaw), 4, "Z")
    for o in new: o.data.transform(R)
    co = np.array([v.co[:] for o in new for v in o.data.vertices])
    off = Vector(at) - Vector(((co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2, co[:, 2].min()))
    for o in new: o.location = off
    return new, co.min(axis=0) + np.array(off), co.max(axis=0) + np.array(off)
FABMAT = {}
CG = os.path.join(ROOT, "build", "tex_test", "fab_coalground")      # Fab Coal Stone Ground (석탄 부스러기 바닥)

def arch_run(fids, x=0.0, objs_out=None):
    """Fab 갱도 조각을 X 로 잇는다 (굴 가운데 y = 0). 끝 x 를 돌려준다. objs_out 에 불러온 물체를 모은다 (위에서 본 그림에서 숨기려고)"""
    for fid in fids:
        objs, lo, hi = fab(fid, (0, 0, 0)); yc = (lo[1] + hi[1]) / 2
        for o in objs: o.location.x += x - lo[0]; o.location.y -= yc
        if objs_out is not None: objs_out += objs
        x += hi[0] - lo[0]
    return x

def coal_floor(x0, x1):
    bm = bmesh.new(); box(bm, ((x0 + x1) / 2, 0, -0.02), (x1 - x0 + 2, 7, 0.04)); fl = obj("FLOOR", bm, M_FLOOR); box_uv(fl.data, 0.35)
    if os.path.isdir(CG): fl.data.materials[0] = tex_mat(CG, 2.0)

def rail_run(x0, x1, y=0.0):
    rx = x0
    while rx < x1 - 1:                                              # 레일 조각을 잇는다
        objs, lo, hi = fab("ufekaeedw", (rx, y, 0), rails=True); L = hi[0] - lo[0]
        for o in objs: o.location.x += L / 2
        rx += L

def wall_pipe(x0, x1, z=2.3):
    """우리 관: 굴을 따라 끊김 없이 한 줄 (벽을 광선으로 재서 붙인다) — 나중에 REP 배수관(고칠 곳)과 같은 관"""
    deps = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = sc.ray_cast(deps, Vector(((x0 + x1) / 2, 0, z)), Vector((0, 1, 0)), distance=6)
    py = (loc.y if hit else 2.0) - 0.28
    M_PIPE = paint("pipe", (0.5, 0.07, 0.04), 0.55, 0.4)
    bm = bmesh.new()
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.08, radius2=0.08, depth=x1 - x0)
    for v in g["verts"]: v.co = Matrix.Rotation(math.radians(90), 3, "Y") @ v.co + Vector(((x0 + x1) / 2, py, z))
    fx = x0 + 1.5
    while fx < x1:                                                   # 3 m 마다 이음 쇠테(플랜지) + 벽에 거는 걸쇠
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.13, radius2=0.13, depth=0.05)
        for v in g["verts"]: v.co = Matrix.Rotation(math.radians(90), 3, "Y") @ v.co + Vector((fx, py, z))
        box(bm, (fx + 0.4, py + 0.17, z), (0.04, 0.3, 0.04))
        fx += 3.0
    pipe = obj("PIPE", bm, M_PIPE); pipe.data.polygons.foreach_set("use_smooth", np.ones(len(pipe.data.polygons), dtype=bool))
    print("CHECK pipe at y %.2f (wall %s)" % (py, "hit" if hit else "guess"))

def hang_lamps(xs, y):
    """철망 갓 전등 — 운반갱도엔 불이 있다. 천장을 광선으로 재서 그 밑에 단다"""
    deps = bpy.context.evaluated_depsgraph_get(); lamps = []
    for lx in xs:
        hit, loc, *_ = sc.ray_cast(deps, Vector((lx, y, 1.7)), Vector((0, 0, 1)), distance=10)
        top = loc.z if hit else 3.3
        fab("vgyidfpaw", (lx, y, top - 0.25)); lamps.append(("L%d" % lx, (lx, y, top - 0.4), 120, (1.0, 0.62, 0.3), 0.08, True))
        print("CHECK lamp x %d ceiling %.2f" % (lx, top))
    return lamps

# ================= 장면 3 — 운반갱도의 광차 싣는 곳 (1편, Fab 모델로)
# 장면 카드 3(한국광물자원공사: 쇠 깔때기 아래 줄 선 광차) + 굴 종류 "운반갱도 = Fab 강철 아치"(사용자 09-30).
# 일어나는 일: 캔 석탄을 슈트로 부어 광차를 채운다(몫). 쏟아지는 동안 괴물 발소리가 안 들린다 — 뒤돌아보면 어둠.
def scene3():
    M_STEEL = paint("steel", (0.2, 0.19, 0.18), 0.55, 0.85)
    tun = arch_run(["wdpnchedw", "wdpnchtdw", "wdpnchedw", "wdpnchtdw", "wdpnchedw"])   # 강철 아치 다섯 — 관 없는 조각만 (grdw · ihdw 는 관이 조각마다 다른 자리라 이음새에서 끊긴다 — 사용자 캡처 09-30)
    coal_floor(0, tun); cg = CG
    rail_run(0, tun)
    cx = tun * 0.55                                                  # 슈트 자리
    fab("ueujednfa", (cx, 0, 0.12), along=True)                      # 석탄 실은 광차 (슈트 아래)
    fab("ufmodhpfa", (cx + 2.5, 0, 0.12), along=True)                # 빈 광차 둘 (앞 · 뒤)
    fab("ufmodhpfa", (cx - 2.4, 0, 0.12), along=True)
    fab("ujzhahdfa", (cx - 7.5, 0, 0.12), along=True)                # 통나무 실은 광차 — 더 뒤에
    bm = bmesh.new()                                                 # 슈트: 벽 위에서 비스듬히 내려오는 쇠 홈통 + 문 + 손잡이
    tilt = Matrix.Rotation(math.radians(-38), 3, "X")
    box(bm, (cx, -1.35, 2.75), (1.0, 2.2, 0.08), tilt)                # 바닥판
    for sx in (-0.5, 0.5): box(bm, (cx + sx, -1.35, 3.0), (0.06, 2.2, 0.55), tilt)   # 옆판
    box(bm, (cx, -0.55, 1.95), (1.05, 0.06, 0.55))                   # 문 (올리면 쏟아진다)
    box(bm, (cx + 0.7, -0.6, 1.6), (0.05, 0.05, 0.9), Matrix.Rotation(math.radians(20), 3, "Y"))   # 손잡이
    box(bm, (cx, -2.2, 3.6), (1.1, 0.8, 1.0))                        # 벽 속으로 들어가는 목 (위 채탄장에서 내려온다)
    box_uv(obj("CHUTE", bm, M_RUST).data, 1.0)                     # 녹슨 쇠
    bm = bmesh.new()                                                 # 흘린 석탄 부스러기
    for i in range(18):
        s_ = random.uniform(0.08, 0.3); blob(bm, (cx + random.uniform(-1.2, 1.2), random.uniform(-1.3, -0.5), s_ * 0.3), (s_, s_, s_ * 0.5), 1)
    rk = obj("COAL", bm, M_FLOOR); box_uv(rk.data, 0.8)
    if os.path.isdir(cg): rk.data.materials[0] = FABMAT.get("_cg") or tex_mat(cg, 1.0)
    wall_pipe(0, tun)
    lamps = hang_lamps((4, 12, 20), 0.9)                             # 8 m 마다
    return dict(
        lights=lamps, adapt=((tun / 2, 0, 2), 40, 6), fills=([(4, 0), (12, 0), (20, 0)], 3.0, 700, 3),
        shots=[("fp_1_along", (1.2, 1.1, EYE), (cx + 3, -0.3, 1.2)),            # 운반갱도를 따라 — 전등 · 광차 줄 · 슈트
               ("fp_2_chute", (cx - 2.3, 1.0, EYE), (cx, -0.8, 1.9)),           # 슈트 문 앞 — 손잡이를 올리면 쏟아진다
               ("fp_3_back", (cx + 0.5, 0.9, EYE), (0, 0.3, 1.3)),              # 쏟는 동안 뒤돌아봄 — 어둠 (발소리가 안 들린다)
               ("fp_4_cart", (cx - 1.3, 1.2, 2.1), (cx, 0, 1.0))],              # 석탄 실은 광차 속
        people=[(cx - 2.3, 1.0, 0)], ortho=tun + 4, side_z=1.8, center=(tun / 2, 0))

# ================= 장면 7 — 바람문 두 짝 (1편 운반갱도 → 곁갱도, Fab 모델로)
# 레퍼런스 둘(10-01 봄): 카드 7 영국 Smallcleugh(돌 아치 굴을 세운 판자 벽이 아치 모양대로 막고 가운데 좁은 판자 문, 문에 빨간 칠)
#   · 예비 사진 독일 광산박물관 Wettertür(강철 아치를 벽돌 벽이 막고 광차가 지나는 큰 두 짝 문 + 사람 문 + 표지판). 국내 사진은 못 찾음.
#   공통 = 굴 단면 전체를 벽이 아치 모양대로 막는다 · 굵은 문틀 · 속이 안 보이는 통짝 문 · 문에 표지.
# 일어나는 일: 앞문을 닫아야 뒷문이 열린다(풍문은 늘 닫아 둔다 — 조사 09). 두 문 사이 6 m 는 머리등뿐, 문 너머가 안 보인다. 괴물은 문을 긁는다.
def tint(m, rgb, name):
    """재질 사본의 바탕색에 rgb 를 곱한다 — 나뭇결은 그대로 두고 칠 · 타르 색만"""
    t = m.copy(); t.name = name; nt = t.node_tree
    inp = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"]
    if inp.links and inp.links[0].from_node.type == "MIX":                # 이미 곱한 재질 — 곱하기를 두 겹으로 쌓으면 glTF 에 마지막 것만 나간다(썩은 동발이 보통 나무 색으로 나갔다, 10-01 조사 12)
        b = [x for x in inp.links[0].from_node.inputs if x.type == "RGBA"][1]; b.default_value = tuple(b.default_value[i] * rgb[i] for i in range(3)) + (1,); return t
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 1.0
    a, b = [x for x in mix.inputs if x.type == "RGBA"][:2]; b.default_value = (*rgb, 1)
    if inp.links: nt.links.new(inp.links[0].from_socket, a)
    else: a.default_value = inp.default_value
    nt.links.new(next(x for x in mix.outputs if x.type == "RGBA"), inp); return t

CC0 = os.path.join(ROOT, "build", "tex_test", "cc0")                   # 모은 무료(CC0) 사진 질감 — 조사 12. git 에 없다: 없으면 옛 재질로 굽고 로그에 적는다 (받는 곳은 폴더마다 source.txt)
def cc0_mat(rel, tile_m, name, mul=None, per_m=0.8, metal=False):
    """CC0 사진 재질. tile_m = 한 장이 덮는 m, per_m = 그 물체들의 box_uv 값. 없으면 None"""
    d = os.path.join(CC0, rel)
    if not os.path.isdir(d): print("CHECK cc0 missing %s — old material kept" % rel); return None
    m = tex_mat(d, tile_m); m.name = name; nt = m.node_tree; mp = next(n for n in nt.nodes if n.type == "MAPPING"); mp.inputs["Scale"].default_value = (1 / (per_m * tile_m),) * 3
    mf = next((os.path.join(d, f) for f in sorted(os.listdir(d)) if "metal" in f.lower().replace(os.path.basename(d).lower(), "") and f.lower().endswith((".jpg", ".png"))), None)
    if metal and mf:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(mf); n.image.colorspace_settings.name = "Non-Color"; nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        nt.links.new(n.outputs["Color"], next(x for x in nt.nodes if x.type == "BSDF_PRINCIPLED").inputs["Metallic"])
    return tint(m, mul, name) if mul else m

def slab(bm, x, a, b, z0, ta, tb, t):
    """세운 판자 하나 — y a~b, 두께 t (x 방향), 위 끝이 비스듬 (ta → tb, 아치에 맞춘다)"""
    vs = [bm.verts.new(v) for v in ((x - t / 2, a, z0), (x - t / 2, b, z0), (x - t / 2, b, tb), (x - t / 2, a, ta),
                                    (x + t / 2, a, z0), (x + t / 2, b, z0), (x + t / 2, b, tb), (x + t / 2, a, ta))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)): bm.faces.new([vs[i] for i in f])

DOOR_W, DOOR_H, BOARD_T = 1.6, 2.0, 0.05                             # 문 = 광차가 지나는 두 짝 (독일 사진) · 판자 두께
def bulkhead(x, inner):
    """굴 단면을 막는 판자 벽 + 문틀 (x 자리). 벽은 광선으로 굴 모양을 재서 판자마다 위 끝을 맞춘다. inner = 두 문 사이 쪽(+1/-1) — 가로대는 그쪽에"""
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
    def ray(p, d): return sc.ray_cast(deps, Vector(p), Vector(d), distance=12)[1]
    y0, y1 = ray((x, 0, 0.3), (0, -1, 0)).y + 0.03, ray((x, 0, 0.3), (0, 1, 0)).y - 0.03
    top = lambda y: ray((x, y, 0.3), (0, 0, 1)).z - 0.03
    fw = DOOR_W / 2 + 0.2                                             # 문틀 바깥 반폭
    bm = bmesh.new(); planks = []
    for a0, a1, z0 in ((y0, -fw, 0.0), (-fw, fw, DOOR_H + 0.2), (fw, y1, 0.0)):   # 문 왼쪽 · 문 위 · 문 오른쪽
        n = max(1, round((a1 - a0) / 0.2))
        for i in range(n):
            a, b = a0 + i * (a1 - a0) / n, a0 + (i + 1) * (a1 - a0) / n - 0.012   # 판자 사이 틈 1.2 cm
            ta, tb = top(a + 0.01), top(b - 0.01); slab(bm, x, a, b, z0, ta, tb, BOARD_T); planks.append((a, b, min(ta, tb)))
    for z in (0.5, 1.5, 2.5):                                         # 가로대 (두 문 사이 쪽) — 판자 위 끝이 닿는 곳까지만
        for side in (-1, 1):
            ok = [(a, b) for a, b, t in planks if t > z + 0.15 and side * (a + b) > 2 * fw - 0.01]
            if ok: box(bm, (x + inner * (BOARD_T / 2 + 0.03), (min(a for a, _ in ok) + max(b for _, b in ok)) / 2, z), (0.06, max(b for _, b in ok) - min(a for a, _ in ok), 0.14))
    box_uv(obj("BOARDS", bm, M_TIMB).data, 0.8)
    bm = bmesh.new()
    for s in (-1, 1): box(bm, (x, s * (DOOR_W / 2 + 0.1), (DOOR_H + 0.2) / 2), (0.26, 0.2, DOOR_H + 0.2))   # 문틀 기둥 (타르 칠 — 벽보다 짙다)
    box(bm, (x, 0, DOOR_H + 0.1), (0.26, DOOR_W + 0.4, 0.2))           # 문틀 머리
    box_uv(obj("TIMBER", bm, M_TAR).data, 0.8)
    print("CHECK bulkhead x %.2f  wall y %.2f ~ %.2f  top %.2f" % (x, y0, y1, max(t for *_, t in planks)))
    return y0, y1

def door(x, name, inner, open_to, deg, M_IRON):
    """두 짝 판자 문 — 세운 판자 넷 + 띠장 둘 + 빗댄 막대(두 문 사이 쪽) + 쇠 경첩 · 손잡이. deg 만큼 open_to(+1/-1) 쪽으로 열린다"""
    lw = DOOR_W / 2; bm = bmesh.new(); bmi = bmesh.new()
    for s in (-1, 1):                                                 # 왼 · 오른 짝 — 경첩은 문틀 쪽
        hinge = Vector((x, s * lw, 0)); R = Matrix.Rotation(math.radians(open_to * s * deg), 3, "Z")
        put = lambda b_, c, size, rot=None: box(b_, hinge + R @ Vector(c), size, R @ rot if rot else R)
        for k in range(4): put(bm, (0, -s * (k + 0.5) * lw / 4, (0.18 + DOOR_H - 0.02) / 2), (0.045, lw / 4 - 0.01, DOOR_H - 0.2))
        zl, zh = 0.45, DOOR_H - 0.4
        for z in (zl, zh):
            put(bm, (inner * 0.045, -s * lw / 2, z), (0.04, lw - 0.06, 0.14))
            put(bmi, (inner * 0.07, -s * 0.25, z), (0.01, 0.5, 0.05))                          # 쇠 경첩 띠
        ang = math.atan2(zh - zl, lw - 0.1) * -s                                                # 빗댄 막대: 경첩 쪽 아래 → 여는 쪽 위
        put(bm, (inner * 0.045, -s * lw / 2, (zl + zh) / 2), (0.035, math.hypot(zh - zl, lw - 0.1), 0.12), Matrix.Rotation(ang, 3, "X"))
        for f in (-1, 1): put(bmi, (f * 0.06, -s * (lw - 0.1), 1.05), (0.03, 0.03, 0.3))       # 손잡이 (양쪽)
    box_uv(obj(name, bm, M_DOOR).data, 0.8); obj(name + "_IRON", bmi, M_IRON)

def scene7():
    M_IRON = paint("iron", (0.08, 0.08, 0.08), 0.6, 0.8); M_PAINT = paint("wallpaint", (0.9, 0.75, 0.1), 0.8)
    M_BLK = paint("gouge", (0.02, 0.015, 0.01), 0.9)
    global M_DOOR, M_TAR
    M_DOOR = tint(M_TIMB, (0.62, 0.2, 0.12), "door_redoxide"); M_TAR = tint(M_TIMB, (0.3, 0.26, 0.24), "frame_tar")   # 문 = 붉은 칠(Smallcleugh 문의 빨간 칠) · 문틀 = 타르
    tunnel = []
    steel = arch_run(["wdpnchedw", "wdpnchtdw", "wdpnchedw", "wdpnchtdw"], 0.0, tunnel)          # 운반갱도 = Fab 강철 아치 (시안 ③ 과 같은 조각)
    tun = arch_run(["wcbpdfsdw", "wcbpdgcdw", "wcbpdfsdw"], steel, tunnel)                       # 문 너머 = 곁갱도 = Fab 나무 버팀 (사용자 09-30 굴 종류)
    coal_floor(0, tun); rail_run(0, tun)
    xb = steel - 0.15; xa = xb - 6.0                                   # 뒷문은 강철 아치 끝 (벽이 두 굴 모양이 바뀌는 곳을 가린다) · 앞문은 6 m 앞
    bulkhead(xa, +1); _, wb = bulkhead(xb, -1)
    door(xa, "DOORA", +1, +1, 75 if MAP else 0, M_IRON)                             # 앞문 — 두 문 사이로 밀어 연다
    door(xb, "DOORB_SHUT", -1, +1, 0, M_IRON)                        # 뒷문 — 곁갱도 쪽으로 밀어 연다 (닫힌 것 · 연 것 두 벌, 그림마다 하나)
    door(xb, "DOORB_OPEN", -1, +1, 80, M_IRON)
    face = lambda sgn: (math.radians(90), 0, math.radians(-90 * sgn))  # 글자가 -x(sgn=1) · +x(sgn=-1) 쪽을 본다
    fw = DOOR_W / 2 + 0.2
    text("풍문", (xa - BOARD_T / 2 - 0.01, 0, DOOR_H + 0.4), 0.6, M_PAINT, face(1))                       # 앞문 (오는 쪽)
    text("항상 닫을 것", (xa - BOARD_T / 2 - 0.01, -(fw + 0.8), 1.55), 0.22, M_PAINT, face(1))
    text("반대쪽 문을\n닫고 여시오", (xb - BOARD_T / 2 - 0.01, -(fw + 0.8), 1.2), 0.2, M_PAINT, face(1))   # 두 문 사이 — 뒷문 옆 (가로대 사이)
    text("반대쪽 문을\n닫고 여시오", (xa + BOARD_T / 2 + 0.01, fw + 0.8, 1.2), 0.2, M_PAINT, face(-1))      # 두 문 사이 — 앞문 옆 (돌아볼 때)
    bm = bmesh.new()                                                  # 긁힌 자국 — 뒷문 옆 판자 (괴물은 문을 긁는다, 제안서 3-1)
    for k in range(4): box(bm, (xb - BOARD_T / 2 - 0.005, fw + 0.4 + k * 0.1, 1.95 - k * 0.04), (0.01, 0.04, 0.85), Matrix.Rotation(math.radians(22), 3, "X"))
    obj("GOUGE", bm, M_BLK)
    wall_pipe(0, xb)                                                  # 관은 앞문 벽을 뚫고 뒷문 벽에서 끝난다
    lamps = hang_lamps((2.0, xa - 1.5), 0.9)                          # 운반갱도 전등 — 앞문 앞에 하나 (문 앞은 밝다, 두 문 사이 · 너머는 어둠)
    return dict(
        lights=lamps, adapt=(((xa + xb) / 2, 0, 1.8), 40, 6), fills=([(3, 0), ((xa + xb) / 2, 0), (xb + 4, 0)], 1.9, 700, 3),
        shots=[("fp_1_approach", (1.0, 0.7, EYE), (xa, -0.1, 1.3)),            # 운반갱도에서 앞문으로 — 전등 아래 판자 벽 · 문 · "풍문"
               ("fp_2_between", (xa + 0.8, 0.5, EYE), (xb, -0.1, 1.2)),         # 앞문을 닫고 두 문 사이 — 머리등뿐, 닫힌 뒷문 · 긁힌 자국
               ("fp_3_behind", (xb - 1.0, -0.4, EYE), (xa, 0.2, 1.3)),          # 뒷문 앞에서 돌아봄 — 닫힌 앞문 (갇힌 6 m)
               ("fp_4_through", (xb - 2.2, 0.3, EYE), (xb + 8, 0, 1.2))],       # 뒷문을 열면 — 나무 버팀 곁갱도, 안 보이던 너머
        shot_only={"DOORB_SHUT": ("fp_1_approach", "fp_2_between", "fp_3_behind"), "DOORB_SHUT_IRON": ("fp_1_approach", "fp_2_between", "fp_3_behind"),
                   "DOORB_OPEN": ("fp_4_through",), "DOORB_OPEN_IRON": ("fp_4_through",)},
        top_hide=tunnel, people=[(xa - 2.5, 0, 0), (xa + 3, 0, 0)], ortho=tun + 4, side_z=1.8, center=(tun / 2, 0))

# ================= 장면 8 — 무너진 기둥 굴 (1편 곁갱도 8 m 구간, 옛 굴 = 우리 바위 굴 + Fab 바위벽 · 돌)
# 레퍼런스: 카드 8 영국 Sharkham Point 갱도(같은 굴 사진 셋) — 네모 동발(다리 둘 + 갓목)이 기울고 · 다리가 안으로 밀리고 · 천장에서 떨어진 돌 더미 · 바닥에 쓰러진 나무 · 동발 사이는 맨 바위.
# 일어나는 일: 동발을 안 고치면 천장이 무너져 길 하나가 사라진다(REP-2 — 판 도중에 맵이 바뀐다). 고칠 곳 = 부러져 처진 갓목(빨간 X) 옆에 새 동발 · 쐐기.
def beam(bm, p0, p1, w=0.2, h=0.2):
    """p0 → p1 로 누운 · 선 각목 (단면 w × h)"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    box(bm, (p0 + p1) / 2, (w, h, d.length), d.to_track_quat("Z", "X" if abs(d.normalized().x) < 0.5 else "Y").to_matrix())

def square_set(bm, x, lean=0.0, sag=0.0, kick=(0.0, 0.0), drop=(0.0, 0.0)):
    """네모 동발: 다리 둘(y ±1.05) + 갓목(2.1 m). lean = 위가 굴 쪽으로 기운 만큼 · sag = 갓목 가운데가 부러져 처진 만큼 · kick = 다리 밑이 안으로 밀린 만큼 · drop = 갓목 끝이 내려앉은 만큼 (왼 · 오른)"""
    ht = 2.1 + (0.15 if MAP else 0.0)                                                  # 맵 모드: 처진 갓목 밑도 2 m 넘게 (저절로 숙이지 않게)
    for k, s in enumerate((-1, 1)): beam(bm, (x, s * (1.05 - kick[k]), 0), (x + lean, s * 1.0, ht - drop[k]))
    L, R = Vector((x + lean, -1.25, ht + 0.11 - drop[0])), Vector((x + lean, 1.25, ht + 0.11 - drop[1]))
    if sag: M = (L + R) / 2 - Vector((0, 0, sag)); beam(bm, L, M, 0.22, 0.22); beam(bm, M, R, 0.22, 0.22)
    else: beam(bm, L, R, 0.22, 0.22)

def rock_pile(cx, cy, rx, ry, h, n, s0, s1, clamp=1.15):
    """돌 더미 자리들 (fab_many 용) — 가운데가 높은 둥근 더미, 굴 안(y ±clamp)에만 (clamp=None 이면 안 묶음)"""
    out = []
    for _ in range(n):
        a, r = random.uniform(0, 2 * math.pi), math.sqrt(random.random())
        py = cy + math.sin(a) * r * ry
        if clamp is not None: py = max(-clamp, min(clamp, py))
        out.append((cx + math.cos(a) * r * rx, py, max(0.0, h * (1 - r * r) * random.uniform(0.4, 1.0) - 0.15), random.uniform(0, 360), random.uniform(s0, s1)))
    return out

def scene8():
    tunnel = []
    a1 = arch_run(["wcbpdfsdw", "wcbpdgcdw"], 0.0, tunnel)                                   # 들어오는 곁갱도 = Fab 나무 버팀 (멀쩡한 곳)
    tun = arch_run(["wcbpdgcdw", "wcbpdfsdw"], a1 + 8.2, tunnel)                             # 무너진 8 m 구간 너머 다시 멀쩡한 곁갱도
    xs = [a1 + 0.6 + i * 1.15 for i in range(7)]                                            # 옛 동발 일곱 (1.15 m 마다)
    bm = bmesh.new()                                                                        # 바위 굴: Fab 구간은 조각 바깥보다 넓게(조각 뒤 바위), 무너진 구간은 폭 2.7 + 천장이 무너진 구멍
    box(bm, (tun / 2, 0, 1.2), (tun + 2, 4.2, 3.0))
    box(bm, (a1 + 4.1, 0, 1.12), (8.6, 2.7, 2.85))
    blob(bm, (xs[3] + 0.5, 0.3, 2.6), (1.3, 0.95, 1.0), 3)
    sh = shell(bm, 0.3)
    if not MAP: sh.data.materials[0] = tint(tex_mat(os.path.join(FABDIR, "ueknfaclw"), 2.0), (0.55, 0.5, 0.45), "rock_fab")   # Fab 광산 바위벽 (착암 자국) — 밝아서 조금 어둡게
    coal_floor(0, tun)
    M_OLD = tint(M_TIMB, (0.42, 0.36, 0.3), "timber_rotten"); M_RED = paint("redpaint", (0.6, 0.05, 0.03), 0.7)
    bm = bmesh.new()
    square_set(bm, xs[0], lean=0.05); square_set(bm, xs[1], lean=0.12)
    square_set(bm, xs[2], lean=0.08, sag=0.22)                                              # 부러져 처진 갓목 — 고칠 곳
    square_set(bm, xs[3], lean=0.15, kick=(0, 0.45), drop=(0, 0.35))                        # 오른 다리가 밀려 들어오고 갓목 끝이 내려앉음
    x = xs[4]; beam(bm, (x, -1.05, 0), (x + 0.1, -1.0, 2.1))                                # 무너진 동발: 왼 다리만 서고
    beam(bm, (x + 0.1, -1.2, 2.2), (x + 0.45, 0.9, 0.95), 0.22, 0.22)                       #   갓목은 돌 더미 위로 떨어지고
    beam(bm, (x - 0.7, 0.75, 0.12), (x + 1.1, 0.95, 0.12))                                  #   오른 다리는 바닥에 누움
    square_set(bm, xs[5], lean=-0.1, sag=0.1); square_set(bm, xs[6], lean=-0.04)
    for a, b in ((0, 1), (5, 6)):                                                           # 동발 위 덧댄 판자 (멀쩡한 곳만)
        for y in (-0.8, -0.4, 0.0, 0.4, 0.8): beam(bm, (xs[a] - 0.2, y, 2.36), (xs[b] + 0.25, y, 2.36), 0.18, 0.04)
    beam(bm, (xs[3] + 0.2, -0.3, 2.36), (xs[3] + 0.95, -0.15, 1.55), 0.18, 0.04)             # 구멍에서 늘어진 부러진 판자
    beam(bm, (xs[3] + 0.3, 0.35, 2.36), (xs[3] + 0.8, 0.5, 1.8), 0.18, 0.04)
    box_uv(obj("TIMBER_OLD", bm, M_OLD).data, 0.8)
    bm = bmesh.new()                                                                        # 새 동발 재료 (고칠 곳 옆 — 벽에 기댄 다리 · 바닥의 갓목 · 쐐기)
    beam(bm, (xs[2] - 0.55, -1.12, 0), (xs[2] - 0.5, -1.3, 2.0))
    beam(bm, (xs[1] + 0.2, -1.05, 0.11), (xs[1] + 2.3, -1.0, 0.11), 0.22, 0.22)
    for k in range(3): box(bm, (xs[2] - 0.2 + k * 0.18, -0.75, 0.04), (0.12, 0.25, 0.07), Matrix.Rotation(random.uniform(-0.4, 0.4), 3, "Z"))
    box_uv(obj("TIMBER_NEW", bm, M_TIMB).data, 0.8)
    bm = bmesh.new()                                                                        # 빨간 X — 위험 표시 (고칠 동발 왼 다리, 오는 쪽 면)
    for s in (-1, 1): box(bm, (xs[2] + 0.057 - 0.12, -1.05, 1.5), (0.006, 0.035, 0.3), Matrix.Rotation(math.radians(30 * s), 3, "X"))
    obj("MARK", bm, M_RED)
    FABMAT["wd3efb0"] = tint(tex_mat(os.path.join(FABDIR, "wd3efb0"), 1 / 0.35), (0.62, 0.62, 0.66), "stone_grey")   # 스캔 돌이 붉다 — 벽 바위 색에 맞춰 회색으로
    fab_many("vmhdagb", [(xs[3] + 0.5, 0.45, 0.0, 30, 1.0)])                                # 흙 더미 + 떨어진 돌 (Fab 스캔 돌 9 cm × 5~12 배)
    fab_many("wd3efb0", rock_pile(xs[3] + 0.5, 0.55, 1.5, 0.7, 1.0, 80, 3, 8))
    fall = fab_many("wd3efb0", rock_pile(a1 + 4.4, 0.0, 3.3, 1.35, 2.3, 160, 4, 11))         # 안 고치면 — 무너져 굴이 막힌다 (④ 한 장에만)
    for o in fall: o.name = "FALL_" + o.name
    eye_in, at_in = (a1 - 1.6, 0.15, EYE), (a1 + 5.5, 0.0, 1.2)
    return dict(
        lights=[], adapt=((a1 + 4, 0, 1.8), 25, 4), fills=([(2, 0), (a1 + 2, 0), (a1 + 6, 0), (tun - 3, 0)], 1.9, 250, 1.5),
        shots=[("fp_1_enter", eye_in, at_in),                                              # 멀쩡한 곁갱도에서 — 기운 동발 · 처진 갓목 · 돌 더미
               ("fp_2_squeeze", (xs[2] + 0.45, -0.5, EYE), (xs[5] + 0.8, -0.3, 1.4)),      # 돌 더미 옆 좁아진 길 (폭 약 1 m) — 머리 위 무너진 동발
               ("fp_3_repair", (xs[2] - 1.7, 0.35, EYE), (xs[2], -0.5, 1.55)),              # 고칠 곳 — 부러진 갓목 · 빨간 X · 새 동발 재료
               ("fp_4_collapsed", eye_in, at_in)],                                         # 안 고치면 — ① 과 같은 자리, 굴이 막혔다
        shot_only={o.name: ("fp_4_collapsed",) for o in fall},
        top_hide=tunnel, people=[(xs[1] + 0.6, -0.6, 0)], ortho=tun + 4, side_z=1.2, center=(tun / 2, 0))

# ================= 장면 2 — 낮은 채탄 막장 (1편, 막다른 곳 6 × 15 m, 천장 1.3~1.6 m)
# 레퍼런스: 카드 2 국내 사진(한국광물자원공사 — 광부 둘이 무릎 꿇고 캠) · Commons 옛 낮은 막장 그림들. 공통점 = 천장이 낮아 무릎 · 쪼그려서만 ·
#   둥근 통나무 기둥이 촘촘히 줄지어 · 위에 통나무 갓목 · 검은 석탄 벽 · 석탄 부스러기 바닥 · 바닥을 기는 공기 호스.
# 일어나는 일: 광석이 가장 많고 가장 위험하다 — 숙여서만 들어가는 막다른 곳이라, 캐는 동안 괴물이 입구에 오면 빠져나갈 길이 없다.
def coal_room_mats(me, sel):
    """낮은 막장 굴의 벽 = 석탄 · 천장 = 셰일 (sel = 입힐 면). 재질 칸 0 바위 · 1 바닥 뒤에 2 석탄 벽 · 3 셰일 천장을 붙인다"""
    while len(me.materials) < 4: me.materials.append(None)
    me.materials[2] = tint(tex_mat(os.path.join(FABDIR, "ueknfaclw"), 1.5), (0.14, 0.14, 0.16), "coal_wall")          # 석탄 (Fab 착암 바위를 검게)
    me.materials[3] = tint(tex_mat(os.path.join(FABDIR, "ueknfaclw"), 2.0), (0.2, 0.19, 0.18), "roof_shale")          # 셰일 (머리등이 가까워 하얗게 탄다 — 많이 어둡게)
    nz = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", nz); nz = nz.reshape(-1, 3)[:, 2]
    mi = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("material_index", mi)
    mi[sel & (nz <= 0.55)] = 2; mi[sel & (nz < -0.55)] = 3; me.polygons.foreach_set("material_index", mi)

CROUCH = 1.0                                                          # 숙인 눈 (Tuning.CROUCH_EYE)
def scene2():
    tunnel = []
    a1 = arch_run(["wcbpdfsdw", "wcbpdgcdw"], 0.0, tunnel)                                   # 들어오는 곁갱도 = Fab 나무 버팀 (천장 2.1)
    L, W = 15.0, 6.0; tun = a1 + L
    bm = bmesh.new()
    box(bm, (a1 / 2, 0, 1.2), (a1 + 2, 4.2, 3.0))                                           # Fab 조각 뒤 바위
    c1, c2 = (1.35, 1.1) if not MAP else (LOWEST + 0.1, LOWEST)                             # 천장 (+ 울퉁불퉁 0~0.3) — 맵 모드는 선 채로 (사용자 10-01)
    box(bm, (a1 + L * 0.3, 0, (c1 - 0.3) / 2), (L * 0.6 + 0.3, W, c1 + 0.3))                 # 막장 앞쪽
    box(bm, (a1 + L * 0.8, 0, (c2 - 0.3) / 2), (L * 0.4, W - 0.6, c2 + 0.3))                 # 안쪽 — 막장 벽으로 갈수록 낮다
    sh = shell(bm, 0.3); me = sh.data
    if not MAP: coal_room_mats(me, np.ones(len(me.polygons), dtype=bool))                # 맵 모드에선 map4 가 구역 자리의 면에 입힌다
    coal_floor(0, tun)
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
    roof = lambda x, y: sc.ray_cast(deps, Vector((x, y, 0.3)), Vector((0, 0, 1)), distance=5)[1].z
    props, caps = [], []                                                                    # 둥근 통나무 기둥 줄 넷 (1.0 m 마다) + 줄 위 통나무 갓목 (2.4 m 씩)
    for ry in (-2.3, -1.0, 1.0, 2.3):
        x = a1 + 0.8
        while x < tun - 1.0:
            seg = [x + i * 1.0 + random.uniform(-0.12, 0.12) for i in range(3) if x + i * 1.0 < tun - 0.8]
            zc = min(roof(px, ry) for px in seg + [x + 2.4]) - 0.12                         # 갓목 가운데 높이 (통나무 반지름 약 0.1 + 틈)
            caps.append((x - 0.2, ry, zc, 0, 0.98, (0, 90)))                                # 눕힌 통나무 (Y 로 90° → 긴 쪽이 +X)
            for px in seg: props.append((px + random.uniform(-0.12, 0.12), ry + random.uniform(-0.22, 0.22), 0.0, random.uniform(0, 360), (zc - 0.1) / 1.61, (random.uniform(-5, 5), random.uniform(-5, 5))))
            x += 2.4
    for fid in ("tgnidj2fa", "tgmrafyfa"): FABMAT[fid] = tint(tex_mat(os.path.join(FABDIR, fid), 1 / 0.35), (0.5, 0.44, 0.38), fid + "_dust")   # 석탄 가루 앉은 나무 (스캔 나무가 희다)
    fab_many("tgnidj2fa", props)                                                            # Fab 나무 기둥 1.61 m (조금씩 기울게)
    fab_many("tgmrafyfa", caps)                                                             # Fab 나무 기둥 2.56 m 를 눕혀 갓목으로
    FABMAT["wd3efb0"] = tint(tex_mat(os.path.join(FABDIR, "wd3efb0"), 1 / 0.35), (0.09, 0.09, 0.1), "coal_lump")   # 캘 석탄 = 막장 발치에 깨진 석탄 더미 (스캔 돌을 검게)
    cb = next(n for n in FABMAT["wd3efb0"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")   # 스캔 돌의 반들거림이 빛을 되쏴 회색으로 보인다 — 덜 반들거리게
    for l in list(cb.inputs["Roughness"].links): FABMAT["wd3efb0"].node_tree.links.remove(l)
    cb.inputs["Roughness"].default_value = 0.55; cb.inputs["Specular IOR Level"].default_value = 0.25
    fab_many("wd3efb0", rock_pile(tun - 0.9, 0.0, 0.8, 2.6, 0.55, 110, 2, 6) + rock_pile(tun - 3.0, -2.5, 0.9, 0.4, 0.4, 25, 2, 5))
    cu = bpy.data.curves.new("HOSE", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.03; cu.bevel_resolution = 3   # 바닥을 기는 공기 호스 (사진)
    pts = [(a1 - 4, -0.9), (a1 - 1, -1.0), (a1 + 1.5, -0.6), (a1 + 4, -0.3), (a1 + 7, -0.55), (a1 + 10, -0.2), (tun - 2.2, -0.5), (tun - 1.4, -1.2)]
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = 3
    for pt, (hx, hy) in zip(sp.points, pts): pt.co = (hx, hy, 0.04, 1)
    ho = bpy.data.objects.new("HOSE", cu); sc.collection.objects.link(ho); cu.materials.append(paint("rubber", (0.02, 0.02, 0.02), 0.5))
    fab_many("uddjeelqx", [(tun - 1.8, -1.6, 0.0, 70, 1.0)])                               # 삽 (막장 앞에 누움)
    M_EYE = paint("eye", (1.0, 0.85, 0.6), 0.3, 0, 25.0)
    bm = bmesh.new()
    for dy in (-0.065, 0.065): blob(bm, (a1 - 0.2, 0.15 + dy, 1.2), (0.02, 0.028, 0.022), 2)   # 입구에 선 그것의 눈 두 점 (④ 한 장에만)
    obj("EYES", bm, M_EYE).visible_shadow = False
    print("CHECK scene2 roof at mouth %.2f  middle %.2f  face %.2f" % (roof(a1 + 1, 0), roof(a1 + 7, 0), roof(tun - 1.5, 0)))
    return dict(
        lights=[], adapt=((a1 + 7, 0, 1.0), 20, 4), fills=([(a1 - 2, 0), (a1 + 3, 0), (a1 + 8, 0), (tun - 2, 0)], 1.1, 200, 1.5),
        shots=[("fp_1_mouth", (a1 - 2.2, 0.2, EYE), (a1 + 6, 0, 0.8)),                     # 곁갱도에서 — 낮은 입구와 그 너머 통나무 기둥 숲
               ("fp_2_crouch_in", (a1 + 2.0, 0.1, CROUCH), (tun, 0.3, 0.7)),               # 숙여 들어감 — 머리 위 갓목, 끝에 반짝이는 석탄
               ("fp_3_face", (tun - 3.2, -0.6, CROUCH), (tun, -0.7, 0.5)),                 # 막장 벽 앞 — 캘 석탄 더미 · 삽 · 호스 끝
               ("fp_4_back", (tun - 2.5, 0.2, CROUCH), (a1 - 1, 0.15, 1.1))],             # 캐다가 돌아봄 — 입구가 멀다, 거기 눈 두 점 (빠져나갈 길이 없다)
        shot_only={"EYES": "fp_4_back"},
        top_hide=tunnel, people=[(a1 + 6, 0.0, 0)], ortho=tun + 4, side_z=1.0, center=(tun / 2, 0))

def fab_many(fid, places, **kw):
    """같은 Fab 모델을 여러 자리에 — 한 번만 불러오고 그물을 나눠 쓴다. places = [(x, y, z, yaw, 배율)] 또는 끝에 (rx, ry) 도 (눕히기, 도) (밑면 가운데 자리)"""
    objs, lo, hi = fab(fid, (0, 0, 0), **kw); out = []
    for k, p in enumerate(places):
        x, y, z, yaw, s_ = p[:5]; e = Euler([math.radians(a) for a in (*(p[5] if len(p) > 5 else (0, 0)), yaw)])
        for o in objs:
            c = o if k == 0 else o.copy()
            if k: sc.collection.objects.link(c)
            off = Vector(o.location) if k == 0 else base[o.name]
            if k == 0: base[o.name] = off.copy()
            c.rotation_euler = e; c.scale = (s_, s_, s_)
            c.location = Vector((x, y, z)) + e.to_matrix() @ (off * s_)
            out.append(c)
    return out
base = {}

# ================= 영상 재현 (사용자 09-30 "Fab 소개 영상은 같은 모델인데 우리는 왜 이렇게 못 나오나") — 영상 5 초 컷: 강철 아치 + 오른쪽 광차 + 왼쪽 광차 틀
# 게임에서 하나씩 켜 보려고 이름으로 묶는다: DRESS_*(채움 — 흙 더미 · 돌 · 판자 · 연장 · 물웅덩이) · BLUE_<i>(먼 곳 차가운 빛 자리) · LAMP_<i>(따뜻한 등)
def scene_v():
    x = 0.0; arch = ["wdpncihdw"] * 6                                  # 영상과 같은 조각 (둥근 통나무 덧댐 + 빨간 관) — 한 가지만 이어서 관 자리가 같다
    for fid in arch:
        objs, lo, hi = fab(fid, (0, 0, 0), yaw=180); L = hi[0] - lo[0]; yc = (lo[1] + hi[1]) / 2   # 180° — 관이 오른쪽 벽 (영상)
        for o in objs: o.location.x += x - lo[0]; o.location.y -= yc
        x += L
    tun = x
    bm = bmesh.new(); box(bm, (tun / 2, 0, -0.02), (tun + 2, 7, 0.04)); fl = obj("FLOOR", bm, M_FLOOR); box_uv(fl.data, 0.35)
    cg = os.path.join(ROOT, "build", "tex_test", "fab_coalground")
    if os.path.isdir(cg): fl.data.materials[0] = tex_mat(cg, 2.0)
    rx = 0.0
    while rx < tun - 1:
        objs, lo, hi = fab("ufekaeedw", (rx, -0.8, 0), rails=True); L = hi[0] - lo[0]   # 선로는 오른쪽으로 치우쳐 (영상)
        for o in objs: o.location.x += L / 2
        rx += L
    deps = bpy.context.evaluated_depsgraph_get()
    fab("ueujednfa", (2.7, -0.8, 0.12), along=True)                   # 영상처럼 오른쪽 앞 큰 광차
    fab("ufmodhpfa", (11.5, -0.8, 0.12), along=True)                  # 멀리 선로 위 빈 광차
    fab("vcyjedsfa", (2.2, 1.3, 0.0), yaw=-15, along=True)            # 왼쪽 광차 틀
    # 채움 (DRESS_) — 영상: 벽 밑 흙 더미 · 흩어진 돌 · 판자 · 기대 세운 삽 · 물웅덩이
    dress = []
    dress += fab_many("vmhdagb", [(2.5, -1.6, 0, 20, 1.0), (9, 1.8, 0, 200, 1.2), (16, -1.7, 0, 90, 1.1), (21, 1.7, 0, 140, 0.9)])
    dress += fab_many("wjfidjgdb", [(7, 0.3, 0.01, 0, 1.0), (14, -0.6, 0.01, 60, 1.0)])
    dress += fab_many("wd3efb0", [(random.uniform(1, tun - 1), random.choice((-1, 1)) * random.uniform(0.9, 1.9), 0, random.uniform(0, 360), random.uniform(1.5, 5)) for _ in range(40)])
    dress += fab_many("tezvbcuda", [(random.uniform(1, tun - 1), random.uniform(-1.8, 1.8), 0.02, random.uniform(0, 360), 1.0) for _ in range(10)])
    dress += fab_many("uebpbetfa", [(3.0, -1.2, 0.02, 75, 1.0), (10.5, 1.5, 0.02, 10, 1.0), (18, -1.4, 0.02, 100, 1.0)])
    dress += fab_many("uddjeelqx", [(6.6, 1.0, 0.0, 95, 1.0)])          # 삽 (광차 옆에 눕힘)
    dress += fab_many("udklcbuiw", [(8.5, -1.3, 0.0, 30, 1.0)])         # 안전모
    bm = bmesh.new()
    for cxy, s_ in (((11.0, -0.7), (1.6, 0.9)), ((15.5, 0.9), (2.2, 1.0)), ((19.0, -0.2), (1.4, 1.2))): box(bm, (cxy[0], cxy[1], 0.03), (s_[0], s_[1], 0.005))
    dress.append(obj("DRESS_PUDDLE", bm, paint("puddle", (0.02, 0.02, 0.025), 0.03)))
    for i, o in enumerate(dress):
        if not o.name.startswith("DRESS_"): o.name = "DRESS_%03d_%s" % (i, o.name)
    lamps = []
    for lx in (3, 9, 15):                                              # 따뜻한 등 (천장 가운데 — 영상처럼)
        hit, loc, *_ = sc.ray_cast(deps, Vector((lx, 0.0, 1.7)), Vector((0, 0, 1)), distance=10); top = loc.z if hit else 3.3
        fab("vgyidfpaw", (lx, 0.0, top - 0.25)); lamps.append(("L%d" % lx, (lx, 0.0, top - 0.4), 120, (1.0, 0.62, 0.3), 0.08, True))
    blues = [("BLUE0", (tun - 2.5, 0.0, 1.6), 400, (0.35, 0.55, 1.0), 1.5, True)]   # 먼 곳 차가운 빛 (영상의 푸른 끝)
    return dict(
        lights=lamps + blues, adapt=((tun / 2, 0, 2), 20, 6), fills=([(4, 0), (12, 0), (20, 0)], 3.0, 700, 3),
        shots=[("fp_1_video5", (0.2, 0.55, 1.35), (tun, -0.25, 1.05))],   # 영상 5 초 컷과 비슷한 구도 (낮은 카메라, 왼쪽에서 오른쪽 앞 광차를 끼고)
        blue_names=[b[0] for b in blues], people=[(4, 0, 0)], ortho=tun + 4, side_z=1.8, center=(tun / 2, 0))

# ================= 맵 모드 — MAP4 1편 전체 (사용자 10-01 "전체 맵을 끝까지 만들어라. 그 뒤에 텍스처 · 구조를 말하겠다")
# 통과한 장면(⑨ ⑥ ① ③ ⑦ ⑧ ②)을 제자리에 놓고 굴 종류로 잇는다(제안서 4절 짜임). 바위는 맵 전체 한 덩어리 — 이음새 · 막힌 끝이 없다.
#   SCENE=m EXPORT_GLB=Assets/Fab/Resources/Map4.glb blender -b --factory-startup -P blender/map/scene_mock.py   (Fab 이 들어 있어 git 금지)
# 좌표 m: 승강장 = (0, 0), 동 +x, 북 +y. 굴 종류(제안서 원칙 2): haul 운반갱도(Fab 강철 아치 · 레일 · 전등) · side 곁갱도(Fab 나무 버팀)
#   · prop 쇠동발 길(Fab 쇠동발) · old 옛 굴(맨 바위 + 썩은 동발) · low 막장길(낮은 바위). 갈림길마다 칠한 표지 · 몇 곳에 판자 문 칸.
KIND = {"haul": (6.4, 4.1), "side": (4.2, 2.8), "prop": (4.0, 2.8), "old": (3.0, 2.7), "low": (3.0, 2.6), "incline": (3.4, 3.0)}   # 바위 공기 (폭, 높이) — 모두 선 채로 지난다 (사용자 10-01)
FAB_RUN = {"haul": ["wdpnchedw", "wdpnchtdw"], "side": ["wcbpdfsdw", "wcbpdgcdw"]}   # 굴 종류마다 Fab 조각 (사용자 09-30)
LIB, LIGHTS, SHOTS = {}, [], []

def lib(fid, key=None, mat=None, **kw):
    """Fab 모델을 한 번만 불러와 장면에서 빼 둔다 — 놓을 때는 그물을 나눠 쓰는 복사본 (GLB 에도 그물은 한 번만). key · mat = 같은 모델을 다른 재질로 (돌 → 바위 · 석탄)"""
    key = key or fid
    if key not in LIB:
        objs, lo, hi = fab(fid, (0, 0, 0), **kw)
        for o in objs:
            if mat is not None: o.data = o.data.copy(); o.data.materials.clear(); o.data.materials.append(mat)
            sc.collection.objects.unlink(o)
        LIB[key] = (objs, hi[0] - lo[0])
    return LIB[key]

def put(key, M):
    objs, _ = lib(key); out = []
    for o in objs:
        c = o.copy(); sc.collection.objects.link(c); c.matrix_world = M @ o.matrix_world; out.append(c)
    return out

def frame(a, b, z=0.0):
    """a → b 굴의 틀: 원점 a (높이 z), X = 굴 방향. (틀, 길이)"""
    d = Vector((b[0] - a[0], b[1] - a[1], 0)); return Matrix.Translation((a[0], a[1], z)) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z"), d.length

def run(kind, a, b, z=0.0):
    """a → b 사이를 Fab 조각으로 잇는다 — 조각 수를 반올림하고 길이 방향만 늘이거나 줄여 딱 맞춘다"""
    F, L = frame(a, b, z); ids = FAB_RUN[kind]; lens = [lib(i)[1] for i in ids]
    n = max(1, round(L / (sum(lens) / len(lens)))); seq = [ids[k % len(ids)] for k in range(n)]
    k = L / sum(lib(i)[1] for i in seq); x = 0.0
    for fid in seq:
        l = lib(fid)[1] * k; put(fid, F @ Matrix.Translation((x + l / 2, 0, 0)) @ Matrix.Diagonal((k, 1, 1, 1))); x += l

def rails(a, b, z=0.0, y=0.0):
    F, L = frame(a, b, z); n = max(1, round(L / 2.5)); k = L / (n * 2.5)
    for i in range(n): put("rail", F @ Matrix.Translation(((i + 0.5) * 2.5 * k, y, 0)) @ Matrix.Diagonal((k, 1, 1, 1)))

LAMP_H = 2.8                                                             # 전등 빛 높이 (바닥 위) = 판정 받은 운반갱도 전등 높이. 게임 전등 빛은 4 m(FAB_LIGHT_RANGE)까지라 4~5.5 m 천장에 붙이면 천장만 밝힌다 (v2 "전체가 많이 어둡다")
CORDS = []                                                               # 높은 천장에서 전등까지 늘어뜨린 줄 (가운데, 크기)
LAMP_WALL = 2.0                                                          # 방 가장자리 전등과 벽 사이 (m)
def lamp_at(x, y, z, top_guess, name, energy=120, col=(1.0, 0.62, 0.3)):
    """철망 갓 전등을 천장 밑에 단다 (천장은 광선으로 잰다) — 천장이 높으면 줄에 매달아 LAMP_H 까지 내린다. 게임에서 LAMP_ = 판정값 빛(Tuning.FAB_*), ZL_<색> = 구역 색 등"""
    deps = bpy.context.evaluated_depsgraph_get(); hit, loc, *_ = sc.ray_cast(deps, Vector((x, y, z + 1.6)), Vector((0, 0, 1)), distance=12)
    top = loc.z if hit else z + top_guess; lz = min(top - 0.45, z + LAMP_H); put("vgyidfpaw", Matrix.Translation((x, y, lz + 0.2)))
    if top - lz > 0.55: CORDS.append(((x, y, (top + lz + 0.45) / 2), (0.014, 0.014, top - lz - 0.45 + 0.3)))   # 줄 끝은 바위 속 0.15 m (울퉁불퉁한 천장에 떠 보이지 않게)
    LIGHTS.append((name % len(LIGHTS) if "%d" in name else name, (x, y, lz), energy, col, 0.08, True))

def lamp_grid(n, nx, ny, name, **kw):
    """방을 nx × ny 칸으로 나눠 칸마다 전등 하나. 전등 높이에 뭔가(돌 더미 · 석탄 기둥 · 통나무)가 있으면 옆으로 비킨다"""
    deps = bpy.context.evaluated_depsgraph_get()
    for ix in range(nx):
        for iy in range(ny):
            x0, y0 = n["x"] - n["w"] / 2 + (ix + 0.5) * n["w"] / nx, n["y"] - n["d"] / 2 + (iy + 0.5) * n["d"] / ny
            # 가장자리 칸은 벽에서 LAMP_WALL 로 붙인다 — 빛이 4 m 까지라 방 가운데 전등은 천장만 밝히고 벽은 검다 (검수 10-01: 방 폭 · 끝 벽이 안 읽힌다). 한 줄뿐이면 양쪽 벽으로 번갈아
            if nx > 1 and ix in (0, nx - 1): x0 = n["x"] + (1 if ix else -1) * (n["w"] / 2 - LAMP_WALL)
            elif nx == 1 and ny > 1: x0 = n["x"] + (1 if iy % 2 else -1) * (n["w"] / 2 - LAMP_WALL)
            if ny > 1 and iy in (0, ny - 1): y0 = n["y"] + (1 if iy else -1) * (n["d"] / 2 - LAMP_WALL)
            elif ny == 1 and nx > 1: y0 = n["y"] + (1 if ix % 2 else -1) * (n["d"] / 2 - LAMP_WALL)
            for dx, dy in ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2), (3, 3), (-3, -3), (3, -3), (-3, 3)):
                if not any(sc.ray_cast(deps, Vector((x0 + dx, y0 + dy, n["z"] + h_)), Vector((math.cos(t), math.sin(t), 0)), distance=1.2)[0] for h_ in (2.0, 2.5) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)): break
            lamp_at(x0 + dx, y0 + dy, n["z"], n["h"], name, **kw)

def pole_lamp(bm, p, name, energy=50, col=(1.0, 0.69, 0.44)):
    """세워 둔 작업등 — 천장이 너무 높아 못 매다는 곳(⑨ 12~16 m). 기둥 + 팔 끝에 전등, 빛 높이는 LAMP_H"""
    deps = bpy.context.evaluated_depsgraph_get(); hit, loc, *_ = sc.ray_cast(deps, Vector((p.x, p.y, p.z + 2.0)), Vector((0, 0, -1)), distance=4)
    z = loc.z if hit else p.z
    box(bm, (p.x - 0.4, p.y, z + (LAMP_H + 0.6) / 2), (0.09, 0.09, LAMP_H + 0.6)); box(bm, (p.x - 0.2, p.y, z + LAMP_H + 0.5), (0.5, 0.06, 0.06)); box(bm, (p.x - 0.4, p.y, z + 0.04), (0.5, 0.5, 0.08))
    put("vgyidfpaw", Matrix.Translation((p.x, p.y, z + LAMP_H + 0.2))); LIGHTS.append((name % len(LIGHTS), (p.x, p.y, z + LAMP_H), energy, col, 0.08, True))

def ceiling_lamps(a, b, z=0.0, step=8.0, y=0.9):
    F, L = frame(a, b, z); bpy.context.view_layer.update()
    for i in range(int(L // step)):
        p = F @ Vector((step / 2 + i * step, y, 0)); lamp_at(p.x, p.y, z, 3.3, "L%d")

def old_sets(a, b, z=0.0, step=1.6):
    """옛 굴: 썩은 네모 동발 (조금씩 기울고 처짐) — 시안 ⑧ 과 같은 모양"""
    F, L = frame(a, b, z); bm = bmesh.new(); x = 1.0
    while x < L - 0.8:
        square_set(bm, x, lean=random.uniform(-0.12, 0.12), sag=random.choice((0, 0, 0, 0.1, 0.18)), kick=(random.choice((0, 0, 0.2)), random.choice((0, 0, 0.2))))
        x += step + random.uniform(-0.2, 0.3)
    if bm.verts: bm.transform(F); box_uv(obj("TIMBER_OLD", bm, M_OLD_).data, 0.8)

def steel_props(a, b, z=0.0, step=1.2):
    """쇠동발 길: Fab 늘어나는 쇠동발 두 줄 (시안 ① 의 은색 숲)"""
    F, L = frame(a, b, z); x = 0.8
    while x < L - 0.5:
        for yy in (-1.5, 1.5):
            put("ugfmehgfa", F @ Matrix.Translation((x + random.uniform(-0.1, 0.1), yy + random.uniform(-0.1, 0.1), 0)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z") @ Matrix.Diagonal((1, 1, 0.9, 1)))
        x += step

DRESS_Y = {"haul": (1.5, 2.0), "side": (0.75, 0.95), "prop": (1.75, 1.9), "old": (0.7, 0.9), "low": (0.8, 1.0), "incline": (0.9, 1.2)}   # 채움을 놓는 벽 쪽 거리 (레일 · 기둥 줄을 비킨다)
def dress_tunnel(a, b, kind, z=0.0):
    """굴 채움 (영상 재현 Z — 사용자 10-01 "넣는다"): 5~8 m 마다 벽 밑 흙 더미 · 흩어진 돌(석탄 덩이) · 판자, 가끔 삽 · 안전모"""
    F, L = frame(a, b, z); x = random.uniform(1.5, 4.0); y0, y1 = DRESS_Y[kind]
    while x < L - 1.0:
        side = random.choice((-1, 1)); y = side * random.uniform(y0, y1); r = random.random()
        if r < 0.35: put("vmhdagb", F @ Matrix.Translation((x, side * (y1 + 0.2), 0)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z") @ Matrix.Diagonal((0.6, 0.6, 1.0, 1)))
        elif r < 0.6: put(random.choice(("uebpbetfa", "uebpbd3fa")), F @ Matrix.Translation((x, y, 0.01)) @ Matrix.Rotation(random.uniform(-0.35, 0.35), 4, "Z"))
        elif r < 0.68: put(random.choice(("uddjeelqx", "udklcbuiw")), F @ Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z"))
        for _ in range(random.randint(2, 4)):
            s_ = random.uniform(1.5, 4.5); put("coal", F @ Matrix.Translation((x + random.uniform(-1.2, 1.2), side * random.uniform(y0 * 0.7, y1 + 0.1), 0)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z") @ Matrix.Diagonal((s_, s_, s_, 1)))
        x += random.uniform(5.0, 8.0)

def plank_door(center, d, name, iron=False):
    """판자 문 칸의 문 (카드 13): 문틀 + 세운 판자 사이 2.5 cm 틈(밖이 보인다) + 띠장 둘. d = 칸 안쪽 방향, 안쪽으로 조금 열려 있다. iron = 화약고 쇠문"""
    F = Matrix.Translation(center) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z"); bm = bmesh.new(); bmd = bmesh.new()
    for s_ in (-1, 1): box(bm, (0, s_ * 0.6, 1.15), (0.14, 0.12, 2.3))
    box(bm, (0, 0, 2.28), (0.14, 1.32, 0.14))
    H = Matrix.Translation((0, -0.54, 0)) @ Matrix.Rotation(math.radians(-25), 4, "Z")          # 경첩 = 한쪽 문틀, 안쪽으로 25° 열림
    if iron: box(bmd, H @ Vector((0.0, 0.54, 1.1)), (0.05, 1.06, 2.15), H.to_3x3())
    else:
        for k in range(9): box(bmd, H @ Vector((0.0, 0.05 + k * 0.12, 1.1)), (0.035, 0.095, 2.1), H.to_3x3())
        for z in (0.4, 1.8): box(bmd, H @ Vector((0.04, 0.54, z)), (0.03, 1.02, 0.12), H.to_3x3())
    bm.transform(F); bmd.transform(F); box_uv(obj("TIMBER_" + name, bm, M_TAR_).data, 0.8)
    box_uv(obj("DOOR_" + name, bmd, M_IRONDOOR_ if iron else M_OLD_).data, 0.8)

def sign_hidden(c, n, w, h, eye):
    """표지 판이 눈 자리(eye)에서 얼마나 가렸나 (0~1): 판 앞면의 점 7 × 3 으로 쏜다 — 판 · 글자보다 먼저 맞는 것이 있으면 가린 것 (사용자 10-01 "표지판이 벽에 박혀 있다")"""
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get(); r = Vector((-n.y, n.x, 0)); bad = 0
    for i in range(7):
        for j in range(3):
            q = c + r * (w * (i / 6 - 0.5) * 0.9) + Vector((0, 0, h * (j / 2 - 0.5) * 0.8)); v = q - eye
            hit, loc, _, _, ob, _ = sc.ray_cast(deps, eye, v.normalized(), distance=v.length)
            bad += bool(hit and (loc - q).length > 0.09 and not ob.name.startswith(("NOCOL_SIGN", "TEXT")))
    return bad / 21

def sign_size(front, back): return max(len(l[0]) * l[1] for l in front + back) * 0.95 + 0.3, 0.2 + sum(l[1] * 1.12 for l in front)   # 판 (폭, 높이)

def whitewash(m, name):
    """흰 칠한 나무판 재질 — 나뭇결 그림을 밝게 바랜 사본으로 바꾼다 (glTF 는 색을 곱하기만 해서 어두운 나무를 밝게 못 만든다)"""
    t = m.copy(); t.name = name; inp = next(n for n in t.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"]
    tex = inp.links[0].from_node if inp.links else None
    if tex is None or tex.type != "TEX_IMAGE": inp.default_value = (0.55, 0.53, 0.47, 1); return t
    im = tex.image.copy(); im.name = name; px = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
    px[:, :3] = 0.40 + px[:, :3] * 0.38; px[:, 1] *= 0.98; px[:, 2] *= 0.92; im.pixels = px.ravel(); im.pack(); tex.image = im; return t

def hang_sign(c, d, front, back, floor):
    """굴 입구에 매단 양면 표지 판. c = 판 가운데(수평 자리), d = 굴 쪽 방향(수평). front = 방 안에서 보이는 줄들(이 굴이 가는 곳), back = 굴에서 들어오며 보이는 줄들(이 방 이름)
    판 밑 = 바닥 위 SIGN_Z (선 채로 지난다), 천장까지 쇠줄 둘. 돌려주는 값 (판 가운데, 폭, 높이)"""
    w, hb = sign_size(front, back); C = Vector((c.x, c.y, floor + SIGN_Z + hb / 2)); F = Matrix.Translation(C) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z")   # 판의 X = 굴 방향(두께), Y = 폭
    deps = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); box(bm, (0, 0, 0), (0.05, w, hb))
    for s_ in (-1, 1):                                                                         # 쇠줄: 판 위에서 천장까지 (바위 속 0.15 m)
        top = F @ Vector((0, s_ * (w / 2 - 0.12), hb / 2)); hit, loc, *_ = sc.ray_cast(deps, top + Vector((0, 0, 0.02)), Vector((0, 0, 1)), distance=8)
        L = (loc.z - top.z if hit else 0.6) + 0.15; box(bm, (0, s_ * (w / 2 - 0.12), hb / 2 + L / 2), (0.02, 0.02, L))
    bm.transform(F); box_uv(obj("NOCOL_SIGNBOARD", bm, M_SIGNBOARD_).data, 0.8)
    for lines, face in ((front, -d), (back, d)):
        z = C.z + (hb - 0.1) / 2 if lines is front else C.z + sum(l[1] * 1.12 for l in lines) / 2
        for body, sz, *mt in lines:
            z -= sz * 0.86; text(body, tuple(Vector((C.x, C.y, z)) + face * 0.032), sz, mt[0] if mt else M_SIGNTEXT_, (math.radians(90), 0, math.atan2(face.x, -face.y))); z -= sz * 0.26
    return C, w, hb
SIGN_Z = 2.15                                                            # 표지 판 밑 높이 (m) — 저절로 숙이는 높이 1.95 m 위

def box_uv_fast(me, per_m):
    """box_uv 와 같은 UV 를 numpy 로 (맵 바위는 면이 수백만)"""
    if not me.uv_layers: me.uv_layers.new()
    vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); c = co.reshape(-1, 3)[vi]
    pn = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", pn); lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_total", lt)
    ax = np.repeat(np.abs(pn.reshape(-1, 3)).argmax(1), lt)
    u = np.where(ax == 0, c[:, 1], c[:, 0]); v = np.where(ax == 2, c[:, 1], c[:, 2])
    me.uv_layers.active.data.foreach_set("uv", (np.stack([u, v], 1) * per_m).ravel())

def unified_shell():
    """모은 공기 전부 → 바위 굴 한 덩어리 (shell() 과 같은 법: 복셀 → 면 뒤집기 → 바위 쪽으로만 파는 잡음). 파는 깊이는 공기마다 (가장 깊은 것)"""
    ball = bmesh.new()
    for b, carve, big in AIR:
        me = bpy.data.meshes.new("a"); b.to_mesh(me); ball.from_mesh(me); bpy.data.meshes.remove(me)
    air = obj("AIR", ball, M_WALL)
    rm = air.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
    cave_me = bpy.data.meshes.new_from_object(air.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(air, do_unlink=True)
    b = bmesh.new(); b.from_mesh(cave_me); bmesh.ops.reverse_faces(b, faces=b.faces); b.normal_update(); b.to_mesh(cave_me); b.free()
    cave = bpy.data.objects.new("CAVE", cave_me); sc.collection.objects.link(cave)
    nv = len(cave_me.vertices); co = np.empty(nv * 3); cave_me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    nz = np.empty(nv * 3); cave_me.vertices.foreach_get("normal", nz); nz = nz.reshape(-1, 3)[:, 2]
    depth = np.full(nv, 0.3)
    for b_, carve, big in AIR:                                                         # 장면 방의 파는 깊이 (⑨ 0.6 · ⑥ ① 0.25 …) — 그 공기 상자 안의 점에
        if abs(carve - 0.3) < 1e-6: continue
        vs = np.array([v.co[:] for v in b_.verts]); lo, hi = vs.min(0) - 0.5, vs.max(0) + 0.5
        depth[np.all((co >= lo) & (co <= hi), axis=1)] = carve
    w = np.round(np.where(nz > 0.6, 0.1, 1.0) * depth / 0.6, 2)
    vg = cave.vertex_groups.new(name="carve")
    for v in np.unique(w): vg.add(np.nonzero(w == v)[0].tolist(), float(v), "REPLACE")
    tex = bpy.data.textures.new("rocknoise", type="CLOUDS"); tex.noise_scale = 1.6; tex.noise_depth = 3
    dm = cave.modifiers.new("carve", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"; dm.strength = 0.6; dm.mid_level = 1.0; dm.direction = "NORMAL"; dm.vertex_group = "carve"
    for b_, carve, big in AIR:                                                         # 그것의 굴(⑨): 벽 · 천장만 크게 굴곡
        if not big: continue
        T, (hx, hy), bm_ = big; c0 = T @ Vector((0, 0, 0)); ex = T.to_3x3() @ Vector((hx, hy, 0))
        sel = (np.abs(co[:, 0] - c0.x) < abs(ex.x)) & (np.abs(co[:, 1] - c0.y) < abs(ex.y)) & (nz <= 0.6) & (co[:, 2] > c0.z + 0.4)
        vg2 = cave.vertex_groups.new(name="big"); vg2.add(np.nonzero(sel)[0].tolist(), 1.0, "REPLACE")
        tex2 = bpy.data.textures.new("bignoise", type="CLOUDS"); tex2.noise_scale = 5.0; tex2.noise_depth = 2
        dm2 = cave.modifiers.new("carve_big", "DISPLACE"); dm2.texture = tex2; dm2.texture_coords = "GLOBAL"; dm2.strength = bm_; dm2.mid_level = 1.0; dm2.direction = "NORMAL"; dm2.vertex_group = "big"
    me = bpy.data.meshes.new_from_object(cave.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(cave, do_unlink=True)
    me.materials.append(tint(tex_mat(os.path.join(FABDIR, "ueknfaclw"), 2.0), (0.55, 0.5, 0.45), "rock_fab")); me.materials.append(tex_mat(CG, 2.0))
    pn = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", pn)
    me.polygons.foreach_set("material_index", (pn.reshape(-1, 3)[:, 2] > 0.55).astype(np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    box_uv_fast(me, 0.35)
    o = bpy.data.objects.new("SHELL", me); sc.collection.objects.link(o); return o

def split_tiles(o, size=24.0):
    """큰 바위 굴을 24 m 칸으로 나눈다 — 게임이 안 보이는 칸은 안 그린다 (한 덩어리면 늘 전부 그린다)"""
    me = o.data; P_ = len(me.polygons)
    ls = np.empty(P_, np.int32); me.polygons.foreach_get("loop_start", ls); lt = np.empty(P_, np.int32); me.polygons.foreach_get("loop_total", lt)
    vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    uv = np.empty(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    mi = np.empty(P_, np.int32); me.polygons.foreach_get("material_index", mi)
    cen = np.empty(P_ * 3); me.polygons.foreach_get("center", cen); cen = cen.reshape(-1, 3)
    key = np.floor(cen[:, 0] / size).astype(np.int64) * 100000 + np.floor(cen[:, 1] / size).astype(np.int64)
    out = []
    for kv in np.unique(key):
        F = np.nonzero(key == kv)[0]; L = (ls[F][:, None] + np.arange(lt.max())[None, :])[np.arange(lt.max())[None, :] < lt[F][:, None]]
        used, remap = np.unique(vi[L], return_inverse=True)
        m2 = bpy.data.meshes.new("SHELL_T"); m2.vertices.add(len(used)); m2.vertices.foreach_set("co", co[used].ravel())
        m2.loops.add(len(L)); m2.loops.foreach_set("vertex_index", remap.astype(np.int32))
        m2.polygons.add(len(F)); m2.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(lt[F])[:-1]]).astype(np.int32)); m2.polygons.foreach_set("loop_total", lt[F])
        m2.update(); m2.uv_layers.new(); m2.uv_layers.active.data.foreach_set("uv", uv[L].ravel())
        m2.polygons.foreach_set("material_index", mi[F]); m2.polygons.foreach_set("use_smooth", np.ones(len(F), dtype=bool))
        for mt in me.materials: m2.materials.append(mt)
        t = bpy.data.objects.new("SHELL_%d" % len(out), m2); sc.collection.objects.link(t); out.append(t)
    bpy.data.objects.remove(o, do_unlink=True); return out

MAP_PLAN = os.path.join(HERE, "map4_plan.json")                      # 1편 구조 (구조 설계 워크플로 추천안, 사용자 10-01 선택) — 방 · 굴 · 판자 문 칸 좌표
L3 = 3 * 3.52 + 2 * 4.54; L7S, L7W = 2 * 3.52 + 2 * 4.54, 3.05 + 2.81 + 3.05   # 장면 ③ · ⑦ 길이 (Fab 목록에서 잰 조각 길이)
PORT = {"z6": {"W": (-8, 1, 0), "E": (8, -1, 0), "S": (0, -20, 0)}, "z3": {"a": (0, 0, 0), "b": (L3, 0, 0)},
        "z7": {"a": (0, 0, 0), "b": (L7S + L7W, 0, 0)}, "z8": {"a": (0, 0, 0), "b": (19.92, 0, 0)},
        "z1": {"a": (-22, 0, 0), "b": (20, 0, 0)}, "z2": {"a": (0, 0, 0), "back": (15, 3, 0)},
        "z9": {"in": (-32.5, 4, 3), "out": (32.5, -8, 0), "crawl": (18, -12, 0)}}                  # 장면 출입구 (장면 좌표)
ROOM_H = {"M": 5.0, "K": 5.5, "S1": 4.4, "W1": 4.4, "P": 4.2, "L": 4.2, "H": 4.2, "R2": 4.2, "E1": 4.0, "N1": 4.2, "N2": 3.2, "V": 3.4, "LD": 3.6, "LW": 3.2, "MAG": 2.6}
SCENE_NAME = {"z6": "⑥ 승강장", "z3": "③ 광차 싣는 곳", "z7": "⑦ 바람문", "z8": "⑧ 무너진 기둥", "z1": "① 쇠동발 숲", "z2": "② 채탄 막장", "z9": "⑨ 그것의 굴"}

def map4():
    global ZT, PASS, SHELL, M_OLD_, M_TAR_, M_IRONDOOR_, M_SIGNBOARD_, M_SIGNTEXT_
    plan = json.load(open(MAP_PLAN, encoding="utf-8"))
    global M_RUST, M_TIMB
    # 사용자 10-01 질감 결정(비교 그림 번호): 나무 4 검게 칠한 판자 · 7 껍질 벗긴 거친 나무 / 쇠 5 이어 붙인 철판 · 8 칠 벗겨지고 녹슨 쇠(물 가까운 곳 · 깊은 층일수록) / 천 · 자루 4
    # 나눔(Claude): 갱목 · 동발 · 판자 = 거친 나무(밝기 0.38 이라 어둡게 물들임) · 문틀 · 디딤판 · 받침 · 기둥(타르 칠) = 검은 판자. 쇠는 물 고인 방(P · R1)만 녹슨 것, 나머지 철판 — 더 깊은 층은 METAL["wet"] 를 넓힌다
    old_rust, old_timb = tint(M_RUST, (0.42, 0.36, 0.32), "rust_dark"), tint(M_TIMB, (0.62, 0.56, 0.5), "timber_map")   # 사진이 없을 때 (머리등에 하얗게 번쩍이던 것, 검수 10-01)
    METAL["new"] = cc0_mat("metal/metal_plate_02", 2.0, "metal_plate"); METAL["old"] = cc0_mat("metal/rusty_metal_04", 2.0, "metal_rusty")   # 금속 지도는 안 쓴다 — 튀는 빛 · 비침이 없는 굴에서 금속 면은 새까맣게만 보였다(권양기 · 배전반). 녹 · 칠은 원래 금속 면이 아니다
    M_RUST = METAL["new"] or old_rust; M_RUST_W = METAL["old"] or old_rust
    M_TIMB = cc0_mat("wood/rough_wood", 0.5, "timber_map", (0.36, 0.31, 0.27)) or old_timb
    M_OLD_ = tint(M_TIMB, (0.7, 0.68, 0.66), "timber_rotten"); M_TAR_ = cc0_mat("wood/black_painted_planks", 1.6, "frame_tar", (0.95, 0.85, 0.72)) or tint(old_timb, (0.72, 0.71, 0.76), "frame_tar")
    M_IRONDOOR_ = paint("irondoor", (0.13, 0.12, 0.11), 0.5, 0.8)
    M_WATER = paint("water", (0.01, 0.012, 0.012), 0.03); M_MACH = paint("machine", (0.07, 0.1, 0.085), 0.6, 0.6); M_RED = paint("redbox", (0.3, 0.05, 0.03), 0.7)
    M_WHITE = paint("white", (0.5, 0.49, 0.45), 0.8); M_CLOTH = cc0_mat("misc/decrepit_wallpaper", 2.5, "tarp", (0.34, 0.31, 0.27)) or paint("tarp", (0.08, 0.07, 0.05), 0.95); M_METAL = paint("metal", (0.09, 0.09, 0.1), 0.55, 0.8)
    M_PAPER = paint("paper", (0.45, 0.42, 0.33), 0.9); M_LADDER = paint("ladderpaint", (0.3, 0.22, 0.05), 0.75, 0.4)
    M_FENCE = tint(M_TIMB, (0.8, 0.75, 0.68), "fence")
    METAL["wet"] = True; M_MACH_W, M_METAL_W = paint("machine_wet", (0.07, 0.1, 0.085), 0.6, 0.6), paint("metal_wet", (0.09, 0.09, 0.1), 0.55, 0.8); METAL["wet"] = False   # 물 가까운 방의 기계
    lib("ufekaeedw", key="rail", rails=True)                                                   # 레일 조각 (레일이 X 로 눕게)
    for fid in ("ueujednfa", "ufmodhpfa", "ujzhahdfa"): lib(fid, along=True)                   # 광차 (긴 쪽을 X 로)
    for key, col in (("coal", (0.09, 0.09, 0.1)), ("stone", (0.55, 0.55, 0.58))):               # 스캔 돌 = 석탄 덩이 · 바위 돌 (같은 모델, 다른 색)
        m = tint(tex_mat(os.path.join(FABDIR, "wd3efb0"), 1 / 0.35), col, key + "_lump"); b_ = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for l in list(b_.inputs["Roughness"].links): m.node_tree.links.remove(l)
        b_.inputs["Roughness"].default_value = 0.8; b_.inputs["Specular IOR Level"].default_value = 0.1; lib("wd3efb0", key=key, mat=m)   # 석탄이 은색 쇠처럼 번쩍였다 (검수)
    R = lambda yaw: Matrix.Rotation(math.radians(yaw), 4, "Z")
    FN = {"z6": scene6, "z3": scene3, "z7": scene7, "z8": scene8, "z1": scene1, "z2": scene2, "z9": scene9}
    AIRZ = {"z3": [((L3 / 2, 0, 2.05), (L3 + 1, KIND["haul"][0], KIND["haul"][1]))],
            "z7": [((L7S / 2, 0, 2.05), (L7S + 1, KIND["haul"][0], KIND["haul"][1])), ((L7S + L7W / 2, 0, 1.4), (L7W + 1, KIND["side"][0], KIND["side"][1]))]}
    Z = []
    for i, s in enumerate(plan["scenes"]):
        z = dict(n=s["scene"], f=FN[s["scene"]], T=Matrix.Translation((s["x"], s["y"], s["z"])) @ R(s["yaw"]), seed=1000 + i)
        if s["scene"] in AIRZ: z["air"] = AIRZ[s["scene"]]
        Z.append(z)
    zi = {z["n"]: z for z in Z}
    N = {n["id"]: n for n in plan["nodes"]}
    rooms = [n for n in plan["nodes"] if n["kind"] in ("junction", "room", "ladder")]
    for n in rooms: n["h"] = ROOM_H.get(n["id"], min(5.0, 3.0 + min(n["w"], n["d"]) / 10))
    def P(k):
        if k in N: return Vector((N[k]["x"], N[k]["y"], N[k]["z"]))
        s, p = k.split("."); return zi[s]["T"] @ Vector(PORT[s][p])
    def exit_t(k, d):                                                                         # 방 가운데에서 d 쪽으로 방 벽까지 (조각을 방 안으로 안 들인다)
        if k not in N or N[k]["kind"] == "closet": return 0.0
        n = N[k]; return min(n["w"] / 2 / abs(d.x) if abs(d.x) > 1e-6 else 1e9, n["d"] / 2 / abs(d.y) if abs(d.y) > 1e-6 else 1e9)
    # 굴 = 토막들 [(p, q, 종류, p 쪽 자르기, q 쪽 자르기)] — 꺾는 점(via)은 작은 바위 방
    SEG, BEND = [], []
    for e in plan["edges"]:
        if e["kind"] == "shaft": continue
        pa, pb = P(e["a"]), P(e["b"]); pts = [pa] + [Vector((v[0], v[1], 0)) for v in e["via"]] + [pb]
        L_all = sum((Vector((q.x - p.x, q.y - p.y, 0))).length for p, q in zip(pts, pts[1:])); acc = 0.0
        for k in range(1, len(pts) - 1):                                                      # 꺾는 점 높이 = 길이 비율로
            acc += Vector((pts[k].x - pts[k - 1].x, pts[k].y - pts[k - 1].y, 0)).length; pts[k].z = pa.z + (pb.z - pa.z) * acc / max(L_all, 1e-6); BEND.append((pts[k], e["kind"]))
        for k, (p, q) in enumerate(zip(pts, pts[1:])):
            d = Vector((q.x - p.x, q.y - p.y, 0))
            if d.length < 0.3: continue
            d.normalize(); w = KIND[e["kind"]][0]
            ta = exit_t(e["a"], d) + (0.6 if e["a"] in N else 0.0) if k == 0 else w / 2 + 0.6; tb = exit_t(e["b"], -d) + (0.6 if e["b"] in N else 0.0) if k == len(pts) - 2 else w / 2 + 0.6
            SEG.append(dict(p=p, q=q, kind=e["kind"], ta=ta, tb=tb, edge=e))
    # ---- 1단계: 바위 공기 모으기
    PASS = "air"
    for z in Z:
        ZT = z["T"]; random.seed(z["seed"]); before = set(bpy.data.objects)
        for c, sz in z.get("air", []): b = bmesh.new(); box(b, c, sz); b.transform(ZT); AIR.append((b, 0.3, None))
        if "air" not in z:
            try: z["f"]()
            except ZoneAir: pass
        for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    def tube(p, q, kind):
        w, h = KIND[kind]; F, L = frame(p, q); slope = abs(q.z - p.z) > 0.05; n = max(1, int(L / 1.2)) if slope else 1
        for i in range(n):                                                                    # 비탈이면 짧은 상자를 계단처럼 (복셀이 매끈한 비탈로 잇는다 — 턱 없음)
            za = p.z + (q.z - p.z) * (i + 0.5) / n
            bm_ = bmesh.new(); box(bm_, ((i + 0.5) * L / n, 0, za + h / 2), (L / n + (0.8 if slope else 0.0), w, h)); bm_.transform(F); AIR.append((bm_, 0.3, None))
    for s in SEG: tube(s["p"], s["q"], s["kind"])
    for v, k in BEND: b = bmesh.new(); w, h = KIND[k]; box(b, (v.x, v.y, v.z + h / 2), (w + 1.2, w + 1.2, h)); AIR.append((b, 0.3, None))
    for n in rooms:
        b = bmesh.new(); box(b, (n["x"], n["y"], n["z"] + n["h"] / 2), (n["w"], n["d"], n["h"])); rr = random.Random(n["id"])
        hx, hy, h = n["w"] / 2, n["d"] / 2, n["h"]
        for cx_, cy_ in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):                          # 네 모서리를 둥글게
            blob(b, (n["x"] + cx_ * 0.8, n["y"] + cy_ * 0.8, n["z"] + h * 0.45), (min(hx, 2.2), min(hy, 2.2), h * 0.5), 2)
        for _ in range(int((n["w"] + n["d"]) / 4)):                                             # 벽을 따라 불룩한 곳 (파낸 자국)
            if rr.random() < 0.5: px, py = n["x"] + rr.uniform(-hx, hx), n["y"] + rr.choice((-hy, hy))
            else: px, py = n["x"] + rr.choice((-hx, hx)), n["y"] + rr.uniform(-hy, hy)
            blob(b, (px, py, n["z"] + rr.uniform(0.9, h * 0.8)), (rr.uniform(0.8, 1.8), rr.uniform(0.8, 1.8), rr.uniform(0.8, 1.5)), 2)
        for _ in range(max(1, int(n["w"] * n["d"] / 60))):                                      # 천장도 들쭉날쭉 (올리기만)
            blob(b, (n["x"] + rr.uniform(-hx, hx) * 0.7, n["y"] + rr.uniform(-hy, hy) * 0.7, n["z"] + h - 0.2), (rr.uniform(1.5, 3.0), rr.uniform(1.5, 3.0), rr.uniform(0.5, 1.0)), 2)
        AIR.append((b, 0.45, None))
    # 판자 문 칸: 방 안이면 가까운 방 벽, 굴이면 굴 옆벽 (Fab 굴이면 조각 판자가 문을 가려서 가까운 방 벽으로 옮긴다)
    def near_wall(p):
        best = None
        for r in rooms:
            dx, dy = p.x - r["x"], p.y - r["y"]
            if abs(dx) <= r["w"] / 2 + 1.0 and abs(dy) <= r["d"] / 2 + 1.0:
                for dist, f in ((r["w"] / 2 - dx, Vector((1, 0, 0))), (r["w"] / 2 + dx, Vector((-1, 0, 0))), (r["d"] / 2 - dy, Vector((0, 1, 0))), (r["d"] / 2 + dy, Vector((0, -1, 0)))):
                    if best is None or abs(dist) < best[0]: best = (abs(dist), Vector((p.x, p.y, r["z"])) + f * dist, f)
        return best
    ALC = []
    for c in [n for n in plan["nodes"] if n["kind"] == "closet"]:
        p = Vector((c["x"], c["y"], c["z"])); hit = near_wall(p)
        if hit is None:
            s = min(SEG, key=lambda s: ((p - s["p"]) - (p - s["p"]).project(s["q"] - s["p"])).length if 0 <= (p - s["p"]).dot(s["q"] - s["p"]) <= (s["q"] - s["p"]).length_squared else 1e9)
            if s["kind"] in FAB_RUN:
                r = min(rooms, key=lambda r: (Vector((r["x"], r["y"], 0)) - Vector((p.x, p.y, 0))).length); hit = near_wall(Vector((r["x"] + (p.x - r["x"]) * 0.2, r["y"] + (p.y - r["y"]) * 0.2, r["z"])))
                hit = near_wall(hit[1] - hit[2] * 0.01)
            else:
                d = (s["q"] - s["p"]); d.z = 0; d.normalize(); nrm = Vector((-d.y, d.x, 0)); off = (p - s["p"]).dot(nrm)
                if off < 0: nrm = -nrm
                t = (p - s["p"]).dot(d) / max((s["q"] - s["p"]).length, 1e-6); base = s["p"].lerp(s["q"], max(0, min(1, t)))
                hit = (0, Vector((base.x, base.y, base.z)) + nrm * (KIND[s["kind"]][0] / 2), nrm)
        _, wall, f = hit
        b = bmesh.new(); box(b, (0, 0, 0), (1.6, 1.15, 2.35)); b.transform(Matrix.Translation(wall + f * 0.5 + Vector((0, 0, 1.175))) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z"))
        AIR.append((b, 0.05, None)); ALC.append((c["id"], wall - f * 0.05, f, c["id"] == "MAG"))
    def side_recess(r, f, depth, width, h, carve=0.1):                                        # 방 벽에서 f 쪽으로 파낸 곳 (막장 · 울타리 너머)
        wall = Vector((r["x"], r["y"], r["z"])) + f * (abs(f.x) * r["w"] / 2 + abs(f.y) * r["d"] / 2)
        b = bmesh.new(); box(b, (0, 0, 0), (depth + 0.4, width, h)); b.transform(Matrix.Translation(wall + f * (depth / 2 - 0.2) + Vector((0, 0, h / 2))) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z"))
        AIR.append((b, carve, None)); return wall
    n2 = N["N2"]; FACES = []
    for dx in (-8, 0, 8):                                                                      # 북쪽 막장 줄: 벽에 깊이 5 m 막장 셋 (협동 때 나눠 캔다)
        r_ = dict(n2); r_["x"] = n2["x"] + dx; FACES.append((side_recess(r_, Vector((0, 1, 0)), 5.0, 3.4, 2.4, 0.3), dx))
    FENCES = []
    for rid, gid in (("M", "GOAF_W"), ("E2", "GOAF_E")):                                       # 막아 둔 채굴적: 방 벽에서 2 m 파고 판자 울타리 (틈으로 어둠이 보인다, 못 들어감)
        r_, g = N[rid], N[gid]; d = Vector((g["x"] - r_["x"], g["y"] - r_["y"], 0)); f = Vector((1 if d.x > 0 else -1, 0, 0)) if abs(d.x) > abs(d.y) else Vector((0, 1 if d.y > 0 else -1, 0))
        FENCES.append((side_recess(r_, f, 4.0, 3.6, 3.0, 0.4), f, r_["z"]))
    lw, n2 = N["LW"], N["N2"]                                                                  # 서쪽 모임터 → 북쪽 막장 줄 6 m 세로 구멍 (사다리 오르기는 아직 없다 — 위에서 뛰어내리는 지름길)
    b = bmesh.new(); box(b, (lw["x"], lw["y"], (lw["z"] + n2["z"] + 3.0) / 2), (2.4, 2.4, n2["z"] - lw["z"] + 3.0)); AIR.append((b, 0.1, None))
    b = bmesh.new(); tp = Vector((lw["x"], lw["y"], n2["z"])); F_, L_ = frame(tp, Vector((n2["x"], n2["y"], 0)), n2["z"]); box(b, (L_ / 2, 0, 1.4), (L_, 2.6, 2.8)); b.transform(F_); AIR.append((b, 0.2, None))
    ld = N["LD"]; b = bmesh.new(); box(b, (ld["x"], ld["y"], ld["z"] - 6.0), (3.0, 3.0, 12.0)); AIR.append((b, 0.2, None))   # 2편으로 내려가는 사다리 구멍 (2편은 아직 없다)
    SHELL = unified_shell()
    T2 = zi["z2"]["T"]; c1, c2 = T2 @ Vector((-0.5, -3.5, -1)), T2 @ Vector((21.5, 3.5, 3))
    cen = np.empty(len(SHELL.data.polygons) * 3); SHELL.data.polygons.foreach_get("center", cen); cen = cen.reshape(-1, 3)
    coal_room_mats(SHELL.data, np.all((cen >= np.minimum(c1, c2)) & (cen <= np.maximum(c1, c2)), axis=1))   # 채탄 막장(②) 자리는 석탄 벽 · 셰일 천장
    # ---- 2단계: 장면 방 소품 (바위 굴을 그 방의 좌표로 잠깐 옮겨 광선 재기가 맞게, 먼저 지은 방은 숨김)
    PASS = "dress"; zone_objs = {}
    for z in Z:
        ZT = z["T"]; random.seed(z["seed"]); SHELL.matrix_world = ZT.inverted(); before = set(bpy.data.objects)
        for objs in zone_objs.values():
            for o in objs: o.hide_viewport = True
        bpy.context.view_layer.update(); S_ = z["f"]()
        bpy.context.view_layer.update()                                                 # 새 물체의 matrix_world 를 갱신한 뒤 옮긴다 (안 하면 글씨가 방 원점 바닥에 눕는다)
        for nm in S_.get("shot_only", {}):                                                 # 그림 한 장에만 보이던 것: 연 문은 두고, 괴물 눈 · 무너진 뒤 돌 · 닫힌 뒷문은 뺀다
            if "OPEN" not in nm and nm in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.parent is None: o.matrix_world = ZT @ o.matrix_world
        zone_objs[z["n"]] = new
        for l in S_["lights"]: LIGHTS.append(("L%d" % len(LIGHTS), tuple(ZT @ Vector(l[1])), *l[2:]))
        for nm, eye, at in S_["shots"][:2]: SHOTS.append(("%s_%s" % (z["n"], nm), tuple(ZT @ Vector(eye)), tuple(ZT @ Vector(at))))
    SHELL.matrix_world = Matrix.Identity(4)
    for objs in zone_objs.values():
        for o in objs: o.hide_viewport = False
    random.seed(77); bpy.context.view_layer.update()
    # ---- 3단계: 굴 소품 (평평한 토막만 — 비탈은 맨바위)
    for s in SEG:
        p, q = s["p"], s["q"]; d = Vector((q.x - p.x, q.y - p.y, 0)); L = d.length; d.normalize()
        if abs(q.z - p.z) > 0.05 or L - s["ta"] - s["tb"] < 1.0: continue
        a, b = (p + d * s["ta"]).to_2d(), (q - d * s["tb"]).to_2d(); z = p.z; k = s["kind"]
        if k in FAB_RUN and L - s["ta"] - s["tb"] >= 3.0: run(k, a, b, z)                  # 3 m 보다 짧으면 조각이 눌려 보인다 — 맨바위로
        if k == "haul": rails(a, b, z)
        if k in ("old", "low"): old_sets(a, b, z)
        if k == "prop": steel_props(a, b, z)
        dress_tunnel(a, b, k, z)
    bpy.context.view_layer.update()
    for s in SEG:                                                                             # 운반갱도 전등 (조각을 다 놓은 뒤 천장을 잰다)
        p, q = s["p"], s["q"]; d = Vector((q.x - p.x, q.y - p.y, 0)); L = d.length; d.normalize()
        if s["kind"] == "haul" and abs(q.z - p.z) <= 0.05 and L - s["ta"] - s["tb"] > 8: ceiling_lamps((p + d * s["ta"]).to_2d(), (q - d * s["tb"]).to_2d(), p.z)
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); bmr = bmesh.new()
    for s in SEG:
        p, q = s["p"], s["q"]
        if abs(q.z - p.z) < 0.5: continue
        d = (q - p); d.z = 0; L = d.length; d.normalize(); nrm = Vector((-d.y, d.x, 0)); t = 1.0
        while t < L - 1.0:
            c = p.lerp(q, t / L); hit, f_, *_ = sc.ray_cast(deps, c + Vector((0, 0, 1.5)), Vector((0, 0, -1)), distance=4.0)
            if hit: box(bm, f_ + Vector((0, 0, 0.04)), (0.28, 1.6, 0.07), Matrix.Rotation(math.atan2(d.y, d.x), 3, "Z"))   # 발 디딤 판
            if hit and int(t / 0.45) % 4 == 0: box(bmr, f_ + nrm * 1.0 + Vector((0, 0, 0.5)), (0.08, 0.08, 1.0))            # 난간 기둥
            t += 0.45
    if bm.verts: box_uv(obj("STEPS", bm, M_TAR_).data, 0.8)
    if bmr.verts: box_uv(obj("STEPRAIL", bmr, M_TAR_).data, 0.8)
    # ---- 방마다 알아볼 소품 (설계의 "여기 있는 것")
    def W(n, dx, dy, dz=0.0): return Vector((n["x"] + dx, n["y"] + dy, n["z"] + dz))
    def M_(n, dx, dy, yaw=0.0, dz=0.0): return Matrix.Translation(W(n, dx, dy, dz)) @ R(yaw)
    def boxes(name, mat, items):
        bm = bmesh.new()
        for c, s_, *rot in items: box(bm, c, s_, rot[0] if rot else None)
        o = obj(name, bm, mat); box_uv(o.data, 0.8); return o
    def cyl(name, mat, c, r, L, axis="Z", seg=20):
        bm = bmesh.new(); g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=L)
        rot = {"Z": Matrix.Identity(3), "X": Matrix.Rotation(math.radians(90), 3, "Y"), "Y": Matrix.Rotation(math.radians(90), 3, "X")}[axis]
        for v in g["verts"]: v.co = rot @ v.co + Vector(c)
        o = obj(name, bm, mat); o.data.polygons.foreach_set("use_smooth", np.ones(len(o.data.polygons), dtype=bool)); return o
    def cart(n, dx, dy, yaw=0.0, fid="ueujednfa", tarp=False):
        put(fid, M_(n, dx, dy, yaw, 0.12))                                                     # 광차 긴 쪽 = yaw 쪽 (레일 위)
        if tarp:                                                                              # 거적 (광차 + 거적 숨기, 카드 3)
            F = M_(n, dx, dy, yaw); boxes("TARP", M_CLOTH, [(F @ Vector((0, 0, 1.12)), (2.2, 1.15, 0.04), F.to_3x3()), (F @ Vector((0, 0.6, 0.7)), (2.2, 0.03, 0.8), F.to_3x3()), (F @ Vector((0, -0.6, 0.7)), (2.2, 0.03, 0.8), F.to_3x3())])
    def logs(n, dx, dy, yaw=0.0, count=6):                                                     # 통나무 더미 (Fab 나무 기둥을 눕혀 쌓는다)
        for i in range(count):
            row, col = divmod(i, 3); put("tgmrafyfa", M_(n, dx, dy, yaw) @ Matrix.Translation((-1.2, (col - 1) * 0.26 + (row % 2) * 0.13, 0.12 + row * 0.22)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    def pile(n, dx, dy, key, rx, ry, h, cnt, s0, s1):
        for (x, y, zz, yaw, s_) in rock_pile(n["x"] + dx, n["y"] + dy, rx, ry, h, cnt, s0, s1, clamp=None): put(key, Matrix.Translation((x, y, n["z"] + zz)) @ R(yaw) @ Matrix.Diagonal((s_, s_, s_, 1)))
    def bench(n, dx, dy, yaw=0.0, L=3.0):
        F = M_(n, dx, dy, yaw); boxes("BENCH", M_TIMB, [(F @ Vector((0, 0, 0.45)), (L, 0.4, 0.06), F.to_3x3())] + [(F @ Vector((s_ * (L / 2 - 0.3), 0, 0.22)), (0.12, 0.35, 0.44), F.to_3x3()) for s_ in (-1, 1)])
    def rail_line(n, x0, y0, x1, y1): rails((n["x"] + x0, n["y"] + y0), (n["x"] + x1, n["y"] + y1), n["z"])
    for n in rooms:
        i = n["id"]; w, dd = n["w"], n["d"]; METAL["wet"] = i in ("P", "R1")
        if i == "P":                                                                          # 펌프실: 물웅덩이(가장 낮은 곳) + 배수 펌프 + 관
            boxes("NOCOL_SUMP", M_WATER, [(W(n, -1, 0, 0.03), (5, 5, 0.02))])
            boxes("PUMP", M_MACH_W, [(W(n, 3.5, 3.5, 0.5), (1.4, 0.9, 1.0)), (W(n, 3.5, 3.5, 0.04), (1.8, 1.3, 0.08))]); cyl("PUMPMOTOR", M_METAL_W, W(n, 3.5, 2.7, 0.6), 0.3, 0.8, "Y")
            cyl("PIPE_SUMP", M_RUST_W, W(n, 1.0, 3.5, 0.35), 0.09, 5.0, "X")                     # 웅덩이에서 펌프로 가는 관
            cyl("PIPE_UP", paint("pipe2", (0.5, 0.07, 0.04), 0.55, 0.4), W(n, 3.5, 4.3, 2.0), 0.1, 4.0, "Z")
        elif i == "R0":                                                                       # 대기소 겸 신호소: 긴 의자 줄 · 게시판 · 전화
            for k in range(3): bench(n, -6 + k * 5, dd / 2 - 1.0)
            boxes("BOARD", M_TAR_, [(W(n, 0, -dd / 2 + 0.3, 1.5), (2.4, 0.05, 1.2))]); boxes("PAPERS", M_PAPER, [(W(n, -0.8 + k * 0.55, -dd / 2 + 0.34, 1.55 + (k % 2) * 0.15), (0.35, 0.02, 0.45)) for k in range(4)])
            boxes("PHONE", M_RED, [(W(n, 3, -dd / 2 + 0.3, 1.4), (0.3, 0.15, 0.4))])
        elif i == "L":                                                                        # 램프실: 선반 + 안전모 줄
            boxes("SHELF", M_TIMB, [(W(n, 0, dd / 2 - 0.4, z_), (w - 2, 0.5, 0.05)) for z_ in (0.8, 1.4)] + [(W(n, x_, dd / 2 - 0.4, 0.75), (0.08, 0.5, 1.5)) for x_ in (-(w - 2) / 2, 0, (w - 2) / 2)])
            for k in range(8): put("udklcbuiw", M_(n, -3.5 + k, dd / 2 - 0.4, random.uniform(0, 360), 0.83 + (k % 2) * 0.6))
        elif i == "W1":                                                                       # 서쪽 모임터: 레일 두 줄 + 석탄 실은 광차 여섯 (한 대에 거적) + 연장 상자
            for y_ in (-1.8, 1.8): rail_line(n, -w / 2 + 0.5, y_, w / 2 - 0.5, y_)
            for k, (x_, y_) in enumerate([(-8, -1.8), (-5.5, -1.8), (-3, -1.8), (4, 1.8), (6.5, 1.8), (9, 1.8)]): cart(n, x_, y_, 0, tarp=(k == 4))
            boxes("TOOLBOX", M_RED, [(W(n, -10, dd / 2 - 1.0, 0.35), (1.2, 0.6, 0.7))])
        elif i == "W2":                                                                       # 갱목 쌓는 곳: 통나무 더미 셋 + 톱질 받침
            for dx_, dy_ in ((-4, 2.5), (0, 2.5), (4, -2.5)): logs(n, dx_, dy_, 0, 15)
            boxes("SAWHORSE", M_TIMB, [(W(n, 3, 1, 0.7), (1.6, 0.12, 0.12))] + [(W(n, 3 + s_ * 0.6, 1, 0.35), (0.1, 0.6, 0.7)) for s_ in (-1, 1)])
        elif i == "F":                                                                        # 막장 앞 방: 물통 · 석탄 자루 · 공기 호스 감개
            cyl("BARREL", M_METAL, W(n, 2.5, 2.5, 0.45), 0.3, 0.9); boxes("SACKS", M_CLOTH, [(W(n, -2.5 + k * 0.7, -2.8, 0.25), (0.6, 0.45, 0.5)) for k in range(4)])
        elif i == "M":                                                                        # 옛 채굴 빈터: 무너진 돌 언덕 둘 + 모양 다른 석탄 기둥 둘 (돌며 눈을 끊는다)
            pile(n, -7, 4, "stone", 4.0, 3.0, 2.2, 90, 3, 9); pile(n, 6, -5, "stone", 3.5, 2.5, 1.8, 70, 3, 8)
            bm = bmesh.new(); column(bm, n["x"] + 7, n["y"] + 5, 1.6, n["z"] - 0.5, n["z"] + 6); column(bm, n["x"] - 6, n["y"] - 6, 1.3, n["z"] - 0.5, n["z"] + 6)
            box_uv(obj("COALPILLAR", bm, bpy.data.materials.get("coal_wall") or M_ROCK).data, 0.5)
        elif i == "K":                                                                        # 붕락 방: 가운데 큰 돌 더미 + 쓰러진 동발 + 여럿이 같이 세울 새 동발 자리 (카드 14)
            pile(n, 0, 0, "stone", 5.0, 3.5, 3.6, 200, 3, 12)
            for k in range(4): put("tgmrafyfa", M_(n, -8 + k * 5, random.uniform(-6, 6), random.uniform(0, 180), 0.15) @ Matrix.Rotation(math.radians(90), 4, "Y"))
            for x_ in (8, 10): put("tgmsdc0fa", M_(n, x_, 5.5, random.uniform(0, 360)) @ Matrix.Diagonal((1, 1, (n["h"] - 0.3) / 2.5, 1)))
        elif i == "K2":                                                                       # 갱목 창고: 통나무 더미 둘 + 판자
            logs(n, -3, 2, 0, 15); logs(n, 3, -2, 90, 12); logs(n, 0, 3.5, 0, 15)
            for k in range(3): put("uebpbetfa", M_(n, 4, 2.5 - k * 0.3, 5 * k, 0.02 + 0.1 * k))
        elif i == "MAG":                                                                      # 화약고: 붉은 상자 (쇠문은 판자 문 칸 자리에)
            boxes("EXPLOSIVE", M_RED, [(W(n, x_, 0.8, 0.25 + 0.4 * (k // 2)), (0.7, 0.45, 0.4)) for k, x_ in enumerate((-0.6, 0.4, -0.2, 0.6))])
        elif i == "S1":                                                                       # 남쪽 광차 조차장: 레일 세 줄 + 빈 광차 두 줄 (한 대에 거적) + 신호 전화
            for x_ in (-4, 0, 4): rail_line(n, x_, -dd / 2 + 0.5, x_, dd / 2 - 0.5)
            for k in range(4): cart(n, -4, -9 + k * 2.4, 90, "ufmodhpfa"); cart(n, 4, 3 + k * 2.4, 90, "ufmodhpfa", tarp=(k == 2))
            boxes("PHONE", M_RED, [(W(n, w / 2 - 0.3, 0, 1.4), (0.15, 0.3, 0.4))])
        elif i == "H":                                                                        # 갱내 대피소: 구급함 · 물통 · 긴 의자
            boxes("FIRSTAID", M_WHITE, [(W(n, -w / 2 + 0.3, 0, 1.4), (0.08, 0.7, 0.5))]); text("+", tuple(W(n, -w / 2 + 0.36, 0, 1.3)), 0.4, M_RED, (math.radians(90), 0, math.radians(-90)))
            cyl("BARREL", M_RUST, W(n, 3, 3, 0.45), 0.3, 0.9); cyl("BARREL", M_RUST, W(n, 3.7, 3, 0.45), 0.3, 0.9); bench(n, 0, -dd / 2 + 1.0)
        elif i == "R2":                                                                       # 선로 끝 방: 레일 멈춤 받침 + 거적 덮인 광차
            rail_line(n, -w / 2 + 0.5, 0, w / 2 - 1.5, 0); boxes("BUFFER", M_TAR_, [(W(n, w / 2 - 1.2, 0, 0.4), (0.5, 1.4, 0.8))]); cart(n, 1, 0, 0, tarp=True)
            pile(n, w / 2 - 0.6, 0, "stone", 0.8, 1.2, 0.8, 25, 2, 6)                              # 선로 끝 흙 · 돌 둔덕
        elif i == "R1":                                                                       # 물 고인 옛 펌프장: 발목 물 + 멈춘 펌프
            boxes("NOCOL_WATER", M_WATER, [(W(n, 0, 0, 0.18), (w - 0.6, dd - 0.6, 0.02))]); boxes("OLDPUMP", M_RUST_W, [(W(n, 3, 3, 0.6), (1.6, 1.0, 1.2))])
        elif i == "E1":                                                                       # 선풍기 방: 큰 국부선풍기 + 찢어진 바람 관
            fy = dd / 2 - 1.6                                                                    # 선풍기: 짧은 원통 틀 + 날개 넷 + 받침 다리 (검수: 초록 캡슐이 공중에 떠 있었다)
            bm = bmesh.new()
            for side in (-1, 1):
                g = bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=0.95)
                for v in g["verts"]: v.co = Matrix.Rotation(math.radians(90), 3, "Y") @ v.co + W(n, side * 0.25, fy, 1.3)
            for a_ in range(0, 360, 30):
                g = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.03, radius2=0.03, depth=0.5)
                for v in g["verts"]: v.co = Matrix.Rotation(math.radians(90), 3, "Y") @ v.co + W(n, 0, fy + 0.95 * math.cos(math.radians(a_)), 1.3 + 0.95 * math.sin(math.radians(a_)))
            for s_ in (-1, 1): box(bm, W(n, 0, fy + s_ * 0.6, 0.45), (0.5, 0.1, 0.9))
            o = obj("FAN", bm, M_METAL); o.data.polygons.foreach_set("use_smooth", np.ones(len(o.data.polygons), dtype=bool))
            boxes("FANBLADE", M_MACH, [(W(n, 0, fy, 1.3), (0.05, 0.85, 0.22), Matrix.Rotation(math.radians(a_), 3, "X")) for a_ in (20, 65, 110, 155)])
            cyl("DUCT", M_CLOTH, W(n, -4.3, fy, 1.3), 0.55, 7.5, "X"); cyl("DUCTTORN", M_CLOTH, W(n, 4.0, fy - 0.3, 0.3), 0.5, 2.5, "X")
        elif i == "E2":                                                                       # 막아 둔 옛 채굴적 입구: 가스 눈금판 (울타리 · 붉은 등은 아래)
            boxes("GASBOARD", M_IRONDOOR_, [(W(n, 0, -dd / 2 + 0.3, 1.5), (1.2, 0.05, 0.8))]); boxes("GASDIAL", M_PAPER, [(W(n, x_, -dd / 2 + 0.33, 1.6), (0.25, 0.02, 0.25)) for x_ in (-0.3, 0.3)])
        elif i == "E4":                                                                       # 옛 권양기 방: 녹슨 감개 + 끊어진 쇠줄
            cyl("WINCH", M_RUST, W(n, 0, 0, 1.0), 0.8, 2.2, "Y"); cyl("WINCHROPE", paint("rope", (0.05, 0.045, 0.04), 0.9, 0.3), W(n, 0, 0, 1.0), 0.84, 1.6, "Y", 32)   # 감긴 쇠줄 (번쩍이는 은색 통으로 보였다)
            boxes("WINCHFRAME", M_TAR_, [(W(n, 0, s_ * 1.2, 0.7), (1.8, 0.2, 1.4)) for s_ in (-1, 1)] + [(W(n, 0, 0, 0.05), (2.2, 3.0, 0.1))])
            boxes("ROPE", M_METAL, [(W(n, 2.5, 0.3, 1.8), (5.0, 0.04, 0.04), Matrix.Rotation(math.radians(-20), 3, "Y"))])   # 끊어진 쇠줄
        elif i == "E3":                                                                       # 쓰러진 광차 굽이: 넘어진 광차 + 걸린 거적
            put("ueujednfa", M_(n, 0, 1.5, 30) @ Matrix.Translation((0, 0, 0.5)) @ Matrix.Rotation(math.radians(100), 4, "X")); pile(n, 1.5, -0.5, "coal", 1.5, 1.0, 0.5, 30, 2, 5)   # 쏟아진 석탄
        elif i == "V":                                                                        # 옛 창고 칸 줄: 판자 칸막이 여섯 칸 (마구간 흔적을 창고로)
            boxes("STALLS", M_FENCE, [(W(n, -w / 2 + 2 + k * 4, -dd / 2 + 1.5, 1.1), (0.08, 3.0, 2.2)) for k in range(7)] + [(W(n, 0, -dd / 2 + 3.0, 1.1), (w - 4, 0.06, 1.2))])
        elif i == "X":                                                                        # 옛 배전실: 배전반 + 케이블
            boxes("SWITCHBOARD", M_METAL, [(W(n, 0, dd / 2 - 0.3, 1.1), (3.0, 0.3, 2.0))]); boxes("CABLES", paint("cable", (0.02, 0.02, 0.02), 0.6), [(W(n, 0, dd / 2 - 0.2, 2.6), (w - 1, 0.1, 0.1))])
            boxes("DIALS", M_PAPER, [(W(n, -1.0 + k * 0.5, dd / 2 - 0.47, 1.6), (0.18, 0.02, 0.18)) for k in range(5)]); boxes("LEVERS", M_RED, [(W(n, -1.0 + k * 0.5, dd / 2 - 0.5, 1.0), (0.05, 0.12, 0.3)) for k in range(5)])
        elif i == "N1":                                                                       # 윗 탄층 저탄장: 석탄 더미 + 거적 덮인 광차
            pile(n, -3, 0, "coal", 5.0, 3.5, 2.0, 120, 2, 7); cart(n, 7, -3, 0, tarp=True)
        elif i == "N3":                                                                       # 단층 방: 벽의 석탄 띠가 계단처럼 2 m 어긋난다
            cw = bpy.data.materials.get("coal_wall") or M_ROCK
            boxes("COALBAND", cw, [(W(n, -w / 4, dd / 2 - 0.05, 1.0), (w / 2, 0.15, 0.7)), (W(n, w / 4, dd / 2 - 0.05, 3.0), (w / 2, 0.15, 0.7)), (W(n, 0, dd / 2 - 0.05, 2.0), (0.2, 0.16, 2.8), Matrix.Rotation(math.radians(20), 3, "Y"))])
        elif i == "N2":                                                                       # 북쪽 막장 줄: 막장 셋마다 석탄 덩이
            for wall, dx_ in FACES: pile(dict(x=wall.x, y=wall.y + 3.5, z=n["z"]), 0, 0, "coal", 1.2, 1.0, 0.6, 20, 2, 5)
    METAL["wet"] = False
    for wall, f, z0 in FENCES:                                                                # 막아 둔 채굴적 울타리 + 붉은 등 + 출입 금지 (1964 광산보안규칙 제156 · 158조)
        F = Matrix.Translation(wall + f * 1.5) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z")
        boxes("FENCE", M_FENCE, [(F @ Vector((0, -1.6 + k * 0.4, 1.2)), (0.05, 0.28, 2.4), F.to_3x3()) for k in range(9)] + [(F @ Vector((-0.06, 0, z_)), (0.05, 3.6, 0.12), F.to_3x3()) for z_ in (0.6, 1.8)])
        text("출입 금지", tuple(F @ Vector((-0.12, 0, 1.3))), 0.3, M_RED, (math.radians(90), 0, math.atan2(-f.x, f.y)))
        red = (wall - Vector((N["E2"]["x"], N["E2"]["y"], 0))).to_2d().length < 20
        lamp_at((wall - f * 0.3).x, (wall - f * 0.3).y, z0, 3.0, "ZL_ff1a0d_%d" if red else "ZL_ff7a1a_%d", 40, (1.0, 0.1, 0.05) if red else (1.0, 0.48, 0.1))
    for nm, c, f, iron in ALC: plank_door(c, f, nm, iron)
    # ---- 빛: 불 켜진 방(7 m 칸마다) · 구역 입구 색 등 (카드 15) · 장면 입구 색 등
    bpy.context.view_layer.update()
    for n in rooms:
        if n.get("lit"): lamp_grid(n, max(1, round(n["w"] / 7)), max(1, round(n["d"] / 7)), "L%d")
    # 안 켜진 방 = 작업등. 사용자 10-01 "전등을 1.5배로 — 넓은 곳은 머리등으로는 멀리 안 보인다" → 넓은 방부터 칸 수를 늘린다 (R1 · E3 · E2 · MAG 는 어둡게 둔다 — 괴물 굴 쪽)
    WORK = {"M": (4, 3), "K": (3, 2), "V": (3, 2), "W1": (4, 1), "N1": (2, 2), "N2": (3, 1), "E1": (2, 1), "K2": (2, 1)}   # 방 → (가로 칸, 세로 칸)
    for rid, (nx, ny) in WORK.items(): lamp_grid(N[rid], nx, ny, "ZL_ffb070_%d", energy=50, col=(1.0, 0.69, 0.44))
    for rid in ("W2", "F", "E4", "X", "N0", "N3", "R2", "LD"):                                    # 작은 방 = 하나 (가운데를 비켜서)
        n = N[rid]; lamp_at(n["x"] + n["w"] * 0.2, n["y"] + n["d"] * 0.15, n["z"], n["h"], "ZL_ffb070_%d", 50, (1.0, 0.69, 0.44))
    bm = bmesh.new()                                                                           # ⑨ 그것의 굴 (40 × 26, 천장 12~16 m): 바닥에 세운 작업등 넷 — 계단 밑 · 가운데 북쪽 · 기둥 사이 · 큰 틈 앞
    for p in ((-15, -5, 0), (-2, 7, 0), (9, 0, 0), (15, 2, 0)): pole_lamp(bm, zi["z9"]["T"] @ Vector(p), "ZL_ffb070_%d")
    box_uv(obj("LAMPPOST", bm, M_TAR_).data, 0.8)
    for rid, zone in (("W1", "west"), ("E1", "east"), ("S1", "south"), ("N1", "north")):
        col = plan["zone_color"][zone]; n = N[rid]; lamp_at(n["x"], n["y"], n["z"], n["h"], "ZL_%s_%%d" % col, 120, tuple(int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    for zn, p, col in (("z1", (-20, 0, 0), "cfe0ff"), ("z2", (1.5, 0, 0), "ff3319"), ("z8", (1.0, 0, 0), "ff8c1a"), ("z9", (-30, 4, 3), "8c0d0d")):
        v = zi[zn]["T"] @ Vector(p); lamp_at(v.x, v.y, v.z, 2.2, "ZL_%s_%%d" % col, 60, tuple(int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    bm = bmesh.new()
    for c, s_ in CORDS: box(bm, c, s_)
    if bm.verts: obj("NOCOL_LAMPCORD", bm, paint("lampcord", (0.012, 0.012, 0.012), 1.0))            # NOCOL_ = 게임에서 부딪힘 없음
    print("CHECK map4 lamps %d  hung on a cord %d (ceiling above %.1f m)" % (len(LIGHTS), len(CORDS), LAMP_H + 0.55))
    # ---- 사다리: 2편으로 내려가는 구멍(카드 10) · 서쪽 모임터 세로 구멍
    def ladder(x, y, z0, z1, yoff):
        bm = bmesh.new()
        for sx in (-0.25, 0.25): box(bm, (x + sx, y + yoff, (z0 + z1) / 2), (0.05, 0.05, z1 - z0))
        for k in range(int((z1 - z0) / 0.3)): box(bm, (x, y + yoff, z0 + 0.15 + k * 0.3), (0.5, 0.03, 0.03))
        for k in range(int((z1 - z0) / 0.8)):
            g = bmesh.ops.create_circle(bm, cap_ends=False, segments=16, radius=0.45)
            for v in g["verts"]: v.co += Vector((x, y + yoff - 0.35, z0 + 0.4 + k * 0.8))
        obj("LADDER", bm, M_LADDER)
    lx, ly, lz = ld["x"], ld["y"], ld["z"]; ladder(lx, ly, lz - 11.6, lz + 1.0, 1.3)
    boxes("RAILING", M_LADDER, [(Vector((lx + sx, ly + sy, lz + 0.55)), (0.08, 0.08, 1.1)) for sx in (-1.6, 1.6) for sy in (-1.6, 1.6)] +
          [(Vector((lx, ly + sy, lz + 1.05)), (3.2, 0.06, 0.06)) for sy in (-1.6, 1.6)] + [(Vector((lx + sx, ly, lz + 1.05)), (0.06, 3.2, 0.06)) for sx in (-1.6, 1.6)])
    ladder(lw["x"], lw["y"], lw["z"], n2["z"] + 0.9, 1.0)
    # ---- 표지 (넓이 우선으로 승강장까지 다음 곳 = home)
    adj = {}
    for e in plan["edges"]:
        a, b = e["a"].split(".")[0], e["b"].split(".")[0]; pa, pb = P(e["a"]), P(e["b"]); via = [Vector((v[0], v[1], 0)) for v in e["via"]]
        da = ((via[0] if via else pb) - pa); db = ((via[-1] if via else pa) - pb); da.z = db.z = 0
        adj.setdefault(a, []).append((b, da.normalized() if da.length > 1e-3 else Vector((0, 1, 0)))); adj.setdefault(b, []).append((a, db.normalized() if db.length > 1e-3 else Vector((0, 1, 0))))
    home, q = {"z6": None}, ["z6"]
    while q:
        u = q.pop(0)
        for v, _ in adj.get(u, []):
            if v not in home: home[v] = u; q.append(v)
    # 굴 입구마다 매단 양면 판 (사용자 10-01 "표지판이 벽에 박혀 알아보기 힘들다 · 어디 있는지 찾기 어렵다" — v2 는 방마다 하나를 출구 없는 쪽 벽에 붙였고 24 개 중 19 개가 바위에 묻혔다)
    # 규칙 하나: 방에서 나가는 굴 입구마다, 입구에서 방 안쪽 1 m 에, 굴 가운데 머리 위. 방 안에서 보면 "이 굴이 가는 곳"(+ 승강장 가는 길이면 한 줄 더), 굴에서 들어오며 보면 "이 방 이름"
    SIGN = {"P": "펌프실", "R0": "대기소", "L": "램프실", "W1": "서쪽 모임터", "W2": "갱목 쌓는 곳", "F": "막장 앞", "M": "옛 채굴 빈터", "K": "붕락 방", "K2": "갱목 창고", "MAG": "화약고",
            "S1": "광차 조차장", "LD": "사다리 굴", "H": "대피소", "R2": "선로 끝", "R1": "옛 펌프장", "E1": "선풍기 방", "E2": "막아 둔 채굴적", "E4": "권양기 방", "E3": "광차 굽이", "V": "창고 칸 줄",
            "X": "배전실", "N0": "계단 방", "N1": "저탄장", "N2": "북쪽 막장", "N3": "단층 방", "LW": "사다리",
            "z6": "승강장", "z3": "광차 싣는 곳", "z7": "바람문", "z8": "무너진 기둥", "z1": "쇠동발 숲", "z2": "채탄 막장", "z9": "큰 빈터"}
    # 모양 = 레퍼런스 공통점(10-01 조사: 장성 · 화순 · 폴란드 Guido · 독일 · 영국 갱 안 사진) — 굴 입구 위 천장에 사슬 둘로 매단 흰 칠 나무판 + 검은 글씨, 강조만 빨강. 어두운 판 + 주황 글씨는 실제 사진에 없었다
    M_SIGNBOARD_ = whitewash(MAT["MAT_Timber_EXPORT"], "sign_whitewash"); M_SIGNTEXT_ = paint("sign_black", (0.03, 0.03, 0.035), 0.8); M_SIGNRED = paint("sign_red", (0.25, 0.012, 0.01), 0.8)
    signs, hid_room, hid_tun, worst = 0, 0, 0, []
    def floor_eye(p):                                                                         # 눈 자리가 바위 바닥 위인가 (돌 더미 · 광차 위가 아니다)
        hit, f_, _, _, ob, _ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((p.x, p.y, p.z + 1.2)), Vector((0, 0, -1)), distance=4.0)
        return Vector((f_.x, f_.y, f_.z + EYE)) if hit and ob.name.startswith(("SHELL", "FLOOR", "STEPS", "NOCOL_")) else None   # 디딤 판 · 물웅덩이 위도 설 수 있다
    for e in plan["edges"]:
        if e["kind"] == "shaft": continue
        for me_, other in ((e["a"], e["b"]), (e["b"], e["a"])):
            n = N.get(me_)
            if n is None or n not in rooms or min(n["w"], n["d"]) < 5: continue                 # 방 쪽 끝만 (장면 · 판자 문 칸 · 사다리 오목은 뺀다)
            oid = other.split(".")[0]; d = next(dd for v, dd in adj[n["id"]] if v == oid)
            front = [(SIGN[oid], 0.24)] + ([("승강장 가는 길", 0.17, M_SIGNRED)] if home.get(n["id"]) == oid and oid != "z6" else []); back = [(SIGN[n["id"]], 0.24)]
            w_, hb = sign_size(front, back); best = None
            for k_ in (1.0, 1.8, 2.6):                                                         # 입구에서 방 안쪽으로 얼마나 — 굴 문틀이 낮으면 굴에서 판이 안 보인다. 양쪽 다 보이는 가장 가까운 자리
                c = W(n, 0, 0) + d * (exit_t(n["id"], d) - k_); C = Vector((c.x, c.y, n["z"] + SIGN_Z + hb / 2))
                fr = next((p_ for p_ in (floor_eye(c - d * b_) for b_ in (3.0, 4.0, 2.4, 5.5, 1.8, 1.0)) if p_), None); ft = floor_eye(c + d * (k_ + 2.0))   # 설 수 있는 눈 자리 (없으면 재기만 하고 캡처 자리는 안 만든다 — 사다리 구멍 · 비탈)
                er = fr or Vector((c.x, c.y, n["z"] + EYE)) - d * 3.0; et = ft or Vector((c.x, c.y, n["z"] + EYE)) + d * (k_ + 2.0)   # 굴 쪽 눈 = 입구에서 굴 안 2 m
                hr, ht = sign_hidden(C - d * 0.03, -d, w_, hb, er), sign_hidden(C + d * 0.03, d, w_, hb, et)
                if best is None or hr + ht < best[0] - 0.05: best = (hr + ht, c, er, et, hr, ht, fr, ft)
                if hr + ht <= 0.1: break
            _, c, er, et, hr, ht, fr, ft = best; C, w_, hb = hang_sign(c, d, front, back, n["z"]); signs += 1; hid_room += hr > 0.1; hid_tun += ht > 0.1
            if max(hr, ht) > 0.1: worst.append("%s→%s room %.0f %% tunnel %.0f %%" % (n["id"], oid, hr * 100, ht * 100))
            if home.get(n["id"]) == oid:                                                       # 캡처 자리: 방마다 승강장 쪽 입구의 표지를 방 안에서 (몇 방은 굴에서 들어오며도)
                if fr: SHOTS.append(("sign_%s" % n["id"], tuple(er), tuple(C)))
                if ft and abs(ft.z - EYE - n["z"]) < 0.3 and n["id"] in ("W1", "S1", "E1", "K"): SHOTS.append(("signin_%s" % n["id"], tuple(et), tuple(C)))
    print("CHECK map4 signs %d at tunnel mouths · hidden more than 10 %% from 3 m at eye height: room side %d · tunnel side %d%s" % (signs, hid_room, hid_tun, (" — " + "; ".join(worst[:20])) if worst else ""))
    # ---- 방 자리 (판정용 [ ] 키 · 사진 맞히기): 방 한쪽에서 건너편을 본다
    LOOK = {"N2": (0, 1), "X": (0, 1), "V": (0, -1), "E1": (0, 1), "E2": None, "R0": (0, -1), "L": (0, 1), "N3": (0, 1)}   # 주인공 소품이 있는 벽 쪽
    for n in rooms:
        if n["id"] in ("LW",): continue
        lk = LOOK.get(n["id"], "long")
        if n["id"] == "N0": lk = tuple((P("N1") - W(n, 0, 0)).to_2d().normalized())
        if n["id"] == "E2": lk = tuple((Vector((N["GOAF_E"]["x"], N["GOAF_E"]["y"])) - Vector((n["x"], n["y"]))).normalized())
        if lk == "long": lk = (1, 0) if n["w"] >= n["d"] else (0, 1)
        ext = abs(lk[0]) * n["w"] / 2 + abs(lk[1]) * n["d"] / 2
        e_ = W(n, -lk[0] * ext * 0.55, -lk[1] * ext * 0.55, EYE); t_ = W(n, lk[0] * ext, lk[1] * ext, 1.3)
        SHOTS.append(("room_%s" % n["id"], tuple(e_), tuple(t_)))
    SHOTS.insert(0, ("start", (0, 2.0, EYE), (0, -12, 1.5)))                                  # 시작 = 승강장, 남쪽 굴을 본다
    # ---- 잰 값: 바닥 넓이 · 선 채로 못 지나는 낮은 곳 (사용자 10-01 "높낮이를 낮게 구성하지 말아라")
    fl = np.empty(len(SHELL.data.polygons) * 3); SHELL.data.polygons.foreach_get("normal", fl); ar = np.empty(len(SHELL.data.polygons)); SHELL.data.polygons.foreach_get("area", ar)
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get(); low, pts = [], []
    for s in SEG:
        L = (s["q"] - s["p"]).to_2d().length
        for t in np.arange(0.5, L, 1.0): pts.append((s["p"].lerp(s["q"], t / L), "tunnel %s-%s" % (s["edge"]["a"], s["edge"]["b"])))
    for n in rooms:
        for x_ in np.arange(-n["w"] / 2 + 1.0, n["w"] / 2 - 0.9, 2.0):
            for y_ in np.arange(-n["d"] / 2 + 1.0, n["d"] / 2 - 0.9, 2.0): pts.append((W(n, x_, y_), "room " + n["id"]))
    for zn, a_, b_, y_ in (("z1", -22, 20, 0.0), ("z2", 0, 20, 0.0), ("z8", 0, 19.9, -0.6)):
        for t in np.arange(a_, b_, 1.0): pts.append((zi[zn]["T"] @ Vector((t, y_, 0)), "scene " + zn))
    for p, where in pts:
        hit, f_, _, _, ob, _ = sc.ray_cast(deps, p + Vector((0, 0, 1.2)), Vector((0, 0, -1)), distance=3.0)
        if not hit or not ob.name.startswith(("SHELL", "FLOOR")): continue                   # 바위 바닥에 선 자리만 (돌 더미 · 광차 · 선반 위는 걷는 곳이 아니다)
        hit2, c_, *_ = sc.ray_cast(deps, f_ + Vector((0, 0, 0.3)), Vector((0, 0, 1)), distance=6.0)
        if hit2 and c_.z - f_.z < 2.0: low.append((where, round(f_.x, 1), round(f_.y, 1), round(c_.z - f_.z, 2)))
    print("CHECK map4 floor %.0f m2  rooms %d  scenes %d  tunnels %d  closets %d  signs %d  lights %d" % (ar[fl.reshape(-1, 3)[:, 2] > 0.9].sum(), len(rooms), len(Z), len(plan["edges"]), len(ALC), signs, len(LIGHTS)))
    print("CHECK map4 low spots %d of %d sampled (headroom < 2.0 m)%s" % (len(low), len(pts), (": " + "; ".join("%s (%s, %s) %.2f" % l for l in low[:12])) if low else ""))
    tiles = split_tiles(SHELL)
    print("CHECK map4 shell tiles %d  tris %d  all tris %d" % (len(tiles), sum(len(t.data.polygons) for t in tiles), sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")))
    xs = [n["x"] for n in plan["nodes"]] + [s["x"] for s in plan["scenes"]]; ys = [n["y"] for n in plan["nodes"]] + [s["y"] for s in plan["scenes"]]
    view = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys)) + 50)
    print("CHECK map4 view %.1f %.1f %.1f" % view)
    for n in rooms: print("CHECK map4 label %s|%.1f|%.1f" % (n["name"][:10], n["x"], n["y"]))
    for z in Z: v = z["T"] @ Vector(((L3 / 2) if z["n"] == "z3" else (L7S + L7W) / 2 if z["n"] == "z7" else 10 if z["n"] in ("z8", "z2") else 0, 0, 0)); print("CHECK map4 label %s|%.1f|%.1f" % (SCENE_NAME[z["n"]], v.x, v.y))
    # 좌표 없는 물체(통 · 관 · 감개 · 장면의 쇠 틀)에 상자 투영 좌표 — 사진 재질이 펴지게 (조사 12: cyl() 이 좌표를 안 만들어 녹슨 통 · 관에 사진이 안 펴졌다)
    nouv = [o for o in bpy.data.objects if o.type == "MESH" and not o.data.uv_layers and any(m_ and m_.use_nodes and any(x.type == "TEX_IMAGE" for x in m_.node_tree.nodes) for m_ in o.data.materials)]
    for o in nouv: box_uv(o.data, 0.8)
    print("CHECK map4 photo materials: wood %s · tar %s · metal %s / %s · cloth %s · box-uv added to %d objects" % tuple(["cc0" if os.path.isdir(os.path.join(CC0, d_)) else "OLD" for d_ in ("wood/rough_wood", "wood/black_painted_planks", "metal/metal_plate_02", "metal/rusty_metal_04", "misc/decrepit_wallpaper")] + [len(nouv)]))
    return dict(lights=LIGHTS, adapt=((0, 0, 3), 1, 1), fills=([], 3, 0, 1), shots=SHOTS, people=[(0, 0, 0)], ortho=view[2], side_z=2, center=view[:2], map=True)

if SCENE == "t": OUT = os.path.join(ROOT, "build", "check_map4", "tex_" + os.environ.get("TEXNAME", "now"))
if SCENE == "f": OUT = os.path.join(ROOT, "build", "check_map4", "tex_" + os.environ.get("TEXNAME", "fab_model"))
if MAP: OUT = os.path.join(ROOT, "build", "check_map4", "map")
S = {"9": scene9, "6": scene6, "1": scene1, "3": scene3, "7": scene7, "8": scene8, "2": scene2, "t": scene_t, "f": scene_f, "v": scene_v, "m": map4}[SCENE]()

# EXPORT_GLB=<파일> — 장면을 게임에 그대로 넣어 보려고 (엔진 확인, 사용자 09-30 "엔진의 한계인가?"). 카메라 자리 CAM_<이름> · 보는 곳 AT_<이름> · 전등 LAMP_<i> 빈 노드를 같이.
# Fab 을 쓴 장면은 Assets/Fab/Resources/ 에만 (git 에 안 올림). 그림은 2K 로 줄인다 — Unity 도 기본 2K 로 줄인다.
if os.environ.get("EXPORT_GLB"):
    for nm, eye, at in S["shots"]:
        for pre, p in (("CAM_", eye), ("AT_", at)):
            e = bpy.data.objects.new(pre + nm, None); e.location = p; sc.collection.objects.link(e)
    for i, l in enumerate(S["lights"]):
        e = bpy.data.objects.new(l[0] if l[0].startswith("ZL_") else ("BLUE_%d" if l[0].startswith("BLUE") else "LAMP_%d") % i, None); e.location = l[1]; sc.collection.objects.link(e)
    deps = bpy.context.evaluated_depsgraph_get()                                     # 글씨 · 호스(곡선)는 그물로 바꿔 넣는다 — glTF 가 곡선을 못 담는다
    for o in [o for o in bpy.data.objects if o.type in ("FONT", "CURVE")]:
        m = bpy.data.meshes.new_from_object(o.evaluated_get(deps)); n = bpy.data.objects.new(o.name + "_M", m); n.matrix_world = o.matrix_world; sc.collection.objects.link(n); bpy.data.objects.remove(o, do_unlink=True)
    for im in bpy.data.images:
        if im.size[0] > 2048: im.scale(2048, 2048); im.pack()
    os.makedirs(os.path.dirname(os.environ["EXPORT_GLB"]), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.environ["EXPORT_GLB"], export_format="GLB", export_image_format="JPEG", export_jpeg_quality=90, export_lights=False)
    print("CHECK export %s  tris %d" % (os.environ["EXPORT_GLB"], sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")))
    if not MAP: raise SystemExit                                                        # 맵은 내보낸 뒤 위에서 본 그림도 찍는다

# ================= 그림
os.makedirs(OUT, exist_ok=True)
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (0, 0, 0, 1)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(FOV); cam.data.clip_end = 200; cam.data.clip_start = 0.05
lamp = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(lamp)
lamp.data.energy = 900; lamp.data.spot_size = math.radians(LAMP_DEG); lamp.data.spot_blend = 0.5; lamp.data.color = (1.0, 0.93, 0.82)
lamp.data.use_custom_distance = True; lamp.data.cutoff_distance = LAMP_M
def point(name, p, energy, color=(1, 1, 1), radius=0.5, shadow=True):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "POINT")); sc.collection.objects.link(L)
    L.location = p; L.data.energy = energy; L.data.color = color; L.data.shadow_soft_size = radius; L.data.use_shadow = shadow; return L
lights = [point(*l) for l in S["lights"]]                         # 그 장면에 실제로 있는 전등
ap, ae, ar = S["adapt"]; adapt = point("ADAPT", ap, ae, (0.8, 0.85, 1.0), ar, False)   # 눈이 어둠에 익은 정도(어림 — 게임의 DARK_ADAPT_AMBIENT 대신)
fp, fz, fe, fr = S["fills"]; fills = [point("FILL%d" % i, (x, y, fz), fe, (1, 0.97, 0.92), fr, False) for i, (x, y) in enumerate(fp)]
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
for nm, eye, at in ([] if S.get("map") else S["shots"]):                    # 맵은 1인칭 그림을 안 찍는다 (게임에서 본다)
    for on, shot in S.get("shot_only", {}).items(): bpy.data.objects[on].hide_render = nm not in ((shot,) if isinstance(shot, str) else shot)   # 그 장(들)에만 보이는 것 (예: 괴물 눈 · 연 문)
    cam.location = eye; q = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
    lamp.location = Vector(eye) + Vector((0, 0, 0.1)); lamp.rotation_euler = q.to_euler()
    for mode in ("lamp", "shape"):
        for f in fills: f.hide_render = mode == "lamp"
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (nm, mode)); bpy.ops.render.render(write_still=True)

# 위 · 옆에서 본 모양 (크기 읽기) — 1.7 m 사람 막대
bm = bmesh.new()
for p in S["people"]: box(bm, (p[0], p[1], p[2] + 0.85), (0.5, 0.5, 1.7))
obj("PERSON", bm, M_RUST).color = (0.9, 0.2, 0.1, 1)
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_backface_culling = True; sh.show_cavity = True
for o in bpy.data.objects:
    if o.type in ("MESH", "FONT") and o.name != "PERSON":
        o.color = next((c for k, c in {"SHELL": (0.62, 0.59, 0.53, 1), "TIMBER": (0.55, 0.36, 0.18, 1), "BOARDS": (0.55, 0.36, 0.18, 1), "ROCKS": (0.4, 0.38, 0.35, 1),
                   "GATE": (0.9, 0.7, 0.1, 1), "CAGEDOOR": (0.7, 0.1, 0.08, 1), "DOOR": (0.75, 0.5, 0.25, 1)}.items() if o.name.startswith(k)), (0.35, 0.36, 0.38, 1))
for L in [lamp, adapt] + lights + fills: L.hide_render = True
for o in S.get("top_hide", []): o.hide_render = True             # 굴 조각을 걷어 내고 속을 본다 (Fab 굴은 위에서 지붕만 보인다)
cam.data.type = "ORTHO"; cam.data.ortho_scale = S["ortho"]
cxy = S.get("center", (0, 0))
for nm, loc, rot in (("top", (cxy[0], cxy[1], 80), (0, 0, 0)), ("side", (cxy[0], -80, S["side_z"]), (math.radians(90), 0, 0))):
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = os.path.join(OUT, nm + ".png"); bpy.ops.render.render(write_still=True)
print("CHECK scene%s renders -> %s  tris %d" % (SCENE, OUT, sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")))
