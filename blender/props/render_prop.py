"""맞춘 소품 GLB 를 앞·옆·위에서 찍는다 (Workbench, 그림 포함). 판정·눈 확인용.
  blender -b --factory-startup -P blender/props/render_prop.py -- <이름> [<이름> …]  → build/check_props/<이름>_sheet.png (3칸 가로)"""
import bpy, os, sys, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "check_props"); os.makedirs(OUT, exist_ok=True)
names = sys.argv[sys.argv.index("--") + 1:]

for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Props", name + ".glb"))
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    ctr = (lo + hi) / 2; size = max(hi - lo)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = 480; sc.render.resolution_y = 480; sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.18, 0.18, 0.18)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.15
    shots = []
    for tag, d, up in (("front", Vector((0, -1, 0)), Vector((0, 0, 1))), ("side", Vector((1, 0, 0)), Vector((0, 0, 1))), ("top", Vector((0, 0, 1)), Vector((0, 1, 0)))):
        cam.location = ctr - d * size * 3
        cam.rotation_euler = (d).to_track_quat("-Z", "Y").to_euler() if tag != "top" else (0, 0, 0)
        if tag == "top": cam.rotation_euler = (0, 0, 0)
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, tag)); bpy.ops.render.render(write_still=True); shots.append(sc.render.filepath)
    # 가로로 붙이기
    ims = [bpy.data.images.load(p) for p in shots]
    W = sum(i.size[0] for i in ims); H = max(i.size[1] for i in ims)
    sheet = bpy.data.images.new("sheet", W, H); px = [0.0] * (W * H * 4); x0 = 0
    for im in ims:
        w, h = im.size; src = im.pixels[:]
        for y in range(h):
            row = src[y * w * 4:(y + 1) * w * 4]
            px[(y * W + x0) * 4:(y * W + x0 + w) * 4] = row
        x0 += w
    sheet.pixels = px; sheet.filepath_raw = os.path.join(OUT, name + "_sheet.png"); sheet.file_format = "PNG"; sheet.save()
    print("sheet", sheet.filepath_raw, "size %.2f x %.2f x %.2f m (blender z-up)" % tuple(hi - lo))
