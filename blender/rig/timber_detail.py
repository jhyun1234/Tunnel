"""timber_detail — 괴물 몸의 갱목(판자 3)·못 5·가죽끈 9 를 사실적으로 (제안서 docs/제안서_3D3b_갱목_못_사실감.md, 승인 2026-09-19).
  MODE=preview WOOD=rough_wood "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/timber_detail.py
입력: Documents/MineTunnel/blender/miner_v4_stage14_plank.blend — 안 고친다
MODE=preview (M1): 모양을 새로 만들고 WOOD 후보 재질을 입혀 가까이 찍기만 한다 (저장 없음) → 사용자가 나무를 고른다
MODE=build (M2, 사용자 09-19 "1번 rough_wood"): 판자마다 썩음·그늘(AO)·석탄 먼지·못 둘레 검은 물·젖은 반들거림을 그림 3장(색·반들거림·요철)에 굽고,
  못·가죽끈은 CC0 그림을 물들여 3장씩 → 자기 검사 → Documents/MineTunnel/blender/miner_v4_stage15_timber.blend (+ blender/stage15_tex/*.png)
사보타주: MODE=build SABOTAGE=boxes -> 상자 그대로·반들거림 그림 없음 (검사 크기·못·꼭짓점·재질 FAIL). 사보타주 실행은 저장하지 않는다
레퍼런스(제안서 Step 1): 쪼갠 널은 면이 비뚤고 끝이 짓눌리며 결 따라 갈라진다 · 손으로 두드린 못은 네 면이 끝으로 가늘어지는 네모 몸통 + 장미 머리 ·
철도 대못 몸통 1.6 cm · 전체 15 cm · 머리 3.5 cm (게임 크기, 모델은 ÷ 1.5)"""
import bpy, bmesh, os, sys, math, random
import numpy as np
from mathutils import Vector, Matrix, noise

MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v4_stage14_plank.blend"))   # WOOD=before SRC_BLEND=…stage15… TAG=after = 만든 뒤 같은 자리에서 찍기
TEX = os.path.join(MT, "textures")
MODE = os.environ.get("MODE", "preview")
WOOD = os.environ.get("WOOD", "rough_wood")                # 사용자 09-19: 1번 rough_wood
SABOTAGE = os.environ.get("SABOTAGE", "")
OUT = os.path.join(MT, "blender", "miner_v4_stage15_timber.blend")
TEX_OUT = os.path.join(MT, "blender", "stage15_tex")
BAKE_PX = {"Plank_Back": 1024, "Plank_Forearm_L": 512, "Plank_Shin_R": 512}
SHOTS = os.environ.get("SHOTS", os.path.join(MT, "blender", "timber_render"))
SCALE = 1.5                                              # Tuning.STALKER_MODEL_SCALE — 아래 크기는 게임 크기 ÷ SCALE
THICK = {"Plank_Back": 0.06 / SCALE, "Plank_Forearm_L": 0.05 / SCALE, "Plank_Shin_R": 0.05 / SCALE}
NAIL_TOTAL, NAIL_SHANK, NAIL_HEAD = 0.15 / SCALE, 0.016 / SCALE, 0.035 / SCALE
NAIL_VIS = (0.04 / SCALE, 0.09 / SCALE)                   # 밖에 보이는 몸통 길이
NAIL_JITTER_DEG, NAIL_BEND = 20.0, {1: 8.0, 3: 6.0}       # 박힌 각도 흔들림 · 휜 못(번호: 도)
# 나무 후보: 결 방향(u/v), 판자 한 장이 차지하는 가로 범위(그림 좌표), 결 방향 한 번 반복 = 모델 m
CAND = {"rough_wood": dict(grain="v", cross=(0.0, 1.0), cross_m=0.6, tile=0.8),     # 판자 한 장짜리 그림 — 가로 0.6 m 로 (좁은 판자에 그림 전체를 넣으면 뭉개진다)
        "medieval_wood": dict(grain="v", cross=(0.035, 0.165), tile=0.8),
        "wooden_rough_planks": dict(grain="u", cross=(0.015, 0.150), tile=0.8)}
DARKEN = {"wood": 0.55, "iron": 0.35, "leather": 0.10}   # 가죽: 광부 허리띠는 두꺼운 검은 가죽 [요약 Powerhouse]
RUST_TINT = (0.30, 0.17, 0.10)                           # rusty_metal_02 는 회색 페인트 위 녹 — 어두운 녹 쪽으로 물들인다 (0.55 는 주황으로 떴다)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
arm = bpy.data.objects["Miner_Rig"]
M = arm.matrix_world.copy()
ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
ad.action = None
arm.data.pose_position = "POSE"
for p in arm.pose.bones:
    p.rotation_mode = "QUATERNION"; p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0); p.scale = (1, 1, 1)
bpy.context.view_layer.update()

