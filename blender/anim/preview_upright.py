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
출력: build/check_3d4/UP_<이름>.mp4. GLB·게임은 안 건드린다. 고르기용 영상이다 — 통과 판정은 배포 실행 파일에서."""
import bpy, os, sys, math, shutil, subprocess
from mathutils import Vector, Quaternion, Matrix

E = os.environ.get
HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
MIX = os.path.join(MT, "blender", "mixamo")
NAME = E("UP_NAME", "U4")
CLOSE = E("UP_CAM") == "close"           # 손가락·팔을 보려고: 괴물 2 m 앞에서 뒷걸음치며 따라가는 카메라 (게임 시점 아님)
STEP = int(E("UP_STEP", "1"))             # 빠른 확인: N 프레임마다 한 장만 굽고 영상은 안 만든다
WALK, RUN = E("UP_WALK", "Mutant Walking"), E("UP_RUN", "Mutant Run")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "check_3d4"); os.makedirs(OUT_DIR, exist_ok=True)
FR_DIR = os.path.join(MT, "blender", "anim_render", "up_" + NAME); shutil.rmtree(FR_DIR, ignore_errors=True); os.makedirs(FR_DIR)
FPS, S = 30, 1.5
START, EYE, WALL_X, CEIL = float(E("UP_START_M", "9")) / S, 1.7 / S, 3.16 / S, 5.6 / S
HUNCH, CROUCH, ARM_STILL = float(E("UP_HUNCH", "42")), float(E("UP_CROUCH", "0.16")), float(E("UP_ARM_STILL", "0.85"))
WALK_RATE, RUN_GAME = float(E("UP_WALK_RATE", "0.72")), float(E("UP_RUN_MS", "6.5"))
DIP = float(E("UP_DIP", "0.05"))           # 발 디딜 때 엉덩이가 내려앉는 깊이 (모델 m)
JAW_FREEZE, JAW_RUN = 22.0, 40.0

bpy.ops.wm.open_mainfile(filepath=os.path.join(MT, "blender", "miner_v4_stage16_neck.blend"))
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
print("curl sign", curl_sign)
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
roots = [o for o in scene.objects if o.parent is None and o.name not in ("tg_Left", "tg_Right")]
base = {o.name: o.location.copy() for o in roots}
rock = bpy.data.materials.new("pv_rock"); rock.use_nodes = True
b = next(n for n in rock.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.10, 0.085, 0.07, 1); b.inputs["Roughness"].default_value = 0.95
def quad(loc, rot, sx, sy):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.scale = (sx, sy, 1); o.data.materials.append(rock)
L = 40.0
quad((0, -L / 2 + 4, 0), (0, 0, 0), WALL_X * 2, L); quad((0, -L / 2 + 4, CEIL), (math.pi, 0, 0), WALL_X * 2, L)
quad((WALL_X, -L / 2 + 4, CEIL / 2), (0, -math.pi / 2, 0), CEIL, L); quad((-WALL_X, -L / 2 + 4, CEIL / 2), (0, math.pi / 2, 0), CEIL, L)
cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(42 if CLOSE else 80); cam.data.clip_start = 0.05
CAM0 = Vector((0.0, -START, EYE))
lamp = bpy.data.objects.new("pv_lamp", bpy.data.lights.new("pv_lamp", "SPOT")); scene.collection.objects.link(lamp)
WATTS = float(E("PV_WATTS", "600"))        # U1 은 너무 밝아 "살 벗겨진 사람"으로 보였다 — 게임에 가깝게 어둡게
lamp.data.spot_size = math.radians(120); lamp.data.spot_blend = 0.35; lamp.data.shadow_soft_size = 0.02
lamp.parent = cam; lamp.location = (0, 0.06, 0)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1280, 720, 100
scene.render.image_settings.file_format = "PNG"
world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0.002, 0.002, 0.002, 1)
try:
    scene.view_settings.view_transform = "Standard"
except TypeError:
    pass

# ---- 시간표: dict(act, f, d, look(머리 좌우 목표°), still(굳음), jaw°)
def lf(act, i, rate): f0, f1 = act.frame_range; return f0 + (i * rate) % (f1 - f0)
plan, dist, wi = [], 0.0, 0
def do_walk(sec, look=0.0):
    global dist, wi
    for _ in range(int(sec * FPS)):
        dist += v_walk * WALK_RATE / FPS; wi += 1
        plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, look=look, mean=mean_walk))
def do_stand(looks, jaw=0.0, still=False):      # 걷다 만 자세로 서서 — looks = [(머리 각도, 머무는 초), …]
    for ang, sec in looks:
        n = int(sec * FPS)
        for i in range(n):
            plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, look=ang, mean=mean_walk, still=still, stand=not still, jaw=jaw * (i + 1) / n))
do_walk(1.5)
do_stand([(-55, 0.7), (35, 1.1)])           # 서서 왼쪽을 딱 — 머물고 — 오른쪽을 딱 — 더 오래 머문다 (간격이 고르지 않게)
do_walk(1.1, look=35)                       # 본 쪽을 본 채 다시 걷는다
do_stand([(0, float(E("UP_FREEZE_S", "1.4")))], jaw=JAW_FREEZE, still=True)     # 나를 딱 — 돌이 된다, 턱만 천천히 벌어진다
rate = (RUN_GAME / S) / v_run; i = 0
while START - dist > 0.85:
    dist += (RUN_GAME / S) / FPS * min(1.0, (i + 1) / 3); i += 1
    plan.append(dict(act=run, f=lf(run, i, rate), d=dist, look=0.0, mean=mean_run, jaw=JAW_RUN, run=True, ri=i))
print("UPRIGHT %s: %d frames (%.2f s), walk x%.2f = %.2f m/s game, run x%.2f" % (NAME, len(plan), len(plan) / FPS, WALK_RATE, v_walk * WALK_RATE * S, rate))

# U2 의 버그(09-19 사용자 판정 "걸음이 U1 과 똑같다 · 머리 돌리기가 없다"로 드러남): 렌더가 동작(action)을 다시 계산해
# 모션캡처에 키가 있는 뼈(엉덩이·팔·척추·목·머리)에 손으로 얹은 값을 전부 지웠다 — 키가 없는 턱만 살아남았다.
# 그래서 얹은 뒤의 자세를 통째로 떠서(freeze) 동작을 떼고 뼈에 직접 박은 다음 굽는다.
order = [b for b in pbs if b.parent is None]
for b in order: order.extend(b.children)
def freeze():
    mats = {b.name: b.matrix.copy() for b in order}           # IK 까지 계산된 결과
    ad.action = None; legs(False)
    for b in order:
        if b.parent:
            rest = mats[b.parent.name] @ b.parent.bone.matrix_local.inverted() @ b.bone.matrix_local
            b.matrix_basis = rest.inverted() @ mats[b.name]
        else:
            b.matrix_basis = b.bone.matrix_local.inverted() @ mats[b.name]
    upd()
    return mats
shake = dip = dip_to = 0.0; look = body_look = life = ft = 0.0; was_up = [True, True]; checked = False
jaw_axis = Vector((1, 0, 0))
for n, st in enumerate(plan):
    for o in roots:                         # 뼈 계산은 늘 처음 자리에서 (M 이 그 자리 기준) — 끝에서 과녁과 같이 옮긴다
        o.location = base[o.name]
    legs(False); use(st["act"], st["f"])
    for s in ("Left", "Right"):             # 원래 모션캡처의 발목 자리·발 방향을 과녁으로
        W = M @ pb(s + "Foot").matrix
        tg[s].location = W.translation; tg[s].rotation_quaternion = W.to_quaternion()
    hit = False
    for k, s in enumerate(("Left", "Right")):
        up = (M @ pb(s + "ToeBase").matrix).translation.z > 0.13
        if was_up[k] and not up and not st.get("still"): hit = True
        was_up[k] = up
    if hit:
        near = min(1.0, (3.5 / S) / max(START - st["d"], 0.6)) ** 0.8
        shake = max(shake, (0.05 if st.get("run") else 0.022) * near + 0.003); dip_to = DIP * (1.6 if st.get("run") else 1.0)
    dip += (dip_to - dip) * 0.5; dip_to *= 0.55               # 한 프레임에 뚝 떨어지면 끊겨 보인다 — 두세 프레임에 걸쳐 내려앉는다
    legs(True)
    t = n / FPS
    # U3 판정: 서서 머리 돌릴 때 온몸이 멈춰 "일시정지"로 보인다 → 서 있는 동안 숨(엉덩이·가슴) · 무게 옮기기 · 팔 앞뒤 흔들림을 얹는다. 굳음(still)은 통과했으니 돌 그대로
    life += ((1.0 if st.get("stand") else 0.0) - life) * 0.15
    if not st.get("still"): ft += 1.0 / FPS                   # 손가락 시계 — 굳으면 같이 멈춘다
    pb("Hips").location = pb("Hips").location + hips_axes @ Vector((0.015 * life * math.sin(2 * math.pi * 0.21 * t), 0,
                                                                    -(CROUCH + dip + 0.010 * life * math.sin(2 * math.pi * 0.30 * t))))
    for nm in ARMS:                         # 팔 흔들기를 죽인다
        pb(nm).rotation_quaternion = pb(nm).rotation_quaternion.slerp(st["mean"][nm], ARM_STILL)
    upd()
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians(HUNCH / 3), 4, "X"))
    rotate_world("Neck", Matrix.Rotation(math.radians(-HUNCH * 0.45), 4, "X"))
    rotate_world("Head", Matrix.Rotation(math.radians(-HUNCH * 0.45), 4, "X"))
    rotate_world("Spine1", Matrix.Rotation(math.radians(1.8 * life * math.sin(2 * math.pi * 0.30 * t + 0.6)), 4, "X"))
    look += max(-12.0, min(12.0, st["look"] - look))          # 머리: 한 프레임에 12° = 0.15 s 에 55° — 딱 돌리고 멈춘다
    lag = st["look"] * 0.45 - body_look
    body_look += lag * 0.07                                   # 상체: 머리를 뒤늦게(0.5 s 쯤) 천천히 따라간다 — 머리 각도의 45 % 까지
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians(body_look / 3), 4, "Z"))
    rotate_world("Neck", Matrix.Rotation(math.radians((look - body_look) * 0.4), 4, "Z"))
    rotate_world("Head", Matrix.Rotation(math.radians((look - body_look) * 0.6), 4, "Z"))
    for k, s_ in enumerate(("Left", "Right")):
        if st.get("run"):                                     # U3 판정: 두 팔로 잡겠다는 듯 앞으로 뻗고 벌려서 — 모션캡처의 팔 펌프질은 20 % 만 남긴다
            r = min(1.0, (st["ri"] + 1) / 8) * 0.8
            sx = 1.0 if (M @ pb(s_ + "Arm").matrix).translation.x > 0 else -1.0
            aim(s_ + "Arm", (sx * 0.38, -1, -0.10), r); aim(s_ + "ForeArm", (sx * 0.12, -1, 0.22), r)
        elif life > 0.01:                                     # 서 있을 때: 팔이 앞뒤로 천천히, 두 팔 엇박자 + 상체가 돌 때 팔이 뒤처진다
            sw = life * (7.0 * math.sin(2 * math.pi * 0.33 * t + k * 2.1) + lag * 0.5)
            rotate_world(s_ + "Arm", Matrix.Rotation(math.radians(sw), 4, "X"))
            rotate_world(s_ + "ForeArm", Matrix.Rotation(math.radians(life * 5.0 * math.sin(2 * math.pi * 0.33 * t + k * 2.1 - 0.9)), 4, "X"))
        ax = (M @ pb(s_ + "Hand").matrix).to_3x3().col[0]
        for f_, angs in finger_curls(s_, ft, st.get("run")).items():
            for i, a in enumerate(angs):
                rotate_world(fb(s_, f_, i + 1), Matrix.Rotation(curl_sign[s_] * math.radians(a), 4, ax))
    if P + "Jaw" in pbs:
        pb("Jaw").rotation_quaternion = Quaternion(jaw_axis, math.radians(st.get("jaw", 0.0)))
    upd()
    for o in roots:
        o.location = base[o.name] + Vector((0, -st["d"], 0))
    for s in ("Left", "Right"):
        tg[s].location = tg[s].location + Vector((0, -st["d"], 0))
    upd()
    # 화면은 늘 살아 있다: 숨결 같은 느린 흔들림 + 발 디딜 때의 떨림
    sway = Vector((0.006 * math.sin(2 * math.pi * 0.23 * t), 0, 0.005 * math.sin(2 * math.pi * 0.31 * t + 1.0)))
    # U2 판정 "영상이 끊긴다": 발 디딜 때 화면을 프레임마다 무작위로 튀게 한 것이 빠진 프레임처럼 보였다 → 무작위 없이 아래로 눌렸다 돌아오기만
    cam.location = CAM0 + sway + Vector((0, 0, -shake))
    cam.rotation_euler = (math.radians(90) + 0.004 * math.sin(2 * math.pi * 0.27 * t) - shake * 0.3,
                          0.003 * math.sin(2 * math.pi * 0.19 * t), 0)
    shake *= 0.7
    if CLOSE:
        cam.location = Vector((0.6, -st["d"] - 2.6, 1.3))
        cam.rotation_euler = (Vector((0, -st["d"], 1.15)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    near = max(START - st["d"] - 0.4, 0.2)
    if CLOSE: near = 2.6
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4)) * (1.0 + 0.03 * math.sin(2 * math.pi * 1.7 * t))
    if n % STEP: continue
    mats = freeze()
    if not checked and abs(look) > 30:      # 자기 검사: 프레임을 다시 계산해도(렌더가 하는 일) 돌린 머리가 그대로인가. SABOTAGE=nofreeze 로 U2 버그를 되살리면 여기서 죽는다
        if E("SABOTAGE") == "nofreeze": use(st["act"], st["f"])
        scene.frame_set(scene.frame_current); upd()
        d = math.degrees((pb("Head").matrix.to_quaternion().rotation_difference(mats[P + "Head"].to_quaternion())).angle)
        print("CHECK head survives re-evaluation: off by %.1f deg (look %.0f)" % (d, look))
        assert d < 1.0, "FAIL: 얹은 자세가 렌더 때 지워진다"
        checked = True
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % n)
    bpy.ops.render.render(write_still=True)
assert checked, "FAIL: 머리 돌리기 검사가 한 번도 안 돌았다"
if STEP > 1: sys.exit(0)

out = os.path.join(OUT_DIR, "UP_%s.mp4" % NAME)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=0.6:color=black", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
