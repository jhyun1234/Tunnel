"""서서 오는 괴물 — 영상 시험 (기준 괴물 A1 제노모프 + A4 관리인, 사용자 결정 2026-09-19: "서서 오는 것으로 바꿔도 된다").
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/anim/preview_upright.py
밑그림 = 이미 받아 둔 Mixamo "Mutant" 묶음(사람이 괴물을 연기한 모션캡처 — 수식이 아니라 기계 티가 없다). 이 뼈대가 Mixamo 뼈대라 옮겨 붙이기 없이 그대로 얹힌다.

U1 판정(09-19): 방향은 맞다 / 두 다리 걸음이 안 무섭다 · 무게가 없다 · 머리 훑기가 "찾고 있다"로 안 읽힌다 · 굳으면 영상이 멈춘 줄 안다 · 걸음·휘두르기가 사람 같다.
그래서 모션캡처 위에 얹는 것 (에일리언 아이솔레이션은 **보기만** 했다 — 문으로 들어오는 한 장면: 몸통을 앞으로 깊이 숙이고, 머리를 앞으로 빼고, 팔은 안 흔들고 앞·아래로 늘어뜨리고, 무릎을 깊이 굽혀 크게 딛는다. 동작 데이터는 안 가져온다):
  · 사람 티의 뿌리 = 팔 흔들기 → 팔 뼈를 그 동작의 평균 자세 쪽으로 ARM_STILL 만큼 당겨 흔들림을 죽인다
  · 몸통을 HUNCH 도 앞으로 숙이고 머리는 되세워 앞을 본다 (숙인 몸통에 달린 팔이 저절로 앞·아래로 늘어진다)
  · 엉덩이를 CROUCH m 낮춘다 — 발은 원래 모션캡처 자리에 IK 로 붙들어 무릎이 더 굽는다
  · 무게: 느린 박자(WALK_RATE) + 발 디딜 때마다 엉덩이가 덜컥 내려앉음 + 화면 흔들림
  · 찾기: 매끄럽게 훑지 않는다. 걷다 **서서** 머리를 0.15 s 에 딱 돌리고 멈춰 본다(조사: 새·올빼미), 간격은 고르지 않게
  · 굳음: 화면은 살아 있고(손에 든 카메라처럼 숨결 흔들림) 괴물만 돌이 된다 — 그동안 턱이 천천히 벌어진다
  · 휘두르기 없음: 굳음에서 바로 질주해 턱을 벌린 채 화면으로 들어온다 → 검은 화면
입력(안 고친다): Documents/MineTunnel/blender/miner_v4_stage16_neck.blend · blender/mixamo/*.fbx (원본 FBX 는 저장소에 안 올린다)
수색 장면 (3D-④ MB, 제안서 docs/제안서_3D4_MB_수색_더듬어_찾기.md 물음 1~3 승인 2026-09-20): UP_NAME 이 B 로 시작하면(UP_NAME=B1) 추격 대신 —
  램프 끈 플레이어 눈높이, 괴물이 수색 걸음(2.5 m/s)으로 4 m 앞까지 오며 몸을 벽 쪽으로 50° 튼다 → 머리를 딱딱 → 목을 1.0 s 에 25 cm(모델 m, Tuning 목 값과 같은 단위) 천천히 내민다
  → 더듬기 → 쓸다 말고 **머리만 0.2 s 에 나를 딱 돌아보며 갸웃, 통째로 2.0 s 멈춤** → 머리가 천천히 돌아가고 마저 쓴다 → 일어서서 나를 딱 본다.
  B1 판정(09-20): 손가락이 간지럽히는 것 같다 · 팔이 기계 같다(→ 약속대로 자세 열쇠 + 팔 IK 를 버림) · "찾고 있다"는 읽히나 "들었나?"는 안 읽힌다. 그래서 B2:
  · 팔 = 수식·IK 없음. 받아 둔 모션캡처 "zombie attack"(사람이 연기한 한 팔 뻗어 휘젓기)을 0.3배쯤으로, 빠르기를 고르지 않게 다시 재생해 선 몸에 온몸째 섞는다(0.5 s 에 걸쳐). 손이 면에 붙지는 않는다 — 허공·벽 높이를 휘젓는다
  · 손가락 = 두드리기 없음. 벌려 세운 갈고리 손이 아주 느리게만 움직인다
  · "들었나?" = 멈추기 직전 화면이 덜컥(내가 소리를 냄) → 몸은 그대로 굳고 머리만 나를 향해 딱 + 갸웃 → 긴 정지
  B2 판정(09-20): "들었나?" 통과 / 팔이 "더듬는다"로 안 읽힌다(앞으로 쭉 뻗은 모양일 뿐) · 바닥을 짚을 때는 손가락이 전부 펴졌으면. 그래서 B3:
  · 더듬기 = **바닥을 여기저기 짚어 본다**: 깊이 웅크려 두 손이 번갈아 — 들어서 옮기고(0.45~0.9 s) → 손가락을 쫙 펴 벌린 손바닥으로 짚고 → 짚은 채 조금 문지르고(0.5~1.4 s) → 다른 자리로. 자리·길이는 고르지 않게(씨앗 고정 난수)
  · 짚으려면 손이 바닥에 닿아야 해서 손목 과녁 IK 가 돌아왔다(B1 에서 버린 것 — 이번엔 고른 빠르기의 호가 아니라 짚는 자리 놓기용). 허리·어깨의 흔들림은 B2 의 모션캡처 그대로, 팔이 곧게 뻗어 뻣뻣해지지 않게 과녁을 팔 길이 94 % 안으로 당긴다
  B3 판정(09-20): 편 손가락 통과 / "더듬는다"로는 읽히나 "탁자 밑·갱도에 숨죽이고 앉은 나를 찾는 중"으로는 안 읽힌다 · 팔을 더 멀리 다양하게. 그래서 B4:
  · 시점 = **탁자 밑에 숨은 나**(눈높이 0.9 m, 탁자 상판이 화면 위를 가린다). 괴물은 3.5 m 앞에 서서 — 벽을 짚고 · 바닥을 멀리 짚고 → 탁자 쪽으로 몸을 돌려 **고개를 낮춰 탁자 밑을 들여다보고** → 탁자 위를 짚고 → 손을 탁자 밑으로 넣어 **짚을 때마다 내 쪽으로 더 깊이** → 가장 가까이 짚은 순간 "들었나?"(덜컥 → 머리만 나를 향해 딱 들림 + 갸웃 → 2.0 s) → 천천히 손을 거두고 일어나 고개를 돌린다
  · 더 멀리 = 짚는 두 손의 가운데 쪽으로 엉덩이가 0.4 m 까지 실린다(발은 제자리). 다양하게 = 바닥·벽·탁자 위, 짚는 자리는 짜 둔 차례(길이만 난수)
  자기 검사: 얹은 머리·손이 렌더 재계산에 살아남나 · 짚는 동안 네 손가락 끝이 다 바닥에 닿나 · 손가락이 곧게 펴졌나 · 손끝이 몸 앞으로 나가나 · 손이 바닥·벽을 안 뚫나 · 머리가 0.2 s 에 40° 넘게 도나 · 긴 정지 동안 뼈 움직임 0.
  사보타주: SABOTAGE=nofreeze(U2 버그) · nogrope(모션캡처 안 섞음) · nohold(정지 중에도 시간이 흐름) · curled(짚을 때 손가락을 안 편다) → 저마다 FAIL 로 죽는다.
도망 장면 (3D-④ MR1 R1, 제안서 docs/제안서_3D4_MR1_도망_구멍.md 승인 2026-09-20 — 벽 틈 먼저 · 새 클립 없이): UP_NAME 이 R 로 시작하면(UP_NAME=R1) —
  램프 켠 내 눈높이. 2.5 m 앞의 괴물을 내가 쳤다(덜컥) → 0.2 s 에 1 m 밀려 굳어서 나를 본다 0.5 s → 나를 본 채 뒷걸음 3 m(걷기 거꾸로) → 돌아서 4.0 m/s 로 9 m 앞 오른쪽 벽의 **큰 벽 틈**(게임 폭 1.2 · 높이 2.2 · 깊이 2.5 m, 안으로 0.5 m 까지 좁아짐)으로
  → 틈 앞에서 멈칫, 머리만 나를 딱 돌아봄 → 몸을 낮춰 걸어 들어가며 왼손이 틈 가장자리 벽을 쥔다 → 몸이 다 들어간 뒤에도 **손 하나가 0.45 s 남았다가** 끌려 들어감 → 빈 틈 1.5 s
  → 나오기: 손가락이 먼저 가장자리를 쥠(0.8 s 손만) → 목을 빼 머리가 나와 딱 — 딱 → 걸어 나와 서서 나를 딱 보고 굳음.
  R4(09-20): 들어갈 때도 두 손으로 옆면을 쥐고 어깨를 한쪽씩 비집어 넣는다 (SABOTAGE=r3 = 그냥 달려 들어가기 · r2 = Mixamo 두 클립, 비교용)
  자기 검사: 뼈가 틈 밖의 바위 속에 들어간 프레임 0 · 머리가 틈 천장 밑 · 남은 손이 과녁(가장자리)에서 0.15 m 안. 사보타주: SABOTAGE=miss(길이 틈을 0.6 m 빗나감) → FAIL.
출력: build/check_3d4/UP_<이름>.mp4. GLB·게임은 안 건드린다. 고르기용 영상이다 — 통과 판정은 배포 실행 파일에서."""
import bpy, os, sys, math, shutil, subprocess
from mathutils import Vector, Quaternion, Matrix

