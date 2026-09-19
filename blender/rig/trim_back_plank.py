"""trim_back_plank — 등 판자 위쪽을 자르고 못 5개를 남은 판자 위로 옮긴다 (사용자 09-19: 머리를 뒤로 돌리면 판자 끝·못이 머리와 겹친다).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/trim_back_plank.py
입력: Documents/MineTunnel/blender/miner_v4_stage13_jaw.blend (blender/rig/add_jaw.py 산출물) — 안 고친다
출력: Documents/MineTunnel/blender/miner_v4_stage14_plank.blend → blender/anim/walk_knuckle.py 가 이것을 읽어 GLB 를 굽는다
하는 일: ① Plank_Back(허리 1.26 → 목 뒤 2.29 m 대각선) 윗끝을 판자 방향을 따라 TOP 높이까지 끌어내린다 (쉬는 자세, 모델 크기 1)
        ② Nail_0~4(목 뒤 1.89~2.13 m 에 박혀 있던 것)를 남은 판자 가운데 줄 위로 옮긴다 — 판자를 등에 박은 못. 방향은 그대로
        ③ 자기 검사: 머리를 좌우 90·135·180° + 갸웃 0·±110° 로 돌려도(Unity StalkerAnim 과 같은 목 40 % · 머리 60 %) 머리 살 점이 판자·못 상자 안에 0 개
사보타주: SABOTAGE=untrimmed -> 자르지도 옮기지도 않는다 (검사 "머리가 판자·못과 안 겹침" FAIL). 사보타주 실행은 blend 를 저장하지 않는다"""
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.path.join(MT, "blender", "miner_v4_stage13_jaw.blend")
OUT = os.path.join(MT, "blender", "miner_v4_stage14_plank.blend")
SABOTAGE = os.environ.get("SABOTAGE", "")
TOP = 1.72                               # 판자 윗끝 높이 (머리 뿌리 2.06 m 아래. 1.80 은 갸웃 110° + 좌우 135° 에서 머리가 판자 끝에 닿았다, 09-19)
NAIL_Z = (1.33, 1.60)                    # 못을 박을 판자 구간 (아래 → 위, 5 개 고르게)
NECK_SHARE = 0.4                         # Tuning.STALKER_HEAD_NECK_SHARE

fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
arm = bpy.data.objects["Miner_Rig"]
M, Mi = arm.matrix_world.copy(), arm.matrix_world.inverted()
ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
ad.action = None
arm.data.pose_position = "POSE"
def reset_pose():
    for p in arm.pose.bones:
        p.rotation_mode = "QUATERNION"; p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0); p.scale = (1, 1, 1)
    bpy.context.view_layer.update()
reset_pose()

plank = bpy.data.objects["Plank_Back"]
nails = [bpy.data.objects["Nail_%d" % i] for i in range(5)]
mw = plank.matrix_world.copy(); mwi = mw.inverted()
ax = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()          # 판자 길이 방향 (위로)
if ax.z < 0:
    ax = -ax
ws = [mw @ v.co for v in plank.data.vertices]
print("plank z %.3f ~ %.3f" % (min(w.z for w in ws), max(w.z for w in ws)))

if SABOTAGE != "untrimmed":
    # ① 윗끝을 판자 방향을 따라 TOP 까지
    for v, w in zip(plank.data.vertices, ws):
        if w.z > TOP:
            v.co = mwi @ (w - ax * ((w.z - TOP) / ax.z))
    plank.data.update()
    # ② 판자 바깥 면(등에서 먼 쪽 = +y) 가운데 줄 위 높이 z 인 점
    bpy.context.view_layer.update()
    ws2 = np.array([plank.matrix_world @ v.co for v in plank.data.vertices])
    outer_y = ws2[:, 1].max()
    lo = Vector(ws2[np.argmin(ws2[:, 2])]); c0 = Vector(ws2.mean(0))
    def on_plank(z):
        p = c0 + ax * ((z - c0.z) / ax.z)
        return Vector((p.x, outer_y, z))
    for i, n in enumerate(nails):
        nb = np.array([n.matrix_world @ Vector(c) for c in n.bound_box])
        base = Vector((nb[:, 0].mean(), nb[:, 1].min(), nb[:, 2][np.argmin(nb[:, 1])]))   # 몸 쪽 끝 (박힌 쪽)
        z = NAIL_Z[0] + (NAIL_Z[1] - NAIL_Z[0]) * i / (len(nails) - 1)
        tgt = on_plank(z) - Vector((0, 0.02, 0))                                            # 2 cm 박힘 (stage11 과 같이)
        n.matrix_world = Matrix.Translation(tgt - base) @ n.matrix_world
    bpy.context.view_layer.update()

