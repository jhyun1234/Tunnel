"""walk_knuckle — 괴물 새 걷기: 두 손(발톱 끝)과 두 발로 짚는 네 점 걸음 (제안서 3D-③b M1, 2026-09-18).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/anim/walk_knuckle.py
입력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend (stage12 → add_jaw.py 턱 뼈 → trim_back_plank.py 등 판자 자름·못 옮김 → timber_detail.py 갱목·못·가죽끈 사실감 → add_long_neck.py 몸 속 긴 목) — 안 고친다
하는 일: ① 두 손·두 발 자리를 한 주기(1.0 s = 30 프레임) 동안 정한다 — 짚는 동안은 뒤로 SPEED 로 밀려 제자리 걸음,
           떼는 동안은 앞으로 호를 그리며 옮긴다. 순서는 원숭이류처럼 왼손 → 오른발 → 오른손 → 왼발(한 박자 0.25 주기)
        ② 엉덩이를 낮추고 몸통을 앞으로 숙인다(어깨가 엉덩이보다 높게), 머리는 세상 기준으로 앞을 본 채 고정(P2)
        ③ 팔·다리는 IK(끝 자리를 정하면 팔꿈치·무릎이 알아서 굽는 계산)로, 손은 발톱 끝이 아래를 향하게
        ④ 키로 굽고(visual bake) 동작 `walk_knuckle` NLA 트랙으로 더한다 → 클립 15개 GLB 를 Unity 로 내보낸다
        ⑤ 자기 검사 PASS/FAIL + 옆·앞 연속 그림
출력: Tunnel/unity/Assets/Tunnel/Monster/miner_rigged.glb (덮어쓰기, 사용자 허락 09-18) · blender/anim/walk_knuckle.blend(리그 + 동작만)
      Documents/MineTunnel/blender/anim_render/walk_knuckle_*.png (저장소 밖)
사보타주: SABOTAGE=noplant -> 손이 바닥에 안 닿는다 (검사 "손 짚기" FAIL). SABOTAGE=straight -> 손가락을 안 굽힌다 (검사 "손가락 굽음" FAIL). 사보타주 실행은 GLB·blend 를 덮어쓰지 않는다"""
import bpy, os, sys, json, struct, math, hashlib
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v4_stage16_neck.blend"))
SABOTAGE = os.environ.get("SABOTAGE", "")
SFX = "_" + SABOTAGE if SABOTAGE else ""
OUT_GLB = os.environ.get("OUT_GLB", os.path.join(MT, "mesh", "miner_rigged_unity%s.glb" % SFX) if SABOTAGE
          else r"C:\Users\anjyo\Tunnel\unity\Assets\Tunnel\Monster\miner_rigged.glb")
OUT_BLEND = os.path.join(HERE, "walk_knuckle%s.blend" % SFX)
RENDER = os.path.join(MT, "blender", "anim_render" + SFX); os.makedirs(RENDER, exist_ok=True)

# ---- 걸음 값 (모델 크기 1 기준 m · s). 게임 괴물은 Tuning.STALKER_MODEL_SCALE 1.5 배
FPS = 30
# 걸음표: 같은 스크립트가 걸음마다 한 번씩 돌아 클립을 굽는다 (M2 09-19). N = 한 주기 프레임(N 번째 = 0 번째와 같은 자세) · SPEED = 원래 빠르기
# DUTY = 한 손발이 바닥을 짚고 있는 몫 · TOUCH = 닿는 순간(주기 몫) · BOB 몸 오르내림 · SWAY 좌우 · ROLL 어깨 기울기(도) · BOBN 한 주기에 오르내리는 횟수
# PH = 몸이 가장 높고 가장 펴진 순간 · FLEX 허리 접기(도, 엉덩이 ±FLEX/2 · 척추 마디마다 ∓FLEX/3) · LIFT 떼는 동안 드는 높이
# MINC 빠르기 검사에 필요한 짚은 프레임 · AIR 네 발이 다 뜬 프레임(이상, 0 이면 없어야 한다)
GAITS = {
    # 배회: STALKER_SPEED_WANDER 2.5 ÷ STALKER_MODEL_SCALE 1.5 = 1.67 m/s → 게임에서 배수 1.0. 원숭이류 순서 왼손 → 오른발 → 오른손 → 왼발.
    # 팔이 다리보다 짧아 손은 짧게 짚는다(손 0.75 · 발 0.92 m)
    "walk_knuckle": dict(N=30, SPEED=2.5 / 1.5, DUTY={"Hand": float(os.environ.get("DUTY_HAND", "0.45")), "Foot": 0.55},
                         TOUCH={"LeftHand": 0.0, "RightFoot": 0.25, "RightHand": 0.5, "LeftFoot": 0.75},
                         BOB=0.025, SWAY=0.03, ROLL=4.0, BOBN=2, PH=0.0, FLEX=0.0, LIFT={"Hand": 0.20, "Foot": 0.14}, MINC=4, AIR=0),
    # 추격: STALKER_SPEED_CHASE 6.5 ÷ 1.5 = 4.33 m/s → 추격 배수 1.0 (조사 0.77 · 철수 0.62). 손 둘이 먼저 짚고 발 둘이 뒤에서 미는 뜀박질,
    # 네 발이 다 뜨는 순간이 있다 (제안서 3D-③b M2). 허리 접기 8° 는 그림에서 안 보였다 → 24° · 오르내림 8 cm (09-19)
    "run_knuckle": dict(N=20, SPEED=6.5 / 1.5,
                        DUTY={"Hand": float(os.environ.get("RUN_DUTY_HAND", "0.25")), "Foot": float(os.environ.get("RUN_DUTY_FOOT", "0.30"))},
                        TOUCH={"LeftHand": 0.0, "RightHand": 0.12, "RightFoot": 0.5, "LeftFoot": 0.62},
                        BOB=float(os.environ.get("RUN_BOB", "0.08")), SWAY=0.02, ROLL=3.0, BOBN=1, PH=0.95, FLEX=float(os.environ.get("RUN_FLEX", "24")),
                        LIFT={"Hand": 0.30, "Foot": 0.22}, MINC=3, AIR=2),
}
if os.environ.get("GAIT_JSON"):          # 시험용: 걸음표에 줄을 더하거나 덮는다 (QUICK 과 같이). 예: GAIT_JSON='{"glide": {"N": 17, ...}}' ONLY=glide
    GAITS.update(json.loads(os.environ["GAIT_JSON"]))
