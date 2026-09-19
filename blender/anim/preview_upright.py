"""서서 오는 괴물 — 영상 시험 (기준 괴물 A1 제노모프 + A4 관리인, 사용자 결정 2026-09-19: "서서 오는 것으로 바꿔도 된다").
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/anim/preview_upright.py
밑그림 = 이미 받아 둔 Mixamo "Mutant" 묶음(사람이 괴물을 연기한 모션캡처 — 수식이 아니라 기계 티가 없다). 이 뼈대가 Mixamo 뼈대라 옮겨 붙이기 없이 그대로 얹힌다.
그 위에 코드로 얹는 것: 걸으며 머리만 천천히 훑기(A1) · 걷다 말고 그 자세 그대로 돌처럼 굳어 나를 봄 · 굳음에서 바로 질주 · 발 디딜 때 화면 흔들림.
입력(안 고친다): Documents/MineTunnel/blender/miner_v4_stage16_neck.blend · blender/mixamo/*.fbx (원본 FBX 는 저장소에 안 올린다)
출력: build/check_3d4/UP_<이름>.mp4 (저장소 밖 산출물). GLB·게임은 안 건드린다. 고르기용 영상이다 — 통과 판정은 배포 실행 파일에서."""
import bpy, os, sys, math, random, shutil, subprocess
from mathutils import Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
MT = r"C:\Users\anjyo\Documents\MineTunnel"
MIX = os.path.join(MT, "blender", "mixamo")
NAME = os.environ.get("UP_NAME", "U1")
WALK, RUN, HIT = os.environ.get("UP_WALK", "Mutant Walking"), os.environ.get("UP_RUN", "Mutant Run"), os.environ.get("UP_HIT", "Mutant Swiping")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "check_3d4"); os.makedirs(OUT_DIR, exist_ok=True)
FR_DIR = os.path.join(MT, "blender", "anim_render", "up_" + NAME); shutil.rmtree(FR_DIR, ignore_errors=True); os.makedirs(FR_DIR)
FPS, S = 30, 1.5
START, EYE, WALL_X, CEIL = float(os.environ.get("UP_START_M", "11")) / S, 1.7 / S, 3.16 / S, 5.6 / S
WALK_S, FREEZE_S, HIT_AT = float(os.environ.get("UP_WALK_S", "2.6")), float(os.environ.get("UP_FREEZE_S", "1.2")), 2.2 / S
HEAD_SWEEP, SWEEP_S = 40.0, 2.4            # 걸으며 머리만 좌우 ±40°, 한 번 훑는 데 2.4 s
RUN_GAME = float(os.environ.get("UP_RUN_MS", "6.5"))     # 질주 빠르기(게임 m/s) — 동작 재생 배수를 여기에 맞춘다

bpy.ops.wm.open_mainfile(filepath=os.path.join(MT, "blender", "miner_v4_stage16_neck.blend"))
scene = bpy.context.scene; scene.render.fps = FPS
arm = bpy.data.objects["Miner_Rig"]; ad = arm.animation_data
for tr in ad.nla_tracks:
    tr.mute = True
P = "mixamorig:"
def upd(): bpy.context.view_layer.update()
def fcurves_of(act):
    return [fc for layer in act.layers for strip in layer.strips for cb in strip.channelbags for fc in cb.fcurves]

def load(stem):
    """FBX 의 동작만 가져온다. 제자리 걸음으로 만들고(엉덩이의 곧은 흐름만 뺀다 — 오르내림은 남는다) 원래 빠르기(m/s, 모델 크기 1)를 돌려준다"""
    before_o, before_a = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MIX, stem + ".fbx"))
    act = next(a for a in bpy.data.actions if a not in before_a)
    for o in [o for o in bpy.data.objects if o not in before_o]:
        bpy.data.objects.remove(o, do_unlink=True)
    use(act, act.frame_range[0]); p0 = (arm.matrix_world @ arm.pose.bones[P + "Hips"].matrix).translation.copy()
    use(act, act.frame_range[1]); p1 = (arm.matrix_world @ arm.pose.bones[P + "Hips"].matrix).translation.copy()
    dur = (act.frame_range[1] - act.frame_range[0]) / FPS
    for fc in fcurves_of(act):
        if fc.data_path.endswith('["%sHips"].location' % P) and len(fc.keyframe_points) > 1:
            k0, k1 = fc.keyframe_points[0], fc.keyframe_points[-1]
            slope = (k1.co.y - k0.co.y) / max(k1.co.x - k0.co.x, 1e-6)
            for k in fc.keyframe_points:
                k.co.y -= slope * (k.co.x - k0.co.x)
            fc.update()
    d = p1 - p0; speed = math.hypot(d.x, d.y) / dur
    print("CLIP %s: %d frames, %.2f m/s (game %.2f), drift %s" % (stem, act.frame_range[1] - act.frame_range[0], speed, speed * S, tuple(round(v, 2) for v in d)))
    return act, speed

