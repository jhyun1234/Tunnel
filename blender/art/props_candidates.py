"""ART-1 차례 3 — 광장 물건 후보를 진짜 부스 맵 광장(새 바위 질감)에 하나씩 세워 같은 빛으로 찍는다.
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/props_candidates.py
  python docs/그림/ART1_물건_후보.py      (한 장으로)
입력(받아 둔 것, 커밋 안 함): build/art/props_cand/<Poly Haven id>/*.gltf · build/art/cand_tex/*(CC0 질감 1K). 게임 파일은 읽기만.
출력: build/art/props_render/<번호>.png + props.json(면 수 · 크기). 빛은 게임이 아니다(EEVEE · 전등 500 W · 헤드램프 600 W)."""
import bpy, os, sys, math, json
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CT = os.path.join(ROOT, "build", "art", "cand_tex"); ART = os.path.join(ROOT, "Assets", "Tunnel", "Art", "textures")
PH = os.path.join(ROOT, "build", "art", "props_cand"); OUT = os.path.join(ROOT, "build", "art", "props_render")
FONT = os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "booth_map.gltf"))
sc = bpy.context.scene
for o in sc.objects:
    if o.name.startswith(("COL_", "NAV")): o.hide_render = True
MAP = set(sc.objects)

# 배경 = 새 모습 질감 (색 + 노멀; 거칠기는 후보 1K)
def swap(mat_name, color, normal, rough):
    m = bpy.data.materials[mat_name]
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            nm = os.path.splitext(n.image.name)[0]
            for suf, path, data in (("_Diffuse", color, False), ("_nor_gl", normal, True), ("_Rough", rough, True)):
                if nm.endswith(suf):
                    n.image = bpy.data.images.load(path, check_existing=True)
                    if data: n.image.colorspace_settings.name = "Non-Color"
swap("MAT_RockWall_EXPORT", os.path.join(ART, "art_rock_Rock031_DiffRough.png"), os.path.join(ART, "art_rock_Rock031_nor_gl.jpg"), os.path.join(CT, "Rock031_Roughness.jpg"))
swap("MAT_Floor_EXPORT", os.path.join(ART, "art_mud_brown_mud_03_DiffRough.png"), os.path.join(ART, "art_mud_brown_mud_03_nor_gl.jpg"), os.path.join(CT, "brown_mud_03_Roughness.jpg"))

M = mp.materials(ROOT)

# (번호, 이름, 출처, 사진 근거, 만들기, 놓기: floor = 바닥 · hang = 눈높이에 띄움 · wall = 벽 높이)
CANDS = [
    ("B1", "레일 + 갈림", "Blender", "사진 8", lambda: mp.rails(M, 6.0, switch=True), "floor"),
    ("B2", "광차 + 석탄", "Blender", "사진 4", lambda: mp.mine_car(M), "floor"),
    ("B3", "케이지 (안 움직임)", "Blender", "사진 3", lambda: mp.cage(M), "floor"),
    ("B4", "강철 아치 + 판자", "Blender", "사진 5 · 3", lambda: mp.steel_set(M), "floor"),
    ("B5", "나무 동발 (둥근 통나무)", "Blender", "사진 2", lambda: mp.timber_set(M), "floor"),
    ("B6", "쇠사슬", "Blender", "사진 3", lambda: mp.chain(M, 1.5), "hang"),
    ("B7", "판 '안전제일'", "Blender + Pretendard", "갱구 사진 2", lambda: mp.sign(M, ["안전제일"], (0.9, 0.35), font=FONT, text_h=0.18), "wall"),
    ("B8", "판 케이지 경고 (글자 지어냄)", "Blender + Pretendard", "사진 1", lambda: mp.sign(M, ["케이지 승강장", "신호 전 승차 금지"], (0.9, 0.5), board=(0.95, 0.8, 0.1), ink=(0.05, 0.05, 0.05), font=FONT, text_h=0.1), "wall"),
    ("B9", "판 작업현황 (화이트보드)", "Blender + Pretendard", "사진 1", lambda: mp.sign(M, ["작업현황", "1편 ___  2편 ___", "화약 ___"], (1.0, 0.7), ink=(0.1, 0.15, 0.45), font=FONT, text_h=0.09), "wall"),
    ("P1", "관 · 밸브", "modular_industrial_pipes_01", "사진 7", "modular_industrial_pipes_01", "hang"),
    ("P2", "전선 묶음", "modular_electric_cables", "사진 6", "modular_electric_cables", "hang"),
    ("P3", "철망 매단 등", "caged_hanging_light", "사진 4", "caged_hanging_light", "hang"),
    ("P4", "철망 벽 등", "industrial_caged_sconce", "사진 4", "industrial_caged_sconce", "wall"),
    ("P5", "관 등", "industrial_pipe_lamp", "사진 4", "industrial_pipe_lamp", "wall"),
    ("P6", "전기함 (작은)", "power_box_01", "사진 1", "power_box_01", "wall"),
    ("P7", "전기함 (큰)", "utility_box_02", "사진 1", "utility_box_02", "floor"),
    ("P8", "통풍관", "modular_airduct_circular_01", "사진 1", "modular_airduct_circular_01", "hang"),
    ("P9", "삽", "rusted_spade_01", "추정", "rusted_spade_01", "floor"),
    ("P10", "쇠지레", "crowbar_01", "추정", "crowbar_01", "floor"),
    ("P11", "큰 망치", "sledgehammer_01", "추정", "sledgehammer_01", "floor"),
    ("P12", "곡괭이 (세워 둔 것)", "picke_dirty_01", "추정", "picke_dirty_01", "floor"),
    ("P13", "나무 상자", "wooden_crate_01", "추정", "wooden_crate_01", "floor"),
    ("P14", "나무 상자 (군용)", "wooden_military_crate", "추정", "wooden_military_crate", "floor"),
    ("P15", "드럼통", "Barrel_01", "추정", "Barrel_01", "floor"),
    ("P16", "드럼통 (파랑)", "barrel_03", "추정", "barrel_03", "floor"),
    ("P17", "나무 양동이", "wooden_bucket_01", "추정", "wooden_bucket_01", "floor"),
    ("P18", "시멘트 포대", "cement_bag", "추정", "cement_bag", "floor"),
    ("P19", "나무 사다리", "wooden_ladder", "사진 1", "wooden_ladder", "floor"),
    ("P20", "쇠 선반", "worn_metal_rack", "추정", "worn_metal_rack", "floor"),
]

