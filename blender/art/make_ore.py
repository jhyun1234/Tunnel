"""ORE-1 — 벽에 박힌 석탄(탄층 조각). 제안서 docs/제안서_ORE1_벽_광석.md (승인 09-27: 석탄 · 띠 30° · 결 둘) · 조사 docs/기획서/조사/12_막장_광맥_레퍼런스.md
차례 1 (후보 그림): 지금 광석과 결 후보 둘을 같은 벽 · 같은 머리등 빛으로 찍는다.
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/make_ore.py
  python docs/그림/ORE1_후보.py        (사진 넣은 한 장 — build/ 만)
  출력: build/art/ore1/<now|kr|grid>_<close|near|far|lump>.png (0.9 m · 1.9 m · 4.5 m · 바닥 덩이) · info.json(삼각형). 빛은 게임이 아니다(EEVEE · 머리등 하나).
  벽: 6 × 3 m 울퉁불퉁한 판(±5 cm) — 바위(Rock031) 위에 30° 석탄 띠(1.2 m, Rock035)를 칠하고 3 cm 들어가게(now 는 지금 게임처럼 띠 없음).
차례 2 (게임, 판정 ① "둘 다 넣는다" 09-27): GAME=1 — 부스 맵 광석 자리 30곳마다 실제 벽에 광선을 쏴 결 덩이를 붙인다. 홀수 자리 = 한국식 · 짝수 = 네모식.
  python blender/art/prop_textures.py    (먼저 — coal_lump · coal_fresh · coal 질감)
  GAME=1 "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/make_ore.py
  입력: Assets/Tunnel/Pieces/booth_map.gltf(SLOT_Pocket_<i> · 충돌 그물 COL_) · blender/map/booth_table.py(자리마다 벽 쪽 방향 — make_booth 와 같은 표)
  출력: Assets/Tunnel/Art/ore_pockets.gltf — 노드 ORE_<i>_Face(둘레 결 덩이, 원점 = 자리) · ORE_<i>_Loose(캘 덩이, 원점 = 덩이 가운데 — MINE-1 이 밀고 기울임) · ORE_<i>_Gap(까만 틈)
        Assets/Tunnel/Art/ore_lump.gltf — ORE_Lump(빠져 굴러 나온 덩이 ~20 cm, 원점 = 가운데)
  석탄 띠 칠은 make_booth.py(ore_bands)가 같은 30° · 같은 방향(벽을 향해 서면 오른쪽이 올라감)으로 한다.
결: kr = 한국식(비스듬한 평행 금 → 길쭉한 판, Rk04 · Rk08) · grid = 네모식(직각 두 결 → 벽돌, Rw13 · Rw19).
캘 덩이 = 30 × 22 × 18 cm, 앞면이 벽에서 9 cm · 위가 8° 들림 · 둘레 까만 틈 · 막 벌어진 결 면이라 조금 더 반짝(우리 판단)."""
import bpy, bmesh, os, sys, math, json, random
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp

ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); OUT = os.path.join(ROOT, "build", "art", "ore1")
CT = os.path.join(ROOT, "build", "art", "cand_tex"); ART = os.path.join(ROOT, "Assets", "Tunnel", "Art")
GAME = os.environ.get("GAME", "") == "1"
TRI_MAX = 60_000                                               # 광석 30곳 삼각형 합 (제안서)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

from ore_kit import BAND_HALF, RECESS, frame, place, mk, lump_bm, tris   # 도형은 ore_kit.py (MAP4 굽기 scene_mock.py 도 같이 쓴다)

