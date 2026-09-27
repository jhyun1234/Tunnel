"""ORE-1 차례 1 — 벽에 박힌 석탄(탄층 조각) 후보 둘을 지금 광석과 같은 벽·같은 머리등 빛으로 찍는다.
제안서 docs/제안서_ORE1_벽_광석.md (승인 09-27: 석탄 · 띠 30° · 결 후보 둘) · 조사 docs/기획서/조사/12_막장_광맥_레퍼런스.md
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/make_ore.py
  python docs/그림/ORE1_후보.py        (사진 넣은 한 장 — build/ 만)
후보: kr = 한국식(비스듬한 평행 금 → 길쭉한 판, Rk04 · Rk08) · grid = 네모식(직각 두 결 → 벽돌, Rw13 · Rw19) · now = 지금 ore.gltf(× 1.2, 벽에서 0.12 m).
벽: 3 × 2.6 m 울퉁불퉁한 판(±5 cm). 바위(Rock031) 위에 30° 기운 석탄 띠(두께 1.2 m, Rock035)를 칠하고 3 cm 들어가게 —
게임에서는 make_booth 가 광석 자리 둘레 벽 점에 칠할 것과 같은 뜻(now 는 지금 게임처럼 띠 없음).
광석 자리 P0 = 바닥 위 1.4 m. 캘 덩이(ORE_Loose) = 30 × 22 × 18 cm, 둘레보다 3 cm 더 나옴(결 틈이 벌어짐).
출력: build/art/ore1/<now|kr|grid>_<close|near|far|lump>.png (0.9 m · 1.9 m · 4.5 m · 바닥 덩이) · info.json(삼각형). 빛은 게임이 아니다(EEVEE · 머리등 하나)."""
import bpy, bmesh, os, sys, math, json, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp

ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); OUT = os.path.join(ROOT, "build", "art", "ore1")
CT = os.path.join(ROOT, "build", "art", "cand_tex")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

P0 = Vector((0.0, 0.0, 1.4))                                   # 광석 자리 (벽 = y 0, 바깥 = −y)
DIP = math.radians(30)                                         # 띠 기울기 (사용자 09-27)
BU = Vector((math.cos(DIP), 0, math.sin(DIP)))                 # 띠 방향
BN = Vector((-math.sin(DIP), 0, math.cos(DIP)))                # 벽 안에서 띠에 수직
BAND_HALF, RECESS = 0.6, 0.03                                  # 띠 두께 1.2 m (한국 평균 1.4 · 사진 1.2~1.4) · 석탄이 3 cm 들어감(무른 쪽이 먼저 떨어짐 — 우리 판단)
LOOSE = (0.30, 0.18, 0.22)                                     # 캘 덩이: 결 방향 길이 · 깊이 · 폭 (지금 덩이 27 × 18 × 22 와 비슷)

def T(i, s): return os.path.join(CT, "%s_%s.jpg" % (i, s))
def band_d(x, z): return (Vector((x, 0, z)) - P0).dot(BN)
def in_band(x, z): return abs(band_d(x, z) + 0.03 * noise.noise(Vector((x * 3.0, 7.1, z * 3.0)))) < BAND_HALF   # 두께가 조금 변함
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

def block(bm, c, ax, size, jit, rnd):
    """모난 덩이: 상자 모서리 8 점을 jit 만큼 흔든 볼록 껍질 (삼각형 12). ax = (길이 축, 바깥 축, 폭 축)"""
    pts = [bm.verts.new(c + sum((a * (s_ * sz / 2 + rnd.uniform(-jit, jit)) for a, s_, sz in zip(ax, sg, size)), Vector()))
           for sg in [(a, b, d) for a in (-1, 1) for b in (-1, 1) for d in (-1, 1)]]
    r = bmesh.ops.convex_hull(bm, input=pts)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")