ONLY = os.environ.get("ONLY", "")       # QUICK 일 때 걸음 하나만 (값 고를 때). 내보내기는 늘 둘 다
if ONLY:
    GAITS = {ONLY: GAITS[ONLY]}
HIP_Z = float(os.environ.get("HIP_Z", "0.90"))       # 엉덩이 뼈 머리 높이 (쉬는 자세 1.30)
HIPS_PITCH = float(os.environ.get("HIPS_PITCH", "62"))   # 도, 엉덩이째 앞으로 숙임
SPINE_PITCH = float(os.environ.get("SPINE_PITCH", "7"))  # 도, 척추 세 마디 각각 더 숙임
NECK_BACK = 30.0                        # 도, 목을 뒤로 젖힘 (나머지는 머리가 세상 기준 고정으로 받는다)
CLAV_DOWN = float(os.environ.get("CLAV_DOWN", "10"))    # 도, 어깨뼈(쇄골)를 앞·아래로
QUICK = os.environ.get("QUICK", "") == "1"            # 검사만 (그림·내보내기 없음) — 값 고를 때
SHOTS = os.environ.get("SHOTS", "") == "1"            # QUICK 과 같이: 그림까지 찍고 내보내기 없이 끝
HEAD_UP = 8.0                           # 도, 머리가 정면보다 살짝 위를 본다
HAND_X, FOOT_X = 0.42, 0.20             # 손·발 좌우 자리 (가운데에서)
HAND_Y_OFF, FOOT_Y_OFF = 0.0, float(os.environ.get("FOOT_Y_OFF", "0.12"))    # 손은 어깨 밑보다 조금 앞, 발은 엉덩이 밑보다 조금 뒤
# 손 방향: 손등이 위, 손바닥이 아래를 보고 앞으로 HAND_DOWN 도 숙인다 → 굽힌 손가락 끝이 아래로 바닥을 찍는다 (09-19, 전엔 손을 거의 수직으로 세워
# 손가락을 굽히면 손가락 등(마디)이 바닥에 닿았다). x 는 바깥쪽 부호를 곱한다
HAND_DOWN = float(os.environ.get("HAND_DOWN", "50"))
HAND_DIR = Vector((0.15, -math.cos(math.radians(HAND_DOWN)), -math.sin(math.radians(HAND_DOWN))))
# 발톱 끝(끝뼈 머리)이 짚는 높이. Unity 팔 들기 안전망(StalkerAnim.LateUpdate)은 손끝이 발바닥 면 위 STALKER_ARM_FLOOR_MARGIN 0.02 m(게임)
# 밑이면 팔을 든다 — 0 에 짚으면 걷는 내내 팔을 들어 올렸다(09-18 Unity 실측 1499 프레임), 0.02 는 Unity 에서 0.020 m 로 문턱에 붙어 11 프레임. 0.03 에 짚는다
CLAW_Z = 0.03
HAND_LIFT_ALL = 0.30 if SABOTAGE == "noplant" else CLAW_Z    # noplant: 손을 바닥에서 30 cm 띄운다
# 손가락 마디 굽힘(도, 첫·둘째·셋째 마디). 09-18 판정 "손가락이 일직선으로 오는 게 어색하다" → 09-19 발톱이 갈고리처럼 바닥을 찍게.
# 엄지는 반만. 굽는 쪽 = 쉬는 자세(T포즈)에서 손가락 끝이 내려가는 쪽(손바닥 쪽) — 뼈마다 재서 고른다
CURL = [0.0, 0.0, 0.0] if SABOTAGE == "straight" else [float(x) for x in os.environ.get("CURL", "10,15,10").split(",")]
THUMB_K = 0.5
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
CHORD_MAX = float(os.environ.get("CHORD_MAX", "0.84"))   # 검사: 손가락 뿌리 → 끝 곧은 거리 ÷ 마디 길이 합(굽을수록 작다). 안 굽힘 0.879 · 10,15,10 굽힘 0.800 (09-19 실측) 사이

