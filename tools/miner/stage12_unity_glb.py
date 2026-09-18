"""stage12 — Unity용 괴물 GLB (제안서 3D-①, 2026-09-17).
  blender -b --factory-startup -P blender/stage12_unity_glb.py
입력: blender/miner_v2_stage6.blend (리그 + 동작 14개 + 갱목 재질, Godot 최종본 — 안 건드린다)
      blender/miner_v3_stage11.blend 의 Miner_Body_HI (고폴리 몸 + 머리, 게임 몸과 같은 좌표)
하는 일: ① 살·머리 색 그림 webp -> PNG (픽셀 그대로)  ② 고폴리 -> 게임 몸 탄젠트 노멀 베이크 2048²
        ③ 살·머리를 새 Principled 재질로(거칠기 1 · 금속 0 · 노멀 연결)  ④ GLB 내보내기 -> Tunnel/unity/Assets/Tunnel/Monster/
        ⑤ 자기 검사 PASS/FAIL  ⑥ Eevee 미리보기 2장 (노멀 있음/없음)
출력: blender/stage12_tex/*.png, blender/stage12_render/*.png, blender/miner_v4_stage12.blend, Unity GLB
사보타주: SKIP_NORMAL=1 -> 노멀을 안 굽는다 (검사 ②·⑤ 가 FAIL 나야 한다)"""
import bpy, os, sys, json, struct, math
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_BLEND = os.path.join(ROOT, "blender", "miner_v2_stage6.blend")
HI_BLEND = os.path.join(ROOT, "blender", "miner_v3_stage11.blend")
SKIP_NORMAL = os.environ.get("SKIP_NORMAL", "0") == "1"
SFX = "_sabotage" if SKIP_NORMAL else ""          # 사보타주 실행은 본 산출물을 덮어쓰지 않는다
OUT_BLEND = os.path.join(ROOT, "blender", "miner_v4_stage12%s.blend" % SFX)
TEX = os.path.join(ROOT, "blender", "stage12_tex" + SFX); os.makedirs(TEX, exist_ok=True)
RENDER = os.path.join(ROOT, "blender", "stage12_render" + SFX); os.makedirs(RENDER, exist_ok=True)
OUT_GLB = os.environ.get("OUT_GLB", os.path.join(ROOT, "mesh", "miner_rigged_unity_sabotage.glb") if SKIP_NORMAL
          else r"C:\Users\anjyo\Tunnel\unity\Assets\Tunnel\Monster\miner_rigged.glb")
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)

BAKE_PX = 2048
CAGE_M, RAY_M = 0.02, 0.06        # stage7 값
BBOX_TOL = 0.01                   # m, 고폴리·게임 몸 경계 상자 허용 오차
SKIN_MATS = ("살", "살_머리")
fails = []

def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

def world_bbox(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])

def px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

def new_png(name, arr, colorspace):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.filepath_raw = os.path.join(TEX, name + ".png"); img.file_format = "PNG"
    img.save()
    img.pack()   # GLB 에 묻히도록
    return img

# ---------------------------------------------------------------- 1. 열기, 자세를 REST 로
bpy.ops.wm.open_mainfile(filepath=SRC_BLEND)
scene = bpy.context.scene
body = bpy.data.objects["Miner_Body"]; arm = bpy.data.objects["Miner_Rig"]
arm.data.pose_position = "REST"
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 2. 고폴리 가져와 자리 대조
with bpy.data.libraries.load(HI_BLEND, link=False) as (src, dst):
    dst.objects = ["Miner_Body_HI"]
hi = dst.objects[0]; scene.collection.objects.link(hi)
bl, bh = world_bbox(body); hl, hh = world_bbox(hi)
err = max(max(abs(bl[i] - hl[i]), abs(bh[i] - hh[i])) for i in range(3))
print("bbox body %s %s  hi %s %s  err %.4f m" % (tuple(round(v, 3) for v in bl), tuple(round(v, 3) for v in bh),
                                                 tuple(round(v, 3) for v in hl), tuple(round(v, 3) for v in hh), err))
check(err <= BBOX_TOL, "고폴리·게임 몸 경계 상자 오차 %.4f ≤ %.2f m" % (err, BBOX_TOL))
if fails:
    print("STOP: 고폴리 자리가 안 맞는다 — 억지로 맞추지 않는다"); sys.exit(1)
print("faces body %d  hi %d" % (len(body.data.polygons), len(hi.data.polygons)))

