# 영상 후보 (제안서 3D-④ MA 1단계). walk_knuckle.py 가 동작을 구운 뒤 PREVIEW=이름 일 때 이 파일을 같은 자리에서 실행한다 — 혼자서는 안 돈다.
#   MA=1 ONLY=coil_a,charge,pounce PREVIEW=A1 PV_COIL=coil_a PV_CHARGE=charge "…/blender.exe" -b --factory-startup -P blender/anim/walk_knuckle.py
# 찍는 것: 플레이어 눈높이에서 본 "12 m 에 멈춰서 봄 1.5 s → 웅크려 굳음 1.0 s → 돌진 → 덮침". 어두운 갱도 크기의 상자 + 헤드램프 같은 원뿔 조명 하나.
# 길이는 모델 크기 1 (게임 ÷ 1.5). 고르기용 영상이다 — 통과 판정은 배포 실행 파일에서 한다. GLB·blend·게임은 안 건드린다.
import subprocess, shutil

PV = os.environ["PREVIEW"]
COIL, CHARGE = os.environ.get("PV_COIL", "coil_a"), os.environ.get("PV_CHARGE", "charge")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "check_3d4"); os.makedirs(OUT_DIR, exist_ok=True)
FR_DIR = os.path.join(RENDER, "pv_" + PV); shutil.rmtree(FR_DIR, ignore_errors=True); os.makedirs(FR_DIR)
S = 1.5                                   # Tuning.STALKER_MODEL_SCALE
START, POUNCE_AT, EYE = float(os.environ.get("PV_START_M", "9")) / S, 2.6 / S, 1.7 / S      # 시작 거리(게임 들킴은 12 m 까지지만 그 거리에선 자세가 안 보인다) · 덮침 시작 · 눈높이 1.7 m
WALL_X, CEIL = 3.16 / S, 5.6 / S
WATCH_F, LAUNCH_F = 45, 3                 # 멈춰서 봄 1.5 s · 출발해서 최고 빠르기까지 0.1 s

bpy.ops.object.mode_set(mode="OBJECT")
roots = [o for o in scene.objects if o.parent is None]
base = {o.name: o.location.copy() for o in roots}

def mat(name, col, rough=0.95):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    return m
rock = mat("pv_rock", (0.10, 0.085, 0.07))
def quad(name, loc, rot, sx, sy):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, 1); o.data.materials.append(rock); return o
L = 40.0
props = [quad("pv_floor", (0, -L / 2 + 4, 0), (0, 0, 0), WALL_X * 2, L),
         quad("pv_ceil", (0, -L / 2 + 4, CEIL), (math.pi, 0, 0), WALL_X * 2, L),
         quad("pv_wl", (WALL_X, -L / 2 + 4, CEIL / 2), (0, -math.pi / 2, 0), CEIL, L),
         quad("pv_wr", (-WALL_X, -L / 2 + 4, CEIL / 2), (0, math.pi / 2, 0), CEIL, L)]

cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(80)      # 게임 시야각 80°
cam.data.clip_start = 0.05
CAM0 = Vector((0.0, -START, EYE))
lamp = bpy.data.objects.new("pv_lamp", bpy.data.lights.new("pv_lamp", "SPOT")); scene.collection.objects.link(lamp)
lamp.data.spot_size = math.radians(120); lamp.data.spot_blend = 0.35; WATTS = float(os.environ.get("PV_WATTS", "1500")); lamp.data.energy = WATTS
lamp.data.shadow_soft_size = 0.02
lamp.parent = cam                          # 헤드램프: 눈에 붙어 같이 흔들린다
lamp.location = (0, 0.06, 0)

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 854, 480, 100
scene.render.image_settings.file_format = "PNG"
world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0.002, 0.002, 0.002, 1)
try:
    scene.view_settings.view_transform = "Standard"
except TypeError:
    pass

def use(act, f):
    ad.action = act
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    scene.frame_set(int(f)); upd()
for tr in ad.nla_tracks:
    tr.mute = True

coil, n_coil = acts[COIL]; chg, n_chg = acts[CHARGE]; pnc, n_pnc = acts[os.environ.get("PV_POUNCE", "pounce")]
v = GAITS[CHARGE]["SPEED"] / FPS           # 돌진 한 프레임에 가는 길이
hand_touch = [GAITS[CHARGE]["TOUCH"][k] for k in ("LeftHand", "RightHand")]

# 시간표: (동작, 동작 프레임, 괴물이 온 길이)
plan, dist = [], 0.0
for f in range(WATCH_F): plan.append((coil, 0, 0.0, None))
for f in range(n_coil): plan.append((coil, f, 0.0, None))
f = 0
while START - dist > POUNCE_AT:
    dist += v * min(1.0, (f + 1) / LAUNCH_F)
    ph0, ph1 = (f % n_chg) / n_chg, ((f % n_chg) + 1) / n_chg
    hit = any(ph0 <= t < ph1 for t in hand_touch)
    plan.append((chg, f % n_chg, dist, hit)); f += 1
left = START - dist - 1.35                 # 덮침: 남은 길이를 0.2 s 에 — 손이 화면을 덮는다
for f in range(n_pnc + 1):
    plan.append((pnc, f, dist + left * (f / n_pnc), None))
print("PREVIEW %s: %s + %s, %d frames (%.2f s), charge %d frames" % (PV, COIL, CHARGE, len(plan), len(plan) / FPS, f))

shake = 0.0
import random; random.seed(7)
for i, (act, af, d, hit) in enumerate(plan):
    use(act, af)
    for o in roots:
        o.location = base[o.name] + Vector((0, -d, 0))
    if hit:                                # 손이 바닥을 칠 때마다 화면이 흔들린다 — 가까울수록 세게 (원리 3: 무게는 닿는 순간에)
        shake = max(shake, 0.035 * min(1.0, (3.0 / S) / max(START - d, 0.5)) ** 0.7 + 0.004)
    cam.location = CAM0 + Vector((random.uniform(-1, 1) * shake * 0.5, 0, -shake * (1 if i % 2 else -0.6)))
    cam.rotation_euler = (math.radians(90) + random.uniform(-1, 1) * shake * 0.6, random.uniform(-1, 1) * shake * 0.8, 0)
    shake *= 0.62
    near = max(START - d - 0.4, 0.2)                                        # 게임 헤드램프의 가까운 면 감광 흉내 (REF 4 m · POW 1.4) — 안 하면 코앞에서 하얗게 탄다
    lamp.data.energy = WATTS * max(0.3, min(1.0, (near / (4.0 / S)) ** 1.4))
    scene.render.filepath = os.path.join(FR_DIR, "f%04d.png" % i)
    bpy.ops.render.render(write_still=True)

out = os.path.join(OUT_DIR, "MA_%s_%s_%s.mp4" % (PV, COIL, CHARGE))
black = int(0.6 * FPS)                     # 끝에 검은 화면 0.6 s (게임의 잡힘 화면)
r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(FR_DIR, "f%04d.png"),
                    "-vf", "tpad=stop_mode=add:stop_duration=%.2f:color=black" % (black / FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out])
print("video", out, "ffmpeg exit", r.returncode)
