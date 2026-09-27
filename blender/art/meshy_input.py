"""ART-1 차례 3 — Meshy 그림 → 3D 에 넣을 그림: Blender 로 만든 물건 하나를 단색 배경 · 고른 빛에서 세 방향으로 (앞 3/4 · 옆 · 뒤 3/4).
  PROP=car "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/meshy_input.py
  PROP=car2 … = 새 광차(mine_car_v2, 조사 10 공통점 — 09-27 58차), 게임 질감(props_tex + 상자 UV) 그대로
  python blender/art/meshy_input.py car2   (시스템 python — Blender 에 PIL 이 없어 자르기는 따로)
출력: build/art/meshy_in/<PROP>_{1,2,3}.png (1024²) + _crop.png(물건 둘레로 잘라 1024² — Meshy 에 넣는 것). 첫 장이 정면. 넣을 그림은 우리 렌더 — 생성 그림(Gemini)은 게임용으로 안 쓴다(사용자 규칙)."""
import os, sys, math
try:
    import bpy
except ImportError:                                  # 시스템 python: 찍은 그림을 물건 둘레로 잘라 정사각 1024² (배경 회색과 다른 픽셀의 상자 + 여백 6 %)
    from PIL import Image, ImageChops
    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "art", "meshy_in")
    for i in (1, 2, 3):
        f = os.path.join(OUT, "%s_%d.png" % (sys.argv[1], i)); im = Image.open(f).convert("RGB"); bgc = im.getpixel((2, 2))
        bb = ImageChops.difference(im, Image.new("RGB", im.size, bgc)).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
        cx, cy, half = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, max(bb[2] - bb[0], bb[3] - bb[1]) / 2 * 1.06
        sq = Image.new("RGB", (int(2 * half), int(2 * half)), bgc); sq.paste(im, (int(half - cx), int(half - cy)))
        sq.resize((1024, 1024), Image.LANCZOS).save(f[:-4] + "_crop.png"); print("crop", f[:-4] + "_crop.png", bb)
    sys.exit()
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROP = os.environ.get("PROP", "car")
OUT = os.path.join(ROOT, "build", "art", "meshy_in"); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
M = mp.game_materials(ROOT) if PROP == "car2" else mp.materials(ROOT)
root = {"car": lambda: mp.mine_car(M), "car2": lambda: mp.mine_car_v2(M)}[PROP]()
for o in sc.objects:
    if o.type == "MESH" and o.data.materials and "uv_m" in o.data.materials[0]: mp.box_uv(o.data, 1.0 / o.data.materials[0]["uv_m"])
objs = [o for o in sc.objects if o.type == "MESH"]
dg = bpy.context.evaluated_depsgraph_get(); lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in objs:
    for c in o.evaluated_get(dg).bound_box:
        w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
c = (lo + hi) / 2; r = (hi - lo).length / 2

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (0.55, 0.55, 0.55, 1); bg.inputs[1].default_value = 0.6
sc.render.film_transparent = False
for loc, e in (((3, -4, 5), 600), ((-4, -2, 3), 250), ((0, 5, 4), 200)):              # 앞 위 · 왼쪽 채움 · 뒤
    L = bpy.data.objects.new("L", bpy.data.lights.new("L", "AREA")); L.data.energy = e; L.data.size = 3
    L.location = c + Vector(loc); L.rotation_euler = (c - L.location).to_track_quat("-Z", "Y").to_euler(); sc.collection.objects.link(L)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
sc.render.resolution_x = sc.render.resolution_y = 1024
d = r / math.tan(math.radians(17)) * 1.05
for i, (az, el) in enumerate(((-35, 20), (-90, 12), (145, 20)), 1):                    # 앞 3/4 (−Y 쪽 = 앞) · 옆 · 뒤 3/4
    a, e = math.radians(az), math.radians(el)
    eye = c + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * d
    cam.location = eye; cam.rotation_euler = (c - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, "%s_%d.png" % (PROP, i)); bpy.ops.render.render(write_still=True)
print("CHECK meshy input %s -> %s" % (PROP, OUT))