# ---------------------------------------------------------------- 3. 색 그림 webp -> PNG, 새 재질
def base_image(mat):
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            for l in n.outputs["Color"].links:
                if l.to_socket.name == "Base Color":
                    return n.image
    raise RuntimeError("base colour image not found in " + mat.name)

new_mats, targets, src_px = {}, {}, {}
for nm in SKIN_MATS:
    old = bpy.data.materials[nm]
    src = base_image(old)
    arr = px(src); src_px[nm] = arr
    print("%s: base image %s %s %dx%d" % (nm, src.name, src.file_format, src.size[0], src.size[1]))
    png = new_png("skin_%s_albedo" % ("body" if nm == "살" else "head"), arr, "sRGB")
    old.name = nm + "_godot"
    m = bpy.data.materials.new(nm); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 1.0; bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = png; t.name = "albedo"
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    tgt = bpy.data.images.new("bake_" + nm, BAKE_PX, BAKE_PX, alpha=False)
    tgt.colorspace_settings.name = "Non-Color"
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = tgt; tn.name = "normal"; nt.nodes.active = tn
    new_mats[nm], targets[nm] = m, tgt
for s in body.material_slots:
    if s.material.name.endswith("_godot"):
        s.material = new_mats[s.material.name[:-6]]
print("body slots", [s.material.name for s in body.material_slots])

# ---------------------------------------------------------------- 4. 노멀 베이크 (고폴리 -> 게임 몸)
# ---------------------------------------------------------------- 3b. 사타구니 표현 없애기 (사용자 09-18). 자리는 쉬는 자세 정면·옆 정사영 렌더에서 잰 것
GROIN = dict(xmax=0.055, zlo=1.035, zhi=1.155, ymax=-0.035)   # m: 좌우 · 높이 · 앞면(y < ymax)
def blur(a, r):
    """상자 흐림 r 텍셀 (누적합)"""
    if r <= 0:
        return a
    pad = np.pad(a, r, mode="wrap")
    c = np.cumsum(np.cumsum(pad, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)

GROIN_RING = {}
GROIN_KEEP = 0.08   # 튀어나온 깊이를 이만큼만 남긴다 (8 cm -> 6 mm)
def flatten_groin(o):
    """그 부위에서 앞으로 튀어나온 정점만, 주변 앞면에 맞춘 곡면(2차식 y = f(x, z))까지 뒤로 민다. 곡면보다 안쪽인 정점은 안 건드린다
    (09-18 첫 시도: 이웃 평균으로 펴니 안쪽 껍질까지 끌려가 구멍처럼 꺼졌다). 상자 가장자리 2 cm 는 서서히. 정점색 'groin' 에 자리를 남긴다"""
    me = o.data; M = np.array(o.matrix_world); Mi = np.linalg.inv(M)
    n = len(me.vertices)
    co = np.empty(n * 3, np.float64); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
    w = co @ M[:3, :3].T + M[:3, 3]
    nrm = np.empty(n * 3, np.float64); me.vertices.foreach_get("normal", nrm); nrm = nrm.reshape(n, 3) @ M[:3, :3].T
    x, y, z = w[:, 0], w[:, 1], w[:, 2]
    box = (np.abs(x) < GROIN["xmax"]) & (z > GROIN["zlo"]) & (z < GROIN["zhi"]) & (y < GROIN["ymax"])
    ring = (~box) & (np.abs(x) < GROIN["xmax"] + 0.05) & (z > GROIN["zlo"] - 0.04) & (z < GROIN["zhi"] + 0.04) & (y < -0.01) & (nrm[:, 1] < -0.3)
    A = lambda xx, zz: np.stack([np.ones_like(xx), xx, zz, xx * xx, zz * zz, xx * zz], 1)
    coef, *_ = np.linalg.lstsq(A(x[ring], z[ring]), y[ring], rcond=None)
    fit = A(x, z) @ coef
    edge = np.minimum.reduce([GROIN["xmax"] - np.abs(x), z - GROIN["zlo"], GROIN["zhi"] - z]) / 0.02
    wgt = np.clip(edge, 0, 1); wgt = wgt * wgt * (3 - 2 * wgt)
    push = box & (y < fit)                                   # 곡면보다 앞으로 나온 것만
    # 곡면에 딱 붙이면 겉살과 속껍질(이 몸은 안쪽에 밝은 겹이 하나 더 있다)이 한 자리에 겹쳐 얼룩덜룩 비친다(09-18) → 나온 깊이를 8 % 로 줄여 겹 순서를 지킨다
    dy = np.where(push, (fit - y) * (1.0 - GROIN_KEEP) * wgt, 0.0)
    w2 = w.copy(); w2[:, 1] += dy
    co2 = (w2 - M[:3, 3]) @ Mi[:3, :3].T
    me.vertices.foreach_set("co", co2.ravel()); me.update()
    attr = me.color_attributes.get("groin") or me.color_attributes.new("groin", "FLOAT_COLOR", "POINT")
    col = np.zeros((n, 4), np.float32); col[:, 3] = 1.0; col[box, :3] = 1.0
    attr.data.foreach_set("color", col.ravel())
    print("groin %s: box verts %d  ring %d  pushed %d  max %.4f m  mean %.4f m" % (o.name, int(box.sum()), int(ring.sum()), int((dy > 0.001).sum()), dy.max(), dy[dy > 0.001].mean() if (dy > 0.001).any() else 0))
    GROIN_RING[o.name] = np.where(ring)[0]
    return int((dy > 0.001).sum()), float(dy.max())

gb, gmax = flatten_groin(body)
gh, _ = flatten_groin(hi)
check(gb >= 50 and gmax > 0.005, "사타구니 자리 정점을 찾아 폈다 (몸 %d개, 최대 이동 %.3f m)" % (gb, gmax))

# 색 그림에서 그 자리 가리개를 굽는다 (재질마다 UV 가 따로라 재질별로)
scene.render.engine = "CYCLES"; scene.cycles.samples = 1; scene.cycles.device = "CPU"
b = scene.render.bake; b.use_selected_to_active = False; b.margin = 4; b.use_clear = True
groin_masks, real_mats, tmp = {}, [sl.material for sl in body.material_slots], []
for sl in body.material_slots:
    em = bpy.data.materials.new("groin_emit_" + sl.material.name); em.use_nodes = True
    ent = em.node_tree; ent.nodes.clear()
    eo = ent.nodes.new("ShaderNodeOutputMaterial"); ee = ent.nodes.new("ShaderNodeEmission"); ea = ent.nodes.new("ShaderNodeAttribute"); ea.attribute_name = "groin"
    ent.links.new(ea.outputs["Color"], ee.inputs["Color"]); ent.links.new(ee.outputs["Emission"], eo.inputs["Surface"])
    img = bpy.data.images.new("bake_groin_" + sl.material.name, BAKE_PX, BAKE_PX, alpha=False); img.colorspace_settings.name = "Non-Color"
    tn = ent.nodes.new("ShaderNodeTexImage"); tn.image = img; ent.nodes.active = tn
    tmp.append((sl.material.name, em, img)); sl.material = em
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type="EMIT")
for sl, real in zip(body.material_slots, real_mats):
    sl.material = real
