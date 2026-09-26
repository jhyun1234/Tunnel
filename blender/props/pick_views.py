"""PICK-1: 곡괭이 GLB 를 흰 바탕 네 방향(앞·옆·위·비스듬히)에서 찍는다 — Meshy 입력 그림 겸 눈 확인용.
  blender -b --factory-startup -P blender/props/pick_views.py -- <이름>   → build/pick1/<이름>_{front,side,top,persp}.png (1024 px)
<이름> = Assets/Tunnel/Props/<이름>.glb. 틀은 make_pick.py 와 같다(자루 +Z, 날 +X)."""
import bpy, os, sys, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "pick1"); os.makedirs(OUT, exist_ok=True)
name = sys.argv[sys.argv.index("--") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Props", name + ".glb"))
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.render.resolution_x = sc.render.resolution_y = 1024
sc.view_settings.view_transform = "Standard"
sc.world = bpy.data.worlds.new("w")
try: sc.world.use_nodes = True
except Exception: pass
bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (1, 1, 1, 1); bg.inputs["Strength"].default_value = 0.6
for rot, e in (((50, 0, 30), 3.0), ((70, 0, 200), 1.2)):
    s = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); s.data.energy = e
    s.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(s)

obs = [o for o in bpy.data.objects if o.type == "MESH"]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in obs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
ctr = (lo + hi) / 2; size = max(hi - lo)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.15
views = {"front": Vector((0, -1, 0)), "side": Vector((1, 0, 0)), "top": Vector((0.001, 0, 1)),
         "persp": Vector((math.cos(math.radians(20)) * math.sin(math.radians(-35)), -math.cos(math.radians(20)) * math.cos(math.radians(35)), math.sin(math.radians(20))))}
for v, d in views.items():
    cam.location = ctr + d.normalized() * size * 3
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, v))
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)
