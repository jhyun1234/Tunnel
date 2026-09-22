"""m3 = Meshy 부위 조립 (2026-09-20): 몸 m2 + 따로 뽑은 머리 head1 + 따로 뽑은 손 hand1(좌우 거울). 옛 몸(4b·4c)과 같은 방식.
  blender -b --factory-startup -P blender/rig/m3_assemble.py
까닭: 전신 그림에서는 머리가 60 픽셀쯤이라 어떤 생성기든 머리·손이 뭉개진다 — 클로즈업 그림으로 따로 뽑아 붙인다.
입력: Documents/MineTunnel/mesh/meshy_{m2,head1,hand1}.glb + meshy_torso1.glb (gen_meshy.py)   출력: mesh/meshy_m3.glb (m2 좌표 그대로, 그물 넷 — glTFast 는 스킨 그물 하나에 재질 둘을 못 읽는다)
숫자는 probe 로 잰 것: 헬멧 챙 너비 m2 0.206 / head1 0.486, m2 손목 x 0.64 · 손끝 0.95, hand1 은 길이 축 y(손목 +0.70 → 발톱 끝 −0.95)
사보타주: SABOTAGE=nohead -> "머리 그물이 몸 목 위에 얹힘" FAIL · SABOTAGE=noholes -> "몸통 피부에 상처 구멍" FAIL
SABOTAGE=blindholes -> "속이 없는 곳은 안 뚫었다" FAIL · ORGAN_SAT=1 -> "장기 색이 진해졌다" FAIL · SABOTAGE=scales -> "몸 색 그림에 자잘한 무늬 없음" FAIL
(SABOTAGE=meshynormal 은 비교용 — Meshy 가 준 비늘 노멀맵을 그대로 둔다)"""
import bpy, os, sys, math, numpy as np
from mathutils import Vector, Matrix

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel", "mesh")
OUT = os.environ.get("OUT_GLB", os.path.join(MT, "meshy_m3.glb"))
SAB = os.environ.get("SABOTAGE", "")
M2_TOP, NECK_CUT = 0.811, 0.52                   # m2 헬멧 꼭대기 · 몸을 자르는 높이(목 밑동 바로 위)
HEAD_F = 0.206 / 0.486                           # head1 → m2 크기 (헬멧 챙 너비로)
WRIST_X, HAND_F, HAND_WRIST_Y = 0.64, 0.20, 0.70  # m2 손목 · hand1 → m2 크기 · hand1 의 손목 자리(y)
ARM_Y, ARM_Z = 0.0, 0.415

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.read_factory_settings(use_empty=True)
def load(name, new_name, mat_name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MT, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    o = next(o for o in new if o.type == "MESH")
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for x in new:
        if x is not o:
            bpy.data.objects.remove(x, do_unlink=True)
    o.name = new_name; o.data.materials[0].name = mat_name
    return o
def co(o):
    a = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get("co", a); return a.reshape(-1, 3).astype(np.float64)
def put(o, V):
    o.data.vertices.foreach_set("co", V.astype(np.float32).ravel()); o.data.update()
def cut(o, point, normal, fill=False):
    """normal 쪽을 버린다. fill = 자른 자리를 막는다(손목: 팔 끝이 빈 대롱으로 보였다, 사용자 09-20)"""
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=point, plane_no=normal, clear_outer=True, use_fill=fill)
    bpy.ops.object.mode_set(mode="OBJECT")

body = load("meshy_m2", "Miner_Body", "살")
head = load("meshy_head1", "Miner_Head", "살_머리")
hand = load("meshy_hand1", "Miner_Hands", "살_손")