orig_px = {}
for nm, em, img in tmp:
    mask = px(img)[..., 0].copy()
    bpy.data.images.remove(img); bpy.data.materials.remove(em)
    orig_px[nm] = src_px[nm].copy()
    groin_masks[nm] = mask
    frac = float((mask > 0.5).mean() * 100)
    if frac == 0.0:
        print("groin mask %s: none" % nm); continue
    alb = src_px[nm][..., :3]
    soft = np.clip(blur(np.clip(blur((mask > 0.5).astype(np.float64), 10) * 3.0, 0, 1), 6), 0, 1)      # 가장자리를 넉넉히 덮고 부드럽게
    lum = 0.2126 * alb[..., 0] + 0.7152 * alb[..., 1] + 0.0722 * alb[..., 2]
    # 색은 몸 위에서 둘러싼 정점(3D 고리)의 UV 자리에서 뽑는다 — 이 몸의 UV 는 조각조각이라 그림 위 이웃은 몸 위 이웃이 아니다
    # (09-18: 그림 위 고리 중앙값·번지기 둘 다 엉뚱한 밝은 부위 색을 끌어와 밝은 얼룩이 됐다)
    me = body.data; H, W = alb.shape[:2]
    slot = [i for i, sl in enumerate(body.material_slots) if sl.material.name == nm][0]
    nl = len(me.loops); lv = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", lv)
    uv = np.empty(nl * 2, np.float64); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(nl, 2)
    npoly = len(me.polygons); pm = np.empty(npoly, np.int64); me.polygons.foreach_get("material_index", pm)
    ls = np.empty(npoly, np.int64); me.polygons.foreach_get("loop_start", ls); lt = np.empty(npoly, np.int64); me.polygons.foreach_get("loop_total", lt)
    loop_mat = np.repeat(pm, lt)
    in_ring = np.isin(lv, GROIN_RING[body.name]) & (loop_mat == slot)
    px_y = np.clip((uv[in_ring, 1] * H).astype(int), 0, H - 1); px_x = np.clip((uv[in_ring, 0] * W).astype(int), 0, W - 1)
    samples = alb[px_y, px_x]
    samples = samples[(0.2126 * samples[:, 0] + 0.7152 * samples[:, 1] + 0.0722 * samples[:, 2]) > 0.03]
    med = np.median(samples, axis=0)
    grain = (blur(np.random.default_rng(7).random(alb.shape[:2]), 2) - 0.5) * 0.06             # 밋밋한 판이 안 되게 잔 얼룩 ±3 %
    new = np.clip(med[None, None, :] * (1.0 + grain[..., None]), 0, 1)
    print("groin colour: %d ring samples, median %s" % (len(samples), med.round(3)))
    src_px[nm][..., :3] = alb * (1 - soft[..., None]) + new * soft[..., None]
    groin_masks[nm] = soft
    tag = "body" if nm == "살" else "head"
    nt = new_mats[nm].node_tree; an = nt.nodes["albedo"]; old_img = an.image
    an.image = new_png("skin_%s_albedo" % tag, src_px[nm], "sRGB"); bpy.data.images.remove(old_img)
    print("groin mask %s: %.3f%% of texture, filled colour mean %s -> albedo repainted" % (nm, frac, med.round(3)))
