"""add_jaw — 괴물 리그에 턱 뼈를 더한다 (제안서 docs/제안서_3D3b_M1c_턱_뼈.md, 승인 2026-09-19).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/add_jaw.py
입력: Documents/MineTunnel/blender/miner_v4_stage12.blend — 안 고친다
출력: Documents/MineTunnel/blender/miner_v4_stage13_jaw.blend (저장소 밖) → blender/anim/walk_knuckle.py 가 이것을 읽어 GLB 를 굽는다
하는 일: ① 뼈 mixamorig:Jaw(부모 Head, 머리 = 턱 관절, 귀 앞) + mixamorig:JawTip(부모 Jaw, 턱 끝 — 살 없음, Unity 검사가 턱 끝 자리를 본다)
        ② 머리 살(Miner_Head)에서 입꼬리 선 → 턱 관절로 오르는 면 아래 살을 Head 무게에서 Jaw 무게로 옮긴다(경계 1.2 cm 섞음, 합은 그대로)
        ③ 자기 검사: 뼈 수 · 무게 합 · 0° 모양 그대로 · 벌렸을 때 턱 살이 따라 내려감 · 살 늘어남
목 끈(Strap_Neck)이 쉴 때도 턱 끝을 감싸고 있어 8° 넘게 벌리면 옆·3/4 에서 턱 끝이 끈 속·아래로 들어간다(09-19 실측).
사용자 결정(09-19): 포효·잡기 땐 괴물이 나를 보고 있으니 정면 기준으로 크게 벌린다 — 옆 모습은 받아들이고 실행 파일 판정에서 다시 본다
턱은 동작 파일에 키로 굽지 않는다 — Unity StalkerAnim 이 동작 이름을 보고 돌린다. 벌림 = 좌우 축(모델 X) 둘레로 턱 끝이 아래로,
30° 를 넘는 만큼 앞으로 미끄러짐(Tuning.STALKER_JAW_SLIDE_FROM_DEG · STALKER_JAW_SLIDE_PER_DEG 와 같은 값)
사보타주: SABOTAGE=noweight -> 살을 턱 뼈로 안 옮긴다 (검사 "턱 살이 따라 내려감" FAIL). 사보타주 실행은 blend 를 저장하지 않는다"""
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.path.join(MT, "blender", "miner_v4_stage12.blend")
OUT = os.path.join(MT, "blender", "miner_v4_stage13_jaw.blend")
SABOTAGE = os.environ.get("SABOTAGE", "")

# 모델 크기 1 기준 m (게임 1.5 배). 입 틈 = 가운데 줄 높이 2.12~2.14, 윗니 2.15 부터 (09-19 실측)
PIV = Vector((0.0, 0.01, 2.165))       # 턱 관절: 귀 앞, 윗니 높이 뒤쪽
LIP = (-0.12, 2.13)                    # 입꼬리 선 (y, z): 이 앞은 이 높이 아래가 턱
BLEND = 0.012                          # 턱/머리 경계 섞는 폭
BACK = 0.03                            # 관절에서 뒤로 이만큼부터 턱 무게 0 (2 cm 에 걸쳐 줄어든다)
FLOOR_Z = 2.0                          # 이 높이(목)부터 3 cm 에 걸쳐 턱 무게가 는다
WIDE_DEG = 40.0                        # 검사할 가장 큰 벌림 (Tuning.STALKER_JAW_WIDE_DEG 제안값)
SLIDE_FROM, SLIDE_PER_DEG = 30.0, 0.0015
FOLLOW_MAX = 0.005                     # 턱에만 붙은 살 점(무게 ≥ 0.99)이 턱 뼈를 그대로 따라간 자리에서 벗어난 평균 거리 상한
# 살 늘어남 배율은 검사하지 않고 적기만 한다: 입꼬리는 윗입술·아랫입술을 잇는 변이라 벌리면 늘어나는 게 맞다(0.5 → 3.9 cm at 40°).
# 찢어져 보이는지는 사람 판정(확인 목록)

fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
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

