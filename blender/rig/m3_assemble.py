"""m3 = Meshy 부위 조립 (2026-09-20): 몸 m2 + 따로 뽑은 머리 head1 + 따로 뽑은 손 hand1(좌우 거울). 옛 몸(4b·4c)과 같은 방식.
  blender -b --factory-startup -P blender/rig/m3_assemble.py
까닭: 전신 그림에서는 머리가 60 픽셀쯤이라 어떤 생성기든 머리·손이 뭉개진다 — 클로즈업 그림으로 따로 뽑아 붙인다.
입력: Documents/MineTunnel/mesh/meshy_{m2,head1,hand1}.glb (gen_meshy.py)   출력: mesh/meshy_m3.glb (m2 좌표 그대로, 그물 셋 — glTFast 는 스킨 그물 하나에 재질 둘을 못 읽는다)
숫자는 probe 로 잰 것: 헬멧 챙 너비 m2 0.206 / head1 0.486, m2 손목 x 0.64 · 손끝 0.95, hand1 은 길이 축 y(손목 +0.70 → 발톱 끝 −0.95)
사보타주: SABOTAGE=nohead -> "머리 그물이 몸 목 위에 얹힘" FAIL"""
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
def cut(o, point, normal):
    """normal 쪽을 버린다"""
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=point, plane_no=normal, clear_outer=True, use_fill=False)
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
cut(body, (WRIST_X, 0, 0), (1, 0, 0)); cut(body, (-WRIST_X, 0, 0), (-1, 0, 0))
bpy.ops.object.select_all(action="DESELECT"); hand.select_set(True); right.select_set(True); bpy.context.view_layer.objects.active = hand
bpy.ops.object.join()

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
faces = {o.name: len(o.data.polygons) for o in (body, head, hand)}
print("faces", faces, "sum", sum(faces.values()))
if fails:
    sys.exit("m3_assemble FAIL %d — 안 내보냄: %s" % (len(fails), fails))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True, export_image_format="AUTO")
print("m3_assemble ALL PASS →", OUT, round(os.path.getsize(OUT) / 1e6, 1), "MB")