check(any((m > 0.5).any() for m in groin_masks.values()), "사타구니 자리의 색 그림을 주변 살 색으로 덮었다")

hi_mat = bpy.data.materials.new("hi_plain"); hi_mat.use_nodes = True   # glTF 재질 그대로면 selected->active 가 0 픽셀 (5.2 함정)
hi.data.materials.clear(); hi.data.materials.append(hi_mat)
if not SKIP_NORMAL:
    scene.render.engine = "CYCLES"; scene.cycles.samples = 4; scene.cycles.device = "CPU"
    b = scene.render.bake
    b.use_selected_to_active = True; b.use_cage = False; b.cage_extrusion = CAGE_M; b.max_ray_distance = RAY_M
    b.margin = 24; b.use_clear = True; b.normal_space = "TANGENT"
    bpy.ops.object.select_all(action="DESELECT"); hi.select_set(True); body.select_set(True)
    bpy.context.view_layer.objects.active = body
    body.data.uv_layers.active = body.data.uv_layers[0]
    bpy.ops.object.bake(type="NORMAL")
    print("baked NORMAL", BAKE_PX)
def blur(a, r):
    """상자 흐림 r 텍셀 (누적합)"""
    if r <= 0:
        return a
    pad = np.pad(a, r, mode="wrap")
    c = np.cumsum(np.cumsum(pad, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)

def normal_from_height(hgt, strength):
    """높이 그림 -> 탄젠트 노멀 (OpenGL +Y), -1~1"""
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5
    n = np.dstack((-dx * strength, -dy * strength, np.ones_like(hgt)))
    return n / np.linalg.norm(n, axis=2, keepdims=True)

def island_dev(n01, isl):
    return float(np.abs(n01[isl][:, :2] - 0.5).mean()) if isl.any() else 0.0

def fit_strength(hgt, isl, target):
    """섬 안 기울기 평균이 target 이 되는 세기 (기울기는 세기에 거의 비례 — 세 번 맞춘다)"""
    s = 1.0
    for _ in range(3):
        d = island_dev(normal_from_height(hgt, s) * 0.5 + 0.5, isl)
        s *= target / max(d, 1e-6)
    return s

RELIEF_TARGET = float(os.environ.get("RELIEF_TARGET", "0.12"))   # 색→요철 섬 안 기울기 평균 (3D-②b 제안값)
GRAIN_TARGET = float(os.environ.get("GRAIN_TARGET", "0.05"))     # 잔결
GRAIN_BLUR = 2                                                    # 텍셀 (2048 에서 약 2~4 mm)
rng = np.random.default_rng(12)
for nm in SKIN_MATS:
    arr = px(targets[nm])
    isl = arr[..., 2] > 0.3                      # UV 섬 안(파란 채널 ≈ 1) 만 잰다 — 바깥은 검정
    dev_geo = island_dev(arr, isl)
    alb = src_px[nm][..., :3]
    lum = 0.2126 * alb[..., 0] + 0.7152 * alb[..., 1] + 0.0722 * alb[..., 2]
    if SKIP_NORMAL:
        arr[..., :3] = (0.5, 0.5, 1.0)
    else:
        # 3D-②b: 구운 노멀(형태 차이) ⊕ 색 그림에서 뽑은 요철(근육 결·핏줄·뼈 이음) ⊕ 잔결. 탄젠트 공간에서 xy 는 더하고 z 는 곱한다
        hgt = blur(lum, 1)
        s_rel = fit_strength(hgt, isl, RELIEF_TARGET)
        n_rel = normal_from_height(hgt, s_rel)
        grain = blur(rng.random(lum.shape), GRAIN_BLUR)
        s_gr = fit_strength(grain, isl, GRAIN_TARGET)
        n_gr = normal_from_height(grain, s_gr)
        n_geo = arr[..., :3] * 2.0 - 1.0
        n = np.dstack((n_geo[..., 0] + n_rel[..., 0] + n_gr[..., 0], n_geo[..., 1] + n_rel[..., 1] + n_gr[..., 1], n_geo[..., 2] * n_rel[..., 2] * n_gr[..., 2]))
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        n01 = n * 0.5 + 0.5
        arr[..., :3] = np.where(isl[..., None], n01, arr[..., :3])
        print("%s relief strength %.2f grain strength %.2f" % (nm, s_rel, s_gr))
    dev = island_dev(arr, isl)
    print("%s normal: island %.1f%%  mean|xy-0.5| geometry %.4f -> combined %.4f" % (nm, isl.mean() * 100, dev_geo, dev))
    check(dev >= 0.15, "%s 노멀맵에 요철이 있다 (섬 안 기울기 평균 %.4f >= 0.15)" % (nm, dev))
    png = new_png("skin_%s_normal" % ("body" if nm == "살" else "head"), arr, "Non-Color")
    nt = new_mats[nm].node_tree; tn = nt.nodes["normal"]; tn.image = png
    bpy.data.images.remove(targets[nm])
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if not SKIP_NORMAL:
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 1.0
        nt.links.new(tn.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    # 3D-②b 거칠기 그림: 붉은 근육·검은 구멍 = 젖음 0.5 · 회청색 살 0.85 · 흰 뼈 0.9 (glTF metallicRoughness G 채널, 금속 0)
    red = alb[..., 0] - 0.5 * (alb[..., 1] + alb[..., 2])
    sat = alb.max(-1) - alb.min(-1)
    # 문턱은 그림마다 분포로 잡는다 (그림 전체가 살짝 붉어 절대값으로는 41 % 가 젖음, 뼈 0 % 였다): 젖음 = 붉음 상위 15 %, 뼈 = 밝기 상위 15 % 이면서 채도 하위 절반
    r85, r97 = np.percentile(red[isl], [85, 97]); l85, l97 = np.percentile(lum[isl], [85, 97]); s50 = np.percentile(sat[isl], 50)
    wet = np.clip((red - r85) / max(r97 - r85, 1e-3), 0, 1)
    wet = np.maximum(wet, np.clip((0.10 - lum) / 0.05, 0, 1))          # 검은 구멍
    bone = np.clip((lum - l85) / max(l97 - l85, 1e-3), 0, 1) * np.clip((s50 - sat) / max(s50, 1e-3) + 0.5, 0, 1)
    rough = 0.85 * np.ones_like(lum)
    rough = rough * (1 - wet) + 0.5 * wet
    rough = rough * (1 - bone * (1 - wet)) + 0.9 * bone * (1 - wet)
    print("%s roughness: wet %.1f%%  bone %.1f%%  mean %.3f" % (nm, (wet > 0.5).mean() * 100, (bone > 0.5).mean() * 100, rough.mean()))
    rimg = new_png("skin_%s_rough" % ("body" if nm == "살" else "head"), np.dstack((np.ones_like(rough), rough, np.zeros_like(rough), np.ones_like(rough))), "Non-Color")
    rt = nt.nodes.new("ShaderNodeTexImage"); rt.image = rimg; rt.name = "rough"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(rt.outputs["Color"], sep.inputs["Color"]); nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])

