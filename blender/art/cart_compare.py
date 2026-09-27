"""광차 다시(09-27) — 옛 Blender 광차(B2)와 새 광차(조사 10 공통점, mine_props.mine_car_v2)를 광장 레일 위에 같은 빛으로 찍는다.
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/cart_compare.py
  python docs/그림/ART1_광차_다시.py        (한 장으로 — 사진 없는 판은 docs/그림, 사진 넣은 판은 build/ 만)
  MESHY=<glb> 이면 그 모델도 "meshy" 로 (가장 긴 수평 길이를 새 광차 2.05 m 에 맞추고 긴 쪽을 X 로, 밑을 레일에)
출력: build/art/cart_v2/<old|new|meshy>_<각도>.png · info.json(삼각형 · 크기). 빛은 게임이 아니다(EEVEE · 전등 500 W · 헤드램프)."""
import bpy, os, sys, math, json
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mine_props as mp

ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); OUT = os.path.join(ROOT, "build", "art", "cart_v2")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "booth_map.gltf"))
sc = bpy.context.scene
for o in sc.objects:
    if o.name.startswith(("COL_", "NAV", "PRP_Timber_")): o.hide_render = True
M = mp.game_materials(ROOT)
rails = mp.rails_path(M, [(-3.0, 1.0), (3.0, 1.0)], lambda x, y: 0.0)
CARS = {"old": mp.mine_car(M), "new": mp.mine_car_v2(M)}
if os.environ.get("MESHY"):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.environ["MESHY"])
    root = bpy.data.objects.new("MESHY", None); sc.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root: o.parent = root
    CARS["meshy"] = root
for o in list(rails.children_recursive) + [c for r in CARS.values() for c in r.children_recursive]:
    if o.type == "MESH" and o.data.materials and "uv_m" in o.data.materials[0]: mp.box_uv(o.data, 1.0 / o.data.materials[0]["uv_m"])

def meshes(root): return [o for o in root.children_recursive if o.type == "MESH"]
def bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.evaluated_get(dg).bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0.012, 0.012, 0.012, 1)
L = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); L.data.energy = 500; L.data.color = (1.0, 0.72, 0.42)
L.location = (-1.5, 1.4, 4.1); sc.collection.objects.link(L)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 28
head = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(head)
head.data.energy = 350; head.data.spot_size = math.radians(70); head.data.spot_blend = 0.5; head.data.color = (1.0, 0.93, 0.82)
sc.render.resolution_x, sc.render.resolution_y = 900, 600
rt = 0.16                                                     # 레일 윗면 (rails_path: 바닥 0 − 묻힘 0.03 + 레일 가운데 0.145 + 반높이 0.045)
info = {}
for tag, root in CARS.items():
    for k, r in CARS.items():
        for o in [r] + list(r.children_recursive): o.hide_render = k != tag
    root.location = (0.0, 1.0, rt)
    bpy.context.view_layer.update()
    if tag == "meshy":                                                        # 크기·방향 맞추기 (Meshy 크기는 제멋대로)
        lo, hi = bbox(meshes(root))
        if hi.y - lo.y > hi.x - lo.x: root.rotation_euler.z = math.pi / 2; bpy.context.view_layer.update(); lo, hi = bbox(meshes(root))
        root.scale *= 2.05 / (hi.x - lo.x); bpy.context.view_layer.update(); lo, hi = bbox(meshes(root))
        root.location += Vector((-(lo.x + hi.x) / 2, 1.0 - (lo.y + hi.y) / 2, rt - 0.02 - lo.z)); bpy.context.view_layer.update()
    lo, hi = bbox(meshes(root)); c = (lo + hi) / 2
    blo, bhi = bbox([o for o in meshes(root) if o.name.split(".")[0] not in ("CarRing", "CarCoal")] or meshes(root))   # 몸통 · 밑틀 · 바퀴 (늘어진 고리 · 석탄 무더기 빼고, 레일 윗면부터)
    info[tag] = dict(tris=sum(len(p.vertices) - 2 for o in meshes(root) for p in o.data.polygons), size=[round(bhi.x - blo.x, 2), round(bhi.y - blo.y, 2), round(bhi.z - rt, 2)])
    for ang, eye in (("34", c + Vector((2.2, -2.6, 1.3))), ("side", c + Vector((0.0, -3.4, 0.35))), ("end", c + Vector((3.0, -0.35, 0.5))), ("top", c + Vector((1.0, -1.3, 2.4)))):
        q = (c - eye).to_track_quat("-Z", "Y"); cam.location = eye; cam.rotation_euler = q.to_euler()
        head.location = eye + Vector((0, 0, 0.1)); head.rotation_euler = q.to_euler()
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, ang)); bpy.ops.render.render(write_still=True)
    print("CHECK cart %s tris %d size %s" % (tag, info[tag]["tris"], info[tag]["size"]))
json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
