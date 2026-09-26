"""PICK-1 판정 ① 재료: 곡괭이 셋을 같은 빛·같은 자리에서 찍는다 (Eevee).
  blender -b --factory-startup -P blender/props/pick_compare.py   → build/pick1/cmp_<이름>_{fp,hit,lamp}.png
  fp · hit = 게임 1인칭 자리(쉴 때 · 내려친 순간): 카메라 원점·세로 시야 80°(Tuning.CAMERA_FOV), 곡괭이는 Pickaxe.cs 가 두는 대로
         (PICK_POS · 기울기 PICK_TILT · 곡괭이 자체 PICK_ROLL·PICK_YAW · 배율), 1.4 m 앞 바위벽(ART-1 Rock031), 이마 헤드램프(60° 스폿)
  lamp = 어두운 바탕에서 비스듬히, 헤드램프 같은 따뜻한 빛 하나
좌표: glTF → Unity 는 X 를 뒤집는다(glTFast). Unity(x, y, z) → Blender(x, z, y). 회전 행렬은 Unity 값 그대로 표준 행렬."""
import bpy, os, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "pick1"); os.makedirs(OUT, exist_ok=True)
PICKS = [("old", os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "pick.gltf"), 0.75),        # 지금 게임 (PICK_SCALE 0.75)
         ("blender", os.path.join(ROOT, "Assets", "Tunnel", "Props", "pick_blender.glb"), 1.0),
         ("meshy", os.path.join(ROOT, "Assets", "Tunnel", "Props", "pick_meshy.glb"), 1.0)]
# Tuning.cs 값 (옮겨 적음 — 바뀌면 여기도)
PICK_POS = np.array([0.32, -0.42, 0.60]); TILT, YAW, ROLL, SWING = 12.0, 90.0, 10.0, 55.0; FOV = 80.0
ROCK = os.path.join(ROOT, "Assets", "Tunnel", "Art", "textures", "art_rock_Rock031_DiffRough.png")

def Rx(d): c, s = math.cos(math.radians(d)), math.sin(math.radians(d)); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(d): c, s = math.cos(math.radians(d)), math.sin(math.radians(d)); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
U2B = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]])        # Unity → Blender (손 방향이 바뀐다 — 왼손 → 오른손)
G2U = np.diag([-1, 1, 1])                                 # glTF → Unity (glTFast)
B2G = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])        # Blender(가져온 뒤) → glTF

def setup(bg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.view_settings.view_transform = "Standard"
    sc.world = bpy.data.worlds.new("w")
    try: sc.world.use_nodes = True
    except Exception: pass
    b = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    b.inputs["Color"].default_value = (*bg, 1); b.inputs["Strength"].default_value = 1.0
    return sc

def load_pick(path, scale, fp, M=None, tilt=TILT, yaw=YAW):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type != "MESH": continue
        mw = o.matrix_world.copy()
        P = np.array([mw @ v.co for v in o.data.vertices])
        if fp:   # 게임 자리로: 뷰모델 계층을 그대로 곱한다
            U = (G2U @ B2G @ P.T).T * scale
            U = (Rx(tilt) @ (Rx(ROLL) @ Ry(yaw) @ U.T)).T + PICK_POS
            P = (U2B @ U.T).T
        elif M is not None:
            P = (M @ P.T).T * scale
        o.matrix_world = Matrix.Identity(4)
        for v, p in zip(o.data.vertices, P): v.co = p
        o.data.update()
    for o in new:   # 부모 빈 물체가 있으면 떼어 둔다 (정점에 이미 구웠다)
        if o.type != "MESH": bpy.data.objects.remove(o, do_unlink=True)
    return [o for o in bpy.data.objects if o.type == "MESH" and o in new]

def spot(sc, loc, target, energy, angle, color=(1.0, 0.93, 0.8)):
    l = bpy.data.objects.new("lamp", bpy.data.lights.new("lamp", "SPOT")); sc.collection.objects.link(l)
    l.data.energy = energy; l.data.spot_size = math.radians(angle); l.data.spot_blend = 0.5; l.data.color = color
    l.location = loc; l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

for key, path, scale in PICKS:
    for tag, tilt, yaw in (("fp", TILT, YAW), ("hit", TILT + SWING, YAW), ("side", TILT, 0.0)):   # 쉴 때 / 내려친 순간(기울기 + PICK_SWING_DEG) / 참고: 머리를 옆으로(PICK_YAW 0°)
        # ── 1인칭 자리 ──
        sc = setup((0.0, 0.0, 0.0)); sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
        load_pick(path, scale, True, tilt=tilt, yaw=yaw)
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(FOV); cam.data.clip_start = 0.01
        cam.rotation_euler = (math.radians(90), 0, 0)
        bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0, 1.4, 0), rotation=(math.radians(90), 0, 0))
        wall = bpy.context.active_object; m = bpy.data.materials.new("rock")
        try: m.use_nodes = True
        except Exception: pass
        t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(ROCK); t.image.alpha_mode = "NONE"
        bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"); m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
        bs.inputs["Roughness"].default_value = 0.85; wall.data.materials.append(m)
        spot(sc, (0, 0, 0.12), (0, 5, 0.12), 60, 60)         # 이마 헤드램프 (LAMP_OFFSET 0.12 · 60°) — 게임에선 곡괭이를 안 비춘다
        spot(sc, (0, 0, 0.12), (0.3, 1, -0.4), 6, 120)       # 곡괭이 전용 약한 등 (BuildM1 PickLight: 같은 자리 · 120° · 세기 3 · 2 m) — 여기선 벽도 조금 비춘다
        sc.render.filepath = os.path.join(OUT, "cmp_%s_%s.png" % (key, tag)); bpy.ops.render.render(write_still=True); print("wrote", sc.render.filepath)
    # ── 어두운 바탕 · 비스듬히 · 램프 빛 ──
    sc = setup((0.012, 0.011, 0.010)); sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    load_pick(path, scale, False, M=Rx(180) @ Ry(-90))   # 자루를 눕혀 박물관 사진처럼 (머리 왼쪽, 날 아래)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.95
    cam.location = (-0.19, -1.5, -0.08); cam.rotation_euler = (math.radians(90), 0, 0)
    spot(sc, (0.3, -1.2, 0.5), (-0.19, 0, -0.08), 90, 50)
    spot(sc, (-1.0, -0.6, -0.5), (-0.19, 0, -0.08), 8, 60, (0.7, 0.8, 1.0))
    sc.render.filepath = os.path.join(OUT, "cmp_%s_lamp.png" % key); bpy.ops.render.render(write_still=True); print("wrote", sc.render.filepath)