# 고폴리·옛 재질 정리 (내보내기에 안 들어가게)
bpy.data.objects.remove(hi, do_unlink=True)
for nm in SKIN_MATS:
    bpy.data.materials.remove(bpy.data.materials[nm + "_godot"])
bpy.data.materials.remove(hi_mat)

# 몸을 재질별로 두 물체(살 / 살_머리)로 가른다 — glTFast 6.14.1 은 스킨 메시 한 개에 프리미티브가 둘이면 임포트가 깨진다
# (SortAndNormalizeBoneWeightsJob 안전 검사 예외, 09-17). 물체마다 재질 하나면 프리미티브 하나라 안 걸린다
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="MATERIAL"); bpy.ops.object.mode_set(mode="OBJECT")
parts = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Miner_Body")]
for o in parts:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.material_slot_remove_unused()
    o.name = "Miner_Body" if o.material_slots[0].material.name == "살" else "Miner_Head"
    print("part", o.name, len(o.data.polygons), [s.material.name for s in o.material_slots], "groups", len(o.vertex_groups), "mods", [m.type for m in o.modifiers])
check(len(parts) == 2 and all(len(o.material_slots) == 1 for o in parts), "몸이 재질별 두 물체로 갈라짐 (%s)" % [(o.name, len(o.material_slots)) for o in parts])
body = next(o for o in parts if o.name == "Miner_Body")

