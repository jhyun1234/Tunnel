"""질감 후보 비교 그림 — 같은 굴 · 같은 빛(머리등 + 매단 전등 하나)에 후보만 바꿔 찍는다 (사용자 10-01 "현실적인 텍스쳐 자료를 모으고 비교군을 보여라").
  CAT=rock "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/tex_compare.py
  CAT = rock(굴 벽 · 천장) · floor(바닥) · wood(갱목 · 판자) · metal(기계 · 드럼통 · 관 · 철판) · misc(천 · 자루 · 벽 판)
후보 = build/tex_test/cc0/<CAT>/<이름>/ (색 · 노멀 · 거칠기 그림이 든 폴더) + 아래 EXTRA(이미 가진 Fab · 지금 게임 것). 한 장 크기(m)는 build/tex_test/cc0/sizes.json {이름: m} (없으면 2 m).
출력: build/tex_test/compare/<CAT>/<이름>.png + index.json → 묶음 그림은 tools/tex_compare_sheet.py. 질감은 세 방향 상자 투영(Blender BOX)이라 모양마다 UV 를 안 편다."""
import bpy, bmesh, os, math, json
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
CAT = os.environ.get("CAT", "rock"); TT = os.path.join(ROOT, "build", "tex_test"); OUT = os.path.join(TT, "compare", CAT)
NOW = os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "textures"); FAB = os.path.join(TT, "fab", "mine_high")
TINT = (0.55, 0.5, 0.45)                                               # scene_mock.unified_shell() 이 Fab 바위벽에 곱하는 색
EXTRA = {   # (이름, 폴더, 파일 이름 앞머리 또는 None, 한 장 m, 출처[, 곱하는 색])
    "rock": [("지금 MAP4 벽 = 옛 부스 바위 rock_face_04 (재질 칸 밀림)", NOW, "rock_face_04", 2.86, "지금 게임"), ("뜻했던 벽 = Fab 바위벽 어둡게 물들임", os.path.join(FAB, "ueknfaclw"), None, 2.0, "Fab(가짐)", TINT),
             ("Fab 광산 바위벽 ueknfaclw", os.path.join(FAB, "ueknfaclw"), None, 2.0, "Fab(가짐)"), ("Fab 착암 자국 uh1nbhzlw", os.path.join(FAB, "uh1nbhzlw"), None, 2.0, "Fab(가짐)"),
             ("Fab 회색 셰일 uebmddyn", os.path.join(FAB, "uebmddyn"), None, 2.0, "Fab(가짐)"), ("Fab 갈색 바위 ueijag3ew", os.path.join(FAB, "ueijag3ew"), None, 2.0, "Fab(가짐)"),
             ("Fab 석탄 부스러기를 벽에", os.path.join(TT, "fab_coalground"), None, 2.0, "Fab(가짐)")],
    "floor": [("지금 MAP4 바닥 = Fab 바위벽 물들임 (재질 칸 밀림)", os.path.join(FAB, "ueknfaclw"), None, 2.0, "지금 게임", TINT), ("뜻했던 바닥 = Fab 석탄 부스러기", os.path.join(TT, "fab_coalground"), None, 2.0, "Fab(가짐)"),
              ("옛 부스 바닥 brown_mud_rocks_01", NOW, "brown_mud_rocks_01", 2.0, "지금 게임"), ("Fab 어두운 진흙 ud0nfezew", os.path.join(FAB, "ud0nfezew"), None, 2.0, "Fab(가짐)")],
    "wood": [("지금 게임 dark_wooden_planks 물들임", NOW, "dark_wooden_planks", 1.25, "지금 게임", (0.62, 0.56, 0.5))],
    "metal": [("지금 게임 (단색 칠)", None, None, 2.0, "지금 게임")],
    "misc": [("지금 게임 (단색 칠)", None, None, 2.0, "지금 게임")],
}
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene

def maps(d, prefix=None):
    fs = {f.lower(): os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("_") and (prefix is None or f.lower().startswith(prefix.lower()))}
    pick = lambda keys, bad=(): next((p for f, p in sorted(fs.items()) if any(k in f for k in keys) and not any(b in f for b in bad)), None)
    return pick(("color", "albedo", "basecolor", "diff")), pick(("normalgl", "normal_gl", "nor_gl", "normal"), ("dx",)), pick(("rough",)), pick(("metal",))

