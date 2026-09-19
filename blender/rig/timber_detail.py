"""timber_detail — 괴물 몸의 갱목(판자 3)·못 5·가죽끈 9 를 사실적으로 (제안서 docs/제안서_3D3b_갱목_못_사실감.md, 승인 2026-09-19).
  MODE=preview WOOD=rough_wood "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/timber_detail.py
입력: Documents/MineTunnel/blender/miner_v4_stage14_plank.blend — 안 고친다
MODE=preview (M1): 모양을 새로 만들고 WOOD 후보 재질을 입혀 가까이 찍기만 한다 (저장 없음) → 사용자가 나무를 고른다
레퍼런스(제안서 Step 1): 쪼갠 널은 면이 비뚤고 끝이 짓눌리며 결 따라 갈라진다 · 손으로 두드린 못은 네 면이 끝으로 가늘어지는 네모 몸통 + 장미 머리 ·
철도 대못 몸통 1.6 cm · 전체 15 cm · 머리 3.5 cm (게임 크기, 모델은 ÷ 1.5)"""
import bpy, bmesh, os, sys, math, random
import numpy as np
from mathutils import Vector, Matrix, noise

MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.path.join(MT, "blender", "miner_v4_stage14_plank.blend")
TEX = os.path.join(MT, "textures")
MODE = os.environ.get("MODE", "preview")
WOOD = os.environ.get("WOOD", "rough_wood")
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
PLANK_FRAME = {}
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
BUILD = WOOD != "before"
for k, name in enumerate(("Plank_Back", "Plank_Forearm_L", "Plank_Shin_R")):
    counts[name] = rebuild_plank(bpy.data.objects[name], seed=k + 1, build=BUILD)
vis = {}
for i in range(5 if BUILD else 0):
    counts["Nail_%d" % i], vis[i] = rebuild_nail(bpy.data.objects["Nail_%d" % i], i, "Plank_Back")
print("verts", counts, "nail visible cm (game)", {i: round(v * SCALE * 100, 1) for i, v in vis.items()})
if BUILD:
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
        scene.render.filepath = os.path.join(SHOTS, "%s_%s.png" % (WOOD, vn))
        bpy.ops.render.render(write_still=True)
        print("shot", scene.render.filepath)
    sys.exit(0)