# EXTRA="M1|광차 (Meshy)|<glb 경로>" 로 뽑은 모델을 같은 자리·빛으로 더 찍는다 · ONLY="B2,M1" 이면 그 번호만 (props.json 은 기존 것에 더함)
for ex in filter(None, os.environ.get("EXTRA", "").split(";")):
    k, nm, path, L = ex.split("|"); CANDS.append((k, nm, "Meshy (유료 구독 · 소유)", "사진 4", ("glb", path, float(L)), "floor"))   # L = 맞출 가장 긴 수평 길이 m (Meshy 크기는 제멋대로)
ONLY = set(filter(None, os.environ.get("ONLY", "").split(",")))
if ONLY: CANDS = [c for c in CANDS if c[0] in ONLY]

def meshes_of(root_objs):
    out = []
    def walk(o):
        if o.type in ("MESH", "FONT"): out.append(o)
        for c in o.children: walk(c)
    for o in root_objs: walk(o)
    return out

def bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.evaluated_get(dg).bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); n += len(me.loop_triangles); o.evaluated_get(dg).to_mesh_clear()
    return n

# 빛 · 카메라
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0, 0, 0, 1)
for nm in ("SLOT_Light_1", "SLOT_Light_2"):
    L = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); L.data.energy = 500; L.data.color = (1.0, 0.72, 0.42)
    L.location = sc.objects[nm].matrix_world.translation - Vector((0, 0, 0.3)); sc.collection.objects.link(L)
head = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(head)
head.data.energy = 600; head.data.spot_size = math.radians(70); head.data.spot_blend = 0.5; head.data.color = (1.0, 0.93, 0.82)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 24; cam.data.clip_start = 0.05
sc.render.resolution_x, sc.render.resolution_y = 800, 500

SPOT = Vector((0.0, 1.0, 0.0))                         # 광장 가운데 조금 북쪽 (첫 자리 (0, -3.15) 에서 앞)
info = {}
for num, name, src, photo, make, place in CANDS:
    before = set(sc.objects)
    if callable(make): roots = [make()]
    else:
        f = make[1] if isinstance(make, tuple) else next(os.path.join(PH, make, x) for x in os.listdir(os.path.join(PH, make)) if x.endswith(".gltf"))
        bpy.ops.import_scene.gltf(filepath=f)
        roots = [o for o in set(sc.objects) - before if o.parent is None]
    objs = meshes_of(roots)
    lo, hi = bbox(objs); size = hi - lo
    if isinstance(make, tuple) and len(make) > 2:
        k_ = make[2] / max(size.x, size.y)
        for r in roots: r.scale *= k_
        bpy.context.view_layer.update(); lo, hi = bbox(objs); size = hi - lo
    target_z = {"floor": 0.0, "hang": 1.4 - size.z / 2, "wall": 1.5 - size.z / 2}[place]
    off = Vector((SPOT.x - (lo.x + hi.x) / 2, SPOT.y - (lo.y + hi.y) / 2, target_z - lo.z))
    for r in roots: r.location += off
    bpy.context.view_layer.update()
    lo, hi = bbox(objs); c = (lo + hi) / 2; r_ = max((hi - lo).length / 2, 0.35)
    dist = max(r_ / math.tan(math.radians(24)), 1.1)
    eye = c + Vector((0.35, -1.0, 0.45)).normalized() * dist
    cam.data.lens = 24
    if hi.z - lo.z > 2.6:                                  # 키 큰 것(케이지): 눈높이에서 뒤로 물러나 넓게 — 위로 올리면 광장 천장(4.5 m)에 박힌다
        eye = Vector((c.x + 1.0, lo.y - 3.4, 1.7)); cam.data.lens = 15
    q = (c - eye).to_track_quat("-Z", "Y")
    cam.location = eye; cam.rotation_euler = q.to_euler(); head.location = eye + Vector((0, 0, 0.1)); head.rotation_euler = q.to_euler()
    head.data.energy = min(max(600 * ((eye - c).length / 3.0) ** 2, 80), 900)   # 가까이 찍는 작은 물건이 헤드램프에 하얗게 타지 않게 (거리² 에 맞춤)
    sc.render.filepath = os.path.join(OUT, num + ".png"); bpy.ops.render.render(write_still=True)
    info[num] = dict(name=name, src=src, photo=photo, tris=tris(objs), size=[round(v, 2) for v in (hi - lo)])
    print("CHECK prop %s %s tris %d size %s" % (num, name, info[num]["tris"], info[num]["size"]))
    for o in set(sc.objects) - before: o.hide_render = True
jp = os.path.join(OUT, "props.json")
if ONLY and os.path.exists(jp): info = {**json.load(open(jp, encoding="utf-8")), **info}
json.dump(info, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("CHECK props candidates -> %s (%d)" % (OUT, len(CANDS)))