fails = []
NAME = ""
def check(ok, msg):
    msg = (NAME + ": " if NAME else "") + msg
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["Miner_Rig"]
M, Mi = arm.matrix_world.copy(), arm.matrix_world.inverted()
P = "mixamorig:"
pbs = arm.pose.bones
def pb(n): return pbs[P + n]
def wmat(n): return M @ pb(n).matrix
def whead(n): return (M @ pb(n).matrix).translation
def wtail(n): return M @ pb(n).tail
def upd(): bpy.context.view_layer.update()

ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
for nm in GAITS:
    if nm in [t.name for t in ad.nla_tracks]:
        ad.nla_tracks.remove(ad.nla_tracks[nm])
arm.data.pose_position = "POSE"
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects:
    o.select_set(o == arm)
bpy.ops.object.mode_set(mode="POSE")

def reset_pose():
    for p in pbs:
        p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0); p.scale = (1, 1, 1)
    upd()

def rotate_world(n, R):
    """뼈를 제 머리를 축으로 세상 기준 회전 R 만큼 더 돌린다"""
    W = wmat(n); h = W.translation
    pb(n).matrix = Mi @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W)
    upd()

def fb(side, f, i): return "%sHand%s%d" % (side, f, i)
curl_sign = {}
reset_pose()
for side in ("Left", "Right"):                            # 손마다 한 축(손 뼈의 X 축)으로 모든 손가락을 같은 쪽으로 굽힌다 — 뼈마다 축이 제각각이라
    z0 = whead(fb(side, "Middle", 4)).z
    for i in (1, 2, 3):
        rotate_world(fb(side, "Middle", i), Matrix.Rotation(math.radians(20), 4, wmat(side + "Hand").to_3x3().col[0]))
    curl_sign[side] = 1 if whead(fb(side, "Middle", 4)).z < z0 else -1
    reset_pose()
print("curl sign", curl_sign)

def curl_fingers():
    for side, sg in curl_sign.items():
        ax = wmat(side + "Hand").to_3x3().col[0]
        for f in FINGERS:
            for i in (1, 2, 3):
                a = CURL[i - 1] * (THUMB_K if f == "Thumb" else 1.0)
                rotate_world(fb(side, f, i), Matrix.Rotation(sg * math.radians(a), 4, ax))

def chord(side):
    """엄지 뺀 네 손가락의 (뿌리 → 끝 곧은 거리) ÷ (마디 길이 합) 평균. Unity 검사도 같은 뼈 점(뼈 머리)으로 잰다"""
    out = 0.0
    for f in FINGERS[1:]:
        h = [whead(fb(side, f, i)) for i in (1, 2, 3, 4)]
        out += (h[3] - h[0]).length / sum((h[i + 1] - h[i]).length for i in range(3))
    return out / 4