def mat(name, d, prefix, tile_m, flat=None, mul=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if d is None: b.inputs["Base Color"].default_value = (*(flat or (0.07, 0.1, 0.085)), 1); b.inputs["Roughness"].default_value = 0.6; return m
    col, nor, rou, met = maps(d, prefix); tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / tile_m,) * 3
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def img(p, color):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p); n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        n.projection = "BOX"; n.projection_blend = 0.25; nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    c = img(col, True).outputs["Color"]
    if mul:
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 1.0
        a_, b_ = [x for x in mx.inputs if x.type == "RGBA"][:2]; b_.default_value = (*mul, 1); nt.links.new(c, a_); c = next(x for x in mx.outputs if x.type == "RGBA")
    nt.links.new(c, b.inputs["Base Color"])
    if rou: nt.links.new(img(rou, False).outputs["Color"], b.inputs["Roughness"])
    if met: nt.links.new(img(met, False).outputs["Color"], b.inputs["Metallic"])
    if nor: nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img(nor, False).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m

def obj(name, bm, m, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(m)
    if smooth: me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return o
def box(bm, c, s, rot=None):
    g = bmesh.ops.create_cube(bm, size=1.0)
    for v in g["verts"]: p = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])); v.co = Vector(c) + (rot @ p if rot else p)
def cyl(bm, c, r, L, axis="Z", seg=24):
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=L)
    R = {"Z": Matrix.Identity(3), "X": Matrix.Rotation(math.radians(90), 3, "Y"), "Y": Matrix.Rotation(math.radians(90), 3, "X")}[axis]
    for v in g["verts"]: v.co = R @ v.co + Vector(c)

M_ROCK = mat("rock_now", NOW, "rock_face_04", 2.0); M_FLOOR = mat("floor_now", os.path.join(TT, "fab_coalground"), None, 2.0); M_WOOD = mat("wood_now", NOW, "dark_wooden_planks", 2.0)
# 굴: 아치 (폭 3.4 · 높이 2.7 m, 길이 9 m) — 벽을 잡음으로 울퉁불퉁하게
bm = bmesh.new(); NX, NT = 90, 48; vs = []
for i in range(NX + 1):
    for j in range(NT + 1):
        x = -1 + 10 * i / NX; t = math.pi * j / NT; r = 1.7 + 0.22 * noise.noise(Vector((x * 0.9, t * 2.2, 3.1))) + 0.06 * noise.noise(Vector((x * 4, t * 9, 7.7)))
        vs.append(bm.verts.new((x, r * math.cos(t), 1.0 + r * math.sin(t))))
for i in range(NX):
    for j in range(NT): bm.faces.new((vs[i * (NT + 1) + j], vs[i * (NT + 1) + j + 1], vs[(i + 1) * (NT + 1) + j + 1], vs[(i + 1) * (NT + 1) + j]))
for s_ in (-1, 1): box(bm, (4, s_ * 1.75, 0.5), (10, 0.3, 1.1))                    # 아치 밑 곧은 벽
WALL = obj("WALL", bm, M_ROCK, True)
bm = bmesh.new(); g = bmesh.ops.create_grid(bm, x_segments=60, y_segments=30, size=1.0)
for v in g["verts"]: v.co = Vector((4 + v.co.x * 5, v.co.y * 1.9, 0.03 * noise.noise(Vector((v.co.x * 9, v.co.y * 5, 1.3)))))
FLOOR = obj("FLOOR", bm, M_FLOOR, True)
SUBJ = []                                                                           # 분류마다 후보 재질을 입힐 물체
if CAT == "rock": SUBJ = [WALL]
if CAT == "floor": SUBJ = [FLOOR]
if CAT == "wood":
    bm = bmesh.new()
    for x in (2.2, 3.8, 5.4):
        for y in (-1.25, 1.25): cyl(bm, (x, y, 1.1), 0.11, 2.2)
        cyl(bm, (x, 0, 2.28), 0.11, 2.9, "Y")
    SUBJ.append(obj("LOGS", bm, M_WOOD, True)); bm = bmesh.new()
    for k in range(9): box(bm, (2.9, -1.2 + k * 0.17, 0.95), (0.03, 0.15, 1.9))        # 판자 벽 (왼쪽)
    for z in (0.5, 1.5): box(bm, (2.94, -0.5, z), (0.03, 1.5, 0.12))
    box(bm, (3.2, 0.9, 0.42), (1.6, 0.4, 0.06)); box(bm, (2.6, 0.9, 0.2), (0.12, 0.35, 0.4)); box(bm, (3.8, 0.9, 0.2), (0.12, 0.35, 0.4))   # 긴 의자
    SUBJ.append(obj("PLANKS", bm, M_WOOD))
if CAT == "metal":
    bm = bmesh.new(); box(bm, (3.2, 0.7, 0.55), (1.3, 0.8, 1.0)); box(bm, (3.2, 0.7, 0.04), (1.6, 1.1, 0.08)); SUBJ.append(obj("MACHINE", bm, M_ROCK))
    bm = bmesh.new(); cyl(bm, (2.6, -0.9, 0.45), 0.3, 0.9); cyl(bm, (3.3, -1.0, 0.45), 0.3, 0.9); cyl(bm, (4.0, 1.45, 1.6), 0.09, 6.0, "X"); cyl(bm, (3.2, 0.2, 0.75), 0.28, 0.7, "Y"); SUBJ.append(obj("DRUMS", bm, M_ROCK, True))
    bm = bmesh.new(); box(bm, (4.4, -1.2, 0.8), (1.6, 0.03, 1.6), Matrix.Rotation(math.radians(12), 3, "X")); SUBJ.append(obj("PLATE", bm, M_ROCK))
