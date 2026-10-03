"""MAP4 장면 시안 — 장면 하나를 블록아웃으로 짓고 눈높이 1인칭 그림을 뽑는다 (제안서 docs/제안서_MAP4_장면부터_짠_맵.md 6절 차례 2).
  SCENE=9 "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/scene_mock.py
  SCENE = 9 (거대한 빈 공간 = 1편 그것의 굴) · 6 (케이지 승강장) · 1 (쇠동발 숲) · 3 (광차 싣는 곳, Fab 모델 — build/tex_test/fab 필요) · 7 (바람문 두 짝, Fab) · 8 (무너진 기둥 굴, Fab) · 2 (낮은 채탄 막장, Fab) · t (질감 시험 벽) · f (Fab 갱도 조각)
재질은 부스 맵과 같다(Assets/Tunnel/Pieces/piece_straight.gltf 에서 가져옴 — 안 고친다). 칠 · 콘크리트 · 전구는 여기서 만든 단색 재질.
동굴 만드는 법도 make_booth.py 와 같다: 공기 덩어리 → 복셀 리메시 → 면 뒤집기 → 벽을 바위 쪽으로만 파는 잡음.
출력: build/check_map4/scene<번호>/ — fp_*_lamp.png(머리등 + 그 장면의 전등 + 눈이 어둠에 익은 정도, 게임에 가깝게) · fp_*_shape.png(모양을 보려고 밝힘)
  · side.png · top.png(1.7 m 사람 크기 막대).
카메라 = 게임과 같은 세로 화각 80° · 눈 1.7 m. 머리등 = 스포트 60° · 14 m (Tuning.LAMP_ANGLE_DEG · LAMP_RANGE)."""
import bpy, bmesh, os, sys, math, random, json
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "props"))   # 알아볼 수 있게 다시 만든 소품 (10-02 판정 ①) — props/<이름>.py, 미리보기는 props/_preview.py
import _util as PU, pump_set, fan_duct, timber_store, staging as staging_, wall_props, cloth as cloth_, machines, cc0_models
import timber_sets, lamp_rack, chute, substation, store_stalls                                   # 10-03 판정 ② 뒤 더한 소품: 둥근 동발 틀 · 램프 충전대 · 광차 싣는 곳 홈통
import face_kit                                                                                   # 10-03 판정 ③ 뒤: 착암기 · 압축공기 관 · 호스 · 발파 구멍 · 분필 (막장 연장)
PMATS = None                                                              # 소품 재질 (이름 → 재질, map4() 가 사진 재질로 채운다)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
SCENE = os.environ.get("SCENE", "9")
OUT = os.path.join(ROOT, "build", "check_map4", "scene" + SCENE)
VOXEL, EYE, FOV, LAMP_DEG, LAMP_M = 0.25, 1.7, 80.0, 60.0, 14.0
random.seed(int(SCENE) if SCENE.isdigit() else SCENE)
MAP = SCENE == "m"                                                    # 맵 모드 (SCENE=m) — 통과한 장면들을 한 맵에 놓고 굴로 잇는다. 맨 아래 map4() 참고
LOWEST = 2.35 if MAP else 0.0                                          # 맵 모드: 천장 최소 (사용자 10-01 "높낮이를 낮게 구성하지 말아라" — 저절로 숙이며 지나가면 짜증) · 시안 그림은 옛 높이 그대로
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

def big_air(bm, big, big_m, keep=()):
    """큰 방(⑨)의 큰 굴곡을 '공기 덩어리'일 때 만든다: 복셀 → 벽 · 천장 점을 바깥(바위 쪽)으로 0~big_m 밀기. 그 뒤 맵 전체 복셀이 다시 한 겹으로 감싼다.
    (사용자 10-02 "굴 위의 모델링이 끊어져 있음": 바위 겉면을 다 만든 뒤에 1.6 m 를 밀어 0.25 m 간격 점들이 서로를 지나쳤다 — 큰 빈터 겉면의 6.9 % 가 뒤집혀 검은 틈 · 뾰족한 조각으로 보였다.)"""
    air = obj("AIRBIG", bm, M_WALL)
    rm = air.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
    me = bpy.data.meshes.new_from_object(air.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(air, do_unlink=True)
    o = bpy.data.objects.new("AIRBIG2", me); sc.collection.objects.link(o)
    n = len(me.vertices); co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    nz = np.empty(n * 3); me.vertices.foreach_get("normal", nz); nz = nz.reshape(-1, 3)[:, 2]            # 공기의 노멀은 바위 쪽 — 바닥은 아래(−z)를 본다
    sel = (np.abs(co[:, 0]) < big[0]) & (np.abs(co[:, 1]) < big[1]) & (nz >= -0.6) & (co[:, 2] > 0.4)   # 방 안의 벽 · 천장만 (굴 · 바닥은 안 넓힌다)
    for kx, ky, kr in keep: sel &= np.hypot(co[:, 0] - kx, co[:, 1] - ky) > kr                           # 굴 입구 · 계단 옆 벽은 그대로 (밀면 발판과 바위 턱 사이가 벌어진다)
    vg = o.vertex_groups.new(name="big"); vg.add(np.nonzero(sel)[0].tolist(), 1.0, "REPLACE")
    tex = bpy.data.textures.new("bignoise", type="CLOUDS"); tex.noise_scale = 5.0; tex.noise_depth = 2
    dm = o.modifiers.new("big", "DISPLACE"); dm.texture = tex; dm.texture_coords = "LOCAL"; dm.strength = big_m; dm.mid_level = 0.0; dm.direction = "NORMAL"; dm.vertex_group = "big"
    me2 = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(o, do_unlink=True)
    out = bmesh.new(); out.from_mesh(me2); bpy.data.meshes.remove(me2); return out

def shell(bm, carve, big=None, big_m=1.6, keep=()):
    """공기 덩어리 → 안에서 보는 바위 동굴. big = (반폭 x, 반폭 y) 안의 벽 · 천장만 크게 굴곡 (굴 · 바닥은 안 넓힌다)"""
    if MAP:                                                           # 맵 모드: 공기는 맵 전체 한 덩어리로 모으고(이음새 · 막힌 끝이 없게), 소품 단계엔 합친 굴을 돌려준다
        if PASS == "air":
            if big: bm = big_air(bm, big, big_m, keep); carve = min(carve, 0.45)   # 큰 굴곡은 공기일 때 민다 (아래 big_air) — 그 뒤 잔 굴곡은 다른 방과 같은 깊이로
            bm.transform(ZT); AIR.append((bm, carve, None)); raise ZoneAir
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
    """벽에 칠한 글자 · 굴 입구 표지 글자 = 인트로 글씨체 배민 을지로체 (사용자 10-03 "표지의 글씨는 인트로 폰트를 사용해라. 모든 것들을").
    곡선은 성기게(resolution 2) + thin 으로 그물에 굽는다 (props/_util.text_mesh). 옛 것: 맑은 고딕 곡선 · 기본 12 — 내보낼 때 그물로 바뀌며 글자만 삼각형 22만 개였다"""
    return PU.text_mesh("TEXT", body, loc, size, mat, rot=rot, extrude=0.005)

# ================= 장면 9 — 거대한 채굴 빈 공간 = 1편 그것의 굴
# 장면 카드 9. 참고(09-30): 스톱의 나무 버팀목 · 벽 따라 발판·계단 · 돌 더미 · 남은 바위 기둥 + 한국 탄광 급경사 탄층 → 천장 위 비스듬한 틈 = 그것이 내려오는 곳.
Z9_COLUMNS = (((-5, -4), 1.8), ((6, 5), 1.6), ((12, -6), 1.5))            # 그것의 굴의 남은 바위 기둥 셋 (장면 좌표 가운데, 반지름)
def rock_column(cx, cy, r, z0, z1, T, name):
    """바닥에서 천장까지 선 바위 기둥을 벽과 같은 법으로: 닫힌 통 → 0.3 m 복셀로 다시 감싸기 → 잡음으로 울퉁불퉁 → 부드럽게. T = 세계 좌표로 옮기는 틀"""
    bm = bmesh.new(); column(bm, cx, cy, r, z0, z1, seg=18, ring=0.7); bm.verts.ensure_lookup_table()
    lo = [v for v in bm.verts if abs(v.co.z - z0) < 1e-4]; n_ = int((z1 - z0) / 0.7); hi = [v for v in bm.verts if abs(v.co.z - (z0 + n_ * 0.7)) < 1e-4]
    bm.faces.new(lo[::-1]); bm.faces.new(hi); bm.transform(T)
    o = obj("COLTMP", bm, M_ROCK); rm = o.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = 0.3; rm.adaptivity = 0.0
    tex = bpy.data.textures.new("colnoise", type="CLOUDS"); tex.noise_scale = 1.4; tex.noise_depth = 3
    dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"; dm.strength = 0.45; dm.mid_level = 0.5
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(o, do_unlink=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool)); me.materials.clear(); me.materials.append(M_ROCK)
    c = bpy.data.objects.new(name, me); sc.collection.objects.link(c); return c

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
    shell(bm, 0.6, big=(22, 15), keep=[(-20, 4, 4.5), (-20, 0, 4.0), (-20, -3.5, 4.0), (20, -8, 3.5)])

    if not MAP:                                               # 맵에서는 map4() 가 놓는다 (Z9_COLUMNS · 아래 "그것의 굴" 절) — 사용자 10-03 "돌 무더기 큰 암석의 모델링이 어색": 14각 통 기둥(면이 평평하게 찍힘) + 면 80개짜리 공 덩이였다
        bm = bmesh.new()                                      # 남은 바위 기둥 셋 — 시야를 끊는다
        for c, r in Z9_COLUMNS: column(bm, c[0], c[1], r)
        for i in range(55):                                   # 무너진 돌 더미 — 벽 밑과 가운데 한 무더기
            c = (random.uniform(-6, 9), random.uniform(-10, -2)) if i < 20 else (random.uniform(-18, 18), random.choice((-11.5, 11.5)) + random.uniform(-1, 1))
            s = random.uniform(0.4, 1.3); blob(bm, (c[0], c[1], s * 0.3), (s, s * random.uniform(0.7, 1.3), s * 0.6), 1)
        box_uv(obj("ROCKS", bm, M_ROCK).data, 0.5)

    bm = bmesh.new()
    if MAP and PMATS:                                         # 맵: 발판 · 계단을 광산 목공으로 (사용자 10-02 "큰 빈터의 건축물의 퀄리티가 너무 떨어진다" — 얇은 판 하나 · 떠 있는 상자 계단 · 기둥 없는 난간이었다)
        PU.place(staging_.build(PMATS, deck_h=3.0, deck_x=4.4, deck_y=3.0), Matrix.Translation((-18, 4, 0)))   # 레퍼런스 공통점: 굵은 기둥 + 가새 · 틈 있는 널 · 옆판 둘 사이 디딤널 · 난간 (props/staging.py)
        PU.place(staging_.spare_timbers(PMATS, seed=3), Matrix.Translation((-13.5, 7.5, 0)) @ Matrix.Rotation(math.radians(20), 4, "Z"))
    else:
        box(bm, (-18, 4, 2.85), (4.4, 3.0, 0.3))                  # 옛 굴 입구의 나무 발판 (높이 3 m)
        for k in range(4): box(bm, (-19.9 + (k % 2) * 3.8, 2.8 + (k // 2) * 2.4, 1.35), (0.25, 0.25, 2.7))
        for s in range(15): box(bm, (-19.4, 2.3 - s * 0.5, 3.0 - (s + 1) * 0.2 + 0.1), (1.2, 0.5, 0.2))   # 벽 따라 내려가는 계단 (3 m 를 7.5 m 에)
        box(bm, (-18.8, -1.2, 2.4), (0.08, 8.1, 0.08), Matrix.Rotation(math.atan2(3, 7.5), 3, "X"))       # 난간
    for x, z, a in ((-14, 7.5, 8), (-6, 9.0, -6), (2, 8.0, 5), (10, 9.5, -4), (16, 7.0, 7)):         # 벽 사이에 걸친 나무 버팀목 (맵에서는 뺀다 — 27 m 통나무의 양 끝이 바위에 안 닿아 떠 있었다)
        if not MAP: box(bm, (x, 0, z), (0.35, 27, 0.35), Matrix.Rotation(math.radians(a), 3, "Y") @ Matrix.Rotation(math.radians(a * 0.4), 3, "X"))
    if bm.verts: box_uv(obj("TIMBER", bm, M_TIMB).data, 0.8)
    if not MAP:
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
    if not MAP:
        for i in range(28): box(bm, (0, 4.4 - i * 0.8, 0.04), (1.4, 0.18, 0.08))    # 레일 침목 (맵: Fab 레일 조각에 침목이 있다)
    box_uv(obj("BOARDS", bm, M_TIMB).data, 0.8)
    bm = bmesh.new()
    for y in (-4.79, 4.79): box(bm, (0, y, 2.9), (16, 0.08, 0.12))   # 케이블 (판자에 붙여서)
    obj("CABLE", bm, M_BLK)
    if not MAP:                                                  # 맵에서는 뺀다 (사용자 10-03 "이 판이 무슨 뜻인지": 반듯한 네모 판 셋이 바닥에서 2~4 cm 떠, 비칠 것이 없는 게임에선 검푸른 민판으로만 보였다) — 젖은 바닥은 바위 사진의 젖음 값으로 (map4_tex.json wet z6)
        bm = bmesh.new()
        for c, s in (((1.5, 3.4), (2.2, 1.4)), ((-3, -1.5), (1.6, 2.4)), ((0.3, -4.2), (1.1, 1.0))): box(bm, (c[0], c[1], 0.02), (s[0], s[1], 0.005))
        obj("PUDDLE", bm, M_WET)                                 # 젖은 바닥 — 전등이 비친다
    bm = bmesh.new()                                           # 레일 둘 (남쪽 운반갱도 → 케이지)
    if MAP: rails((0, 4.4), (0, -20.0), 0.0)                    # 맵: 굴과 같은 Fab 좁은 레일 (상자 레일 둘은 굴 레일과 폭이 달랐다)
    else:
        for x in (-0.45, 0.45): box(bm, (x, -6.5, 0.13), (0.07, 26, 0.1))
        obj("RAIL", bm, M_STEEL)

    bm = bmesh.new()                                           # 케이지: 강철 틀 + 철망 옆면 (수갱 안, 승강장 바닥 높이에 섰다)
    for x in (-1.25, 1.25):
        for y in (5.6, 7.4): box(bm, (x, y, 1.4), (0.12, 0.12, 2.8))
    for z in (0.05, 2.8): box(bm, (0, 6.5, z), (2.6, 1.9, 0.08))
    for i in range(21):
        box(bm, (-1.25, 5.6 + i * 0.09, 1.4), (0.02, 0.02, 2.7)); box(bm, (1.25, 5.6 + i * 0.09, 1.4), (0.02, 0.02, 2.7))
    for k in range(4): box(bm, (0.6 * (k - 1.5), 6.5, 11.5), (0.05, 0.05, 17.4))                 # 케이지를 매단 쇠줄 넷 — 케이지 지붕에서 수갱 위 끝까지 (옛 것: 3.2 m 토막 넷이 층층이 떠 있었다)
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
        box(bm, (-1.8 + i * 0.4, 4.7, 0.012), (0.2, 0.3, 0.012))
    obj("GATE", bm, M_YEL)
    bm = bmesh.new()                                           # 신호벨 상자 · 신호판 (문 오른쪽 벽)
    box(bm, (2.6, 4.75, 1.55), (0.35, 0.18, 0.45)); blob(bm, (2.6, 4.62, 1.88), (0.14, 0.08, 0.14), 2)
    box(bm, (3.9, 4.8, 1.7), (1.1, 0.04, 0.8))
    obj("SIGNAL", bm, M_RED)
    bm = bmesh.new()                                           # 광차 하나 (케이지에 실을 차례)
    if MAP: put("ufmodhpfa", Matrix.Translation((0, -1.5, cart_z("ufmodhpfa"))) @ Matrix.Rotation(math.radians(90), 4, "Z")); CARTS.append((ZT @ Vector((0, -1.5, 0)), "ufmodhpfa"))   # 맵: Fab 빈 광차를 레일 위에 (녹슨 상자 + 공 넷이었다)
    else:
        box(bm, (0, -1.5, 0.75), (1.0, 1.7, 0.9))
        for x in (-0.4, 0.4):
            for y in (-2.1, -0.9): blob(bm, (x, y, 0.22), (0.05, 0.2, 0.2), 1)
        box_uv(obj("CART", bm, M_RUST).data, 1.0)
    bm = bmesh.new()                                           # 전구 둘 (유리갓) — 케이지 앞만 밝다
    for x in (-2.2, 2.2): blob(bm, (x, 4.0, 3.55), (0.12, 0.12, 0.16), 2)
    obj("BULB", bm, M_BULB).visible_shadow = False               # 전구가 제 빛을 가리지 않게
    bm = bmesh.new()
    for x in (-2.2, 2.2): blob(bm, (x, 4.0, 3.72), (0.28, 0.28, 0.1), 2); box(bm, (x, 4.0, 4.2), (0.025, 0.025, 0.9))   # 갓 + 천장까지 줄
    obj("SHADE", bm, M_STEEL).visible_shadow = False
    text("1편", (-4.2, 4.812, 1.5), 1.3, M_PAINT)                 # 층 번호를 벽에 크게 — 어느 층인지 한눈에
    text("케이지 부르기 — 벨", (3.9, 4.812, 2.25), 0.16, paint("white", (0.85, 0.85, 0.8), 0.8))
    text("← 서 운반갱도", (-6.2, 4.812, 3.0), 0.3, M_PAINT); text("동 운반갱도 →", (6.2, 4.812, 3.0), 0.3, M_PAINT)
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
    L, W, H = 24.0, 10.0, 2.45 if MAP else 2.3                  # 쇠동발 구역 24 × 10 m, 천장 2.3 (가운데 널빤지 길) — 양옆은 조금 낮다 (맵: 어디나 2.35 m 넘게)
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
    if MAP and fid in SIDE_TALL:                                                      # 맵: 나무 버팀 조각을 위로 늘인다 (갓목 밑 2.06 → 2.35 m — 레일 · 판자 위에 서면 1.95 m 선에 걸려 저절로 숙여졌다)
        for o in new: o.data.transform(Matrix.Diagonal((1, 1, SIDE_Z, 1)))
    if fid in CART:                                                                   # 광차: 바퀴 사이를 레일 폭(GAUGE)에 맞게 통째로 키우거나 줄인다 (놓는 높이는 cart_z)
        s_ = GAUGE / CART[fid][0]
        for o in new: o.data.transform(Matrix.Scale(s_, 4))
        cw = np.array([v.co[:] for o in new for v in o.data.vertices]); xm = (cw[:, 0].min() + cw[:, 0].max()) / 2; ym = np.median(cw[:, 1])
        low = cw[(cw[:, 2] < cw[:, 2].min() + 0.14) & (np.abs(cw[:, 1] - ym) > 0.12) & (np.abs(cw[:, 0] - xm) < np.ptp(cw[:, 0]) * 0.375)]   # 바퀴 밑동 (가운데 고리 · 끝 연결쇠는 뺀다)
        yw = (low[:, 1].min() + low[:, 1].max()) / 2
        for o in new: o.data.transform(Matrix.Translation((0, -yw, -cw[:, 2].min())))   # 바퀴 가운데 = y 0 · 모델 맨 밑 = z 0 (Fab 광차는 바퀴가 몸통 가운데에서 몇 cm 비켜 있고 원점이 맨 밑보다 3.6 cm 높다 — 바퀴 테가 레일 머리를 파고들었다, 검사 map4_carts_on_rails)
    co = np.array([v.co[:] for o in new for v in o.data.vertices])
    if rails:                                                                         # 레일을 좁은 궤간으로: 레일 + 받침쇠는 폭 0.7 배로 안쪽에, 침목 가운데는 그만큼 줄인다 (높이 · 길이는 그대로)
        ym = (co[:, 1].min() + co[:, 1].max()) / 2; top = co[co[:, 2] > co[:, 2].max() - 0.01]; c = np.abs(top[:, 1] - ym).mean(); edge = c - 0.21
        for o in new:
            for v in o.data.vertices:
                a = abs(v.co.y - ym); v.co.y = ym + math.copysign(GAUGE / 2 + (a - c) * 0.7 if a > edge else a * (GAUGE / 2 - 0.147) / edge, v.co.y - ym)
            o.data.update()
        co = np.array([v.co[:] for o in new for v in o.data.vertices])
        print("CHECK rail %s gauge %.3f -> %.3f m (rail head centres), sleeper %.2f m, rail top %.3f" % (fid, 2 * c, GAUGE, np.ptp(co[:, 1]), co[:, 2].max() - co[:, 2].min()))
    off = Vector(at) - Vector(((co[:, 0].min() + co[:, 0].max()) / 2, 0.0 if fid in CART else (co[:, 1].min() + co[:, 1].max()) / 2, co[:, 2].min()))
    for o in new: o.location = off
    return new, co.min(axis=0) + np.array(off), co.max(axis=0) + np.array(off)
FABMAT = {}
HEAP_MAT = {}                                                         # 돌 · 석탄 더미 둔덕의 겉 재질 (map4() 가 채운다)
SIDE_TALL, SIDE_Z = ("wcbpdfsdw", "wcbpdgcdw"), 1.14                  # Fab 나무 버팀 굴 조각 · 맵에서 위로 늘이는 배율 (바깥 높이 2.36 → 2.69 m, 곁갱도 공기 2.8 m 안)
# 레일 · 광차 (사용자 10-02 "광차와 레일이 간격이 맞지 않다 — 바퀴가 레일 길에 안 맞음"). 잰 값(Blender, 10-02): Fab 레일 ufekaeedw 는 레일 머리 가운데 사이 1.525 m(표준궤),
# 광차 바퀴 디딤면 가운데 사이는 작은 것 0.54 m · 큰 것 0.765 m — 레일이 2~2.8 배 넓었고, 광차를 바닥 위 0.12 m 에 놓아 바퀴가 레일 머리(0.217 m)보다 낮게 떠 있었다.
GAUGE = 0.65                                                         # 레일 머리 가운데 사이 (m) — 두 광차 폭의 가운데 값 (작은 것 × 1.2 · 큰 것 × 0.85). Fab 좁은 선로 판 wcskfaidw 도 0.65
RAIL_TOP = 0.217                                                     # 레일 머리 윗면 (바닥 위 m)
CART = {"ufmodhpfa": (0.54, 0.018), "ujzhahdfa": (0.54, 0.018), "ueujednfa": (0.765, 0.063)}   # 광차 → (바퀴 디딤면 가운데 사이, 디딤면 높이 — 모델 맨 밑에서)
def cart_z(fid): return RAIL_TOP - CART[fid][1] * GAUGE / CART[fid][0]   # 광차를 놓는 높이 (바닥 위) = 바퀴 디딤면이 레일 머리에 닿게
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
    bm = bmesh.new()
    if MAP:                                                           # 맵: 1 m 칸 한 겹 (윗면 z = 0) — TEX-1 이 점마다 사진 · 이음 자리를 적는다 (상자 모서리 여덟 점으로는 판 가운데의 경계를 못 적는다)
        g = bmesh.ops.create_grid(bm, x_segments=int(x1 - x0), y_segments=7, size=0.5)   # 딱 장면 길이만 (끝에서 1 m 씩 더 나가 방 공기 속에 0.5 m 떠 있었다 — 사용자 10-02 캡처 1 · 2)
        for v in g["verts"]: v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), v.co.y * 7, 0.0))
    else: box(bm, ((x0 + x1) / 2, 0, -0.02), (x1 - x0 + 2, 7, 0.04))
    fl = obj("FLOOR", bm, M_FLOOR); box_uv(fl.data, 0.35)
    if os.path.isdir(CG): fl.data.materials[0] = tex_mat(CG, 2.0)

def rail_run(x0, x1, y=0.0):
    rx = x0
    while rx < x1 - 1:                                              # 레일 조각을 잇는다
        objs, lo, hi = fab("ufekaeedw", (rx, y, 0), rails=True); L = hi[0] - lo[0]
        for o in objs: o.location.x += L / 2
        rx += L

def wall_pipe(x0, x1, z=2.3, ends=(True, True)):
    """우리 관: 굴을 따라 끊김 없이 한 줄 (벽을 광선으로 재서 붙인다) — 나중에 REP 배수관(고칠 곳)과 같은 관"""
    deps = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = sc.ray_cast(deps, Vector(((x0 + x1) / 2, 0, z)), Vector((0, 1, 0)), distance=6)
    py = (loc.y if hit else 2.0) - 0.28
    # 맵: 펌프 관과 같은 붉은 녹막이 칠 (옛 것은 더 밝은 주황 한 색 — 사용자 10-03 캡처 5 "파이프는 왜 넣은 건지": 바로 밑에서 보면 주황 원뿔 같았다). 양 끝은 벽 속으로 꺾어 넣는다 (ends) — 허공에서 뚜껑으로 끝나 있었다
    M_PIPE = PMATS["steel_red"] if MAP and PMATS else paint("pipe", (0.5, 0.07, 0.04), 0.55, 0.4)
    bm = bmesh.new(); RY = Matrix.Rotation(math.radians(90), 3, "Y"); RX = Matrix.Rotation(math.radians(90), 3, "X")
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.08, radius2=0.08, depth=x1 - x0)
    for v in g["verts"]: v.co = RY @ v.co + Vector(((x0 + x1) / 2, py, z))
    if MAP:
        for xe, on in zip((x0, x1), ends):
            if not on: continue
            g = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.088)                       # 굽은 이음
            for v in g["verts"]: v.co = v.co + Vector((xe, py, z))
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.08, radius2=0.08, depth=0.6)   # 벽 속으로 0.3 m
            for v in g["verts"]: v.co = RX @ v.co + Vector((xe, py + 0.3, z))
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.14, radius2=0.14, depth=0.04)  # 벽에 댄 둥근 판
            for v in g["verts"]: v.co = RX @ v.co + Vector((xe, py + 0.25, z))
    fx = x0 + 1.5
    while fx < x1 - (0.6 if MAP else 0.0):                           # 3 m 마다 이음 쇠테(플랜지) + 벽에 거는 걸쇠 (맵: 마지막 걸쇠가 관 끝을 0.26 m 지나 벽에 혼자 붙어 있었다)
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.13, radius2=0.13, depth=0.05)
        for v in g["verts"]: v.co = RY @ v.co + Vector((fx, py, z))
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
    fab("ueujednfa", (cx, 0, cart_z("ueujednfa")), along=True)       # 석탄 실은 광차 (슈트 아래)
    fab("ufmodhpfa", (cx + 2.5, 0, cart_z("ufmodhpfa")), along=True) # 빈 광차 둘 (앞 · 뒤)
    fab("ufmodhpfa", (cx - 2.4, 0, cart_z("ufmodhpfa")), along=True)
    fab("ujzhahdfa", (cx - 7.5, 0, cart_z("ujzhahdfa")), along=True) # 통나무 실은 광차 — 더 뒤에
    if MAP and PMATS:                                                # 맵: 홈통을 사진대로 다시 지은 것 (props/chute.py — 광차 줄 위로 내민 쇠 호퍼 입 + 틀 + 문 + 공기 손잡이). 사용자 10-03 "광차 싣는 곳의 용도가 무엇인지":
        deps = bpy.context.evaluated_depsgraph_get()                 #   옛 것은 벽에 붙은 납작한 회색 판 넷이었고 굴 덧댐을 그냥 뚫고 들어갔다. 굴 벽 · 꼭대기는 광선으로 잰다
        hit, wl, *_ = sc.ray_cast(deps, Vector((cx, 0, 2.0)), Vector((0, -1, 0)), distance=6); wd = abs(wl.y) if hit else 2.2
        hit, rf, *_ = sc.ray_cast(deps, Vector((cx, 0, 2.2)), Vector((0, 0, 1)), distance=6); crown = rf.z if hit else 3.6
        co = PU.place(chute.build(PMATS, wall_d=wd, roof_h=crown, side=1, pouring=False, seed=1), Matrix.Translation((cx, 0, 0)) @ Matrix.Rotation(math.radians(180), 4, "Z"))   # 반 바퀴 돌려 벽이 −y · 손잡이가 펌프실에서 오는 쪽
        for o in co:                                                 # 홈통 속 · 입 · 바닥에 흘린 석탄은 맵의 석탄 재질로 (가루 = 둔덕 사진, 덩이 = 석탄 덩이 사진)
            if "COAL" in o.name and HEAP_MAT: o.data.materials[0] = HEAP_MAT["coal"] if "black" in o.name else lib("coal")[0][0].data.materials[0]
        print("CHECK scene3 chute: lining %.2f m from the track centre at 2 m, crown %.2f m" % (wd, crown))
    else:
        bm = bmesh.new()                                             # 슈트: 벽 위에서 비스듬히 내려오는 쇠 홈통 + 문 + 손잡이
        tilt = Matrix.Rotation(math.radians(-38), 3, "X")
        box(bm, (cx, -1.35, 2.75), (1.0, 2.2, 0.08), tilt)            # 바닥판
        for sx in (-0.5, 0.5): box(bm, (cx + sx, -1.35, 3.0), (0.06, 2.2, 0.55), tilt)   # 옆판
        box(bm, (cx, -0.55, 1.95), (1.05, 0.06, 0.55))               # 문 (올리면 쏟아진다)
        box(bm, (cx + 0.7, -0.6, 1.6), (0.05, 0.05, 0.9), Matrix.Rotation(math.radians(20), 3, "Y"))   # 손잡이
        box(bm, (cx, -2.2, 3.6), (1.1, 0.8, 1.0))                    # 벽 속으로 들어가는 목 (위 채탄장에서 내려온다)
        box_uv(obj("CHUTE", bm, M_RUST).data, 1.0)                 # 녹슨 쇠
        bm = bmesh.new()                                             # 흘린 석탄 부스러기
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