def bone_point(o, x):
    """부모 뼈 선분 위에서 x 에 가장 가까운 점 (몸 쪽 방향을 정할 때)"""
    b = arm.pose.bones[o.parent_bone]
    h, t = M @ b.head, M @ b.tail
    d = t - h; k = max(0.0, min(1.0, (x - h).dot(d) / d.length_squared))
    return h + d * k

def unit_frame(o):
    """물체 크기(비균일 배율)를 빼고 자리·회전만 남긴다 — 새 메시는 이 틀에서 m 단위로"""
    loc, rot, _ = o.matrix_world.decompose()
    o.matrix_world = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    bpy.context.view_layer.update()

def set_mesh(o, world_verts, faces, uvs, name):
    mwi = o.matrix_world.inverted()
    me = bpy.data.meshes.new(name)
    me.from_pydata([mwi @ Vector(v) for v in world_verts], [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = uvs[(poly.index, vi)] if (poly.index, vi) in uvs else (0, 0)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    for m in o.data.materials:
        me.materials.append(m)
    old = o.data; o.data = me; bpy.data.meshes.remove(old)

# ---------------- 판자
PLANK_FRAME, PLANK_PAR, NAIL_INFO = {}, {}, {}
def rebuild_plank(o, seed, build=True):
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    R = o.matrix_world.to_3x3().normalized()
    axes = [R.col[i].normalized() for i in range(3)]
    c = sum(ws, Vector()) / len(ws)
    ext = [(min((w - c).dot(a) for w in ws), max((w - c).dot(a) for w in ws)) for a in axes]
    size = [e[1] - e[0] for e in ext]
    iL = int(np.argmax(size)); iT = int(np.argmin(size)); iW = 3 - iL - iT
    aL, aW, aT = axes[iL], axes[iW], axes[iT]
    if (bone_point(o, c) - c).dot(aT) > 0:              # aT = 몸에서 바깥으로
        aT = -aT
    body_t = min((w - c).dot(aT) for w in ws)           # 몸 쪽 면
    L = size[iL]; Wd = size[iW]; T = THICK[o.name]
    P0 = c + aL * ext[iL][0] + aW * ((ext[iW][0] + ext[iW][1]) / 2) + aT * body_t
    PLANK_FRAME[o.name] = (P0, aL, aW, aT, L, Wd, T)
    if not build:                                         # WOOD=before: 지금 모양 그대로 찍기
        return len(ws)
    unit_frame(o)
    nl, nw, nt = max(12, int(L / 0.014)), max(6, int(Wd / 0.012)), 3
    idx, par, verts, faces, kinds = {}, [], [], [], []
    def V(i, j, k):
        if (i, j, k) not in idx:
            idx[(i, j, k)] = len(par); par.append((i / nl, j / nw, k / nt))
        return idx[(i, j, k)]
    for i in range(nl):
        for j in range(nw):
            faces.append((V(i, j, 0), V(i, j + 1, 0), V(i + 1, j + 1, 0), V(i + 1, j, 0))); kinds.append("T")
            faces.append((V(i, j, nt), V(i + 1, j, nt), V(i + 1, j + 1, nt), V(i, j + 1, nt))); kinds.append("T")
        for k in range(nt):
            faces.append((V(i, 0, k), V(i + 1, 0, k), V(i + 1, 0, k + 1), V(i, 0, k + 1))); kinds.append("W")
            faces.append((V(i, nw, k), V(i, nw, k + 1), V(i + 1, nw, k + 1), V(i + 1, nw, k))); kinds.append("W")
    for j in range(nw):
        for k in range(nt):
            faces.append((V(0, j, k), V(0, j, k + 1), V(0, j + 1, k + 1), V(0, j + 1, k))); kinds.append("L")
            faces.append((V(nl, j, k), V(nl, j + 1, k), V(nl, j + 1, k + 1), V(nl, j, k + 1))); kinds.append("L")
    rnd = random.Random(seed)
    cracks = [(rnd.uniform(-0.3, 0.3) * Wd, rnd.uniform(0.0, 0.3) * L, rnd.uniform(0.55, 1.0) * L) for _ in range(2)]
    off = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    for (u, v, s) in par:
        l, w, t = u * L, (v - 0.5) * Wd, s * T
        endd = min(l, L - l)
        if u in (0.0, 1.0) and s > 0:                    # 짓눌린 끝: 결 따라 들쭉날쭉
            jag = 0.012 * noise.noise(Vector((w * 60, s * 3, u * 10)) + off)
            l += jag if u == 1.0 else -jag
        if endd < 0.04 and s > 0:                         # 끝 4 cm 는 눌려 얇고 넓다
            k = 1 - endd / 0.04
            t *= 1 - 0.18 * k; w *= 1 + 0.04 * k
        if s > 0:                                         # 바깥 면: 결 방향으로 늘인 얼룩진 높낮이
            t += s * (0.0018 * noise.noise(Vector((l * 4, w * 45, 0)) + off) + 0.0007 * noise.noise(Vector((l * 30, w * 90, 1)) + off))
        if v in (0.0, 1.0):                               # 옆면 비뚤게
            w += (1 if v else -1) * 0.002 * noise.noise(Vector((l * 6, t * 40, 2)) + off)
        if v in (0.0, 1.0) and s == 1.0:                  # 바깥 모서리 무르게 + 군데군데 떨어져 나감
            chip = 0.003 + 0.004 * max(0.0, noise.noise(Vector((l * 9, 3, 3)) + off))
            w -= (1 if v else -1) * chip; t -= chip
        if s == 1.0:                                      # 결 따라 갈라진 틈
            for wc, la, lb in cracks:
                if la < l < lb and abs(w - wc) < Wd / nw * 0.6:
                    taper = math.sin(math.pi * (l - la) / (lb - la))
                    t -= 0.004 * taper
        t += 0.004 * math.sin(math.pi * u)                # 살짝 휨 (바깥으로)
        ang = math.radians(2.0) * (u - 0.5)               # 살짝 비틀림
        w, t = w * math.cos(ang) - t * math.sin(ang) * (1 if s > 0 else 0), t + w * math.sin(ang) * (1 if s > 0 else 0)
        verts.append(P0 + aL * l + aW * w + aT * t)
    cd = CAND[WOOD]
    uvs = {}
    for fi, (f, kd) in enumerate(zip(faces, kinds)):
        for vi in f:
            u, v, s = par[vi]
            if kd == "T":   along, across = u * L / cd["tile"], v
            elif kd == "W": along, across = u * L / cd["tile"], (s * T / Wd if v == 0 else 1 - s * T / Wd)
            else:           along, across = s * T / cd["tile"], v
            c0, c1 = cd["cross"]
            if "cross_m" in cd:
                c1 = c0 + Wd / cd["cross_m"]
            across = c0 + across * (c1 - c0)
            uvs[(fi, vi)] = (across, along) if cd["grain"] == "v" else (along, across)
    set_mesh(o, verts, faces, uvs, o.name + "_detail")
    PLANK_PAR[o.name] = par
    return len(verts)

# ---------------- 못
def rebuild_nail(o, i, plank_name):
    P0, aL, aW, aT, L, Wd, T = PLANK_FRAME[plank_name]
    R = o.matrix_world.to_3x3().normalized()
    a = R.col[2].normalized()
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    c = sum(ws, Vector()) / len(ws)
    if a.dot(aT) < 0:
        a = -a
    rnd = random.Random(100 + i)
    perp = a.orthogonal().normalized()
    perp = Matrix.Rotation(rnd.uniform(0, 2 * math.pi), 3, a) @ perp
    a = (Matrix.Rotation(math.radians(rnd.uniform(-NAIL_JITTER_DEG, NAIL_JITTER_DEG)), 3, perp) @ a).normalized()
    if a.dot(aT) < 0.3:                                   # 판자에 너무 눕지 않게
        a = (a + aT * 0.5).normalized()
    s = (T - (c - P0).dot(aT)) / a.dot(aT)                # 가운데 줄이 판자 바깥 면과 만나는 곳 = 박힌 자리
    E = c + a * s
    vis = rnd.uniform(*NAIL_VIS)
    b1 = a.orthogonal().normalized(); b2 = a.cross(b1).normalized()
    bend = NAIL_BEND.get(i, 0.0)
    unit_frame(o)
    verts, faces = [], []
    n_seg = 7
    def axis_point(x):                                    # x: 박힌 자리에서 바깥으로 m (음수 = 나무 속)
        if x <= 0 or not bend:
            return E + a * x, a
        ang = math.radians(bend) * (x / vis)
        Rb = Matrix.Rotation(ang, 3, b1)
        return E + (Rb @ a) * x, Rb @ a
    rings = []
    for k in range(n_seg + 1):
        p = k / n_seg                                     # 0 끝(뾰족) → 1 머리 밑
        x = -(NAIL_TOTAL - vis) + p * NAIL_TOTAL
        side = NAIL_SHANK * (0.18 + 0.82 * p ** 0.5) * (1 + 0.06 * noise.noise(Vector((i, k, 0.3))))
        pt, ax = axis_point(x)
        u1 = (b1 - ax * b1.dot(ax)).normalized(); u2 = ax.cross(u1)
        ring = []
        for q in range(4):
            ang = math.pi / 4 + q * math.pi / 2
            ring.append(len(verts)); verts.append(pt + (u1 * math.cos(ang) + u2 * math.sin(ang)) * side * 0.707)
        rings.append((ring, pt, ax, u1, u2))
    tip = len(verts); verts.append(E - a * (NAIL_TOTAL - vis + 0.004))
    for q in range(4):
        faces.append((tip, rings[0][0][(q + 1) % 4], rings[0][0][q]))
    for k in range(n_seg):
        r0, r1 = rings[k][0], rings[k + 1][0]
        for q in range(4):
            faces.append((r0[q], r0[(q + 1) % 4], r1[(q + 1) % 4], r1[q]))
    _, pt, ax, u1, u2 = rings[-1]
    hb, ht = [], []                                       # 장미 머리: 넓은 밑판 → 좁은 윗면 → 망치로 두드린 꼭지
    for q in range(4):
        ang = q * math.pi / 2 + rnd.uniform(-0.15, 0.15)
        d = u1 * math.cos(ang) + u2 * math.sin(ang)
        hb.append(len(verts)); verts.append(pt + d * NAIL_HEAD * 0.5 * rnd.uniform(0.9, 1.1) + ax * 0.001)
        ht.append(len(verts)); verts.append(pt + d * NAIL_HEAD * 0.28 + ax * NAIL_HEAD * 0.22 * rnd.uniform(0.85, 1.15))
    apex = len(verts); verts.append(pt + ax * NAIL_HEAD * 0.34 + u1 * rnd.uniform(-0.002, 0.002))
    top = rings[-1][0]
    for q in range(4):
        faces.append((top[q], top[(q + 1) % 4], hb[(q + 1) % 4], hb[q]))
        faces.append((hb[q], hb[(q + 1) % 4], ht[(q + 1) % 4], ht[q]))
        faces.append((ht[q], ht[(q + 1) % 4], apex))
    uvs = {}
    for fi, f in enumerate(faces):
        for n, vi in enumerate(f):
            uvs[(fi, vi)] = ((fi % 4) * 0.25 + n * 0.08, (verts[vi] - E).dot(a) * 4 + 0.5)
    set_mesh(o, verts, faces, uvs, o.name + "_detail")
    NAIL_INFO[i] = dict(E=E, a=a, vis=vis, head=rings[-1][1], tip=verts[tip])
    return len(verts), vis

# ---------------- 재질 (미리보기: 그림 그대로 + 어둡게 + 반들거림 그림)
def pbr(mat, folder, darken, tint=None, uv_scale=1.0):
    mat.use_nodes = True
    N, Lk = mat.node_tree.nodes, mat.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial"); bsdf = N.new("ShaderNodeBsdfPrincipled")
    Lk.new(bsdf.outputs[0], out.inputs[0])
    uvn = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs[3].default_value = (uv_scale, uv_scale, 1)
    Lk.new(uvn.outputs["UV"], mp.inputs[0])
    def img(suffix, colour):
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, folder, "%s_%s.jpg" % (folder, suffix)), check_existing=True)
        t.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        Lk.new(mp.outputs[0], t.inputs[0]); return t
    d = img("Diffuse", True)
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
    Lk.new(d.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (*(tint or (darken, darken, darken)), 1)
    Lk.new(mul.outputs[2], bsdf.inputs["Base Color"])
    r = img("Rough", False); Lk.new(r.outputs[0], bsdf.inputs["Roughness"])
    n = img("nor_gl", False); nm = N.new("ShaderNodeNormalMap"); Lk.new(n.outputs[0], nm.inputs[1]); Lk.new(nm.outputs[0], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0.0

# ---------------- 실행
counts = {}
BUILD = WOOD != "before" and SABOTAGE != "boxes"
for k, name in enumerate(("Plank_Back", "Plank_Forearm_L", "Plank_Shin_R")):
    counts[name] = rebuild_plank(bpy.data.objects[name], seed=k + 1, build=BUILD)
vis = {}
for i in range(5 if BUILD else 0):
    counts["Nail_%d" % i], vis[i] = rebuild_nail(bpy.data.objects["Nail_%d" % i], i, "Plank_Back")
print("verts", counts, "nail visible cm (game)", {i: round(v * SCALE * 100, 1) for i, v in vis.items()})
if BUILD and MODE == "preview":
  pbr(bpy.data.materials["뒤틀린_갱목"], WOOD, DARKEN["wood"])
  pbr(bpy.data.materials["녹슨_주철"], "rusty_metal_02", DARKEN["iron"], tint=tuple(c * DARKEN["iron"] * 2 for c in RUST_TINT), uv_scale=0.5)
  pbr(bpy.data.materials["가죽끈"], "fabric_leather_02", DARKEN["leather"], uv_scale=3.0)

if MODE == "preview":
    os.makedirs(SHOTS, exist_ok=True)
    scene.render.engine = "BLENDER_EEVEE"; scene.render.resolution_x = scene.render.resolution_y = 520
    w = scene.world or bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0.01, 0.01, 0.01, 1)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam); scene.camera = cam
    lamp = bpy.data.objects.new("lamp", bpy.data.lights.new("lamp", "SPOT")); scene.collection.objects.link(lamp)
    lamp.data.energy = 60; lamp.data.spot_size = math.radians(70); lamp.data.shadow_soft_size = 0.02
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN")); scene.collection.objects.link(fill); fill.data.energy = 0.3
    P0, aL, aW, aT, L, Wd, T = PLANK_FRAME["Plank_Back"]
    back_c = P0 + aL * (L * 0.6) + aT * T
    fa = PLANK_FRAME["Plank_Forearm_L"]; fa_c = fa[0] + fa[1] * fa[4] * 0.5 + fa[3] * fa[6]
    views = {"back_close": (back_c, back_c + aT * 0.55 + Vector((0.25, 0, 0.2)), 50),
             "back_far": (back_c + Vector((0, 0, 0.3)), back_c + aT * 1.6 + Vector((0.6, 0, 0.5)), 40),
             "forearm": (fa_c, fa_c + fa[3] * 0.5 + Vector((0, -0.25, 0.15)), 50)}
    for vn, (look, pos, lens) in views.items():
        cam.location = pos; cam.data.lens = lens
        cam.rotation_euler = (look - pos).to_track_quat("-Z", "Y").to_euler()
        lamp.location = pos + Vector((0, 0, 0.05)); lamp.rotation_euler = cam.rotation_euler
        scene.render.filepath = os.path.join(SHOTS, "%s_%s.png" % (os.environ.get("TAG", WOOD), vn))
        bpy.ops.render.render(write_still=True)
        print("shot", scene.render.filepath)
    sys.exit(0)