E = os.environ.get
HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
MIX = os.path.join(MT, "blender", "mixamo")
NAME = E("UP_NAME", "U4")
SEARCH = NAME.startswith("B")             # 수색 장면 (MB)
RETREAT = NAME.startswith("R")            # 도망 장면 (MR1 R1)
SAB = E("SABOTAGE", "")
CLOSE = E("UP_CAM") == "close"           # 손가락·팔을 보려고: 괴물 2 m 앞에서 뒷걸음치며 따라가는 카메라 (게임 시점 아님)
STEP = int(E("UP_STEP", "1"))             # 빠른 확인: N 프레임마다 한 장만 굽고 영상은 안 만든다
WALK, RUN = E("UP_WALK", "Mutant Walking"), E("UP_RUN", "Mutant Run")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "check_3d4"); os.makedirs(OUT_DIR, exist_ok=True)
FR_DIR = os.path.join(MT, "blender", "anim_render", "up_" + NAME); shutil.rmtree(FR_DIR, ignore_errors=True); os.makedirs(FR_DIR)
FPS, S = 30, 1.5
START, EYE, WALL_X, CEIL = float(E("UP_START_M", "9")) / S, 1.7 / S, 3.16 / S, 5.6 / S
HUNCH, CROUCH, ARM_STILL = float(E("UP_HUNCH", "42")), float(E("UP_CROUCH", "0.16")), float(E("UP_ARM_STILL", "0.85"))
WALK_RATE, RUN_GAME = float(E("UP_WALK_RATE", "0.72")), float(E("UP_RUN_MS", "6.5"))
SEARCH_MS, STOP_M = 2.5, float(E("UP_STOP_M", "3.5"))               # 수색 걸음(게임 m/s) · 플레이어 앞 멈추는 거리(게임 m)
CX = float(E("UP_CX", "0.5")) if SEARCH else 0.0       # 수색: 괴물이 갱도 가운데서 조금 왼쪽(화면 오른쪽)으로 온다
YAW, TILT = float(E("UP_YAW", "25")), 18.0             # 수색: 몸을 벽 쪽으로 트는 각 (나를 돌아보는 머리가 크게 돌아야 읽힌다) · 들었을 때 갸웃
HUNCH_CUT = float(E("UP_HUNCH_CUT", "0.35"))           # 더듬는 모션캡처는 제 스스로 숙이고 있다 — 우리 숙임을 이만큼 덜어야 손이 바닥을 안 뚫는다
GROPE, GROPE_RATE, HEAR_AT = E("UP_GROPE", "Creeping Zombie Walk"), float(E("UP_GROPE_RATE", "0.40")), float(E("UP_HEAR_AT", "0.3"))
NECK_OUT, NECK_S = float(E("UP_NECK", "0.25")), 1.0    # 목 내밀기 (모델 m) · 나오는 데 걸리는 초
DIP = float(E("UP_DIP", "0.05"))           # 발 디딜 때 엉덩이가 내려앉는 깊이 (모델 m)
JAW_FREEZE, JAW_RUN = 22.0, 40.0

bpy.ops.wm.open_mainfile(filepath=E("UP_BLEND", os.path.join(MT, "blender", "miner_v4_stage16_neck.blend")))   # UP_BLEND: 다른 몸(새 몸 m3 = miner_v5_stage22_m3_props.blend)으로 같은 동작을 굽는다 — 쇼츠 비교용(09-22)
scene = bpy.context.scene; scene.render.fps = FPS
arm = bpy.data.objects["Miner_Rig"]; ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
P = "mixamorig:"; pbs = arm.pose.bones
M, Mi = arm.matrix_world.copy(), arm.matrix_world.inverted()
def pb(n): return pbs[P + n]
def upd(): bpy.context.view_layer.update()
def fcurves_of(act):
    return [fc for layer in act.layers for strip in layer.strips for cb in strip.channelbags for fc in cb.fcurves]
def use(act, f):
    ad.action = act
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    scene.frame_set(int(f), subframe=f - int(f)); upd()
def rotate_world(n, R):
    W = M @ pb(n).matrix; h = W.translation
    pb(n).matrix = Mi @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W); upd()

ARMS = [s + b for s in ("Left", "Right") for b in ("Shoulder", "Arm", "ForeArm", "Hand")]
def load(stem):
    """FBX 의 동작만. 제자리 걸음으로 만들고(엉덩이의 곧은 흐름만 뺀다) 원래 빠르기(모델 m/s)와 팔 뼈의 평균 자세를 돌려준다"""
    before_o, before_a = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MIX, stem + ".fbx"))
    act = next(a for a in bpy.data.actions if a not in before_a)
    for o in [o for o in bpy.data.objects if o not in before_o]:
        bpy.data.objects.remove(o, do_unlink=True)
    f0, f1 = act.frame_range
    use(act, f0); p0 = (M @ pb("Hips").matrix).translation.copy()
    use(act, f1); p1 = (M @ pb("Hips").matrix).translation.copy()
    for fc in fcurves_of(act):
        if fc.data_path.endswith('["%sHips"].location' % P) and len(fc.keyframe_points) > 1:
            k0, k1 = fc.keyframe_points[0], fc.keyframe_points[-1]
            slope = (k1.co.y - k0.co.y) / max(k1.co.x - k0.co.x, 1e-6)
            for k in fc.keyframe_points:
                k.co.y -= slope * (k.co.x - k0.co.x)
            fc.update()
    mean = {}
    for f in range(int(f0), int(f1)):
        use(act, f)
        for n in ARMS:
            q = pb(n).rotation_quaternion.copy()
            if n in mean and mean[n].dot(q) < 0: q.negate()
            mean[n] = q if n not in mean else Quaternion([a + b for a, b in zip(mean[n], q)])
    for n in mean: mean[n].normalize()
    speed = math.hypot(p1.x - p0.x, p1.y - p0.y) / ((f1 - f0) / FPS)
    print("CLIP %s: %d frames, %.2f m/s (game %.2f)" % (stem, f1 - f0, speed, speed * S))
    return act, speed, mean
walk, v_walk, mean_walk = load(WALK); run, v_run, mean_run = load(RUN)
grope_act = load(GROPE)[0] if SEARCH else None

# ---- 다리 IK: 발목은 원래 모션캡처 자리에 붙든 채 엉덩이만 낮춘다
col = bpy.data.collections.new("up_rig"); scene.collection.children.link(col)
tg = {}
for s in ("Left", "Right"):
    e = bpy.data.objects.new("tg_" + s, None); e.rotation_mode = "QUATERNION"; col.objects.link(e); tg[s] = e
    c = pb(s + "Leg").constraints.new("IK"); c.target = e; c.chain_count = 2; c.use_tail = True; c.name = "up_ik"
    c = pb(s + "Foot").constraints.new("COPY_ROTATION"); c.target = e; c.target_space = "WORLD"; c.owner_space = "WORLD"; c.name = "up_rot"
def legs(on):
    for s in ("Left", "Right"):
        pb(s + "Leg").constraints["up_ik"].influence = 1.0 if on else 0.0
        pb(s + "Foot").constraints["up_rot"].influence = 1.0 if on else 0.0
# ---- 팔 IK (수색: 바닥 짚기): 손목 과녁 + 손 방향. 영향(influence) g 로 모션캡처 팔과 섞는다
for s in ("Left", "Right"):
    e = bpy.data.objects.new("tg_hand_" + s, None); e.rotation_mode = "QUATERNION"; col.objects.link(e); tg["hand_" + s] = e
    c = pb(s + "ForeArm").constraints.new("IK"); c.target = e; c.chain_count = 2; c.use_tail = True; c.name = "up_ik"; c.influence = 0
    c = pb(s + "Hand").constraints.new("COPY_ROTATION"); c.target = e; c.target_space = "WORLD"; c.owner_space = "WORLD"; c.name = "up_rot"; c.influence = 0
def arm_ik(s, g):
    pb(s + "ForeArm").constraints["up_ik"].influence = g; pb(s + "Hand").constraints["up_rot"].influence = g
# ---- 손가락: walk_knuckle.py 와 같은 법 — 손 뼈의 X 축 하나로 굽힌다(뼈마다 축이 제각각이라). 굽는 쪽은 쉬는 자세에서 재어 정한다
FINGERS = ("Index", "Middle", "Ring", "Pinky", "Thumb")
def fb(side, f, i): return "%sHand%s%d" % (side, f, i)
def reset_pose():
    for b in pbs: b.matrix_basis = Matrix.Identity(4)
    upd()
ad.action = None; reset_pose(); curl_sign = {}
for s_ in ("Left", "Right"):
    z0 = (M @ pb(fb(s_, "Middle", 4)).matrix).translation.z
    for i in (1, 2, 3):
        rotate_world(fb(s_, "Middle", i), Matrix.Rotation(math.radians(20), 4, (M @ pb(s_ + "Hand").matrix).to_3x3().col[0]))
    curl_sign[s_] = 1 if (M @ pb(fb(s_, "Middle", 4)).matrix).translation.z < z0 else -1
    reset_pose()
spread_sign = {}                            # 손가락 벌리기: 손바닥 법선(손 뼈 Z) 둘레로 새끼 쪽을 + 로 돌렸을 때 검지와 멀어지는 쪽
for s_ in ("Left", "Right"):
    d0 = ((M @ pb(fb(s_, "Pinky", 4)).matrix).translation - (M @ pb(fb(s_, "Index", 4)).matrix).translation).length
    rotate_world(fb(s_, "Pinky", 1), Matrix.Rotation(math.radians(15), 4, (M @ pb(s_ + "Hand").matrix).to_3x3().col[2]))
    d1 = ((M @ pb(fb(s_, "Pinky", 4)).matrix).translation - (M @ pb(fb(s_, "Index", 4)).matrix).translation).length
    spread_sign[s_] = 1 if d1 > d0 else -1; reset_pose()
SPREAD = {"Thumb": -22, "Index": -9, "Middle": -2, "Ring": 6, "Pinky": 15}
print("curl sign", curl_sign, "spread sign", spread_sign)
# ---- 긴 목 (M1e): Unity StalkerAnim.NeckOut·BuildPath·PathAt 과 같은 셈 — 머리를 보는 쪽(+ 위 0.4)으로 밀고, 마디 7개를 "머리 → 나오는 곳 → 등뼈" 길 위에 놓는다
NECK_N, NECK_LEN, TOP_IN, OUT_UP = 7, 0.80, 0.03, 0.4
def wpos(n): return (M @ pb(n).matrix).translation.copy()
head_l = (M.to_3x3() @ pb("Head").bone.matrix_local.to_3x3()).inverted()
face_l, head_up_l = head_l @ Vector((0, -1, 0)), head_l @ Vector((0, 0, 1))
def neck_path():
    H, X = wpos("Head"), wpos("Neck"); up = ((M @ pb("Head").matrix).to_3x3() @ head_up_l).normalized()
    sp = [wpos(n_) for n_ in ("Spine2", "Spine1", "Spine", "Hips")]; d = (X - H).length * 0.45
    p1, p2 = H - up * d, X + (X - sp[0]).normalized() * d
    pts = [H + up * TOP_IN] + [(1 - u) ** 3 * H + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u ** 3 * X for u in (k / 16 for k in range(17))] + sp
    return pts + [pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.6]
def path_at(pts, s_):
    acc = 0.0
    for a, b_ in zip(pts, pts[1:]):
        l = (b_ - a).length
        if l > 1e-6 and acc + l >= s_: return a.lerp(b_, (s_ - acc) / l), (a - b_) / l
        acc += l
    return b_, (a - b_).normalized()