DOOR_W, DOOR_H, BOARD_T = 1.6, 2.35 if MAP else 2.0, 0.05            # 문 = 광차가 지나는 두 짝 (독일 사진) · 판자 두께. 맵: 문틀 머리 밑 2.35 m (사용자 10-02 "풍문으로 들어갈 때 자동 숙임" — 2.0 m 머리 밑에 침목 0.09 · 레일 0.22 m 가 깔려 1.95 m 선에 걸렸다)
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
    text("풍문", (xa - BOARD_T / 2 - 0.01, 0, DOOR_H + (0.32 if MAP else 0.4)), 0.5 if MAP else 0.6, M_PAINT, face(1))                       # 앞문 (오는 쪽)
    text("항상 닫을 것", (xa - BOARD_T / 2 - 0.01, -(fw + 0.8), 1.55), 0.22, M_PAINT, face(1))
    text("반대쪽 문을\n닫고 여시오", (xb - BOARD_T / 2 - 0.01, -(fw + 0.8), 1.2), 0.2, M_PAINT, face(1))   # 두 문 사이 — 뒷문 옆 (가로대 사이)
    text("반대쪽 문을\n닫고 여시오", (xa + BOARD_T / 2 + 0.01, fw + 0.8, 1.2), 0.2, M_PAINT, face(-1))      # 두 문 사이 — 앞문 옆 (돌아볼 때)
    bm = bmesh.new()                                                  # 긁힌 자국 — 뒷문 옆 판자 (괴물은 문을 긁는다, 제안서 3-1)
    for k in range(4): box(bm, (xb - BOARD_T / 2 - 0.005, fw + 0.4 + k * 0.1, 1.95 - k * 0.04), (0.01, 0.04, 0.85), Matrix.Rotation(math.radians(22), 3, "X"))
    obj("GOUGE", bm, M_BLK)
    wall_pipe(0, xb, ends=(True, False))                              # 관은 앞문 벽을 뚫고 뒷문 벽에서 끝난다 (승강장 쪽 끝은 벽 속으로)
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
    ht = 2.1 + (0.3 if MAP else 0.0)                                                   # 맵 모드: 처진 갓목 밑도 2.15 m 넘게 (저절로 숙이지 않게 — 1.95 m 선 + 바닥 판자 · 돌)
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
    fz = 0.0 if MAP else -0.3                                                               # 맵: 바위 바닥 = 0 (바닥 판 밑이 0.3 m 비어 판 끝이 떠 보였다) · 무너진 구간 천장은 높인 동발 위로
    box(bm, (tun / 2, 0, (fz + 2.7) / 2), (tun + 2, 4.2, 2.7 - fz))
    box(bm, (a1 + 4.1, 0, (fz + (2.85 if MAP else 2.545)) / 2), (8.6, 2.7, (2.85 if MAP else 2.545) - fz))
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
    if MAP: beam(bm, (x + 0.1, 0.4, 1.0), (x + 0.45, 1.15, 0.6), 0.22, 0.22)              #   갓목은 부러져 돌 더미 위에 누웠다 (맵: 걷는 쪽(왼) 머리 위를 가로지르지 않게 — 그 밑이 1.6~1.7 m 라 선 채로 못 지났다)
    else: beam(bm, (x + 0.1, -1.2, 2.2), (x + 0.45, 0.9, 0.95), 0.22, 0.22)                 #   갓목은 돌 더미 위로 떨어지고
    beam(bm, (x - 0.7, 0.75, 0.12), (x + 1.1, 0.95, 0.12))                                  #   오른 다리는 바닥에 누움
    square_set(bm, xs[5], lean=-0.1, sag=0.1); square_set(bm, xs[6], lean=-0.04)
    for a, b in ((0, 1), (5, 6)):                                                           # 동발 위 덧댄 판자 (멀쩡한 곳만)
        for y in (-0.8, -0.4, 0.0, 0.4, 0.8): beam(bm, (xs[a] - 0.2, y, 2.36 + (0.3 if MAP else 0)), (xs[b] + 0.25, y, 2.36 + (0.3 if MAP else 0)), 0.18, 0.04)
    hy = 0.6 if MAP else 0.0                                                                # 맵: 늘어진 판자 · 돌 더미를 오른쪽(굴 벽 쪽)으로 — 왼쪽 1.1 m 를 선 채로 지난다
    beam(bm, (xs[3] + 0.2, -0.3 + hy, 2.36 + (0.3 if MAP else 0)), (xs[3] + 0.95, -0.15 + hy, 1.55), 0.18, 0.04)   # 구멍에서 늘어진 부러진 판자
    beam(bm, (xs[3] + 0.3, 0.35 + hy, 2.36 + (0.3 if MAP else 0)), (xs[3] + 0.8, 0.5 + hy, 1.8), 0.18, 0.04)
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
    fab_many("vmhdagb", [(xs[3] + 0.5, 0.45 + (0.35 if MAP else 0), 0.0, 30, 1.0)])         # 흙 더미 + 떨어진 돌 (Fab 스캔 돌 9 cm × 5~12 배)
    fab_many("wd3efb0", rock_pile(xs[3] + 0.5, 0.75 if MAP else 0.55, 1.5, 0.5 if MAP else 0.7, 1.0, 80, 3, 8))
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
    fz = 0.0 if MAP else -0.3                                                               # 맵: 바위 바닥 = 0
    box(bm, (a1 / 2, 0, (fz + 2.7) / 2), (a1 + 2, 4.2, 2.7 - fz))                           # Fab 조각 뒤 바위
    c1, c2 = (1.35, 1.1) if not MAP else (LOWEST + 0.1, LOWEST)                             # 천장 (+ 울퉁불퉁 0~0.3) — 맵 모드는 선 채로 (사용자 10-01)
    box(bm, (a1 + L * 0.3, 0, (c1 + fz) / 2), (L * 0.6 + 0.3, W, c1 - fz))                   # 막장 앞쪽
    box(bm, (a1 + L * 0.8, 0, (c2 + fz) / 2), (L * 0.4, W - 0.6, c2 - fz))                   # 안쪽 — 막장 벽으로 갈수록 낮다
    if MAP:                                                                                 # 맵: 막장 끝 벽이 반듯한 상자 면이었다 (사용자 10-03 "막장이라고 보이지 않는다") — 캐낸 자국: 들쭉날쭉 파인 곳 둘 + 발치의 가로 홈(밑파기, 조사 12 Rw04 · Rw13)
        blob(bm, (tun + 0.1, -1.1, 1.25), (0.9, 1.5, 1.05), 2); blob(bm, (tun + 0.25, 1.5, 1.45), (0.85, 1.2, 0.85), 2); box(bm, (tun + 0.3, 0.2, 0.28), (0.75, 4.4, 0.55))
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
            zc = min(roof(px, ry) for px in seg + [min(x + 2.4, tun - 0.4)]) - 0.12         # 갓목 가운데 높이 (통나무 반지름 약 0.1 + 틈). 끝 묶음은 막장 벽 안쪽에서 잰다 — x + 2.4 가 벽 너머(21.07 > 20.87)라 광선이 빗나가 높이 0 이 되고,
            assert zc > 1.0, "scene2 timber group at x %.2f got roof %.2f" % (x, zc)         #   막장 앞 2.4 m 의 기둥 여덟 · 갓목 넷이 배율 −0.14 로 바닥 속에 묻혔다 (10-03 조사: 사용자가 본 '아무것도 없는 막장 끝')
            caps.append((x - 0.2, ry, zc, 0, 0.98, (0, 90)))                                # 눕힌 통나무 (Y 로 90° → 긴 쪽이 +X)
            for px in seg:
                zs = (zc - 0.1) / 1.61                                                      # 맵: 키만 늘인다 (통째로 1.4~1.5 배 키워 굵기 0.35 m 넘는 통나무가 됐다 — 캡처 8 의 오른쪽 '주황 바위')
                pr = (px + random.uniform(-0.12, 0.12), ry + random.uniform(-0.22, 0.22), 0.0, random.uniform(0, 360), (1.05, 1.05, zs) if MAP else zs, (random.uniform(-5, 5), random.uniform(-5, 5)))
                way = [Vector((a1 + 9 - 5.865, 0, 0)), Vector((a1 + 14 - 5.865, 2.2, 0)), Vector((a1 + 15 - 5.865, 3.0, 0))]   # 맵: 옛 채굴 빈터로 빠지는 길(뒤 구멍) 위의 기둥은 뺀다 — 기둥 사이 0.75 m 로는 몸(0.8 m)이 못 지났다 (걷기 검사)
                near = MAP and any(((Vector((pr[0], pr[1], 0)) - a_) - (b_ - a_) * max(0.0, min(1.0, (Vector((pr[0], pr[1], 0)) - a_).dot(b_ - a_) / (b_ - a_).length_squared))).length < 0.8 for a_, b_ in zip(way, way[1:]))
                if not near: props.append(pr)
            x += 2.4
    for fid in ("tgnidj2fa", "tgmrafyfa"): FABMAT[fid] = tint(tex_mat(os.path.join(FABDIR, fid), 1 / 0.35), (0.27, 0.24, 0.21) if MAP else (0.5, 0.44, 0.38), fid + "_dust")   # 석탄 가루 앉은 나무 (스캔 나무가 희다)
    fab_many("tgnidj2fa", props)                                                            # Fab 나무 기둥 1.61 m (조금씩 기울게)
    fab_many("tgmrafyfa", caps)                                                             # Fab 나무 기둥 2.56 m 를 눕혀 갓목으로
    FABMAT["wd3efb0"] = tint(tex_mat(os.path.join(FABDIR, "wd3efb0"), 1 / 0.35), (0.09, 0.09, 0.1), "coal_lump")   # 캘 석탄 = 막장 발치에 깨진 석탄 더미 (스캔 돌을 검게)
    cb = next(n for n in FABMAT["wd3efb0"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")   # 스캔 돌의 반들거림이 빛을 되쏴 회색으로 보인다 — 덜 반들거리게
    for l in list(cb.inputs["Roughness"].links): FABMAT["wd3efb0"].node_tree.links.remove(l)
    cb.inputs["Roughness"].default_value = 0.55; cb.inputs["Specular IOR Level"].default_value = 0.25
    if MAP:                                                                                 # 맵: 막장 벽 발치를 따라 길게 누운 석탄 둔덕(가루) + 그 겉에 묻힌 덩이. 옛 것은 덩이 높이를 난수로 줘 떠 있는 것이 있었고, 폭이 ±1.15 m 로 묶여(곁갱도용 값) 5.4 m 막장 벽에 2.3 m 띠만 깔렸다
        hx, hy, hh = 1.5, 2.55, 0.45; top = lambda x, y: hh * math.sqrt(max(0.0, 1 - ((x - (tun - 0.35)) / hx) ** 2 - (y / hy) ** 2))
        bm = bmesh.new(); g = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        for v in g["verts"]: v.co = Vector((tun - 0.35 + v.co.x * hx * (1 + 0.1 * math.sin(v.co.y * 9)), v.co.y * hy, max(v.co.z, -0.2) * hh * (1 + 0.12 * math.sin(v.co.x * 7 + v.co.y * 5))))
        mo = obj("HEAP_face_z2", bm, HEAP_MAT["coal"]); mo.data.polygons.foreach_set("use_smooth", np.ones(len(mo.data.polygons), dtype=bool)); box_uv(mo.data, 0.8)
        spots = []
        for _ in range(110):
            a, r = random.uniform(0, 2 * math.pi), math.sqrt(random.random()) * random.choice((1.0, 1.0, 1.0, 1.25)); x, y = tun - 0.35 + math.cos(a) * r * hx, math.sin(a) * r * hy; s_ = random.uniform(2, 6)
            if x < tun + 0.3: spots.append((x, y, max(0.0, top(x, y) - 0.0694 * s_ * 0.35), random.uniform(0, 360), s_))
        fab_many("wd3efb0", spots)
    else: fab_many("wd3efb0", rock_pile(tun - 0.9, 0.0, 0.8, 2.6, 0.55, 110, 2, 6) + rock_pile(tun - 3.0, -2.5, 0.9, 0.4, 0.4, 25, 2, 5))
    if not MAP:                                                                             # 맵: 호스는 map4() 의 "막장 연장" 이 곁굴 벽의 압축공기 관 밸브 → 착암기로 잇는다 (사용자 10-03 판정 ③ "막장의 디테일 부족" — 이 호스는 양 끝이 바닥에서 뚝 끊겨 있었다)
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
            sv = Vector(s_) if isinstance(s_, (tuple, list)) else Vector((s_, s_, s_))   # 배율 하나 또는 (x, y, z) — 기둥을 굵어지지 않게 키만 늘일 때
            c.rotation_euler = e; c.scale = sv
            c.location = Vector((x, y, z)) + e.to_matrix() @ Vector((off.x * sv.x, off.y * sv.y, off.z * sv.z))
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
# 운반갱도 바위 공기의 단면 (y, 높이) — Fab 강철 아치 겉(바닥 폭 5.3 m · 꼭대기 3.77 m)보다 0.25 m 쯤 넓게. 네모(6.4 × 4.1)로 파면 아치 옆 · 위에 0.7~1.9 m 빈 곳이 생겨
# 방에서 보면 아치가 바위와 떨어져 서 있었다 (사용자 10-02 "맵과 이어지지 않고 떠 있음")
HAUL_PROFILE = [(-2.9, 0.0), (2.9, 0.0), (2.9, 0.6), (2.45, 2.0), (1.75, 3.0), (1.0, 3.6), (0.4, 3.95), (-0.4, 3.95), (-1.0, 3.6), (-1.75, 3.0), (-2.45, 2.0), (-2.9, 0.6)]
def arch_air(bm, x0, x1, z=0.0):
    a = [bm.verts.new((x0, y, z + h)) for y, h in HAUL_PROFILE]; b = [bm.verts.new((x1, y, z + h)) for y, h in HAUL_PROFILE]; n = len(a)
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
RUNS, TRACKS, CARTS = [], [], []                                           # 맵에 놓은 Fab 굴 줄 (틀, 길이, 종류) · 레일 줄 (시작, 끝) · 광차 (자리, 종류, 넘어진 것인가)

def lib(fid, key=None, mat=None, **kw):
    """Fab 모델을 한 번만 불러와 장면에서 빼 둔다 — 놓을 때는 그물을 나눠 쓰는 복사본 (GLB 에도 그물은 한 번만). key · mat = 같은 모델을 다른 재질로 (돌 → 바위 · 석탄)"""
    key = key or fid
    if key not in LIB:
        objs, lo, hi = fab(fid, (0, 0, 0), **kw)
        for o in objs:
            if mat is not None: o.data = o.data.copy(); o.data.materials.clear(); o.data.materials.append(mat)
            o.location = (0, 0, 0); sc.collection.objects.unlink(o)                   # 그물 좌표 그대로 둔다 (Fab 원점 — 광차 · 전등 · 돌은 가운데 밑, 굴 조각 · 레일은 한쪽 끝)
        co = np.array([v.co[:] for o in objs for v in o.data.vertices])
        LIB[key] = (objs, hi[0] - lo[0], (co[:, 0].min(), (co[:, 1].min() + co[:, 1].max()) / 2, co[:, 2].min()))   # (물체, 길이, 그물의 (시작 x, 가운데 y, 밑 z))
    return LIB[key]

def put(key, M):
    objs = lib(key)[0]; out = []
    for o in objs:
        c = o.copy(); sc.collection.objects.link(c); c.matrix_world = M; out.append(c)
    return out

def frame(a, b, z=0.0):
    """a → b 굴의 틀: 원점 a (높이 z), X = 굴 방향. (틀, 길이)"""
    d = Vector((b[0] - a[0], b[1] - a[1], 0)); return Matrix.Translation((a[0], a[1], z)) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z"), d.length

def run(kind, a, b, z=0.0):
    """a → b 사이를 Fab 조각으로 잇는다 — 조각 수를 반올림하고 길이 방향만 늘이거나 줄여 딱 맞춘다"""
    F, L = frame(a, b, z); ids = FAB_RUN[kind]; lens = [lib(i)[1] for i in ids]
    n = max(1, round(L / (sum(lens) / len(lens)))); seq = [ids[k % len(ids)] for k in range(n)]
    k = L / sum(lib(i)[1] for i in seq); x = 0.0
    for fid in seq:                                                                           # 조각의 시작 끝을 x 에 (Fab 굴 조각은 원점이 한쪽 끝이다 — 가운데로 치고 놓아 반 조각씩 밀려 있었다: 빈 틈 2.4 m · 방 속으로 1.8 m, 10-02 잼)
        x0, yc, z0 = lib(fid)[2]; l = lib(fid)[1] * k; put(fid, F @ Matrix.Translation((x - x0 * k, -yc, -z0)) @ Matrix.Diagonal((k, 1, 1, 1))); x += l
    RUNS.append((F, L, kind))

def rails(a, b, z=0.0, y=0.0):
    F, L = frame(a, b, z); pl = lib("rail")[1]; x0, yc, z0 = lib("rail")[2]; n = max(1, round(L / pl)); k = L / (n * pl)
    for i in range(n): put("rail", F @ Matrix.Translation((i * pl * k - x0 * k, y - yc, -z0)) @ Matrix.Diagonal((k, 1, 1, 1)))
    TRACKS.append((F @ Vector((0, y, 0)), F @ Vector((L, y, 0))))                              # 레일 줄 (시작, 끝) — 광차가 레일 위에 있나 재는 데 쓴다

LAMP_H = 2.8                                                             # 전등 빛 높이 (바닥 위) = 판정 받은 운반갱도 전등 높이. 게임 전등 빛은 4 m(FAB_LIGHT_RANGE)까지라 4~5.5 m 천장에 붙이면 천장만 밝힌다 (v2 "전체가 많이 어둡다")
CORDS = []                                                               # 높은 천장에서 전등까지 늘어뜨린 줄 (가운데, 크기)
LAMP_WALL = 2.0                                                          # 방 가장자리 전등과 벽 사이 (m)
def lamp_at(x, y, z, top_guess, name, energy=120, col=(1.0, 0.62, 0.3)):
    """철망 갓 전등을 천장 밑에 단다 (천장은 광선으로 잰다) — 천장이 높으면 줄에 매달아 LAMP_H 까지 내린다. 게임에서 LAMP_ = 판정값 빛(Tuning.FAB_*), ZL_<색> = 구역 색 등"""
    deps = bpy.context.evaluated_depsgraph_get(); o_ = Vector((x, y, z + 1.6))
    for _ in range(4):                                                                        # 천장 = 바위나 굴 조각. 소품(눈금판 · 표지 · 다른 전등)에 맞으면 그 위에서 다시 쏜다 (출입 금지 앞 붉은 등이 눈금판 밑 1.57 m 에 매달렸다)
        hit, loc, _, _, ob, _ = sc.ray_cast(deps, o_, Vector((0, 0, 1)), distance=12)
        if not hit or ob.name.startswith(("SHELL", "CAVE", "wdpn", "wcbp")): break
        o_ = loc + Vector((0, 0, 0.05))
    top = loc.z if hit else z + top_guess; lz = min(top - 0.45, z + LAMP_H); put("vgyidfpaw", Matrix.Translation((x, y, lz + 0.2)))
    if top - lz > 0.3: CORDS.append(((x, y, (top + lz + 0.35) / 2), (0.014, 0.014, top - lz - 0.05)))   # 줄 끝은 바위 속 0.15 m (울퉁불퉁한 천장에 떠 보이지 않게)
    LIGHTS.append((name % len(LIGHTS) if "%d" in name else name, (x, y, lz), energy, col, 0.08, True))

def lamp_grid(n, nx, ny, name, move=None, **kw):
    """방을 nx × ny 칸으로 나눠 칸마다 전등 하나. 전등 높이에 뭔가(돌 더미 · 석탄 기둥 · 통나무)가 있으면 옆으로 비킨다. move = {(ix, iy): (x, y)} 그 칸 전등을 정한 자리에"""
    deps = bpy.context.evaluated_depsgraph_get()
    for ix in range(nx):
        for iy in range(ny):
            if move and (ix, iy) in move: lamp_at(*move[(ix, iy)], n["z"], n["h"], name, **kw); continue
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
    box(bm, (p.x - 0.4, p.y, z + (LAMP_H + 0.6) / 2), (0.09, 0.09, LAMP_H + 0.6)); box(bm, (p.x - 0.2, p.y, z + LAMP_H + 0.28), (0.5, 0.06, 0.06)); box(bm, (p.x - 0.4, p.y, z + 0.04), (0.5, 0.5, 0.08))
    put("vgyidfpaw", Matrix.Translation((p.x, p.y, z + LAMP_H + 0.2))); LIGHTS.append((name % len(LIGHTS), (p.x, p.y, z + LAMP_H), energy, col, 0.08, True))   # 전등 머리가 팔에 닿게 (6 cm 떠 있었다)

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

def steel_props(a, b, z=0.0, step=1.0):
    """쇠동발 길: Fab 늘어나는 쇠동발 두 줄 (시안 ① 의 은색 숲). 기둥마다 바닥 · 천장을 재서 천장 밑까지 늘이고 머리 위에 나무 받침을 끼운다 (시안 ① 과 같은 법).
    사용자 10-03 "저탄장 가는 길목에 이 구조물이 있는 이유는": 옛 것은 키를 0.9 배(2.3 m)로 고정해 2.8~3.1 m 천장 밑 0.5~0.8 m 허공에서 끝났고 머리에 아무것도 없었다 — 아무것도 안 받치는 기둥.
    레퍼런스(R08 유압동발 · R05): 쇠기둥 머리와 천장 사이에 나무 받침 토막, 그 위로 천장 널. 간격은 1 m (단단한 곳 1 m — 조사 11)"""
    F, L = frame(a, b, z); x = 0.8; deps = bpy.context.evaluated_depsgraph_get(); done = 0; short = []
    co_ = np.array([v.co[:] for o in lib("ugfmehgfa")[0] for v in o.data.vertices]); h_nat = co_[:, 2].max()   # 모델 원점 = 발 (0 ~ 2.55 m)
    while x < L - 0.5:
        for yy in (-1.5, 1.5):
            p = F @ Vector((x + random.uniform(-0.1, 0.1), yy + random.uniform(-0.1, 0.1), 0))
            hit, fl, *_ = sc.ray_cast(deps, p + Vector((0, 0, 1.2)), Vector((0, 0, -1)), distance=3.0); fz = fl.z if hit else p.z
            hit, rf, _, _, ob, _ = sc.ray_cast(deps, Vector((p.x, p.y, fz + 0.6)), Vector((0, 0, 1)), distance=6.0); top = rf.z if hit else fz + 2.8
            if top - fz < 2.0 or top - fz > 3.7: short.append("%.2f" % (top - fz)); continue                 # 못 세울 높이 (없어야 한다)
            yaw = random.uniform(0, 6.28)
            put("ugfmehgfa", Matrix.Translation((p.x, p.y, fz - 0.02)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((1, 1, (top - fz - 0.165 + 0.02) / h_nat, 1)))
            PU.place(timber_sets.head_block(PMATS, seed=done), Matrix.Translation((p.x, p.y, top - 0.165)) @ Matrix.Rotation(yaw, 4, "Z")); done += 1   # 머리 토막 맨 위(0.165 m)가 천장에 닿는다
        x += step
    print("CHECK map4 steel props %d on a %.1f m run, each from floor to a head block under the roof · skipped %d%s" % (done, L, len(short), (" (" + " ".join(short) + ")") if short else ""))

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
            z -= sz * 0.86; text(body, tuple(Vector((C.x, C.y, z)) + face * 0.032), sz, mt[0] if mt else M_SIGNTEXT_, (math.radians(90), 0, math.atan2(face.x, -face.y))).name = "NOCOL_SIGNTEXT"; z -= sz * 0.26   # 글자도 부딪힘 없음 (판 밑 글자가 머리에 걸려 저절로 숙여졌다)
    return C, w, hb
SIGN_Z = 2.15                                                            # 표지 판 밑 높이 (m) — 저절로 숙이는 높이 1.95 m 위

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
    for b_, carve, big in sorted(AIR, key=lambda a_: -a_[1]):                          # 장면 방의 파는 깊이 (⑨ 0.45 · ⑥ ① 0.25 …) — 그 공기 상자 안의 점에. 얕은 것을 나중에 (문 칸 0.05 가 방 0.45 를 이긴다 — 문틀 옆 바위가 물러나면 문이 벽에서 뜬다)
        if abs(carve - 0.3) < 1e-6: continue
        vs = np.array([v.co[:] for v in b_.verts]); lo, hi = vs.min(0) - 0.5, vs.max(0) + 0.5
        depth[np.all((co >= lo) & (co <= hi), axis=1)] = carve
    w = np.round(np.where(nz > 0.6, 0.1, 1.0) * depth / 0.6, 2)
    vg = cave.vertex_groups.new(name="carve")
    for v in np.unique(w): vg.add(np.nonzero(w == v)[0].tolist(), float(v), "REPLACE")
    tex = bpy.data.textures.new("rocknoise", type="CLOUDS"); tex.noise_scale = 1.6; tex.noise_depth = 3
    dm = cave.modifiers.new("carve", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"; dm.strength = 0.6; dm.mid_level = 1.0; dm.direction = "NORMAL"; dm.vertex_group = "carve"
    if os.environ.get("SAB") == "tear":                                                # 사보타주: 옛 방식 되살림 — 겉면을 만든 뒤 큰 빈터 벽을 1.6 m 민다 → CHECK map4 shell torn 이 떨어져야 한다
        z9 = Vector((125, -66, 0)); sel = (np.abs(co[:, 0] - z9.x) < 15) & (np.abs(co[:, 1] - z9.y) < 22) & (nz <= 0.6) & (co[:, 2] > 0.4)
        vg2 = cave.vertex_groups.new(name="big"); vg2.add(np.nonzero(sel)[0].tolist(), 1.0, "REPLACE")
        tex2 = bpy.data.textures.new("bignoise2", type="CLOUDS"); tex2.noise_scale = 5.0; tex2.noise_depth = 2
        dm2 = cave.modifiers.new("carve_big", "DISPLACE"); dm2.texture = tex2; dm2.texture_coords = "GLOBAL"; dm2.strength = 1.6; dm2.mid_level = 1.0; dm2.direction = "NORMAL"; dm2.vertex_group = "big"
    me = bpy.data.meshes.new_from_object(cave.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(cave, do_unlink=True)
    me.materials.clear()                                                               # 재질 칸 · UV 는 tex1_paint() 가 적는다 (TEX-1). 여기서 옛 부스 바위가 0번 칸에 남아 벽에 들어가던 것(재질 칸 밀림)도 같이 없어진다
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    o = bpy.data.objects.new("SHELL", me); sc.collection.objects.link(o); return o

def split_tiles(o, size=24.0):
    """큰 바위 굴을 24 m 칸으로 나눈다 — 게임이 안 보이는 칸은 안 그린다 (한 덩어리면 늘 전부 그린다)"""
    me = o.data; P_ = len(me.polygons)
    ls = np.empty(P_, np.int32); me.polygons.foreach_get("loop_start", ls); lt = np.empty(P_, np.int32); me.polygons.foreach_get("loop_total", lt)
    vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    uvs = []
    for lay in me.uv_layers: u_ = np.empty(len(me.loops) * 2); lay.data.foreach_get("uv", u_); uvs.append((lay.name, u_.reshape(-1, 2)))   # 첫 겹 = 이음 자리 · 둘째 겹 "art" (TEX-1) — 만든 차례가 TEXCOORD 번호
    nr = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("normal", nr); nr = nr.reshape(-1, 3)
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
        m2.update()
        for k_, (nm_, u_) in enumerate(uvs): m2.uv_layers.new(name=nm_); m2.uv_layers[k_].data.foreach_set("uv", u_[L].ravel())
        um, inv = np.unique(mi[F], return_inverse=True)                                    # 그 칸이 쓰는 재질 칸만 (사진 짝이 맵 전체로는 수십 개)
        m2.polygons.foreach_set("material_index", inv.astype(np.int32)); m2.polygons.foreach_set("use_smooth", np.ones(len(F), dtype=bool))
        for k_ in um: m2.materials.append(me.materials[k_])
        m2.normals_split_custom_set_from_vertices(nr[used].tolist())                       # 칸 경계의 점 노멀을 한 덩어리일 때 값으로 — 안 옮기면 24 m 선에서 빛이 어긋난다
        t = bpy.data.objects.new("SHELL_%d" % len(out), m2); sc.collection.objects.link(t); out.append(t)
    bpy.data.objects.remove(o, do_unlink=True); return out

# ================= TEX-1 — 환경마다 벽 · 바닥 사진, 경계는 얼룩으로 잇기 (제안서 docs/제안서_TEX1_층과_환경에_따라_잇는_벽과_바닥.md, 사용자 10-01 승인)
# 표 = map4_tex.json (환경 → 사진 · 방 → 환경). 여기서는 굴 그물의 점마다 "어느 사진의 자리가 몇 m 에 있나"를 재서 UV 세 겹을 적고 (부스 맵 art_uv 와 같은 길), 면마다 재질 칸 이름 RK_<벽A>_<벽B>_<바닥A>_<바닥B> 를 붙인다.
#   첫 겹 = (벽 이음 자리, 바닥 이음 자리): 0 = 사진 A 만 · 1 = B 만 · 0.5 = 두 사진의 경계, 1 m = 0.05 (TEX_SEAM 20 m 로 넓게 굽고 게임이 키로 좁힌다). 벽과 바닥은 따로 잇는다 — 승강장 둘레처럼 벽은 같고 바닥만 다른 환경이 붙은 곳이 많다
#   둘째 겹 "art" = (탄층 띠, 바닥 — 벽 아래 띠 포함) · 셋째 겹 "more" = (젖음 ÷ 2, 큰 길 = 벽 ② 의 어둡기를 받는 정도). 사진은 게임(Map4.cs)이 칸 이름을 읽어 바위 재질 MineRock 사본에 끼운다 — glb 에는 바위 사진이 안 들어간다.
TEX = json.load(open(os.path.join(HERE, "map4_tex.json"), encoding="utf-8")) if MAP else None
FRAME_OVER = timber_sets.FRAME_TOP                                    # 동발 틀: 캡 밑 = height, 맨 위(덧판 · 쐐기) = height + 0.27 → 그 자리 천장 높이에서 이만큼 뺀 값을 height 로 준다
FAULT_BAND = {"N3": ([0.5, 1.5], [2.5, 3.5])}                          # 단층 방의 탄층 띠 (바닥 위 m): 서쪽 반 · 동쪽 반 — 2 m 어긋남
TEX_SEAM, TEX_TRI = 20.0, 4.0                                        # 구운 이음 길이 m · 세 사진이 만나는 곳에서 둘째 사진을 걷어 내는 거리 m (셋째가 둘째만큼 가까우면 섞지 않는다 — 재질 칸이 갈리는 선에서 한 사진 100 %)
def vnoise3(p):
    """값 잡음 0..1 (make_booth.py 와 같은 것)"""
    i = np.floor(p); f = p - i; u = f * f * (3 - 2 * f); i = i.astype(np.int64)
    def h(dx, dy, dz):
        n = ((i[:, 0] + dx) * 73856093) ^ ((i[:, 1] + dy) * 19349663) ^ ((i[:, 2] + dz) * 83492791)
        n = n.astype(np.uint64); n = (n ^ (n >> np.uint64(13))) * np.uint64(1274126177)
        return ((n ^ (n >> np.uint64(16))) & np.uint64(0xFFFF)).astype(np.float64) / 65535.0
    x0 = h(0, 0, 0) * (1 - u[:, 0]) + h(1, 0, 0) * u[:, 0]; x1 = h(0, 1, 0) * (1 - u[:, 0]) + h(1, 1, 0) * u[:, 0]
    x2 = h(0, 0, 1) * (1 - u[:, 0]) + h(1, 0, 1) * u[:, 0]; x3 = h(0, 1, 1) * (1 - u[:, 0]) + h(1, 1, 1) * u[:, 0]
    return (x0 * (1 - u[:, 1]) + x1 * u[:, 1]) * (1 - u[:, 2]) + (x2 * (1 - u[:, 1]) + x3 * u[:, 1]) * u[:, 2]
def fbm3(p, octaves=3): return sum(vnoise3(p * 2 ** k) * 0.5 ** k for k in range(octaves)) / sum(0.5 ** k for k in range(octaves))

def tex1_sites(rooms, N, SEG, zi, scene_air, face_air, shell):
    """환경 자리(굴 안 공기 속 점)들: 방은 2 m 칸 · 굴은 1.5 m 마다(가운데에서 가까운 끝 방의 환경으로 갈린다) · 장면은 공기 상자 안 2 m 칸.
    자리마다 [x, y, z, 벽 사진, 천장 사진, 바닥 사진, 바닥 높이, 젖음, 벽 아래 띠 높이, 큰 길, 탄층 띠 아래, 위]"""
    from mathutils import kdtree
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(shell, bpy.context.evaluated_depsgraph_get()); down = Vector((0, 0, -1)); drop = [0]; S = []
    def inair(p):                                                      # 굴 안의 점인가: 아래로 쏜 광선이 위를 보는 면(바닥)에 맞는다 — 상자 범위로 뽑은 자리 중 바위 속에 든 것을 버린다
        h = bvh.ray_cast(Vector(p), down, 30.0); return h[0] is not None and h[1].z > 0.3
    wetof = lambda k: float(TEX["wet"].get(k, 1.0))
    SPLITX = {"door": L7S - 0.15 - 6.0, "chute": L3 * 0.55}           # scene7 의 앞문 틀 xa · scene3 의 석탄 홈통 cx (장면 좌표)
    def add(p, env, fz, wet, cb=None):
        e = TEX["env"][env]; cb = cb or e.get("coalband", [0.0, 0.0])
        if not inair(p): drop[0] += 1; return
        S.append((p[0], p[1], p[2], e["wall"], e.get("roof", e["wall"]), e["floor"], fz, wet, e.get("band", TEX["band_m"]), e.get("dim", 0), cb[0], cb[1]))
    grid = lambda a, b: (np.arange(a + 1.0, b - 0.99, 2.0) if b - a > 2.0 else np.array([(a + b) / 2]))
    levels = lambda z0, z1: np.arange(z0 + 1.2, max(z1 - 0.5, z0 + 1.3), 3.0)
    def scene_env(sn, pl):
        sp = TEX["scene_split"].get(sn)
        if sp and pl.x < SPLITX[sp["x"]]: return sp["before"]
        return "lairhigh" if sn == "z9" and pl.z >= TEX["lair_split_m"] else TEX["scene"][sn]
    def end_env(k, p):
        if k in N: return TEX["room"][k], wetof(k)
        sn = k.split(".")[0]; return scene_env(sn, zi[sn]["T"].inverted() @ p), wetof(sn)
    for n in rooms:
        for x in grid(n["x"] - n["w"] / 2, n["x"] + n["w"] / 2):
            for y in grid(n["y"] - n["d"] / 2, n["y"] + n["d"] / 2):
                # 단층 방: 탄층 띠가 방 가운데(단층 선)에서 2 m 어긋난다 — 벽 사진에 칠한다 (사용자 10-03 "벽면 모델링이 네모로 튀어나와 있다": 옛 것은 0.8 × 0.7 × 0.16 m 상자를 0.75 m 마다 벽에 붙였다)
                cb = None if n["id"] not in FAULT_BAND else FAULT_BAND[n["id"]][0 if x < n["x"] else 1]
                for z in levels(n["z"], n["z"] + n["h"]): add((x, y, z), TEX["room"][n["id"]], n["z"], wetof(n["id"]), cb)
    for s in SEG:
        p, q = s["p"], s["q"]; L = (q - p).to_2d().length; a0, a1 = s["ta"], L - s["tb"]
        if a1 <= a0: continue                                                                 # 방 벽끼리 맞닿은 굴 — 방 자리들이 가른다
        (ea, wa), (eb, wb) = end_env(s["edge"]["a"], p), end_env(s["edge"]["b"], q)
        for t in np.arange(a0 + 0.5, a1, 1.5): pt = p.lerp(q, t / L); h_ = t < (a0 + a1) / 2; add((pt.x, pt.y, pt.z + 1.2), ea if h_ else eb, pt.z, wa if h_ else wb)
    for sn, b in scene_air:
        vs = np.array([v.co[:] for v in b.verts]); lo, hi = vs.min(0), vs.max(0); T = zi[sn]["T"]; Ti = T.inverted(); fz = T.translation.z
        for x in grid(lo[0], hi[0]):
            for y in grid(lo[1], hi[1]):
                for z in levels(fz, hi[2]):
                    pl = Ti @ Vector((x, y, z)); up_ = PORT["z9"]["in"][2] if sn == "z9" and pl.x < -19.5 and abs(pl.y - PORT["z9"]["in"][1]) < 2.0 else 0.0   # 그것의 굴로 들어오는 굴은 바닥이 +3 m (0 으로 적으면 그 굴 바닥이 벽 사진이 되고 벽 아래 띠가 없다 — 검토 10-01. 광선 맞은 높이를 두루 쓰면 벽 선반 위 자리가 선반을 바닥으로 만든다)
                    if any(abs(x - r_["x"]) < r_["w"] / 2 and abs(y - r_["y"]) < r_["d"] / 2 and r_["z"] - 1.0 < z < r_["z"] + r_["h"] + 1.0 for r_ in rooms): continue   # 장면 상자가 덮은 '방 안'은 그 방의 자리다 (승강장 상자가 펌프실을 덮어, 바닥 높이가 같아지자 펌프실 바닥이 승강장 사진이 됐다 — 검사 map4_room_photos)
                    add((x, y, z), scene_env(sn, pl), fz + up_, wetof(sn))
    for b, fz in face_air:                                              # 막장 홈(깊이 5 m): 1 m 칸으로 끝 벽 앞까지 — 2 m 칸 둘로는 홈 벽이 석탄 반 · 셰일 반으로 구워졌다 (검토 10-01)
        vs = np.array([v.co[:] for v in b.verts]); lo, hi = vs.min(0), vs.max(0)
        for x in np.arange(lo[0] + 0.5, hi[0], 1.0):
            for y in np.arange(lo[1] + 0.5, hi[1], 1.0): add((x, y, fz + 1.2), "coalface", fz, 0.3)   # 젖음 0.3 (1.0 일 때 석탄 벽에 세로로 번들거리는 물 자국 줄이 섰다 — 사용자 캡처 8 · 16 의 흰 세로 줄)
    S = np.array(S)
    def tree(ix):
        k = kdtree.KDTree(len(ix))
        for i in ix: k.insert(S[i, :3], int(i))
        k.balance(); return k
    by = lambda col: {int(p): tree(np.nonzero(S[:, col] == p)[0]) for p in np.unique(S[:, col])}   # 사진 번호 → 그 사진을 쓰는 자리들
    return dict(pillars=[p_ for n in rooms for p_ in n.get("pillars", [])], end_env=end_env, splitx=SPLITX, S=S, kd=tree(range(len(S))), wall=by(3), roof=by(4), floor=by(5), seam=tree(np.nonzero(S[:, 11] > S[:, 10])[0]), noseam=tree(np.nonzero(S[:, 11] <= S[:, 10])[0]), bvh=bvh, dropped=drop[0])

def tex1_paint(o, T1, fixed=None, ray=False):
    """그물 하나에 TEX-1 을 적는다 (위 설명). fixed = 환경 이름이면 그 환경만(석탄 기둥 같은 소품). ray = 바닥에서 높이를 아래로 쏜 광선으로(바위 굴) — 아니면 가까운 자리의 바닥 높이에서. 돌려줌 = 잰 값"""
    me = o.data; M = np.array(o.matrix_world); R3 = M[:3, :3].T; nv, P_ = len(me.vertices), len(me.polygons); S = T1["S"]
    co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ R3 + M[:3, 3]
    nr = np.empty(nv * 3); me.vertices.foreach_get("normal", nr); nr = nr.reshape(-1, 3) @ R3
    pn = np.empty(P_ * 3); me.polygons.foreach_get("normal", pn); pnz = (pn.reshape(-1, 3) @ R3)[:, 2]; roof = pnz < -0.55
    ls = np.empty(P_, np.int32); me.polygons.foreach_get("loop_start", ls); lt = np.empty(P_, np.int32); me.polygons.foreach_get("loop_total", lt)
    vi = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", vi); fidx = np.repeat(np.arange(P_), lt); col = co.tolist(); NL = len(vi)
    wet = np.empty(nv); band = np.empty(nv); dim = np.empty(nv); fz = np.empty(nv); b0 = np.empty(nv); b1 = np.empty(nv)
    for k, c in enumerate(col):                                                               # 가까운 자리 넷: 젖음 · 띠 높이 · 큰 길은 거리로 고르게 섞고(방 경계에서 딱 끊기지 않게), 바닥 높이 · 탄층 띠는 가장 가까운 것
        r = T1["kd"].find_n(c, 4); w = np.array([1.0 / (d + 0.5) for _, _, d in r]); ix = [i for _, i, _ in r]; w /= w.sum()
        wet[k] = S[ix, 7] @ w; band[k] = S[ix, 8] @ w; dim[k] = S[ix, 9] @ w; fz[k] = S[ix[0], 6]; b0[k] = S[ix[0], 10]; b1[k] = S[ix[0], 11]
    floor = nr[:, 2] > 0.6; up = co[:, 2] - fz
    if ray:                                                                                   # 공기 쪽으로 5 cm 뜬 뒤 아래로 (부스 art_uv 와 같다) — 벽 점만
        bvh = T1["bvh"]; down = Vector((0, 0, -1)); hgt = np.full(nv, 9.0)
        for k in np.nonzero(floor & (up > 1.0))[0]:                                           # 벽 중턱의 불룩한 곳 윗면은 바닥이 아니다 (첫 굽기: 벽 한가운데에 자갈 얼룩이 떴다) — 그 높이(±0.6 m)를 바닥으로 가진 자리가 2.6 m 안에 없으면 턱, 있으면 높은 바닥
            if not any(abs(S[i, 6] - co[k, 2]) < 0.6 for _, i, _ in T1["kd"].find_range(col[k], 2.6)): floor[k] = False
        for k in np.nonzero(~floor & (nr[:, 2] > -0.3))[0]:
            hit = bvh.ray_cast(Vector(co[k] + nr[k] * 0.05), down, 3.0); hgt[k] = hit[3] if hit[0] is not None else 9.0
        hgt = np.where(floor, 0.0, np.maximum(hgt, up - 0.5))                                 # 턱 바로 위 벽에도 띠가 생기지 않게 — 띠는 그 방 바닥 높이 둘레에만
    else: hgt = up
    mud = np.where(floor, 1.0, np.clip(1 - (hgt - band * (0.4 + 0.9 * fbm3(co * np.array([1 / 1.3, 1 / 1.3, 1 / 0.5])))) / 0.25, 0, 1))
    dist = lambda kd: np.array([kd.find(c)[2] for c in col], np.float32)
    if fixed is None:                                                                         # 탄층 띠: 그 환경 안쪽 벽에, 바닥에서 b0~b1 m, 흐트러진 또렷한 선 (섞지 않는다)
        zw = co[:, 2] - fz + 0.5 * (fbm3(co * np.array([1 / 6.0, 1 / 6.0, 1 / 2.0]) + 31.7) - 0.5)
        coal = np.clip(np.minimum(zw - b0, b1 - zw) / 0.08 + 0.5, 0, 1) * (b1 > b0) * np.clip((dist(T1["noseam"]) - dist(T1["seam"])) / 3.0, 0, 1) * (1 - mud) * (nr[:, 2] > -0.5)
        for px_, py_, sx_, sy_ in T1.get("pillars", ()):                                       # 남겨 둔 석탄 기둥의 옆면 전부 = 석탄 (발치 띠 · 천장은 그대로)
            on = (np.abs(co[:, 0] - px_) < sx_ / 2 + 0.9) & (np.abs(co[:, 1] - py_) < sy_ / 2 + 0.9)
            coal = np.where(on, (1 - mud) * (nr[:, 2] > -0.5) * (nr[:, 2] < 0.6), coal)
    else: coal = np.zeros(nv)
    lean = TEX["lean_m"] * np.clip((co[vi, 2] - fz[vi]) / 3.0, 0, 1)                           # 경계를 눕힌다 — 천장이 바닥보다 lean_m 먼저 바뀐다(지층 면처럼)
    def chan(Dl, ids, lean_, hard_ids=()):
        """사진 하나하나까지의 거리(면 모서리마다) → 그 면의 사진 짝(A < B 번호 차례) · 이음 자리 u"""
        k = len(ids); od = np.argsort(np.add.reduceat(Dl, ls, axis=0) / lt[:, None], axis=1); P1, P2, P3 = od[:, 0], od[:, min(1, k - 1)], od[:, min(2, k - 1)]
        rows = np.arange(NL); p1, p2, p3 = P1[fidx], P2[fidx], P3[fidx]; d1, d2, d3 = Dl[rows, p1], Dl[rows, p2], Dl[rows, p3]; first = ids[p1] < ids[p2]
        hard = np.isin(ids[p1], hard_ids) | np.isin(ids[p2], hard_ids)                         # 그것의 굴 6 m 위 ⑩(높이로 바뀌는 경계) · 석탄 면 ⑦(탄층이 딱 갈리는 선): 눕히지 않고, 이음을 2.5 배 좁게
        c = np.where(first, d1 - d2, d2 - d1) * np.where(hard, 2.5, 1.0) + lean_ * ~hard          # 경계에서 잰 m (자리가 굴을 채우고 있어 제 사진까지 d1 은 거의 그대로이고 d2 만 1 m 에 1 m 바뀐다 — ÷ 2 하면 이음이 숫자의 두 배로 길어진다, 검토 10-01)
        w3 = np.clip((d3 - d2) / TEX_TRI, 0, 1) if k > 2 else np.ones(NL); pure = np.where(first, -TEX_SEAM / 2, TEX_SEAM / 2)
        c = pure + (c - pure) * w3
        u = np.clip(0.5 + c / TEX_SEAM, 0, 1); umin, umax = np.minimum.reduceat(u, ls), np.maximum.reduceat(u, ls)
        f1 = ids[P1] < ids[P2]; LO, HI = np.where(f1, P1, P2), np.where(f1, P2, P1); A = np.where(umin >= 0.999, HI, LO); B = np.where(umax <= 0.001, LO, HI)
        same = A == B; u[same[fidx]] = 0.0
        return ids[A], ids[B], u, same
    if fixed is None:
        cache = {}
        def table(trees):
            ids = np.array(sorted(trees)); cols = []
            for p in ids:
                key = id(trees[p])
                if key not in cache: cache[key] = dist(trees[p])
                cols.append(cache[key])
            return ids, np.stack(cols, 1)
        wi, Dw = table(T1["wall"]); ri, Dr = table(T1["roof"]); fi, Df = table(T1["floor"])
        wA, wB, uw, _ = chan(Dw[vi], wi, lean, (7, 10)); split = np.zeros(P_, bool)
        if roof.any() and (len(ri) != len(wi) or (ri != wi).any() or (Dr != Dw).any()):       # 천장 사진이 따로인 환경(석탄 면: 벽 ⑦ · 천장 ⑧) — 천장 면은 천장 표로 다시
            rA, rB, ur, _ = chan(Dr[vi], ri, lean, (7, 10)); split = roof & ((rA != wA) | (rB != wB)); wA, wB = np.where(roof, rA, wA), np.where(roof, rB, wB); uw = np.where(roof[fidx], ur, uw)
        fA, fB, uf, _ = chan(Df[vi], fi, np.zeros(NL))
        def jumps(A_, B_, u_, sel):
            """한 점을 나눠 쓰는 면들(sel) 사이에서 어느 사진의 몫이 0.25 넘게 뛰는 점 = 화면에서 사진이 딱 끊겨 보이는 곳"""
            L = sel[fidx]; v = vi[L]; a_, b_, uu = A_[fidx][L], B_[fidx][L], u_[L]; one = a_ == b_
            key = np.concatenate([v * 100 + a_, (v * 100 + b_)[~one]]); sh = np.concatenate([np.where(one, 1.0, 1 - uu), uu[~one]])
            uq, inv = np.unique(key, return_inverse=True); hi_ = np.zeros(len(uq)); lo_ = np.ones(len(uq)); n_ = np.zeros(len(uq))
            np.maximum.at(hi_, inv, sh); np.minimum.at(lo_, inv, sh); np.add.at(n_, inv, 1)
            lo_[n_ < np.bincount(v, minlength=nv)[uq // 100]] = 0.0                               # 그 점의 어떤 면에는 이 사진이 아예 없다 = 몫 0
            return np.unique(uq[(hi_ - lo_) > 0.25] // 100)
        isfl_ = pnz > 0.55
        cut = np.unique(np.concatenate([jumps(wA, wB, uw, ~isfl_ & ~split), jumps(wA, wB, uw, split), jumps(fA, fB, uf, isfl_)]))   # 벽 ↔ 천장 사진이 따로인 선(석탄 면)은 일부러 안 섞는 곳이라 따로 센다
    else:
        e = TEX["env"][fixed]; wA = wB = np.full(P_, e["wall"]); fA = fB = np.full(P_, e["floor"]); uw = uf = np.zeros(NL); cut = np.zeros(0, int)
    code = wA * 1000000 + wB * 10000 + fA * 100 + fB; uniq, inv = np.unique(code, return_inverse=True); me.materials.clear()
    for cd in uniq:
        nm = "RK_%d_%d_%d_%d" % (cd // 1000000, cd // 10000 % 100, cd // 100 % 100, cd % 100); m = bpy.data.materials.get(nm)
        if m is None: m = bpy.data.materials.new(nm); m.use_nodes = True; next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.2, 0.18, 0.16, 1)
        me.materials.append(m)
    me.polygons.foreach_set("material_index", inv.astype(np.int32))
    for k, (nm, a, b) in enumerate((("UVMap", uw, uf), ("art", coal[vi], mud[vi]), ("more", np.clip(wet / 2, 0, 1)[vi], np.clip(dim, 0, 1)[vi]))):   # 만든 차례가 TEXCOORD 번호
        if len(me.uv_layers) <= k: me.uv_layers.new(name=nm)
        me.uv_layers[k].data.foreach_set("uv", np.stack([a, b], 1).ravel())
    me.uv_layers.active = me.uv_layers[0]
    ar = np.empty(P_); me.polygons.foreach_get("area", ar); cen = np.add.reduceat(co[vi], ls, axis=0) / lt[:, None]; isfl = pnz > 0.55
    wdom = np.where(np.add.reduceat(uw, ls) / lt < 0.5, wA, wB); fdom = np.where(np.add.reduceat(uf, ls) / lt < 0.5, fA, fB)
    return dict(names=[m.name for m in me.materials], wall={int(k): float(ar[(wdom == k) & ~isfl].sum()) for k in np.unique(wdom)}, floor={int(k): float(ar[(fdom == k) & isfl].sum()) for k in np.unique(fdom)},
                blend=float(ar[(wA != wB) | (fA != fB)].sum()), all=float(ar.sum()), tri=co[cut], coal=float(ar[np.maximum.reduceat(coal[vi], ls) > 0.5].sum()))

MAP_PLAN = os.path.join(HERE, "map4_plan.json")                      # 1편 구조 (구조 설계 워크플로 추천안, 사용자 10-01 선택) — 방 · 굴 · 판자 문 칸 좌표
# ⑨ 큰 빈터 안의 걷는 길 (장면 좌표): 들어오는 굴 → 발판 → 계단 → 바닥 → 나가는 굴 · 바닥 → 좁은 굴 쪽
Z9_WALKS = [("z9", 1.2, [(-32.5, 4, 3), (-19.2, 4, 3)]), ("z9", 0.4, [(-19.2, 4, 3), (-19.65, 2.9, 3), (-19.65, 2.4, 3), (-19.65, 0.42, 1.5), (-19.65, -0.62, 1.5), (-19.65, -2.7, 0), (-19.65, -3.8, 0)]),
            ("z9", 1.5, [(-19.65, -3.8, 0), (-15, -3.5, 0), (-13, -1, 0), (0, 1.5, 0), (12, 0.5, 0), (19, -4, 0), (22, -8, 0), (32.5, -8, 0)]), ("z9", 1.2, [(19, -4, 0), (18.5, -9, 0), (18, -12, 0)])]
L3 = 3 * 3.52 + 2 * 4.54; L7S, L7W = 2 * 3.52 + 2 * 4.54, 3.05 + 2.81 + 3.05   # 장면 ③ · ⑦ 길이 (Fab 목록에서 잰 조각 길이)
PORT = {"z6": {"W": (-8, 1, 0), "E": (8, -1, 0), "S": (0, -20, 0)}, "z3": {"a": (0, 0, 0), "b": (L3, 0, 0)},
        "z7": {"a": (0, 0, 0), "b": (L7S + L7W, 0, 0)}, "z8": {"a": (0, 0, 0), "b": (19.92, 0, 0)},
        "z1": {"a": (-22, 0, 0), "b": (20, 0, 0)}, "z2": {"a": (0, 0, 0), "back": (15, 3, 0)},
        "z9": {"in": (-32.5, 4, 3), "out": (32.5, -8, 0), "crawl": (18, -12, 0)}}                  # 장면 출입구 (장면 좌표)
ROOM_H = {"M": 5.0, "K": 5.5, "S1": 4.4, "W1": 4.4, "P": 4.2, "L": 4.2, "H": 4.2, "R2": 4.2, "E1": 4.0, "N1": 4.2, "N2": 3.2, "V": 3.4, "LD": 3.6, "LW": 3.2, "MAG": 2.6}
SCENE_NAME = {"z6": "⑥ 승강장", "z3": "③ 광차 싣는 곳", "z7": "⑦ 바람문", "z8": "⑧ 무너진 기둥", "z1": "① 쇠동발 숲", "z2": "② 채탄 막장", "z9": "⑨ 그것의 굴"}

def map4():
    global ZT, PASS, SHELL, M_OLD_, M_TAR_, M_IRONDOOR_, M_SIGNBOARD_, M_SIGNTEXT_, HEAP_MAT
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
    M_MURK = paint("water_murk", (0.034, 0.03, 0.02), 0.2); M_WATER = paint("water", (0.01, 0.012, 0.012), 0.03); M_MACH = paint("machine", (0.07, 0.1, 0.085), 0.6, 0.6); M_RED = paint("redbox", (0.3, 0.05, 0.03), 0.7)
    M_WHITE = paint("white", (0.5, 0.49, 0.45), 0.8); M_CLOTH = cc0_mat("misc/decrepit_wallpaper", 2.5, "tarp", (0.34, 0.31, 0.27)) or paint("tarp", (0.08, 0.07, 0.05), 0.95); M_METAL = paint("metal", (0.09, 0.09, 0.1), 0.55, 0.8)
    M_PAPER = paint("paper", (0.45, 0.42, 0.33), 0.9); M_LADDER = paint("ladderpaint", (0.3, 0.22, 0.05), 0.75, 0.4)
    M_FENCE = tint(M_TIMB, (0.8, 0.75, 0.68), "fence")
    METAL["wet"] = True; M_MACH_W, M_METAL_W = paint("machine_wet", (0.07, 0.1, 0.085), 0.6, 0.6), paint("metal_wet", (0.09, 0.09, 0.1), 0.55, 0.8); METAL["wet"] = False   # 물 가까운 방의 기계
    # 소품 재질 (props/_util.py MAT_KEYS → 사용자 10-01 이 고른 사진: 나무 4 · 7 / 쇠 5 · 8 / 천 4). 칠 색은 머리등에 타지 않게 어둡게
    global PMATS
    solid = lambda nm, rgb, rough=0.8: paint(nm, rgb, rough)
    def recolor(m, rgb, nm):                                                                  # 사진의 결(노멀 · 거칠기)은 두고 색만 바꾼 사본
        t = m.copy(); t.name = nm; b_ = next(n_ for n_ in t.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
        for l in list(b_.inputs["Base Color"].links): t.node_tree.links.remove(l)
        b_.inputs["Base Color"].default_value = (*rgb, 1); return t
    # 칠 색 (10-03): 초록빛 기계 칠 · 파란 판 · 노란 바람 관을 화면 기준(docs/ART_BIBLE.md 금지 색 제안: 파랑 · 진한 초록)에 맞춘다 — 사용자 "노란 통은 밑의 기계와 분위기가 맞지 않다" · "드럼통은 왜 있는 것인지"(파란 통)
    #   기계 칠 = 바랜 잿빛 · steel_blue = 검은 잿빛(가스 검정판 = 칠판 · 펌프 몸) · 바람 관 = 때 탄 잿빛 갈색 천 · 물때 = 어두운 누런 갈색(받침 둘레가 주황 판처럼 보였다)
    PMATS = {"steel_paint": paint("p_steel_paint", (0.088, 0.09, 0.084), 0.6, 0.6), "steel_red": paint("p_steel_red", (0.045, 0.02, 0.016), 0.7, 0.5), "steel_blue": paint("p_steel_blue", (0.04, 0.045, 0.05), 0.6, 0.5),
             "steel_yellow": paint("p_steel_yellow", (0.22, 0.15, 0.035), 0.6, 0.5), "rust": M_RUST_W, "iron": paint("p_iron", (0.05, 0.05, 0.055), 0.55, 0.8), "bare": paint("p_bare", (0.2, 0.2, 0.21), 0.4, 0.9),
             "timber": M_TIMB, "timber_end": cc0_mat("wood/TreeEnd005", 0.3, "p_timber_end", (0.5, 0.45, 0.38)) or tint(M_TIMB, (1.25, 1.2, 1.1), "p_timber_end"), "timber_old": M_OLD_, "tar": M_TAR_,
             "plank": tint(M_TIMB, (0.85, 0.8, 0.74), "p_plank"), "cloth": tint(M_CLOTH, (0.2, 0.19, 0.175), "p_cloth"),   # 거적 · 자루: 가까이서 머리등에 하얗게 탔다 → 3분의 1 로 어둡게
              "cloth_yellow": recolor(M_CLOTH, (0.13, 0.105, 0.07), "p_cloth_yellow"),
             "concrete": cc0_mat("misc/wood_textured_concrete", 2.0, "p_concrete", (0.42, 0.42, 0.42)) or solid("p_concrete", (0.16, 0.155, 0.15)), "white": solid("p_white", (0.4, 0.39, 0.36)), "black": solid("p_black", (0.02, 0.02, 0.022), 0.85),
             "red": solid("p_red", (0.25, 0.012, 0.01)), "chalk": solid("p_chalk", (0.5, 0.5, 0.47)), "glass": solid("p_glass", (0.3, 0.33, 0.31), 0.3), "rubber": solid("p_rubber", (0.02, 0.02, 0.02), 0.6), "water": M_WATER,
             "ochre": solid("p_ochre", (0.085, 0.055, 0.025), 0.9)}
    PM = PMATS
    PMD = dict(PM); PMD["timber"] = tint(M_TIMB, (0.6, 0.57, 0.54), "timber_dusty"); PMD["timber_end"] = tint(PM["timber_end"], (0.55, 0.52, 0.48), "p_timber_end_dusty"); PMD["plank"] = tint(PM["plank"], (0.6, 0.58, 0.55), "p_plank_dusty")   # 막장 동발: 가루 앉아 어둡다 (밝은 새 나무는 머리등 1 m 앞에서 하얗게 탔다)
    lib("ufekaeedw", key="rail", rails=True)                                                   # 레일 조각 (레일이 X 로 눕게)
    for fid in ("ueujednfa", "ufmodhpfa", "ujzhahdfa"): lib(fid, along=True)                   # 광차 (긴 쪽을 X 로)
    for key, col in (("coal", (0.09, 0.09, 0.1)), ("stone", (0.55, 0.55, 0.58))):               # 스캔 돌 = 석탄 덩이 · 바위 돌 (같은 모델, 다른 색)
        m = tint(tex_mat(os.path.join(FABDIR, "wd3efb0"), 1 / 0.35), col, key + "_lump"); b_ = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for l in list(b_.inputs["Roughness"].links): m.node_tree.links.remove(l)
        b_.inputs["Roughness"].default_value = 0.8; b_.inputs["Specular IOR Level"].default_value = 0.1; lib("wd3efb0", key=key, mat=m)   # 석탄이 은색 쇠처럼 번쩍였다 (검수)
        for o in lib(key)[0]:                                                                  # 덩이 하나 약 1,490 → 450 삼각형 (더미 · 막힌 굴 · 틈 발치에 천 개 가까이 놓인다 — 결은 노멀 그림이 살린다)
            sc.collection.objects.link(o); dm = o.modifiers.new("dec2", "DECIMATE"); dm.ratio = 0.3
            me_ = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); o.modifiers.clear(); o.data = me_; sc.collection.objects.unlink(o)
    def fines(d_, tile_m, name, mul):                                                         # 더미 둔덕 겉의 흙 · 가루 사진 (box_uv 0.8 에 맞춘 크기)
        m_ = tex_mat(d_, tile_m); m_.name = name; next(n_ for n_ in m_.node_tree.nodes if n_.type == "MAPPING").inputs["Scale"].default_value = (1 / (0.8 * tile_m),) * 3; return tint(m_, mul, name)
    HEAP_MAT = {"stone": fines(os.path.join(CC0, "floor", "Rocks006"), 1.6, "heap_rubble", (0.3, 0.265, 0.23)) if os.path.isdir(os.path.join(CC0, "floor", "Rocks006")) else lib("stone")[0][0].data.materials[0],
                "coal": fines(CG, 1.4, "heap_coalfines", (0.3, 0.29, 0.28)) if os.path.isdir(CG) else lib("coal")[0][0].data.materials[0]}
    R = lambda yaw: Matrix.Rotation(math.radians(yaw), 4, "Z")
    FN = {"z6": scene6, "z3": scene3, "z7": scene7, "z8": scene8, "z1": scene1, "z2": scene2, "z9": scene9}
    AIRZ = {"z3": [("haul", -0.5, L3 + 0.5)],
            "z7": [("haul", -0.5, L7S + 0.5), ((L7S + L7W / 2, 0, 1.4), (L7W + 1, KIND["side"][0], KIND["side"][1]))]}
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
    PASS = "air"; scene_air, face_air = [], []                                                # TEX-1: 장면 · 막장 홈의 공기 (환경 자리를 뽑을 범위)
    for z in Z:
        ZT = z["T"]; random.seed(z["seed"]); before = set(bpy.data.objects); i0 = len(AIR)
        for c, *sz in z.get("air", []):
            b = bmesh.new()
            if c == "haul": arch_air(b, *sz)
            else: box(b, c, sz[0])
            b.transform(ZT); AIR.append((b, 0.3, None))
        if "air" not in z:
            try: z["f"]()
            except ZoneAir: pass
        scene_air += [(z["n"], a[0]) for a in AIR[i0:]]
        for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    def tube(p, q, kind, t0=0.0, t1=0.0):
        w, h = KIND[kind]; F, L = frame(p, q); slope = abs(q.z - p.z) > 0.05; n = max(1, int(L / 0.6)) if slope else 1
        if kind == "haul" and not slope: bm_ = bmesh.new(); arch_air(bm_, 0, L, p.z); bm_.transform(F); AIR.append((bm_, 0.3, None)); return   # 운반갱도 = 아치 꼴
        for i in range(n):                                                                    # 비탈이면 짧은 상자를 계단처럼 (복셀이 매끈한 비탈로 잇는다 — 턱 없음)
            za = p.z + (q.z - p.z) * min(1.0, max(0.0, ((i + 0.5) * L / n - t0) / max(L - t0 - t1, 0.5)))   # 비탈은 방 벽(t0)에서 방 벽(L − t1)까지 — 방 가운데끼리 이으면 낮은 방 입구에 1.3 m 턱이 남았다 (걷기 검사가 찾음)
            bm_ = bmesh.new(); box(bm_, ((i + 0.5) * L / n, 0, za + h / 2), (L / n + (0.8 if slope else 0.0), w, h)); bm_.transform(F); AIR.append((bm_, 0.3, None))
    for s in SEG: tube(s["p"], s["q"], s["kind"], max(0.0, s["ta"] - 0.6), max(0.0, s["tb"] - 0.6))
    for v, k in BEND: b = bmesh.new(); w, h = KIND[k]; box(b, (v.x, v.y, v.z + h / 2), (w + 1.2, w + 1.2, h)); AIR.append((b, 0.3, None))
    # 방마다 벽에 난 것들: 굴 입구(MOUTH) · 파낸 홈(REC — 북쪽 막장 셋 · 막아 둔 채굴적 울타리 둘). 그 둘레는 벽을 불룩하게 파지 않고(아치 옆이 휑하게 드러났다),
    # 판자 문 칸도 거기를 피해 놓는다 (사용자 10-02 "뜬금없이 문이 있다": C14 가 대피소 → 선로 끝 굴 입구 한가운데에 문틀만 서 있었다 — 가까운 방 벽으로 옮기는 법이 굴 입구를 골랐다)
    MOUTH, REC, KEEP = {}, {}, {}
    def wall_of(r, pt):                                                                       # 방 벽 위의 점 → (벽 방향 f, 벽 따라 자리 t)
        dx, dy = pt.x - r["x"], pt.y - r["y"]
        f = Vector((1 if dx > 0 else -1, 0, 0)) if abs(abs(dx) - r["w"] / 2) < abs(abs(dy) - r["d"] / 2) else Vector((0, 1 if dy > 0 else -1, 0))
        return f, Vector((dx, dy, 0)).dot(Vector((-f.y, f.x, 0)))
    for sg in SEG:
        d = (sg["q"] - sg["p"]); d.z = 0; d.normalize(); hw = 2.9 if sg["kind"] == "haul" else KIND[sg["kind"]][0] / 2
        for k_, pt, far, din, oth in ((sg["edge"]["a"], sg["p"] + d * exit_t(sg["edge"]["a"], d), sg["p"], -d, sg["edge"]["b"]), (sg["edge"]["b"], sg["q"] - d * exit_t(sg["edge"]["b"], -d), sg["q"], d.copy(), sg["edge"]["a"])):
            if k_ in N and N[k_] in rooms and (pt - far).length > 0.5: MOUTH.setdefault(k_, []).append((wall_of(N[k_], pt), hw, pt, oth.split(".")[0], din, sg["kind"]))   # (벽 · 자리, 반폭, 입구 점, 이어진 곳, 방 안쪽 방향, 굴 종류)
    for dx in (-8, 0, 8): REC.setdefault("N2", []).append(((Vector((0, 1, 0)), -dx), 1.7))
    for rid, gid in (("M", "GOAF_W"), ("E2", "GOAF_E")):
        r_, g = N[rid], N[gid]; d = Vector((g["x"] - r_["x"], g["y"] - r_["y"], 0)); REC.setdefault(rid, []).append(((Vector((1 if d.x > 0 else -1, 0, 0)) if abs(d.x) > abs(d.y) else Vector((0, 1 if d.y > 0 else -1, 0)), 0.0), 1.8))
    def wall_pt(r, f, t): return Vector((r["x"], r["y"], r["z"])) + f * (abs(f.x) * r["w"] / 2 + abs(f.y) * r["d"] / 2) + Vector((-f.y, f.x, 0)) * t
    # 괴물 틈 (사용자 10-03 "모든 방에서 괴물이 튀어나올 만한 위험이 인지되는 곳이 없다 — 괴물 전용 틈이나 천장에서 나오는 곳이 없다"). 설계(map4_plan.json 방 설명)가 약속한 자리인데 하나도 안 지어져 있었다:
    #   갱목 쌓는 곳 뒷벽 · 옛 채굴 빈터 북쪽 벽(울타리 옆) · 붕락 방 서쪽 벽 · 막아 둔 채굴적 입구 울타리 옆 · 창고 칸 줄 · 단층 방 · 광차 굽이 남쪽 벽. 승강장 동네(집)에는 두지 않는다.
    #   모양 = 기획서 4절 "그것이 드나드는 큰 틈: 높이 2.6 · 폭 1.35 m": 입(폭 1.35 · 깊이 1.7 m)은 사람이 설 수 있고, 그 뒤는 폭 0.5 m 로 좁아지며 꺾여 6 m 넘게 어둠 속으로 — 사람은 못 들어가고 머리등이 끝에 안 닿는다.
    #   지금 빌드에는 괴물이 없다(모양만). 괴물이 여기로 드나드는 동작은 다음 번호(바위 틈 드나들기 MR1 R3)
    CRACK_WANT = (("W2", "W", 0.0), ("M", "N", -9.0), ("K", "W", 1.0), ("E2", "S", -5.5), ("V", "W", 0.0), ("N3", "W", 0.0), ("E3", "N", 0.0))   # (방, 벽, 벽 가운데에서 세계 좌표 +x · +y 쪽으로 m)
    CRACKS = []
    def crack_path(w0, f, bend):                                                              # 틈 가운데 줄 (벽 점에서 바위 속으로): 입 1.7 m → 28° 꺾어 2.6 m → 55° 꺾어 3 m
        d1 = Matrix.Rotation(math.radians(28 * bend), 3, "Z") @ f; d2 = Matrix.Rotation(math.radians(55 * bend), 3, "Z") @ f
        p1 = w0 + f * 1.7; p2 = p1 + d1 * 2.6; return [(w0 - f * 0.3, p1, 1.35, 2.6), (p1 - d1 * 0.2, p2, 0.5, 2.45), (p2 - d2 * 0.2, p2 + d2 * 3.0, 0.5, 2.25)]
    def near_air(pt, skip):                                                                   # 그 점 1.6 m 안에 다른 방 · 굴 · 장면 공기가 있나
        for r_ in rooms:
            if r_["id"] != skip and abs(pt.x - r_["x"]) < r_["w"] / 2 + 1.6 and abs(pt.y - r_["y"]) < r_["d"] / 2 + 1.6 and r_["z"] - 3.5 < pt.z < r_["z"] + r_.get("h", 4.0) + 3.0: return r_["id"]
        for sg in SEG:
            a_, b_ = sg["p"], sg["q"]; ab = (b_ - a_); t_ = max(0.0, min(1.0, (pt - a_).dot(ab) / max(ab.length_squared, 1e-6))); c_ = a_ + ab * t_
            if (pt - c_).to_2d().length < KIND[sg["kind"]][0] / 2 + 1.6 and c_.z - 3.5 < pt.z < c_.z + 6.0: return "%s-%s" % (sg["edge"]["a"], sg["edge"]["b"])
        for sn_, b_ in scene_air:
            vs = np.array([v.co[:] for v in b_.verts]); lo, hi = vs.min(0) - 1.6, vs.max(0) + 1.6
            if lo[0] < pt.x < hi[0] and lo[1] < pt.y < hi[1] and lo[2] - 2.0 < pt.z < hi[2] + 2.0: return sn_
        return None
    # 선풍기 방 북쪽 벽의 굴진 막장 (사용자 10-03 판정 ③ "바람 관이 무슨 의미인지 모르겠다. 방 하나에 선풍기 하나가 달랑 남아 있어서 무슨 기구인지 인지가 안 된다. 실제로 어떻게 쓰이는지 확인 후 배치와 모델링").
    #   레퍼런스 공통점(보령석탄박물관 국부선풍기 · 독일 Sonderbewetterung 통기도 · La Mine Image · Idrija · Nowa Ruda 풍관 · 조사/09:514 · 09:642): 국부선풍기 = 바람이 안 통하는 막다른 굴(굴진 막장) 하나에
    #   관으로 새 바람을 밀어 넣는 기계 → 그 막다른 굴을 판다. 북쪽 벽(그 너머 12 m 넘게 빈 바위) · 북쪽 막장 줄과 같은 법(side_recess). 폭 3.2 · 깊이 12 m.
    #   높이 3.2 m (지시는 3.0 — 동발 캡 밑 = 천장 − 0.27 에 매단 지름 0.6 m 관의 밑이 바닥 위 2.0 m 를 넘게. 3.0 이면 잰 천장에 따라 1.95 m 안팎)
    e1 = N["E1"]; HEAD = dict(w=3.2, d=12.0, h=3.2, x=None); hw_ = HEAD["w"] / 2
    for hx_ in sorted({round(52.5 + 0.5 * k, 2) for k in range(-20, 21)}, key=lambda v: abs(v - 52.5)):   # 입 둘레를 비운다: 방 모서리에서 2 m · 개폐기(sw_E1, x 44.9)에서 2.5 m · 다른 방 · 굴과 1.6 m
        if not (e1["x"] - e1["w"] / 2 + hw_ + 2.0 <= hx_ <= e1["x"] + e1["w"] / 2 - hw_ - 2.0) or abs(hx_ - (e1["x"] - 4.1)) < hw_ + 2.5: continue
        if next((x for x in (near_air(Vector((hx_ + sx_, e1["y"] + e1["d"] / 2 + t_, 1.2)), "E1") for t_ in np.arange(0.5, HEAD["d"] + 0.01, 1.0) for sx_ in (-hw_, 0.0, hw_)) if x), None) is None: HEAD["x"] = float(hx_); break
    assert HEAD["x"] is not None, "E1 heading: no free north wall"
    REC.setdefault("E1", []).append(((Vector((0, 1, 0)), e1["x"] - HEAD["x"]), hw_))
    print("CHECK map4 E1 heading: mouth at x %.1f on the north wall, %.0f m deep, %.1f m wide, %.1f m high (no other room or tunnel within 1.6 m)" % (HEAD["x"], HEAD["d"], HEAD["w"], HEAD["h"]))
    for rid, side, want in CRACK_WANT:
        r = N[rid]; f = {"N": Vector((0, 1, 0)), "S": Vector((0, -1, 0)), "E": Vector((1, 0, 0)), "W": Vector((-1, 0, 0))}[side]; u = Vector((-f.y, f.x, 0)); Lw = (r["d"] if f.x else r["w"]) / 2 - 2.0
        want_t = want * (u.x + u.y)                                                            # 세계 좌표 쪽 → 벽 따라 자리
        ban = [(t_, hw + 2.2) for (f_, t_), hw, *_ in MOUTH.get(rid, []) + REC.get(rid, []) if (f_ - f).length < 0.1]; found = None; why = "no free wall"
        for t in sorted(np.arange(-Lw, Lw + 1e-6, 0.5), key=lambda t: abs(t - want_t)):
            w0 = wall_pt(r, f, t)
            if any(abs(t - bt) < bh for bt, bh in ban) or any((w0 - pt_).to_2d().length < hw_ + 2.4 for _, hw_, pt_, *_ in MOUTH.get(rid, [])): continue
            nb = min(ban, key=lambda b_: abs(t - b_[0]), default=None)
            for bend in ((1, -1) if nb is None or t >= nb[0] else (-1, 1)):                    # 같은 벽의 가장 가까운 홈 · 굴 입구에서 멀어지는 쪽으로 먼저 꺾는다 (막아 둔 채굴적: 울타리 뒤 9 m 홈으로 꺾여 무너진 돌 속에서 끝났다 — 10-03 검사)
                hit = next((x for x in (near_air(a_.lerp(b_, k_ / 3) + Vector((0, 0, 1.2)), rid) for a_, b_, _, _ in crack_path(w0, f, bend)[1:] for k_ in range(4)) if x), None)
                if hit is None: found = (t, w0, bend); break
                why = "would break into " + hit
            if found: break
        if found: t, w0, bend = found; CRACKS.append((rid, f, w0, bend)); REC.setdefault(rid, []).append(((f, t), 1.3))
        print("CHECK map4 monster crack %s wall %s: %s" % (rid, side, ("at (%.1f, %.1f) bend %+d" % (found[1].x, found[1].y, found[2])) if found else "NOT placed — " + why))
    def closet_spot(r, p):                                                                    # 방 r 의 벽에서 p 에 가장 가까운 '빈 벽' 자리 (굴 입구 · 홈 · 모서리 · 다른 문 칸에서 떨어진 곳)
        best = None
        for f in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0))):
            Lw = (r["d"] if f.x else r["w"]) / 2 - 1.5; u = Vector((-f.y, f.x, 0)); t0 = (Vector((p.x - r["x"], p.y - r["y"], 0))).dot(u)
            ban = [(t_, hw + 1.4) for (f_, t_), hw, *_ in MOUTH.get(r["id"], []) + REC.get(r["id"], []) if (f_ - f).length < 0.1] + [(t_, h_ + 0.9) for f_, t_, h_ in TAKEN.get(r["id"], []) if (f_ - f).length < 0.1]
            for t in sorted(np.arange(-Lw, Lw + 1e-6, 0.25), key=lambda t: abs(t - t0)):
                if all(abs(t - bt) > bh for bt, bh in ban) and all((wall_pt(r, f, t) - pt_).to_2d().length > hw_ + 1.6 for _, hw_, pt_, *_ in MOUTH.get(r["id"], [])):   # 옆 벽 모서리에 난 굴 입구도 (C13: 문틀 한쪽이 굴 입구에 걸렸다)
                    w_ = wall_pt(r, f, t); cost = (w_ - Vector((p.x, p.y, r["z"]))).length
                    if best is None or cost < best[0]: best = (cost, w_, f, t)
                    break
        return best
    TAKEN, ALC = {}, []
    for c in [n for n in plan["nodes"] if n["kind"] == "closet"]:
        p = Vector((c["x"], c["y"], c["z"])); room = next((r for r in rooms if abs(p.x - r["x"]) <= r["w"] / 2 + 1.0 and abs(p.y - r["y"]) <= r["d"] / 2 + 1.0), None); wide = (1.6, 1.15, 2.35); moved = 0.0
        if room is None:
            sg = min(SEG, key=lambda s: ((p - s["p"]) - (p - s["p"]).project(s["q"] - s["p"])).length if 0 <= (p - s["p"]).dot(s["q"] - s["p"]) <= (s["q"] - s["p"]).length_squared else 1e9)
            d = (sg["q"] - sg["p"]); d.z = 0; d.normalize(); t = (p - sg["p"]).dot(d) / max((sg["q"] - sg["p"]).length, 1e-6)
            if sg["kind"] in FAB_RUN or abs(sg["q"].z - sg["p"].z) > 0.3: room = min(rooms, key=lambda r: (Vector((r["x"], r["y"], 0)) - Vector((p.x, p.y, 0))).length)   # Fab 굴이면 조각 판자가 문을 가린다 → 가까운 방의 빈 벽으로
            elif t > 0.95 and sg["edge"]["b"] == c["id"]: wall, f = sg["q"].copy(), d.copy(); wide = (1.6, 1.15, 2.35, 2.4)   # 막다른 굴 끝(화약고): 끝 벽에 문, 그 너머 2 × 2.4 m 방 (옆벽에 달면 문틀 반이 끝 벽에 묻혔다)
            else:
                nrm = Vector((-d.y, d.x, 0)); nrm = -nrm if (p - sg["p"]).dot(nrm) < 0 else nrm; base = sg["p"].lerp(sg["q"], max(0, min(1, t)))
                wall, f = Vector((base.x, base.y, base.z)) + nrm * (KIND[sg["kind"]][0] / 2), nrm
        if room is not None:
            _, wall, f, t = closet_spot(room, p); TAKEN.setdefault(room["id"], []).append((f, t, 0.7)); moved = (wall - Vector((p.x, p.y, wall.z))).length
            KEEP.setdefault(room["id"], []).append((wall, 2.8))
        b = bmesh.new(); box(b, (0, 0, 0), wide[:3]); b.transform(Matrix.Translation(wall + f * (wide[0] / 2 - 0.3) + Vector((0, 0, wide[2] / 2))) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z"))
        if len(wide) > 3: box(b, wall + f * 2.0 + Vector((0, 0, 1.2)), (2.0 if abs(f.x) > 0.5 else wide[3], wide[3] if abs(f.x) > 0.5 else 2.0, 2.4))   # 문 뒤 방 (벽에서 1~3 m)
        AIR.append((b, 0.05, None)); ALC.append((c["id"], wall - f * 0.05, f, c["id"] == "MAG", moved, wide))
    # 벽에 붙는 소품 자리 (사용자 10-02 "떠 있는 물체": 가스 눈금판이 벽에서 4 m 떨어진 허공에, 게시판 · 전화 · 배전반은 벽 '가상의 평면'에서 0.3 m 앞에 — 실제 바위는 울퉁불퉁해 0.2~0.8 m 떴다.
    #   램프실 선반 · 배전반 · 창고 칸막이는 굴 입구를 가로막았다). 자리 = 굴 입구 · 홈 · 문 칸을 피한 빈 벽. 그 벽은 평평하게 두고(파는 깊이 0.05), 놓을 때 바위를 광선으로 재서 붙인다
    WSPOT = {}
    def wall_spot(key, rid, side, want, half):
        r = N[rid]; f = {"N": Vector((0, 1, 0)), "S": Vector((0, -1, 0)), "E": Vector((1, 0, 0)), "W": Vector((-1, 0, 0))}[side]; Lw = (r["d"] if f.x else r["w"]) / 2 - half - 0.4
        ban = [(t_, hw + 0.6 + half) for (f_, t_), hw, *_ in MOUTH.get(rid, []) + REC.get(rid, []) if (f_ - f).length < 0.1] + [(t_, h_ + half + 0.3) for f_, t_, h_ in TAKEN.get(rid, []) if (f_ - f).length < 0.1]
        t = next((t for t in sorted(np.arange(-Lw, Lw + 1e-6, 0.25), key=lambda t: abs(t - want)) if all(abs(t - bt) > bh for bt, bh in ban)), None)
        if t is None: print("CHECK map4 wall spot %s: no free wall on %s %s — placed at the wanted spot" % (key, rid, side)); t = want
        TAKEN.setdefault(rid, []).append((f, t, half)); w_ = wall_pt(r, f, t); WSPOT[key] = (r, f, t, w_); KEEP.setdefault(rid, []).append((w_, half + 1.2))
        b = bmesh.new(); box(b, (0, 0, 0), (0.24, half * 2 + 0.6, 2.8)); b.transform(Matrix.Translation(w_ + Vector((0, 0, 1.4))) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z")); AIR.append((b, 0.05, None))
        return w_, f
    for key, rid, side, want, half in (("pump_P", "P", "S", 1.95, 2.9), ("pump_R1", "R1", "S", 0.0, 3.3), ("sw_E1", "E1", "N", 4.1, 0.5), ("board_R0", "R0", "S", -1.0, 1.7), ("phone_R0", "R0", "S", 3.0, 0.4),
                                      ("rack_L", "L", "E", 0.0, 1.7), ("lamps_L1", "L", "S", 5.0, 1.3), ("lamps_L2", "L", "S", -5.0, 1.3), ("aid_H", "H", "N", -2.0, 0.9), ("phone_S1", "S1", "E", 2.0, 0.4), ("swb_X", "X", "E", 0.0, 3.4), ("store_K2", "K2", "N", 4.5, 3.2), ("st0_V", "V", "N", -10.0, 1.9), ("st1_V", "V", "N", -5.5, 1.9), ("st2_V", "V", "N", 9.0, 1.9),
                                      ("poles_W2", "W2", "N", 3.0, 0.5)): wall_spot(key, rid, side, want, half)
    for rid, ms in MOUTH.items(): KEEP.setdefault(rid, []).extend((pt, hw + 2.5) for _, hw, pt, *_ in ms)
    for rid, rs in REC.items(): KEEP.setdefault(rid, []).extend((wall_pt(N[rid], f, t), hw + 1.5) for (f, t), hw in rs)
    # 남겨 둔 석탄 기둥 (옛 채굴 빈터) = 파지 않은 바위. 사용자 10-03 "큰 구조물은 무슨 의미인지 · 가까이서 보면 사각형 폴리곤이 다 보인다": 옛 것은 방 안에 따로 세운 14각 통(column(), 0.8 m 고리 —
    #   면이 평평하게 찍혀 네모 판으로 보였고 바닥 · 천장을 그냥 뚫고 지났다). 레퍼런스(주방식 채굴 그림 · 사진): 기둥은 둥근 통이 아니라 캐다 남긴 네모난 덩어리 — 폭 수 m, 모서리가 떨어져 나가고 발치에 부스러기.
    #   이제: 방 공기를 기둥 자리만 빼고 판다 → 벽과 한 덩어리로 복셀 · 잔굴곡이 들어가고 바닥 · 천장과 이어진다. 겉은 탄층 띠(석탄 사진)로 칠한다 (tex1_sites 의 pillars)
    PILLARS = {"M": [(7.0, 5.0, 4.6, 3.8), (-6.0, -6.0, 3.6, 4.4)]}                            # 방 → [(가운데 dx, dy, 크기 x, y)]
    for n in rooms: n["pillars"] = [(n["x"] + a_, n["y"] + b_, c_, d_) for a_, b_, c_, d_ in PILLARS.get(n["id"], [])]
    FALL = {"K": (0.0, 0.0, 4.2, 3.0)}                                                         # 방 → 붕락 구멍 (가운데 dx, dy, 반지름, 천장 위 높이) — 돌 더미 바로 위
    # 천장 구멍 (사용자 10-03 판정 ③ ⓑ "벽 틈은 '여기서 나오겠다'로 읽히는데 천장은 '저기서 갑자기 나오는 듯 = 괴물이 저기서 생성된다'로 읽힌다" → 고친다(나)).
    #   옛 것: 곧게 6~7 m 뻗은 상자 하나 — 밑에서 올려다보면 끝까지 휑한 네모 굴뚝. 이제 벽 틈(crack_path)과 같은 법으로 세 토막: 입(세로 1.1 m) → 수직에서 50° 기울여 2.6 m (폭 0.9)
    #   → 수평 3.0 m (폭 0.7) — 밑 어디서 올려다봐도 끝이 안 보이고, 뒤 두 토막은 파는 깊이 0.05 로 좁게(사람 몸이 못 든다). 다른 방 · 굴 1.6 m 안으로 가는 쪽이면 45° 씩 돌려 다시 잰다 (near_air, 뒤 두 토막만).
    #   긁힌 자국 · 떨어진 돌은 아래 "천장 구멍 꾸밈". 자리 · 입 크기 · 먼저 기울일 쪽은 옛 것 그대로 (K = 붕락 구멍 꼭대기, M = 옛 채굴 빈터 천장의 긴 틈)
    CHIMNEY = {"K": (1.2, -0.5, 1.8, 1.5, (0, -1)), "M": (-1.0, 1.5, 3.4, 1.1, (0, 1))}       # 방 → (입 가운데 dx, dy, 입 폭 x, y, 먼저 기울일 쪽)
    def chim_path(c0, a):                                                                     # 입 가운데 c0 (천장 높이) → (꺾는 점 1, 꺾는 점 2, 끝, 둘째 토막 방향, 수평 방향)
        a = Vector((a[0], a[1], 0)).normalized(); d1 = a * math.sin(math.radians(50)) + Vector((0, 0, math.cos(math.radians(50))))
        p1 = c0 + Vector((0, 0, 1.1)); p2 = p1 + d1 * 2.6; return p1, p2, p2 + a * 3.0, d1, a
    CHIMS = {}
    for rid, (dx_, dy_, sx_, sy_, a0) in CHIMNEY.items():
        n = N[rid]; c0 = Vector((n["x"] + dx_, n["y"] + dy_, n["z"] + n["h"] + (FALL[rid][3] * 0.84 if rid in FALL else 0.0))); why = ""   # 천장 높이 (붕락 방 = 무너져 올라간 구멍의 셋째 판 꼭대기)
        for k_ in (0, 1, -1, 2, -2, 3, -3, 4):
            p1, p2, p3, d1, a = chim_path(c0, Matrix.Rotation(math.radians(45 * k_), 3, "Z") @ Vector((a0[0], a0[1], 0)))
            hit = next((x for x in (near_air(q, rid) for q in [p1.lerp(p2, t_) for t_ in (0.33, 0.66, 1.0)] + [p2.lerp(p3, t_) for t_ in (0.33, 0.66, 1.0)]) if x), None)   # 입 꼭대기(p1)는 빼고 잰다 — 방 가운데까지 이어 잰 굴 줄(F-M)이 방 천장 위 6 m 안을 다 막았다 (첫 굽기)
            if hit is None: CHIMS[rid] = (c0, p1, p2, p3, d1, a, sx_, sy_); break
            why = "would break into " + hit
        print("CHECK map4 ceiling chimney %s: mouth (%.1f, %.1f, %.1f) %s" % (rid, c0.x, c0.y, c0.z, ("leans toward (%+.2f, %+.2f), end (%.1f, %.1f, %.1f)" % (a.x, a.y, p3.x, p3.y, p3.z)) if rid in CHIMS else "NOT built — " + why))
    for n in rooms:
        b = bmesh.new(); rr = random.Random(n["id"])
        if n["pillars"]:                                                                      # 기둥 가장자리로 칸을 나눠, 기둥 칸만 빼고 상자를 놓는다 (2 cm 씩 겹쳐 한 덩어리로 합쳐진다)
            xs_ = sorted({n["x"] - n["w"] / 2, n["x"] + n["w"] / 2} | {px_ + s_ * sx_ / 2 for px_, py_, sx_, sy_ in n["pillars"] for s_ in (-1, 1)})
            ys_ = sorted({n["y"] - n["d"] / 2, n["y"] + n["d"] / 2} | {py_ + s_ * sy_ / 2 for px_, py_, sx_, sy_ in n["pillars"] for s_ in (-1, 1)})
            for xa, xb in zip(xs_, xs_[1:]):
                for ya, yb in zip(ys_, ys_[1:]):
                    if any(abs((xa + xb) / 2 - px_) < sx_ / 2 and abs((ya + yb) / 2 - py_) < sy_ / 2 for px_, py_, sx_, sy_ in n["pillars"]): continue
                    box(b, ((xa + xb) / 2, (ya + yb) / 2, n["z"] + n["h"] / 2), (xb - xa + 0.04, yb - ya + 0.04, n["h"]))
            for px_, py_, sx_, sy_ in n["pillars"]:                                           # 모서리 둘은 떨어져 나갔다 (네모 반듯한 기둥이 안 되게)
                for cx_, cy_ in rr.sample([(-1, -1), (1, -1), (-1, 1), (1, 1)], 2): blob(b, (px_ + cx_ * sx_ / 2, py_ + cy_ * sy_ / 2, n["z"] + rr.uniform(0.8, 2.2)), (rr.uniform(0.7, 1.1), rr.uniform(0.7, 1.1), rr.uniform(1.2, 2.2)), 2)
        else: box(b, (n["x"], n["y"], n["z"] + n["h"] / 2), (n["w"], n["d"], n["h"]))
        hx, hy, h = n["w"] / 2, n["d"] / 2, n["h"]; keep = KEEP.get(n["id"], []) + [(Vector((px_, py_, 0)), max(sx_, sy_) / 2 + 0.6) for px_, py_, sx_, sy_ in n["pillars"]]   # 기둥 위 천장은 안 판다 (기둥 머리가 천장에서 떨어진다)
        plain = lambda x_, y_, r_: any((Vector((x_, y_, 0)) - Vector((k.x, k.y, 0))).length < kr + r_ for k, kr in keep)
        for cx_, cy_ in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):                          # 네 모서리를 둥글게 (굴 입구 · 문 칸 가까운 모서리는 그대로 둔다)
            if not plain(n["x"] + cx_, n["y"] + cy_, 1.5): blob(b, (n["x"] + cx_ * 0.8, n["y"] + cy_ * 0.8, n["z"] + h * 0.45), (min(hx, 2.2), min(hy, 2.2), h * 0.5), 2)
        for _ in range(int((n["w"] + n["d"]) / 4)):                                             # 벽을 따라 불룩한 곳 (파낸 자국) — 난수는 그대로 뽑고, 굴 입구 · 문 칸 · 홈 둘레면 안 판다
            if rr.random() < 0.5: px, py = n["x"] + rr.uniform(-hx, hx), n["y"] + rr.choice((-hy, hy))
            else: px, py = n["x"] + rr.choice((-hx, hx)), n["y"] + rr.uniform(-hy, hy)
            pz = n["z"] + rr.uniform(0.9, h * 0.8); br = (rr.uniform(0.8, 1.8), rr.uniform(0.8, 1.8), rr.uniform(0.8, 1.5))
            if not plain(px, py, max(br[0], br[1])): blob(b, (px, py, pz), br, 2)
        for _ in range(max(1, int(n["w"] * n["d"] / 60))):                                      # 천장도 들쭉날쭉 (올리기만)
            cx_, cy_, br = n["x"] + rr.uniform(-hx, hx) * 0.7, n["y"] + rr.uniform(-hy, hy) * 0.7, (rr.uniform(1.5, 3.0), rr.uniform(1.5, 3.0), rr.uniform(0.5, 1.0))
            if not any(abs(cx_ - px_) < sx_ / 2 + br[0] and abs(cy_ - py_) < sy_ / 2 + br[1] for px_, py_, sx_, sy_ in n["pillars"]): blob(b, (cx_, cy_, n["z"] + h - 0.2), br, 2)   # 기둥 머리 둘레는 안 판다
        if n["id"] in CHIMS:                                                                  # 천장 구멍의 입 (세로 — 그 위 꺾인 두 토막은 방 공기 뒤에 따로, 좁게). 붕락 방은 무너져 올라간 구멍 속에서 시작한다
            c0, p1, *_, sx_, sy_ = CHIMS[n["id"]]; z0_ = c0.z - 1.2 if n["id"] in FALL else n["z"] + h - 0.4
            box(b, (c0.x, c0.y, (z0_ + p1.z + 0.3) / 2), (sx_, sy_, p1.z + 0.3 - z0_))
        if n["id"] in FALL:                                                                   # 붕락 구멍: 돌 더미 위 천장이 둥글게 떨어져 나갔다 (사용자 10-03 "붕락인데 위쪽 천장은 평평하고 깨끗하다").
            dx_, dy_, fr_, fh_ = FALL[n["id"]]                                                  #   레퍼런스(붕락 사진 다섯): 더미 바로 위 천장에 더미보다 조금 좁은 구멍, 가장자리가 층층이 깨져 들쭉날쭉(지층 판이 턱턱 떨어진다), 구멍 속은 방 천장보다 2~4 m 높다
            for k_, (sc_, zt_) in enumerate(((1.0, 0.35), (0.78, 0.62), (0.52, 0.84), (0.3, 1.0))):   # 둥근 공 하나면 물방울 같다 → 위로 갈수록 좁아지고 조금씩 돌아간 판 넷 (복셀 0.25 m 가 0.5~0.9 m 턱을 남긴다)
                z0_ = n["z"] + h - 0.3 if k_ == 0 else n["z"] + h + fh_ * (0.35, 0.62, 0.84)[k_ - 1] - 0.1
                box(b, (n["x"] + dx_ + rr.uniform(-0.5, 0.5), n["y"] + dy_ + rr.uniform(-0.4, 0.4), (z0_ + n["z"] + h + fh_ * zt_) / 2), (fr_ * 2 * sc_, fr_ * 1.6 * sc_, n["z"] + h + fh_ * zt_ - z0_), Matrix.Rotation(rr.uniform(-0.5, 0.5), 3, "Z"))
            for k_ in range(7):                                                                 #   가장자리가 떨어져 나간 자리
                a_ = rr.uniform(0, 6.28); blob(b, (n["x"] + dx_ + math.cos(a_) * fr_ * 0.9, n["y"] + dy_ + math.sin(a_) * fr_ * 0.72, n["z"] + h + rr.uniform(-0.1, 0.4)), (rr.uniform(0.8, 1.5), rr.uniform(0.8, 1.5), rr.uniform(0.5, 1.0)), 2)
        AIR.append((b, 0.45, None))
        if n["id"] in CHIMS:                                                                  # 천장 구멍의 꺾인 두 토막: 기운 것 폭 0.9 · 수평 폭 0.7 (파는 깊이 0.05 — 벽 틈 뒤쪽과 같은 법)
            c0, p1, p2, p3, d1, a, *_ = CHIMS[n["id"]]; b = bmesh.new(); box(b, (p1 - d1 * 0.25 + p2) / 2, (0.9, 0.9, 2.85), d1.to_track_quat("Z", "Y").to_matrix()); AIR.append((b, 0.05, None))
            b = bmesh.new(); box(b, (p2 - a * 0.35 + p3) / 2, (3.35, 0.7, 0.8), Matrix.Rotation(math.atan2(a.y, a.x), 3, "Z")); AIR.append((b, 0.05, None))
    print("CHECK map4 closets %d · moved more than 3 m from the plan spot: %s" % (len(ALC), "; ".join("%s %.1f m" % (a[0], a[4]) for a in ALC if a[4] > 3.0) or "none"))
    # 펌프 자리(펌프실 남쪽 벽): 받침 가운데 = 벽에서 1.2 m, 소품 자리표의 +y 가 벽 쪽. 물구덩이는 그 빨아들이는 관 끝 밑 (props/pump_set.py station() 의 자리: 받침에서 (-2.567, -0.5))
    def wall_frame(key, back=0.0, along=0.0):                                                  # 벽 소품 자리표 (벽 평면 기준 — 바위는 놓을 때 잰다): 원점 = 벽에서 back 만큼 방 안, 벽 따라 along
        r, f, t, w_ = WSPOT[key]; ex = Vector((f.y, -f.x, 0)); return Matrix.Translation(w_ - f * back + ex * along) @ Matrix.Rotation(math.atan2(f.y, f.x) - math.pi / 2, 4, "Z"), f, ex
    PUMP_P = wall_frame("pump_P", 1.2, 0.935)[0]; sump_c = PUMP_P @ Vector((-2.567, -0.5, 0))
    b = bmesh.new(); box(b, (sump_c.x, sump_c.y, sump_c.z - 0.3), (2.0, 1.5, 0.9)); AIR.append((b, 0.05, None))   # 펌프실 물구덩이 (깊이 0.75 m) — 방 바닥은 둘레 굴과 같은 높이 (0.5 m 낮은 바닥이 굴 끝마다 턱을 만들었다)
    def side_recess(r, f, depth, width, h, carve=0.1):                                        # 방 벽에서 f 쪽으로 파낸 곳 (막장 · 울타리 너머)
        wall = Vector((r["x"], r["y"], r["z"])) + f * (abs(f.x) * r["w"] / 2 + abs(f.y) * r["d"] / 2)
        b = bmesh.new(); box(b, (0, 0, 0), (depth + 0.4, width, h)); b.transform(Matrix.Translation(wall + f * (depth / 2 - 0.2) + Vector((0, 0, h / 2))) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z"))
        AIR.append((b, carve, None)); return wall
    n2 = N["N2"]; FACES = []; FACE_D = 7.0
    # 북쪽 막장 줄: 벽에 막장 셋 (협동 때 나눠 캔다). 사용자 10-03 "막장 굴 디자인이 이게 끝인가? 막장이라고 느껴지지 않는다": 옛 것은 3.4 × 5 × 2.4 m 맨 상자 + 석탄 덩이 스무 개.
    #   레퍼런스 공통점(조사 11 · 12, 사진 k03 k05 R02 R03 R05): 동발 틀이 0.5~1 m 마다 막장 벽 바로 앞까지 · 틀 위 짧은 덧판 · 끝 벽은 온통 석탄(반듯하지 않고 캐낸 자국) · 벽 발치에 쏟아진 탄 더미 · 연장.
    #   깊이 7 m(돌아보면 입구가 멀고 좁다) · 높이 2.7 m(틀 갓목 밑 2.35 m — 숙이지 않는다) · 끝 벽은 파인 자국 둘 + 발치 가로 홈(밑파기). 틀 · 더미 · 연장은 아래 N2 소품에서
    for dx in (-8, 0, 8):
        r_ = dict(n2); r_["x"] = n2["x"] + dx; wall_ = side_recess(r_, Vector((0, 1, 0)), FACE_D, 3.3, 2.7, 0.2); FACES.append((wall_, dx)); face_air.append((AIR[-1][0], n2["z"]))
        b = bmesh.new(); rr = random.Random("face%d" % dx)
        blob(b, wall_ + Vector((rr.uniform(-0.8, -0.4), FACE_D + 0.1, 1.3)), (1.15, 0.8, 1.0), 2); blob(b, wall_ + Vector((rr.uniform(0.4, 0.8), FACE_D + 0.2, 1.6)), (1.0, 0.75, 0.8), 2)
        box(b, wall_ + Vector((0.1, FACE_D + 0.25, 0.27)), (2.7, 0.7, 0.55)); AIR.append((b, 0.3, None))
    r_ = dict(N["E1"]); r_["x"] = HEAD["x"]; HEAD["wall"] = side_recess(r_, Vector((0, 1, 0)), HEAD["d"], HEAD["w"], HEAD["h"], 0.2)   # 선풍기 방 굴진 막장의 공기 (위 HEAD). 막장 면은 발파한 바위 면 그대로 (캐낸 자국을 안 판다 — 구멍 · 착암기는 소품 단계에서)
    FENCES = []
    for rid, gid in (("M", "GOAF_W"), ("E2", "GOAF_E")):                                       # 막아 둔 채굴적: 방 벽에서 2 m 파고 판자 울타리 (틈으로 어둠이 보인다, 못 들어감)
        r_, g = N[rid], N[gid]; d = Vector((g["x"] - r_["x"], g["y"] - r_["y"], 0)); f = Vector((1 if d.x > 0 else -1, 0, 0)) if abs(d.x) > abs(d.y) else Vector((0, 1 if d.y > 0 else -1, 0))
        FENCES.append((side_recess(r_, f, 9.0, 3.6, 3.0, 0.4), f, r_["z"]))                   # 깊이 9 m (옛 것 4 m: 울타리 2.5 m 뒤가 맨 바위 벽이라 "그 뒤에는 벽밖에 안 보인다" — 사용자 10-03). 울타리 뒤 3 m 부터는 무너진 돌 비탈이 천장까지 막는다 (아래 choke)
    for rid, f, w0, bend in CRACKS:                                                            # 괴물 틈 공기: 입은 넉넉히, 그 뒤는 폭 0.5 m (복셀 둘) — 파는 깊이를 0.05 로 묶어 사람 몸(0.8 m)이 못 든다
        for k_, (a_, b_, wd, hh) in enumerate(crack_path(w0, f, bend)):
            d_ = (b_ - a_); L_ = d_.length; b = bmesh.new(); F_ = Matrix.Translation((a_ + b_) / 2) @ Matrix.Rotation(math.atan2(d_.y, d_.x), 4, "Z")
            if k_ == 0:                                                                        # 입: 층층이 좁아지며 한쪽으로 기운 틈 (발치 1.35 m → 머리 위 3.3 m 에서 0.3 m)
                for z0_, z1_, w_, off in ((0.0, 1.05, 1.35, 0.0), (0.95, 1.85, 1.1, 0.1), (1.75, 2.6, 0.9, 0.18), (2.5, 3.4, 0.38, 0.36)): box(b, (0, off * bend, (z0_ + z1_) / 2), (L_, w_, z1_ - z0_))
            else: box(b, (0, 0, hh / 2), (L_, wd, hh))
            b.transform(F_); AIR.append((b, 0.3 if k_ == 0 else 0.05, None))
    lw, n2 = N["LW"], N["N2"]                                                                  # 서쪽 모임터 → 북쪽 막장 줄 6 m 세로 구멍 (사다리 오르기는 아직 없다 — 위에서 뛰어내리는 지름길)
    b = bmesh.new(); box(b, (lw["x"], lw["y"], (lw["z"] + n2["z"] + 3.0) / 2), (2.4, 2.4, n2["z"] - lw["z"] + 3.0)); AIR.append((b, 0.1, None))
    b = bmesh.new(); tp = Vector((lw["x"], lw["y"], n2["z"])); F_, L_ = frame(tp, Vector((n2["x"], n2["y"], 0)), n2["z"]); box(b, (L_ / 2, 0, 1.4), (L_, 2.6, 2.8)); b.transform(F_); AIR.append((b, 0.2, None))
    ld = N["LD"]; b = bmesh.new(); box(b, (ld["x"], ld["y"], ld["z"] - 6.0), (3.0, 3.0, 12.0)); AIR.append((b, 0.2, None))   # 2편으로 내려가는 사다리 구멍 (2편은 아직 없다)
    SHELL = unified_shell(); T1 = tex1_sites(rooms, N, SEG, zi, scene_air, face_air, SHELL)   # 벽 · 바닥 사진은 소품을 다 놓은 뒤 tex1_paint() 가 (채탄 막장의 석탄 벽 · 셰일 천장도 환경 표에서)
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
    # 비탈 굴의 걷는 길 (사용자 10-02 "바닥의 판이 무엇을 의미하는지 모르겠음"): 옛 것은 굴 끝점 높이 차가 0.5 m 넘으면 방 가운데에서 방 가운데까지 0.45 m 마다
    # 검은 판자를 깔아 평평한 방 바닥(펌프실 52장 · 물 속)에도 놓였고, 난간은 기둥만 서 있었다. 레퍼런스 공통점(사갱 보도): 한쪽 벽을 따라 이어진 발판 + 가로 미끄럼막이 + 이어진 손잡이 줄.
    # 이제: 진짜 비탈(기울기 12 % 넘는 굴)의 굴 구간에만, 한쪽으로 0.9 m 비켜서 — 세로 널 셋(0.66 m 폭) + 0.4 m 마다 가로 막대 + 기둥과 이어진 손잡이. 널은 부딪힘 없음(바위 바닥을 그대로 걷는다)
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); bmc = bmesh.new(); bmr = bmesh.new(); ways = []
    for s in SEG:
        p, q = s["p"], s["q"]; d = (q - p); d.z = 0; L = d.length; d.normalize(); nrm = Vector((-d.y, d.x, 0)); run_ = L - s["ta"] - s["tb"]
        if run_ < 3.0 or abs(q.z - p.z) < 0.5: continue
        def plank(bm_, a_, b_, wide, thick):                                                  # a → b 로 누운 널 (넓은 면이 위)
            x_ = (b_ - a_).normalized(); y_ = Vector((0, 0, 1)).cross(x_).normalized(); box(bm_, (a_ + b_) / 2, ((b_ - a_).length + 0.02, wide, thick), Matrix((x_, y_, x_.cross(y_))).transposed())
        pts, t = [], s["ta"] + 0.3
        while t < L - s["tb"] - 0.3:
            c = p.lerp(q, t / L) + nrm * 0.9; hit, f_, _, _, ob, _ = sc.ray_cast(deps, c + Vector((0, 0, 1.5)), Vector((0, 0, -1)), distance=4.0)
            if hit and ob.name.startswith("SHELL"): pts.append(f_.copy())
            t += 0.4
        if len(pts) < 6 or abs(pts[-1].z - pts[0].z) / max((pts[-1] - pts[0]).to_2d().length, 1e-6) < 0.12: continue   # 굴 구간 바닥을 재 본 기울기 (끝점 높이 차로 치면 방 안의 평평한 바닥까지 비탈로 쳤다)
        for a_, b_ in zip(pts, pts[1:]):
            for k_ in (-1, 0, 1): plank(bm, a_ + nrm * k_ * 0.225 + Vector((0, 0, 0.03)), b_ + nrm * k_ * 0.225 + Vector((0, 0, 0.03)), 0.2, 0.045)   # 세로 널 셋
            box(bmc, (a_ + b_) / 2 + Vector((0, 0, 0.075)), (0.06, 0.7, 0.04), Matrix.Rotation(math.atan2(d.y, d.x), 3, "Z"))                    # 가로 미끄럼막이
        tops = []
        for k_, a_ in enumerate(pts):
            if k_ % 5: continue
            hit, w_, *_ = sc.ray_cast(deps, a_ + Vector((0, 0, 1.0)), nrm, distance=3.0); post = a_ + nrm * (min((w_ - a_).to_2d().length - 0.25, 0.75) if hit else 0.6)   # 기둥은 벽 쪽 (벽에서 0.25 m)
            hit2, g_, *_ = sc.ray_cast(deps, post + Vector((0, 0, 1.5)), Vector((0, 0, -1)), distance=4.0); foot = g_ if hit2 else post
            box(bmr, foot + Vector((0, 0, 0.5)), (0.1, 0.1, 1.04)); tops.append(foot + Vector((0, 0, 0.95)))
        for a_, b_ in zip(tops, tops[1:]): plank(bmr, a_, b_, 0.07, 0.07)                                                                            # 이어진 손잡이
        ways.append("%s-%s %.0f m %.0f %%" % (s["edge"]["a"], s["edge"]["b"], run_, 100 * abs(pts[-1].z - pts[0].z) / (pts[-1] - pts[0]).to_2d().length))
    if bm.verts: box_uv(obj("NOCOL_WALKWAY", bm, M_TIMB).data, 0.8); box_uv(obj("NOCOL_WALKCLEAT", bmc, M_TAR_).data, 0.8)
    if bmr.verts: box_uv(obj("STEPRAIL", bmr, M_TAR_).data, 0.8)
    print("CHECK map4 incline walkways %d: %s" % (len(ways), "; ".join(ways) or "-"))
    # ---- 방마다 알아볼 소품 (설계의 "여기 있는 것"). 10-02 판정 ① 뒤 다시 지음: 상자 · 원통 블록아웃(펌프 · 선풍기 · 가스 눈금판 · 갱목 · 배전반 · 감개 …)을
    #   실제 탄광 사진 · 자료의 공통 구조로 만든 소품(props/*.py — 그림만 보고 무엇인지 맞히는 검수를 거쳤다)으로 바꾸고, 벽에 붙는 것은 바위를 광선으로 재서 붙인다.
    bpy.context.view_layer.update()
    def W(n, dx, dy, dz=0.0): return Vector((n["x"] + dx, n["y"] + dy, n["z"] + dz))
    def M_(n, dx, dy, yaw=0.0, dz=0.0): return Matrix.Translation(W(n, dx, dy, dz)) @ R(yaw)
    def boxes(name, mat, items):
        bm = bmesh.new()
        for c, s_, *rot in items: box(bm, c, s_, rot[0] if rot else None)
        o = obj(name, bm, mat); box_uv(o.data, 0.8); return o
    def rock(o_, d_, dist=10.0):                                                              # 바위(굴 겉면)까지 쏜다 — 소품에 먼저 맞으면 그 뒤에서 다시
        o_, d_, left = Vector(o_), Vector(d_), dist; deps_ = bpy.context.evaluated_depsgraph_get()
        for _ in range(8):
            hit, loc, nor, _i, ob, _m = sc.ray_cast(deps_, o_, d_, distance=left)
            if not hit: return None
            if ob.name.startswith("SHELL"): return loc, nor
            left -= (loc - o_).length + 0.02; o_ = loc + d_ * 0.02
            if left <= 0: return None
        return None
    def floor_at(x, y, z): h_ = rock((x, y, z + 1.0), (0, 0, -1), 3.0); return h_[0].z if h_ else z
    def roof_at(x, y, z): h_ = rock((x, y, z + 1.2), (0, 0, 1), 25.0); return h_[0].z if h_ else z + 3.0
    def on_floor(objs, x, y, z, yaw=0.0, sink=0.02): return PU.place(objs, Matrix.Translation((x, y, floor_at(x, y, z) - sink)) @ R(yaw))   # 바닥을 재서 2 cm 묻는다 (바위 바닥은 ±4 cm 울퉁불퉁)
    def at_wall(key, half=0.3, back=0.0, along=0.0):
        """벽 소품 자리표: 원점 = 그 자리 바위 벽면(광선 셋 가운데 방 쪽으로 가장 나온 곳)에서 back 만큼 방 안 · 바닥, +y = 벽 속, +x = 벽 따라. 돌려주는 값 (자리표, 벽면 점, 벽 방향)"""
        r, f, t, w_ = WSPOT[key]; ex = Vector((f.y, -f.x, 0)); c = w_ + ex * along; best = None
        for k_ in (-1, 0, 1):
            h_ = rock(c + ex * (k_ * half) - f * 1.5 + Vector((0, 0, 1.3)), f, 4.0)
            if h_ and (best is None or (h_[0] - c).dot(f) < best): best = (h_[0] - c).dot(f)
        wallp = c + f * (best if best is not None else 0.0); o_ = wallp - f * back; g_ = o_ - f * (0.4 if back < 0.3 else 0.0)
        return Matrix.Translation((o_.x, o_.y, floor_at(g_.x, g_.y, r["z"]) - 0.02)) @ Matrix.Rotation(math.atan2(f.y, f.x) - math.pi / 2, 4, "Z"), wallp, f
    def cable_up(M, lx, lz, ly=-0.03):                                                         # (안 쓴다 — 10-03: 벽 소품 자리의 평평한 홈이 2.8 m 높이라 천장 광선이 그 턱에 맞아, 검은 네모 막대가 벽 2.9 m 에서 끊겼다. 전화 · 개폐기의 전선관은 이제 소품 안에서 벽 속으로 꺾여 들어간다)
        p_ = M @ Vector((lx, ly, lz)); top = roof_at(p_.x, p_.y, p_.z - 1.0)
        if top - p_.z > 0.05: boxes("NOCOL_CABLE", PM["rubber"], [((p_.x, p_.y, (p_.z + top) / 2 + 0.05), (0.035, 0.035, top - p_.z + 0.1))])
    def mouth_of(rid, other): return next(m_ for m_ in MOUTH[rid] if m_[3] == other)           # 그 방에서 other 로 가는 굴 입구 (…, 반폭, 입구 점, 이어진 곳, 방 안쪽 방향, 굴 종류)
    def rail_end(rid, other): m_ = mouth_of(rid, other); return m_[2] - m_[4] * 0.6, m_[4]   # 굴 레일이 끝나는 곳(입구에서 굴 쪽 0.6 m) · 방 안쪽 방향
    def track(a, b, z): rails((a.x, a.y), (b.x, b.y), z)                                       # 방 안 레일 (굴 레일과 이어지게 — 레일이 방 벽에서 끊겨 있었다)
    def rails_slope(a, b):                                                                    # 비탈 굴의 레일: 조각마다 두 끝 바닥을 재서 눕힌다 (평평한 조각을 한 높이로 놓으면 뜨거나 묻힌다)
        d = Vector((b.x - a.x, b.y - a.y, 0)); L = d.length; d.normalize(); pl = lib("rail")[1]; x0, yc, z0 = lib("rail")[2]; n_ = max(1, round(L / pl)); k = L / (n_ * pl); yaw = math.atan2(d.y, d.x)
        for i_ in range(n_):
            p0 = a + d * (i_ * pl * k); p1 = a + d * ((i_ + 1) * pl * k); za = floor_at(p0.x, p0.y, a.z + (b.z - a.z) * i_ / n_); zb = floor_at(p1.x, p1.y, a.z + (b.z - a.z) * (i_ + 1) / n_)
            put("rail", Matrix.Translation((p0.x, p0.y, za)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(-math.atan2(zb - za, pl * k), 4, "Y") @ Matrix.Translation((-x0 * k, -yc, -z0)) @ Matrix.Diagonal((k, 1, 1, 1)))
    def water_sheet(name, c, sx, sy):                                                         # 고인 물: 잔물결 진 면 (반듯한 검은 판 한 장은 "밑에 있는 판"으로 보였다 — 사용자 10-03). 머리등 빛이 물결에 길게 맺힌다
        bm = bmesh.new(); g = bmesh.ops.create_grid(bm, x_segments=max(2, int(sx / 0.4)), y_segments=max(2, int(sy / 0.4)), size=0.5)
        for v in g["verts"]: x_, y_ = c.x + v.co.x * sx, c.y + v.co.y * sy; v.co = Vector((x_, y_, c.z + 0.012 * math.sin(x_ * 3.1 + y_ * 1.7) + 0.008 * math.sin(y_ * 4.3 - x_ * 2.2)))
        o_ = obj(name, bm, M_MURK); o_.data.polygons.foreach_set("use_smooth", np.ones(len(o_.data.polygons), dtype=bool)); return o_
    CART_BOX = {"ueujednfa": (2.059, 0.95, 1.556), "ufmodhpfa": (1.096, 0.767, 1.056), "ujzhahdfa": (2.303, 0.831, 1.061)}   # 광차 크기 (늘이기 전, m)
    def cart(n, dx, dy, yaw=0.0, fid="ueujednfa", tarp=False, seed=0):
        put(fid, M_(n, dx, dy, yaw, cart_z(fid))); CARTS.append((W(n, dx, dy), fid))           # 광차 긴 쪽 = yaw 쪽, 바퀴 디딤면이 레일 머리 위
        if tarp:                                                                              # 거적 (광차 + 거적 숨기, 카드 3) — 늘어진 천 한 장 + 밧줄 (옛 것: 납작한 판 셋이 광차를 가로질렀다)
            k_ = GAUGE / CART[fid][0]; L_, W__, H_ = (v * k_ for v in CART_BOX[fid])
            PU.place(cloth_.tarp(PM, L=L_ + 0.14, W=W__ + 0.14, H=H_ + cart_z(fid) + 0.04, seed=seed), M_(n, dx, dy, yaw))
    HEAPS = []                                                                                # 더미 (이름, 가운데 밑, 반지름 x · y, 높이) — 게임 검사 map4_heaps_solid 가 읽는 빈 노드로 나간다
    def pile(n, dx, dy, key, rx, ry, h, cnt, s0, s1):
        """돌 · 석탄 더미 = 속이 찬 둔덕(쏟아진 흙 · 가루) + 그 겉에 반쯤 묻힌 덩이. 큰 덩이는 발치로 굴러 내려가 있다.
        사용자 10-03 "돌 무더기를 일부러 이렇게 띄워 놓았나": 옛 것은 덩이를 '얹어' 쌓아(앞 덩이 위로 30 % 겹쳐) 가운데에 덩이 한 줄 탑이 서고, 덩이끼리 모서리만 닿아 떠 보였다
        (검사 map4_no_floating 은 상자가 5 cm 안이면 닿은 것으로 쳐서 통과). 레퍼런스(막장 발치 · 붕락 사진): 쏟아진 더미는 원뿔 — 비탈 35~40° 를 안 넘고, 덩이 사이는 가루가 메운다.
        둔덕 높이 = h, 발치 반지름 rx × ry (들쭉날쭉). 비탈이 tan 38° 를 넘지 않게 h 를 깎는다. 덩이는 둔덕 겉에 35 % 묻는다 — 덩이 위에 덩이를 얹지 않는다"""
        objs = lib(key)[0]; co_ = np.array([v.co[:] for o in objs for v in o.data.vertices]); x0, yc, z0 = lib(key)[2]; xc = (co_[:, 0].min() + co_[:, 0].max()) / 2
        h0 = np.ptp(co_[:, 2]); cx, cy = n["x"] + dx, n["y"] + dy
        h = min(h, 0.8 * 0.58 * min(rx, ry)); ph = [random.uniform(0, 6.28) for _ in range(4)]   # 발치가 가장 좁은 곳(× 0.81)에서도 비탈 tan 38° 를 안 넘게
        zf = min(floor_at(cx + ax_ * rx * 0.6, cy + ay_ * ry * 0.6, n["z"]) for ax_, ay_ in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
        def top(x, y):                                                                         # 둔덕 윗면 높이 (바닥 위) · 발치에서 가운데까지 0~1
            u, v = (x - cx) / rx, (y - cy) / ry; a_ = math.atan2(v, u); edge = 1 + 0.12 * math.sin(3 * a_ + ph[0]) + 0.07 * math.sin(5 * a_ + ph[1])
            t = max(0.0, 1 - math.hypot(u, v) / edge); bump = 0.025 * math.sin(x * 2.3 + ph[2]) * math.sin(y * 2.9 + ph[3])
            return h * ((t - 0.5 * max(0.0, t - 0.6) ** 2 / 0.4) / 0.8 + bump * min(1.0, t * 4)), t   # 곧은 비탈 + 둥근 꼭대기
        bm = bmesh.new(); NR, NS = 20, 64; rings = []; steep = 0.0
        for i in range(NR + 1):
            row = []
            for j in range(NS):
                a_ = 2 * math.pi * j / NS; edge = 1 + 0.12 * math.sin(3 * a_ + ph[0]) + 0.07 * math.sin(5 * a_ + ph[1]); r_ = (1 - i / NR) * edge * 1.02
                x, y = cx + math.cos(a_) * r_ * rx, cy + math.sin(a_) * r_ * ry
                row.append(bm.verts.new((x, y, zf + top(x, y)[0] - (0.15 if i == 0 else 0.0))))    # 발치 고리는 바닥 속 0.15 m
            if i > 1: steep = max(steep, max((b_.co.z - a_.co.z) / max((b_.co - a_.co).to_2d().length, 1e-6) for a_, b_ in zip(rings[-1], row)))
            rings.append(row)
        for A_, B_ in zip(rings, rings[1:]):
            for j in range(NS): bm.faces.new((A_[j], A_[(j + 1) % NS], B_[(j + 1) % NS], B_[j]))
        bm.faces.new(rings[-1])
        mo = obj("HEAP_%s_%d" % (key, len(HEAPS)), bm, HEAP_MAT[key]); mo.data.polygons.foreach_set("use_smooth", np.ones(len(mo.data.polygons), dtype=bool)); box_uv(mo.data, 0.8)   # 둔덕 겉 = 덩이 사이를 메운 흙 · 가루 (덩이 사진을 그대로 펴면 큰 바위 하나로 보인다)
        HEAPS.append((key, Vector((cx, cy, zf)), rx, ry, h)); print("CHECK map4 heap %d %s at (%.1f, %.1f) %.1f x %.1f m, height %.2f m, steepest slope %.0f deg, lumps %d" % (len(HEAPS) - 1, key, cx, cy, rx, ry, h, math.degrees(math.atan(steep)), cnt))
        for k_ in range(cnt):
            a_, r_ = random.uniform(0, 2 * math.pi), math.sqrt(random.random()) * (1.0 if k_ % 8 else 1.3)   # 여덟에 하나는 발치 밖까지 굴러 나간 덩이
            x, y = cx + math.cos(a_) * r_ * rx, cy + math.sin(a_) * r_ * ry; zt, t = top(x, y)
            s_ = s0 + (s1 - s0) * max(0.0, min(1.0, (1 - t) * 0.75 + random.uniform(0.0, 0.35)))   # 발치일수록 큰 덩이
            o_ = Vector((cx, cy, zf + h + 0.3)); dv = Vector((x, y, zf + zt + 0.25)) - o_
            if dv.length > 0.3 and rock(o_, dv.normalized(), dv.length): continue              # 벽에 기댄 더미: 바위 속에 들어가는 덩이는 안 놓는다 (더미 꼭대기 위에서 그 자리까지 바위에 안 막혀야 한다)
            tilt = Matrix.Rotation(random.uniform(-0.4, 0.4), 4, "X") @ Matrix.Rotation(random.uniform(-0.4, 0.4), 4, "Y")
            put(key, Matrix.Translation((x, y, zf + zt - h0 * s_ * 0.35)) @ R(random.uniform(0, 360)) @ tilt @ Matrix.Diagonal((s_, s_, s_, 1)) @ Matrix.Translation((-xc, -yc, -z0 - h0 * 0.15)))
        return lambda x, y: zf + top(x, y)[0]                                                  # 둔덕 윗면 높이 (세계 좌표) — 더미에 묻힌 것(부러진 동발)을 놓을 때
    def stuck_log(surf, x, y, yaw, pitch, L=2.2, r=0.1, seed=0, sink=0.3, old=True):
        """더미에 반쯤 묻힌 부러진 동발: 한쪽 끝은 둔덕 속, 다른 끝은 비스듬히 솟는다 (덩이 위에 얹지 않는다 — 떠 보인다)"""
        objs = timber_store.loose_log(PM, L, r * 2, seed)
        if old:
            for o_ in objs:
                if "END" not in o_.name: o_.data.materials[0] = PM["timber_old"]
        PU.place(objs, Matrix.Translation((x, y, surf(x, y) - sink)) @ R(yaw) @ Matrix.Rotation(math.radians(-pitch), 4, "Y") @ Matrix.Translation((L * 0.3, 0, -r)))
    def buffer_stop(e_, din, z):                                                              # 선로 끝의 나무 차막이 (Fab) — e_ = 레일 끝, din = 레일이 가던 방향
        x0_, yc_, z0_ = lib("ufekab3dw")[2]; L_ = lib("ufekab3dw")[1]; bp = e_ + din * 0.45
        put("ufekab3dw", Matrix.Translation((bp.x, bp.y, floor_at(bp.x, bp.y, z) - 0.02)) @ R(math.degrees(math.atan2(din.y, din.x))) @ Matrix.Diagonal((0.55, 0.55, 0.55, 1)) @ Matrix.Translation((-(x0_ + L_ / 2), -yc_, -z0_)))
    def bench(n, dx, dy, yaw=0.0, L=3.0):
        F = M_(n, dx, dy, yaw, floor_at(n["x"] + dx, n["y"] + dy, n["z"]) - n["z"] - 0.02); boxes("BENCH", M_TIMB, [(F @ Vector((0, 0, 0.45)), (L, 0.4, 0.06), F.to_3x3())] + [(F @ Vector((s_ * (L / 2 - 0.3), 0, 0.22)), (0.12, 0.35, 0.44), F.to_3x3()) for s_ in (-1, 1)])
    def rail_line(n, x0, y0, x1, y1): rails((n["x"] + x0, n["y"] + y0), (n["x"] + x1, n["y"] + y1), n["z"])
    def crate(x, y, z, yaw=0.0, up=0.0, scale=1.0): return PU.place(cc0_models.load("wooden_crate_01", cc0_models.DARK["wooden_crate_01"], scale=scale), Matrix.Translation((x, y, floor_at(x, y, z) - 0.02 + up)) @ R(yaw))
    DRUM_MAT = {}
    def barrel(x, y, z, yaw=0.0):
        """쇠 드럼통 (받아 온 모델). 모델의 파란 칠을 뺀다: 바탕색 그림을 잿빛으로 바꾸고 녹 갈색을 조금 입힌 사본 (glTF 는 색조 바꾸기 노드를 못 담아 그림 자체를 바꾼다)"""
        objs = cc0_models.load("barrel_03", cc0_models.DARK["barrel_03"])
        for o_ in objs:
            for k_, m_ in enumerate(o_.data.materials):
                if m_ is None or m_.name.endswith("_grey"): continue                             # 그물을 나눠 쓴다 — 한 번 바꾸면 다음 통도 같은 재질
                if m_.name not in DRUM_MAT:
                    t_ = m_.copy(); t_.name = m_.name + "_grey"
                    for nd in t_.node_tree.nodes:
                        if nd.type == "TEX_IMAGE" and nd.image and nd.image.colorspace_settings.name == "sRGB":
                            im = nd.image.copy(); im.name = nd.image.name + "_grey"; px = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4); g_ = px[:, :3] @ np.array([0.3, 0.55, 0.15], np.float32)
                            sat = px[:, :3].max(1) - px[:, :3].min(1); mix_ = np.clip(sat * 4, 0, 1)[:, None]      # 칠한 곳(색이 진한 점)만 잿빛으로, 녹 · 긁힌 곳은 그대로
                            px[:, :3] = px[:, :3] * (1 - mix_) + (g_[:, None] * np.array([0.95, 0.9, 0.82], np.float32)) * mix_; im.pixels = px.ravel(); im.pack(); nd.image = im
                    DRUM_MAT[m_.name] = t_
                o_.data.materials[k_] = DRUM_MAT[m_.name]
        return on_floor(objs, x, y, z, yaw)
    def pump_here(key, along, state, standby, sump):
        """배수 펌프 한 벌 (props/pump_set.py): 전동기 + 여러 단 펌프가 한 받침 위, 굵은 내보내는 관이 손잡이 밸브를 지나 벽을 타고 천장으로, 빨아들이는 관은 물구덩이로, 벽에 기동반"""
        M0, f, ex = wall_frame(key, 1.2, along); o_ = M0.translation; fz = floor_at(o_.x, o_.y, o_.z) - 0.02
        ds = [(h_[0] - (o_ + ex * a_)).dot(f) for a_ in (-0.3, 1.5, 3.0 if standby else 0.6) for h_ in [rock(o_ + ex * a_ + Vector((0, 0, 1.3)), f, 4.0)] if h_]; wd = min(ds) if ds else 1.2
        rz = roof_at((o_ + f * (wd - 0.15) - ex * 0.22).x, (o_ + f * (wd - 0.15) - ex * 0.22).y, fz)
        fn = pump_set.station if sump else pump_set.build; Mp = Matrix.Translation((0, 0, fz - o_.z)) @ M0
        PU.place(fn(PM, state=state, wall_d=wd, ceil_h=max(2.9, rz - fz), standby=standby, riser_top=3.0 if key in RISING else None, **({"broken": False, "stub": False} if state == "abandoned" else {})), Mp)
        print("CHECK map4 pump %s: wall %.2f m from the plinth, roof %.2f m" % (key, wd, rz - fz))
        if key in RISING:                                                                     # 내보내는 관을 수갱까지 잇는다 (세계 좌표의 꺾이는 점들) — 물은 수갱을 타고 땅 위로 올라간다
            a0 = Mp @ Vector((-0.22, wd - 0.13, 2.97)); pts = [a0, Vector((a0.x, a0.y, fz + RISING[key][0]))] + [Vector((x_ if x_ is not None else a0.x, y_ if y_ is not None else a0.y, z_)) for x_, y_, z_ in RISING[key][1]]
            pipe_run(pts); print("CHECK map4 rising main %s: %.0f m from the pump to the shaft top" % (key, sum((b_ - a_).length for a_, b_ in zip(pts, pts[1:]))))
    # 펌프실 배수 펌프의 내보내는 관이 가는 길 (사용자 10-03 "실제 배수구가 위쪽으로 이어지는지? 이게 끝인지?" — 옛 것은 펌프 위 천장 속으로 들어가 끝났고, 수갱 · 승강장에는 관이 없었다):
    #   펌프실 남쪽 벽을 따라 동쪽 → 승강장 남쪽 벽 → 천장 들보 옆으로 방을 건너 → 북쪽 벽 → 수갱 구석을 타고 위로. 높이 3.5 m (들보 밑 3.72 m 아래 · 머리 위)
    RISING = {"pump_P": (3.5, [(-8.45, None, 3.5), (-8.45, -4.42, 3.5), (-4.72, -4.42, 3.5), (-4.72, 4.42, 3.5), (-1.52, 4.42, 3.5), (-1.52, 5.3, 3.5), (-1.52, 5.3, 20.3)])}
    def pipe_run(pts, r=0.075, key="steel_red", name="RISINGMAIN"):
        """굵은 관 한 줄: 꺾이는 곳은 굽은 이음(엘보), 3 m 마다 플랜지, 누운 구간은 2.4 m 마다 천장에서 내린 걸쇠"""
        P = pump_set._Parts(PM, False); PU.sweep(P[key], pump_set._fillet(pts, 0.16, 3), r, 10); far = 1.5
        for a_, b_ in zip(pts, pts[1:]):
            d_ = b_ - a_; L_ = d_.length; d_.normalize(); t = far
            while t < L_ - 0.35:
                if t > 0.35: pump_set._joint(P, key, a_ + d_ * t, d_, r)
                t += 3.0
            far = t - L_
            if abs(d_.z) > 0.5 or L_ < 1.0: continue
            for t in np.arange(0.7, L_ - 0.3, 2.4):
                p_ = a_ + d_ * float(t); h_ = rock(p_ + Vector((0, 0, 0.1)), (0, 0, 1), 3.0)
                if h_: PU.box(P["iron"], (p_.x, p_.y, (p_.z + h_[0].z) / 2 + 0.05), (0.03, 0.03, h_[0].z - p_.z + 0.1)); PU.torus(P["iron"], p_, d_, r + 0.012, 0.012, 12, 5)
        return P.finish(name)
    # ---- 막장 연장 도구 (사용자 10-03 판정 ③ "막장의 디테일 부족" · "바람 관이 무슨 의미인지" — 소품은 props/face_kit.py). 레퍼런스: 한국 탄광 막장 사진 둘 + 수기 "에어 틀고 물 뿌려"
    #   (지역N문화 coalmine/story/3683) · 공기다리 착암기 사진 공통점 · 조사/01:26 · 03:29 · 11:23 · 12:26 · 12:63 · 12:68: 벽을 따라 관 두 줄(압축공기 · 물) → 끝 밸브 → 바닥을 기는 고무 호스 → 착암기
    #   (정이 발파 구멍에 꽂힌 채) · 막장 면 발파 구멍 20~25 (가운데 몰림 + 둘레 + 바닥 줄) · 분필 X 와 숫자 · 발치에 쏟아진 버력 · 삽
    HEAPTOP = {}                                                                              # 방 → 더미 윗면 높이 함수 (floor_at 은 소품을 뚫는다 — 붕락 방 천장 구멍 밑 돌을 더미 위에)
    def node(nm, p): e_ = bpy.data.objects.new(nm, None); e_.location = Vector(p); sc.collection.objects.link(e_)   # 검사(map4_fan_ducts · map4_air_lines · map4_ceiling_holes)가 읽는 빈 노드
    def pile_own(seed, *a):                                                                   # 새로 놓는 더미: pile() 은 전역 random 을 쓴다 — 뒤에 놓이는 것들의 모양이 안 바뀌게 그 상태를 되돌린다
        st_ = random.getstate(); random.seed(seed); out_ = pile(*a); random.setstate(st_); return out_
    def ground(x, y, z):                                                                      # 바닥 높이 = 바위 바닥이나 장면 바닥 판(FLOOR) — 채탄 막장은 바닥 판이 바위 위에 깔렸다 (floor_at 은 바위만 본다)
        deps_ = bpy.context.evaluated_depsgraph_get(); o_ = Vector((x, y, z + 1.0))
        for _ in range(6):
            hit, loc, _n, _i, ob, _m = sc.ray_cast(deps_, o_, Vector((0, 0, -1)), distance=3.0)
            if not hit: return z
            if ob.name.startswith(("SHELL", "FLOOR")): return loc.z
            o_ = loc - Vector((0, 0, 0.02))
        return z
    def first_hit(p, d, dist=4.0):                                                            # 아무것에나 처음 맞는 곳 (Fab 굴 조각의 덧댄 판처럼 바위 앞에 선 벽)
        hit, loc, nor, _i, ob, _m = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector(p), Vector(d), distance=dist); return (loc, nor) if hit else None
    def hug(a, b, z, f, gap=0.24, look=None):
        """a → b (벽 앞 기준선 위 두 점 (x, y)) 를 따라 f 쪽 벽에 붙여 가는 관 점들: 3 m 토막마다 벽을 0.25 m 간격 · 두 높이(z 와 물 관 z − 0.2)로 재서 가장 나온 곳에서 gap 만큼 띄운다.
        토막 사이 0.6 m 는 비스듬히 잇는다 (한 줄로 곧게 두면 바위가 물러난 곳에서 받침쇠가 벽에 안 닿는다 — 관은 이음마다 조금씩 꺾여 벽을 따른다)"""
        look = look or (lambda p_, d_: rock(p_, d_, 4.0)); a, b, f = Vector((a[0], a[1], z)), Vector((b[0], b[1], z)), Vector(f); L = (b - a).length; d = (b - a) / L; n_ = max(1, round(L / 3.0)); out = []
        def wall(s):
            ds = [(h_[0] - q).dot(f) for q in (a + d * s, a + d * s - Vector((0, 0, 0.2))) for h_ in [look(q, f)] if h_]
            return min(ds) if ds else 1.5
        for k in range(n_):
            s0, s1 = L * k / n_, L * (k + 1) / n_; dm = min(wall(s) for s in np.arange(max(0.0, s0 - 0.6), min(L, s1 + 0.6) + 1e-6, 0.25)) - gap
            out += [a + d * (s0 + (0.3 if k else 0.0)) + f * dm, a + d * (s1 - (0.3 if k < n_ - 1 else 0.0)) + f * dm]
        return out
    def meet(A, B):                                                                           # 두 벽의 관 줄을 모퉁이에서 잇는다 (A 끝 줄과 B 첫 줄이 만나는 점)
        p, d1 = A[-1], (A[-1] - A[-2]).normalized(); q, d2 = B[0], (B[1] - B[0]).normalized()
        t = ((q.x - p.x) * d2.y - (q.y - p.y) * d2.x) / (d1.x * d2.y - d1.y * d2.x); return A[:-1] + [p + d1 * t] + B[1:]
    def into_wall(p, d):                                                                      # 관 끝을 벽 속으로: p 에서 d 쪽 바위 겉면 너머 0.2 m (굴 한가운데서 끊기지 않게 — 사용자 10-03 "관이 양 끝에서 뚝 끊김")
        d = Vector(d); h_ = rock(p, d, 4.0); return p + d * (((h_[0] - p).dot(d) if h_ else 0.3) + 0.2)
    def drill_at(p, fwd, gz, seed=1):
        """착암기를 막장에 세운 꼴 (구멍을 뚫다 멈춤): p = 정이 꽂힐 자리 (x, y, 바닥 짐작), fwd = 면 쪽. 정 높이 = 다리 발 밑 바닥 + 1.2 m, 면은 광선으로 잰다. → (자리표, 호스 꼭지 점들, 구멍 점)"""
        fwd = Vector(fwd); ft = Vector((p[0], p[1], 0)) - fwd * 2.4; z_ = gz(ft.x, ft.y, p[2]) + face_kit.BODY_H
        h_ = rock(Vector((p[0], p[1], z_)) - fwd * 1.5, fwd, 3.5); hp = h_[0] if h_ else Vector((p[0], p[1], z_))
        jl, ends = face_kit.jackleg(PM, seed=seed); M = Matrix.Translation(hp) @ R(math.degrees(math.atan2(-fwd.y, -fwd.x))); PU.place(jl, M); return M, ends, hp
    def face_holes(c, fwd, right, fz, w, h, n_, seed, keep=()):
        """막장 면 발파 구멍 (face_kit.burn_pattern 자리): 면 앞 c(바닥 fz)에서 fwd 로 쏘아 실제 면 위 점 · 법선. 먼저 맞는 것이 바위가 아니면 (더미 · 착암기 · 동발에 가림) 그 구멍은 뺀다"""
        bpy.context.view_layer.update(); deps_ = bpy.context.evaluated_depsgraph_get(); out_ = []
        for u, v in face_kit.burn_pattern(w, h, n_, seed):
            o_ = Vector((c.x, c.y, fz + h / 2 + v)) + Vector(right) * u; hit, loc, nor, _i, ob, _m = sc.ray_cast(deps_, o_, Vector(fwd), distance=4.0)
            if hit and ob.name.startswith("SHELL") and all((loc - k).length > 0.18 for k in keep): out_.append((loc.copy(), nor.copy()))
        return out_
    def chalk_at(txt, p, fwd, size, seed):                                                    # 막장 면에 분필 (Rk08 "벽에 분필 X" · 조사/11:23 · 12:26) — 앞에서 fwd 로 쏘아 잰 면 위 점에, 면 앞에서 읽히게
        fwd = Vector(fwd); h_ = rock(Vector(p) - fwd * 1.0, fwd, 3.0)
        if h_: PU.place(face_kit.chalk(PM, txt, size, seed), Matrix.Translation(h_[0]) @ R(math.degrees(math.atan2(-fwd.y, -fwd.x)) + 90))
    def air_line(tag, V, wall_side, tap_out, Mj, ends, way, gz, wside):
        """압축공기 관(지름 0.1) + 그 0.2 m 밑 물 관(0.05 — 끝이 0.6 m 짧아 밸브 꼭지가 공기 관에 안 걸린다): 첫 끝은 벽 속, 다른 끝은 밸브 → 고무 호스가 바닥으로 내려와 way 를 지나 착암기 꼭지까지.
        V = 공기 관 가운데 줄 (세계 · 첫 점이 벽 속 · 끝에서 둘째 점이 밸브), tap_out = 밸브에서 방 쪽, way = 바닥 경유 점 [(x, y)], wside = 물 호스를 공기 호스 옆으로 비키는 만큼 (x, y).
        빈 노드 (검사 map4_air_lines): AIRP_<tag>_<00..> 관 줄 (3 m 안 간격) · VALVE_<tag>_0 공기 밸브 꼭지 · HOSEP_<tag>_<00..> 공기 호스 점 (00 = 밸브 쪽) · JACKLEG_<tag> 착암기 공기 꼭지"""
        V = [Vector(p) for p in V]; _, taps = face_kit.air_pipe(PM, V, 0.1, valves=(len(V) - 2,), wall_side=wall_side)
        dz = Vector((0, 0, 0.2)); dl = (V[-1] - V[-3]).normalized(); Ll = (V[-1] - V[-3]).length
        Wv = [p - dz for p in V[:-2]] + [V[-3] - dz + dl * (Ll - 0.85), V[-3] - dz + dl * (Ll - 0.6)]; _, wtaps = face_kit.air_pipe(PM, Wv, 0.05, valves=(len(Wv) - 2,), wall_side=wall_side)
        def drop(t, e, off, r):                                                               # 꼭지 → 바로 앞 바닥 → 경유 점 → 착암기 꼭지 (점마다 그 자리 바닥 높이, 1 m 안 간격)
            q = t + Vector(tap_out) * 0.25; out_ = [t - Vector((0, 0, 0.7 * r)), Vector((q.x, q.y, gz(q.x, q.y, t.z - 1.5)))]
            for x_, y_ in [(x_ + off[0], y_ + off[1]) for x_, y_ in way] + [(e.x, e.y)]:
                a_ = out_[-1]; n_ = max(1, math.ceil(math.hypot(x_ - a_.x, y_ - a_.y) / 1.0))
                for k in range(1, n_ + 1): cx_, cy_ = a_.x + (x_ - a_.x) * k / n_, a_.y + (y_ - a_.y) * k / n_; out_.append(Vector((cx_, cy_, gz(cx_, cy_, t.z - 1.5))))
            out_[-1] = e.copy(); return out_
        ho, wo = Mj @ ends["hose_out"], Mj @ ends["water_out"]; H_ = drop(taps[0], ho, (0, 0), 0.02)
        face_kit.hose(PM, H_, 0.04, 1, "AIRHOSE_" + tag); face_kit.hose(PM, drop(wtaps[0], wo, wside, 0.01), 0.02, 2, "WATERHOSE_" + tag)
        P_ = [V[0]]
        for a_, b_ in zip(V, V[1:]): n_ = max(1, math.ceil((b_ - a_).length / 3.0)); P_ += [a_.lerp(b_, k / n_) for k in range(1, n_ + 1)]
        for k, p in enumerate(P_): node("AIRP_%s_%02d" % (tag, k), p)
        for k, p in enumerate(H_): node("HOSEP_%s_%02d" % (tag, k), p)
        node("VALVE_%s_0" % tag, taps[0]); node("JACKLEG_%s" % tag, ho)
        print("CHECK map4 air line %s: pipe %.1f m (%d points, into the rock at one end, valve at the other) · air hose %.1f m to the drill · water pipe and hose beside it" % (tag, sum((b_ - a_).length for a_, b_ in zip(V, V[1:])), len(P_), sum((b_ - a_).length for a_, b_ in zip(H_, H_[1:]))))
    for n in rooms:
        i = n["id"]; w, dd = n["w"], n["d"]; METAL["wet"] = i in ("P", "R1")
        if i == "P":                                                                          # 펌프실: 배수 펌프 한 벌 + 판자 덮은 물구덩이 (남쪽 벽)
            pump_here("pump_P", 0.935, "working", False, True)
        elif i == "R0":                                                                       # 대기소 겸 신호소: 긴 의자 줄 · 게시판(+ 입갱표) · 갱내 전화
            for k in range(3): bench(n, -10 + k * 3.6, dd / 2 - 1.0)                            # 펌프실에서 오는 굴 입구(x −24.7) 앞을 비운다 — 걷기 검사가 찾음
            Mw, _, _ = at_wall("board_R0", 1.2); PU.place(wall_props.notice_board(PM, w=2.0, h=1.1), Mw)
            Mw, _, _ = at_wall("phone_R0", 0.3); PU.place(wall_props.phone(PM), Mw)
        elif i == "L":                                                                        # 램프실: 남쪽 벽(승강장에서 들어오면 정면) 굴 입구 양옆에 안전등 충전대 둘 + 건네는 대 · 동쪽 벽에 쇠 선반과 안전모 선반
            # 사용자 10-03 "램프실이라고 도착했을 때 이 의미를 알지 못하겠다": 램프가 하나도 없었고(연장 선반 + 안전모), 그나마 옆 벽에 붙어 들어오는 눈에 안 들어왔고, 방 가운데 전등 하나(4 m)는 그 벽에 안 닿았다
            for k_, key_ in enumerate(("lamps_L1", "lamps_L2")):
                Mw, _, _ = at_wall(key_, 1.3); PU.place(lamp_rack.build(PM, width=2.4, tiers=3, slots=10, filled=0.7 if k_ else 0.45, seed=k_ + 1), Mw)
            on_floor(lamp_rack.counter(PM, width=1.6, seed=1), n["x"] + 3.9, n["y"] - 0.2, n["z"], 0)
            Mw, _, _ = at_wall("rack_L", 1.6); PU.place(cc0_models.rack_full(PM), Mw @ Matrix.Translation((-1.05, -0.34, 0)))
            sh = Mw @ Matrix.Translation((0.75, 0, 0))
            boxes("SHELF", M_TIMB, [(sh @ Vector((0, -0.27, z_)), (2.0, 0.5, 0.05), sh.to_3x3()) for z_ in (0.8, 1.4)] + [(sh @ Vector((x_, -0.27, 0.77)), (0.08, 0.5, 1.54), sh.to_3x3()) for x_ in (-0.96, 0, 0.96)])
            for k in range(7): put("udklcbuiw", sh @ Matrix.Translation((-0.78 + (k % 4) * 0.5 + (0.25 if k > 3 else 0), -0.27, 0.845 + (k // 4) * 0.6)) @ R(random.uniform(0, 360)))
        elif i == "W1":                                                                       # 서쪽 모임터: 굴에서 이어진 본선 + 곁선(석탄 실은 광차 여섯, 한 대에 거적) + 연장 상자
            a_, din = rail_end("W1", "z3"); track(a_, Vector((n["x"] - w / 2 + 2.0, a_.y, 0)), n["z"]); y0 = a_.y - n["y"]
            rail_line(n, -9, y0 + 2.2, 8, y0 + 2.2); rails((n["x"] + 8, n["y"] + y0 + 2.2), (n["x"] + 11.5, n["y"] + y0), n["z"])   # 곁선 + 본선으로 드는 비낀 선
            for k, (x_, y_) in enumerate([(-2, 0), (0.5, 0), (3, 0), (0, 2.2), (2.5, 2.2), (5, 2.2)]): cart(n, x_, y0 + y_, 0, tarp=(k == 4), seed=1)   # 승강장 쪽 입구에서 8~15 m (옛 것 11.5~18.6 m: 머리등 14 m 끝이라 들어서면 빈 레일뿐이었다 — 사용자 10-03 "그저 모임터인가")
            buffer_stop(Vector((n["x"] - w / 2 + 2.0, a_.y, 0)), Vector((-1, 0, 0)), n["z"]); buffer_stop(Vector((n["x"] - 9, n["y"] + y0 + 2.2, 0)), Vector((-1, 0, 0)), n["z"])   # 본선 · 곁선 서쪽 끝 (맨바닥에서 그냥 끝나 있었다)
            crate(n["x"] - 10, n["y"] + dd / 2 - 1.3, n["z"], 12); crate(n["x"] - 8.9, n["y"] + dd / 2 - 1.2, n["z"], -8)
            PU.place(cc0_models.load("metal_toolbox", cc0_models.DARK["metal_toolbox"]), Matrix.Translation((n["x"] - 10, n["y"] + dd / 2 - 1.3, floor_at(n["x"] - 10, n["y"] + dd / 2 - 1.3, n["z"]) + 0.33)) @ R(30))
        elif i == "W2":                                                                       # 갱목 쌓는 곳: 둥근 갱목 더미 둘(말뚝 사이, 끝이 길 쪽) + 톱질 자리 + 벽에 기댄 가는 장대
            on_floor(timber_store.log_rack(PM, 2.4, 6, 1.6, seed=4), n["x"] - 4.6, n["y"] + 2.3, n["z"], 90); on_floor(timber_store.log_rack(PM, 1.8, 5, 1.4, seed=5), n["x"] - 1.9, n["y"] + 2.6, n["z"], 90)
            on_floor(timber_store.saw_station(PM, seed=2), n["x"] + 2.6, n["y"] - 2.4, n["z"], 25); on_floor(timber_store.loose_log(PM, 2.2, 0.18, 1), n["x"] - 1.0, n["y"] - 2.6, n["z"], -20)
            Mw, _, _ = at_wall("poles_W2", 0.3); PU.place(timber_store.pole_bundle(PM, seed=3), Mw)
        elif i == "F":                                                                        # 막장 앞 방: 물통 · 석탄 자루 더미
            barrel(n["x"] + 2.5, n["y"] + 2.5, n["z"]); on_floor(cloth_.sacks(PM, 6, seed=2), n["x"] - 2.2, n["y"] - 2.6, n["z"], 30)
        elif i == "M":                                                                        # 옛 채굴 빈터: 무너진 돌 언덕 둘 + 모양 다른 석탄 기둥 둘 (돌며 눈을 끊는다)
            pile(n, -7, 4, "stone", 4.5, 3.8, 1.9, 100, 3, 9); pile(n, 6, -5, "stone", 4.0, 3.8, 1.9, 90, 3, 8)   # 무너진 돌 언덕 둘 — 선 사람이 가려지는 높이(1.9 m). 석탄 기둥 둘은 방 공기를 팔 때 남겼다 (PILLARS)
        elif i == "K":                                                                        # 붕락 방: 가운데 큰 돌 더미 + 쓰러진 둥근 동발 + 여럿이 같이 세울 새 동발 자리 (카드 14)
            surf = pile(n, FALL["K"][0], FALL["K"][1], "stone", 6.6, 4.4, 2.6, 200, 3, 12); HEAPTOP["K"] = surf   # 천장 구멍(FALL) 바로 밑 — 떨어진 바위는 부풀어 구멍보다 넓게 퍼진다
            for k, (dx_, dy_, yaw_, pt_) in enumerate(((-3.2, 1.2, 200, 28), (1.8, -2.4, 310, 35), (3.6, 1.6, 20, 22), (-0.8, 2.9, 100, 40), (-4.6, -1.8, 160, 18))):   # 더미에 묻힌 부러진 동발 (기획서 4절 "무너진 막장: 부러진 동발 · 돌무더기")
                stuck_log(surf, n["x"] + dx_, n["y"] + dy_, yaw_, pt_, random.uniform(1.6, 2.4), 0.1, seed=k)
            for k in range(3): on_floor(timber_store.loose_log(PM, 2.3, 0.2, seed=k), n["x"] - 10.5 + k * 9.5, n["y"] + (6.4 if k % 2 else -6.5), n["z"], random.uniform(0, 180))
            # 서 있던 각재 둘(사용자 10-03 "두 나무 기둥은 무슨 의미인가")은 뺐다: Fab 각재의 원점이 발이 아니라 가운데 가까이여서 2.5 m 가 바닥 속에 묻히고 머리는 천장 2.4 m 밑 허공에서 끝났다.
            # "여럿이 같이 세우는 동발 자리"(카드 14)는 붕락 방에서 옛 채굴 빈터로 가는 옛 굴 입구로 — 천장이 2.7 m 라 진짜 길이(2~3 m)의 둥근 동발 틀이 선다. 아래 raising spot
            m_ = mouth_of("K", "M"); pt, din = m_[2], m_[4]; u_ = Vector((-din.y, din.x, 0)); q = pt - din * 0.55; yaw_ = math.degrees(math.atan2(din.y, din.x))   # 옛 채굴 빈터로 가는 옛 굴 입구 (방 벽에서 굴 쪽 0.55 m)
            fz_ = floor_at(q.x, q.y, n["z"]); rz = min(roof_at((q + u_ * s_).x, (q + u_ * s_).y, n["z"]) for s_ in (-0.8, 0.0, 0.8))
            PU.place(timber_sets.frame(PMD, width=2.6, height=rz - fz_ - FRAME_OVER, lean=0.12, lagging=3, seed=41), Matrix.Translation((q.x, q.y, fz_ - 0.02)) @ R(yaw_))   # 새로 세운 틀 하나 (썩은 옛 틀 줄 앞)
            k_ = pt + din * 1.3 + u_ * 3.8; on_floor(timber_sets.raising_kit(PM, seed=2, standing=False), k_.x, k_.y, n["z"], yaw_ + 90)   # 세우다 만 다음 틀의 재료 (입구 옆 벽 밑 — 이 방 천장은 5.5 m 라 기둥은 세우지 않고 눕혀 둔다)
            print("CHECK map4 raising spot K: new frame %.2f m high at (%.1f, %.1f), kit at (%.1f, %.1f)" % (rz - fz_, q.x, q.y, k_.x, k_.y))
            print("CHECK map4 fall K: roof above the heap centre %.1f m, room roof %.1f m, heap top %.1f m" % (roof_at(n["x"] + FALL["K"][0], n["y"] + FALL["K"][1], n["z"] + 3.0) - n["z"], n["h"], surf(n["x"] + FALL["K"][0], n["y"] + FALL["K"][1]) - n["z"]))
        elif i == "K2":                                                                       # 갱목 창고: 둥근 갱목 더미 · 우물 정 더미 · 판자 · 쐐기 상자 · 톱질 받침 (북쪽 벽) + 갱목 실은 광차
            Mw, _, _ = at_wall("store_K2", 2.8, 2.0); PU.place(timber_store.build(PM), Mw)
            on_floor(timber_store.log_rack(PM, 2.4, 5, 1.6, seed=7), n["x"] + 2.2, n["y"] - 2.9, n["z"], 0); on_floor(timber_store.cross_pile(PM, 1.1, 7, seed=2), n["x"] - 5.6, n["y"] - 3.2, n["z"], 15)
            # (갱목 실은 광차와 5 m 레일 토막은 뺐다 — 이 방으로 오는 굴 셋에는 레일이 없다. 사용자 10-03 "광차와 레일이 갑자기 있는 이유" 와 같은 흠)
        elif i == "S1":                                                                       # 남쪽 광차 조차장: 본선(북 ↔ 남) + 대피소 가는 갈래 + 곁선 둘(빈 광차, 한 대에 거적) + 갱내 전화
            a_, _ = rail_end("S1", "L"); track(a_, Vector((a_.x, n["y"] - dd / 2 + 2.0, 0)), n["z"]); x0 = a_.x - n["x"]
            b_, _ = rail_end("S1", "H"); track(Vector((a_.x, b_.y + 5.0, 0)), b_, n["z"])
            rail_line(n, x0 - 4, -11, x0 - 4, 9); rails((n["x"] + x0 - 4, n["y"] + 9), (n["x"] + x0, n["y"] + 12.5), n["z"])
            rail_line(n, x0 + 4, 2, x0 + 4, 13); rails((n["x"] + x0 + 4, n["y"] + 2), (n["x"] + x0, n["y"] - 1.5), n["z"])
            for k in range(4): cart(n, x0 - 4, -9 + k * 2.4, 90, "ufmodhpfa"); cart(n, x0 + 4, 4 + k * 2.4, 90, "ufmodhpfa", tarp=(k == 2), seed=2)
            buffer_stop(W(n, x0 - 4, -11), Vector((0, -1, 0)), n["z"]); buffer_stop(W(n, x0 + 4, 13), Vector((0, 1, 0)), n["z"])
            Mw, _, _ = at_wall("phone_S1", 0.3); PU.place(wall_props.phone(PM), Mw)
        elif i == "H":                                                                        # 갱내 대피소: 구급함 + 들것 · 물통 · 긴 의자 · 방을 지나는 레일
            a_, _ = rail_end("H", "S1"); b_, _ = rail_end("H", "R2"); mid = Vector((n["x"], (a_.y + b_.y) / 2, 0)); track(a_, mid, n["z"]); track(mid, b_, n["z"])
            Mw, _, _ = at_wall("aid_H", 0.7); PU.place(wall_props.first_aid(PM), Mw)
            barrel(n["x"] + 3, n["y"] + 3.4, n["z"]); barrel(n["x"] + 3.8, n["y"] + 3.3, n["z"], 40); bench(n, -2.5, -dd / 2 + 1.0)
        elif i == "R2":                                                                       # 선로 끝 방: 굴에서 이어진 레일 끝에 나무 차막이(Fab) + 거적 덮인 광차 + 흙 · 돌 둔덕
            a_, din = rail_end("R2", "H"); e_ = a_ + din * 8.4; track(a_, e_, n["z"]); yaw_ = math.degrees(math.atan2(din.y, din.x)); c_ = a_ + din * 6.6   # 5.0 이면 거적 자락이 표지 보는 자리(입구에서 3 m) 머리 위에 걸려 저절로 숙여졌다 (10-03 검사 map4_no_forced_crouch)
            cart(n, c_.x - n["x"], c_.y - n["y"], yaw_, tarp=True, seed=3)
            buffer_stop(e_, din, n["z"])
            sp = e_ + din * 1.9; pile(n, sp.x - n["x"], sp.y - n["y"], "stone", 1.2, 1.4, 0.6, 25, 2, 6)
        elif i == "R1":                                                                       # 물 고인 옛 펌프장: 발목 물 + 녹슨 펌프 한 벌과 빈 받침 (남쪽 벽)
            water_sheet("NOCOL_WATER", W(n, 0, 0, 0.19), w - 0.6, dd - 0.6)
            pump_here("pump_R1", -1.065, "abandoned", True, False)                               # 녹슨 펌프 한 벌 + 떼어 간 빈 받침. 내보내는 관은 온전히 천장까지 (옛 것은 가운데 토막이 빠져 벽에 관 토막 둘만 매달려 보였다)
            lp = WSPOT["pump_R1"][3] - WSPOT["pump_R1"][1] * 2.6; lamp_at(lp.x - 1.0, lp.y, n["z"], n["h"], "ZL_ffb070_%d", 50, (1.0, 0.69, 0.44))   # 펌프 위 작업등 하나 (불 없는 방이라 입구에서 펌프가 안 보였다 — 사용자 10-02 "무엇을 뜻하는지 확인이 안 된다")
        elif i == "E1":                                                                       # 선풍기 방 = 북쪽 벽 굴진 막장(HEAD)에 새 바람을 보내는 곳: 국부 선풍기 → 관 → 막장 · 벽 개폐기 · 압축공기 관 → 착암기
            # 사용자 10-03 판정 ③ "바람 관이 무슨 의미인지 모르겠다. 방 하나에 선풍기 하나가 달랑 남아 있어서 무슨 기구인지 인지가 안 된다. 실제로 어떻게 쓰이는지 확인 후 배치와 모델링".
            #   옛 것: 선풍기 → 방 안 10 m 천 관 → 찢긴 끝이 방 바닥에 누움 (바람이 갈 곳이 없었다). 레퍼런스 1~5 (보령석탄박물관 국부선풍기 · Sonderbewetterung 통기도 · La Mine Image · Idrija · Nowa Ruda 풍관):
            #   선풍기는 새 바람이 오는 쪽(서쪽 바람문 굴)을 빨아들이는 입으로 보고 막다른 굴 입구 밖(9 m 넘게) 벽 앞에 · 관은 출구에서 올라가 북쪽 벽을 따라 동쪽으로 가다 굴 입구에서
            #   북쪽으로 꺾여 굴 천장 동쪽 모서리(동발 캡 밑)에 매달려 막장 4~5 m 앞에서 열린 입으로 끝난다 (법: 풍관 끝은 막장에서 7 m 안 — 조사/09:642) · 통에 흰 페인트 번호
            hx, hy0, hd = HEAD["x"], n["y"] + dd / 2, HEAD["d"]; Fh = Vector((0, 1, 0)); hwh = HEAD["w"] / 2; caps = []; yv = 0.7
            while yv < hd - 1.3:                                                              # 동발 틀: 북쪽 막장 줄과 같은 법 (입구 0.7 m 안쪽부터 막장 1.3 m 앞까지 1 m 마다 · 1988 = 나무 동발 시대). 폭 2.5 — 기둥 바깥 벽 쪽으로 관 두 줄이 지난다
                py = hy0 + yv; fz_ = floor_at(hx, py, n["z"]); rz = min(roof_at(hx + sx_, py, n["z"]) for sx_ in (-0.9, 0.0, 0.9))
                PU.place(timber_sets.frame(PMD, width=2.5, height=rz - fz_ - FRAME_OVER, lean=0.13, lagging=4, seed=300 + int(yv), bay=1.0 if yv + 1.0 < hd - 1.3 else None), Matrix.Translation((hx, py, fz_ - 0.02)) @ R(90))
                caps.append((py, rz - FRAME_OVER - 0.02)); yv += 1.0
            fh_ = rock((hx, hy0 + hd - 2.0, n["z"] + 1.5), Fh, 6.0); HEAD["face"] = face_y = fh_[0].y if fh_ else hy0 + hd; fzf = floor_at(hx, face_y - 1.0, n["z"])   # 막장 면 (잰 곳)
            node("DFACE_E1", (hx, face_y - 0.2, fzf + 1.5))
            pile_own("E1 muck", dict(x=hx + 0.75, y=face_y - 0.6, z=n["z"]), 0, 0, "stone", 0.85, 0.65, 0.45, 22, 2, 5)   # 발파 뒤 발치에 쏟아진 버력 (조사/12:63) — 작은 더미 (착암기 옆을 비운다)
            Mj, ends, hp = drill_at((hx - 0.45, face_y, n["z"]), Fh, floor_at, seed=1)        # 착암기: 정이 막장 면 구멍 하나에 꽂힌 채 (몸통이 서쪽 — 호스 꼭지는 동쪽으로 나온다)
            face_kit.drill_holes(PM, face_holes(Vector((hx, face_y - 1.0, 0)), Fh, (1, 0, 0), fzf, 2.9, 2.9, 24, 1, keep=(hp,)) + [(hp, -Fh)])   # 굴진(바위) 막장 면의 발파 구멍 (조사/01:26 · 12:68)
            chalk_at("X", (hx + 0.85, face_y, fzf + 2.2), Fh, 0.22, 1); chalk_at("12", (hx - 0.95, face_y, fzf + 2.45), Fh, 0.14, 2)
            sx0, syc, sz0 = lib("uddjeelqx")[2]; sL = lib("uddjeelqx")[1]; sp = Vector((hx + 0.6, face_y - 2.3, 0))
            put("uddjeelqx", Matrix.Translation((sp.x, sp.y, floor_at(sp.x, sp.y, n["z"]) + 0.01)) @ R(95) @ Matrix.Translation((-(sx0 + sL / 2), -syc, -sz0)))   # 삽 (버력 치우는)
            zd = min(c_ for _, c_ in caps) - 0.40                                              # 관 가운데 높이 = 가장 낮은 캡 밑 − 0.4 (관 위 0.38 m 를 쇠줄이 지난다) — 방에서도 같은 높이 (꺾어 내리지 않는다)
            fx, fy = n["x"] - 6.0, n["y"] + dd / 2 - 1.7; fz = floor_at(fx, fy, n["z"]) - 0.01; Mf = Matrix.Translation((fx, fy, fz))   # 선풍기 자리는 그대로 (북쪽 벽 1.7 m 앞 · 빨아들이는 입 = 서쪽)
            Mw, _, _ = at_wall("sw_E1", 0.4); PU.place(wall_props.switch_box(PM), Mw)          # 개폐기 (정전 뒤 사람이 손으로 켠다 — 조사/09:771)
            PU.place(fan_duct.fan(PM, outlet_z=zd - fz, cable_to=tuple(Mf.inverted() @ (Mw @ Vector((-0.2, -0.12, 0.03)))), number="3"), Mf)
            dx_ = hx + 0.5; x0_ = fx + 1.95; k_ = max(2, round((dx_ - x0_) / 2.0)); end_y = face_y - 4.4
            dp = [(x0_ + (dx_ - x0_) * j / k_, fy, zd, roof_at(x0_ + (dx_ - x0_) * j / k_, fy, n["z"])) for j in range(k_ + 1)]   # 방: 출구에서 북쪽 벽을 따라 동쪽으로, 2 m 마다 천장 걸이 · 마지막 점에서 북쪽으로 꺾인다 (쇠 굽은 토막)
            ins = [c_ for c_ in caps if c_[0] < end_y + 0.5]; dp += [(dx_, py, zd, cz) for k2, (py, cz) in enumerate(ins) if k2 % 2 == 0 or k2 == len(ins) - 1]   # 굴: 동발 캡에 2 m 마다 건다 · 막장 4~5 m 앞에서 끝
            _, dline = fan_duct.duct(PM, dp, end="open", seed=3, floor_z=[floor_at(p_[0], p_[1], n["z"]) for p_ in dp])
            node("FAN_E1", dp[0][:3]); cum = [0.0]
            for a_, b_ in zip(dline, dline[1:]): cum.append(cum[-1] + (b_ - a_).length)
            nd_ = max(1, math.ceil(cum[-1] / 2.0))                                              # DUCTP = 관 가운데 줄을 2 m 안 간격으로 (굽은 곳도 그 줄 위)
            for k2 in range(nd_ + 1): node("DUCTP_E1_%02d" % k2, dline[min(range(len(cum)), key=lambda q: abs(cum[q] - cum[-1] * k2 / nd_))])
            print("CHECK map4 E1 fan duct: centre %.2f m · lowest underside %.2f m above the floor (with sag) · %.1f m long · open end %.1f m from the face · fan %.1f m from the face · frames %d" % (
                zd, min(p_.z - floor_at(p_.x, p_.y, n["z"]) for p_ in dline) - 0.32, cum[-1], face_y - dline[-1].y, (Vector((x0_, fy, 0)) - Vector((hx, face_y, 0))).length, len(caps)))
            zp = n["z"] + 2.0; xw = n["x"] - w / 2                                              # 압축공기 · 물 관 (높이 2.0 · 1.8 — 개폐기 1.65 위): 바람문 굴 입구 북쪽 서쪽 벽에서 나와 → 북쪽 벽 → 굴 서쪽 벽(동발 기둥 바깥)으로 막장 3 m 앞까지
            Ln = meet(meet(hug((xw + 1.2, n["y"] + 2.9), (xw + 1.2, hy0 - 1.0), zp, (-1, 0, 0)), hug((xw + 1.0, hy0 - 1.0), (hx - hwh - 0.3, hy0 - 1.0), zp, (0, 1, 0))),
                      hug((hx - hwh + 0.9, hy0 + 0.3), (hx - hwh + 0.9, face_y - 3.0), zp, (-1, 0, 0))); dl_ = (Ln[-1] - Ln[-2]).normalized()
            air_line("E1", [into_wall(Ln[0], (-1, 0, 0))] + Ln[:-1] + [Ln[-1] - dl_ * 0.25, Ln[-1]], (-1, 1, 0), (1, 0, 0), Mj, ends, [(hx - 0.6, face_y - 2.75)], floor_at, (0, -0.12))
            SHOTS.append(("heading_E1", (n["x"] - 3.5, n["y"] - 2.5, floor_at(n["x"] - 3.5, n["y"] - 2.5, n["z"]) + EYE), (n["x"] - 1.5, hy0, n["z"] + 2.0)))   # [ ] 자리: 방 남서쪽에서 선풍기 → 관 → 굴 입구가 한 화면에
            SHOTS.append(("face_E1", (hx - 0.2, face_y - 6.5, floor_at(hx - 0.2, face_y - 6.5, n["z"]) + EYE), (hx, face_y, fzf + 1.3)))   # [ ] 자리: 굴 안에서 막장 면 (관 끝 · 착암기 · 발파 구멍 · 버력)
        elif i == "E4":                                                                       # 옛 권양기 방: 작은 권양기(감개 · 큰 톱니 · 전동기 · 제동 손잡이) — 끊어진 쇠줄은 바닥에
            # 사용자 10-03 "권양기 방이 무엇을 뜻하는지 모르겠다": 옛 것은 방 한쪽에 감개만 덩그러니 — 줄이 어디로 가는지, 무엇을 끄는지가 없었다.
            #   권양기 = 쇠줄로 광차를 비탈 위로 끌어올리는 감개 (레퍼런스: 직접 끄는 줄 운반 — 감개는 비탈 머리에, 줄은 레일 사이로 비탈을 내려간다). 이 방은 막아 둔 채굴적 입구(E2)에서 올라오는 비탈의 머리다.
            #   → 감개를 그 굴 입구를 보게 놓고, 굴 입구에서 감개 앞까지 레일 + 비탈 굴 속 레일(바닥을 재서 눕힘) + 통에서 풀려 레일 사이로 비탈을 내려가다 끊긴 쇠줄
            a_, din = rail_end("E4", "E2"); wx = a_ + din * 7.2; on_floor(machines.winch(PM, "abandoned"), wx.x, wx.y, n["z"], math.degrees(math.atan2(-din.y, -din.x)))
            track(a_, a_ + din * 5.4, n["z"]); a2, _ = rail_end("E2", "E4"); rails_slope(Vector((a2.x, a2.y, N["E2"]["z"])), Vector((a_.x, a_.y, n["z"])))
            rope = []
            for t in np.arange(5.0, -7.4, -0.5):
                q = a_ + din * float(t); zq = floor_at(q.x, q.y, n["z"] - (0.0 if t > 0 else 0.5)) + 0.115                              # 침목 위에 얹혀 내려간다
                rope.append(Vector((q.x - din.y * 0.07 * math.sin(t * 1.3), q.y + din.x * 0.07 * math.sin(t * 1.3), zq)))
            bm = bmesh.new(); PU.sweep(bm, rope, 0.013, 6); PU.obj("NOCOL_HAULROPE", bm, PM["iron"], smooth=True)
        elif i == "E2":                                                                       # 막아 둔 옛 채굴적 입구: 권양기 방 비탈에서 내려온 옛 선로가 울타리 밑으로 무너진 채굴적 속으로 (설계의 "녹슨 레일 토막")
            a_, din = rail_end("E2", "E4"); wall_, f_, _ = FENCES[1]; p1 = a_ + din * 4.5; p2 = wall_ - f_ * 2.8
            track(a_, p1, n["z"]); track(p1, p2, n["z"]); track(p2, wall_ + f_ * 0.9, n["z"]); track(wall_ + f_ * 2.1, wall_ + f_ * 4.7, n["z"])   # 울타리(벽에서 1.5 m) 앞뒤 0.6 m 는 비운다
        elif i == "E3":                                                                       # 쓰러진 광차 굽이: 넘어진 광차 + 쏟아진 석탄
            put("ueujednfa", M_(n, 0, 1.5, 30) @ Matrix.Translation((0, 0, 0.63)) @ Matrix.Rotation(math.radians(100), 4, "X")); pile(n, 1.5, -0.5, "coal", 1.5, 1.0, 0.5, 30, 2, 5)
        elif i == "V":                                                                        # 옛 창고 칸 줄: 판자 칸막이 일곱(벽까지) + 칸마다 상자 · 통 · 자루 (앞을 막던 가로 판은 뺌 — 굴 입구와 문 칸 둘을 막았다)
            # 사용자 10-03 "창고 칸이 너무 허전하다": 옛 것은 칸막이가 통짜 판 한 장(0.08 × 3 × 2.2 m)이고 칸마다 통 둘 · 자루 몇 개뿐이었다.
            #   이제(props/store_stalls.py): 기둥 · 띠장 · 세운 판자로 짠 칸막이 일곱 + 칸마다 다른 것 — 레일과 침목 · 기름통 · 관 · 연장 · 쇠줄 · 바람 관. 이 광산의 다른 곳에서 쓰는 물건들이다
            busy = [m_[2].x for m_ in MOUTH.get("V", []) if m_[0][0].y < -0.5] + [a[1].x for a in ALC if a[0] in ("C10", "C11")]; back = lambda x_: (lambda h_: h_[0].y if h_ else n["y"] - dd / 2)(rock((x_, n["y"] - dd / 2 + 3.0, n["z"] + 1.1), (0, -1, 0), 6.0))
            for k in range(7):
                x_ = n["x"] - w / 2 + 2 + k * 4; yb = back(x_)
                PU.place(store_stalls.partition(PM, depth=n["y"] - dd / 2 + 3.0 - yb + 0.1, height=2.2, seed=k), Matrix.Translation((x_, yb - 0.1, floor_at(x_, yb + 1.5, n["z"]) - 0.02)) @ R(180))   # 벽 속 0.1 m 에서 시작해 방 쪽으로
            spare = []
            for k, kind in enumerate(("rails", "drums", "pipes", "tools", "rope", "duct")):
                cx = n["x"] - w / 2 + 4 + k * 4
                if any(abs(cx - b_) < 2.6 for b_ in busy): spare.append((k, kind)); continue
                yb = max(back(cx - 1.2), back(cx), back(cx + 1.2))                                # 가장 방 쪽으로 나온 벽에 맞춘다
                PU.place(store_stalls.fill(PM, kind, width=3.4, depth=2.4, seed=k), Matrix.Translation((cx, yb + 0.05, floor_at(cx, yb + 1.2, n["z"]) - 0.02)) @ R(180))
            for (k, kind), key in zip(spare, ("st0_V", "st1_V", "st2_V")):                        # 판자 문 칸 둘 · 배전실 굴 입구가 차지한 칸의 몫은 맞은편(북쪽) 벽 밑에 — 10-03 캡처: 여섯 칸 중 셋만 채워져 여전히 허전했다
                Mw, _, _ = at_wall(key, 1.7, 0.05); PU.place(store_stalls.fill(PM, kind, width=3.4, depth=2.4, seed=k), Mw)
        elif i == "X":                                                                        # 옛 배전실: 옛 배전반 석 장(둥근 계기 · 칼 스위치 · 한 장은 덮개 없이 구리 띠가 보임) + 천장으로 가는 케이블 (동쪽 벽)
            # 사용자 10-03 "실제 배전실의 구조가 이렇게 생겼는지? 배전실이라고 생각이 들지 않는다": 옛 것은 빈 방 벽에 계기판 석 장뿐.
            #   레퍼런스(갱내 변전실 사진 셋 · 변압기 사진): 바닥에 선 쇠 함(큐비클)이 벽을 따라 한 줄 + 옆에 기름 변압기 + 함 위에서 천장으로 올라가 벽을 타는 굵은 케이블 다발 + 앞의 막이와 "고압 위험" 판 + 불 끄는 모래
            Mw, wallp, f_ = at_wall("swb_X", 2.9); PU.place(substation.build(PM, cubicles=4, wall_d=0.0, ceil_h=roof_at((wallp - f_ * 0.5).x, (wallp - f_ * 0.5).y, n["z"]) - Mw.translation.z, state="old", seed=1), Mw)
        elif i == "N1":                                                                       # 윗 탄층 저탄장: 석탄 더미 + 레일 위 거적 덮인 광차
            pile(n, -3, 0, "coal", 5.0, 3.5, 2.0, 120, 2, 7)
            # 레일: 북쪽 막장 줄에서 쇠동발 길을 지나 이 석탄 더미 발치까지 (막장에서 캔 탄을 광차로 실어 와 쌓는 곳). 사용자 10-03 "천이 덮인 광차와 레일이 갑자기 있는 이유":
            #   옛 것은 방 한가운데 8 m 토막 — 10-02 "광차가 레일 위에 없다" 를 고치며 광차 밑에만 깔았고, 이 방으로 오는 굴(돌계단 · 쇠동발 길)에는 레일이 없었다
            a_, din = rail_end("N1", "N2"); e_ = a_ + din * 7.2; track(a_, e_, n["z"]); buffer_stop(e_, din, n["z"]); c_ = a_ + din * 4.2
            cart(n, c_.x - n["x"], c_.y - n["y"], math.degrees(math.atan2(din.y, din.x)), tarp=True)
            b_, _ = rail_end("N2", "N1"); track(b_, a_, n["z"])                                 # 쇠동발 길 속 (기둥 줄 ±1.5 m 사이 가운데)
        elif i == "N2":                                                                       # (단층 방 N3 의 어긋난 탄층 띠는 벽 사진에 칠한다 — FAULT_BAND)                                                                       # 북쪽 막장 줄: 막장 셋마다 석탄 덩이
            b_, din = rail_end("N2", "N1"); p1 = b_ + din * 3.2; p2 = Vector((p1.x - 2.4, n["y"] + dd / 2 - 2.4, 0)); p3 = Vector((n["x"] - 10.5, p2.y, 0))   # 저탄장에서 온 레일이 막장 셋 앞(벽에서 2.4 m)을 지난다
            track(b_, p1, n["z"]); track(p1, p2, n["z"]); track(p2, p3, n["z"]); buffer_stop(p3, Vector((-1, 0, 0)), n["z"])
            for x_ in (2.0, -6.5): cart(n, x_, p2.y - n["y"], 0, "ufmodhpfa")                    # 빈 광차 둘 (막장 앞에서 탄을 받는다)
            for k_, (wall, dx_) in enumerate(FACES):
                yv = 0.7
                while yv < FACE_D - 1.3:                                                      # 동발 틀: 입구 0.7 m 안쪽부터 막장 벽 1.3 m 앞까지 1 m 마다 (굴은 +y 로 — 틀은 x 로 걸친다)
                    px, py = wall.x, wall.y + yv; fz_ = floor_at(px, py, n["z"]); rz = min(roof_at(px + sx_, py, n["z"]) for sx_ in (-0.9, 0.0, 0.9))
                    PU.place(timber_sets.frame(PMD, width=2.9, height=rz - fz_ - FRAME_OVER, lean=0.13, lagging=4, seed=k_ * 20 + int(yv), bay=1.0 if yv + 1.0 < FACE_D - 1.3 else None), Matrix.Translation((px, py, fz_ - 0.02)) @ R(90)); yv += 1.0   # 널이 다음 틀 캡까지 걸친다
                surf = pile(dict(x=wall.x, y=wall.y + FACE_D - 0.5, z=n["z"]), 0, 0, "coal", 1.6, 1.3, 0.8, 34, 2, 5)   # 막장 벽 발치에 기댄 탄 더미 (옛 것은 벽 0.7 m 앞 통로 가운데)
                sx0, syc, sz0 = lib("uddjeelqx")[2]; sL = lib("uddjeelqx")[1]; sp = Vector((wall.x - 1.0 + k_ * 0.4, wall.y + FACE_D - 2.3, 0))
                put("uddjeelqx", Matrix.Translation((sp.x, sp.y, floor_at(sp.x, sp.y, n["z"]) + 0.01)) @ R(70 + k_ * 40) @ Matrix.Translation((-(sx0 + sL / 2), -syc, -sz0)))   # 삽 (막장 앞에 누움)
                # 막장 연장 (사용자 10-03 판정 ③ "막장의 디테일 부족"): 면마다 발파 구멍 + 분필 X · 막장 번호 · 가운데 막장에 착암기를 세우고(관 · 호스는 아래) · 동쪽 막장엔 뉘어 둔 착암기 (정을 빼서 옆에)
                fy_ = wall.y + FACE_D; fzf = floor_at(wall.x, fy_ - 1.5, n["z"]); hp_ = ()
                if dx_ == 0: Mj2, ends2, hpj = drill_at((wall.x + 0.2, fy_, n["z"]), (0, 1, 0), floor_at, seed=2); hp_ = (hpj,)
                if dx_ == 8: on_floor(face_kit.jackleg_lying(PM, seed=2), wall.x - 0.4, wall.y + 2.2, n["z"], 75)
                face_kit.drill_holes(PM, face_holes(Vector((wall.x, fy_ - 1.0, 0)), (0, 1, 0), (1, 0, 0), fzf, 3.0, 2.5, 22, 10 + k_, keep=hp_) + [(p_, Vector((0, -1, 0))) for p_ in hp_])
                chalk_at("X", (wall.x - 0.85, fy_, fzf + 1.9), (0, 1, 0), 0.2, 10 + k_); chalk_at(str(k_ + 1), (wall.x + 0.95, fy_, fzf + 2.15), (0, 1, 0), 0.15, 20 + k_)
            wl = FACES[1][0]; yw = n["y"] + dd / 2                                             # 가운데 막장의 압축공기 · 물 관: 동쪽 막장과 사이 벽에서 나와 북쪽 벽을 따라 가운데 막장 입구 옆 밸브까지 → 호스가 바닥을 기어 막장 속 착암기로 (사진 "바닥에 검은 고무 호스가 막장까지")
            Ln = hug((wl.x + 5.4, yw - 1.0), (wl.x + 2.05, yw - 1.0), n["z"] + 2.0, (0, 1, 0)); dl_ = (Ln[-1] - Ln[-2]).normalized()
            air_line("N2", [into_wall(Ln[0], (0, 1, 0))] + Ln[:-1] + [Ln[-1] - dl_ * 0.25, Ln[-1]], (0, 1, 0), (0, -1, 0), Mj2, ends2, [(wl.x + 1.15, yw - 0.25), (wl.x + 1.0, yw + 1.0), (wl.x + 0.9, yw + 3.0)], floor_at, (0.12, 0))
    METAL["wet"] = False
    # ---- 채탄 막장(②) 연장 (사용자 10-03 판정 ③ "막장의 디테일 부족"): 곁굴(Fab 나무 버팀) 서쪽 벽을 따라 압축공기 · 물 관 → 밸브 → 호스가 옛 호스 길로 막장 앞 착암기까지 · 막장 면 발파 구멍 · 분필.
    #   옛 호스(장면 ②)는 양 끝이 바닥에서 뚝 끊겨 있었다. 장면 좌표(S2: +x = 막장 쪽) → 세계
    T2 = zi["z2"]["T"]; a2_ = 3.054 + 2.811; tun2 = a2_ + 15.0; z2f = T2.translation.z; S2 = lambda x_, y_, z_=0.0: T2 @ Vector((x_, y_, z_)); D2 = lambda x_, y_: T2.to_3x3() @ Vector((x_, y_, 0))
    Fw, Fs = D2(1, 0), D2(0, -1)                                                                  # 막장 쪽 · 곁굴 서쪽 벽 쪽 (세계)
    Mj3, ends3, hp3 = drill_at(tuple(S2(tun2, 0.3)), Fw, ground, seed=3)                        # 착암기: 막장 면의 캐낸 자국 둘 사이에 정을 꽂은 채
    fz3 = ground(S2(tun2 - 1.2, 0.0).x, S2(tun2 - 1.2, 0.0).y, z2f)
    face_kit.drill_holes(PM, face_holes(S2(tun2 - 0.55, 0.0), Fw, Fs, fz3, 4.6, 2.2, 24, 3, keep=(hp3,)) + [(hp3, -Fw)])
    chalk_at("X", tuple(S2(tun2, -1.5, fz3 - z2f + 1.65)), Fw, 0.2, 3); chalk_at("7", tuple(S2(tun2, 1.6, fz3 - z2f + 1.85)), Fw, 0.15, 4)
    Ln = hug(tuple(S2(0.6, -0.2))[:2], tuple(S2(4.1, -0.2))[:2], z2f + 1.9, Fs, gap=0.15, look=first_hit); dl_ = (Ln[-1] - Ln[-2]).normalized()   # 관은 곁굴 덧댄 판 0.15 m 앞 (판 너머 바위로 들어가 끝난다)
    air_line("z2", [into_wall(Ln[0], Fs)] + Ln[:-1] + [Ln[-1] - dl_ * 0.25, Ln[-1]], Fs, D2(0, 1), Mj3, ends3,
             [tuple(S2(x_, y_))[:2] for x_, y_ in ((a2_ - 1.0, -0.95), (a2_ + 1.5, -0.6), (a2_ + 4, -0.3), (a2_ + 7, -0.55), (a2_ + 10, -0.2), (tun2 - 2.9, -0.2))], ground, tuple(D2(0, 0.12))[:2])
    # 채탄 막장 바람 관 (막장 앞 방 F 의 선풍기 → 곁굴 → 막장 천장 서쪽 모서리, 지름 0.45): 사용자 지시 "천장이 낮아 숙임 검사를 못 넘으면 빼고 이유를 적는다" — 먼저 재 본다.
    #   매단 관 밑 = 머리 위 가장 낮은 것(Fab 굴 갓목 · 통나무 갓목 · 바위 천장, 세운 기둥은 비켜 간다) − (걸이 쇠줄 0.305 + 반지름 0.225 + 테 0.02 + 처짐 0.055)
    deps_ = bpy.context.evaluated_depsgraph_get(); worst = (9.0, 0.0)
    for x_ in np.arange(0.5, tun2 - 6.5, 0.5):
        q = S2(x_, -0.8 if x_ < a2_ else -2.55); g_ = ground(q.x, q.y, z2f); o_ = Vector((q.x, q.y, g_ + 0.3)); top = None
        for _ in range(6):
            hit, loc, _n, _i, ob, _m = sc.ray_cast(deps_, o_, Vector((0, 0, 1)), distance=6.0)
            if not hit: break
            if "tgnidj2fa" not in ob.name and loc.z - g_ > 1.2: top = loc.z; break
            o_ = loc + Vector((0, 0, 0.02))
        if top is not None and top - g_ - 0.605 < worst[0]: worst = (top - g_ - 0.605, x_)
    print("CHECK map4 z2 fan duct %s: a 0.45 m duct hung along the west roof corner would hang %.2f m above the floor at %.1f m in (crouch line 1.85 m, wanted > 2.0)" % ("NOT built" if worst[0] < 2.0 else "would fit — not built", *worst))
    def choke(wall, f, d0, d1, width, z0, seed):
        """무너져 막힌 굴: 벽에서 d0 m 안쪽 바닥에서 시작해 d1 에서 천장에 닿는 돌 비탈(약 38°) + 그 겉에 묻힌 덩이 + 부러진 동발. 굴 폭보다 넓게 깔아 옆 틈이 없다.
        막아 둔 채굴적 울타리 틈으로 보이는 것 = "쓰지 않는 갱도"가 무너져 있다 (설계 map4_plan.json: 울타리 틈으로 무너진 채굴적 덩어리가 보인다)"""
        rnd = random.Random(seed); u = Vector((-f.y, f.x, 0)); NX, NY = 16, 14; mid = wall + f * d1
        hr = roof_at(mid.x, mid.y, z0) - z0 + 0.35; zf = floor_at((wall + f * d0).x, (wall + f * d0).y, z0); ph = [rnd.uniform(0, 6.28) for _ in range(3)]
        def top(t, s): return hr * t ** 0.9 + 0.16 * math.sin(s * 2.3 + ph[0]) * math.sin(t * 7 + ph[1]) * min(1.0, t * 3) + 0.25 * (s / width) * math.sin(ph[2]) * t   # 가운데 0~1 · 옆으로 s m
        bm = bmesh.new(); rows = [[bm.verts.new(wall + f * (d0 + (d1 + 0.6 - d0) * i / NX) + u * ((j / NY - 0.5) * (width + 1.2)) + Vector((0, 0, zf - z0 + min(hr, top(i / NX * (d1 + 0.6 - d0) / (d1 - d0), (j / NY - 0.5) * (width + 1.2))) - (0.15 if i == 0 else 0.0))))
                                   for j in range(NY + 1)] for i in range(NX + 1)]
        for A_, B_ in zip(rows, rows[1:]):
            for j in range(NY): bm.faces.new((A_[j], B_[j], B_[j + 1], A_[j + 1]))
        mo = obj("HEAP_choke_%d" % seed, bm, HEAP_MAT["stone"]); mo.data.polygons.foreach_set("use_smooth", np.ones(len(mo.data.polygons), dtype=bool)); box_uv(mo.data, 0.8)
        objs = lib("stone")[0]; co_ = np.array([v.co[:] for o in objs for v in o.data.vertices]); x0, yc, zb = lib("stone")[2]; xc = (co_[:, 0].min() + co_[:, 0].max()) / 2; h0 = np.ptp(co_[:, 2])
        for k_ in range(46):                                                                   # 발치에 큰 덩이, 위로 갈수록 작은 것 — 둔덕 겉에 35 % 묻는다
            t, s = rnd.uniform(-0.12, 0.95), rnd.uniform(-0.5, 0.5) * (width - 0.3); sc_ = 3 + 7 * max(0.0, 1 - max(t, 0.0)) * rnd.uniform(0.4, 1.0)
            p = wall + f * (d0 + (d1 - d0) * t) + u * s
            put("stone", Matrix.Translation((p.x, p.y, zf + max(0.0, min(hr, top(max(t, 0.0), s))) - h0 * sc_ * 0.35)) @ R(rnd.uniform(0, 360)) @ Matrix.Rotation(rnd.uniform(-0.4, 0.4), 4, "X") @ Matrix.Diagonal((sc_, sc_, sc_, 1)) @ Matrix.Translation((-xc, -yc, -zb - h0 * 0.15)))
        surf = lambda x, y: zf + max(0.0, min(hr, top(max(0.0, ((Vector((x, y, 0)) - Vector((wall.x, wall.y, 0))).dot(f) - d0) / (d1 - d0)), (Vector((x, y, 0)) - Vector((wall.x, wall.y, 0))).dot(u))))
        yaw_f = math.degrees(math.atan2(f.y, f.x))
        for k_, (t, s, dyaw, pt_) in enumerate(((0.18, -0.9, 150, 30), (0.3, 0.7, 200, 42), (0.5, -0.2, 175, 25), (0.62, 1.0, 230, 50))):   # 비탈에서 솟은 부러진 옛 동발 (울타리 쪽으로 기운다)
            p = wall + f * (d0 + (d1 - d0) * t) + u * s; stuck_log(surf, p.x, p.y, yaw_f + dyaw, pt_, rnd.uniform(1.7, 2.3), 0.1, seed=seed * 10 + k_)
        print("CHECK map4 choke %d: slope from %.1f m to %.1f m behind the wall, roof %.2f m" % (seed, d0, d1, hr - 0.35))
    for k_f, (wall, f, z0) in enumerate(FENCES):                                              # 막아 둔 채굴적 울타리 + 붉은 등 + 출입금지 판 (1964 광산보안규칙 제156 · 158조) · 동쪽 것 옆에 가스 검정판
        F = Matrix.Translation(wall + f * 1.5) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, "Z"); u = Vector((-f.y, f.x, 0))
        choke(wall, f, 4.4, 8.2, 3.6, z0, k_f)
        boxes("FENCE", M_FENCE, [(F @ Vector((0, -1.6 + k * 0.4, 1.18)), (0.05, 0.28, 2.4), F.to_3x3()) for k in range(9)] + [(F @ Vector((-0.06, 0, z_)), (0.05, 3.9, 0.12), F.to_3x3()) for z_ in (0.6, 1.8)])
        red = (wall - Vector((N["E2"]["x"], N["E2"]["y"], 0))).to_2d().length < 20             # 동쪽 = 막아 둔 채굴적(E2) = 가스 · 서쪽 = 옛 채굴 빈터(M) = 붕락
        # 막은 까닭을 나눠 보이게 (사용자 10-03 판정 ③ "출입금지 구역의 이유 디테일 부족"). 레퍼런스: 1964 광산보안법 시행규칙 제156조(쓰지 않는 갱도 = 출입 금지 경표 + 책위) · 제67조(유해 가스 = 경표 + 책위,
        #   허락 없이 걷어 내지 못함) · 메탄 1.5 % 넘으면 전기를 끊고 2 % 넘으면 통행을 막는다 · 붕락 신호 '이슬이 온다 · 짐이 온다' (조사/07:139-151 · 02:9 · 03:21 · 09:655) · 기획서:566 "판자로 막고 분필로 '출입금지'".
        #   판자에 못 박은 까닭 적은 흰 판 (옛 것: "출입금지" 한 줄 판) + 위 가로대 위 판자에 분필
        PU.place(wall_props.danger_board(PM, ("출입금지", "유해가스 발생" if red else "붕락 위험", "허가 없이 들어가지 말 것")), F @ Matrix.Translation((-0.027, 0, 1.3)) @ Matrix.Rotation(math.radians(-90), 4, "Z"))
        PU.place(wall_props.chalk_on_boards(PM, "출입금지 가스!" if red else "붕락 위험", 2.6, 0.36, seed=k_f, x0=0.0), F @ Matrix.Translation((-0.025, 0, 2.12)) @ Matrix.Rotation(math.radians(-90), 4, "Z"))
        if red:                                                                               # 가스 검정판 (사용자 10-02 "출입 금지 앞에 떠 있는 물체는 무엇을 의미하는지 모르겠음" — 벽에서 4 m 떨어진 허공의 판 + 흰 네모 둘이었다).
            gp = wall + u * 2.55 - f * 0.55; gz = floor_at(gp.x, gp.y, z0)                     # 레퍼런스 공통점: 막은 곳 바로 옆 기둥에 철사로 건 판 — 표(가스 · 측정값 · 날짜 · 검정자)에 분필 글씨. 10-03 판정 ③: 날마다 한 줄씩 오르는 메탄 값 · 마지막 2.3 % 에 빨간 동그라미 · 분필 "출입금지" (장면카드 "점검표의 가스 숫자가 날마다 오르다가")
            PU.place(wall_props.gas_board(PM, h=roof_at(gp.x, gp.y, z0) - gz + 0.04, warn=True), Matrix.Translation((gp.x, gp.y, gz - 0.02)) @ Matrix.Rotation(math.atan2(f.y, f.x) - math.pi / 2, 4, "Z"))
        lamp_at((wall - f * 0.3).x, (wall - f * 0.3).y, z0, 3.0, "ZL_ff1a0d_%d", 40, (1.0, 0.1, 0.05))   # 두 곳 다 위험 빨강 한 값 (옛 서쪽 것은 주황 ff7a1a) — 설계 map4_plan.json:151 "붉은 등" · 제158조 "위험한 곳에는 적색 전등"
    # ---- 그것의 굴(⑨): 남은 바위 기둥 셋 · 무너진 돌 언덕 · 넘어진 광차 (장면 좌표 → 세계). 사용자 10-03 "큰 빈터에서의 광차의 위치 · 돌 무더기 큰 암석의 모델링이 어색"
    T9 = zi["z9"]["T"]; n9 = lambda lx, ly: (lambda v: dict(x=v.x, y=v.y, z=v.z))(T9 @ Vector((lx, ly, 0)))
    for k_, (c_, r_) in enumerate(Z9_COLUMNS): rock_column(c_[0], c_[1], r_, -1.0, 19.0, T9, "ROCKCOL_%d" % k_)      # 벽과 같은 법으로 감싼 기둥 (사진도 벽과 같이 — 아래 tex1_paint)
    pile(n9(1.5, -6.0), 0, 0, "stone", 3.4, 5.5, 2.0, 60, 4, 12)                                  # 가운데 무너진 돌 언덕 (장면의 x 가 세계의 −y)
    for lx, ly in ((-12, -10.2), (-3, -10.6), (-8, 10.3), (2, 10.4), (13, 10.0)): pile(n9(lx, ly), 0, 0, "stone", 1.3, 2.6, 0.7, 14, 3, 9)   # 벽 밑 낮은 둔덕 다섯
    tc = put("ueujednfa", T9 @ Matrix.Translation((12, -9.5, 0.63)) @ Matrix.Rotation(math.radians(25), 4, "Z") @ Matrix.Rotation(math.radians(100), 4, "X"))   # 넘어진 광차: 맨바닥에 (옛 것은 각진 큰 돌덩이 위에 얹혀 있었다)
    bpy.context.view_layer.update(); lowv = min((o.matrix_world @ v.co for o in tc for v in o.data.vertices), key=lambda v: v.z)   # 높이 0.63 으로 못박으면 굴곡진 바닥에서 뜬다 (10-03 검사) — 가장 낮은 점 밑의 바닥을 재서 3 cm 묻는다
    for o in tc: o.matrix_world = Matrix.Translation((0, 0, floor_at(lowv.x, lowv.y, lowv.z) - 0.03 - lowv.z)) @ o.matrix_world
    pile(n9(11.2, -8.0), 0, 0, "coal", 1.0, 1.3, 0.35, 16, 2, 4)                                  # 쏟아진 석탄
    # ---- 괴물 틈 꾸밈: 입 양옆 바위의 긁힌 자국 · 발치에 떨어진 돌 · 자리 표시 빈 노드 (MGAP_<방> — 괴물이 드나드는 동작은 다음 번호)
    M_GOUGE = paint("gouge", (0.02, 0.015, 0.01), 0.9); sx0, syc, sz0 = lib("stone")[2]; sco = np.array([v.co[:] for o in lib("stone")[0] for v in o.data.vertices]); sxc = (sco[:, 0].min() + sco[:, 0].max()) / 2; sh0 = np.ptp(sco[:, 2])
    for k_, (rid, f, w0, bend) in enumerate(CRACKS):
        u = Vector((-f.y, f.x, 0)); z0 = N[rid]["z"]; rnd = random.Random("gap" + rid); items = []; Rw = Matrix.Rotation(math.atan2(f.y, f.x) - math.pi / 2, 3, "Z")
        for sd in (-1, 1):
            h_ = rock(w0 - f * 1.3 + u * sd * 1.1 + Vector((0, 0, 1.5)), f, 3.5)
            if not h_: continue
            for j in range(4): items.append((h_[0] - f * 0.012 + u * ((j - 1.5) * 0.085) + Vector((0, 0, 0.2 - j * 0.06 + rnd.uniform(-0.05, 0.05))), (0.03, 0.012, rnd.uniform(0.55, 0.9)), Rw @ Matrix.Rotation(math.radians(20 * sd), 3, "Y")))
        if items: boxes("NOCOL_GOUGE", M_GOUGE, items)
        for j in range(7):
            q = w0 - f * rnd.uniform(0.2, 1.3) + u * rnd.uniform(-1.3, 1.3); sc_ = rnd.uniform(2.5, 6.0)
            put("stone", Matrix.Translation((q.x, q.y, floor_at(q.x, q.y, z0) - sh0 * sc_ * 0.3)) @ R(rnd.uniform(0, 360)) @ Matrix.Diagonal((sc_, sc_, sc_, 1)) @ Matrix.Translation((-sxc, -syc, -sz0)))
        path = crack_path(w0, f, bend)                                                      # 검사 map4_monster_gaps 가 읽는 점 넷: 입(벽 면) · 입 안 1 m · 좁은 데 가운데 · 맨 끝 0.4 m 앞
        for nm_, pt_ in (("MGAP", w0), ("MGAPIN", w0 + f * 1.0), ("MGAPMID", path[1][0].lerp(path[1][1], 0.55)), ("MGAPEND", path[2][0].lerp(path[2][1], 0.86))):
            e_ = bpy.data.objects.new("%s_%s" % (nm_, rid), None); e_.location = Vector((pt_.x, pt_.y, z0 + 1.2)); sc.collection.objects.link(e_)
        SHOTS.append(("gap_%s" % rid, tuple(w0 - f * 4.0 + u * 0.8 + Vector((0, 0, EYE))), tuple(w0 + f * 1.0 + Vector((0, 0, 1.4)))))
    # ---- 천장 구멍 꾸밈 (사용자 10-03 판정 ③ ⓑ — 벽 틈처럼 "저기로 드나든다"로 읽히게, 벽 틈 꾸밈과 같은 법): 입 둘레 천장에 누워 구멍 쪽을 가리키는 긁힌 자국 여섯 군데 × 네 줄
    #   + 목 안쪽 세로 자국 + 밑에 떨어진 돌 5~7 (붕락 방은 돌 더미 윗면 위, 옛 채굴 빈터는 무너진 돌 언덕을 비켜 바닥에). 벽에서 구멍까지 이어지는 자국은 넣지 않았다 (지적 밖 — 물어본다).
    #   빈 노드 CHIM(입 가운데, 천장 높이) · CHIMP1 · CHIMP2(꺾는 점) · CHIMEND(끝 0.4 m 앞) _<방> = 검사 map4_ceiling_holes
    for rid, (c0, p1, p2, p3, d1, a, sx_, sy_) in CHIMS.items():
        rnd = random.Random("chim" + rid); items = []; zlo = min(c0.z - 1.6, N[rid]["z"] + N[rid]["h"] - 0.5)
        for k in range(6):
            t_ = math.radians(60 * k + rnd.uniform(-12, 12)); u_ = Vector((math.cos(t_), math.sin(t_), 0)); v_ = Vector((-u_.y, u_.x, 0))
            re = min(sx_ / 2 / max(abs(u_.x), 1e-6), sy_ / 2 / max(abs(u_.y), 1e-6)) + rnd.uniform(0.12, 0.3)   # 입 가장자리에서 조금 밖
            for j in range(4):
                Lg = rnd.uniform(0.45, 0.75); o_ = c0 + u_ * re + v_ * ((j - 1.5) * 0.085 + rnd.uniform(-0.01, 0.01))
                hs = [rock(Vector((q.x, q.y, zlo)), (0, 0, 1), 4.0) for q in (o_, o_ + u_ * Lg)]
                if not all(hs) or any(abs(h_[0].z - c0.z) > 1.2 or h_[1].z > -0.3 for h_ in hs): continue   # 입 둘레 천장(아래를 보는 면)에 닿은 것만
                e0, e1 = hs[0][0], hs[1][0]; x_ = (e1 - e0).normalized(); nz = (hs[0][1] + hs[1][1]).normalized(); z_ = (nz - x_ * nz.dot(x_)).normalized()
                items.append(((e0 + e1) / 2 + z_ * 0.008, ((e1 - e0).length, 0.05, 0.012), Matrix((x_, z_.cross(x_), z_)).transposed()))
        for k in range(4):                                                                    # 목 안쪽 세로 자국 (입 벽)
            dv = Matrix.Rotation(math.radians(90 * k + rnd.uniform(-20, 20)), 3, "Z") @ Vector((1, 0, 0))
            for j in range(2):
                q = c0 + Vector((0, 0, 0.35 + 0.3 * j)); h_ = rock(q, dv, 2.5)
                if not h_ or (h_[0] - q).length > 2.0: continue
                items.append((h_[0] - dv * 0.008 + Vector((-dv.y, dv.x, 0)) * (0.07 * (j - 0.5)), (0.05, 0.012, rnd.uniform(0.45, 0.7)), Matrix.Rotation(math.atan2(dv.y, dv.x) - math.pi / 2, 3, "Z") @ Matrix.Rotation(rnd.uniform(-0.25, 0.25), 3, "Y")))
        if items: boxes("NOCOL_CHGOUGE_" + rid, M_GOUGE, items)
        surf_ = HEAPTOP.get(rid); nst = rnd.randint(5, 7)                                       # 떨어진 돌: 구멍 바로 밑 1.1 m 안 (붕락 방 = 더미 윗면 위 · 옛 채굴 빈터 = 무너진 돌 언덕 둘레를 비켜 바닥에)
        for j in range(nst):
            for _ in range(30):
                a_, r_ = rnd.uniform(0, 6.28), rnd.uniform(0.2, 1.1); q = Vector((c0.x + math.cos(a_) * r_, c0.y + math.sin(a_) * r_, 0))
                if surf_ or all(((q.x - hc.x) / hrx) ** 2 + ((q.y - hc.y) / hry) ** 2 > 1.3 for _k, hc, hrx, hry, _h in HEAPS): break
            sc_ = rnd.uniform(2.5, 5.0); zq = (surf_(q.x, q.y) if surf_ else floor_at(q.x, q.y, N[rid]["z"])) - sh0 * sc_ * 0.3
            put("stone", Matrix.Translation((q.x, q.y, zq)) @ R(rnd.uniform(0, 360)) @ Matrix.Diagonal((sc_, sc_, sc_, 1)) @ Matrix.Translation((-sxc, -syc, -sz0)))
        for nm_, pt_ in (("CHIM", c0), ("CHIMP1", p1), ("CHIMP2", p2), ("CHIMEND", p2 + a * 2.6)): node("%s_%s" % (nm_, rid), pt_)
        e_ = {"K": (-52.0, -34.5), "M": (-80.0, -66.0)}[rid]; SHOTS.append(("chim_%s" % rid, (e_[0], e_[1], floor_at(e_[0], e_[1], N[rid]["z"]) + EYE), tuple(c0 + Vector((0, 0, 1.0)))))   # [ ] 자리 (j2 캡처와 같은 눈 자리, 위를 본다)
        print("CHECK map4 ceiling chimney %s dressing: gouge strips %d · fallen stones %d" % (rid, len(items), nst))
    for nm, c, f, iron, moved, wide in ALC:
        plank_door(c, f, nm, iron)
        if len(wide) > 3:                                                                     # 화약고 방 안: 화약 상자 (옛 코드는 방 목록에 없어 한 번도 안 놓였다)
            u = Vector((-f.y, f.x, 0))
            for a_, b_, up_ in ((1.7, -0.55, 0.0), (1.75, 0.4, 0.0), (2.45, -0.1, 0.0), (1.72, -0.5, 0.35)): q_ = c + f * a_ + u * b_; crate(q_.x, q_.y, c.z, random.uniform(-12, 12), up=up_)
    # ---- 빛: 불 켜진 방(7 m 칸마다) · 구역 입구 색 등 (카드 15) · 장면 입구 색 등
    bpy.context.view_layer.update()
    for n in rooms:
        if n["id"] == "L":                                                                    # 램프실: 충전대 둘 앞 1.3 m 에 하나씩 (가운데 하나로는 4 m 빛이 벽 소품에 안 닿았다)
            for sx_ in (-5.0, 5.0): lamp_at(n["x"] + sx_, n["y"] - 1.4, n["z"], n["h"], "L%d")
        elif n.get("lit"): lamp_grid(n, max(1, round(n["w"] / 7)), max(1, round(n["d"] / 7)), "L%d")
    # 안 켜진 방 = 작업등. 사용자 10-01 "전등을 1.5배로 — 넓은 곳은 머리등으로는 멀리 안 보인다" → 넓은 방부터 칸 수를 늘린다 (R1 · E3 · E2 · MAG 는 어둡게 둔다 — 괴물 굴 쪽)
    WORK = {"M": (4, 3), "K": (3, 2), "V": (3, 2), "W1": (4, 1), "N1": (2, 2), "N2": (3, 1), "E1": (2, 1), "K2": (2, 1)}   # 방 → (가로 칸, 세로 칸)
    MOVE = {"E1": {(0, 0): (N["E1"]["x"] - 4.0, N["E1"]["y"] + 3.3)}}                          # 선풍기 방 남서쪽 작업등 (42, −6) → 선풍기 · 관 출구 앞 (사용자 10-03 판정 ③ 선풍기 방 — 굴 입구는 북동쪽 작업등이 비춘다). 전등 수는 그대로 (fps 를 깎는 것이 벽 전등 그림자)
    for rid, (nx, ny) in WORK.items(): lamp_grid(N[rid], nx, ny, "ZL_ffb070_%d", move=MOVE.get(rid), energy=50, col=(1.0, 0.69, 0.44))
    for rid in ("W2", "F", "E4", "X", "N0", "N3", "R2", "LD"):                                    # 작은 방 = 하나 (가운데를 비켜서)
        n = N[rid]; lamp_at(n["x"] + n["w"] * 0.2, n["y"] + n["d"] * 0.15, n["z"], n["h"], "ZL_ffb070_%d", 50, (1.0, 0.69, 0.44))
    bm = bmesh.new()                                                                           # ⑨ 그것의 굴 (40 × 26, 천장 12~16 m): 바닥에 세운 작업등 넷 — 계단 밑 · 가운데 북쪽 · 기둥 사이 · 큰 틈 앞
    for p in ((-15, -5, 0), (-2, 7, 0), (9, 0, 0), (15, 2, 0)): pole_lamp(bm, zi["z9"]["T"] @ Vector(p), "ZL_ffb070_%d")
    box_uv(obj("LAMPPOST", bm, M_TAR_).data, 0.8)
    for rid, zone in (("W1", "west"), ("E1", "east"), ("S1", "south"), ("N1", "north")):
        col = plan["zone_color"][zone]; n = N[rid]; lamp_at(n["x"], n["y"], n["z"], n["h"], "ZL_%s_%%d" % col, 120, tuple(int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    for zn, p, col in (("z1", (-20, 0.95, 0), "cfe0ff"), ("z2", (1.5, 0.95, 0), "ff3319"), ("z8", (1.0, 0.95, 0), "ff8c1a"), ("z9", (-30, 4.9, 3), "8c0d0d")):   # 굴 가운데가 아니라 벽 쪽 (낮은 천장 밑 전등이 머리 높이에 걸렸다)
        v = zi[zn]["T"] @ Vector(p); lamp_at(v.x, v.y, v.z, 2.2, "ZL_%s_%%d" % col, 60, tuple(int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    bm = bmesh.new()
    for c, s_ in CORDS: box(bm, c, s_)
    if bm.verts: obj("NOCOL_LAMPCORD", bm, paint("lampcord", (0.012, 0.012, 0.012), 1.0))            # NOCOL_ = 게임에서 부딪힘 없음
    print("CHECK map4 lamps %d  hung on a cord %d (ceiling above %.1f m)" % (len(LIGHTS), len(CORDS), LAMP_H + 0.55))
    # ---- 사다리: 2편으로 내려가는 구멍(카드 10) · 서쪽 모임터 세로 구멍
    def ladder(x, y, z0, z1, yoff):
        bm = bmesh.new()
        g_ = rock((x, y + yoff, (z0 + z1) / 2), (0, 0, -1), 20.0); z0 = min(z0, g_[0].z) if g_ else z0     # 사다리 발은 구멍 바닥까지
        for sx in (-0.25, 0.25): box(bm, (x + sx, y + yoff, (z0 + z1) / 2), (0.05, 0.05, z1 - z0))
        for k in range(int((z1 - z0) / 0.3)): box(bm, (x, y + yoff, z0 + 0.15 + k * 0.3), (0.5, 0.03, 0.03))
        cy_ = y + yoff - 0.36                                                                  # 등받이 테: 사다리 앞(벽 반대쪽) 반지름 0.36 m (선만 있는 원은 게임에 안 나온다 — 납작한 띠 12 토막으로) + 세로 띠 셋
        for k in range(int((z1 - z0 - 2.2) / 0.8) + 1):
            for a_ in range(0, 360, 30): box(bm, (x + 0.36 * math.cos(math.radians(a_)), cy_ + 0.36 * math.sin(math.radians(a_)), z0 + 2.2 + k * 0.8), (0.2, 0.012, 0.04), Matrix.Rotation(math.radians(a_ + 90), 3, "Z"))
        if z1 - z0 > 3.0:
            for a_ in (210, 270, 330): box(bm, (x + 0.36 * math.cos(math.radians(a_)), cy_ + 0.36 * math.sin(math.radians(a_)), (z0 + 2.2 + z1) / 2), (0.04, 0.012, z1 - z0 - 2.2), Matrix.Rotation(math.radians(a_ + 90), 3, "Z"))
        for k in range(int((z1 - z0) / 1.6) + 1):                                              # 벽에 박은 받침쇠 (사다리가 벽에서 떠 있었다)
            zz = min(z1 - 0.2, z0 + 0.3 + k * 1.6); h_ = rock((x, y + yoff, zz), (0, 1, 0), 2.0); d_ = (h_[0].y - (y + yoff)) if h_ else 0.3
            for sx in (-0.25, 0.25): box(bm, (x + sx, y + yoff + d_ / 2 + 0.03, zz), (0.04, d_ + 0.1, 0.04))
        obj("LADDER", bm, M_LADDER)
    lx, ly, lz = ld["x"], ld["y"], ld["z"]; ladder(lx, ly, lz - 11.6, lz + 1.0, 1.3)
    boxes("RAILING", M_LADDER, [(Vector((lx + sx, ly + sy, floor_at(lx + sx, ly + sy, lz) + 0.53)), (0.08, 0.08, 1.1)) for sx in (-2.0, 0.0, 2.0) for sy in (-2.0, 2.0)] + [(Vector((lx + sx, ly, floor_at(lx + sx, ly, lz) + 0.53)), (0.08, 0.08, 1.1)) for sx in (-2.0, 2.0)] +
          [(Vector((lx, ly + sy, lz + z_)), (4.0, 0.06, 0.06)) for sy in (-2.0, 2.0) for z_ in (0.55, 1.05)] + [(Vector((lx + sx, ly, lz + z_)), (0.06, 4.0, 0.06)) for sx in (-2.0, 2.0) for z_ in (0.55, 1.05)])   # 구멍 가장자리에서 0.5 m 물러선 난간 (기둥이 구멍 위에 떠 있었다)
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
    # 한 방의 두 입구가 한 줄로 마주 보고 방이 얕으면(14 m 안쪽) 두 판이 굴 가운데 줄에 겹쳐 걸린다 (사용자 10-03 캡처 20: '램프실' 판 뒤에 '광차 조차장' 판이 반쯤 가려 있었다 — 램프실 · 막장 앞 · 펌프실).
    #   그런 짝은 서로 반대쪽으로 비켜 건다. 가림 검사(sign_hidden)는 다른 판을 가리는 것으로 안 쳐서 못 잡았다
    COAX = {}
    for rid, lst in adj.items():
        if rid not in N: continue
        for i_, (v1, d1) in enumerate(lst):
            for v2, d2 in lst[i_ + 1:]:
                if d1.dot(d2) < -0.95 and abs(d1.x) * N[rid]["w"] + abs(d1.y) * N[rid]["d"] < 14.5: COAX[(rid, v1)] = -1; COAX[(rid, v2)] = 1
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
            pp = Vector((-d.y, d.x, 0)); pp = -pp if pp.x < -1e-6 or (abs(pp.x) < 1e-6 and pp.y < 0) else pp      # 옆 방향 (마주 보는 두 입구에 같은 쪽)
            side = pp * (COAX.get((n["id"], oid), 0) * min(0.85, max(0.0, (2.9 if e["kind"] == "haul" else KIND[e["kind"]][0] / 2) - w_ / 2 - 0.1)))
            for k_ in (1.0, 1.8, 2.6):                                                         # 입구에서 방 안쪽으로 얼마나 — 굴 문틀이 낮으면 굴에서 판이 안 보인다. 양쪽 다 보이는 가장 가까운 자리
                c = W(n, 0, 0) + d * (exit_t(n["id"], d) - k_) + side; C = Vector((c.x, c.y, n["z"] + SIGN_Z + hb / 2))
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
    LOOK = {"N2": (0, 1), "X": (0, 1), "V": (0, -1), "E1": (0, 1), "E2": None, "R0": (0, -1), "L": (0, -1), "N3": (0, 1)}   # 주인공 소품이 있는 벽 쪽
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
        hit2, c_, _, _, ob2, _ = sc.ray_cast(deps, f_ + Vector((0, 0, 0.3)), Vector((0, 0, 1)), distance=6.0)
        if hit2 and c_.z - f_.z < 2.0 and not ob2.name.startswith("HEAP"): low.append((where, round(f_.x, 1), round(f_.y, 1), round(c_.z - f_.z, 2)))   # 더미 둔덕 속 바닥은 걷는 곳이 아니다
    print("CHECK map4 floor %.0f m2  rooms %d  scenes %d  tunnels %d  closets %d  signs %d  lights %d" % (ar[fl.reshape(-1, 3)[:, 2] > 0.9].sum(), len(rooms), len(Z), len(plan["edges"]), len(ALC), signs, len(LIGHTS)))
    print("CHECK map4 low spots %d of %d sampled (headroom < 2.0 m)%s" % (len(low), len(pts), (": " + "; ".join("%s (%s, %s) %.2f" % l for l in low[:12])) if low else ""))
    # ---- TEX-1: 바위 굴 · 장면 바닥 판 · 석탄 소품에 환경 사진 (map4_tex.json)
    st = tex1_paint(SHELL, T1, ray=True); extra = 0
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("FLOOR", "ROCKCOL"))]:
        tex1_paint(o, T1, fixed=None); extra += 1   # 바닥 판 넷은 걷지 않고 그 자리 바닥 사진을 입힌다(가장자리 금) · 석탄 기둥 · 단층 방 석탄 띠 = 석탄 면
    for k_, env_ in list(TEX["room"].items()) + list(TEX["scene"].items()):                    # 방 · 장면마다 "여기 벽 · 바닥은 몇 번" 빈 노드 → 게임 검사 map4_room_photos 가 맞춰 본다
        if k_ in N and N[k_]["kind"] == "closet": continue
        c_ = Vector((N[k_]["x"], N[k_]["y"], N[k_]["z"] + 1.5)) if k_ in N else zi[k_]["T"] @ Vector({"z3": (L3 * 0.8, 0, 1.5), "z7": (L7S + L7W * 0.5, 0, 1.4), "z8": (10, 0, 1.5), "z2": (12, 0, 1.2)}.get(k_, (0, 0, 1.5)))
        e_ = bpy.data.objects.new("TEX_%s_%d_%d" % (k_, TEX["env"][env_]["wall"], TEX["env"][env_]["floor"]), None); e_.location = c_; sc.collection.objects.link(e_)   # 큰 길의 벽 ② 는 사진 ③ (어둡기만 점마다)
    for k_, (wall_, dx_) in enumerate(FACES):                                                  # 북쪽 막장 홈 셋 가운데 = 석탄 면
        e_ = bpy.data.objects.new("TEX_N2face%d_%d_%d" % (k_, TEX["env"]["coalface"]["wall"], TEX["env"]["coalface"]["floor"]), None); e_.location = wall_ + Vector((0, 2.5, 1.2)); sc.collection.objects.link(e_)
    joins = 0
    for s in SEG:                                                                             # 이음 자리 캡처: 굴 가운데 4 m 앞에서 굴을 따라 본다 (환경이 바뀌는 굴만 — 굽기와 같은 환경 표로)
        ea, eb = s["edge"]["a"].split(".")[0], s["edge"]["b"].split(".")[0]; na, nb = T1["end_env"](s["edge"]["a"], s["p"])[0], T1["end_env"](s["edge"]["b"], s["q"])[0]
        if na == nb: continue
        p, q = s["p"], s["q"]; d = (q - p).normalized(); L = (q - p).length; m_ = p.lerp(q, min(max((s["ta"] + L - s["tb"]) / 2 / max(L, 1e-6), 0.0), 1.0)); joins += 1
        SHOTS.append(("seam%02d_%s_%s" % (joins, ea, eb), tuple(m_ - d * 4.0 + Vector((0, 0, EYE))), tuple(m_ + d * 4.0 + Vector((0, 0, 1.4)))))
    for sn_, sp_ in TEX["scene_split"].items():                                                # 장면 안에서 환경이 바뀌는 자리 (바람문 앞문 틀 · 석탄 홈통) — 굴 가운데가 아니라 틀에 맞춘 경계
        if sn_ not in zi: continue
        x_ = T1["splitx"][sp_["x"]]; joins += 1
        SHOTS.append(("seam%02d_%s_%s" % (joins, sn_, sp_["x"]), tuple(zi[sn_]["T"] @ Vector((x_ - 4.0, 0, EYE))), tuple(zi[sn_]["T"] @ Vector((x_ + 4.0, 0, 1.4)))))
    tc = st["tri"]; cl = {}
    for c_ in tc: cl.setdefault((int(c_[0] // 8), int(c_[1] // 8)), []).append(c_)
    worst = sorted(cl.values(), key=len, reverse=True)
    for k_, g_ in enumerate(worst):                                                           # 사진이 딱 끊겨 보이는 곳 (점이 많은 차례로 전부) — 가까운 자리에서 본다
        c_ = np.mean(g_, axis=0); r_ = T1["kd"].find(c_.tolist())[1]; SHOTS.append(("tri_%d" % k_, (T1["S"][r_, 0], T1["S"][r_, 1], T1["S"][r_, 6] + EYE), tuple(c_)))
    print("CHECK map4 tex1 sites %d (dropped %d in rock) · rock materials %d (%s) · two-photo faces %.0f of %.0f m2 · coal band %.0f m2 · floor plates and coal props %d" % (len(T1["S"]), T1["dropped"], len(st["names"]), " ".join(sorted(st["names"])), st["blend"], st["all"], st["coal"], extra))
    print("CHECK map4 tex1 area by photo (m2): wall %s / floor %s" % (" · ".join("%d: %.0f" % kv for kv in sorted(st["wall"].items())), " · ".join("%d: %.0f" % kv for kv in sorted(st["floor"].items()))))
    print("CHECK map4 tex1 joins %d (tunnels whose two ends differ + scene splits) · points where a photo's share jumps > 0.25 between touching faces (visible hard edge) %d in %d places%s" % (joins, len(tc), len(cl), (": " + "; ".join("(%.0f, %.0f, %.0f) x%d" % (*np.mean(g_, axis=0), len(g_)) for g_ in worst)) if worst else ""))
    # ---- 판자 문 칸의 문이 바위 벽에 붙어 있나 (사용자 10-02 "뜬금없이 문이 있다"): 문틀 양옆 0.75 m 에서 칸 쪽으로 쏜 광선이 0.65 m 안에 바위를 만나야 한다
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get(); lone = []
    for nm, c, f, *_ in ALC:
        u = Vector((-f.y, f.x, 0)); gap = []
        for sd in (-1, 1):
            ds = [sc.ray_cast(deps, c - f * 0.3 + u * sd * 0.75 + Vector((0, 0, h_)), f, distance=3.0) for h_ in (0.5, 1.2, 2.0)]
            gap.append(min([(h[1] - (c - f * 0.3 + u * sd * 0.75)).to_2d().length - 0.3 for h in ds if h[0] and h[4].name.startswith("SHELL")] or [9.0]))
        if max(gap) > 0.35: lone.append("%s %.1f/%.1f m" % (nm, gap[0], gap[1]))
    print("CHECK map4 closet doors %d · not against rock (gap beside the frame > 0.35 m): %d%s" % (len(ALC), len(lone), (" — " + "; ".join(lone)) if lone else ""))
    # ---- 광차가 레일 위에 있나 (사용자 10-02 "광차와 레일이 간격이 맞지 않다"): 광차 가운데가 레일 줄 가운데에서 3 cm 안, 레일 줄 길이 안
    off = []
    for c_, fid in CARTS:
        best = 9.0
        for a_, b_ in TRACKS:
            d_ = (b_ - a_); L_ = d_.length; d_.normalize(); t_ = (c_ - a_).dot(d_)
            if -0.2 <= t_ <= L_ + 0.2 and abs(c_.z - a_.z) < 0.3: best = min(best, ((c_ - a_) - d_ * t_).to_2d().length)
        if best > 0.03: off.append("%s (%.1f, %.1f) %s" % (fid, c_.x, c_.y, "no rail" if best > 2 else "%.2f m off" % best))
    print("CHECK map4 carts %d on %d track lines · off the rails: %d%s · gauge %.2f m · wheel treads at rail top %.3f m" % (len(CARTS), len(TRACKS), len(off), (" — " + "; ".join(off)) if off else "", GAUGE, RAIL_TOP))
    # ---- 걷는 길 (게임 검사 map4_walk_* 가 그대로 걷는다): 굴마다 한 줄 + 장면 안 길. 이름 WALK_<번호>_<반폭 × 10>_<점 번호>
    WALKS, AREAS, seen_e = [], [], {}
    last_sg = {}
    for sg in SEG:                                                                            # 방 안은 벽에서 1.5 m 까지만 (방 가운데는 돌 더미 · 기계가 있다 — 방은 넓이로 훑는다)
        k_ = id(sg["edge"]); d_ = (sg["q"] - sg["p"]).normalized()
        f2 = lambda v, z_: Vector((v.x, v.y, z_)); h2 = Vector((d_.x, d_.y, 0)).normalized()
        if k_ not in seen_e:
            seen_e[k_] = len(WALKS); WALKS.append(("%s~%s" % (sg["edge"]["a"].replace(".", ""), sg["edge"]["b"].replace(".", "")), 2.9 if sg["kind"] == "haul" else KIND[sg["kind"]][0] / 2, []))
            if sg["edge"]["a"] in N and sg["ta"] > 0.7: WALKS[-1][2].extend([f2(sg["p"] + h2 * max(0.0, sg["ta"] - 2.1), sg["p"].z), f2(sg["p"] + h2 * (sg["ta"] - 0.6), sg["p"].z)])   # 방 안 1.5 m → 방 벽
            else: WALKS[-1][2].append(sg["p"].copy())
        WALKS[seen_e[k_]][2].append(sg["q"].copy()); last_sg[k_] = sg
    for k_, sg in last_sg.items():
        if sg["edge"]["b"] in N and sg["tb"] > 0.7:
            h2 = (sg["q"] - sg["p"]); h2.z = 0; h2.normalize(); f2 = lambda v, z_: Vector((v.x, v.y, z_))
            WALKS[seen_e[k_]][2][-1:] = [f2(sg["q"] - h2 * (sg["tb"] - 0.6), sg["q"].z), f2(sg["q"] - h2 * max(0.0, sg["tb"] - 2.1), sg["q"].z)]
    a8 = 3.054 + 2.811
    for zn, hw, pts in (("z3", 2.9, [(0, 0, 0), (1.5, 1.7, 0), (L3 - 1.5, 1.7, 0), (L3, 0, 0)]), ("z7", 2.9, [(0, 0, 0), (L7S, 0, 0)]), ("z7", 1.4, [(L7S, 0, 0), (L7S + L7W, 0, 0)]),
                        ("z8", 1.3, [(0, 0, 0), (a8, -0.35, 0), (a8 + 8.2, -0.35, 0), (19.92, 0, 0)]), ("z1", 1.2, [(-22, 0, 0), (20, 0, 0)]), ("z2", 1.2, [(0, 0, 0), (9, 0, 0), (14, 2.2, 0), (15, 3, 0)]),
                        ("z6", 1.4, [(-8, 1, 0), (-1.5, 1.2, 0), (1.5, 1.2, 0), (8, -1, 0)]), ("z6", 1.4, [(1.2, 1.2, 0), (1.25, -3.0, 0), (0.0, -4.4, 0), (0.0, -20, 0)])) + tuple(Z9_WALKS):
        if zn in zi: WALKS.append((zn, hw, [zi[zn]["T"] @ Vector(p_) for p_ in pts]))
    for n in rooms: AREAS.append((n["id"], Vector((n["x"], n["y"], n["z"])), n["w"], n["d"], 0.0))
    e1 = N["E1"]; hy_ = e1["y"] + e1["d"] / 2                                                  # 선풍기 방 굴진 막장 (방 넓이 밖): 사람이 막장 면을 보러 걸어 들어가는 길 + 그 바닥 전체 — 동발 · 관 · 관 받침이 저절로 숙이게 하지 않나 (map4_no_auto_crouch · map4_walk_through)
    WALKS.append(("E1~heading", 1.0, [Vector((HEAD["x"], hy_ - 1.0, e1["z"])), Vector((HEAD["x"], hy_, e1["z"])), Vector((HEAD["x"], HEAD["face"] - 3.4, e1["z"]))]))
    AREAS.append(("E1head", Vector((HEAD["x"], hy_ + HEAD["d"] / 2, e1["z"])), HEAD["w"], HEAD["d"], 0.0))
    for zn, c_, w_, d_ in (("z6", (0, 0, 0), 16, 10), ("z1", (0, 0, 0), 24, 10), ("z2", (a8 + 7.5, 0, 0), 15, 6), ("z9", (0, 0, 0), 40, 26)):
        if zn in zi: AREAS.append((zn, zi[zn]["T"] @ Vector(c_), w_, d_, next(s_["yaw"] for s_ in plan["scenes"] if s_["scene"] == zn)))
    for k_, (nm, hw, pts) in enumerate(WALKS): print("CHECK map4 walk %02d %s half width %.1f m, %d points, %.0f m" % (k_, nm, hw, len(pts), sum((b_ - a_).length for a_, b_ in zip(pts, pts[1:]))))
    tiles = split_tiles(SHELL)
    print("CHECK map4 shell tiles %d  tris %d  all tris %d" % (len(tiles), sum(len(t.data.polygons) for t in tiles), sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")))
    # ---- 찢어진 바위 (사용자 10-02 "굴 위의 모델링이 끊어져 있음"): 복셀 0.25 m 그물에서 변이 0.75 m 넘게 늘어난 면 = 겉면이 접힌 곳. 10-01 굽기는 큰 빈터 여섯 칸에서 6,792 개 · 가장 긴 변 2.27 m, 나머지 칸은 0 개 · 0.59 m
    torn, worst_e = [], 0.0
    for t in tiles:
        me_ = t.data; co_ = np.empty(len(me_.vertices) * 3); me_.vertices.foreach_get("co", co_); co_ = co_.reshape(-1, 3)
        ev = np.empty(len(me_.edges) * 2, np.int32); me_.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2); el = np.linalg.norm(co_[ev[:, 0]] - co_[ev[:, 1]], axis=1)
        worst_e = max(worst_e, float(el.max()))
        if (el > 0.75).sum(): torn.append("%s %d (%.2f m)" % (t.name, int((el > 0.75).sum()), el.max()))
    print("CHECK map4 shell torn: tiles with edges longer than 0.75 m: %d of %d%s · longest edge %.2f m" % (len(torn), len(tiles), (" — " + "; ".join(torn)) if torn else "", worst_e))
    xs = [n["x"] for n in plan["nodes"]] + [s["x"] for s in plan["scenes"]]; ys = [n["y"] for n in plan["nodes"]] + [s["y"] for s in plan["scenes"]]
    view = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys)) + 50)
    print("CHECK map4 view %.1f %.1f %.1f" % view)
    for n in rooms: print("CHECK map4 label %s|%.1f|%.1f" % (n["name"][:10], n["x"], n["y"]))
    for z in Z: v = z["T"] @ Vector(((L3 / 2) if z["n"] == "z3" else (L7S + L7W) / 2 if z["n"] == "z7" else 10 if z["n"] in ("z8", "z2") else 0, 0, 0)); print("CHECK map4 label %s|%.1f|%.1f" % (SCENE_NAME[z["n"]], v.x, v.y))
    # 좌표 없는 물체(통 · 관 · 감개 · 장면의 쇠 틀)에 상자 투영 좌표 — 사진 재질이 펴지게 (조사 12: cyl() 이 좌표를 안 만들어 녹슨 통 · 관에 사진이 안 펴졌다)
    nouv = [o for o in bpy.data.objects if o.type == "MESH" and not o.data.uv_layers and any(m_ and m_.use_nodes and any(x.type == "TEX_IMAGE" for x in m_.node_tree.nodes) for m_ in o.data.materials)]
    for o in nouv: box_uv(o.data, 0.8)
    print("CHECK map4 photo materials: wood %s · tar %s · metal %s / %s · cloth %s · box-uv added to %d objects" % tuple(["cc0" if os.path.isdir(os.path.join(CC0, d_)) else "OLD" for d_ in ("wood/rough_wood", "wood/black_painted_planks", "metal/metal_plate_02", "metal/rusty_metal_04", "misc/decrepit_wallpaper")] + [len(nouv)]))
    return dict(lights=LIGHTS, adapt=((0, 0, 3), 1, 1), fills=([], 3, 0, 1), shots=SHOTS, people=[(0, 0, 0)], ortho=view[2], side_z=2, center=view[:2], map=True, walks=WALKS, areas=AREAS, heaps=HEAPS)

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
    for k_, (nm, hw, pts) in enumerate(S.get("walks", [])):                             # 걷는 길 (검사 map4_walk_*) · 훑을 넓이 (검사 map4_no_low_spot)
        for i_, p_ in enumerate(pts): e = bpy.data.objects.new("WALK_%02d_%d_%02d" % (k_, round(hw * 10), i_), None); e.location = p_; sc.collection.objects.link(e)
    for nm, c_, w_, d_, yaw_ in S.get("areas", []):
        e = bpy.data.objects.new("AREA_%s_%d_%d" % (nm, round(w_ * 10), round(d_ * 10)), None); e.location = c_; e.rotation_euler = (0, 0, math.radians(yaw_)); sc.collection.objects.link(e)
    for k_, (key_, c_, rx_, ry_, h_) in enumerate(S.get("heaps", [])):                  # 돌 · 석탄 더미 (검사 map4_heaps_solid): 가운데 밑 · 반지름 · 높이 (× 10)
        e = bpy.data.objects.new("HEAPC_%s_%d_%d_%d_%d" % (key_, k_, round(rx_ * 10), round(ry_ * 10), round(h_ * 10)), None); e.location = c_; sc.collection.objects.link(e)
    if S.get("walks"):                                                                  # 같은 것을 글 파일로도 (옛 맵 파일에 새 검사를 돌려 볼 때: exe -walks <파일>) — Blender 좌표
        with open(os.path.splitext(os.environ["EXPORT_GLB"])[0] + "_walks.txt", "w", encoding="utf-8") as f_:
            for k_, (nm, hw, pts) in enumerate(S["walks"]): print("WALK %02d %s %.1f %s" % (k_, nm, hw, " ".join("%.2f,%.2f,%.2f" % tuple(p_) for p_ in pts)), file=f_)
            for nm, c_, w_, d_, yaw_ in S["areas"]: print("AREA %s %.2f,%.2f,%.2f %.1f %.1f %.1f" % (nm, *c_, w_, d_, yaw_), file=f_)
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