# ---- 머리: 챙 너비로 줄이고 헬멧 꼭대기를 맞춘다. 앞(−y)·가운데는 챙 높이 띠의 가운데로
H = co(head); top = H[:, 2].max()
brim = H[(H[:, 2] < top - 0.24) & (H[:, 2] > top - 0.30)]
B = co(body); bbrim = B[(B[:, 2] < M2_TOP - 0.09) & (B[:, 2] > M2_TOP - 0.15)]
hc = (brim.min(0) + brim.max(0)) / 2; bc = (bbrim.min(0) + bbrim.max(0)) / 2
H = (H - [hc[0], hc[1], top]) * HEAD_F + [bc[0], bc[1], M2_TOP]
# 앞뒤·좌우는 헬멧이 아니라 목에서 맞춘다 — 머리는 통째로 바뀌니 이어지는 곳은 목뿐이다 (헬멧으로 맞추면 목이 6 cm 어긋났다, 09-20)
mid = lambda P: (P.min(0) + P.max(0)) / 2
H[:, :2] += (mid(B[(abs(B[:, 2] - NECK_CUT) < 0.01) & (abs(B[:, 0]) < 0.1)]) - mid(H[abs(H[:, 2] - NECK_CUT) < 0.01]))[:2]
put(head, H)
cut(head, (0, 0, NECK_CUT - 0.02), (0, 0, -1))   # 머리: 목 아래(흉상)를 버림 — 몸 목과 2 cm 겹침
if SAB != "nohead":
    cut(body, (0, 0, NECK_CUT), (0, 0, 1))       # 몸: 머리를 버림

# ---- 손: 길이 축 y(−y 가 발톱 끝) → 왼손은 +x. z 축으로 +90° 돌림: (x, y, z) → (−y, x, z)
D = co(hand)
wrist = D[(D[:, 1] > HAND_WRIST_Y - 0.05) & (D[:, 1] < HAND_WRIST_Y + 0.05)]
wc = (wrist.min(0) + wrist.max(0)) / 2
D = D - [wc[0], HAND_WRIST_Y, wc[2]]
D = np.c_[-D[:, 1], D[:, 0], D[:, 2]] * HAND_F + [WRIST_X, ARM_Y, ARM_Z]
put(hand, D)
cut(hand, (WRIST_X - 0.015, 0, 0), (-1, 0, 0))   # 손: 손목 안쪽(뼈 밑동)을 버림 — 팔과 1.5 cm 겹침
right = hand.copy(); right.data = hand.data.copy(); bpy.context.scene.collection.objects.link(right)
R = co(right); R[:, 0] *= -1; put(right, R)
right.data.flip_normals()
cut(body, (WRIST_X, 0, 0), (1, 0, 0), fill=True); cut(body, (-WRIST_X, 0, 0), (-1, 0, 0), fill=True)
bpy.ops.object.select_all(action="DESELECT"); hand.select_set(True); right.select_set(True); bpy.context.view_layer.objects.active = hand
bpy.ops.object.join()

# ---- 몸통 속: 따로 뽑은 갈비·장기·골반(torso1)을 피부 안에 넣고, 피부는 상처 자리(그림에서 살·뼈 색인 면)만 뚫는다
# torso1 표지(probe): 어깨선 z 0.47 · 골반 밑 −0.95 · 갈비 반폭 0.29 · 그 밖 |x| > 0.30 은 위팔뼈 밑동(T 포즈와 안 맞아 버림) · z > 0.50 은 지어낸 해골
TORSO_F = (0.50 - -0.12) / (0.47 - -0.95)         # m2 어깨선 0.50 ~ 가랑이 −0.12
torso = load("meshy_torso1", "Miner_Torso", "살_속")
cut(torso, (0, 0, 0.50), (0, 0, 1)); cut(torso, (0.30, 0, 0), (1, 0, 0)); cut(torso, (-0.30, 0, 0), (-1, 0, 0))
T = co(torso); T = np.c_[T[:, 0] * TORSO_F, T[:, 1] * TORSO_F + 0.02, (T[:, 2] - 0.47) * TORSO_F + 0.50]; put(torso, T)