# ---------------------------------------------------------------- 4b. 눈구멍 발광 그림 (3D-②b: 눈 구체 대신 눈구멍 면이 빛난다)
# 재질 나누기(살/살_머리)는 해골과 안 맞는다(살_머리 정점이 온몸에 퍼져 있다, 09-17 실측) → 해골 자리는 정점 좌표로 잡는다: 맨 위 0.44 m (Unity 머리 상자 0.66/1.5)
EYE_R = 0.020   # m (Blender). 눈구멍은 정면 렌더에서 폭 5.4 cm · 높이 4.4 cm
# 눈구멍 가운데 = 해골 정면 정사영 렌더(1 px = 0.49 mm)에서 집은 자리 (09-18). 3D-②b 첫 식(머리 상자 가운데-20 %)은 상자에 헬멧이 들어 있어 광대뼈에 칠했다(사용자 "코뼈에 붙어 있다")
EYE_XZ = [(-0.0474, 2.2473), (0.0479, 2.2459)]
from mathutils.bvhtree import BVHTree
allco = {o: np.array([[c.x, c.y, c.z] for c in (o.matrix_world @ v.co for v in o.data.vertices)]) for o in parts}
dg = bpy.context.evaluated_depsgraph_get()
eye_pts = []
for ex, ez in EYE_XZ:
    best = None
    for o in parts:
        inv = o.matrix_world.inverted()
        hit = BVHTree.FromObject(o, dg).ray_cast(inv @ Vector((ex, -1.0, ez)), (inv.to_3x3() @ Vector((0, 1, 0))).normalized())
        if hit[0] is not None:
            w = o.matrix_world @ hit[0]
            if best is None or w.y < best.y:
                best = w
    check(best is not None, "눈구멍 (%.3f, %.3f) 에서 얼굴 면을 찾았다" % (ex, ez))
    eye_pts.append(best if best is not None else Vector((ex, 0, ez)))
print("eye socket surface points", [tuple(round(c, 3) for c in p) for p in eye_pts])
painted = {}
for o in parts:
    attr = o.data.color_attributes.new("eye", "FLOAT_COLOR", "POINT")
    co = allco[o]
    vals = np.zeros(len(co))
    cnt = [0, 0]
    for k, pt in enumerate(eye_pts):
        d = np.hypot(co[:, 0] - pt.x, co[:, 2] - pt.z)                       # 정면에서 본 거리 — 홈 안쪽 면까지 칠한다
        m = (d < EYE_R) & (co[:, 1] > pt.y - 0.012) & (co[:, 1] < pt.y + 0.04)   # 깊이: 닿은 면 앞 1.2 cm ~ 안쪽 4 cm
        vals = np.maximum(vals, np.where(m, 1.0 - (d / EYE_R) ** 2, 0.0)); cnt[k] = int(m.sum())
    for i, v in enumerate(vals):
        attr.data[i].color = (v, v, v, 1.0)
    painted[o.name] = cnt