_pts = neck_path()
neck_rest_t = [path_at(_pts, TOP_IN + i * NECK_LEN / NECK_N)[1] for i in range(NECK_N)]
neck_rest_r = [(M @ pb("NeckExt_%d" % i).matrix).to_quaternion() for i in range(NECK_N)]
def neck_place(out):
    if out > 0:
        W = M @ pb("Head").matrix; face = W.to_3x3() @ face_l; face.z = min(face.z, 0.0)
        W.translation = W.translation + (face.normalized() + Vector((0, 0, OUT_UP))).normalized() * out
        pb("Head").matrix = Mi @ W; upd()
    pts, q = neck_path(), Quaternion()
    for i in reversed(range(NECK_N)):
        p_, t_ = path_at(pts, TOP_IN + i * NECK_LEN / NECK_N)
        q = (q @ neck_rest_t[i]).rotation_difference(t_) @ q
        pb("NeckExt_%d" % i).matrix = Mi @ (Matrix.Translation(p_) @ (q @ neck_rest_r[i]).to_matrix().to_4x4())
    upd()
def grope_curls(ft, k):                     # 더듬는 손 (B1 판정 "간지럽히는 것 같다" → 두드리기 없음): 벌려 세운 갈고리 손이 아주 느리게만 움직인다
    out = {"Thumb": (8, 12, 8)}
    for i, f in enumerate(FINGERS[:4]):
        w_ = math.sin(2 * math.pi * 0.23 * ft + i * 1.7 + k * 2.0)
        out[f] = (14 + 8 * w_, 22 + 8 * w_, 16)
    return out
def finger_curls(side, ft, run):
    """손가락마다 마디 셋의 굽힘°. 4.5 s 한 바퀴: 주먹을 천천히 쥐었다 편다(1.4 s) → 피아노 치듯 검지부터 차례로 두드린다. 두 손은 엇박자"""
    if run: return {f: (10, 28, 28) for f in FINGERS}          # 질주: 잡으려고 벌린 갈고리 손
    u = (ft + (1.9 if side == "Right" else 0.0)) % 4.5
    out = {}
    for i, f in enumerate(FINGERS):
        if u < 1.4:
            c = math.sin(math.pi * max(0.0, min(1.0, (u - i * 0.05) / 1.2))) ** 2
            a = (8 + 55 * c, 10 + 70 * c, 8 + 55 * c)
        else:
            c = max(0.0, math.sin(2 * math.pi * 1.8 * u - i * 1.15)) ** 2
            a = (8 + 42 * c, 10 + 18 * c, 8 + 12 * c)
        out[f] = tuple(x * (0.5 if f == "Thumb" else 1.0) for x in a)
    return out
def aim(bone, to, k):                       # 뼈가 뻗은 방향을 세상 방향 to 쪽으로 k 만큼 돌린다
    cur = (M @ pb(bone).matrix).to_3x3().col[1].normalized()
    q = Quaternion().slerp(cur.rotation_difference(Vector(to).normalized()), k)
    rotate_world(bone, q.to_matrix().to_4x4())

hips_axes = (M.to_3x3() @ pb("Hips").bone.matrix_local.to_3x3()).inverted()      # 세상 방향 → 엉덩이 뼈의 location 축

# ---- 갱도 크기 상자 · 눈높이 카메라 · 헤드램프
roots = [o for o in scene.objects if o.parent is None and not o.name.startswith("tg_")]
base_mw = {o.name: o.matrix_world.copy() for o in roots}
rock = bpy.data.materials.new("pv_rock"); rock.use_nodes = True
b = next(n for n in rock.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.10, 0.085, 0.07, 1); b.inputs["Roughness"].default_value = 0.95
def quad(loc, rot, sx, sy):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.scale = (sx, sy, 1); o.data.materials.append(rock)
L = 40.0
quad((0, -L / 2 + 4, 0), (0, 0, 0), WALL_X * 2, L); quad((0, -L / 2 + 4, CEIL), (math.pi, 0, 0), WALL_X * 2, L)
if not RETREAT: quad((WALL_X, -L / 2 + 4, CEIL / 2), (0, -math.pi / 2, 0), CEIL, L)
quad((-WALL_X, -L / 2 + 4, CEIL / 2), (0, math.pi / 2, 0), CEIL, L)
GAP_Y, GAP_HW, GAP_H, GAP_D, GAP_BACK = -START + float(E("UP_GAP_M", "7")) / S, float(E("UP_GAP_W", "1.5")) / 2 / S, float(E("UP_GAP_H", "3.0")) / S, float(E("UP_GAP_DEPTH", "3.5")) / S, float(E("UP_GAP_BACK", "1.2")) / 2 / S      # 벽 틈: 나에게서 9 m · 입구 반폭 · 높이 · 깊이 · 안쪽 끝 반폭 (모델 m)
if RETREAT:
    def poly(*vs):
        me = bpy.data.meshes.new("pv_poly"); me.from_pydata([Vector(v) for v in vs], [], [list(range(len(vs)))]); me.update(); me.materials.append(rock)
        scene.collection.objects.link(bpy.data.objects.new("pv_poly", me))
    W_, g0, g1, b0, b1, D_, Y0, Y1 = WALL_X, GAP_Y - GAP_HW, GAP_Y + GAP_HW, GAP_Y - GAP_BACK, GAP_Y + GAP_BACK, WALL_X + GAP_D, -L + 4, 4
    poly((W_, Y0, 0), (W_, g0, 0), (W_, g0, CEIL), (W_, Y0, CEIL)); poly((W_, g1, 0), (W_, Y1, 0), (W_, Y1, CEIL), (W_, g1, CEIL)); poly((W_, g0, GAP_H), (W_, g1, GAP_H), (W_, g1, CEIL), (W_, g0, CEIL))
    poly((W_, g0, 0), (D_, b0, 0), (D_, b0, GAP_H), (W_, g0, GAP_H)); poly((W_, g1, 0), (D_, b1, 0), (D_, b1, GAP_H), (W_, g1, GAP_H)); poly((D_, b0, 0), (D_, b1, 0), (D_, b1, GAP_H), (D_, b0, GAP_H))
    poly((W_, g0, GAP_H), (W_, g1, GAP_H), (D_, b1, GAP_H), (D_, b0, GAP_H)); poly((W_, g0, 0), (W_, g1, 0), (D_, b1, 0), (D_, b0, 0))
cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(42 if CLOSE else 80); cam.data.clip_start = 0.05
if SEARCH: EYE = 0.9 / S                  # 탁자 밑에 앉아 숨은 눈높이
CAM0 = Vector((0.0, -START, EYE))
TABLE_H = 0.85                              # 탁자 상판 윗면 (모델 m — 게임 1.3 m 작업대). 상판은 나(카메라) 뒤 0.3 ~ 앞 1.15, 좌우 ±0.95
if SEARCH:
    wood = bpy.data.materials.new("pv_wood"); wood.use_nodes = True
    b = next(n for n in wood.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.16, 0.11, 0.07, 1); b.inputs["Roughness"].default_value = 0.8
    def box(loc, scale):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.active_object; o.scale = scale; o.data.materials.append(wood)
    box((0, -START + 0.425, TABLE_H - 0.03), (1.9, 1.45, 0.06))
    POST = (0.70, -0.55)                    # 갱목 기둥 (괴물이 선 곳 기준 가운데, 굵기 0.2) — 벽은 팔이 안 닿아(1.6 m) 짚을 세운 면으로 기둥을 둔다
    box((CX + POST[0], -(START - STOP_M / S) + POST[1], CEIL / 2), (0.2, 0.2, CEIL))
    for lx in (-0.88, 0.88):
        for ly in (-0.22, 1.07): box((lx, -START + ly, (TABLE_H - 0.06) / 2), (0.08, 0.08, TABLE_H - 0.06))
lamp = bpy.data.objects.new("pv_lamp", bpy.data.lights.new("pv_lamp", "SPOT")); scene.collection.objects.link(lamp)
WATTS = float(E("PV_WATTS", "0" if SEARCH else "600"))   # 수색 장면은 램프를 껐다 — 어둠에 익은 눈(게임 DARK_ADAPT)처럼 고른 빛만        # U1 은 너무 밝아 "살 벗겨진 사람"으로 보였다 — 게임에 가깝게 어둡게
lamp.data.spot_size = math.radians(120); lamp.data.spot_blend = 0.35; lamp.data.shadow_soft_size = 0.02
lamp.parent = cam; lamp.location = (0, 0.06, 0)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1280, 720, 100
scene.render.image_settings.file_format = "PNG"
world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0.002, 0.002, 0.002, 1)
if SEARCH:
    amb = bpy.data.objects.new("pv_amb", bpy.data.lights.new("pv_amb", "POINT")); scene.collection.objects.link(amb)
    amb.data.energy = float(E("PV_AMBIENT", "90")); amb.data.use_shadow = False; amb.data.color = (0.75, 0.85, 1.0); amb.parent = cam; amb.location = (0, 1.0, -1.4)
    next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0, 0, 0, 1)      # 갱도 끝이 벽보다 밝은 네모로 보였다
try:
    scene.view_settings.view_transform = "Standard"
except TypeError:
    pass

# ---- 시간표: dict(act, f, d, look(머리 좌우 목표°), still(굳음), jaw°)
def lf(act, i, rate): f0, f1 = act.frame_range; return f0 + (i * rate) % (f1 - f0)
plan, dist, wi = [], 0.0, 0
def do_walk(sec, look=0.0, **kw):
    global dist, wi
    for _ in range(int(sec * FPS)):
        dist += v_walk * WALK_RATE / FPS; wi += 1
        plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, look=look, mean=mean_walk, **kw))
def do_stand(looks, jaw=0.0, still=False):      # 걷다 만 자세로 서서 — looks = [(머리 각도, 머무는 초), …]
    for ang, sec in looks:
        n = int(sec * FPS)
        for i in range(n):
            plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, look=ang, mean=mean_walk, still=still, stand=not still, jaw=jaw * (i + 1) / n))
