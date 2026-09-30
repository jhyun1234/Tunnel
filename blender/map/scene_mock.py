"""MAP4 장면 시안 — 장면 하나를 블록아웃으로 짓고 눈높이 1인칭 그림을 뽑는다 (제안서 docs/제안서_MAP4_장면부터_짠_맵.md 6절 차례 2).
  SCENE=9 "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/scene_mock.py
  SCENE = 9 (거대한 빈 공간 = 1편 그것의 굴) · 6 (케이지 승강장) · 1 (쇠동발 숲) · 3 (광차 싣는 곳, Fab 모델 — build/tex_test/fab 필요) · 7 (바람문 두 짝, Fab) · t (질감 시험 벽) · f (Fab 갱도 조각)
재질은 부스 맵과 같다(Assets/Tunnel/Pieces/piece_straight.gltf 에서 가져옴 — 안 고친다). 칠 · 콘크리트 · 전구는 여기서 만든 단색 재질.
동굴 만드는 법도 make_booth.py 와 같다: 공기 덩어리 → 복셀 리메시 → 면 뒤집기 → 벽을 바위 쪽으로만 파는 잡음.
출력: build/check_map4/scene<번호>/ — fp_*_lamp.png(머리등 + 그 장면의 전등 + 눈이 어둠에 익은 정도, 게임에 가깝게) · fp_*_shape.png(모양을 보려고 밝힘)
  · side.png · top.png(1.7 m 사람 크기 막대).
카메라 = 게임과 같은 세로 화각 80° · 눈 1.7 m. 머리등 = 스포트 60° · 14 m (Tuning.LAMP_ANGLE_DEG · LAMP_RANGE)."""
import bpy, bmesh, os, math, random
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
SCENE = os.environ.get("SCENE", "9")
OUT = os.path.join(ROOT, "build", "check_map4", "scene" + SCENE)
VOXEL, EYE, FOV, LAMP_DEG, LAMP_M = 0.25, 1.7, 80.0, 60.0, 14.0
random.seed(int(SCENE) if SCENE.isdigit() else SCENE)

# ================= 재질 (부스 맵과 같은 것 + 단색)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(PIECES, "piece_straight.gltf"))
MAT = {m.name: m for m in bpy.data.materials}
M_WALL, M_FLOOR, M_TIMB, M_ROCK, M_RUST = (MAT[n] for n in ("MAT_RockWall_EXPORT", "MAT_Floor_EXPORT", "MAT_Timber_EXPORT", "MAT_Rock_EXPORT", "MAT_RustyMetal_EXPORT"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene

def paint(name, rgb, rough=0.7, metal=0.0, emit=0.0):
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
    for y in (-3.5, 3.5): box(bm, (0, y, 0.95), (L, 3, 1.9))     # 양옆 가장자리는 1.9 m 로 낮아진다 (탄층 따라)
    box(bm, (-L / 2 - 5, 0, 1.2), (10, 2.6, 2.4))               # 들어오는 곁갱도 (나무동발)
    box(bm, (L / 2 + 4, 0, 0.8), (8, 5, 1.6))                   # 새로 판 막장 쪽 — 더 낮다 (1.6 m, 숙여야 한다)
    shell(bm, 0.25)
    bm = bmesh.new(); bmc = bmesh.new(); bmt = bmesh.new()
    for i, x in enumerate(np.arange(-L / 2 + 0.8, L / 2 - 0.5, 1.1)):
        for y in (-4.3, -3.2, -2.1, -1.0, 1.0, 2.1, 3.2, 4.3):
            px, py = x + random.uniform(-0.15, 0.15), y + random.uniform(-0.12, 0.12)
            top = (H if abs(y) < 2.5 else 1.9) - 0.12
            tilt = Matrix.Rotation(math.radians(random.uniform(-3, 3)), 3, "X") @ Matrix.Rotation(math.radians(random.uniform(-3, 3)), 3, "Y")
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.075, radius2=0.075, depth=top * 0.55)          # 아래 통
            for v in g["verts"]: v.co = tilt @ (v.co + Vector((0, 0, top * 0.275))) + Vector((px, py, 0))
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.058, radius2=0.058, depth=top * 0.5)           # 위 통 (늘어나는 쇠동발)
            for v in g["verts"]: v.co = tilt @ (v.co + Vector((0, 0, top * 0.75))) + Vector((px, py, 0))
            box(bmc, tilt @ Vector((0, 0, top * 0.55)) + Vector((px, py, 0)), (0.2, 0.2, 0.14), tilt)                             # 조임쇠
            box(bmt, tilt @ Vector((0, 0, top + 0.06)) + Vector((px, py, 0)), (0.55, 0.16, 0.12), tilt)                           # 나무 받침
    props = obj("PROPS", bm, M_PROP); props.data.polygons.foreach_set("use_smooth", np.ones(len(props.data.polygons), dtype=bool)); obj("CLAMPS", bmc, M_CLAMP)
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
    for s in (-1, 1): box(bm, (x, s * (DOOR_W / 2 + 0.1), (DOOR_H + 0.2) / 2), (0.22, 0.2, DOOR_H + 0.2))   # 문틀 기둥
    box(bm, (x, 0, DOOR_H + 0.1), (0.22, DOOR_W + 0.4, 0.2))           # 문틀 머리
    box_uv(obj("BOARDS", bm, M_TIMB).data, 0.8)
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
    box_uv(obj(name, bm, M_TIMB).data, 0.8); obj(name + "_IRON", bmi, M_IRON)