def use(act, f):
    ad.action = act
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    scene.frame_set(int(f), subframe=f - int(f)); upd()

walk, v_walk = load(WALK); run, v_run = load(RUN); hit, _ = load(HIT)

# ---- 갱도 크기 상자 · 눈높이 카메라 · 헤드램프
roots = [o for o in scene.objects if o.parent is None]
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
WATTS = float(os.environ.get("PV_WATTS", "1500"))
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

# ---- 시간표: (동작, 동작 프레임, 온 길이, 머리 좌우 각도)
def loop_frame(act, i, rate=1.0):
    f0, f1 = act.frame_range; return f0 + (i * rate) % (f1 - f0)
plan, dist = [], 0.0
n_walk = int(WALK_S * FPS)
for i in range(n_walk):
    dist += v_walk / FPS
    plan.append((walk, loop_frame(walk, i), dist, HEAD_SWEEP * math.sin(2 * math.pi * i / (SWEEP_S * FPS))))
freeze_f = plan[-1][1]
for i in range(int(FREEZE_S * FPS)):       # 걷다 만 그 자세 그대로 돌처럼 — 머리만 0.1 s 에 나에게 딱
    plan.append((walk, freeze_f, dist, plan[n_walk - 1][3] * max(0.0, 1 - i / 3)))
rate = (RUN_GAME / S) / v_run
i = 0
while START - dist > HIT_AT + 0.9:
    dist += (RUN_GAME / S) / FPS * min(1.0, (i + 1) / 3)
    plan.append((run, loop_frame(run, i, rate), dist, 0.0)); i += 1
n_hit = int(min(hit.frame_range[1] - hit.frame_range[0], 0.5 * FPS))
left = START - dist - 0.75
for j in range(n_hit):
    plan.append((hit, hit.frame_range[0] + j * 1.6, dist + left * min(1.0, j / (n_hit * 0.6)), 0.0))
print("UPRIGHT %s: %d frames (%.2f s) — walk %.1f s at %.2f m/s game, freeze %.1f s, run x%.2f" % (NAME, len(plan), len(plan) / FPS, WALK_S, v_walk * S, FREEZE_S, rate))

head = arm.pose.bones[P + "Head"]; toes = [arm.pose.bones[P + s + "ToeBase"] for s in ("Left", "Right")]
random.seed(7); shake = 0.0; was_up = [True, True]
for n, (act, af, d, yaw) in enumerate(plan):
    use(act, af)
    if abs(yaw) > 0.01:                     # 머리만 돌린다: 몸은 가던 대로 가고 머리가 따로 훑는다
        head.rotation_quaternion = head.rotation_quaternion @ Quaternion((0, 1, 0), math.radians(yaw)); upd()
    for o in roots:
        o.location = base[o.name] + Vector((0, -d, 0))
    upd()
    for k, t in enumerate(toes):            # 발이 닿는 순간 화면 흔들림 — 가까울수록, 달릴수록 세게
        up = (arm.matrix_world @ t.matrix).translation.z > 0.13
        if was_up[k] and not up:
            shake = max(shake, (0.045 if act is run else 0.015) * min(1.0, (3.5 / S) / max(START - d, 0.6)) ** 0.8)
        was_up[k] = up
    cam.location = CAM0 + Vector((random.uniform(-1, 1) * shake * 0.4, 0, -shake))
    cam.rotation_euler = (math.radians(90) + random.uniform(-1, 1) * shake * 0.5, random.uniform(-1, 1) * shake * 0.7, 0)
    shake *= 0.6
    near = max(START - d - 0.4, 0.2)
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4))
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % n)
    bpy.ops.render.render(write_still=True)

out = os.path.join(OUT_DIR, "UP_%s.mp4" % NAME)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=0.6:color=black", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
