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
for nm in SKIN_MATS:
    arr = px(targets[nm])
    if SKIP_NORMAL:
        arr[..., :3] = (0.5, 0.5, 1.0)
    isl = arr[..., 2] > 0.3                      # UV 섬 안(파란 채널 ≈ 1) 만 잰다 — 바깥은 검정
    dev = float(np.abs(arr[isl][:, :2] - 0.5).mean()) if isl.any() else 0.0
    print("%s normal: island %.1f%%  mean|xy-0.5| %.4f" % (nm, isl.mean() * 100, dev))
    check(dev > 0.02, "%s 노멀맵이 평평한 판이 아니다 (섬 안 기울기 평균 %.4f > 0.02)" % (nm, dev))
    png = new_png("skin_%s_normal" % ("body" if nm == "살" else "head"), arr, "Non-Color")
    nt = new_mats[nm].node_tree; tn = nt.nodes["normal"]; tn.image = png
    bpy.data.images.remove(targets[nm])
    if not SKIP_NORMAL:
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 1.0
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        nt.links.new(tn.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

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
anims = [a["name"] for a in j.get("animations", [])]
check(len(anims) == 14, "동작 14개 (%d) %s" % (len(anims), anims))
multi = [(m.get("name"), len(m["primitives"])) for m in j["meshes"] if len(m["primitives"]) != 1]
check(not multi, "메시마다 프리미티브 1개 (glTFast 스킨 버그 회피) %s" % multi)
skins = j.get("skins", [])
check(len(skins) >= 1 and all(n.get("skin") is not None for n in j["nodes"] if n.get("name") in ("Miner_Body", "Miner_Head")), "몸·머리 둘 다 스킨 연결 (skins %d)" % len(skins))
for nm in SKIN_MATS:
    tag = "body" if nm == "살" else "head"
    re = bpy.data.images.load(os.path.join(TEX, "skin_%s_albedo.png" % tag))
    d = float(np.abs(px(re)[..., :3] - src_px[nm][..., :3]).mean())
    check(d <= 1.0 / 255, "%s PNG 색이 원본 webp 와 같다 (평균 차 %.5f ≤ %.5f)" % (nm, d, 1 / 255))
print("stage12 %s  fails=%d %s" % ("ALL PASS" if not fails else "FAIL", len(fails), fails))
sys.exit(0 if not fails else 2)
