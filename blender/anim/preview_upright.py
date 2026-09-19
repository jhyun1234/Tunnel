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
  자기 검사: 얹은 머리·손이 렌더 재계산에 살아남나 · 손끝이 몸 앞으로 나가나 · 손이 바닥·벽을 안 뚫나 · 머리가 0.2 s 에 40° 넘게 도나 · 긴 정지 동안 뼈 움직임 0.
  사보타주: SABOTAGE=nofreeze(U2 버그) · nogrope(모션캡처 안 섞음) · nohold(정지 중에도 시간이 흐름) → 저마다 FAIL 로 죽는다.
출력: build/check_3d4/UP_<이름>.mp4. GLB·게임은 안 건드린다. 고르기용 영상이다 — 통과 판정은 배포 실행 파일에서."""
import bpy, os, sys, math, shutil, subprocess
from mathutils import Vector, Quaternion, Matrix

E = os.environ.get
HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
MIX = os.path.join(MT, "blender", "mixamo")
NAME = E("UP_NAME", "U4")
SEARCH = NAME.startswith("B")             # 수색 장면 (MB)
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
SEARCH_MS, STOP_M = 2.5, 4.0               # 수색 걸음(게임 m/s) · 플레이어 앞 멈추는 거리(게임 m)
CX = float(E("UP_CX", "0.5")) if SEARCH else 0.0       # 수색: 괴물이 갱도 가운데서 조금 왼쪽(화면 오른쪽)으로 온다
YAW, TILT = float(E("UP_YAW", "50")), 18.0             # 수색: 몸을 벽 쪽으로 트는 각 (나를 돌아보는 머리가 크게 돌아야 읽힌다) · 들었을 때 갸웃
HUNCH_CUT = float(E("UP_HUNCH_CUT", "0.35"))           # 더듬는 모션캡처는 제 스스로 숙이고 있다 — 우리 숙임을 이만큼 덜어야 손이 바닥을 안 뚫는다
GROPE_END = float(E("UP_GROPE_END", "0.7"))
GROPE, GROPE_RATE, HEAR_AT = E("UP_GROPE", "Creeping Zombie Walk"), float(E("UP_GROPE_RATE", "0.40")), float(E("UP_HEAR_AT", "0.3"))
NECK_OUT, NECK_S = float(E("UP_NECK", "0.25")), 1.0    # 목 내밀기 (모델 m) · 나오는 데 걸리는 초
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
quad((WALL_X, -L / 2 + 4, CEIL / 2), (0, -math.pi / 2, 0), CEIL, L); quad((-WALL_X, -L / 2 + 4, CEIL / 2), (0, math.pi / 2, 0), CEIL, L)
cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(42 if CLOSE else 80); cam.data.clip_start = 0.05
CAM0 = Vector((0.0, -START, EYE))
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
gf = 0.0
def do_sweep(to, **kw):
    """더듬기 = 모션캡처를 GROPE_RATE 배로, 빠르기를 고르지 않게(0.2~1.8배 사이를 오가며) 다시 재생. to = 클립의 어디까지(0~1)"""
    global gf
    g0, g1 = grope_act.frame_range
    while gf < to * (g1 - g0):
        tt = len(plan) / FPS
        gf += GROPE_RATE * (1.0 + 0.55 * math.sin(2 * math.pi * 0.37 * tt) + 0.25 * math.sin(2 * math.pi * 0.83 * tt + 1.3))
        plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, mean=mean_walk, stand=True, look=0.0, act2=grope_act, f2=g0 + min(gf, g1 - g0), mix=1.0, **kw))
if SEARCH:
    WALK_RATE = (SEARCH_MS / S) / v_walk    # 수색 걸음은 게임 그대로 2.5 m/s (up_walk ×1.36 — MA 판정에서 그대로 두기로 함)
    PLAYER = -(YAW + math.degrees(math.atan2(CX, STOP_M / S)))       # 몸에서 본 나의 방향
    do_walk((START - STOP_M / S) / (SEARCH_MS / S) - 1.0); do_walk(1.0, yaw=YAW)        # 마지막 1 s 는 벽 쪽으로 휘어 걷는다
    do_stand([(-55, 0.6), (30, 0.9)])       # 서서 딱 — 딱
    do_grope(NECK_S, neck=NECK_OUT, lean=10, pitch=12)                                  # 앞을 딱 — 목을 천천히 내밀어 들여다본다
    G = dict(neck=NECK_OUT, lean=float(E("UP_LEAN", "0")), crouch=float(E("UP_SQUAT", "0.18")), pitch=6)
    do_sweep(HEAR_AT, **G)
    plan[-5]["jolt"] = True                 # 내가 소리를 냈다 — 화면이 덜컥
    heard = {**plan[-1], "hold": True, "look": PLAYER, "tilt": TILT}
    plan += [{**heard, "snap": True} for _ in range(int(0.2 * FPS))]                    # 몸은 굳고 머리만 나를 딱 + 갸웃
    plan += [dict(heard) for _ in range(int(float(E("UP_HOLD_S", "2.0")) * FPS))]       # 통째로 멈춤 — "들었나?"
    do_sweep(GROPE_END, lr=2.0, **G)              # 머리가 천천히 돌아가고 마저 쓴다
    do_grope(0.8)                           # 거두고 일어선다
    do_stand([(PLAYER, 1.0)])               # 나를 딱 본다 — 끝
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
    ad.action = None; legs(False)
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
    hit = False
    for k, s in enumerate(("Left", "Right")):
        up = (M @ pb(s + "ToeBase").matrix).translation.z > 0.13
        if was_up[k] and not up and not st.get("still"): hit = True
        was_up[k] = up
    if hit:
        near = min(1.0, (3.5 / S) / max(START - st["d"], 0.6)) ** 0.8
        shake = max(shake, (0.05 if st.get("run") else 0.022) * near + 0.003); dip_to = DIP * (1.6 if st.get("run") else 1.0)
    if not hold: dip += (dip_to - dip) * 0.5; dip_to *= 0.55               # 한 프레임에 뚝 떨어지면 끊겨 보인다 — 두세 프레임에 걸쳐 내려앉는다
    legs(True)
    t, tc = n / FPS - held, n / FPS          # t = 몸의 시계(긴 정지 동안 선다) · tc = 화면의 시계
    # U3 판정: 서서 머리 돌릴 때 온몸이 멈춰 "일시정지"로 보인다 → 서 있는 동안 숨(엉덩이·가슴) · 무게 옮기기 · 팔 앞뒤 흔들림을 얹는다. 굳음(still)은 통과했으니 돌 그대로
    if not hold:
        life += ((1.0 if st.get("stand") else 0.0) - life) * 0.15
        if not st.get("still"): ft += 1.0 / FPS               # 손가락 시계 — 굳으면 같이 멈춘다
        lean += (st.get("lean", 0.0) - lean) * 0.07; squat += (st.get("crouch", 0.0) - squat) * 0.07; pitch += (st.get("pitch", 0.0) - pitch) * 0.07
        neck += max(-NECK_OUT / NECK_S / FPS, min(NECK_OUT / NECK_S / FPS, st.get("neck", 0.0) - neck))     # 목은 고른 빠르기로 천천히 (Unity MoveTowards 와 같다)
        if "yaw" in st: yaw_to = st["yaw"]
        yaw += (yaw_to - yaw) * 0.08
    pb("Hips").location = pb("Hips").location + hips_axes @ Vector((0.015 * life * math.sin(2 * math.pi * 0.21 * t), 0.35 * squat,
                                                                    -(CROUCH + squat + dip + 0.010 * life * math.sin(2 * math.pi * 0.30 * t))))
    for nm in ARMS:                         # 팔 흔들기를 죽인다
        pb(nm).rotation_quaternion = pb(nm).rotation_quaternion.slerp(st["mean"][nm], ARM_STILL * (1 - mixw))
    upd()
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians((HUNCH * (1 - HUNCH_CUT * mixw) + lean) / 3), 4, "X"))
    rotate_world("Neck", Matrix.Rotation(math.radians(-(HUNCH * (1 - HUNCH_CUT * mixw) + lean) * 0.45 + pitch * 0.4), 4, "X"))
    rotate_world("Head", Matrix.Rotation(math.radians(-(HUNCH * (1 - HUNCH_CUT * mixw) + lean) * 0.45 + pitch * 0.6), 4, "X"))
    rotate_world("Spine1", Matrix.Rotation(math.radians(1.8 * life * math.sin(2 * math.pi * 0.30 * t + 0.6)), 4, "X"))
    want, lr = st["look"], st.get("lr", 12.0)
    if not hold or st.get("snap"):                            # 머리: 한 프레임에 12° = 0.15 s 에 55° — 딱 돌리고 멈춘다. "들었나?"(snap)는 몸이 굳은 채 머리만
        look += max(-lr, min(lr, want - look)); tilt += max(-3.0, min(3.0, st.get("tilt", 0.0) - tilt))
    lag = want * 0.45 - body_look
    if not hold: body_look += lag * 0.07                                   # 상체: 머리를 뒤늦게(0.5 s 쯤) 천천히 따라간다 — 머리 각도의 45 % 까지
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians(body_look / 3), 4, "Z"))
    rotate_world("Neck", Matrix.Rotation(math.radians((look - body_look) * 0.4), 4, "Z"))
    rotate_world("Head", Matrix.Rotation(math.radians((look - body_look) * 0.6), 4, "Z"))
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
        ax = (M @ pb(s_ + "Hand").matrix).to_3x3().col[0]
        curls = finger_curls(s_, ft, st.get("run")); gc = grope_curls(ft, k)
        for f_, angs in curls.items():
            angs = tuple(a + (b_ - a) * mixw for a, b_ in zip(angs, gc[f_]))
            for i, a in enumerate(angs):
                rotate_world(fb(s_, f_, i + 1), Matrix.Rotation(curl_sign[s_] * math.radians(a), 4, ax))
    if P + "Jaw" in pbs:
        pb("Jaw").rotation_quaternion = Quaternion(jaw_axis, math.radians(st.get("jaw", 0.0)))
    upd()
    if SEARCH:
        neck_place(neck); neck_max = max(neck_max, (wpos("Head") - wpos("Neck")).length)
        if mixw > 0.9:                      # 자기 검사용 기록
            tips = [wpos(fb(s_, f_, 4)) for s_ in ("Left", "Right") for f_ in FINGERS[:4]]
            Rz = Matrix.Rotation(math.radians(yaw), 3, "Z")
            reach_max = max(reach_max, max(-q_.y for q_ in tips)); low_min = min(low_min, min(q_.z for q_ in tips))
            wall_max = max(wall_max, max(abs((Rz @ q_).x + CX) for q_ in tips))
        if st.get("snap"): snap_deg = max(snap_deg, abs(look - look_pre))
        elif not st.get("hold"): look_pre = look
        snap = [b_.matrix.copy() for b_ in order]
        still_ = st.get("hold") and not st.get("snap")
        if still_ and hold_prev:
            hold_move = max(hold_move, max(abs(x) for a, b_ in zip(snap, hold_prev) for row in (a - b_) for x in row))
        hold_prev = snap if still_ else None
    X = Matrix.Translation((CX, -st["d"], 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
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
    cam.rotation_euler = (math.radians(90) + 0.004 * math.sin(2 * math.pi * 0.27 * tc) - shake * 0.3 - (0.10 if SEARCH else 0.0),
                          0.003 * math.sin(2 * math.pi * 0.19 * tc), -0.06 if SEARCH else 0.0)       # 수색: 바닥을 쓰는 손이 보이게 살짝 아래·괴물 쪽을 본다
    shake *= 0.7
    if CLOSE:
        cam.location = Vector((0.6, -st["d"] - 2.6, 1.3))
        cam.rotation_euler = (Vector((0, -st["d"], 1.15)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    if CLOSE and SEARCH:                    # 팔·손가락이 보이게: 괴물 오른쪽 앞 낮은 곳에서 (게임 시점 아님)
        cam.location = Vector((CX - 1.0, -st["d"] - 2.4, 1.0)) + sway          # 몸을 따라 돌리면 카메라가 벽 밖으로 나간다(시험 프레임이 새까맸다) — 갱도 기준 자리
        cam.rotation_euler = (X @ Vector((0.0, -0.5, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.angle_y = math.radians(55)
    near = max(START - st["d"] - 0.4, 0.2)
    if CLOSE: near = 2.6
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4)) * (1.0 + 0.03 * math.sin(2 * math.pi * 1.7 * tc))
    if n % STEP: continue
    mats = freeze()
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
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % n)
    bpy.ops.render.render(write_still=True)
assert "head" in checked, "FAIL: 머리 돌리기 검사가 한 번도 안 돌았다"
if SEARCH:
    print("CHECK grope: fingertips reach %.2f m game in front · lowest %.3f m above floor · farthest %.2f m from centre (wall %.2f) · head snap %.0f deg in 0.2 s · neck head-to-base %.3f m · hold motion %.6f"
          % (reach_max * S, low_min, wall_max, WALL_X, snap_deg, neck_max, hold_move))
    assert "hand" in checked, "FAIL: 손 검사가 한 번도 안 돌았다 (모션캡처가 안 섞였다)"
    assert reach_max * S >= 1.2, "FAIL: 손끝이 몸 앞 1.2 m 도 안 나간다"
    assert low_min > -0.03 and wall_max < WALL_X, "FAIL: 손이 바닥·벽을 뚫는다"
    assert snap_deg >= 40, "FAIL: 들었을 때 머리가 0.2 s 에 40° 를 못 돈다"
    assert any(st.get("hold") for st in plan) and hold_move < 1e-4, "FAIL: 긴 정지 동안 뼈가 움직인다"
if STEP > 1: sys.exit(0)

out = os.path.join(OUT_DIR, "UP_%s.mp4" % NAME)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=0.6:color=black", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
