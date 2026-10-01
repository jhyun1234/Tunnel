"""질감 후보 비교 그림 — 같은 굴 · 같은 빛(머리등 + 매단 전등 하나)에 후보만 바꿔 찍는다 (사용자 10-01 "현실적인 텍스쳐 자료를 모으고 비교군을 보여라").
  CAT=rock "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/tex_compare.py
  CAT = rock(굴 벽 · 천장) · floor(바닥) · wood(갱목 · 판자) · metal(기계 · 드럼통 · 관 · 철판) · misc(천 · 자루 · 벽 판)
후보 = build/tex_test/cc0/<CAT>/<이름>/ (색 · 노멀 · 거칠기 그림이 든 폴더) + 아래 EXTRA(이미 가진 Fab · 지금 게임 것). 한 장 크기(m)는 build/tex_test/cc0/sizes.json {이름: m} (없으면 2 m).
CAT=blend — 벽 질감 여러 장을 굴을 따라 자연스럽게 잇는 모습(사용자 10-01 "층 · 환경에 따라 자연스럽게 이어지도록"). SEQ="fab:ueknfaclw*0.5,cc0:rock/Rock022*0.55,cc0:rock/dark_rock_02" (굴 따라 차례, *숫자 = 어둡게 곱함 · tt:<build/tex_test 아래>)
  · WIDTH=얼룩이 번지는 길이 m(기본 4) · EDGE=얼룩 가장자리 폭 m(기본 0.3 — 크게 주면 뿌옇게 겹친다) · LEAN=천장이 먼저 바뀌는 눕힘
  · BAND="cc0:rock/dark_rock@0.5-1.7" (탄층 띠: 높이 m, 기울고 흐트러진 선) · WIDTH=경계가 섞이는 길이 m(기본 4) · NAME=그림 이름. 게임에서는 같은 섞기를 재질(셰이더)이 한다 — 이 그림은 목표 모습.
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

def spec(t):
    """cc0:rock/Rock022*0.55 -> (폴더, 곱)"""
    t, _, k = t.partition("*"); kind, _, rel = t.partition(":")
    return os.path.join(TT, "cc0", rel) if kind == "cc0" else os.path.join(TT, rel) if kind == "tt" else os.path.join(FAB, rel), float(k) if k else 1.0

def blend_mat(seq, band, width, length, tile=2.0, edge=0.3, lean=1.0):
    """굴을 따라 seq 의 사진을 차례로 섞는다 (경계 = 잡음으로 흐트러진 선, width m 에 걸쳐). band = 높이 띠(탄층)"""
    m = bpy.data.materials.new("BLEND"); m.use_nodes = True; nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); N = nt.nodes.new; L = nt.links.new
    tc = N("ShaderNodeTexCoord"); mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / tile,) * 3; L(tc.outputs["Object"], mp.inputs["Vector"])
    sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
    nm_ = N("ShaderNodeMapping"); nm_.inputs["Scale"].default_value = (1 / 3.0, 1 / 3.0, 1 / 0.7); L(tc.outputs["Object"], nm_.inputs["Vector"])   # 얼룩 = 옆으로 긴 덩이 (가로 3 m × 세로 0.7 m)
    nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 3.0; L(nm_.outputs["Vector"], nz.inputs["Vector"])
    def layer(t):
        d, k = spec(t); col, nor, rou, _ = maps(d); out = []
        for p_, color in ((col, True), (rou, False), (nor, False)):
            n = N("ShaderNodeTexImage"); n.image = bpy.data.images.load(p_); n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"; n.projection = "BOX"; n.projection_blend = 0.25; L(mp.outputs["Vector"], n.inputs["Vector"]); out.append(n.outputs["Color"])
        if k != 1.0:
            mx = N("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 1.0; a_, b_ = [x for x in mx.inputs if x.type == "RGBA"][:2]; b_.default_value = (k, k * 0.93, k * 0.86, 1); L(out[0], a_); out[0] = next(x for x in mx.outputs if x.type == "RGBA")
        return out
    def mix3(a_, b_, fac):
        r = []
        for x, y in zip(a_, b_):
            mx = N("ShaderNodeMix"); mx.data_type = "RGBA"; L(fac, mx.inputs["Factor"]); i0, i1 = [q for q in mx.inputs if q.type == "RGBA"][:2]; L(x, i0); L(y, i1); r.append(next(q for q in mx.outputs if q.type == "RGBA"))
        return r
    def ramp(src, lo, hi):                                                  # src 가 lo → hi 를 지날 때 0 → 1
        mr = N("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"; mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi; L(src, mr.inputs["Value"]); return mr.outputs["Result"]
    def wobble(sock, amp):                                                  # sock + (잡음 − 0.5) × amp
        st = N("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.3; st.inputs["From Max"].default_value = 0.7; L(nz.outputs[0], st.inputs["Value"])   # 잡음은 0.5 둘레에 몰려 있다 — 펴 준다
        ma = N("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; L(st.outputs["Result"], ma.inputs[0]); ma.inputs[1].default_value = amp; ma.inputs[2].default_value = -amp / 2
        ad = N("ShaderNodeMath"); ad.operation = "ADD"; L(ma.outputs[0], ad.inputs[0]); L(sock, ad.inputs[1]); return ad.outputs[0]
    ln = N("ShaderNodeMath"); ln.operation = "MULTIPLY_ADD"; L(sep.outputs["Z"], ln.inputs[0]); ln.inputs[1].default_value = lean; L(sep.outputs["X"], ln.inputs[2])   # x + z × lean
    cur = layer(seq[0]); xw = wobble(ln.outputs[0], width)
    for i, t in enumerate(seq[1:]):
        c = length * (i + 1) / len(seq) - 1.0 + 1.3 * lean; cur = mix3(cur, layer(t), ramp(xw, c - edge / 2, c + edge / 2))
    if band:
        t, _, hz = band.partition("@"); z0, z1 = (float(v) for v in hz.split("-")); dip = N("ShaderNodeMath"); dip.operation = "MULTIPLY_ADD"; L(sep.outputs["X"], dip.inputs[0]); dip.inputs[1].default_value = -0.035; L(sep.outputs["Z"], dip.inputs[2])   # 탄층이 굴을 따라 조금 기운다
        zw = wobble(dip.outputs[0], 0.7); up = ramp(zw, z0 - 0.12, z0 + 0.12); dn = ramp(zw, z1 - 0.12, z1 + 0.12); f = N("ShaderNodeMath"); f.operation = "SUBTRACT"; L(up, f.inputs[0]); L(dn, f.inputs[1]); cur = mix3(cur, layer(t), f.outputs[0])
    L(cur[0], b.inputs["Base Color"]); L(cur[1], b.inputs["Roughness"]); nm = N("ShaderNodeNormalMap"); L(cur[2], nm.inputs["Color"]); L(nm.outputs["Normal"], b.inputs["Normal"]); return m

M_ROCK = mat("rock_now", NOW, "rock_face_04", 2.0); M_FLOOR = mat("floor_now", os.path.join(TT, "fab_coalground"), None, 2.0); M_WOOD = mat("wood_now", NOW, "dark_wooden_planks", 2.0)
# 굴: 아치 (폭 3.4 · 높이 2.7 m, 길이 9 m) — 벽을 잡음으로 울퉁불퉁하게
LEN = 34.0 if CAT == "blend" else 10.0
bm = bmesh.new(); NX, NT = int(LEN * 9), 48; vs = []
for i in range(NX + 1):
    for j in range(NT + 1):
        x = -1 + LEN * i / NX; t = math.pi * j / NT; r = 1.7 + 0.22 * noise.noise(Vector((x * 0.9, t * 2.2, 3.1))) + 0.06 * noise.noise(Vector((x * 4, t * 9, 7.7)))
        vs.append(bm.verts.new((x, r * math.cos(t), 1.0 + r * math.sin(t))))
for i in range(NX):
    for j in range(NT): bm.faces.new((vs[i * (NT + 1) + j], vs[i * (NT + 1) + j + 1], vs[(i + 1) * (NT + 1) + j + 1], vs[(i + 1) * (NT + 1) + j]))
for s_ in (-1, 1): box(bm, (LEN / 2 - 1, s_ * 1.75, 0.5), (LEN, 0.3, 1.1))                    # 아치 밑 곧은 벽
WALL = obj("WALL", bm, M_ROCK, True)
bm = bmesh.new(); g = bmesh.ops.create_grid(bm, x_segments=60, y_segments=30, size=1.0)
for v in g["verts"]: v.co = Vector((LEN / 2 - 1 + v.co.x * LEN / 2, v.co.y * 1.9, 0.03 * noise.noise(Vector((v.co.x * 9, v.co.y * 5, 1.3)))))
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
CAMS = {"blend": ((0.2, -0.4, 1.7), (6.0, 0.9, 1.45)), "rock": ((0.2, -0.4, 1.7), (6.0, 0.9, 1.45)), "floor": ((0.2, 0, 1.7), (4.0, 0.2, 0.0)), "wood": ((0.0, 0.25, 1.7), (4.2, -0.3, 1.2)), "metal": ((0.4, 0, 1.7), (3.6, 0, 0.7)), "misc": ((0.4, -0.1, 1.7), (3.8, 0, 0.8))}
eye, at = CAMS[CAT]; cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(80); cam.location = eye; q = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
L = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(L); L.location = Vector(eye) + Vector((0, 0, 0.1)); L.rotation_euler = q.to_euler()
L.data.energy = 900; L.data.spot_size = math.radians(120); L.data.spot_blend = 0.7; L.data.color = (1.0, 0.93, 0.82); L.data.use_custom_distance = True; L.data.cutoff_distance = 14
P = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); sc.collection.objects.link(P); P.location = (3.6, 0.3, 2.45); P.data.energy = 160; P.data.color = (1.0, 0.62, 0.3); P.data.shadow_soft_size = 0.08
A = bpy.data.objects.new("ADAPT", bpy.data.lights.new("ADAPT", "POINT")); sc.collection.objects.link(A); A.location = (3, 0, 1.8); A.data.energy = 70; A.data.color = (0.8, 0.85, 1.0); A.data.shadow_soft_size = 4; A.data.use_shadow = False
sc.render.resolution_x, sc.render.resolution_y = 960, 540; os.makedirs(OUT, exist_ok=True)
if CAT == "blend":
    seq = os.environ.get("SEQ", "fab:ueknfaclw*0.5,cc0:rock/Rock022*0.55,cc0:rock/dark_rock_02").split(","); width = float(os.environ.get("WIDTH", "4"))
    WALL.data.materials[0] = blend_mat(seq, os.environ.get("BAND", ""), width, LEN, edge=float(os.environ.get("EDGE", "0.3")), lean=float(os.environ.get("LEAN", "1.0"))); name = os.environ.get("NAME", "blend")
    for k in range(int(LEN // 6)):                                         # 굴을 따라 6 m 마다 매단 전등
        q_ = bpy.data.objects.new("LP%d" % k, bpy.data.lights.new("LP%d" % k, "POINT")); sc.collection.objects.link(q_); q_.location = (2 + k * 6, 0.3 * (-1) ** k, 2.45); q_.data.energy = 160; q_.data.color = (1.0, 0.62, 0.3); q_.data.shadow_soft_size = 0.08
    P.hide_render = True; sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    for i in range(len(seq) - 1):                                          # 경계마다 3.5 m 앞에서 굴을 따라 본다
        c = LEN * (i + 1) / len(seq) - 1.0; e = Vector((c - width / 2 - 1.0, -0.3, 1.7)); cam.location = e; q = (Vector((c + 6, 0.7, 1.45)) - e).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler(); L.location = e + Vector((0, 0, 0.1)); L.rotation_euler = q.to_euler()
        sc.render.filepath = os.path.join(OUT, "%s_%d.png" % (name, i + 1)); bpy.ops.render.render(write_still=True)
    L.hide_render = True; cam.data.type = "ORTHO"; cam.data.sensor_fit = "HORIZONTAL"; cam.data.ortho_scale = LEN + 1; cam.location = (LEN / 2 - 1, -1.2, 1.3); cam.rotation_euler = (math.radians(90), 0, 0)   # 굴 안에서 한쪽 벽을 통째로 (펼친 그림)
    cam.data.clip_start = 0.01; sc.render.resolution_x, sc.render.resolution_y = 3200, 420
    for k in range(int(LEN // 3)): q_ = bpy.data.objects.new("F%d" % k, bpy.data.lights.new("F%d" % k, "POINT")); sc.collection.objects.link(q_); q_.location = (k * 3, -0.9, 1.4); q_.data.energy = 90; q_.data.shadow_soft_size = 1.0; q_.data.color = (1.0, 0.9, 0.78)
    sc.render.filepath = os.path.join(OUT, "%s_wall.png" % name); bpy.ops.render.render(write_still=True)
    print("CHECK tex_compare blend %s  %d textures  width %.1f m -> %s" % (name, len(seq), width, OUT)); raise SystemExit
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
