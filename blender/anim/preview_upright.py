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
import bpy, os, sys, math, random, shutil, subprocess
from mathutils import Vector, Quaternion, Matrix

E = os.environ.get
HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
MIX = os.path.join(MT, "blender", "mixamo")
NAME = E("UP_NAME", "U2")
WALK, RUN = E("UP_WALK", "Mutant Walking"), E("UP_RUN", "Mutant Run")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "check_3d4"); os.makedirs(OUT_DIR, exist_ok=True)
FR_DIR = os.path.join(MT, "blender", "anim_render", "up_" + NAME); shutil.rmtree(FR_DIR, ignore_errors=True); os.makedirs(FR_DIR)
FPS, S = 30, 1.5
START, EYE, WALL_X, CEIL = float(E("UP_START_M", "11")) / S, 1.7 / S, 3.16 / S, 5.6 / S
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
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(80); cam.data.clip_start = 0.05
CAM0 = Vector((0.0, -START, EYE))
lamp = bpy.data.objects.new("pv_lamp", bpy.data.lights.new("pv_lamp", "SPOT")); scene.collection.objects.link(lamp)
WATTS = float(E("PV_WATTS", "600"))        # U1 은 너무 밝아 "살 벗겨진 사람"으로 보였다 — 게임에 가깝게 어둡게
lamp.data.spot_size = math.radians(120); lamp.data.spot_blend = 0.35; lamp.data.shadow_soft_size = 0.02
lamp.parent = cam; lamp.location = (0, 0.06, 0)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 854, 480, 100
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
            plan.append(dict(act=walk, f=lf(walk, wi, WALK_RATE), d=dist, look=ang, mean=mean_walk, still=still, jaw=jaw * (i + 1) / n))
do_walk(1.5)
do_stand([(-55, 0.7), (35, 1.1)])           # 서서 왼쪽을 딱 — 머물고 — 오른쪽을 딱 — 더 오래 머문다 (간격이 고르지 않게)
do_walk(1.1, look=35)                       # 본 쪽을 본 채 다시 걷는다
do_stand([(0, float(E("UP_FREEZE_S", "1.4")))], jaw=JAW_FREEZE, still=True)     # 나를 딱 — 돌이 된다, 턱만 천천히 벌어진다
rate = (RUN_GAME / S) / v_run; i = 0
while START - dist > 0.85:
    dist += (RUN_GAME / S) / FPS * min(1.0, (i + 1) / 3); i += 1
    plan.append(dict(act=run, f=lf(run, i, rate), d=dist, look=0.0, mean=mean_run, jaw=JAW_RUN, run=True))
print("UPRIGHT %s: %d frames (%.2f s), walk x%.2f = %.2f m/s game, run x%.2f" % (NAME, len(plan), len(plan) / FPS, WALK_RATE, v_walk * WALK_RATE * S, rate))

random.seed(7); shake = dip = 0.0; look = 0.0; was_up = [True, True]
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
        shake = max(shake, (0.05 if st.get("run") else 0.022) * near + 0.003); dip = DIP * (1.6 if st.get("run") else 1.0)
    legs(True)
    pb("Hips").location = pb("Hips").location + hips_axes @ Vector((0, 0, -(CROUCH + dip)))
    for nm in ARMS:                         # 팔 흔들기를 죽인다
        pb(nm).rotation_quaternion = pb(nm).rotation_quaternion.slerp(st["mean"][nm], ARM_STILL)
    upd()
    for nm in ("Spine", "Spine1", "Spine2"):
        rotate_world(nm, Matrix.Rotation(math.radians(HUNCH / 3), 4, "X"))
    rotate_world("Neck", Matrix.Rotation(math.radians(-HUNCH * 0.45), 4, "X"))
    rotate_world("Head", Matrix.Rotation(math.radians(-HUNCH * 0.45), 4, "X"))
    look += max(-12.0, min(12.0, st["look"] - look))          # 한 프레임에 12° = 0.15 s 에 55° — 딱 돌리고 멈춘다
    if abs(look) > 0.01:
        rotate_world("Spine2", Matrix.Rotation(math.radians(look * 0.2), 4, "Z"))
        rotate_world("Neck", Matrix.Rotation(math.radians(look * 0.3), 4, "Z"))
        rotate_world("Head", Matrix.Rotation(math.radians(look * 0.5), 4, "Z"))
    if P + "Jaw" in pbs:
        pb("Jaw").rotation_quaternion = Quaternion(jaw_axis, math.radians(st.get("jaw", 0.0)))
    upd()
    for o in roots:
        o.location = base[o.name] + Vector((0, -st["d"], 0))
    for s in ("Left", "Right"):
        tg[s].location = tg[s].location + Vector((0, -st["d"], 0))
    upd()
    t = n / FPS                             # 화면은 늘 살아 있다: 숨결 같은 느린 흔들림 + 발 디딜 때의 떨림
    sway = Vector((0.006 * math.sin(2 * math.pi * 0.23 * t), 0, 0.005 * math.sin(2 * math.pi * 0.31 * t + 1.0)))
    cam.location = CAM0 + sway + Vector((random.uniform(-1, 1) * shake * 0.4, 0, -shake))
    cam.rotation_euler = (math.radians(90) + 0.004 * math.sin(2 * math.pi * 0.27 * t) + random.uniform(-1, 1) * shake * 0.5,
                          0.003 * math.sin(2 * math.pi * 0.19 * t) + random.uniform(-1, 1) * shake * 0.7, 0)
    shake *= 0.6; dip *= 0.55
    near = max(START - st["d"] - 0.4, 0.2)
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4)) * (1.0 + 0.03 * math.sin(2 * math.pi * 1.7 * t))
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % n)
    bpy.ops.render.render(write_still=True)

out = os.path.join(OUT_DIR, "UP_%s.mp4" % NAME)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=0.6:color=black", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
