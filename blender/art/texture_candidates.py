"""ART-1 차례 1 — 질감 후보를 진짜 부스 맵(광장)에 입혀 같은 빛으로 찍는다.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/art/texture_candidates.py
  python docs/그림/ART1_질감_후보.py        (찍은 그림을 한 장으로)

후보 질감(CC0 — Poly Haven · ambientCG, 1K)은 build/art/cand_tex/<id>_{Color,NormalGL,Roughness}.jpg 에 미리 받아 둔다
(받는 법은 제안서 ART-1 "차례 1"). 게임 파일(Assets)은 안 건드린다 — 맵 glTF 를 읽기만 한다.
빛은 게임과 같지 않다(Blender EEVEE · 전등 120 W · 헤드램프 500 W) — 후보끼리 비교용.
"""
import bpy, os, math
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "build", "art", "cand_tex")
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
OUT = os.path.join(ROOT, "build", "art", "cand")
os.makedirs(OUT, exist_ok=True)

# (종류, 재질, 후보 id) — "now" = 지금 게임 질감
CANDS = [("wall", "MAT_RockWall_EXPORT", i) for i in ("now", "Rock031", "Rock022", "Rock030", "Rock050")] \
      + [("coal", "MAT_RockWall_EXPORT", i) for i in ("Rock035", "Rock037", "Rock033", "dark_rock")] \
      + [("floor", "MAT_Floor_EXPORT", i) for i in ("now", "brown_mud_03", "rocks_ground_02", "stony_dirt_path", "brown_mud_02")]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(PIECES, "booth_map.gltf"))
sc = bpy.context.scene
for o in sc.objects:
    if o.name.startswith(("COL_", "PRP_", "NAV")): o.hide_render = True

# 재질마다 그림 마디: 이름 끝(_Diffuse · _Rough · _nor_gl)으로 찾는다
SLOT = {"_Diffuse": "Color", "_Rough": "Roughness", "_nor_gl": "NormalGL"}
def img_nodes(mat):
    out = {}
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            for k, s in SLOT.items():
                if os.path.splitext(n.image.name)[0].endswith(k): out[s] = n
    return out
MATS = {m.name: m for m in bpy.data.materials}
NODES = {mn: img_nodes(MATS[mn]) for mn in ("MAT_RockWall_EXPORT", "MAT_Floor_EXPORT")}   # 처음 한 번 — 바꾼 뒤엔 그림 이름으로 못 찾는다
ORIG = {mn: {s: n.image for s, n in nd.items()} for mn, nd in NODES.items()}
for mn, d in ORIG.items(): assert set(d) == {"Color", "Roughness", "NormalGL"}, "FAIL: %s 그림 마디 %s" % (mn, list(d))

def use(mn, cid):
    for s, n in NODES[mn].items():
        if cid == "now": n.image = ORIG[mn][s]; continue
        im = bpy.data.images.load(os.path.join(TEX, "%s_%s.jpg" % (cid, s)), check_existing=True)
        im.colorspace_settings.name = "sRGB" if s == "Color" else "Non-Color"
        n.image = im

# 빛: 광장 전등 둘(SLOT_Light_1·2) + 헤드램프(카메라에 붙은 스포트)
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0, 0, 0, 1)
for nm in ("SLOT_Light_1", "SLOT_Light_2"):
    L = bpy.data.objects.new("LAMP", bpy.data.lights.new("LAMP", "POINT")); L.data.energy = 500; L.data.color = (1.0, 0.72, 0.42)
    L.location = sc.objects[nm].matrix_world.translation - Vector((0, 0, 0.3)); sc.collection.objects.link(L)
head = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(head)
head.data.energy = 900; head.data.spot_size = math.radians(70); head.data.spot_blend = 0.5; head.data.color = (1.0, 0.93, 0.82)
cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 18; cam.data.clip_start = 0.05
sc.render.resolution_x, sc.render.resolution_y = 960, 540

# 보는 자리: 넓게 = 첫 자리에서 LOOK 쪽(게임 캡처 26_booth_station 과 같은 방향) · 가까이 = 그 방향 벽 1.4 m 앞 / 바닥은 발밑 비스듬히
sp = sc.objects["SPAWN_Player"].matrix_world.translation; lk = sc.objects["LOOK_Player"].matrix_world.translation
eye = sp + Vector((0, 0, 1.6)); d = (lk - eye); d.z = 0; d.normalize()
dg = bpy.context.evaluated_depsgraph_get()
dn = Vector((d.x * math.cos(0.6) - d.y * math.sin(0.6), d.x * math.sin(0.6) + d.y * math.cos(0.6), 0))   # 가까이는 35° 왼쪽 — 정면엔 바위 틈이 있다
hit, loc, *_ = sc.ray_cast(dg, eye, dn)
assert hit, "FAIL: 앞 벽을 못 찾음"
VIEWS = {"wide": (eye, eye + d * 10 + Vector((0, 0, -0.3))),
         "near_wall": (loc - dn * 1.4, loc + Vector((0, 0, 0.1))),
         "near_floor": (eye, eye + d * 1.6 + Vector((0, 0, -1.6)))}

def shoot(tag, view):
    e, at = VIEWS[view]
    q = (Vector(at) - Vector(e)).to_track_quat("-Z", "Y")
    cam.location = e; cam.rotation_euler = q.to_euler()
    head.location = Vector(e) + Vector((0, 0, 0.1)); head.rotation_euler = q.to_euler(); head.data.energy = 900 if view == "wide" else 180   # 가까이는 1.4 m 라 약하게
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, view)); bpy.ops.render.render(write_still=True)

for kind, mn, cid in CANDS:
    use("MAT_RockWall_EXPORT", "now"); use("MAT_Floor_EXPORT", "now"); use(mn, cid)
    shoot("%s_%s" % (kind, cid), "wide")
    shoot("%s_%s" % (kind, cid), "near_floor" if kind == "floor" else "near_wall")
print("CHECK texture candidates -> %s (%d)" % (OUT, len(CANDS) * 2))
