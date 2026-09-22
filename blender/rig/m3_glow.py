"""m3 빛: 안전모 램프 유리를 따로 그물·재질로 떼고, 두 눈구멍 발광 그림을 만든다 (제안서 docs/제안서_m3_눈_발광_램프_미끼_갱목.md M1, 09-20 승인).
  blender -b --factory-startup -P blender/rig/m3_glow.py
입력: Documents/MineTunnel/blender/miner_v5_stage19_m3_neck.blend (안 고친다)
출력: Documents/MineTunnel/blender/miner_v5_stage20_m3_glow.blend → SRC_BLEND 로 walk_knuckle.py 에 (tools/bake_m3.sh)
하는 일: ① 램프 유리 면(안전모 앞 둥근 판 — 아래 자리·반지름·앞을 보는 면)을 머리 그물에서 떼어 물체 Miner_LampGlass · 재질 '램프_유리'로. 발광 그림 = 제 색 그림(켜면 유리 무늬째 빛난다)
           재질이 따로여야 Unity(StalkerLook)가 램프와 눈을 따로 켜고 끈다. 이름이 '살'로 시작하면 눈 발광을 같이 받으니 피한다
        ② 눈 발광 그림 skin_head_emissive: 두 눈구멍 속 면(아래 자리·반지름·깊이)만 흰 그림을 머리 UV 에 그린다 → 머리 재질 발광에 잇는다 (옛 몸 3D-②b 와 같은 구실)
자리 값은 2 cm 눈금 그림(앞·옆)에서 읽은 것 — 머리 뼈 머리 기준. 틀리면 아래 검사가 잡는다.
사보타주: SABOTAGE=noglass(유리 안 뗌) -> 검사 1 FAIL · wholeface(눈구멍 반지름 20 cm) -> 검사 2 FAIL · oneeye(오른 눈만) -> 검사 3 FAIL"""
import bpy, bmesh, os, sys, numpy as np
from mathutils import Vector

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage19_m3_neck.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage20_m3_glow.blend"))
SHOTS = os.environ.get("SHOTS", "")
SABOTAGE = os.environ.get("SABOTAGE", "")
P = "mixamorig:"
# 머리 뼈 머리(쉬는 자세 세계 좌표 0, 0.064, 2.055) 기준 (x 옆, y 앞뒤(−가 얼굴), z 위) m
GLASS_C, GLASS_R, GLASS_Y = (0.014, 0.369), 0.043, -0.155      # 유리 가운데 (x, z) · 반지름 · 이보다 앞(y 작은)쪽 면만
EYES = {"L": (-0.040, 0.233), "R": (0.060, 0.233)}              # 눈구멍 가운데 (x, z) — 얼굴 가운데가 x +0.01 로 치우쳐 있다
EYE_R = 0.20 if SABOTAGE == "wholeface" else 0.030
EYE_Y = (-0.142, -0.030)                                        # 눈구멍 속 깊이: 눈두덩 앞면(−0.146)보다 뒤 ~ 구멍 바닥. −0.094 까지만 잡으니 테두리 초승달만 빛났다(09-20 그림)
TEX = 1024

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
arm = bpy.data.objects["Miner_Rig"]; head = bpy.data.objects["Miner_Head"]
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
h0 = arm.matrix_world @ arm.data.bones[P + "Head"].head_local
mw = head.matrix_world; nw = mw.to_3x3()
faces0 = len(head.data.polygons)
cen = np.array([(mw @ p.center) - h0 for p in head.data.polygons]); nor = np.array([(nw @ p.normal).normalized() for p in head.data.polygons])

