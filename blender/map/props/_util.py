"""소품 만들기 공용 도구 (10-02 판정 ① "무엇인지 모르겠다" 소품 다시 만들기). Blender 안에서만 돈다.
소품 파일 하나 = build(mats, **옵션) 함수 하나 → 물체 목록. 좌표는 소품 자리표(원점 = 바닥 위 기준점, z 위, m). 맵에 놓는 일은 scene_mock.py 가 한다.
약속:
  - 재질은 mats["이름"] 으로만 받는다 (아래 MAT_KEYS). 색을 직접 만들지 않는다 — 맵에서는 사진 재질, 미리보기에서는 단색이 들어온다.
  - 물체 이름이 NOCOL_ 로 시작하면 게임에서 부딪힘이 없다 (줄 · 고리 · 머리 위 관). COLONLY_ 로 시작하면 부딪힘만 있고 안 보인다 (계단 비탈).
  - 떠 있는 것이 없어야 한다: 모든 덩어리는 바닥 · 벽 · 다른 덩어리에 닿는다. 선만 있고 면이 없는 그물(원 테두리)은 게임에 안 나온다 — 쓰지 않는다.
  - 걸어 지나는 자리 위 2.3 m 아래에는 부딪힘 있는 것을 두지 않는다 (바닥에 선 장애물은 된다).
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

MAT_KEYS = {  # 이름 → 미리보기 색 (맵에서는 scene_mock.py 가 사진 재질로 바꿔 끼운다)
    "steel_paint": (0.20, 0.27, 0.23),   # 칠한 쇠 (바랜 회녹색)
    "steel_red": (0.33, 0.10, 0.07),     # 붉은 녹막이 칠
    "steel_blue": (0.06, 0.16, 0.42),    # 파란 칠 (검정 판)
    "steel_yellow": (0.55, 0.42, 0.06),  # 노란 칠
    "rust": (0.25, 0.13, 0.08),          # 녹슨 쇠
    "iron": (0.07, 0.07, 0.075),         # 검은 쇠 (주물 · 볼트 · 쇠줄)
    "bare": (0.42, 0.42, 0.44),          # 닳아 드러난 쇠
    "timber": (0.50, 0.40, 0.26),        # 껍질 벗긴 통나무 옆면
    "timber_end": (0.66, 0.56, 0.38),    # 통나무 끝면 (나이테)
    "timber_old": (0.27, 0.23, 0.19),    # 오래된 잿빛 나무
    "tar": (0.10, 0.085, 0.07),          # 타르 칠 판자
    "plank": (0.36, 0.29, 0.20),         # 켠 판자
    "cloth": (0.30, 0.27, 0.22),         # 거적 · 자루
    "cloth_yellow": (0.62, 0.48, 0.10),  # 바람 관 천 (때 탄 노랑)
    "concrete": (0.34, 0.33, 0.31),
    "white": (0.62, 0.61, 0.57),         # 흰 칠 판
    "black": (0.02, 0.02, 0.022),        # 검정 칠 · 분필 판
    "red": (0.45, 0.03, 0.02),           # 빨간 글씨 · 표시
    "chalk": (0.80, 0.80, 0.76),         # 분필 글씨
    "glass": (0.55, 0.60, 0.58),         # 계기 유리 · 눈금판 바탕
    "rubber": (0.03, 0.03, 0.03),        # 케이블 · 호스
    "water": (0.01, 0.012, 0.012),
    "ochre": (0.42, 0.22, 0.06),         # 갱내수 누런 때
}

def box(bm, c, s, rot=None):
    """가운데 c, 크기 s 인 상자. rot = 3x3 (가운데를 중심으로 돈다)"""
    g = bmesh.ops.create_cube(bm, size=1.0); R = rot.to_3x3() if rot is not None else Matrix.Identity(3)
    for v in g["verts"]: v.co = R @ Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])) + Vector(c)
    return g["verts"]

def cyl(bm, p0, p1, r, seg=12, r1=None, caps=True):
    """p0 → p1 원기둥 (r1 을 주면 끝 반지름이 다른 뿔대). 뚜껑 없이(caps=False) 속 빈 관의 겉"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length
    g = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r1 is None else r1, depth=L)
    M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    for v in g["verts"]: v.co = M @ v.co
    return g["verts"]