# ======================================================================= 차례 2: 게임 (GAME=1)
if GAME:
    sys.path.insert(0, os.path.join(ROOT, "blender", "map"))
    import booth_table as bt
    POCKETS = bt.build(crevices=True)["pockets"]              # make_booth 와 같은 표 · 같은 차례 (SLOT_Pocket_<i> = i 번째)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "booth_map.gltf"))
    MAP = list(sc.objects); SLOT = {o.name: o.matrix_world.translation.copy() for o in MAP if o.type == "EMPTY"}
    vs, fs = [], []
    for o in MAP:
        if o.type == "MESH" and o.name.startswith("COL_"):
            mw = o.matrix_world; k = len(vs)
            vs += [mw @ v.co for v in o.data.vertices]; fs += [[k + i for i in p.vertices] for p in o.data.polygons]
    BVH = BVHTree.FromPolygons(vs, fs); del vs, fs
    for o in MAP: bpy.data.objects.remove(o, do_unlink=True)
    GM = mp.game_materials(ROOT); MAT = dict(face=GM["coal_lump"], loose=GM["coal_fresh"], gap=GM["coal"])
    objs, stats = [], []
    for i, (o_, d_) in enumerate(POCKETS[:30], 1):
        P = SLOT["SLOT_Pocket_%d" % i].copy()
        D = Vector((d_[0], d_[1], 0)).normalized(); out = -D; along = Vector((-out.y, out.x, 0))
        def surf(c, out=out):                                  # 0.6 m 바깥에서 벽 쪽으로 — 자리 평면에서 ±0.35 m 안의 벽만(모퉁이 너머 먼 벽은 버림)
            hit = BVH.ray_cast(c + out * 0.6, -out, 1.5)
            return hit[0] if hit[0] is not None and abs((hit[0] - c).dot(out)) < 0.35 else None
        if surf(P) is None: raise SystemExit("FAIL: SLOT_Pocket_%d 앞 벽을 못 찾음" % i)
        kind = "kr" if i % 2 else "grid"
        bm, lb, gb = bmesh.new(), bmesh.new(), bmesh.new()
        cl, gc, placed, skipped = place(bm, lb, gb, kind, P, along, out, surf, random.Random(100 + i))
        objs += [mk("ORE_%d_Face" % i, bm, MAT["face"], P), mk("ORE_%d_Loose" % i, lb, MAT["loose"], cl), mk("ORE_%d_Gap" % i, gb, MAT["gap"], gc)]
        stats.append((i, kind, placed, skipped))
    lump = mp.obj("ORE_Lump", lump_bm(), MAT["face"])
    for o in objs + [lump]: mp.box_uv(o.data, 1.0 / o.data.materials[0]["uv_m"])
    n = tris(objs); few = [s for s in stats if s[2] < 25]
    print("CHECK ore pockets: %d · kr %d grid %d · tris %d (≤ %d) · blocks per pocket %d~%d · rays missed %d · few blocks %s"
          % (len(stats), sum(s[1] == "kr" for s in stats), sum(s[1] == "grid" for s in stats), n, TRI_MAX,
             min(s[2] for s in stats), max(s[2] for s in stats), sum(s[3] for s in stats), few))
    assert len(stats) == 30 and n <= TRI_MAX and not few, "FAIL: 광석 조각"
    for path, sel in ((os.path.join(ART, "ore_pockets.gltf"), objs), (os.path.join(ART, "ore_lump.gltf"), [lump])):
        bpy.ops.object.select_all(action="DESELECT")
        for o in sel: o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", use_selection=True, export_keep_originals=True, export_apply=True, export_yup=True)
        doc = json.load(open(path, encoding="utf-8")); uris = [im.get("uri", "") for im in doc.get("images", [])]
        bad = [u for u in uris if u.startswith("..") or not os.path.exists(os.path.join(ART, u.replace("%20", " ")))]
        print("CHECK ore export: %s (%d KB bin) · nodes %d · images %d outside/missing %d" % (os.path.basename(path), os.path.getsize(path[:-5] + ".bin") // 1024, len(doc["nodes"]), len(uris), len(bad)))
        assert not bad, "FAIL: 그림 경로 %s" % bad[:3]
    raise SystemExit(0)

# ======================================================================= 차례 1: 후보 그림
P0 = Vector((0.0, 0.0, 1.4))                                   # 광석 자리 (벽 = y 0, 바깥 = −y)
BU0, BN0 = frame(Vector((1, 0, 0)))
def T(i, s): return os.path.join(CT, "%s_%s.jpg" % (i, s))
def in_band(x, z): return abs((Vector((x, 0, z)) - P0).dot(BN0) + 0.03 * noise.noise(Vector((x * 3.0, 7.1, z * 3.0)))) < BAND_HALF   # 두께가 조금 변함
def wall_y(x, z, band=True):
    y = 0.05 * noise.fractal(Vector((x * 1.4, 3.3, z * 1.4)), 0.6, 2.0, 4)
    return y + (RECESS if band and in_band(x, z) else 0.0)

def coal_block_mat(name="M_CoalBlock", rough=(0.22, 0.6)):
    """깨진 면만 작게 반짝: 검은 Rock035 + 거칠기 얼룩 (ART-1 판정 ③ '빛 반사가 심하다' — 면 전체 유리 광택은 피함).
    캘 덩이는 막 벌어진 결 면이라 조금 더 반짝(0.12~0.35 — 우리 판단: 발파 직후 덩이 Rw14 가 벽보다 번쩍임)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mpn = nt.nodes.new("ShaderNodeMapping"); mpn.inputs["Scale"].default_value = (1 / 0.35,) * 3
    nt.links.new(tc.outputs["Object"], mpn.inputs["Vector"])
    def img(i, s, data):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(T(i, s), check_existing=True); n.projection = "BOX"; n.projection_blend = 0.2
        if data: n.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mpn.outputs["Vector"], n.inputs["Vector"]); return n
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    nt.links.new(img("Rock035", "Color", False).outputs["Color"], mul.inputs["A"]); mul.inputs["B"].default_value = (0.22, 0.22, 0.24, 1)
    nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough[0]; mr.inputs["To Max"].default_value = rough[1]
    nt.links.new(img("Rock035", "Roughness", True).outputs["Color"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img("Rock035", "NormalGL", True).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m

M = dict(rock=mp.pbr("M_Rock", T("Rock031", "Color"), T("Rock031", "Roughness"), T("Rock031", "NormalGL"), 1.5, tint=(0.85, 0.82, 0.78)),   # 띠 위·아래 회색 판 돌 (Rw13 · Rw14)
         coal=mp.pbr("M_CoalWall", T("Rock035", "Color"), T("Rock035", "Roughness"), T("Rock035", "NormalGL"), 0.8, tint=(0.13, 0.13, 0.14)),   # 석탄 = 검정
         floor=mp.pbr("M_Floor", T("brown_mud_03", "Color"), T("brown_mud_03", "Roughness"), T("brown_mud_03", "NormalGL"), 1.5, tint=(0.6, 0.58, 0.55)),
         block=coal_block_mat(), fresh=coal_block_mat("M_CoalFresh", (0.12, 0.35)), gap=mp.flat("M_Gap", (0.005, 0.005, 0.005), rough=1.0))

def wall(name, band):
    """울퉁불퉁한 벽 6 × 3 m (4 cm 칸). band 면 띠 안 면은 석탄 재질 + 3 cm 들어감"""
    bm = bmesh.new(); nx, nz, x0, x1, z1 = 150, 75, -3.0, 3.0, 3.0
    vs = [[bm.verts.new((x0 + (x1 - x0) * i / nx, wall_y(x0 + (x1 - x0) * i / nx, z1 * k / nz, band), z1 * k / nz)) for k in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for k in range(nz):
            f = bm.faces.new((vs[i][k], vs[i + 1][k], vs[i + 1][k + 1], vs[i][k + 1]))
            c = f.calc_center_median(); f.material_index = 1 if band and in_band(c.x, c.z) else 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M["rock"]); me.materials.append(M["coal"])
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o

def face_cluster(kind, seed=3):
    bm, lb, gb = bmesh.new(), bmesh.new(), bmesh.new()
    cl, gc, *_ = place(bm, lb, gb, kind, P0, Vector((1, 0, 0)), Vector((0, -1, 0)), lambda c: Vector((c.x, wall_y(c.x, c.z), c.z)), random.Random(seed))
    return [mk("ORE_Face_" + kind, bm, M["block"], P0), mk("ORE_Loose_" + kind, lb, M["fresh"], cl), mk("ORE_Gap_" + kind, gb, M["gap"], gc)]

def lump():
    o = mp.obj("ORE_Lump", lump_bm(), M["block"]); o.rotation_euler = (0.2, 0.3, 0.9); return o

def import_now():
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "ore.gltf"))
    new = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    root = bpy.data.objects.new("NOW", None); sc.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root: o.parent = root
    return root, new

# ---------- 장면
fl = bmesh.new(); bmesh.ops.create_grid(fl, x_segments=1, y_segments=1, size=3.0)
floor = mp.obj("Floor", fl, M["floor"], loc=(0, -3.0, 0))
W_BAND, W_PLAIN = wall("WallBand", True), wall("WallPlain", False)
CAND = {"kr": face_cluster("kr") + [lump()], "grid": face_cluster("grid") + [lump()]}   # [결 덩이 무리, 캘 덩이, 틈, 굴러 나온 덩이]
now_root, now_meshes = import_now()
now_root.scale = (1.2,) * 3                                     # POCKET_MESH_SCALE
now_root.location = (P0.x, wall_y(P0.x, P0.z, False) - 0.12, P0.z)   # POCKET_WALL_OUT (벽에서 통로 쪽으로)
now_lump_root, now_lump_meshes = import_now(); now_lump_root.location = (0.35, -0.55, 0.1)
for o in (CAND["kr"][3], CAND["grid"][3]): o.location = (0.35, -0.55, 0.075)

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0.004, 0.004, 0.004, 1)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 24
head = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(head)
head.data.energy = 200; head.data.spot_size = math.radians(60); head.data.spot_blend = 0.7   # 게임 LAMP_ANGLE_DEG 60 · 안쪽 0.3
head.data.color = (1.0, 0.93, 0.82)
sc.render.resolution_x, sc.render.resolution_y = 1000, 750
SHOTS = {"close": (Vector((0.2, -0.9, 1.55)), P0), "near": (Vector((0.3, -1.9, 1.62)), P0), "far": (Vector((0.9, -4.5, 1.62)), P0 + Vector((0, 0, -0.1))),
         "lump": (Vector((0.75, -1.25, 0.75)), Vector((0.3, -0.45, 0.1)))}

def show(tag):
    vis = {W_BAND: tag != "now", W_PLAIN: tag == "now", now_root: tag == "now", now_lump_root: tag == "now"}
    for o in sc.objects:
        if o.type in ("CAMERA", "LIGHT") or o is floor: continue
        on = None
        for k, v in vis.items():
            if o is k or o in k.children_recursive: on = v
        for k, objs in CAND.items():
            if o in objs: on = k == tag
        if on is not None: o.hide_render = not on

info = {}
for tag in ("now", "kr", "grid"):
    show(tag)
    meshes = now_meshes if tag == "now" else CAND[tag][:3]
    info[tag] = dict(tris=tris(meshes), loose_tris=tris([now_meshes[0] if tag == "now" else CAND[tag][1]]))
    for shot, (eye, at) in SHOTS.items():
        q = (at - eye).to_track_quat("-Z", "Y"); cam.location = eye; cam.rotation_euler = q.to_euler()
        head.location = eye + Vector((0, 0, 0.08)); head.rotation_euler = q.to_euler()
        sc.view_settings.exposure = 1.5 if shot == "far" else 0.0   # 멀리 = 1/r² 로 너무 어두워 밝기만 올림(게임 화면 밝기와 다름 — 그림에 적음)
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, shot)); bpy.ops.render.render(write_still=True)
    print("CHECK ore1 %s tris %d (loose %d)" % (tag, info[tag]["tris"], info[tag]["loose_tris"]))
json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