# ---- ① 램프 유리
glass = (np.hypot(cen[:, 0] - GLASS_C[0], cen[:, 2] - GLASS_C[1]) < GLASS_R) & (cen[:, 1] < GLASS_Y) & (nor[:, 1] < -0.3)
glass_idx = set(np.where(glass)[0]) if SABOTAGE != "noglass" else set()
lamp = None
if glass_idx:
    lamp = head.copy(); lamp.data = head.data.copy(); bpy.context.scene.collection.objects.link(lamp)
    for ob, keep in ((lamp, True), (head, False)):
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.index in glass_idx) != keep], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces and (keep or not v.link_edges)], context="VERTS")      # 면을 잃은 점 (머리 쪽은 원래 있던 빈 변의 점은 둔다)
        bm.to_mesh(ob.data); bm.free(); ob.data.update()
    lamp.name = "Miner_LampGlass"; lamp.data.name = "Miner_LampGlass"
    lm = head.data.materials[0].copy(); lm.name = "램프_유리"; lamp.data.materials.clear(); lamp.data.materials.append(lm)
    nt = lm.node_tree; bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src = bs.inputs["Base Color"].links[0].from_socket
    while src.node.type != "TEX_IMAGE":                          # 색에 곱한 어둡게(m2_body.py) 노드를 거슬러 그림까지
        src = next(i for i in src.node.inputs if i.links).links[0].from_socket
    nt.links.new(src, bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.0
    gw = {lamp.vertex_groups[g.group].name for v in lamp.data.vertices for g in v.groups if g.weight > 1e-4}
    gc = np.array([lamp.matrix_world @ v.co for v in lamp.data.vertices]).mean(0) - np.array(h0)
check(lamp is not None and len(lamp.data.polygons) >= 50 and gw == {P + "Head"} and len(head.data.polygons) + len(lamp.data.polygons) == faces0,
      "램프 유리를 따로 그물로: 면 %d (≥ 50) · 붙은 뼈 %s (머리 뼈만) · 가운데 %s (머리 뼈 기준) · 머리 + 유리 면 수 = 전과 같음" %
      (len(lamp.data.polygons) if lamp else 0, sorted(gw) if lamp else None, gc.round(3) if lamp else None))

# ---- ② 눈 발광 그림 (머리 UV 에 눈구멍 속 면의 세모를 흰색으로)
me = head.data; uv = me.uv_layers.active.data
cen = np.array([(mw @ p.center) - h0 for p in me.polygons])
img = np.zeros((TEX, TEX), np.float32); lit = {}
for side, (ex, ez) in EYES.items():
    if SABOTAGE == "oneeye" and side == "L":
        continue
    m = (np.hypot(cen[:, 0] - ex, cen[:, 2] - ez) < EYE_R) & (cen[:, 1] > EYE_Y[0]) & (cen[:, 1] < EYE_Y[1])
    lit[side] = np.where(m)[0]
    for fi in lit[side]:
        p = me.polygons[fi]; pts = np.array([uv[li].uv[:] for li in p.loop_indices]) * TEX
        for k in range(1, len(pts) - 1):                         # 부채꼴 세모마다 채운다
            a, b, c = pts[0], pts[k], pts[k + 1]
            x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])) - 1)), int(min(TEX - 1, np.ceil(max(a[0], b[0], c[0])) + 1))
            y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])) - 1)), int(min(TEX - 1, np.ceil(max(a[1], b[1], c[1])) + 1))
            if x1 < x0 or y1 < y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d; w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
            inside = (w0 >= -0.35) & (w1 >= -0.35) & (w0 + w1 <= 1.35)            # 세모보다 조금 넓게 — 이음매에서 검은 줄이 안 생기게
            img[y0:y1 + 1, x0:x1 + 1][inside] = 1.0
em = bpy.data.images.new("skin_head_emissive", TEX, TEX, alpha=False)
px = np.ones((TEX, TEX, 4), np.float32); px[:, :, :3] = img[:, :, None]; em.pixels.foreach_set(px.ravel())
em.filepath_raw = os.path.join(MT, "mesh", "meshy_m3_head_emissive.png"); em.file_format = "PNG"; em.save(); em.pack()
hm = head.data.materials[0]; nt = hm.node_tree; bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
node = nt.nodes.new("ShaderNodeTexImage"); node.image = em
nt.links.new(node.outputs["Color"], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.0
share = float(img.mean()); n_lit = sum(len(v) for v in lit.values())
check(0 < share <= 0.02 and n_lit >= 40, "눈 발광 그림: 밝은 넓이 %.3f %% (0 < ≤ 2 — 얼굴 전체가 빛나면 안 된다) · 눈구멍 속 면 %d (≥ 40)" % (share * 100, n_lit))
check(all(len(lit.get(s, [])) >= 15 for s in EYES), "두 눈 다: 왼 %d · 오른 %d 면 (눈마다 ≥ 15)" % (len(lit.get("L", [])), len(lit.get("R", []))))

if SHOTS:
    import math
    os.makedirs(SHOTS, exist_ok=True); sc = bpy.context.scene
    hidden = {o: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in ("Miner_Head", "Miner_LampGlass")
    white = bpy.data.materials.new("shot_white"); white.diffuse_color = (1, 0.85, 0.4, 1); red = bpy.data.materials.new("shot_red"); red.diffuse_color = (1, 0.1, 0.1, 1)
    base = head.data.materials[0]; head.data.materials.append(red)
    for s_ in lit.values():
        for fi in s_:
            head.data.polygons[fi].material_index = 1
    if lamp:
        keep_l = lamp.data.materials[0]; lamp.data.materials[0] = white
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.6; cam.location = (0.01, -4, 2.3); cam.rotation_euler = (math.pi / 2, 0, 0)
    sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 900
    sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "MATERIAL"
    sc.render.filepath = os.path.join(SHOTS, "30_glow_faces_front.png"); bpy.ops.render.render(write_still=True)
    for p in head.data.polygons:
        p.material_index = 0
    head.data.materials.pop(index=1)
    if lamp:
        lamp.data.materials[0] = keep_l
    bpy.data.objects.remove(cam, do_unlink=True)
    for o, h in hidden.items():
        o.hide_render = h

arm.data.pose_position = "POSE"
if fails:
    sys.exit("m3_glow FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_glow ALL PASS →", OUT)