mat = body.data.materials[0]
img = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].links[0].from_node.image
w, h = img.size; px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
uv = body.data.uv_layers.active.data; B = co(body); holes = []; holes_c = []
# 속 몸통이 바로 뒤(면 안쪽 5 cm 안)에 있는 면만 뚫는다 — 색만 보고 뚫으면 골반 밑·어깨처럼 속이 없는 곳이 휑하게 뚫린다(사용자 09-20 "엉덩이 골반·오른쪽 어깨가 뚫려 있음")
from mathutils.bvhtree import BVHTree
bvh = BVHTree.FromObject(torso, bpy.context.evaluated_depsgraph_get())
for poly in body.data.polygons:
    c = B[list(poly.vertices)].mean(0)
    if not (abs(c[0]) < 0.19 and -0.10 < c[2] < 0.47):
        continue
    if SAB != "blindholes" and bvh.ray_cast(Vector(c), -poly.normal, 0.05)[0] is None:
        continue
    u = np.mean([uv[i].uv for i in poly.loop_indices], axis=0)
    r, g, b_ = px[int(u[1] % 1 * (h - 1)), int(u[0] % 1 * (w - 1)), :3]
    mx = max(r, g, b_)
    if SAB != "noholes" and mx - min(r, g, b_) > 0.10 and (mx - min(r, g, b_)) / mx > 0.25:   # 살·뼈 = 채도 0.25 위 + 색 차 0.10 위 (어두운 피부는 잡음만으로 채도가 높게 나온다 — 86 % 가 뚫렸었다)
        holes.append(poly.index); holes_c.append((tuple(c), tuple(-poly.normal)))
torso_faces = sum(1 for poly in body.data.polygons if abs(B[list(poly.vertices)].mean(0)[0]) < 0.19 and -0.10 < B[list(poly.vertices)].mean(0)[2] < 0.47)
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
for i in holes:
    body.data.polygons[i].select = True
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.delete(type="FACE"); bpy.ops.object.mode_set(mode="OBJECT")
# 뚫고 남은 조각 부스러기(면 150개 아래로 따로 떨어진 섬)를 지운다 — 09-20 첫 렌더에서 갈비 앞에 색종이처럼 떠 있었다
import bmesh
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)      # glTF 는 UV 솔기마다 점이 갈라져 있다 — 안 붙이면 면마다 섬이 된다(09-20 몸 전체가 지워졌다)
bm.faces.ensure_lookup_table(); bm.faces.index_update(); seen = set(); crumbs = []
for f0 in bm.faces:
    if f0.index in seen:
        continue
    isl, stack = [], [f0]; seen.add(f0.index)
    while stack:
        f = stack.pop(); isl.append(f)
        for e in f.edges:
            for g in e.link_faces:
                if g.index not in seen:
                    seen.add(g.index); stack.append(g)
    if len(isl) < 150:
        crumbs += isl
n_crumbs = len(crumbs)
bmesh.ops.delete(bm, geom=crumbs, context="FACES"); bm.to_mesh(body.data); bm.free(); body.data.update()
print("crumb faces removed", n_crumbs)
check(0 < len(body.data.polygons) and n_crumbs < 3000, "부스러기만 지웠다: %d 면 지움 · 몸 %d 면 남음" % (n_crumbs, len(body.data.polygons)))
# 구멍으로 피부 안쪽이 보인다. 양면 재질은 Unity 에서 뒷면이 새까맣게 나왔다(사용자 09-20 "갈비뼈 사이 검은 것") → 몸통 피부를 뒤집은 안감 그물을 따로 둔다(어두운 살색, 그림 없음)
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.duplicate(); liner = bpy.context.active_object; liner.name = "Miner_Liner"
bm = bmesh.new(); bm.from_mesh(liner.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not (abs(f.calc_center_median().x) < 0.24 and -0.16 < f.calc_center_median().z < 0.53)], context="FACES")
for v in bm.verts:
    v.co -= v.normal * 0.002
bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(liner.data); bm.free()
lm = bpy.data.materials.new("안감_살")      # "살" 로 시작하면 Unity StalkerLook·검사가 살 재질로 세어 노멀맵을 찾는다; lm.use_nodes = True
lb = next(n for n in lm.node_tree.nodes if n.type == "BSDF_PRINCIPLED"); lb.inputs["Base Color"].default_value = (0.10, 0.025, 0.02, 1); lb.inputs["Roughness"].default_value = 0.85
liner.data.materials.clear(); liner.data.materials.append(lm)
check(0.10 <= len(holes) / torso_faces <= 0.75, "몸통 피부에 상처 구멍: 몸통 면 %d 중 %d 뚫음 (%.0f %%, 15~75)" % (torso_faces, len(holes), 100 * len(holes) / torso_faces))
blind = sum(1 for i in holes_c if bvh.ray_cast(Vector(i[0]), Vector(i[1]), 0.05)[0] is None)
check(blind == 0, "속이 없는 곳은 안 뚫었다: 뚫은 면 %d 중 뒤에 속 몸통이 없는 면 %d" % (len(holes_c), blind))
B = co(body); T = co(torso); skin = B[(abs(B[:, 0]) < 0.19) & (B[:, 2] > -0.10) & (B[:, 2] < 0.47)]
out_x = max(0.0, abs(T[:, 0]).max() - abs(skin[:, 0]).max()); out_y = max(0.0, skin[:, 1].min() - T[:, 1].min(), T[:, 1].max() - skin[:, 1].max())
check(out_x <= 0.01 and out_y <= 0.015, "속 몸통이 피부 안에 든다: 옆으로 %.3f · 앞뒤로 %.3f m 삐져나옴 (≤ 0.01 · 0.015)" % (out_x, out_y))