if CAT == "misc":
    bm = bmesh.new(); g = bmesh.ops.create_grid(bm, x_segments=40, y_segments=30, size=1.0)   # 거적 덮인 광차 (늘어진 천)
    for v in g["verts"]:
        x, y = v.co.x, v.co.y; e = max(abs(x) - 0.75, abs(y) - 0.6, 0.0); v.co = Vector((3.2 + x * 1.3, 0.6 + y * 1.0, 1.05 - e * 2.6 + 0.03 * noise.noise(Vector((x * 6, y * 6, 2)))))
    SUBJ.append(obj("TARP", bm, M_ROCK, True)); bm = bmesh.new()
    for k in range(4): g = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0); [setattr(v, "co", Vector((2.5 + k * 0.55 + v.co.x * 0.3, -1.0 + v.co.y * 0.22, 0.2 + v.co.z * 0.2))) for v in g["verts"]]   # 자루
    SUBJ.append(obj("SACKS", bm, M_ROCK, True)); bm = bmesh.new(); box(bm, (5.2, -1.3, 1.1), (2.2, 0.2, 2.2)); SUBJ.append(obj("SLAB", bm, M_ROCK))      # 벽 판 (콘크리트 · 벽돌)
# 빛 = 게임에 가깝게: 머리등(스포트 120° · 14 m) + 2.8 m 에 매단 따뜻한 전등 하나 + 어둠에 익은 눈 어림
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True; next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0, 0, 0, 1)
CAMS = {"rock": ((0.2, -0.4, 1.7), (6.0, 0.9, 1.45)), "floor": ((0.2, 0, 1.7), (4.0, 0.2, 0.0)), "wood": ((0.0, 0.25, 1.7), (4.2, -0.3, 1.2)), "metal": ((0.4, 0, 1.7), (3.6, 0, 0.7)), "misc": ((0.4, -0.1, 1.7), (3.8, 0, 0.8))}
eye, at = CAMS[CAT]; cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(80); cam.location = eye; q = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
L = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(L); L.location = Vector(eye) + Vector((0, 0, 0.1)); L.rotation_euler = q.to_euler()
L.data.energy = 900; L.data.spot_size = math.radians(120); L.data.spot_blend = 0.7; L.data.color = (1.0, 0.93, 0.82); L.data.use_custom_distance = True; L.data.cutoff_distance = 14
P = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); sc.collection.objects.link(P); P.location = (3.6, 0.3, 2.45); P.data.energy = 160; P.data.color = (1.0, 0.62, 0.3); P.data.shadow_soft_size = 0.08
A = bpy.data.objects.new("ADAPT", bpy.data.lights.new("ADAPT", "POINT")); sc.collection.objects.link(A); A.location = (3, 0, 1.8); A.data.energy = 70; A.data.color = (0.8, 0.85, 1.0); A.data.shadow_soft_size = 4; A.data.use_shadow = False
sc.render.resolution_x, sc.render.resolution_y = 960, 540; os.makedirs(OUT, exist_ok=True)
sizes = json.load(open(os.path.join(TT, "cc0", "sizes.json"), encoding="utf-8")) if os.path.exists(os.path.join(TT, "cc0", "sizes.json")) else {}
cands = list(EXTRA.get(CAT, [])); cd = os.path.join(TT, "cc0", CAT)
for n in sorted(os.listdir(cd)) if os.path.isdir(cd) else []:
    d = os.path.join(cd, n)
    if os.path.isdir(d) and not n.startswith("_") and maps(d)[0]: cands.append((n, d, None, float(sizes.get(n, 2.0)), open(os.path.join(d, "source.txt"), encoding="utf-8", errors="ignore").read()[:400] if os.path.exists(os.path.join(d, "source.txt")) else ""))
index = []
for k, (name, d, prefix, tile, src, *mul) in enumerate(cands):
    m = mat("C%d" % k, d, prefix, tile, mul=mul[0] if mul else None)
    for o in SUBJ: o.data.materials[0] = m
    fn = "%02d.png" % k; sc.render.filepath = os.path.join(OUT, fn); bpy.ops.render.render(write_still=True)
    index.append(dict(file=fn, name=name, tile_m=tile, source=src, color=maps(d, prefix)[0] if d else None)); print("CHECK tex %s %s" % (CAT, name))
json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("CHECK tex_compare %s  %d candidates -> %s" % (CAT, len(index), OUT))