def eval_co(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh(); co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    return (np.array(o.matrix_world) @ np.c_[co, np.ones(len(co))].T).T[:, :3]

skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
before = {o.name: eval_co(o) for o in skinned}
n_bones0 = len(arm.data.bones)

# ---- ② 무게 계산 (쉬는 자세 세상 좌표)
head = bpy.data.objects["Miner_Head"]
co = before["Miner_Head"]
hg = head.vertex_groups["mixamorig:Head"]
hw = np.zeros(len(co))
for v in head.data.vertices:
    for g in v.groups:
        if g.group == hg.index:
            hw[v.index] = g.weight
slope = (PIV.z - LIP[1]) / (PIV.y - LIP[0])
plane = np.where(co[:, 1] < LIP[0], LIP[1], LIP[1] + (co[:, 1] - LIP[0]) * slope)
jw = (np.clip((plane - co[:, 2]) / BLEND + 0.5, 0, 1) * np.clip((PIV.y + BACK - co[:, 1]) / 0.02, 0, 1)
      * np.clip((co[:, 2] - FLOOR_Z) / 0.03, 0, 1) * hw)
chin_pts = co[(jw > 0.5) & (np.abs(co[:, 0]) < 0.02)]
chin = Vector(chin_pts[np.argmin(chin_pts[:, 2] + 0.5 * chin_pts[:, 1])])   # 가장 낮고 앞인 점
print("jaw verts > 0.5: %d · chin %s" % (int((jw > 0.5).sum()), tuple(round(x, 3) for x in chin)))

# ---- ① 뼈
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects:
    o.select_set(o == arm)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
jaw = eb.new("mixamorig:Jaw"); jaw.head = Mi @ PIV; jaw.tail = Mi @ chin; jaw.roll = 0.0
jaw.parent = eb["mixamorig:Head"]; jaw.use_deform = True
tip = eb.new("mixamorig:JawTip"); tip.head = Mi @ chin; tip.tail = Mi @ (chin + (chin - PIV).normalized() * 0.03); tip.roll = 0.0
tip.parent = jaw; tip.use_connect = True; tip.use_deform = False
bpy.ops.object.mode_set(mode="POSE")
reset_pose()

gj = head.vertex_groups.new(name="mixamorig:Jaw")
for i in (np.nonzero(jw > 1e-4)[0] if SABOTAGE != "noweight" else []):
    i = int(i)
    gj.add([i], float(jw[i]), "REPLACE")
    hg.add([i], float(hw[i] - jw[i]), "REPLACE")

# ---- ③ 검사
check(len(arm.data.bones) == n_bones0 + 2 == 67, "뼈 %d → %d (67)" % (n_bones0, len(arm.data.bones)))
check(arm.data.bones["mixamorig:Jaw"].parent.name == "mixamorig:Head" and arm.data.bones["mixamorig:JawTip"].parent.name == "mixamorig:Jaw",
      "Jaw 부모 = Head, JawTip 부모 = Jaw")
hw2 = np.zeros(len(co)); jw2 = np.zeros(len(co))
for v in head.data.vertices:
    for g in v.groups:
        if g.group == hg.index: hw2[v.index] = g.weight
        if g.group == gj.index: jw2[v.index] = g.weight
jw2_plan = jw if SABOTAGE == "noweight" else jw2      # noweight: 무게 검사는 계획한 무게로 (살 따라감 검사가 잡아야 한다)
check(float(np.abs(hw2 + jw2 - hw).max()) < 1e-3, "점마다 머리 + 턱 무게 합 = 옮기기 전 머리 무게 (차 최대 %.5f)" % float(np.abs(hw2 + jw2 - hw).max()))
others = [o.name for o in skinned if o != head and "mixamorig:Jaw" in o.vertex_groups]
check(not others, "턱 무게는 머리 살에만 %s" % others)
after = {o.name: eval_co(o) for o in skinned}
d0 = max(float(np.abs(after[n] - before[n]).max()) for n in before)
check(d0 < 1e-4, "0° 에서 살 점 위치 그대로 (최대 차 %.6f m < 0.0001)" % d0)

pj = arm.pose.bones["mixamorig:Jaw"]
def open_jaw(deg):
    reset_pose()
    slide = SLIDE_PER_DEG * max(0.0, deg - SLIDE_FROM)
    W = M @ pj.matrix
    R = Matrix.Translation(Vector((0, -slide, 0))) @ Matrix.Translation(PIV) @ Matrix.Rotation(math.radians(deg), 4, "X") @ Matrix.Translation(-PIV)
    pj.matrix = Mi @ (R @ W)
    bpy.context.view_layer.update()
    return slide

full_idx = np.nonzero(jw2_plan >= 0.99)[0]
edges = np.array([tuple(e.vertices) for e in head.data.edges])
mix = edges[np.abs(jw2_plan[edges[:, 0]] - jw2_plan[edges[:, 1]]) > 0.3]
len0 = np.linalg.norm(co[mix[:, 0]] - co[mix[:, 1]], axis=1)
keep = len0 >= 0.005
mix, len0 = mix[keep], len0[keep]
for deg in (20.0, WIDE_DEG):
    slide = open_jaw(deg)
    c = eval_co(head)
    tipz = (M @ arm.pose.bones["mixamorig:JawTip"].head).z
    check(tipz < chin.z - 0.02, "%.0f°: 턱 끝 뼈가 내려감 (%.3f < 쉴 때 %.3f − 0.02, 앞 미끄러짐 %.1f cm)" % (deg, tipz, chin.z, slide * 100))
    Rj = np.array(M @ pj.matrix @ (M @ arm.data.bones["mixamorig:Jaw"].matrix_local).inverted())   # 쉬는 자리 → 지금 자리
    want = (Rj @ np.c_[co[full_idx], np.ones(len(full_idx))].T).T[:, :3]
    err = float(np.linalg.norm(c[full_idx] - want, axis=1).mean()); move = float(np.linalg.norm(want - co[full_idx], axis=1).mean())
    check(err <= FOLLOW_MAX and move > 0.01, "%.0f°: 턱에만 붙은 살 점 %d 개가 턱 뼈를 따라감 (벗어남 평균 %.4f m ≤ %.3f, 움직임 평균 %.1f cm)" % (deg, len(full_idx), err, FOLLOW_MAX, move * 100))
    ln = np.linalg.norm(c[mix[:, 0]] - c[mix[:, 1]], axis=1)
    t = int(np.argmax(ln / len0))
    print("적기 %.0f°: 턱·머리 경계 변 %d 개(5 mm 이상) 가장 많이 늘어난 배율 %.2f (%.1f → %.1f cm)" % (deg, len(ln), ln[t] / len0[t], len0[t] * 100, ln[t] * 100))
reset_pose()

if SABOTAGE:
    print("add_jaw SABOTAGE=%s %s fails=%d (저장 안 함)" % (SABOTAGE, "ALL PASS" if not fails else "FAIL", len(fails)))
    sys.exit(0 if not fails else 2)
if fails:
    print("add_jaw FAIL fails=%d %s (저장 안 함)" % (len(fails), fails))
    sys.exit(2)
bpy.ops.object.mode_set(mode="OBJECT")
for tr in ad.nla_tracks:
    tr.mute = False
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
print("add_jaw ALL PASS")