# ---- 몸 색 그림의 비늘 무늬 지우기: Meshy 가 만든 몸 색 그림에 주기 10 픽셀쯤의 자갈 무늬가 박혀 있다(노멀을 새로 구워도 남았다, 09-20).
# 512 로 줄였다 2048 로 키워 무늬 주기보다 넓게 흐린다 — 색·상처 자리는 남고 무늬만 죽는다. 상처 속은 이제 진짜 형상(torso1)이라 흐려져도 된다
def rough(im):                                    # 같은 물리 간격(4096 기준 8 픽셀)에서 본 밝기 차 — 자갈 무늬 주기가 10 픽셀쯤
    n = im.size[0]; a = np.empty(n * n * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(n, n, 4)[:, :, :3].mean(2); k = max(1, n * 4 // 4096)
    return float(np.abs(a[:, k:] - a[:, :-k]).mean())
hf0 = rough(img)
if SAB != "scales":
    img.scale(512, 512); img.scale(2048, 2048); img.pack()
if SAB != "scales":                               # 속 몸통(갈비) 그림에도 같은 자갈 무늬가 있다 (09-20 목·가슴 확대 렌더) — 덜 흐리게(1024)
    timg = next(n for n in torso.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].links[0].from_node.image
    timg.scale(1024, 1024); timg.scale(2048, 2048); timg.pack()
# 장기 색을 진하게 (사용자 09-20): 속 몸통 그림에서 붉은 픽셀(장기·살)만 채도 1.8배 · 밝기 0.8배. 뼈(베이지)는 그대로
ORGAN_SAT = float(os.environ.get("ORGAN_SAT", "1.8"))
n_ = timg.size[0]; tp = np.empty(n_ * n_ * 4, np.float32); timg.pixels.foreach_get(tp); tp = tp.reshape(-1, 4)
rgb = tp[:, :3]; red = (rgb[:, 0] > rgb[:, 1] * 1.25) & (rgb[:, 0] > rgb[:, 2] * 1.25)
sat0 = float((rgb[red].max(1) - rgb[red].min(1)).mean())
lum = rgb[red].mean(1, keepdims=True); rgb[red] = np.clip((lum + (rgb[red] - lum) * ORGAN_SAT) * 0.8, 0, 1)
sat1 = float((rgb[red].max(1) - rgb[red].min(1)).mean())
timg.pixels.foreach_set(tp.ravel()); timg.pack()
check(red.mean() > 0.05 and sat1 > sat0 * 1.25, "장기 색이 진해졌다: 붉은 픽셀 %.0f %% · 색 차 %.3f → %.3f (≥ 1.25배)" % (100 * red.mean(), sat0, sat1))
hf = rough(img)
check(hf < 0.6 * hf0, "몸 색 그림의 자잘한 무늬가 죽었다: 4 픽셀 간격 밝기 차 %.4f → %.4f (< 60 %%)" % (hf0, hf))

# ---- 몸 노멀맵을 86만 면 원본(_pre)에서 다시 굽는다 — Meshy 가 준 몸 노멀맵에는 온몸을 덮는 비늘 무늬가 들어 있다(Blender 렌더에서도 보임, 09-20)
if SAB != "meshynormal":
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(MT, "meshy_m2_pre.glb"))
    hi = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    bpy.ops.object.select_all(action="DESELECT"); hi.select_set(True); bpy.context.view_layer.objects.active = hi
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 4
    try:
        cp = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                cp.compute_device_type = kind; cp.get_devices()
                if any(d.type == kind for d in cp.devices):
                    for d in cp.devices:
                        d.use = True
                    sc.cycles.device = "GPU"; break
            except Exception:
                pass
    except Exception as e:
        print("GPU 없음 — CPU 로 굽는다", e)
    nt = mat.node_tree
    bake_img = bpy.data.images.new("skin_body_normal_baked", 4096, 4096, alpha=False, float_buffer=False); bake_img.colorspace_settings.name = "Non-Color"
    node = nt.nodes.new("ShaderNodeTexImage"); node.image = bake_img; nt.nodes.active = node; node.select = True
    bpy.ops.object.select_all(action="DESELECT"); hi.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.bake(type="NORMAL", use_selected_to_active=True, cage_extrusion=0.006, max_ray_distance=0.02, margin=16)
    bake_img.filepath_raw = os.path.join(MT, "meshy_m3_body_normal.png"); bake_img.file_format = "PNG"; bake_img.save()
    nm = next(n for n in nt.nodes if n.type == "NORMAL_MAP")
    nt.links.new(node.outputs["Color"], nm.inputs["Color"])
    bpy.data.objects.remove(hi, do_unlink=True)
    a = np.empty(4096 * 4096 * 4, np.float32); bake_img.pixels.foreach_get(a); a = a.reshape(-1, 4)[:, :3]
    used = a[np.abs(a - [0.5, 0.5, 1.0]).sum(1) > 0.02]
    check(len(used) > 0.05 * len(a) and used[:, 2].mean() > 0.8, "구운 몸 노멀맵: 평평하지 않은 픽셀 %.0f %% (> 5), 그 파랑 평균 %.2f (> 0.8 — 광선이 제 면을 맞혔다)" % (100 * len(used) / len(a), used[:, 2].mean() if len(used) else 0))

# ---- 검사
B, H, D = co(body), co(head), co(hand)
check(B[:, 2].max() <= NECK_CUT + 0.005 and abs(H[:, 2].min() - (NECK_CUT - 0.02)) < 0.01 and abs(H[:, 2].max() - M2_TOP) < 0.005,
      "머리 그물이 몸 목 위에 얹힘: 몸 꼭대기 %.3f ≤ %.3f · 머리 %.3f ~ %.3f" % (B[:, 2].max(), NECK_CUT, H[:, 2].min(), H[:, 2].max()))
neck_b = B[B[:, 2] > NECK_CUT - 0.01]; neck_h = H[H[:, 2] < NECK_CUT]
off = np.linalg.norm(((neck_b.min(0) + neck_b.max(0)) / 2 - (neck_h.min(0) + neck_h.max(0)) / 2)[:2])
check(off <= 0.03, "목 이음매 가운데 어긋남 %.3f m (≤ 0.03)" % off)
check(abs(B[:, 0]).max() <= WRIST_X + 0.005 and abs(D[:, 0]).min() >= WRIST_X - 0.02, "손 그물이 손목에서 이어짐: 몸 |x| 끝 %.3f · 손 시작 %.3f" % (abs(B[:, 0]).max(), abs(D[:, 0]).min()))
tip = abs(D[:, 0]).max()
check(0.90 <= tip <= 1.02, "손끝 |x| %.3f (m2 0.95 ± 0.06 — 손 크기가 맞다)" % tip)
faces = {o.name: len(o.data.polygons) for o in (body, head, hand, torso, liner)}
print("faces", faces, "sum", sum(faces.values()))
if fails:
    sys.exit("m3_assemble FAIL %d — 안 내보냄: %s" % (len(fails), fails))
for m_ in bpy.data.materials:
    m_.use_backface_culling = True               # Meshy GLB 는 양면으로 들어온다 — 그대로 두면 Unity 에서 피부 뒷면이 새까맣게 보인다(안감 그물이 그 일을 한다)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True, export_image_format="AUTO")
print("m3_assemble ALL PASS →", OUT, round(os.path.getsize(OUT) / 1e6, 1), "MB")