# ======================= M2 굽기 =======================
def mode(m):
    if bpy.context.object and bpy.context.object.mode != m:
        bpy.ops.object.mode_set(mode=m)

def activate(o):
    mode("OBJECT")
    for x in bpy.context.view_layer.objects:
        x.select_set(x == o)
    bpy.context.view_layer.objects.active = o

def save_img(name, arr, colour):
    """arr (h, w, 4) 0~1 → stage15_tex/name.png, 불러온 그림 돌려줌"""
    os.makedirs(TEX_OUT, exist_ok=True)
    h, w = arr.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    im.pixels.foreach_set(arr.astype(np.float32).ravel())
    im.filepath_raw = os.path.join(TEX_OUT, name + ".png"); im.file_format = "PNG"; im.save()
    return im

def load_arr(folder, suffix, px):
    im = bpy.data.images.load(os.path.join(TEX, folder, "%s_%s.jpg" % (folder, suffix)))
    im.scale(px, px)
    a = np.empty(px * px * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    return a.reshape(px, px, 4)

def final_material(mat, alb, rough, nor, uv_scale=1.0):
    """glTF 로 그대로 나가는 모양: 그림 3장 → Principled (중간 계산 노드 없음, 배율은 Mapping → KHR_texture_transform)"""
    mat.use_nodes = True
    N, Lk = mat.node_tree.nodes, mat.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial"); b = N.new("ShaderNodeBsdfPrincipled"); Lk.new(b.outputs[0], out.inputs[0])
    b.inputs["Metallic"].default_value = 0.0
    mp = None
    if uv_scale != 1.0:
        tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs[3].default_value = (uv_scale, uv_scale, 1)
        Lk.new(tc.outputs["UV"], mp.inputs[0])
    for im, sock in ((alb, "Base Color"), (rough, "Roughness"), (nor, None)):
        t = N.new("ShaderNodeTexImage"); t.image = im
        if mp: Lk.new(mp.outputs[0], t.inputs[0])
        if sock:
            Lk.new(t.outputs[0], b.inputs[sock])
        else:
            nm = N.new("ShaderNodeNormalMap"); Lk.new(t.outputs[0], nm.inputs[1]); Lk.new(nm.outputs[0], b.inputs["Normal"])

def bake_plank(o, tag):
    px = BAKE_PX[o.name]
    me = o.data
    me.uv_layers["UVMap"].name = "Tile"
    bake_uv = me.uv_layers.new(name="UVMap")
    me.uv_layers.active = bake_uv
    activate(o); mode("EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
    mode("OBJECT")
    # 못 둘레 검은 물: 박힌 자리에서 3.5 cm 까지 번짐 (점 색으로)
    ca = me.color_attributes.new("nailstain", "FLOAT_COLOR", "POINT")
    mw = o.matrix_world
    for v in me.vertices:
        w = mw @ v.co
        d = min(((w - n["E"]).length for n in NAIL_INFO.values()), default=9.0) if o.name == "Plank_Back" else 9.0
        k = max(0.0, 1 - d / (0.035 / SCALE * 1.5)) ** 1.5
        ca.data[v.index].color = (k, k, k, 1)
    mat = bpy.data.materials.new("뒤틀린_갱목_" + tag); me.materials.clear(); me.materials.append(mat)
    mat.use_nodes = True
    N, Lk = mat.node_tree.nodes, mat.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    uvt = N.new("ShaderNodeUVMap"); uvt.uv_map = "Tile"
    def tex(sfx, colour):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(TEX, WOOD, "%s_%s.jpg" % (WOOD, sfx)), check_existing=True)
        t.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"; Lk.new(uvt.outputs[0], t.inputs[0]); return t
    dif, rgh, nrm = tex("Diffuse", True), tex("Rough", False), tex("nor_gl", False)
    def mix(a, b, fac, blend="MIX"):
        m = N.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = blend
        for sock, val in ((0, fac), (6, a), (7, b)):
            if isinstance(val, (int, float)): m.inputs[sock].default_value = val
            elif isinstance(val, tuple): m.inputs[sock].default_value = (*val, 1) if len(val) == 3 else val
            else: Lk.new(val, m.inputs[sock])
        return m.outputs[2]
    def ramp(src, a, b, top=1.0):
        r = N.new("ShaderNodeMapRange"); r.inputs[1].default_value = a; r.inputs[2].default_value = b; r.inputs[4].default_value = top; r.clamp = True
        Lk.new(src, r.inputs[0]); return r.outputs[0]
    def noise(scale, detail=4.0):
        tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = detail
        Lk.new(tc.outputs["Object"], nz.inputs["Vector"]); return nz.outputs["Fac"]
    ao = N.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.05; ao.samples = 16
    col = mix(dif.outputs[0], (0.15, 0.13, 0.11), 1.0, "MULTIPLY")                          # 어둡게 — 0.55·0.36 은 헤드램프 아래 살(평균 0.25)만큼 밝은 베이지로 떴다(09-19 실행 파일). 살보다 어둡게 — 목표: 색 그림 평균(sRGB) ≤ 0.16 (살 0.25)
    rot = ramp(noise(9.0, 6.0), 0.42, 0.62, 0.9)                                            # 갈색 썩음 얼룩 (최대 90 %)
    col = mix(col, (0.020, 0.012, 0.006), rot, "MIX")                                      # 선형 값 — 0.10 은 그림에서 0.35 로 나무보다 밝았다
    stain = N.new("ShaderNodeVertexColor"); stain.layer_name = "nailstain"
    col = mix(col, (0.028, 0.034, 0.042), stain.outputs[0], "MIX")                          # 못 둘레 검푸른 물 (철 + 타닌)
    dust = ramp(noise(140.0, 2.0), 0.4, 0.75, 0.45)                                         # 석탄 먼지 점 (최대 45 %)
    col = mix(col, (0.02, 0.02, 0.02), dust, "MIX")
    # AO: 틈·끝·몸에 닿는 쪽 어둡게 = 색 × (0.3 + 0.7 AO)
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY_ADD"; mul.inputs[1].default_value = 0.7; mul.inputs[2].default_value = 0.3
    Lk.new(ao.outputs["AO"], mul.inputs[0])
    m2 = N.new("ShaderNodeMix"); m2.data_type = "RGBA"; m2.blend_type = "MULTIPLY"; m2.inputs[0].default_value = 1.0
    Lk.new(col, m2.inputs[6]); cm = N.new("ShaderNodeCombineColor"); Lk.new(mul.outputs[0], cm.inputs[0]); Lk.new(mul.outputs[0], cm.inputs[1]); Lk.new(mul.outputs[0], cm.inputs[2])
    Lk.new(cm.outputs[0], m2.inputs[7])
    color_out = m2.outputs[2]
    # 반들거림(거칠기): 썩은 나무는 거칠다 — 0.72 + 0.28 × 그림, 젖은 곳만 최대 25 % 덜 거칠게 (그림 그대로 쓰면 0.3 안팎이라 헤드램프에 번들거렸다, 09-19)
    wet = ramp(noise(3.0, 2.0), 0.5, 0.7)
    base_r = N.new("ShaderNodeMath"); base_r.operation = "MULTIPLY_ADD"; base_r.inputs[1].default_value = 0.28; base_r.inputs[2].default_value = 0.72
    Lk.new(rgh.outputs[0], base_r.inputs[0])
    wetk = N.new("ShaderNodeMath"); wetk.operation = "MULTIPLY_ADD"; wetk.inputs[1].default_value = -0.25; wetk.inputs[2].default_value = 1.0
    Lk.new(wet, wetk.inputs[0])
    rclamp = N.new("ShaderNodeMath"); rclamp.operation = "MULTIPLY"; Lk.new(base_r.outputs[0], rclamp.inputs[0]); Lk.new(wetk.outputs[0], rclamp.inputs[1])
    emi = N.new("ShaderNodeEmission"); Lk.new(emi.outputs[0], out.inputs[0])
    bsdf = N.new("ShaderNodeBsdfPrincipled"); nmap = N.new("ShaderNodeNormalMap"); nmap.uv_map = "Tile"
    Lk.new(nrm.outputs[0], nmap.inputs[1]); Lk.new(nmap.outputs[0], bsdf.inputs["Normal"])
    target = N.new("ShaderNodeTexImage")
    scene.render.engine = "CYCLES"; scene.cycles.samples = 16; scene.cycles.device = "CPU"
    scene.render.bake.margin = 6; scene.render.bake.use_clear = True
    imgs = {}
    for kind in ("albedo", "rough", "normal"):
        im = bpy.data.images.new("timber_%s_%s" % (tag, kind), px, px, alpha=False)
        im.colorspace_settings.name = "sRGB" if kind == "albedo" else "Non-Color"
        target.image = im; N.active = target; target.select = True
        for l in list(out.inputs[0].links): Lk.remove(l)
        if kind == "albedo":
            Lk.new(color_out, emi.inputs[0]); Lk.new(emi.outputs[0], out.inputs[0]); bpy.ops.object.bake(type="EMIT")
        elif kind == "rough":
            Lk.new(rclamp.outputs[0], emi.inputs[0]); Lk.new(emi.outputs[0], out.inputs[0]); bpy.ops.object.bake(type="EMIT")
        else:
            Lk.new(bsdf.outputs[0], out.inputs[0]); bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
        a = np.empty(px * px * 4, np.float32); im.pixels.foreach_get(a)
        imgs[kind] = save_img(im.name, a.reshape(px, px, 4), kind == "albedo")
        bpy.data.images.remove(im)
    final_material(mat, imgs["albedo"], imgs["rough"], imgs["normal"])
    me.uv_layers.remove(me.uv_layers["Tile"])
    me.color_attributes.remove(me.color_attributes["nailstain"])
    return imgs

def small_set(folder, name, px, tint):
    """못·가죽끈: CC0 그림을 물들이고 줄여서 3장 (중간 노드 없이 glTF 로)"""
    d = load_arr(folder, "Diffuse", px); d[..., :3] *= np.array(tint, np.float32)
    r = load_arr(folder, "Rough", px); n = load_arr(folder, "nor_gl", px)
    return save_img(name + "_albedo", d, True), save_img(name + "_rough", r, False), save_img(name + "_normal", n, False)

fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

def head_vs_props():
    """trim_back_plank.py 와 같은 15 자세 — 두꺼워진 판자·새 못이 머리와 안 겹치는지"""
    Mi = M.inverted()
    head = bpy.data.objects["Miner_Head"]; hg = head.vertex_groups["mixamorig:Head"].index
    hidx = np.array([v.index for v in head.data.vertices if any(g.group == hg and g.weight > 0.5 for g in v.groups)])
    def eval_co(o):
        ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
        nv = len(me.vertices); co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
        return (np.array(o.matrix_world) @ np.c_[co.reshape(-1, 3), np.ones(nv)].T).T[:, :3]
    def hull_inside(o, pts):
        """물체 상자(자기 좌표) 안 — 새 판자는 거의 상자 모양이라 상자로 잰다, 못은 머리 크기 상자"""
        L = np.array(o.matrix_world.inverted()) @ np.c_[pts, np.ones(len(pts))].T
        lo, hi = np.array([min(c[k] for c in o.bound_box) for k in range(3)]), np.array([max(c[k] for c in o.bound_box) for k in range(3)])
        return int(np.all((L[:3].T >= lo) & (L[:3].T <= hi), axis=1).sum())
    def rot(n, R):
        pb = arm.pose.bones["mixamorig:" + n]; W = M @ pb.matrix; h = W.translation
        pb.matrix = Mi @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W); bpy.context.view_layer.update()
    props = [bpy.data.objects["Plank_Back"]] + [bpy.data.objects["Nail_%d" % i] for i in range(5)]
    bad = []
    for yaw in (90, 135, 180, -90, -135):
        for tilt in (0, 110, -110):
            for p_ in arm.pose.bones:
                p_.rotation_quaternion = (1, 0, 0, 0)
            bpy.context.view_layer.update()
            for b, k in (("Neck", 0.4), ("Head", 0.6)):
                fwd = Matrix.Rotation(math.radians(yaw * k), 3, "Z") @ Vector((0, -1, 0))
                rot(b, Matrix.Rotation(math.radians(tilt * k), 4, fwd) @ Matrix.Rotation(math.radians(yaw * k), 4, "Z"))
            pts = eval_co(head)[hidx]
            n = sum(hull_inside(o, pts) for o in props)
            if n: bad.append((n, yaw, tilt))
    for p_ in arm.pose.bones:
        p_.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    return bad