def tube(bm, p0, p1, r_out, r_in, seg=16):
    """속이 보이는 관 (두께 있는 벽 + 양 끝 고리 면) — 끝이 트인 관 · 통에 쓴다"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; M = Matrix.Translation(p0) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4(); L = d.length
    ring = lambda r, z: [bm.verts.new(M @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)]
    a, b, c_, e = ring(r_out, 0), ring(r_out, L), ring(r_in, L), ring(r_in, 0)
    for A, B in ((a, b), (b, c_), (c_, e), (e, a)):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))

def torus(bm, c, axis, R, r, seg=16, sub=6):
    """도넛 (손잡이 바퀴 테 · 관 이음 테 · 고리). axis = 구멍이 보는 쪽"""
    M = Matrix.Translation(Vector(c)) @ Vector(axis).to_track_quat("Z", "Y").to_matrix().to_4x4()
    rings = [[bm.verts.new(M @ Vector(((R + r * math.cos(2 * math.pi * j / sub)) * math.cos(2 * math.pi * i / seg), (R + r * math.cos(2 * math.pi * j / sub)) * math.sin(2 * math.pi * i / seg), r * math.sin(2 * math.pi * j / sub)))) for j in range(sub)] for i in range(seg)]
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(sub): bm.faces.new((A[j], B[j], B[(j + 1) % sub], A[(j + 1) % sub]))

def sweep(bm, pts, r, seg=10, caps=True, r_fn=None):
    """꺾인 선을 따라가는 둥근 관 (관 · 케이블 · 바람 관). pts = 가운데 선의 점들. r_fn(i) = i번째 점의 반지름 (주름 · 처짐)"""
    pts = [Vector(p) for p in pts]; rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized(); q = t.to_track_quat("Z", "Y").to_matrix(); rr = r_fn(i) if r_fn else r
        rings.append([bm.verts.new(p + q @ Vector((rr * math.cos(2 * math.pi * k / seg), rr * math.sin(2 * math.pi * k / seg), 0))) for k in range(seg)])
    for A, B in zip(rings, rings[1:]):
        best = min(range(seg), key=lambda s: sum((A[k].co - B[(k + s) % seg].co).length for k in range(0, seg, max(1, seg // 4))))   # 꺾일 때 고리가 비틀리지 않게 맞춘다
        for k in range(seg): bm.faces.new((A[k], A[(k + 1) % seg], B[(k + 1 + best) % seg], B[(k + best) % seg]))
    if caps: bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return rings

def box_uv(me, per_m=0.8):
    """상자 투영 UV — 사진 재질이 1 m 에 per_m 번 깔린다"""
    uv = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i])); a, b = [i for i in range(3) if i != ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (co[a] * per_m, co[b] * per_m)

def obj(name, bm, mat, smooth=False, per_m=0.8):
    """bmesh → 장면 물체. 노멀을 바깥으로 맞추고 UV 를 편다"""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    if smooth: me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    box_uv(me, per_m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def text_mesh(name, body, loc, size, mat, rot=(math.radians(90), 0, 0), font="C:/Windows/Fonts/malgunbd.ttf", extrude=0.002):
    """판에 쓴 글자 (그물로 바꿔 돌려준다 — glTF 는 글꼴 곡선을 못 담는다). 기본 방향 = −y 쪽에서 읽힌다"""
    cu = bpy.data.curves.new(name, "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.extrude = extrude; cu.font = bpy.data.fonts.load(font, check_existing=True)
    t = bpy.data.objects.new(name + "_c", cu); t.location = loc; t.rotation_euler = rot; bpy.context.scene.collection.objects.link(t); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(bpy.context.evaluated_depsgraph_get())); me.transform(t.matrix_world); bpy.data.objects.remove(t, do_unlink=True)
    me.materials.clear(); me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def place(objs, M):
    """소품 자리표 → 세계 좌표 (물체마다 matrix_world 를 곱한다)"""
    for o in objs: o.matrix_world = M @ o.matrix_world
    return objs

def report(objs):
    """미리보기 · 굽기 로그용 숫자: 삼각형 수 · 크기 · 가장 낮은 곳 · 면 없는 선"""
    tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
    co = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))); hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    loose = [o.name for o in objs if any(not e.is_manifold and len(e.link_faces) == 0 for e in _bm(o).edges)]
    return dict(objects=len(objs), tris=tris, lo=tuple(round(v, 3) for v in lo), hi=tuple(round(v, 3) for v in hi), loose_edge_objects=loose)

def _bm(o):
    b = bmesh.new(); b.from_mesh(o.data); return b