def do_grope(sec, **kw):
    """서 있는 시간 (수색). 자세 열쇠(lean 숙임° · crouch 웅크림 m · neck 목 m · pitch 고개 숙임° · mix 모션캡처 섞기)는 목표값 — 프레임 루프가 천천히 따라간다"""
    for _ in range(int(sec * FPS)):
        plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, mean=mean_walk, stand=True, look=0.0, **kw))
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
import random
UPV, WALLN = Vector((0, 0, 1)), Vector((-1, 0, 0))
def build_pats(events, rnd):
    """짚기 시간표. 자리는 괴물이 선 곳 기준(몸을 안 돌린 축: −Y 가 갱도 앞, +X 가 왼쪽 벽) — 벽·탁자가 갱도에 붙어 있어서. 프레임마다 손별 (손목 과녁이 닿을 면 위의 자리, 면 법선, 짚음 0~1) + 그 프레임의 자세 열쇠.
    한 번에 한 손만 옮긴다: 들어서 옮기기(mv) → 짚고 문지르기(ct). hand 없는 사건 = 두 손 짚은 채 자세만(dur)"""
    cur = {"Left": (Vector((0.35, -0.75, 0)), UPV), "Right": (Vector((-0.35, -0.75, 0)), UPV)}
    pat, keys, marks = {"Left": [], "Right": []}, [], {}
    for ev in events:
        h, kw = ev.get("hand"), ev["keys"]
        if h is None:
            for _ in range(int(ev["dur"] * FPS)):
                for s_ in pat: pat[s_].append((cur[s_][0], cur[s_][1], 1.0))
                keys.append(kw)
        else:
            (p0, n0), p1, n1, o_ = cur[h], Vector(ev["p"]), ev.get("n", UPV), "Left" if h == "Right" else "Right"
            mv, ct = int(ev.get("mv", rnd.uniform(0.45, 0.8)) * FPS), int(ev.get("ct", rnd.uniform(0.35, 0.9)) * FPS)
            rub = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 0.4), rnd.uniform(-1, 1))); rub = (rub - n1 * rub.dot(n1)).normalized() * rnd.uniform(0.06, 0.14)
            via, lift = ev.get("via"), 0.17 if n0.dot(n1) > 0.9 and abs((p1 - p0).dot(n1)) < 0.1 else 0.28
            for i in range(mv):
                u = smooth((i + 1) / mv)
                q_ = (1 - u) ** 2 * p0 + 2 * u * (1 - u) * Vector(via) + u * u * p1 if via else p0.lerp(p1, u)
                nn = n0.lerp(n1, u).normalized()
                pat[h].append((q_ + nn * lift * math.sin(math.pi * u), nn, max(smooth(1 - u / 0.15), smooth((u - 0.7) / 0.3))))     # 떼자마자 조금 오므리고, 내려놓기 전에 편다
                pat[o_].append((cur[o_][0], cur[o_][1], 1.0)); keys.append(kw)
            for i in range(ct):
                pat[h].append((p1 + rub * smooth((i + 1) / ct), n1, 1.0)); pat[o_].append((cur[o_][0], cur[o_][1], 1.0)); keys.append(kw)
            cur[h] = (p1 + rub, n1)
        if "mark" in ev: marks[ev["mark"]] = len(keys)
    return pat, keys, marks
gf = 0.0
def do_pat(n0, n1):
    """짚기 구간. 허리 위 흔들림은 모션캡처(GROPE_RATE 배, 빠르기 고르지 않게), 손은 PAT 시간표, 자세 열쇠는 KEYS"""
    global gf
    g0, g1 = grope_act.frame_range
    for gi in range(n0, n1):
        tt = len(plan) / FPS
        gf += GROPE_RATE * (1.0 + 0.55 * math.sin(2 * math.pi * 0.37 * tt) + 0.25 * math.sin(2 * math.pi * 0.83 * tt + 1.3))
        plan.append({**dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, mean=mean_walk, stand=True, look=0.0, follow=True, lr=2.5,
                            act2=grope_act, f2=g0 + gf % (g1 - g0), mix=1.0, g=1.0, gi=gi), **KEYS[gi]})
if SEARCH:
    WALK_RATE = (SEARCH_MS / S) / v_walk    # 수색 걸음은 게임 그대로 2.5 m/s (up_walk ×1.36 — MA 판정에서 그대로 두기로 함)
    def player_at(yaw_): return -(yaw_ + math.degrees(math.atan2(CX, STOP_M / S)))     # 몸에서 본 나의 방향
    do_walk((START - STOP_M / S) / (SEARCH_MS / S) - 1.0); do_walk(1.0, yaw=YAW)        # 마지막 1 s 는 벽 쪽으로 휘어 걷는다
    PX, TY = POST[0] - 0.1, float(E("UP_TABLE_YAW", "-12"))     # 기둥의 괴물 쪽 면 · 탁자(나) 쪽으로 몸을 돌린 각
    EDGE_Y, CAM_X = -(STOP_M / S) + 1.15, -CX                   # 탁자 상판의 괴물 쪽 끝 · 나의 x (괴물이 선 곳 기준)
    LOW = dict(lean=float(E("UP_LEAN", "52")), crouch=float(E("UP_SQUAT", "0.70"))); MID = HIGH = LOW       # 어깨가 0.5 m 쯤까지 내려와야 바닥을 멀리(어깨에서 0.6 m) 짚는다.       # 높은 데를 짚을 때도 몸은 거의 안 든다 — 들면 바닥을 짚은 다른 손이 떠 버린다(어깨가 0.8 m 위로 가면 바닥에 안 닿는다)
    W = dict(neck=NECK_OUT, pitch=22, yaw=YAW); T = {**W, "yaw": TY}
    EVENTS = [
        dict(hand="Left", p=(PX, POST[1], 0.75), n=WALLN, keys={**W, **HIGH}),                       # 기둥을 짚고
        dict(hand="Right", p=(-0.30, -0.95, 0), keys={**W, **LOW}),                                 # 바닥 멀리
        dict(hand="Left", p=(PX, POST[1] - 0.02, 1.05), n=WALLN, keys={**W, **HIGH}, ct=0.5),        # 기둥 더 위
        dict(hand="Left", p=(0.45, -0.90, 0), keys={**T, **LOW}, ct=0.4, via=(0.45, -0.35, 0.55)),                           # 탁자 쪽으로 돌아앉는다
        dict(dur=float(E("UP_PEEK_S", "1.6")), keys={**T, "lean": 60, "crouch": 0.76, "pitch": -20, "follow": False, "look": player_at(TY), "lr": 12.0}),   # 고개를 낮춰 탁자 밑을 들여다본다 (나를 보지만 어둠 속이라 못 본다)
        dict(hand="Right", p=(-0.30, EDGE_Y + 0.36, TABLE_H), keys={**T, **HIGH}, via=(-0.35, -0.55, 1.0), ct=0.6),   # 탁자 위를 짚고
        dict(hand="Right", p=(-0.30, EDGE_Y + 0.12, 0), keys={**T, **LOW}, via=(-0.3, -0.15, 0.75)),              # 손을 탁자 밑으로 — 짚을 때마다 더 깊이
        dict(hand="Left", p=(0.05, EDGE_Y + 0.04, 0), keys={**T, **LOW}),
        dict(hand="Right", p=(-0.36, EDGE_Y + 0.0, 0), keys={**T, **LOW}, ct=0.9, mark="hear"),                 # 가장 가까이
        dict(hand="Right", p=(-0.30, -0.75, 0), keys={**T, **MID}, mv=1.3, ct=0.3),                             # 천천히 손을 거둔다
    ]
    PAT, KEYS, MARKS = build_pats(EVENTS, random.Random(int(E("UP_SEED", "7"))))
    PAT_N, hear = len(KEYS), MARKS["hear"] - 4
    do_stand([(-55, 0.6), (30, 0.9)])       # 서서 딱 — 딱
    do_grope(NECK_S, neck=NECK_OUT, lean=10, pitch=12)                                  # 앞을 딱 — 목을 천천히 내밀어 들여다본다
    do_grope(0.9, mix=1.0, act2=grope_act, f2=grope_act.frame_range[0], g=1.0, gi=0, **KEYS[0])     # 몸을 접으며 두 손이 첫 자리로 내려간다
    do_pat(0, hear)
    plan[-5]["jolt"] = True                 # 내가 소리를 냈다 — 화면이 덜컥
    heard = {**plan[-1], "hold": True, "look": player_at(TY), "pitch": -14, "tilt": TILT, "follow": False, "lr": 12.0}
    plan += [{**heard, "snap": True} for _ in range(int(0.2 * FPS))]                    # 몸은 굳고 머리만 나를 향해 딱 들린다 + 갸웃
    plan += [dict(heard) for _ in range(int(float(E("UP_HOLD_S", "2.0")) * FPS))]       # 통째로 멈춤 — "들었나?"
    do_pat(hear, PAT_N)                     # 머리가 천천히 손으로 돌아가고, 손을 거둔다
    do_grope(1.0, g=1.0, mix=1.0, rise=True, yaw=TY)                                 # 손을 짚은 채 몸부터 일으키고
    do_grope(0.8)                           # 일어선다
    do_stand([(45, 1.2)])                   # 못 찾았다 — 고개를 딴 데로 돌린다