acts = {}
for NAME, G in GAITS.items():
    N, SPEED, DUTY, TOUCH, LIFT = G["N"], G["SPEED"], G["DUTY"], G["TOUCH"], G["LIFT"]
    BOB, SWAY, ROLL, BOBN, PH, FLEX, MINC, AIR = G["BOB"], G["SWAY"], G["ROLL"], G["BOBN"], G["PH"], G["FLEX"], G["MINC"], G["AIR"]
    STRIDE = {k: SPEED * d * N / FPS for k, d in DUTY.items()}                   # 짚는 동안 밀리는 길이
    ad.action = None
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.ops.object.mode_set(mode="POSE")
    reset_pose()
    head_z = None
    def body_pose(t):
        """t = 주기 몫 0~1. 엉덩이 자리·숙임·흔들림, 척추, 목"""
        reset_pose()
        rest_h = whead("Hips")
        z = HIP_Z + BOB * math.cos(2 * math.pi * BOBN * (t - PH))
        x = SWAY * math.sin(2 * math.pi * t)
        fx = FLEX * math.cos(2 * math.pi * (t - PH))          # + 펴짐(발로 민 뒤 공중) · − 말림(손 뗀 뒤 발이 앞으로 들어올 때). 걷기는 0
        R = Matrix.Rotation(math.radians(ROLL) * math.sin(2 * math.pi * t), 4, "Y") @ Matrix.Rotation(math.radians(HIPS_PITCH + fx / 2), 4, "X")
        W = wmat("Hips")
        pb("Hips").matrix = Mi @ (Matrix.Translation(Vector((x, rest_h.y, z))) @ R @ Matrix.Translation(-rest_h) @ W)
        upd()
        for s in ("Spine", "Spine1", "Spine2"):
            rotate_world(s, Matrix.Rotation(math.radians(SPINE_PITCH - fx / 3), 4, "X"))
        for side in ("Left", "Right"):                        # 어깨뼈를 앞·아래로 — 팔 뿌리가 낮아져 손이 바닥에 닿는다
            rotate_world(side + "Shoulder", Matrix.Rotation(math.radians(CLAV_DOWN), 4, "X"))
        rotate_world("Neck", Matrix.Rotation(math.radians(-NECK_BACK), 4, "X"))
        if head_z is not None:                                # P2 머리 고정: 가슴이 오르내린 만큼 가슴 마디를 숙이거나 들어 머리 높이를 맞춘다
            for _ in range(3):
                e = whead("Head").z - head_z
                L = (whead("Head") - whead("Spine2")).length
                rotate_world("Spine2", Matrix.Rotation(math.asin(max(-0.5, min(0.5, e / L))), 4, "X"))
        curl_fingers()

    # ---- 1. 과녁(빈 물체) — 손·발 자리, 팔꿈치·무릎 방향, 손·발·머리 방향
    col = bpy.data.collections.new("wk_rig"); scene.collection.children.link(col)
    def empty(name, loc=(0, 0, 0)):
        e = bpy.data.objects.new(name, None); e.location = loc; col.objects.link(e); return e

    BOB0, SWAY0, ROLL0, FLEX0 = BOB, SWAY, ROLL, FLEX
    BOB = SWAY = ROLL = FLEX = 0.0
    body_pose(0.0); head_z = whead("Head").z
    BOB, SWAY, ROLL, FLEX = BOB0, SWAY0, ROLL0, FLEX0
    print("head z (흔들림 없을 때) %.3f" % head_z)
    reset_pose()
    rest_world = {n: wmat(n).copy() for n in ("LeftHand", "RightHand", "LeftFoot", "RightFoot", "Head")}
    body_pose(0.0)
    sh_y = (whead("LeftArm").y + whead("RightArm").y) * 0.5
    hip_y = (whead("LeftUpLeg").y + whead("RightUpLeg").y) * 0.5
    print("shoulder y %.3f z %.3f · hip joint y %.3f z %.3f" % (sh_y, whead("LeftArm").z, hip_y, whead("LeftUpLeg").z))

    limbs = {}
    for side, sx in (("Left", 1), ("Right", -1)):
        limbs[side + "Hand"] = dict(kind="Hand", bone=side + "ForeArm", x=sx * HAND_X, yc=sh_y + HAND_Y_OFF, z0=0.0, lift=LIFT["Hand"],
                                    pole=(sx * 1.2, sh_y + 1.0, 1.4), sx=sx)
        limbs[side + "Foot"] = dict(kind="Foot", bone=side + "Leg", x=sx * FOOT_X, yc=hip_y + FOOT_Y_OFF, z0=rest_world[side + "Foot"].translation.z,
                                    lift=LIFT["Foot"], pole=(sx * 0.3, hip_y - 1.5, 0.6), sx=sx)
    tg = {k: empty("tg_" + k) for k in limbs}
    po = {k: empty("po_" + k, v["pole"]) for k, v in limbs.items()}

    def orient_empty(name, Wrot):
        e = empty(name); e.rotation_mode = "QUATERNION"; e.rotation_quaternion = Wrot.to_quaternion(); return e
    rot = {}
    for side, sx in (("Left", 1), ("Right", -1)):
        R0 = rest_world[side + "Hand"].to_3x3()
        d0 = R0.col[1].normalized()                          # 뼈 방향 = 쉬는 자세에서 바깥
        d1 = Vector((HAND_DIR.x * sx, HAND_DIR.y, HAND_DIR.z)).normalized()
        down = Vector((0, 0, -1))                             # 손바닥 = 쉬는 자세(T포즈)에서 아래 → 걸을 때도 아래 쪽으로
        p0 = (down - d0 * down.dot(d0)).normalized(); p1 = (down - d1 * down.dot(d1)).normalized()
        F0 = Matrix((d0, p0, d0.cross(p0))).transposed(); F1 = Matrix((d1, p1, d1.cross(p1))).transposed()
        rot[side + "Hand"] = orient_empty("ro_%sHand" % side, F1 @ F0.transposed() @ R0)
        rot[side + "Foot"] = orient_empty("ro_%sFoot" % side, rest_world[side + "Foot"].to_3x3())
    Rh = rest_world["Head"].to_3x3()
    rot["Head"] = orient_empty("ro_Head", Matrix.Rotation(math.radians(-HEAD_UP), 3, "X") @ Rh)

    for k, v in limbs.items():
        c = pb(v["bone"]).constraints.new("IK")
        c.target = tg[k]; c.pole_target = po[k]; c.chain_count = 2; c.use_tail = True
    for k in ("LeftHand", "RightHand", "LeftFoot", "RightFoot", "Head"):
        c = pb(k).constraints.new("COPY_ROTATION")
        c.target = rot[k]; c.target_space = "WORLD"; c.owner_space = "WORLD"

    def place(t):
        """주기 몫 t 에서 손발 과녁 자리"""
        for k, v in limbs.items():
            ph = (t - TOUCH[k]) % 1.0
            du, st = DUTY[v["kind"]], STRIDE[v["kind"]]
            if ph < du:                                       # 짚음: 앞(−Y)에서 닿아 뒤로 밀린다
                y = v["yc"] - st / 2 + SPEED * ph * N / FPS; z = 0.0
            else:                                             # 뗌: 뒤에서 앞으로 호
                u = (ph - du) / (1 - du)
                y = v["yc"] + st / 2 - st * (0.5 - 0.5 * math.cos(math.pi * u)); z = v["lift"] * math.sin(math.pi * u)
            tg[k].location = (v["x"], y, v["z0"] + z + v.get("dz", 0.0))

    # ---- 2. 팔꿈치·무릎이 과녁(pole) 쪽으로 굽는 각도를 고른다 (Mixamo 팔다리 축이 제각각이라 넷을 재 본다)
    place(0.1); upd()
    for k, v in limbs.items():
        c = pb(v["bone"]).constraints["IK"]
        best = None
        for a in (-90, 0, 90, 180):
            c.pole_angle = math.radians(a); upd()
            mid = whead(v["bone"]); root = whead(pb(v["bone"]).parent.name[len(P):])
            tip = wtail(v["bone"])
            line = (tip - root).normalized(); off = (mid - root) - line * (mid - root).dot(line)
            want = (Vector(v["pole"]) - root); want = want - line * want.dot(line)
            sc = off.normalized().dot(want.normalized()) if off.length > 1e-4 else -1
            if best is None or sc > best[0]:
                best = (sc, a)
        c.pole_angle = math.radians(best[1])
        print("pole %s %d° (맞음 %.2f)" % (k, best[1], best[0]))

    # ---- 3. 손 과녁 높이: 발톱 끝이 바닥(z 0)에 오게 — 손 방향이 고정이라 손목 → 발톱 끝 거리가 늘 같다
    def tips(side):
        return [b for b in pbs if b.name.startswith(P + side + "Hand") and not b.children]
    # 발톱 끝 = 손가락 끝뼈(…4)의 **머리**. 끝뼈 꼬리는 Mixamo 가 붙인 가짜 연장이라 살보다 5~9 cm 더 나간다 — 꼬리로 맞추면 발톱이 4 cm 떴다(09-18 메시 실측).
    # Unity 에는 끝뼈 머리까지만 뼈(Transform)로 들어가니 Unity 검사도 같은 점을 본다
    def lowest(side):
        return min((M @ b.head).z for b in tips(side))
    body_pose(0.0); place(0.0); upd()
    for side in ("Left", "Right"):
        k = side + "Hand"
        ph_ok = [t / N for t in range(N) if (t / N - TOUCH[k]) % 1.0 < DUTY["Hand"] * 0.5]
        body_pose(ph_ok[0]); place(ph_ok[0]); upd()
        wrist = wtail(side + "ForeArm")
        miss = (wrist - tg[k].location).length
        limbs[k]["dz"] = wrist.z - lowest(side) + HAND_LIFT_ALL     # 손목 → 가장 낮은 발톱 끝 높이 차 (손 방향이 고정이라 늘 같다)
        print("hand %s: 손목 → 발톱 끝 %.3f → 손목 과녁 높이 %.3f" % (side, wrist.z - lowest(side), limbs[k]["dz"]))

    # ---- 4. 프레임마다 몸 자세·과녁을 키로 → 굽기
    src = bpy.data.actions.new("wk_src"); ad.action = src
    if hasattr(ad, "action_slot") and src.slots:
        ad.action_slot = src.slots[0]
    for e in tg.values():
        e.animation_data_create()
    for f in range(N + 1):
        t = (f % N) / N
        scene.frame_set(f)
        body_pose(t); place(t); upd()
        for n in ("Hips", "Spine", "Spine1", "Spine2", "Neck"):
            pb(n).keyframe_insert("rotation_quaternion", frame=f)
        pb("Hips").keyframe_insert("location", frame=f)
        for side in curl_sign:
            for f_ in FINGERS:
                for i in (1, 2, 3):
                    pb(fb(side, f_, i)).keyframe_insert("rotation_quaternion", frame=f)
        for e in tg.values():
            e.keyframe_insert("location", frame=f)
        reset_pose()

    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=0, frame_end=N, only_selected=True, visual_keying=True, clear_constraints=True,
                     use_current_action=False, bake_types={"POSE"})
    act = ad.action
    act.name = NAME
    act.use_fake_user = True
    acts[NAME] = (act, N)
    bpy.data.actions.remove(src)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
    print("baked", act.name, act.frame_range[:])

    # ---- 5. 자기 검사 (굽힌 동작을 프레임마다 재생해서 잰다)
    def sample():
        rows = []
        for f in range(N + 1):
            scene.frame_set(f); upd()
            rows.append(dict(
                q={p.name: p.rotation_quaternion.copy() for p in pbs},
                hand={s: min((M @ b.head for b in tips(s)), key=lambda v: v.z) for s in ("Left", "Right")},
                toe={s: M @ pb(s + "ToeBase").tail for s in ("Left", "Right")},
                sh=(whead("LeftArm").z + whead("RightArm").z) / 2, hip=(whead("LeftUpLeg").z + whead("RightUpLeg").z) / 2,
                chord={s: chord(s) for s in ("Left", "Right")},
                knee=min(whead("LeftLeg").z, whead("RightLeg").z), head=whead("Head").z, chest=whead("Spine2").z, top=max(wtail("HeadTop_End").z, wtail("Head").z)))
        return rows
    rows = sample()
    d = max(math.degrees(rows[0]["q"][n].rotation_difference(rows[N]["q"][n]).angle) for n in rows[0]["q"])
    d = min(d, 360 - d)
    check(d < 1.0, "첫 자세 = 끝 자세 (뼈 회전 차 최대 %.2f° < 1°)" % d)

    def contact_speed(key, side):
        """짚는 구간(닿은 뒤 ~ 떼기 전, 가장자리 0.05 주기 뺌)의 뒤로 밀리는 빠르기 평균 · 미끄러짐(원래 빠르기와의 차) 평균"""
        kind = "Hand" if key == "hand" else "Foot"
        touch = TOUCH[side + kind]
        vs, slip = [], []
        for f in range(N):
            ph = ((f + 0.5) / N - touch) % 1.0
            if 0.05 <= ph <= DUTY[kind] - 0.05:
                v = (rows[f + 1][key][side] - rows[f][key][side]) * FPS
                vs.append(v.y); slip.append(math.sqrt(v.x ** 2 + (v.y - SPEED) ** 2 + v.z ** 2))
        return (sum(vs) / len(vs) if vs else 0.0), (sum(slip) / len(slip) if slip else 9.9), len(vs)
    for key, nm in (("hand", "손"), ("toe", "발")):
        for s in ("Left", "Right"):
            v, sl, n = contact_speed(key, s)
            check(n >= MINC and abs(v - SPEED) <= 0.08, "%s %s 짚는 동안 뒤로 %.2f m/s (= 원래 빠르기 %.2f ± 0.08, 짚은 프레임 %d)" % (s, nm, v, SPEED, n))
            check(sl < 0.05, "%s %s 짚는 동안 미끄러짐 %.3f m/s (< 0.05)" % (s, nm, sl))
    for s in ("Left", "Right"):
        zs = [r["hand"][s].z for r in rows[:N]]
        on = sum(1 for z in zs if z <= 0.05) / N
        check(on >= 0.25, "%s 손 발톱 끝이 바닥 0.05 m 안에 있는 몫 %.0f %% (≥ 25 %%)" % (s, on * 100))
        check(min(zs) >= CLAW_Z - 0.005, "%s 손 발톱 끝이 바닥을 안 뚫음 (가장 낮은 %.3f ≥ %.3f — Unity 팔 들기가 안 걸리는 높이)" % (s, min(zs), CLAW_Z - 0.005))
    sh = sum(r["sh"] for r in rows[:N]) / N; hp = sum(r["hip"] for r in rows[:N]) / N
    check(sh > hp, "어깨 평균 높이 %.3f > 엉덩이 %.3f (게임 %.2f / %.2f m)" % (sh, hp, sh * 1.5, hp * 1.5))
    top = min(r["top"] for r in rows[:N])
    check(top * 1.5 >= 1.9, "머리 꼭대기 가장 낮을 때 게임 %.2f m ≥ 1.9" % (top * 1.5))
    check(min(r["knee"] for r in rows) * 1.5 >= 0.3, "무릎이 바닥에 안 닿는다 (가장 낮을 때 게임 %.2f m ≥ 0.3 제안값 — 무릎 꿇고 기는 사람으로 안 보이게)" % (1.5 * min(r["knee"] for r in rows)))
    print("무릎 가장 낮을 때 %.3f (게임 %.2f m)" % (min(r["knee"] for r in rows), 1.5 * min(r["knee"] for r in rows)))
    sd = lambda k: float(np.std([r[k] for r in rows[:N]]))
    check(sd("head") <= 0.5 * sd("chest") + 1e-4, "머리 높이 흔들림 %.4f ≤ 가슴 흔들림 %.4f 의 절반" % (sd("head"), sd("chest")))
    toe0 = min(r["toe"][s].z for r in rows[:N] for s in ("Left", "Right"))
    air = sum(1 for r in rows[:N] if all(r["hand"][s].z > 0.05 and r["toe"][s].z > toe0 + 0.02 for s in ("Left", "Right")))
    check(air >= AIR if AIR else air == 0, "네 발이 다 뜬 프레임 %d (%s)" % (air, "≥ %d — 뛴다" % AIR if AIR else "0 — 걷는다"))
    cmax = max(r["chord"][s] for r in rows[:N] for s in ("Left", "Right"))
    check(cmax <= CHORD_MAX, "손가락 굽음: 뿌리 → 끝 곧은 거리 ÷ 마디 길이 합 가장 클 때 %.3f (≤ %.2f, 곧으면 1 에 가깝다)" % (cmax, CHORD_MAX))

    # 살이 바닥을 뚫는지: 손·손가락 뼈에 붙은 살 점 중 가장 낮은 것 (뼈 끝 점만 재는 위 검사로는 굽은 손가락 등이 안 잡힌다)
    body = bpy.data.objects["Miner_Body"]
    hand_g = {g.index for g in body.vertex_groups if "Hand" in g.name}
    hand_v = np.array([v.index for v in body.data.vertices if any(g.group in hand_g and g.weight > 0.3 for g in v.groups)])
    mesh_low = 9.9
    for f in range(0, N, 2):
        scene.frame_set(f); upd()
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh(); co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
        co = co.reshape(-1, 3)[hand_v]
        wz = (np.array(body.matrix_world) @ np.c_[co, np.ones(len(co))].T)[2]
        mesh_low = min(mesh_low, float(wz.min()))
    check(mesh_low >= -0.01, "손 살이 바닥을 안 뚫음: 손·손가락 살 점 가장 낮은 %.3f m ≥ −0.01 (점 %d개, 2 프레임마다)" % (mesh_low, len(hand_v)))

    if QUICK and not SHOTS:
        continue

    # ---- 6. 연속 그림 (옆·앞, 한 주기 0.1 s 간격 10장) — 바닥 판 + 헤드램프 하나
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0)); floor = bpy.context.active_object
    fm = bpy.data.materials.new("wk_floor"); fm.diffuse_color = (0.25, 0.22, 0.2, 1); floor.data.materials.append(fm)
    scene.render.engine = "BLENDER_EEVEE"; scene.render.resolution_x, scene.render.resolution_y = 400, 400
    world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam); scene.camera = cam
    lamp = bpy.data.objects.new("lamp", bpy.data.lights.new("lamp", "SUN")); scene.collection.objects.link(lamp)
    lamp.data.energy = 4; lamp.rotation_euler = (math.radians(50), 0, math.radians(30))
    def hand_cam():
        """왼손 가까이(옆에서) — 프레임마다 손을 따라간다. 손가락 굽음 판정용"""
        h = whead("LeftHand") + Vector((0, -0.05, -0.15))
        loc = h + Vector((1.1, -0.45, 0.05))
        return loc, (h - loc).to_track_quat("-Z", "Y").to_euler()
    views = {"side": (lambda: ((2.9, -0.25, 0.75), (math.radians(90), 0, math.radians(90))), 30),
             "front": (lambda: ((0.0, -3.1, 0.9), (math.radians(86), 0, 0)), 30),
             "hand": (hand_cam, 50)}
    for vname, (pose_cam, lens) in views.items():
        cam.data.lens = lens
        tiles = []
        for f in range(0, N, N // 10):
            scene.frame_set(f); upd()
            cam.location, cam.rotation_euler = pose_cam()
            scene.render.filepath = os.path.join(RENDER, "_tmp.png")
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(scene.render.filepath); a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
            im.pixels.foreach_get(a); tiles.append(a.reshape(im.size[1], im.size[0], 4)); bpy.data.images.remove(im)
        sheet = np.concatenate([np.concatenate(tiles[5:10], axis=1), np.concatenate(tiles[:5], axis=1)], axis=0)   # Blender 그림은 아랫줄이 먼저 — 윗줄 = 0~4 번째
        out = bpy.data.images.new("sheet_" + vname, sheet.shape[1], sheet.shape[0], alpha=True)
        out.pixels.foreach_set(sheet.ravel()); out.filepath_raw = os.path.join(RENDER, "%s_%s_sheet.png" % (NAME, vname))
        out.file_format = "PNG"; out.save()
        print("sheet", out.filepath_raw)
    for o in (floor, cam, lamp):
        bpy.data.objects.remove(o, do_unlink=True)
    os.remove(os.path.join(RENDER, "_tmp.png"))
NAME = ""
if QUICK:
    print("walk_knuckle QUICK %s  fails=%d %s" % ("ALL PASS" if not fails else "FAIL", len(fails), fails))
    sys.exit(0 if not fails else 2)

# ---- 7. NLA 트랙으로 더하고 GLB 내보내기 (stage12 와 같은 설정)
for tr in ad.nla_tracks:
    tr.mute = False
ad.action = None
for nm, (a, _) in acts.items():
    tr = ad.nla_tracks.new(); tr.name = nm
    strip = tr.strips.new(nm, 0, a); strip.name = nm
bpy.data.libraries.write(OUT_BLEND, {a for a, _ in acts.values()}, fake_user=True)   # 동작만 (뼈 이름으로 붙는다) — 리그째 쓰면 39 MB
print("saved", OUT_BLEND)

def glb_json(path):
    with open(path, "rb") as fh:
        fh.read(12); ln, = struct.unpack("<I", fh.read(4)); fh.read(4); j = json.loads(fh.read(ln))
        bl, = struct.unpack("<I", fh.read(4)); fh.read(4); binc = fh.read(bl)
    return j, binc
def image_hashes(path):
    j, b = glb_json(path)
    out = {}
    for im in j.get("images", []):
        bv = j["bufferViews"][im["bufferView"]]
        out[im.get("name")] = hashlib.md5(b[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]).hexdigest()
    return out
old_imgs = image_hashes(OUT_GLB) if os.path.exists(OUT_GLB) and not SABOTAGE else image_hashes(r"C:\Users\anjyo\Tunnel\unity\Assets\Tunnel\Monster\miner_rigged.glb")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS",
                          export_apply=True, export_yup=True, export_skins=True, export_image_format="AUTO")