print("eye sockets painted verts", painted)
tot = [sum(painted[o][k] for o in painted) for k in (0, 1)]
check(min(tot) >= 10, "눈구멍 자리마다 정점 10개 이상 칠해짐 %s" % tot)
emit_mat = bpy.data.materials.new("eye_emit"); emit_mat.use_nodes = True
ent = emit_mat.node_tree; ent.nodes.clear()
eo = ent.nodes.new("ShaderNodeOutputMaterial"); ee = ent.nodes.new("ShaderNodeEmission"); ea = ent.nodes.new("ShaderNodeAttribute"); ea.attribute_name = "eye"
ent.links.new(ea.outputs["Color"], ee.inputs["Color"]); ent.links.new(ee.outputs["Emission"], eo.inputs["Surface"])
etgt = bpy.data.images.new("bake_eye", BAKE_PX, BAKE_PX, alpha=False); etgt.colorspace_settings.name = "Non-Color"
etn = ent.nodes.new("ShaderNodeTexImage"); etn.image = etgt; ent.nodes.active = etn
scene.render.engine = "CYCLES"; scene.cycles.samples = 1; scene.cycles.device = "CPU"
b = scene.render.bake; b.use_selected_to_active = False; b.margin = 8; b.use_clear = True
emissive_mats = []
for o in parts:
    if sum(painted[o.name]) == 0:
        continue
    real = o.material_slots[0].material
    o.material_slots[0].material = emit_mat
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type="EMIT")
    o.material_slots[0].material = real
    earr = px(etgt); em = blur(earr[..., 0], 1)
    white = float((em > 0.5).mean() * 100)
    print("eye emissive %s (%s): white %.3f%% of texture" % (o.name, real.name, white))
    check(0.0 < white < 2.0, "%s 발광 그림에 눈구멍 얼룩이 있고 2 %% 미만 (%.3f%%)" % (real.name, white))
    eimg = new_png("skin_%s_emissive" % ("body" if real.name == "살" else "head"), np.dstack((em, em, em, np.ones_like(em))), "sRGB")
    hnt = real.node_tree; hbsdf = next(n for n in hnt.nodes if n.type == "BSDF_PRINCIPLED")
    et = hnt.nodes.new("ShaderNodeTexImage"); et.image = eimg; et.name = "emissive"
    hnt.links.new(et.outputs["Color"], hbsdf.inputs["Emission Color"]); hbsdf.inputs["Emission Strength"].default_value = 1.0
    emissive_mats.append(real.name)
bpy.data.images.remove(etgt); bpy.data.materials.remove(emit_mat)
print("emissive materials", emissive_mats)

def parts_bbox():
    los, his = zip(*[world_bbox(o) for o in parts])
    return Vector([min(v[i] for v in los) for i in range(3)]), Vector([max(v[i] for v in his) for i in range(3)])

# ---------------------------------------------------------------- 5. 미리보기 렌더 (Eevee, 정면 2 m 헤드램프 하나) — 노멀 있음 / 없음
arm.data.pose_position = "POSE"
actions = {a.name: a for a in bpy.data.actions}
for tr in arm.animation_data.nla_tracks:
    tr.mute = True
ad = arm.animation_data; ad.action = actions["idle_crouch"]
if hasattr(ad, "action_slot") and actions["idle_crouch"].slots:
    ad.action_slot = actions["idle_crouch"].slots[0]
scene.frame_set(10)
bpy.context.view_layer.update()
lo, hi_ = parts_bbox(); center = (lo + hi_) * 0.5
print("idle_crouch f10 bbox", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi_))
scene.render.engine = "BLENDER_EEVEE"; scene.render.resolution_x = scene.render.resolution_y = 1024
world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0.01, 0.01, 0.01, 1)
cam_data = bpy.data.cameras.new("cam"); cam_data.lens = 28
cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
lamp = bpy.data.objects.new("lamp", bpy.data.lights.new("lamp", "SPOT")); scene.collection.objects.link(lamp)
lamp.data.energy = 600; lamp.data.spot_size = math.radians(100); lamp.data.shadow_soft_size = 0.05
lamp.data.color = (1.0, 0.96, 0.88)
cam.location = (center.x, lo.y - 2.0, 1.6); cam.rotation_euler = (math.radians(90 - math.degrees(math.atan2(1.6 - center.z, 2.0))), 0, 0)
views = {"front": (tuple(cam.location), tuple(cam.rotation_euler)),                          # 램프 = 머리 (정면)
         "side": ((center.x - 1.5, lo.y - 1.4, 1.6), (math.radians(80), 0, math.radians(-40)))}   # 램프를 왼쪽 40° 로 — 요철 그늘이 잘 보인다
def rd(path):
    im = bpy.data.images.load(path); a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im); return a
