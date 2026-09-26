"""PICK-1 A — 보령석탄박물관 탄광 곡괭이를 치수 표대로 코드로 만든다 (제안서 docs/제안서_PICK1_곡괭이_모양.md, 2026-09-27 승인).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/props/make_pick.py
출력(새 파일): Assets/Tunnel/Props/pick_blender.glb — 그림은 GLB 안에
틀(옛 pick.gltf 와 같다 — Tuning 의 PICK_POS·기울기를 그대로 쓰려고): 자루 = Blender +Z(glTF +Y) · 머리 너비 = X ·
    뾰족한 날 = +X(Unity 로 가면 X 가 뒤집히고 PICK_YAW 90° 가 돌려 앞 = 벽 쪽) · 원점 = 자루 끝에서 15 cm(쥐는 곳) · 물체 PICK_Handle · PICK_Head
자기 검사(내보낸 GLB 를 다시 읽어서, FAIL 이면 종료 1): 긴 축 68 cm ±1 % · 머리 끝에서 끝 32 cm ±1 cm · 날이 +X 한쪽에만(반대쪽 꼭지 ≤ 머리의 20 %) ·
    자루가 머리 쪽이 더 굵음 · 원점(자루 끝 = −15 cm) · 이름 · 삼각형 ≤ 8,000 · 그림 4장 이상이 GLB 안에
사보타주: SABOTAGE=twopoint(양쪽 날) · noscale(자루 1.3배) · thinhead(굵기 거꾸로) → 각각 FAIL"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "Assets", "Tunnel", "Props", "pick_blender.glb")
TEX_WOOD = os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "textures", "dark_wooden_planks_")
TEX_IRON = os.path.join(HERE, "tex", "rusty_metal_04_")
SAB = os.environ.get("SABOTAGE", "")

# ── 치수 (m) — 조사 10 · 제안서 표. "사진에서 잼" 은 보령 381·383·386 사진 ──
HANDLE = 0.66                 # 자루 길이 (보령 64·69 cm 가운데, 사용자 09-27)
GRIP = 0.15                   # 원점 = 자루 끝에서 (옛 pick.gltf 와 같다)
CAP = 0.02                    # 쇠 통이 자루 끝 위로 덮는 만큼 (사진에서 잼)
HEAD = 0.32                   # 머리 끝에서 끝 (보령 29·32·34 cm)
KNOB_FRAC = 0.16              # 위 네모 꼭지 몫 (381 사진에서 잼) — 나머지 84 % 가 날
BEND = 0.04                   # 날 끝이 자루 쪽으로 휜 만큼 — 날 전체가 바나나처럼 (사진에서 잼)
R_TOP, R_END = 0.022, 0.0165  # 자루 반지름: 머리 쪽 / 끝 (굵기 4.4 → 3.3 cm, 사진에서 잼)
SOCK_R, SOCK_H = 0.033, 0.06  # 쇠 통 반지름·높이 (386: 너비 7 · 높이 6 cm)
BLADE_H, BLADE_T = 0.050, 0.030   # 날 밑동 높이(자루 방향)·두께 (너비 5.5~6 cm 기록 → 어림)
IRON_TINT = (0.50, 0.47, 0.45)    # 쇠를 검게: 녹 + 탄가루 (보령 사진은 거의 검정 — 우리 어림)
WOOD_TINT = (0.62, 0.58, 0.55)    # 나무도 거무스름하게 (보령 381·383 — 우리 어림)
TRIS_MAX = 8000
if SAB == "noscale": HANDLE *= 1.3
if SAB == "thinhead": R_TOP, R_END = R_END, R_TOP

Z_END = -GRIP
Z_TOP = HANDLE - GRIP
Z_CAP = Z_TOP + CAP
ZC = Z_CAP - SOCK_H / 2       # 머리 가운데 높이
POINT_X = HEAD * (1 - KNOB_FRAC)
KNOB_X = HEAD * KNOB_FRAC


# ── 그물 ──
def handle_mesh():
    bm = bmesh.new(); N = 20
    cracks = [(0.7, -0.10, 0.25), (2.9, 0.00, 0.45), (4.4, -0.14, 0.10)]   # (각, z 시작, z 끝) 세로 갈라짐 — 수는 지어냄
    def radius(z, th):
        t = (z - Z_END) / HANDLE
        r = R_END + (R_TOP - R_END) * t + 0.0018 * math.exp(-((z - Z_END) / 0.02) ** 2)   # 끝이 뭉개져 조금 부풂 (383)
        for a, z0, z1 in cracks:
            dth = abs((th - a + math.pi) % (2 * math.pi) - math.pi)
            if z0 < z < z1 and dth < 0.09:
                r -= 0.0012 * (1 - dth / 0.09) * math.sin(math.pi * (z - z0) / (z1 - z0))
        return r
    zs = list(np.linspace(Z_END + 0.006, Z_TOP, 44))
    rings = []
    def ring(z, k=1.0):
        vs = []
        for i in range(N):
            th = 2 * math.pi * i / N; r = radius(z, th) * k
            vs.append(bm.verts.new((r * math.cos(th), 0.9 * r * math.sin(th), z)))   # 조금 납작한 타원
        return vs
    rings.append(ring(Z_END + 0.0015, 0.72))
    for z in zs: rings.append(ring(z))
    for a, b in zip(rings, rings[1:]):
        for i in range(N):
            bm.faces.new((a[i], a[(i + 1) % N], b[(i + 1) % N], b[i]))
    bot = bm.verts.new((0, 0, Z_END)); top = bm.verts.new((0, 0, Z_TOP))
    for i in range(N):
        bm.faces.new((rings[0][(i + 1) % N], rings[0][i], bot))
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % N], top))
    for f in bm.faces: f.smooth = True
    # UV: 나무결 = 자루 길이 방향, 둘레는 널빤지 한 장 폭 안에
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        ths = [math.atan2(l.vert.co.y / 0.9, l.vert.co.x) % (2 * math.pi) for l in f.loops]
        wrap = max(ths) - min(ths) > math.pi
        for l, th in zip(f.loops, ths):
            if wrap and th < math.pi: th += 2 * math.pi
            l[uv].uv = ((l.vert.co.z - Z_END) / HANDLE * 0.55 + 0.02, 0.29 + th / (2 * math.pi) * 0.085)
    return bm


def box_uv(bm, scale=0.25):
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        for l in f.loops: l[uv].uv = (l.vert.co[a] / scale, l.vert.co[b] / scale)


def blade(bm, sign):
    """날 하나: 머리 가운데에서 sign(+1 = +X) 쪽으로, 끝이 자루 쪽(−Z)으로 휜다. 단면 = 모서리 깎은 네모."""
    n = 16; secs = []
    for i in range(n):
        u = i / n
        x = sign * (0.005 + (POINT_X - 0.005) * u)
        zc = ZC - BEND * u ** 1.6
        h = BLADE_H / 2 * (1 - u) ** 0.6 + 0.0012     # 밑동 절반까지 굵다가 끝에서 가늘어짐 (381 사진)
        t = BLADE_T / 2 * (1 - u) ** 0.6 + 0.0012
        c = min(h, t) * 0.35
        pts = [(t - c, h), (t, h - c), (t, -h + c), (t - c, -h), (-t + c, -h), (-t, -h + c), (-t, h - c), (-t + c, h)]
        secs.append([bm.verts.new((x, y, zc + z)) for y, z in pts])
    tip = bm.verts.new((sign * POINT_X, 0, ZC - BEND))
    for a, b in zip(secs, secs[1:]):
        for k in range(8):
            f = bm.faces.new((a[k], a[(k + 1) % 8], b[(k + 1) % 8], b[k]) if sign > 0 else (a[k], b[k], b[(k + 1) % 8], a[(k + 1) % 8]))
            f.smooth = True
    for k in range(8):
        f = bm.faces.new((secs[-1][k], secs[-1][(k + 1) % 8], tip) if sign > 0 else (secs[-1][(k + 1) % 8], secs[-1][k], tip)); f.smooth = True
    f = bm.faces.new(secs[0][::-1] if sign > 0 else secs[0])   # 쇠 통 안에 묻히는 밑동 뚜껑


def head_mesh():
    bm = bmesh.new()
    # 쇠 통: 둥근 통, 자루 끝을 감싼다 (윗면·아랫면 모서리 조금 둥글게)
    N = 28; prof = [(SOCK_R * 0.80, Z_CAP - SOCK_H), (SOCK_R * 0.97, Z_CAP - SOCK_H + 0.002), (SOCK_R, Z_CAP - SOCK_H + 0.006),
                    (SOCK_R, Z_CAP - 0.006), (SOCK_R * 0.97, Z_CAP - 0.002), (SOCK_R * 0.80, Z_CAP)]
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / N), r * math.sin(2 * math.pi * i / N) * 0.92, z)) for i in range(N)] for r, z in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(N): bm.faces.new((a[i], a[(i + 1) % N], b[(i + 1) % N], b[i])).smooth = True
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    blade(bm, +1)
    if SAB == "twopoint":
        blade(bm, -1)
    else:   # 위 네모 꼭지 (반대쪽, 짧은 두드리는 면)
        r = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        L = KNOB_X - SOCK_R * 0.5
        for v in r:
            v.co = Vector((-(SOCK_R * 0.5 + (v.co.x + 0.5) * L), v.co.y * 0.030, ZC + v.co.z * 0.040))
        edges = list({e for v in r for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=r + edges, offset=0.003, segments=2, affect="EDGES", profile=0.5)
    # 쇠 통 아래 납작한 쐐기 (381 사진 — 모양은 어림)
    w = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    for v in w:
        v.co = Vector((0.0215 + v.co.x * 0.004, v.co.y * 0.014, (Z_CAP - SOCK_H) - 0.012 + v.co.z * 0.03))
    box_uv(bm)
    return bm


# ── 재질 ──
def load(path, noncolor=False):
    im = bpy.data.images.load(path)
    if noncolor: im.colorspace_settings.name = "Non-Color"
    return im


def tinted(path, tint):
    """사진 그림을 곱해 어둡게 한 새 그림(GLB 에 들어간다)."""
    src = load(path); w, h = src.size
    px = np.empty(w * h * 4, dtype=np.float32); src.pixels.foreach_get(px)
    px = px.reshape(-1, 4); px[:, :3] *= np.array(tint, dtype=np.float32)
    im = bpy.data.images.new(os.path.basename(path).replace(".jpg", "_dark"), w, h)
    im.pixels.foreach_set(px.ravel()); im.pack()
    bpy.data.images.remove(src)
    return im


def material(name, base_img, nor_img, rough_img=None, arm_img=None):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    def tex(img, x):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.location = (x, 0); return t
    nt.links.new(tex(base_img, -600).outputs["Color"], bsdf.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tex(nor_img, -600).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if arm_img:     # AO·거칠기·쇠 = R·G·B (glTF 와 같은 배치)
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tex(arm_img, -600).outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    else:
        nt.links.new(tex(rough_img, -600).outputs["Color"], bsdf.inputs["Roughness"]); bsdf.inputs["Metallic"].default_value = 0.0
    return m


def obj(name, bm, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


# ── 만들기 · 내보내기 ──
bpy.ops.wm.read_factory_settings(use_empty=True)
wood = material("MAT_PickWood", tinted(TEX_WOOD + "Diffuse.jpg", WOOD_TINT), load(TEX_WOOD + "nor_gl.jpg", True), rough_img=load(TEX_WOOD + "Rough.jpg", True))
iron = material("MAT_PickIron", tinted(TEX_IRON + "diff_1k.jpg", IRON_TINT), load(TEX_IRON + "nor_gl_1k.jpg", True), arm_img=load(TEX_IRON + "arm_1k.jpg", True))
obj("PICK_Handle", handle_mesh(), wood)
obj("PICK_Head", head_mesh(), iron)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True, export_image_format="JPEG", export_jpeg_quality=90)
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))

# ── 자기 검사: 내보낸 GLB 를 다시 읽는다 ──
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT)
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)
obs = {o.name.split(".")[0]: o for o in bpy.data.objects if o.type == "MESH"}
check("PICK_Handle" in obs and "PICK_Head" in obs, "물체 이름 PICK_Handle · PICK_Head (%s)" % sorted(obs))
def pts(o): return np.array([o.matrix_world @ v.co for v in o.data.vertices])
allp = np.vstack([pts(o) for o in obs.values()])
long_ = allp[:, 2].max() - allp[:, 2].min(); want = 0.66 + CAP
check(abs(long_ - want) <= want * 0.01, "긴 축 %.3f m (표 %.2f ±1 %%)" % (long_, want))
check(abs(allp[:, 2].min() + GRIP) <= 0.003, "원점: 자루 끝 z %.3f (−%.2f)" % (allp[:, 2].min(), GRIP))
hp = pts(obs["PICK_Head"]); hw = hp[:, 0].max() - hp[:, 0].min()
check(abs(hw - 0.32) <= 0.01, "머리 끝에서 끝 %.3f m (0.32 ±0.01)" % hw)
kn = -hp[:, 0].min() / hw
check(hp[:, 0].max() > 0.2 and kn <= 0.20, "날은 +X 한쪽에만: +X 끝 %.3f · 반대쪽 %.0f %% (≤ 20 %%)" % (hp[:, 0].max(), kn * 100))
hd = pts(obs["PICK_Handle"])
def rad(z0, z1):
    s = hd[(hd[:, 2] > z0) & (hd[:, 2] < z1)]; return np.abs(s[:, 0]).max()
rt, re = rad(Z_TOP - 0.10, Z_TOP - 0.05), rad(-GRIP + 0.05, -GRIP + 0.10)
check(rt > re * 1.1, "자루가 머리 쪽이 굵음: 위 %.1f · 끝 %.1f mm (반지름)" % (rt * 1000, re * 1000))
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in obs.values())
check(tris <= TRIS_MAX, "삼각형 %d ≤ %d" % (tris, TRIS_MAX))
imgs = [im for im in bpy.data.images if im.size[0] > 0]
check(len(imgs) >= 4, "GLB 안 그림 %d 장 (%s)" % (len(imgs), ", ".join(sorted(im.name for im in imgs))))
print("make_pick: %s (%d FAIL)" % ("ALL PASS" if not fails else "FAIL", len(fails)))
sys.exit(1 if fails else 0)