elif RETREAT:
    pos, ph = Vector((0.0, -START + 2.0 / S)), {"w": 0.0, "r": 0.0}       # 괴물 자리(세상 x, y) · 걷기·달리기 클립의 흐른 프레임
    def put(act, mean, f, **kw): plan.append({**dict(act=act, f=f, d=-pos.y, x=pos.x, mean=mean, look=0.0), **kw})
    def wf(): f0, f1 = walk.frame_range; return f0 + ph["w"] % (f1 - f0)
    def stay(sec, **kw):
        for _ in range(int(sec * FPS)): put(walk, mean_walk, wf(), **{**dict(stand=True), **kw})
    def move(pts, speed, back=False, near_kw=None, near_m=1.4, clip=None, **kw):
        """pts(세상 x, y 꺾은선)를 speed(남은 거리) 모델 m/s 로 간다. 2.4 m/s(게임) 넘으면 달리기 클립. 몸은 가는 쪽을 본다(back = 뒷걸음: 보는 쪽 그대로, 걷기 거꾸로). grip 이 함수면 간 몫(0~1)으로 부른다"""
        pts = [Vector(p_) for p_ in pts]; cum = [0.0]
        for a, b_ in zip(pts, pts[1:]): cum.append(cum[-1] + (b_ - a).length)
        s_ = 0.0
        while True:
            v = speed(cum[-1] - s_); s_ += v / FPS
            if s_ >= cum[-1]: break
            k = max(i for i in range(len(cum) - 1) if cum[i] <= s_); h = pts[k + 1] - pts[k]
            pos.x, pos.y = pts[k].lerp(pts[k + 1], (s_ - cum[k]) / h.length)
            kk = {**kw, **(near_kw if near_kw and cum[-1] - s_ < near_m else {})}
            if callable(kk.get("grip")): kk["grip"] = kk["grip"](s_ / cum[-1])
            if not back: kk["yaw"] = math.degrees(math.atan2(h.x, -h.y))
            if v * S > 2.4:
                a_, m_, va_ = clip or (run, mean_run, v_run)
                ph["r"] += v / va_; f0, f1 = a_.frame_range; put(a_, m_, f0 + ph["r"] % (f1 - f0), **kk)
            else:
                ph["w"] += (-1 if back else 1) * v / v_walk; put(walk, mean_walk, wf(), **kk)
    PY = GAP_Y + (0.6 if SAB == "miss" else 0.0)                    # 사보타주: 길이 틈을 빗나간다 → 바위 속 검사가 죽어야 한다
    # R1 판정(09-20): 걷기 거꾸로 = 도망으로 안 읽힌다 · 남는 손 안 섬뜩 → 곧바로 도망 · 맞고 굳음 + 뒷걸음 어색 → 새 동작 · 멈칫 없이 · 나오기 = 두 손으로 벽을 잡고 머리가 쭉 뻗어 나와 나를 찾은 뒤 몸이 비집고 나온다
    # 조사(에일리언 아이솔레이션): 다친 제노모프는 가장 가까운 환풍구로 **곧장** 달려간다 — 머뭇거림 없음. 맞는 순간은 팔로 몸을 가리며 움찔
    # R2 판정(09-20): 나오기 통과 · 도망 1.5 s 괜찮다 / 다친 달리기가 Mixamo(zombie run)라 사람 같다 · 움찔(Zombie Reaction Hit)이 어색하다
    # → R3: 사람 모션캡처를 둘 다 뺀다. 달리기 = MA 에서 통과한 up_jog 식(Mutant Run + 팔 죽이기 0.85 + 숙임) 위에 절뚝임·기운 몸·감싼 팔. 움찔 = 통과한 "딱" 동작들로: 맞은 쪽에서 몸통이 홱 비틀려 낮아지고 머리가 딱 돌아갔다 나에게 딱 돌아온다(턱 벌림) → 바로 튄다
    OLD = SAB == "r2"                       # 비교용: R2 의 Mixamo 두 클립
    hit_act, _, mean_hit = load("Zombie Reaction Hit") if OLD else (walk, 0, mean_walk); hurt, v_hurt, mean_hurt = load("zombie run") if OLD else (run, v_run, mean_run)      # 사람이 연기한 맞음 반응 · 비틀거리는 달리기 (둘 다 받아 둔 Mixamo)
    def me_from(yaw_):                      # 몸이 yaw_ 를 볼 때 나를 보려면 머리를 몇 도 (왼쪽 +)
        f, t_ = Vector((math.sin(math.radians(yaw_)), -math.cos(math.radians(yaw_)))), Vector((0, -START)) - pos
        return math.degrees(math.atan2(f.x * t_.y - f.y * t_.x, f.dot(t_)))
    LOW = dict(crouch=float(E("UP_R_SQUAT", "0.30")), lean=float(E("UP_R_LEAN", "22")))
    TW = float(E("UP_R_TWIST", "65"))
    stay(0.4, jaw=JAW_RUN); plan[-1]["jolt"] = True                                       # 코앞 2 m — 내가 곡괭이로 쳤다
    h0, h1 = hit_act.frame_range; n_hit = int(0.5 * FPS)
    for i in range(n_hit):                                                                 # 스턴 0.5 s — 첫 0.2 s 에 1.0 m 밀린다
        if i < 6: pos.y += (1.0 / S) / 6
        if OLD: put(hit_act, mean_hit, h0 + min(h1 - h0 - 1, i * 1.6), jaw=JAW_RUN, arm_still=0.15); continue
        away = i < 7                                                                       # 0.23 s: 맞은 데서 몸이 홱 비틀려 낮아지고 머리가 딱 돌아간다 → 나머지: 낮은 채 머리만 나에게 딱, 턱을 벌린다
        put(walk, mean_walk, wf(), still=True, fast=0.45, twist=55.0, crouch=0.34, lean=-14.0 if away else 16.0, roll=-14.0, tuck=1.0, ghand="Left",
            look=-70.0 if away else 0.0, lr=25.0, tilt=-20.0 if away else 0.0, jaw=JAW_RUN, yaw=35.0, yr=0.3)
    FLEE = dict(limp=True, jaw=JAW_FREEZE, yr=0.22, ghand="Left", tuck=0.9, roll=-11.0, crouch=0.14, lean=10.0)         # 비틀거리는 달리기 + 왼발에 크게 주저앉음 + 오른팔로 몸을 감싼다. 몸은 빨리 돌아선다
    C0, C1, C2, C3 = pos.copy(), pos + Vector((0.8, 0.5)), Vector((WALL_X - 2.1, PY)), Vector((WALL_X - 1.3, PY))
    def cubic(u): return (1 - u) ** 3 * C0 + 3 * u * (1 - u) ** 2 * C1 + 3 * u * u * (1 - u) * C2 + u ** 3 * C3
    n0 = len(plan)
    # 사용자(09-20, R3 뒤): 들어갈 때도 두 손으로 벽을 비집으며 들어가게 → 입구 앞까지 달려와 두 손을 틈 속으로 뻗어 양쪽 옆면(0.45 안쪽)을 쥐고, 어깨를 한쪽씩 비틀어 몸을 끌어 넣는다
    OLD_IN = SAB == "r3"                    # 비교용: R3 의 그냥 달려 들어가기
    def jamb_y(depth): return GAP_HW - (GAP_HW - GAP_BACK) * depth / GAP_D - 0.04
    GIN = {"Left": (Vector((WALL_X + 0.06, GAP_Y + jamb_y(0.06), 1.05)), Vector((0, -1, 0)), 0.8), "Right": (Vector((WALL_X + 0.06, GAP_Y - jamb_y(0.06), 0.90)), Vector((0, 1, 0)), 0.8)}      # 입구 모서리 바로 안 — 0.45 안쪽을 쥐게 했더니 뒤에서 보는 내 눈엔 손이 몸에 가려 안 보였다     # 틈을 보고(+X) 서면 왼손 = 먼 쪽 옆면
    ENT = dict(g=1.0, ghand="Both", grips=GIN, jaw=JAW_FREEZE, **LOW)
    END = Vector((WALL_X + 0.9, PY - 0.06)) if OLD_IN else Vector((WALL_X - 0.55, PY))
    move([cubic(k / 60) for k in range(61)] + [END], (lambda r: 4.0 / S) if OLD_IN else (lambda r: (2.5 + 1.5 * min(1.0, r / 0.7)) / S),        # 곡선으로 돌아선 뒤 마지막은 곧게 — 덜 돌아선 몸으로 들어가면 팔이 옆면에 걸린다
         clip=(hurt, mean_hurt, v_hurt), near_kw=dict(twist=TW, tuck=1.0, roll=0.0, yr=0.35, ghand="-", **LOW) if OLD_IN else dict(roll=0.0, yr=0.35, **{**ENT, "jaw": JAW_FREEZE}), near_m=2.7 if OLD_IN else 0.9, **FLEE)
    if not OLD_IN:
        stay(0.25, twist=TW * 0.4, **ENT)                                                       # 두 팔을 벌려 양쪽 모서리를 쥔다 (뒤에서 보인다)
        move([pos, (WALL_X - 0.30, PY - 0.03)], lambda r: 0.9, twist=TW, **ENT)                 # 쥔 채 몸을 끌어당기며 오른 어깨부터 밀어 넣는다 — 어깨가 손을 지나기 전에 놓는다(지나면 손 방향이 뒤집힌다)
        move([pos, (WALL_X + 0.18, PY - 0.04)], lambda r: 0.9, ghand="-", letgo=True, tuck=1.0, twist=-TW * 0.7, jaw=JAW_FREEZE, **LOW)      # 손을 놓고 반대로 비틀어 왼 어깨를 빼 넣는다
        move([pos, (WALL_X + 0.9, PY - 0.06)], lambda r: 1.5, ghand="-", tuck=1.0, twist=TW, **LOW)      # 손을 놓고 어둠 속으로
    print("RETREAT flee: hit %.2f s, run %.2f s to inside the gap" % (n_hit / FPS, (len(plan) - n0) / FPS))
    for _ in range(int(float(E("UP_R_EMPTY_S", "1.5")) * FPS)): put(walk, mean_walk, wf(), hidden=True, **LOW)   # 빈 틈
    # 나오기: 두 손이 먼저 양쪽 옆면을 쥔다 → 머리가 쭉 뻗어 나와 나를 찾는다 → 찾았다 → 어깨를 한쪽씩 비집고 나온다
    GY = GAP_HW - 0.04
    GRIPS = {"Left": (Vector((WALL_X + 0.06, GAP_Y - GY + 0.08, 1.00)), Vector((0, 1, 0)), 0.8), "Right": (Vector((WALL_X + 0.06, GAP_Y + GY, 0.90)), Vector((0, -1, 0)), 0.8)}     # 틈을 등지고(−X 를 보고) 서면 왼손 = 나 쪽 옆면
    G = dict(g=1.0, ghand="Both", grips=GRIPS, **LOW)
    pos.x, pos.y = WALL_X + 0.75, PY
    for _ in range(12): put(walk, mean_walk, wf(), hidden=True, yaw_now=-90.0, **G)            # 어둠 속에서 나올 자세를 잡는다 (안 보인다)
    move([pos, (WALL_X + 0.62, PY)], lambda r: 0.35, **G)                                                  # 어둠 속에서 두 손이 나와 가장자리를 쥔다
    stay(0.7, linger=True, **G)                                                                            # 손만 보인다
    NK = float(E("UP_R_NECK", "0.42"))
    OUT = {**G, "neck": NK, "lean": 34, "nr": NK / 1.4}
    move([pos, (WALL_X + 0.40, PY + 0.06)], lambda r: 0.16, look=-50, lr=3.0, **OUT)                              # 머리가 쭈욱 뻗어 나온다 — 저쪽(갱도 안쪽)부터 천천히 훑는다
    stay(0.7, look=-50, **OUT); stay(0.9, look=15, lr=2.5, **OUT)                                          # … 이쪽으로 천천히
    stay(0.2, look=me_from(-90.0), lr=12.0, tilt=TILT, pitch=-8, **OUT)                                   # 나를 찾았다 — 딱 + 갸웃
    stay(0.9, look=me_from(-90.0), tilt=TILT, pitch=-8, still=True, stand=False, jaw=JAW_FREEZE, **OUT)   # 굳어서 본다, 턱이 벌어진다
    SQ = {**G, "look": me_from(-90.0), "jaw": JAW_FREEZE, "lean": 30}
    move([pos, (WALL_X + 0.05, PY + 0.05)], lambda r: 0.55, twist=-TW, **SQ)                               # 비집고 나온다: 오른 어깨를 뒤로 빼 왼 어깨부터
    move([pos, (WALL_X - 0.40, PY - 0.05)], lambda r: 0.55, twist=TW * 0.7, **SQ)                          # … 반대로 비틀어 오른 어깨를 빼낸다
    move([pos, (WALL_X - 1.1, PY - 0.12)], lambda r: 1.85 / S, ghand="Both", look=me_from(-90.0), jaw=JAW_FREEZE)      # 손을 놓고 걸어 나온다
    yaw_end = plan[-1]["yaw"]
    stay(0.9, look=me_from(yaw_end), still=True, stand=False, jaw=JAW_RUN)                                # 굳는다
    rate_note = "retreat"