if MODE == "build":
    mode("OBJECT")
    if BUILD:
        for name, tag in (("Plank_Back", "back"), ("Plank_Forearm_L", "forearm"), ("Plank_Shin_R", "shin")):
            bake_plank(bpy.data.objects[name], tag)
        iron = small_set("rusty_metal_02", "iron_nail", 512, tuple(c * DARKEN["iron"] * 2 for c in RUST_TINT))
        final_material(bpy.data.materials["녹슨_주철"], *iron, uv_scale=0.5)
        leather = small_set("fabric_leather_02", "leather", 512, (DARKEN["leather"],) * 3)
        final_material(bpy.data.materials["가죽끈"], *leather, uv_scale=3.0)
    # ---- 자기 검사 (제안서 Step 4)
    for name in ("Plank_Back", "Plank_Forearm_L", "Plank_Shin_R"):
        o = bpy.data.objects[name]
        P0, aL, aW, aT, L, Wd, T = PLANK_FRAME[name]
        ws = np.array([o.matrix_world @ v.co for v in o.data.vertices])
        rel = ws - np.array(P0)
        tl, tw, tt = rel @ np.array(aL), rel @ np.array(aW), rel @ np.array(aT)
        par = PLANK_PAR.get(name)
        if par:
            s_ = np.array([q[2] for q in par]); body, outer = s_ == 0, s_ == 1
            thick = float(np.median(tt[outer]) - np.median(tt[body]))
            wid = float(tw[body].max() - tw[body].min()); ln = float(tl[body].max() - tl[body].min())
            bodyoff = float(np.abs(tt[body]).max())
        else:
            thick, wid, ln, bodyoff = float(tt.max() - tt.min()), float(tw.max() - tw.min()), float(tl.max() - tl.min()), 0.0
        ok = abs(thick - T) <= 0.1 * T and abs(wid - Wd) <= 0.1 * Wd and abs(ln - L) <= 0.1 * L and bodyoff <= 0.005
        check(ok, "%s 크기 게임 두께 %.1f cm (목표 %.1f) · 너비 %.1f (%.1f) · 길이 %.1f (%.1f) ±10 %% · 몸 쪽 면 벗어남 %.1f mm (≤ 5)"
              % (name, thick * SCALE * 100, T * SCALE * 100, wid * SCALE * 100, Wd * SCALE * 100, ln * SCALE * 100, L * SCALE * 100, bodyoff * 1000))
    for i in range(5):
        n = NAIL_INFO.get(i)
        if not n:
            check(False, "Nail_%d 새 못 없음" % i); continue
        P0, aL, aW, aT, L, Wd, T = PLANK_FRAME["Plank_Back"]
        o = bpy.data.objects["Nail_%d" % i]
        vis = (n["head"] - n["E"]).length
        tip_t = (n["tip"] - P0).dot(aT)
        side = max((o.matrix_world @ o.data.vertices[a_].co - o.matrix_world @ o.data.vertices[b_].co).length for a_, b_ in ((28, 29), (29, 30), (30, 31), (31, 28))) if len(o.data.vertices) > 31 else 9
        check(abs(side * SCALE - 0.016) <= 0.2 * 0.016 and 0.04 <= vis * SCALE <= 0.09 and tip_t < T - 0.005,
              "Nail_%d 몸통 굵기(머리 밑) 게임 %.2f cm (1.6 ± 20 %%) · 밖에 보이는 %.1f cm (4~9) · 끝이 나무 속 (판자 바깥 면보다 %.1f cm 안)" % (i, side * SCALE * 100, vis * SCALE * 100, (T - tip_t) * SCALE * 100))
    for name in ("Plank_Back", "Plank_Forearm_L", "Plank_Shin_R") + tuple("Nail_%d" % i for i in range(5)):
        nv = len(bpy.data.objects[name].data.vertices)
        check(8 < nv <= 2000, "%s 꼭짓점 %d (8 초과 · 2000 이하)" % (name, nv))
    for tag in ("back", "forearm", "shin"):                # 색 그림 밝기: 살(평균 0.25)보다 어둡게 — 짙은 갈색 썩음 [요약 미국 산림연구소]
        fp = os.path.join(TEX_OUT, "timber_%s_albedo.png" % tag)
        if BUILD and os.path.exists(fp):
            im = bpy.data.images.load(fp); a_ = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a_); bpy.data.images.remove(im)
            a_ = a_.reshape(-1, 4)[:, :3]; mk = a_.sum(1) > 0.02
            mean = float(a_[mk].mean())
        else:
            mean = 9.0
        check(mean <= 0.16, "timber_%s 색 그림 평균 밝기 %.3f (≤ 0.16, 살 0.25)" % (tag, mean))
    bad = head_vs_props()
    check(not bad, "머리가 판자·못과 안 겹침 (15 자세 중 겹침 %d %s)" % (len(bad), bad[:4]))
    def mat_ok(m):
        if not m.use_nodes: return False
        b = next((x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED"), None)
        if not b: return False
        def img_into(sock):
            for l in b.inputs[sock].links:
                nd = l.from_node
                if nd.type == "NORMAL_MAP": nd = nd.inputs[1].links[0].from_node if nd.inputs[1].links else None
                if nd is not None and nd.type == "TEX_IMAGE" and nd.image: return True
            return False
        return img_into("Base Color") and img_into("Roughness") and img_into("Normal")
    mats = sorted({ms.material.name for o in bpy.data.objects if o.name.startswith(("Plank", "Nail", "Strap")) for ms in o.material_slots if ms.material})
    bad_m = [m for m in mats if not mat_ok(bpy.data.materials[m])]
    check(not bad_m and len(mats) >= 5, "갱목·못·가죽끈 재질 %d 개에 색·반들거림·요철 그림 %s" % (len(mats), bad_m))
    if SABOTAGE or fails:
        print("timber_detail %s fails=%d (저장 안 함)" % ("SABOTAGE=" + SABOTAGE if SABOTAGE else "FAIL", len(fails)))
        sys.exit(2 if fails else 0)
    for tr in ad.nla_tracks:
        tr.mute = False
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("saved", OUT)
    print("timber_detail ALL PASS")