def hull(bm, c, ax, size, rnd):
    """모난 덩이(면 많음): 상자 모서리 8 + 면 가운데 6 점을 흔든 볼록 껍질"""
    pts = [Vector((sx, sy, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    vs = [bm.verts.new(c + sum((a * (q * sz / 2 * (0.85 if p_.length > 1.2 else 1.15) * rnd.uniform(0.85, 1.1)) for a, q, sz in zip(ax, p_, size)), Vector())) for p_ in pts]
    r = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")

def falloff(t, d):                                             # 덩이 무리 가장자리로 갈수록 벽에 묻힘 (띠 칠과 이어지게)
    return max(0.0, 1 - (t / 0.62) ** 2 - (d / BAND_HALF) ** 2)

def face_cluster(kind, seed=3):
    """캘 덩이 둘레의 결 덩이 무리 + 캘 덩이. kind = kr(비스듬한 평행 금 → 길쭉한 판) | grid(띠와 나란한 층 × 직각 결 → 벽돌)"""
    rnd = random.Random(seed); bm = bmesh.new(); lb = bmesh.new(); out = Vector((0, -1, 0))
    if kind == "grid":                                         # 층(띠와 나란히) 6~12 cm · 벽돌 길이 8~20 cm · 줄마다 엇갈림
        ax = (BU, out, BN); d = -BAND_HALF
        while d < BAND_HALF:
            h = rnd.uniform(0.06, 0.12); t = -0.7 + rnd.uniform(0, 0.1)
            while t < 0.7:
                L = rnd.uniform(0.08, 0.2); c2 = P0 + BU * (t + L / 2) + BN * (d + h / 2)
                w = falloff(t + L / 2, d + h / 2)
                if w > 0 and rnd.random() > 0.08 and (c2 - P0).length > 0.2:
                    prot = w * rnd.uniform(0.005, 0.03); sn = 0.08
                    c3 = Vector((c2.x, wall_y(c2.x, c2.z) - prot + sn / 2, c2.z))
                    block(bm, c3, ax, (L - 0.012, sn, h - 0.01), 0.008, rnd)
                t += L
            d += h
    else:                                                      # 금 방향 = 수평에서 60° (한국 사진 45~60°) — 판은 금을 따라 길쭉, 두께 3~8 cm
        cd = Vector((math.cos(math.radians(60)), 0, math.sin(math.radians(60)))); cn = Vector((-cd.z, 0, cd.x))
        ax = (cd, out, cn); s = -0.8
        while s < 0.8:
            th = rnd.uniform(0.03, 0.08); a = -0.8 + rnd.uniform(0, 0.12)
            while a < 0.8:
                L = rnd.uniform(0.12, 0.3); c2 = P0 + cn * (s + th / 2) + cd * (a + L / 2)
                t, d = (c2 - P0).dot(BU), (c2 - P0).dot(BN); w = falloff(t, d)
                if w > 0 and rnd.random() > 0.08 and (c2 - P0).length > 0.2:
                    prot = w * rnd.uniform(0.005, 0.035); sn = 0.08
                    c3 = Vector((c2.x, wall_y(c2.x, c2.z) - prot + sn / 2, c2.z))
                    block(bm, c3, ax, (L - 0.012, sn, th - 0.008), 0.007, rnd)
                a += L + rnd.uniform(0, 0.02)
            s += th
    L_, D_, W_ = LOOSE                                         # 캘 덩이: 둘레(최대 3.5 cm)보다 더 — 앞면이 벽에서 9 cm, 위가 8° 들림(결 틈이 벌어짐)
    tilt = Matrix.Rotation(math.radians(8), 3, BU); axl = tuple(tilt @ a for a in ax); cl = Vector((P0.x, wall_y(P0.x, P0.z) - 0.09 + D_ / 2, P0.z))
    hull(lb, cl, axl, (L_, D_, W_), rnd)                       # 모서리 14 점 — 면이 여러 방향이라 머리등에 어느 한 면은 번쩍
    gb = bmesh.new(); block(gb, cl + Vector((0, D_ / 2 - 0.02, 0)), axl, (L_ * 1.25, 0.03, W_ * 1.3), 0.01, rnd)   # 벌어진 틈 = 덩이 뒤 까만 판(가장자리만 보임)
    face = mp.obj("ORE_Face_" + kind, bm, M["block"]); loose = mp.obj("ORE_Loose_" + kind, lb, M["fresh"]); gap = mp.obj("ORE_Gap_" + kind, gb, M["gap"])
    return [face, loose, gap]

def lump(seed=11, size=0.2):
    """굴러 나온 탄 덩이 ~20 cm (Rk25 손에 든 15~20 · 모난 덩이): 깨진 상자 점 14 개의 볼록 껍질 (coal_heap 덩어리와 같은 방식)"""
    rnd = random.Random(seed); bm = bmesh.new()
    pts = [Vector((sx, sy, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    sq = Vector((1.0, 0.75, 0.6))
    vs = [bm.verts.new(Vector([q * s_ * size * 0.5 * rnd.uniform(0.8, 1.1) for q, s_ in zip(p_ * (0.85 if p_.length > 1.2 else 1.2), sq)])) for p_ in pts]
    r = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")
    o = mp.obj("ORE_Lump", bm, M["block"]); o.rotation_euler = (0.2, 0.3, 0.9); return o

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
head.data.energy = 200; head.data.spot_size = math.radians(60); head.data.spot_blend = 0.7   # 게임 LAMP_ANGLE_DEG 60 · 안쪽 0.3; head.data.color = (1.0, 0.93, 0.82)
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
    info[tag] = dict(tris=sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons),
                     loose_tris=sum(len(p.vertices) - 2 for p in (now_meshes[0] if tag == "now" else CAND[tag][1]).data.polygons))
    for shot, (eye, at) in SHOTS.items():
        q = (at - eye).to_track_quat("-Z", "Y"); cam.location = eye; cam.rotation_euler = q.to_euler()
        head.location = eye + Vector((0, 0, 0.08)); head.rotation_euler = q.to_euler()
        sc.view_settings.exposure = 1.5 if shot == "far" else 0.0   # 멀리 = 1/r² 로 너무 어두워 밝기만 올림(게임 화면 밝기와 다름 — 그림에 적음)
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, shot)); bpy.ops.render.render(write_still=True)
    print("CHECK ore1 %s tris %d (loose %d)" % (tag, info[tag]["tris"], info[tag]["loose_tris"]))
json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