else:
    do_walk(1.5)
    do_stand([(-55, 0.7), (35, 1.1)])           # 서서 왼쪽을 딱 — 머물고 — 오른쪽을 딱 — 더 오래 머문다 (간격이 고르지 않게)
    do_walk(1.1, look=35)                       # 본 쪽을 본 채 다시 걷는다
    do_stand([(0, float(E("UP_FREEZE_S", "1.4")))], jaw=JAW_FREEZE, still=True)     # 나를 딱 — 돌이 된다, 턱만 천천히 벌어진다
    rate = (RUN_GAME / S) / v_run; i = 0
    while START - dist > 0.85:
        dist += (RUN_GAME / S) / FPS * min(1.0, (i + 1) / 3); i += 1
        plan.append(dict(act=run, f=lf(run, i, rate), d=dist, look=0.0, mean=mean_run, jaw=JAW_RUN, run=True, ri=i))
    rate_note = "run x%.2f" % rate
print("UPRIGHT %s: %d frames (%.2f s), walk x%.2f = %.2f m/s game, %s" % (NAME, len(plan), len(plan) / FPS, WALK_RATE, v_walk * WALK_RATE * S, "search" if SEARCH else rate_note))

# U2 의 버그(09-19 사용자 판정 "걸음이 U1 과 똑같다 · 머리 돌리기가 없다"로 드러남): 렌더가 동작(action)을 다시 계산해
# 모션캡처에 키가 있는 뼈(엉덩이·팔·척추·목·머리)에 손으로 얹은 값을 전부 지웠다 — 키가 없는 턱만 살아남았다.
# 그래서 얹은 뒤의 자세를 통째로 떠서(freeze) 동작을 떼고 뼈에 직접 박은 다음 굽는다.
order = [b for b in pbs if b.parent is None]
for b in order: order.extend(b.children)
def freeze():
    mats = {b.name: b.matrix.copy() for b in order}           # IK 까지 계산된 결과
    ad.action = None; legs(False); arm_ik("Left", 0.0); arm_ik("Right", 0.0)
    for b in order:
        if b.parent:
            rest = mats[b.parent.name] @ b.parent.bone.matrix_local.inverted() @ b.bone.matrix_local
            b.matrix_basis = rest.inverted() @ mats[b.name]
        else:
            b.matrix_basis = b.bone.matrix_local.inverted() @ mats[b.name]
    upd()
    return mats
