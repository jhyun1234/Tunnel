"""소품 하나를 혼자 놓고 찍어 본다 (맵을 굽기 전에 모양부터 — 메모리 "모양 먼저").
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/props/_preview.py -- <모듈> <나갈 폴더> ['{"옵션": 값}'] [함수 이름]
→ <폴더>/<모듈>_lamp_front.png (게임처럼: 어두운 굴 + 머리등, 눈높이 1.7 m, 3 m 앞) · _lamp_side · _lamp_close · _shape (밝게, 위 비스듬히 — 모양 확인)
  + 로그 "PREVIEW <숫자>" (삼각형 수 · 크기 · 가장 낮은 곳 · 면 없는 선 · 떠 있는 덩어리).
바닥 z = 0, 벽은 +y 쪽 y = WALL(기본 소품 뒤 0.0 — 옵션 "_wall" 로), 1.7 m 사람 막대가 옆에 선다(크기 읽기)."""
import bpy, bmesh, sys, os, json, math, importlib
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import _util
argv = sys.argv[sys.argv.index("--") + 1:]; mod, out = argv[0], argv[1]; opts = json.loads(argv[2]) if len(argv) > 2 else {}; fn = argv[3] if len(argv) > 3 else "build"
wall_y = opts.pop("_wall", None); ceil_z = opts.pop("_ceil", None); tag = opts.pop("_tag", mod if fn == "build" else mod + "_" + fn)
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
def flat(name, rgb, rough=0.75, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal; return m
mats = {k: flat(k, v, 0.05 if k == "water" else 0.55 if k in ("steel_paint", "steel_red", "steel_blue", "steel_yellow", "iron", "bare") else 0.8) for k, v in _util.MAT_KEYS.items()}
objs = getattr(importlib.import_module(mod), fn)(mats, **opts); bpy.context.view_layer.update()
rep = _util.report(objs)
# 떠 있는 덩어리: 덩어리(이어진 면)마다 다른 덩어리 · 바닥(z ≤ 0.02) · 벽 · 천장에 2 cm 안으로 닿는가를 번져 가며 센다
from mathutils.bvhtree import BVHTree
isl = []
for o in objs:
    b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world); b.verts.ensure_lookup_table(); seen = set()
    for v in b.verts:
        if v.index in seen: continue
        st, comp = [v], []
        while st:
            x = st.pop()
            if x.index in seen: continue
            seen.add(x.index); comp.append(x.co.copy()); st += [e.other_vert(x) for e in x.link_edges]
        isl.append((o.name, comp))
def grounded(comp): return any(c.z <= 0.03 for c in comp) or (wall_y is not None and any(c.y >= wall_y - 0.03 for c in comp)) or (ceil_z is not None and any(c.z >= ceil_z - 0.03 for c in comp))
ok = [grounded(c) for _, c in isl]; boxes = [(Vector((min(p.x for p in c), min(p.y for p in c), min(p.z for p in c))), Vector((max(p.x for p in c), max(p.y for p in c), max(p.z for p in c)))) for _, c in isl]
changed = True
while changed:
    changed = False
    for i in range(len(isl)):
        if ok[i]: continue
        for j in range(len(isl)):
            if ok[j] and all(boxes[i][0][k] <= boxes[j][1][k] + 0.02 and boxes[j][0][k] <= boxes[i][1][k] + 0.02 for k in range(3)): ok[i] = True; changed = True; break
flo = ["%s (%.2f, %.2f, %.2f)" % (isl[i][0], *((boxes[i][0] + boxes[i][1]) / 2)) for i in range(len(isl)) if not ok[i]]
rep["islands"] = len(isl); rep["floating_islands"] = flo[:12]; rep["floating_count"] = len(flo)
print("PREVIEW " + json.dumps(rep, ensure_ascii=False))
lo, hi = Vector(rep["lo"]), Vector(rep["hi"]); cen = (lo + hi) / 2; size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, 1.0)
# 무대: 바닥 · 벽 · 사람 막대
bm = bmesh.new(); _util.box(bm, (cen.x, cen.y, -0.05), (size * 4 + 8, size * 4 + 8, 0.1)); _util.obj("STAGE_FLOOR", bm, flat("floor", (0.07, 0.065, 0.06), 0.95))
wy = wall_y if wall_y is not None else hi.y + 1.5
bm = bmesh.new(); _util.box(bm, (cen.x, wy + 0.1, 3), (size * 4 + 8, 0.2, 6)); _util.obj("STAGE_WALL", bm, flat("wall", (0.10, 0.09, 0.08), 0.95))
if ceil_z is not None: bm = bmesh.new(); _util.box(bm, (cen.x, cen.y, ceil_z + 0.1), (size * 4 + 8, size * 4 + 8, 0.2)); _util.obj("STAGE_CEIL", bm, flat("ceil", (0.10, 0.09, 0.08), 0.95))
bm = bmesh.new(); _util.box(bm, (hi.x + 0.6, lo.y - 0.2, 0.85), (0.45, 0.3, 1.7)); _util.obj("STAGE_PERSON", bm, flat("person", (0.6, 0.15, 0.1)))
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True; bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(57); cam.data.clip_start = 0.05
lamp = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(lamp); lamp.data.energy = 900; lamp.data.spot_size = math.radians(70); lamp.data.spot_blend = 0.5; lamp.data.color = (1.0, 0.93, 0.82)
sun = bpy.data.objects.new("SUN", bpy.data.lights.new("SUN", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sun.data.energy = 3.0
sc.render.resolution_x, sc.render.resolution_y = 960, 540; os.makedirs(out, exist_ok=True)
d = max(3.0, size * 1.1)
views = [("lamp_front", (cen.x + 0.6, lo.y - d, 1.7), False), ("lamp_side", (hi.x + d * 0.8, lo.y - d * 0.5, 1.7), False), ("lamp_close", (cen.x - size * 0.25, lo.y - 1.4, 1.5), False), ("shape", (cen.x + d, lo.y - d, hi.z + d * 0.6), True)]
for nm, eye, bright in views:
    at = Vector((cen.x, cen.y, min(cen.z, 1.4) if not bright else cen.z)); cam.location = eye; q = (at - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = q.to_euler()
    lamp.location = Vector(eye) + Vector((0, 0, 0.1)); lamp.rotation_euler = q.to_euler(); lamp.hide_render = bright; sun.hide_render = not bright
    bg.inputs[0].default_value = (0.25, 0.25, 0.27, 1) if bright else (0.004, 0.004, 0.005, 1); bg.inputs[1].default_value = 1.0
    sc.render.filepath = os.path.join(out, "%s_%s.png" % (tag, nm)); bpy.ops.render.render(write_still=True)
print("PREVIEW done -> %s" % out)