def scene7():
    M_IRON = paint("iron", (0.08, 0.08, 0.08), 0.6, 0.8); M_PAINT = paint("wallpaint", (0.9, 0.75, 0.1), 0.8)
    M_BLK = paint("gouge", (0.02, 0.015, 0.01), 0.9)
    tunnel = []
    steel = arch_run(["wdpnchedw", "wdpnchtdw", "wdpnchedw", "wdpnchtdw"], 0.0, tunnel)          # 운반갱도 = Fab 강철 아치 (시안 ③ 과 같은 조각)
    tun = arch_run(["wcbpdfsdw", "wcbpdgcdw", "wcbpdfsdw"], steel, tunnel)                       # 문 너머 = 곁갱도 = Fab 나무 버팀 (사용자 09-30 굴 종류)
    coal_floor(0, tun); rail_run(0, tun)
    xb = steel - 0.15; xa = xb - 6.0                                   # 뒷문은 강철 아치 끝 (벽이 두 굴 모양이 바뀌는 곳을 가린다) · 앞문은 6 m 앞
    bulkhead(xa, +1); _, wb = bulkhead(xb, -1)
    door(xa, "DOORA", +1, +1, 0, M_IRON)                             # 앞문 — 두 문 사이로 밀어 연다
    door(xb, "DOORB_SHUT", -1, +1, 0, M_IRON)                        # 뒷문 — 곁갱도 쪽으로 밀어 연다 (닫힌 것 · 연 것 두 벌, 그림마다 하나)
    door(xb, "DOORB_OPEN", -1, +1, 80, M_IRON)
    face = lambda sgn: (math.radians(90), 0, math.radians(-90 * sgn))  # 글자가 -x(sgn=1) · +x(sgn=-1) 쪽을 본다
    fw = DOOR_W / 2 + 0.2
    text("풍문", (xa - BOARD_T / 2 - 0.01, 0, DOOR_H + 0.45), 0.45, M_PAINT, face(1))                       # 앞문 (오는 쪽)
    text("항상 닫을 것", (xa - BOARD_T / 2 - 0.01, -(fw + 0.6), 1.55), 0.16, M_PAINT, face(1))
    text("반대쪽 문을 닫고 여시오", (xb - BOARD_T / 2 - 0.01, -(fw + 0.65), 1.0), 0.12, M_PAINT, face(1))   # 두 문 사이 — 뒷문 옆 (가로대 사이)
    text("반대쪽 문을 닫고 여시오", (xa + BOARD_T / 2 + 0.01, fw + 0.65, 1.0), 0.12, M_PAINT, face(-1))      # 두 문 사이 — 앞문 옆 (돌아볼 때)
    bm = bmesh.new()                                                  # 긁힌 자국 — 뒷문 옆 판자 (괴물은 문을 긁는다, 제안서 3-1)
    for k in range(4): box(bm, (xb - BOARD_T / 2 - 0.004, fw + 0.35 + k * 0.07, 2.0 - k * 0.03), (0.008, 0.025, 0.55), Matrix.Rotation(math.radians(22), 3, "X"))
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

def fab_many(fid, places, **kw):
    """같은 Fab 모델을 여러 자리에 — 한 번만 불러오고 그물을 나눠 쓴다. places = [(x, y, z, yaw, 배율)] (밑면 가운데 자리)"""
    objs, lo, hi = fab(fid, (0, 0, 0), **kw); out = []
    for k, (x, y, z, yaw, s_) in enumerate(places):
        for o in objs:
            c = o if k == 0 else o.copy()
            if k: sc.collection.objects.link(c)
            R = Matrix.Rotation(math.radians(yaw), 3, "Z"); off = Vector(o.location) if k == 0 else base[o.name]
            if k == 0: base[o.name] = off.copy()
            c.rotation_euler = (0, 0, math.radians(yaw)); c.scale = (s_, s_, s_)
            c.location = Vector((x, y, z)) + R @ (off * s_)
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

if SCENE == "t": OUT = os.path.join(ROOT, "build", "check_map4", "tex_" + os.environ.get("TEXNAME", "now"))
if SCENE == "f": OUT = os.path.join(ROOT, "build", "check_map4", "tex_" + os.environ.get("TEXNAME", "fab_model"))
S = {"9": scene9, "6": scene6, "1": scene1, "3": scene3, "7": scene7, "t": scene_t, "f": scene_f, "v": scene_v}[SCENE]()

# EXPORT_GLB=<파일> — 장면을 게임에 그대로 넣어 보려고 (엔진 확인, 사용자 09-30 "엔진의 한계인가?"). 카메라 자리 CAM_<이름> · 보는 곳 AT_<이름> · 전등 LAMP_<i> 빈 노드를 같이.
# Fab 을 쓴 장면은 Assets/Fab/Resources/ 에만 (git 에 안 올림). 그림은 2K 로 줄인다 — Unity 도 기본 2K 로 줄인다.
if os.environ.get("EXPORT_GLB"):
    for nm, eye, at in S["shots"]:
        for pre, p in (("CAM_", eye), ("AT_", at)):
            e = bpy.data.objects.new(pre + nm, None); e.location = p; sc.collection.objects.link(e)
    for i, l in enumerate(S["lights"]):
        e = bpy.data.objects.new(("BLUE_%d" if l[0].startswith("BLUE") else "LAMP_%d") % i, None); e.location = l[1]; sc.collection.objects.link(e)
    for im in bpy.data.images:
        if im.size[0] > 2048: im.scale(2048, 2048); im.pack()
    os.makedirs(os.path.dirname(os.environ["EXPORT_GLB"]), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.environ["EXPORT_GLB"], export_format="GLB", export_image_format="JPEG", export_jpeg_quality=90, export_lights=False)
    print("CHECK export %s  tris %d" % (os.environ["EXPORT_GLB"], sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH"))); raise SystemExit

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
for nm, eye, at in S["shots"]:
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