print("exported", OUT_GLB, round(os.path.getsize(OUT_GLB) / 1e6, 2), "MB")

j, _ = glb_json(OUT_GLB)
anims = {a["name"]: a for a in j.get("animations", [])}
check(len(anims) == 16 and all(nm in anims for nm in acts), "동작 16개, %s 있음 (%d)" % (" · ".join(acts), len(anims)))
for nm, (_, n_) in acts.items():
    if nm in anims:
        ins = [j["accessors"][s["input"]] for s in anims[nm]["samplers"]]
        t0, t1 = min(a["min"][0] for a in ins), max(a["max"][0] for a in ins)
        check(abs(t0) < 1e-3 and abs(t1 - n_ / FPS) < 1e-3, "%s 시간 %.3f ~ %.3f s (0 ~ %.3f)" % (nm, t0, t1, n_ / FPS))
new_imgs = image_hashes(OUT_GLB)
# 라이선스 절차 ④ 는 TRELLIS 살·머리 그림(skin_*)만 — 갱목·못·가죽끈 그림은 09-19 timber_detail.py 가 CC0 에서 새로 굽는다
skin_new = {k: v for k, v in new_imgs.items() if k and k.startswith("skin_")}
skin_old = {k: v for k, v in old_imgs.items() if k and k.startswith("skin_")}
check(skin_new == skin_old and len(skin_new) == 7, "살·머리 그림 %d장이 이전 GLB 와 바이트까지 같다 (라이선스 절차 ④)" % len(skin_new))
props = {m["name"]: m for m in j.get("materials", []) if m["name"].startswith(("뒤틀린_갱목", "녹슨_주철", "가죽끈"))}
full = [n for n, m in props.items() if "normalTexture" in m and m.get("pbrMetallicRoughness", {}).get("baseColorTexture") and m["pbrMetallicRoughness"].get("metallicRoughnessTexture")]
check(len(props) >= 5 and len(full) == len(props), "갱목·못·가죽끈 재질 %d 개 중 색·요철·반들거림 그림이 다 있는 것 %d" % (len(props), len(full)))
joints = [j["nodes"][i]["name"] for sk in j["skins"] for i in sk["joints"]]
check(len(set(joints)) == 74 and "mixamorig:Jaw" in joints and "mixamorig:JawTip" in joints and all("mixamorig:NeckExt_%d" % i in joints for i in range(7)), "뼈 %d 개, 턱 뼈(Jaw·JawTip)·목 마디 뼈(NeckExt_0~6) 있음 (74)" % len(set(joints)))
check(any(m.get("name") == "Miner_Neck" for m in j["meshes"]), "목 관 메시 Miner_Neck 있음")
multi = [m.get("name") for m in j["meshes"] if len(m["primitives"]) != 1]
check(not multi, "메시마다 프리미티브 1개 %s" % multi)
print("walk_knuckle %s  fails=%d %s" % ("ALL PASS" if not fails else "FAIL", len(fails), fails))
sys.exit(0 if not fails else 2)