upper = set(pb("Spine").children_recursive) | {pb("Spine")}      # 더듬기는 허리 위만 모션캡처 — 다리는 선 자세 그대로 (zombie attack 온몸 섞기는 몸이 150° 돌아가 버렸다)
shake = dip = dip_to = 0.0; look = body_look = life = ft = 0.0; was_up = [True, True]; checked = set()
held = lean = squat = pitch = neck = yaw = yaw_to = tilt = mixw = f2 = 0.0; a2 = None       # 수색: 멈춘 시간 · 자세 열쇠를 따라가는 값 · 모션캡처 섞는 몫
floor_min = 9.0
twist = tuck = 0.0                          # 도망: 좁은 틈에 어깨를 비껴 넣는 상체 비틀기° · 안 쥐는 팔을 몸 앞으로 모으기 0~1
grip, in_rock, head_top, grip_err, grips_last = None, 0, 0.0, 0.0, {}   # 도망: 쥐는 자리 · 바위 속에 든 뼈-프레임 · 틈 안에서 머리 꼭대기 · 남은 손이 과녁에서 뜬 거리
roll = 0.0; hshift, face_pre = Vector((0, 0, 0)), None  # 짚는 손 쪽으로 실리는 엉덩이 · 들었을 때 머리가 얼마나 돌았나 재는 기준
gw, gi_now, focus = {"Left": 0.0, "Right": 0.0}, 0, Vector((0, -1, 0))      # 팔 IK 영향 · 짚기 시간표의 지금 칸 · 머리가 따라가는 손 자리
by = {}; slid = 0.0; pat_n = pat_ok = clipped = in_slab = 0; straight_min, pat_low, pat_reach = 9.0, 9.0, 0.0
reach_max, low_min, wall_max, hold_move, hold_prev, neck_max, look_pre, snap_deg = 0.0, 9.0, 0.0, 0.0, None, 0.0, 0.0, 0.0
jaw_axis = Vector((1, 0, 0))
for n, st in enumerate(plan):
    for o in roots:                         # 뼈 계산은 늘 처음 자리에서 (M 이 그 자리 기준) — 끝에서 과녁과 같이 옮긴다
        o.matrix_world = base_mw[o.name]
    hold = bool(st.get("hold")) and SAB != "nohold"            # 긴 정지: 자세에 드는 모든 시계·따라가는 값을 세운다 → 같은 자세가 그대로 다시 나온다 (화면만 산다)
    if hold: held += 1.0 / FPS
    legs(False); reset_pose(); use(st["act"], st["f"])          # reset: freeze() 가 키 없는 채널(크기 등)에 남긴 찌꺼기를 지운다 — 없으면 구운 프레임 다음 프레임이 1 mm 쯤 다르다
    if "act2" in st: a2, f2 = st["act2"], st["f2"]
    if not hold: mixw += ((st.get("mix", 0.0) if SAB != "nogrope" else 0.0) - mixw) * 0.12
    if a2 and mixw > 0.001:                 # 더듬기: 선 자세와 모션캡처를 뼈마다 섞는다 (온몸 — 팔만 얹으면 어깨·허리가 안 따라와 도로 기계 같다)
        A = [(b.rotation_quaternion.copy(), b.location.copy()) for b in order]
        use(a2, f2)
        for b, (q_, l_) in zip(order, A):
            if b not in upper: b.rotation_quaternion, b.location = q_, l_; continue
            b.rotation_quaternion = q_.slerp(b.rotation_quaternion, mixw); b.location = l_.lerp(b.location, mixw)
        upd()
    for s in ("Left", "Right"):             # 원래 모션캡처의 발목 자리·발 방향을 과녁으로
        W = M @ pb(s + "Foot").matrix
        tg[s].location = W.translation; tg[s].rotation_quaternion = W.to_quaternion()
    hit = hit_left = False
    for k, s in enumerate(("Left", "Right")):
        up = (M @ pb(s + "ToeBase").matrix).translation.z > 0.13
        if was_up[k] and not up and not st.get("still"): hit = True; hit_left = hit_left or k == 0
        was_up[k] = up
    if hit:
        near = min(1.0, (3.5 / S) / max(START - st["d"], 0.6)) ** 0.8
        shake = max(shake, (0.05 if st.get("run") else 0.022) * near + 0.003); dip_to = DIP * (1.6 if st.get("run") else 1.0)
        if st.get("limp") and hit_left: dip_to = DIP * 3.2         # 다친 티: 왼발을 디딜 때마다 크게 주저앉는다
    if not hold: dip += (dip_to - dip) * 0.5; dip_to *= 0.55               # 한 프레임에 뚝 떨어지면 끊겨 보인다 — 두세 프레임에 걸쳐 내려앉는다
    legs(True)
    t, tc = n / FPS - held, n / FPS          # t = 몸의 시계(긴 정지 동안 선다) · tc = 화면의 시계
    # U3 판정: 서서 머리 돌릴 때 온몸이 멈춰 "일시정지"로 보인다 → 서 있는 동안 숨(엉덩이·가슴) · 무게 옮기기 · 팔 앞뒤 흔들림을 얹는다. 굳음(still)은 통과했으니 돌 그대로
    if not hold:
        life += ((1.0 if st.get("stand") else 0.0) - life) * 0.15
        if not st.get("still"): ft += 1.0 / FPS               # 손가락 시계 — 굳으면 같이 멈춘다
        lean += (st.get("lean", 0.0) - lean) * st.get("fast", 0.07); squat += (st.get("crouch", 0.0) - squat) * st.get("fast", 0.07); pitch += (st.get("pitch", 0.0) - pitch) * 0.07
        nr_ = st.get("nr", NECK_OUT / NECK_S) / FPS
        neck += max(-nr_, min(nr_, st.get("neck", 0.0) - neck))     # 목은 고른 빠르기로 천천히 (Unity MoveTowards 와 같다)
        for s_ in gw: gw[s_] += ((st.get("g", 0.0) if SAB != "nogrope" and st.get("ghand", s_) in (s_, "Both") else 0.0) - gw[s_]) * 0.22      # 몸이 접히는 것(0.07)보다 팔이 먼저 자리를 잡아야 손이 바닥 밑으로 안 들어간다
        gi_now = st.get("gi", gi_now)
        if SEARCH and gw["Left"] > 0.5:     # 더 멀리: 두 손 가운데 쪽으로 엉덩이가 실린다 (발은 제자리 — 다리 IK)
            mid = Matrix.Rotation(math.radians(-yaw), 3, "Z") @ ((PAT["Left"][gi_now][0] + PAT["Right"][gi_now][0]) / 2) - Vector((0, -0.75, 0)); mid.z = 0
            if mid.length > 0.45: mid = mid.normalized() * 0.45
            hshift += (mid - hshift) * 0.06
            far = {s_: (Matrix.Rotation(math.radians(-yaw), 3, "Z") @ PAT[s_][gi_now][0] - wpos(s_ + "Arm")).length for s_ in gw}
            roll += (max(-16.0, min(16.0, (far["Left"] - far["Right"]) * 40)) - roll) * 0.06      # 더 멀리 뻗는 쪽 어깨가 내려간다 (몸통이 그쪽으로 기운다)
        else: hshift *= 0.9; roll += (st.get("roll", 0.0) - roll) * st.get("fast", 0.1)
        if "yaw" in st: yaw_to = st["yaw"]
        twist += (st.get("twist", 0.0) - twist) * st.get("fast", 0.10); tuck += (st.get("tuck", 0.0) - tuck) * st.get("fast", 0.12)
        if "grips" in st: grips_last = st["grips"]
        if "yaw_now" in st: yaw = yaw_to = st["yaw_now"]
        yaw += (yaw_to - yaw) * st.get("yr", 0.08)
    pb("Hips").location = pb("Hips").location + hips_axes @ Vector((0.015 * life * math.sin(2 * math.pi * 0.21 * t) + hshift.x, 0.35 * squat + hshift.y,
                                                                    -(CROUCH + squat + dip + 0.010 * life * math.sin(2 * math.pi * 0.30 * t))))
    for nm in ARMS:                         # 팔 흔들기를 죽인다
        pb(nm).rotation_quaternion = pb(nm).rotation_quaternion.slerp(st["mean"][nm], st.get("arm_still", ARM_STILL) * (1 - mixw))
    upd()
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians((HUNCH * (1 - HUNCH_CUT * mixw) + lean) / 3), 4, "X"))
    rotate_world("Neck", Matrix.Rotation(math.radians(-(HUNCH * (1 - HUNCH_CUT * mixw) + lean) * 0.45 + pitch * 0.4), 4, "X"))
    rotate_world("Head", Matrix.Rotation(math.radians(-(HUNCH * (1 - HUNCH_CUT * mixw) + lean) * 0.45 + pitch * 0.6), 4, "X"))
    if abs(roll) > 0.01: rotate_world("Spine", Matrix.Rotation(math.radians(roll), 4, "Y"))
    rotate_world("Spine1", Matrix.Rotation(math.radians(1.8 * life * math.sin(2 * math.pi * 0.30 * t + 0.6)), 4, "X"))
    want, lr = st["look"], st.get("lr", 12.0)
    if st.get("follow"): want = max(-60.0, min(60.0, math.degrees(math.atan2(focus.x, -focus.y)) * 0.8))       # 머리가 옮기는 손을 느리게 따라간다
    if not hold or st.get("snap"):                            # 머리: 한 프레임에 12° = 0.15 s 에 55° — 딱 돌리고 멈춘다. "들었나?"(snap)는 몸이 굳은 채 머리만
        if st.get("snap"): pitch += max(-6.0, min(6.0, st.get("pitch", 0.0) - pitch))       # 들었을 때는 숙인 고개도 딱 들린다
        look += max(-lr, min(lr, want - look)); tilt += max(-3.0, min(3.0, st.get("tilt", 0.0) - tilt))
    lag = want * 0.45 - body_look
    if not hold: body_look += lag * 0.07                                   # 상체: 머리를 뒤늦게(0.5 s 쯤) 천천히 따라간다 — 머리 각도의 45 % 까지
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians(body_look / 3), 4, "Z"))
        if abs(twist) > 0.01: rotate_world(nm, Matrix.Rotation(math.radians(twist / 3), 4, (M @ pb(nm).matrix).to_3x3().col[1]))      # 숙인 몸통을 세로축으로 돌리면 머리가 옆으로 0.5 m 휘둘린다 — 등뼈 제 축으로 비튼다
    rotate_world("Neck", Matrix.Rotation(math.radians((look - body_look - twist) * 0.4), 4, "Z"))
    rotate_world("Head", Matrix.Rotation(math.radians((look - body_look - twist) * 0.6), 4, "Z"))
    if abs(tilt) > 0.01: rotate_world("Head", Matrix.Rotation(math.radians(tilt), 4, (M @ pb("Head").matrix).to_3x3() @ face_l))      # 갸웃
    for k, s_ in enumerate(("Left", "Right")):
        if st.get("run"):                                     # U3 판정: 두 팔로 잡겠다는 듯 앞으로 뻗고 벌려서 — 모션캡처의 팔 펌프질은 20 % 만 남긴다
            r = min(1.0, (st["ri"] + 1) / 8) * 0.8
            sx = 1.0 if (M @ pb(s_ + "Arm").matrix).translation.x > 0 else -1.0
            aim(s_ + "Arm", (sx * 0.38, -1, -0.10), r); aim(s_ + "ForeArm", (sx * 0.12, -1, 0.22), r)
        elif life > 0.01:                    # 서 있을 때: 팔이 앞뒤로 천천히, 두 팔 엇박자 + 상체가 돌 때 팔이 뒤처진다
            sw = life * (1 - mixw) * (7.0 * math.sin(2 * math.pi * 0.33 * t + k * 2.1) + lag * 0.5)
            rotate_world(s_ + "Arm", Matrix.Rotation(math.radians(sw), 4, "X"))
            rotate_world(s_ + "ForeArm", Matrix.Rotation(math.radians(life * (1 - mixw) * 5.0 * math.sin(2 * math.pi * 0.33 * t + k * 2.1 - 0.9)), 4, "X"))
        if tuck > 0.01 and st.get("ghand") not in (s_, "Both"):             # 안 쥐는 팔: 팔꿈치를 몸에 붙이고 손을 가슴 앞·아래로
            cx_ = 0.15 if s_ == "Right" else -0.15                 # 아래팔은 가슴을 가로질러 몸 가운데 쪽으로 (오른쪽 = −X)
            aim(s_ + "Arm", (0, -0.35, -1), min(1.0, tuck)); aim(s_ + "ForeArm", (cx_, -0.7, 0.1), min(1.0, tuck))
        g = gw[s_]
        if RETREAT and g > 0.001:                             # 옆면을 쥔 팔: 팔꿈치가 옆(바위 속)이 아니라 아래로 꺾이게 IK 앞에 자세를 잡아 준다
            in_ = -0.3 if (M @ pb(s_ + "Arm").matrix).translation.x > 0 else 0.3          # … 그리고 몸 가운데 쪽으로 (밖으로 0.06 m 벌어져 옆면에 걸렸다)
            aim(s_ + "Arm", (in_ * 2.3, 0.25, -0.8), g * g); aim(s_ + "ForeArm", (0, -1, 0.1), g * g)     # g*g: 막 쥐러 갈 때(IK 가 아직 약할 때) 팔을 아래로 겨누면 손이 바닥을 뚫는다
        arm_ik(s_, g); c_ = 0.0
        if g > 0.001:                                         # 짚는 팔: 손목 과녁(팔 길이 94 % 안으로 당김) + 손 방향(손가락은 어깨에서 뻗는 쪽, 손바닥은 바닥 쪽, 떠 있을 땐 끝을 조금 든다)
            Rzi = Matrix.Rotation(math.radians(-yaw), 3, "Z")
            if RETREAT:                                       # 쥐는 자리는 세상에 박혀 있고 몸이 움직인다
                grip = st.get("grip", grip); p_, nrm, c_ = st["grips"][s_] if "grips" in st else (grips_last.get(s_) or grip); p_, nrm = Rzi @ (p_ - Vector((st["x"], -st["d"], 0))), Rzi @ nrm
            else:
                p_, nrm, c_ = PAT[s_][gi_now]; p_, nrm = Rzi @ p_, Rzi @ nrm
            if c_ < 1.0 and not RETREAT: focus = p_
            sh = wpos(s_ + "Arm")
            p_ = p_ + nrm * (0.035 + 0.05 * (1 - c_)) + Vector((0, 0, 0.0 if RETREAT else 0.5 * max(0.0, 1 - squat / 0.3)))      # 몸이 덜 접힌 동안은 손도 그만큼 떠 있다 (접고 펼 때 손이 몸과 같이 내려가고 올라온다)
            off = (sh - p_).dot(nrm); s0 = sh - nrm * off; r_ = math.sqrt(max(0.01, 0.80 ** 2 - off ** 2))      # 팔 길이 94 % 밖이면 면을 따라 어깨 쪽으로 당긴다
            if (p_ - s0).length > r_: p_ = s0 + (p_ - s0).normalized() * r_; clipped += 1
            yv = ((p_ - s0).normalized() + nrm * 0.30 * (1 - c_)).normalized(); dn = -nrm
            zv = (dn - yv * dn.dot(yv)).normalized() * curl_sign[s_]
            tg["hand_" + s_].location = p_; tg["hand_" + s_].rotation_quaternion = Matrix((yv.cross(zv), yv, zv)).transposed().to_quaternion()
            upd()
        cf = 0.55 + 0.45 * c_ if g > 0.001 else 0.0          # 옮기는 동안에도 반쯤은 펴 둔다 — 다 오므리면 낮게 옮길 때 끝이 바닥 밑으로 들어간다
        if SAB == "curled": cf = 0.0
        hm = (M @ pb(s_ + "Hand").matrix).to_3x3(); ax = hm.col[0]
        curls = finger_curls(s_, ft, st.get("run")); gc = grope_curls(ft, k)
        for f_, angs in curls.items():
            angs = tuple(a + (b_ - a) * mixw for a, b_ in zip(angs, gc[f_]))
            angs = tuple(a * (1 - g * cf) for a in angs)      # B2 판정: 바닥을 짚을 때는 손가락을 전부 편다 …
            if g * cf > 0.001:                                # … 쉬는 자세에도 굽힘이 들어 있어(곧은 정도 0.88) 각도를 0 으로 해선 안 펴진다 → 마디마다 손이 뻗은 쪽(벌린 만큼 돌린)으로 겨눈다
                to = Matrix.Rotation(spread_sign[s_] * math.radians(SPREAD[f_]), 3, hm.col[2]) @ hm.col[1]
                for i in (1, 2, 3): aim(fb(s_, f_, i), to, cf * smooth(g))
            for i, a in enumerate(angs):
                rotate_world(fb(s_, f_, i + 1), Matrix.Rotation(curl_sign[s_] * math.radians(a), 4, ax))
    if P + "Jaw" in pbs:
        pb("Jaw").rotation_quaternion = Quaternion(jaw_axis, math.radians(st.get("jaw", 0.0)))
    upd()
    if RETREAT:
        neck_place(neck)
        if st.get("linger"): grip_err = max(grip_err, max((wpos(s_ + "Hand") - tg["hand_" + s_].location).length for s_ in ("Left", "Right")))
    if SEARCH:
        neck_place(neck); neck_max = max(neck_max, (wpos("Head") - wpos("Neck")).length)
        for s_ in ("Left", "Right"):        # 짚은 손: 가장 낮은 손끝(과 손목 밑)이 바닥에 딱 닿게 과녁을 위아래로 한 번 바로잡는다 + 자기 검사 기록
            if gw[s_] < 0.97 or "gi" not in st or squat < 0.6 or PAT[s_][gi_now][1] < 1.0: continue
            Rzi = Matrix.Rotation(math.radians(-yaw), 3, "Z"); p0, nrm = Rzi @ PAT[s_][gi_now][0], Rzi @ PAT[s_][gi_now][1]
            def off_(): return [(wpos(fb(s_, f_, 4)) - p0).dot(nrm) for f_ in FINGERS[:4]] + [(wpos(s_ + "Hand") - p0).dot(nrm) - 0.03]
            tg["hand_" + s_].location = tg["hand_" + s_].location + nrm * (0.004 - min(off_())); upd()
            d_ = off_()
            slid = max(slid, (tg["hand_" + s_].location - (p0 + nrm * 0.035)).length)      # 짚은 손이 제자리에서 밀린 거리 (팔이 모자라 당겨진 것)
            k_ = "post" if abs(nrm.z) < 0.5 else ("table" if p0.z > 0.5 else "floor"); by[k_] = [by.get(k_, [0, 0])[0] + 1, by.get(k_, [0, 0])[1] + (max(d_[:4]) <= 0.06)]
            pat_n += 1; pat_ok += max(d_[:4]) <= 0.06      # 뼈는 손가락 가운데 줄이다 — 눕힌 손가락의 뼈 높이는 0.04~0.05
            pat_low = min(pat_low, min(d_)); pat_reach = max(pat_reach, max(-wpos(fb(s_, f_, 4)).y for f_ in FINGERS[:4]))
            for f_ in FINGERS[:4]:
                js = [wpos(fb(s_, f_, i)) for i in (1, 2, 3, 4)]
                straight_min = min(straight_min, (js[3] - js[0]).length / sum((b_ - a).length for a, b_ in zip(js, js[1:])))
        if True:                            # 자기 검사용 기록 (모든 프레임 — 몸을 접고 펴는 사이에 손이 바닥 밑으로 들어간 적이 있다)
            tips = [wpos(fb(s_, f_, 4)) for s_ in ("Left", "Right") for f_ in FINGERS[:4]]
            Rz = Matrix.Rotation(math.radians(yaw), 3, "Z")
            reach_max = max(reach_max, max(-q_.y for q_ in tips)); low_min = min(low_min, min(q_.z for q_ in tips))
            wall_max = max(wall_max, max(abs((Rz @ q_).x + CX) for q_ in tips))
            for q_ in tips:                 # 탁자 상판 속에 든 손끝
                w_ = Rz @ q_
                in_slab += abs(w_.x - CAM_X) < 0.95 and w_.y < EDGE_Y and TABLE_H - 0.06 < w_.z < TABLE_H - 0.005
        face = (M @ pb("Head").matrix).to_3x3() @ face_l
        if st.get("snap"): snap_deg = max(snap_deg, math.degrees(face.angle(face_pre)))
        elif not st.get("hold"): face_pre = face
        snap = [b_.matrix.copy() for b_ in order]
        still_ = st.get("hold") and not st.get("snap")
        if still_ and hold_prev:
            hold_move = max(hold_move, max(abs(x) for a, b_ in zip(snap, hold_prev) for row in (a - b_) for x in row))
        if still_ and hold_prev and E("UP_DEBUG"):
            w_ = max(zip(order, snap, hold_prev), key=lambda z: max(abs(x) for row in (z[1] - z[2]) for x in row))
            print("HOLDDBG", n, w_[0].name, max(abs(x) for row in (w_[1] - w_[2]) for x in row))
        hold_prev = snap if still_ else None
    X = Matrix.Translation((st.get("x", CX) + (50.0 if st.get("hidden") else 0.0), -st["d"], 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    if RETREAT and not st.get("hidden"):    # 자기 검사: 벽 너머(x > 벽)에 있는 뼈는 전부 틈 안(안으로 좁아지는 폭 · 천장 밑)이어야 한다
        bad = 0
        for b_ in order:
            w_ = X @ (M @ b_.matrix).translation
            grip_f = "Hand" in b_.name and (st.get("ghand") == "Both" or st.get("letgo") or st.get("ghand", "-") + "Hand" in b_.name)       # 쥐는 손의 손가락은 바위에 닿는 게 일이다 — 모서리에서 0.18 m 까지 봐준다 (손끝이 모서리를 스칠 때 0.15 m, 손을 놓는 한 프레임에 0.17 m 까지 든다)
            if w_.x <= WALL_X + (0.08 if grip_f else 0.03): continue
            hw = GAP_HW - (GAP_HW - GAP_BACK) * min(1.0, (w_.x - WALL_X) / GAP_D)
            out_ = abs(w_.y - GAP_Y) > hw + (0.18 if grip_f else 0.05) or w_.z > GAP_H or w_.x > WALL_X + GAP_D; bad += out_
            if out_ and E("UP_DEBUG") : print("ROCKBONE", n, b_.name, "%.2f %.2f %.2f" % tuple(w_), "halfwidth %.2f" % hw)
            if "Head" in b_.name: head_top = max(head_top, w_.z)
        in_rock += bad > 0
        f_prev = floor_min
        floor_min = min(floor_min, min((X @ (M @ pb(s_ + "Hand" + f_ + "4").matrix).translation).z for s_ in ("Left", "Right") for f_ in FINGERS[:4]))
        if bad and E("UP_DEBUG"): print("ROCKDBG frame", n, "bones", bad)
        if floor_min < min(f_prev, 0.0) and E("UP_DEBUG"): print("FLOORDBG frame", n, "%.3f" % floor_min, "g", gw, "tuck %.2f" % tuck)
    for o in roots:
        o.matrix_world = X @ base_mw[o.name]
    for e in tg.values():
        W = X @ Matrix.LocRotScale(e.location, e.rotation_quaternion, None)
        e.location, e.rotation_quaternion = W.translation, W.to_quaternion()
    upd()
    # 화면은 늘 살아 있다: 숨결 같은 느린 흔들림 + 발 디딜 때의 떨림
    if st.get("jolt"): shake = 0.035
    sway = Vector((0.006 * math.sin(2 * math.pi * 0.23 * tc), 0, 0.005 * math.sin(2 * math.pi * 0.31 * tc + 1.0)))
    # U2 판정 "영상이 끊긴다": 발 디딜 때 화면을 프레임마다 무작위로 튀게 한 것이 빠진 프레임처럼 보였다 → 무작위 없이 아래로 눌렸다 돌아오기만
    cam.location = CAM0 + sway + Vector((0, 0, -shake))
    cam.rotation_euler = (math.radians(90) + 0.004 * math.sin(2 * math.pi * 0.27 * tc) - shake * 0.3 - (0.04 if SEARCH else 0.0),
                          0.003 * math.sin(2 * math.pi * 0.19 * tc), -0.15 if SEARCH else (-0.20 if RETREAT else 0.0))       # 수색: 바닥을 쓰는 손이 보이게 살짝 아래·괴물 쪽을 본다
    shake *= 0.7
    if CLOSE:
        cam.location = Vector((0.6, -st["d"] - 2.6, 1.3))
        cam.rotation_euler = (Vector((0, -st["d"], 1.15)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    if CLOSE and RETREAT:                   # 틈 가장자리의 손·머리가 보이게: 틈 맞은편 (게임 시점 아님)
        cam.location = Vector((-1.7, GAP_Y - 1.6, 1.25)) + sway          # 맞은편 벽 쪽 — 가운데에 두면 달아나는 괴물이 카메라를 뚫고 지나가 화면이 하얗게 탄다(R1)
        cam.rotation_euler = (Vector((WALL_X, GAP_Y + 0.2, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.angle_y = math.radians(55)
    if CLOSE and SEARCH:                    # 팔·손가락이 보이게: 괴물 오른쪽 앞 낮은 곳에서 (게임 시점 아님)
        cam.location = Vector((-1.85, -st["d"] - 0.5, 1.45)) + sway          # 몸을 따라 돌리면 카메라가 벽 밖으로 나간다(시험 프레임이 새까맸다) — 갱도 기준 자리
        cam.rotation_euler = (Vector((CX - 0.5, -st["d"] - 0.95, 0.55)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.angle_y = math.radians(55)
    near = max(START - st["d"] - 0.4, 0.2)
    if CLOSE: near = 2.6
    if CLOSE and RETREAT: near = 9.0
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4)) * (1.0 + 0.03 * math.sin(2 * math.pi * 1.7 * tc))
    mats = freeze()                         # 안 굽는 프레임도 뜬다 — 뜨고 난 다음 프레임은 팔 IK 가 조금 다르게 풀려서, 빠른 확인(UP_STEP)의 검사 숫자가 본 렌더와 달랐다
    # 자기 검사: 프레임을 다시 계산해도(렌더가 하는 일) 돌린 머리·뻗은 손이 그대로인가. SABOTAGE=nofreeze 로 U2 버그를 되살리면 여기서 죽는다
    for key, bone in ((("head", "Head"),) if abs(look) > 30 else ()) + ((("hand", "LeftHand"),) if mixw > 0.9 else ()):
        if key in checked: continue
        if SAB == "nofreeze": use(st["act"], st["f"])
        scene.frame_set(scene.frame_current); upd()
        d = math.degrees((pb(bone).matrix.to_quaternion().rotation_difference(mats[P + bone].to_quaternion())).angle)
        dm = (pb(bone).matrix.translation - mats[P + bone].translation).length
        print("CHECK %s survives re-evaluation: off by %.1f deg %.3f m (look %.0f)" % (key, d, dm, look))
        assert d < 1.0 and dm < 0.005, "FAIL: 얹은 자세가 렌더 때 지워진다"
        checked.add(key)
    if n % STEP: continue
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % n)
    bpy.ops.render.render(write_still=True)
assert "head" in checked, "FAIL: 머리 돌리기 검사가 한 번도 안 돌았다"
if SEARCH:
    print("CHECK grope: %d hand-frames planted, all four fingertips on floor in %.0f %% · fingers straight min %.3f · lowest %.3f m (any time %.3f) · planted fingertips reach %.2f m game in front · target pulled in on %d arm-frames · farthest %.2f m from centre (wall %.2f) · head snap %.0f deg in 0.2 s · neck %.3f m · hold motion %.6f"
          % (pat_n, 100.0 * pat_ok / max(pat_n, 1), straight_min, pat_low, low_min, pat_reach * S, clipped, wall_max, WALL_X, snap_deg, neck_max, hold_move))
    print("CHECK planted by surface [frames, all-four-on]:", by, "· planted hand dragged off its spot by up to %.2f m" % slid)
    assert "hand" in checked, "FAIL: 손 검사가 한 번도 안 돌았다 (모션캡처가 안 섞였다)"
    assert pat_n > 3 * FPS and pat_ok / pat_n >= 0.85, "FAIL: 짚는 동안 네 손가락 끝이 바닥에 안 닿는다"
    assert straight_min >= 0.93, "FAIL: 짚을 때 손가락이 안 펴졌다"
    assert pat_low > -0.02 and low_min > -0.03 and wall_max < WALL_X, "FAIL: 손이 바닥·벽을 뚫는다"
    assert 2.0 <= pat_reach * S <= 3.0, "FAIL: 짚는 손끝이 몸 앞 2.0~3.0 m 밖 (B3 는 1.95 — 더 멀리 뻗기로 함)"
    assert snap_deg >= 25, "FAIL: 들었을 때 머리가 0.2 s 에 25° 를 못 돈다"
    assert any(st.get("hold") for st in plan) and hold_move < 1e-4, "FAIL: 긴 정지 동안 뼈가 움직인다"
    assert in_slab == 0, "FAIL: 손끝이 탁자 상판 속에 들어갔다 (%d)" % in_slab
if RETREAT:
    print("CHECK retreat: frames with a bone inside rock %d · head top inside the gap %.2f m (gap ceiling %.2f) · lingering hand off its grip by %.3f m (%d linger frames)" % (in_rock, head_top, GAP_H, grip_err, sum(1 for st in plan if st.get("linger"))))
    print("CHECK retreat: lowest fingertip %.3f m (floor 0)" % floor_min)
    assert in_rock == 0, "FAIL: 뼈가 틈 밖의 바위 속에 들어갔다"
    assert floor_min > -0.03, "FAIL: 손끝이 바닥 밑으로 들어갔다"
    assert 0.5 < head_top < GAP_H, "FAIL: 머리가 틈 천장을 뚫는다 (또는 틈에 안 들어갔다)"
    assert grip_err < 0.15, "FAIL: 남은 손이 가장자리를 못 쥐고 있다"
if STEP > 1: sys.exit(0)

out = os.path.join(OUT_DIR, "UP_%s.mp4" % NAME)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=0.6:color=black", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