for vname, (lloc, lrot) in views.items():
    lamp.location = lloc; lamp.rotation_euler = lrot
    got = {}
    for tag, strength in (("normal_on", 1.0), ("normal_off", 0.0)):
        for nm in SKIN_MATS:
            for n in new_mats[nm].node_tree.nodes:
                if n.type == "NORMAL_MAP":
                    n.inputs["Strength"].default_value = strength
        scene.render.filepath = os.path.join(RENDER, "%s_2m_%s.png" % (vname, tag))
        bpy.ops.render.render(write_still=True)
        got[tag] = rd(scene.render.filepath)
    d = np.abs(got["normal_on"] - got["normal_off"])
    print("render %s: brightness %.3f  normal on/off diff mean %.4f max %.3f" % (vname, got["normal_on"].mean(), d.mean(), d.max()))
for nm in SKIN_MATS:
    for n in new_mats[nm].node_tree.nodes:
        if n.type == "NORMAL_MAP":
            n.inputs["Strength"].default_value = 1.0
for o in (cam, lamp):
    bpy.data.objects.remove(o, do_unlink=True)
for tr in arm.animation_data.nla_tracks:
    tr.mute = False
ad.action = None
print("rendered", RENDER)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("saved", OUT_BLEND)

# ---------------------------------------------------------------- 6. GLB 내보내기 (stage6 과 같은 설정)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS",
                          export_apply=True, export_yup=True, export_skins=True, export_image_format="AUTO")
print("exported", OUT_GLB, round(os.path.getsize(OUT_GLB) / 1e6, 2), "MB")

# ---------------------------------------------------------------- 7. 자기 검사 (내보낸 파일을 다시 읽는다)
with open(OUT_GLB, "rb") as f:
    f.read(12); ln, = struct.unpack("<I", f.read(4)); f.read(4); j = json.loads(f.read(ln))
mimes = [i.get("mimeType") for i in j.get("images", [])]
print("glb images", [(i.get("name"), i.get("mimeType")) for i in j.get("images", [])])
check(mimes.count("image/webp") == 0, "GLB 안 webp 0장 (%s)" % mimes)
mats = {m["name"]: m for m in j["materials"]}
for nm in SKIN_MATS:
    m = mats.get(nm)
    check(m is not None and "normalTexture" in m, "%s 재질에 normalTexture" % nm)
    check(m is not None and m.get("pbrMetallicRoughness", {}).get("baseColorTexture") is not None, "%s 재질에 색 그림" % nm)
    check(m is not None and m.get("pbrMetallicRoughness", {}).get("metallicFactor", 1) == 0, "%s 금속 0" % nm)
    check(m is not None and m.get("pbrMetallicRoughness", {}).get("metallicRoughnessTexture") is not None, "%s 재질에 거칠기 그림" % nm)
check(all("emissiveTexture" in mats.get(nm, {}) for nm in emissive_mats) and len(emissive_mats) >= 1, "눈구멍 발광 그림이 든 재질 %s (emissiveFactor %s)" % (emissive_mats, [mats.get(nm, {}).get("emissiveFactor") for nm in emissive_mats]))
anims = [a["name"] for a in j.get("animations", [])]
check(len(anims) == 14, "동작 14개 (%d) %s" % (len(anims), anims))
multi = [(m.get("name"), len(m["primitives"])) for m in j["meshes"] if len(m["primitives"]) != 1]
check(not multi, "메시마다 프리미티브 1개 (glTFast 스킨 버그 회피) %s" % multi)
skins = j.get("skins", [])
check(len(skins) >= 1 and all(n.get("skin") is not None for n in j["nodes"] if n.get("name") in ("Miner_Body", "Miner_Head")), "몸·머리 둘 다 스킨 연결 (skins %d)" % len(skins))
for nm in SKIN_MATS:
    tag = "body" if nm == "살" else "head"
    re = bpy.data.images.load(os.path.join(TEX, "skin_%s_albedo.png" % tag))
    keep = groin_masks[nm] < 0.01                                         # 사타구니를 덮은 자리 밖은 원본 그대로여야 한다
    d = float(np.abs(px(re)[..., :3] - orig_px[nm][..., :3])[keep].mean())
    check(d <= 1.0 / 255, "%s PNG 색이 원본 webp 와 같다 (평균 차 %.5f ≤ %.5f)" % (nm, d, 1 / 255))
print("stage12 %s  fails=%d %s" % ("ALL PASS" if not fails else "FAIL", len(fails), fails))
sys.exit(0 if not fails else 2)