# ---- ③ 검사
ws3 = np.array([plank.matrix_world @ v.co for v in plank.data.vertices])
check(ws3[:, 2].max() <= TOP + 1e-3 or SABOTAGE, "판자 윗끝 %.3f m ≤ %.2f (길이 %.2f m 남음)" % (ws3[:, 2].max(), TOP, float(np.linalg.norm(ws3.max(0) - ws3.min(0)))))
if not SABOTAGE:
    for n in nails:
        nb = np.array([n.matrix_world @ Vector(c) for c in n.bound_box])
        L = np.array(plank.matrix_world.inverted()) @ np.c_[nb, np.ones(8)].T
        lo_, hi_ = np.array([min(c[k] for c in plank.bound_box) for k in range(3)]), np.array([max(c[k] for c in plank.bound_box) for k in range(3)])
        touching = int(np.all((L[:3].T >= lo_ - 0.02) & (L[:3].T <= hi_ + 0.02), axis=1).sum())
        check(touching >= 1 and nb[:, 2].max() < TOP, "%s 가 판자에 박힘 (판자 상자 2 cm 안 꼭짓점 %d 개, 가장 높은 곳 %.3f m < %.2f)" % (n.name, touching, nb[:, 2].max(), TOP))

head = bpy.data.objects["Miner_Head"]
hg = head.vertex_groups["mixamorig:Head"].index
hidx = np.array([v.index for v in head.data.vertices if any(g.group == hg and g.weight > 0.5 for g in v.groups)])
def eval_co(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh(); co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    return (np.array(o.matrix_world) @ np.c_[co, np.ones(len(co))].T).T[:, :3]
def inside(obj, pts):
    L = np.array(obj.matrix_world.inverted()) @ np.c_[pts, np.ones(len(pts))].T
    lo_, hi_ = np.array([min(c[k] for c in obj.bound_box) for k in range(3)]), np.array([max(c[k] for c in obj.bound_box) for k in range(3)])
    return int(np.all((L[:3].T >= lo_) & (L[:3].T <= hi_), axis=1).sum())
def rot(n, R):
    pb = arm.pose.bones["mixamorig:" + n]; W = M @ pb.matrix; h = W.translation
    pb.matrix = Mi @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W)
    bpy.context.view_layer.update()
worst = []
for yaw in (90, 135, 180, -90, -135):
    for tilt in (0, 110, -110):
        reset_pose()
        for b, k in (("Neck", NECK_SHARE), ("Head", 1 - NECK_SHARE)):
            fwd = Matrix.Rotation(math.radians(yaw * k), 3, "Z") @ Vector((0, -1, 0))     # 돌린 뒤 얼굴 축 (모델 앞 = −Y)
            rot(b, Matrix.Rotation(math.radians(tilt * k), 4, fwd) @ Matrix.Rotation(math.radians(yaw * k), 4, "Z"))
        pts = eval_co(head)[hidx]
        n_in = inside(plank, pts) + sum(inside(n, pts) for n in nails)
        worst.append((n_in, yaw, tilt))
reset_pose()
bad = [w for w in worst if w[0] > 0]
check(not bad, "머리가 판자·못과 안 겹침: 좌우 ±90·±135·180° × 갸웃 0·±110° 15 가지 중 겹친 것 %d %s (머리 살 점 %d 개)" % (len(bad), bad[:5], len(hidx)))

if SABOTAGE:
    print("trim_back_plank SABOTAGE=%s %s fails=%d (저장 안 함)" % (SABOTAGE, "ALL PASS" if not fails else "FAIL", len(fails)))
    sys.exit(0 if not fails else 2)
if fails:
    print("trim_back_plank FAIL fails=%d (저장 안 함)" % len(fails))
    sys.exit(2)
for tr in ad.nla_tracks:
    tr.mute = False
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
print("trim_back_plank ALL PASS")
