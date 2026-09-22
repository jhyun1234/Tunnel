"""곧은 길 조각의 갱목·전등을 Meshy 소품으로 갈아끼운 새 조각 (제안서 A1 1차, 2026-09-23).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/piece_v2.py
입력(안 고친다): Assets/Tunnel/Pieces/piece_straight.gltf · Assets/Tunnel/Props/timber_log.glb(fit_prop.py: 0.34 × 4.8 m, 긴 축 Y) · Assets/Tunnel/Props/mine_lamp.glb(매다는 점이 원점, 0.30 m)
출력(새 파일): Assets/Tunnel/Pieces/piece_straight_v2.gltf(.bin) + textures/prop_*.png — 원본 조각은 안 덮어쓴다(md5 검사)
하는 일: TMB_straight_<n>_post_{L,R}(기둥 0.34 × 4.8)·_cap(가로대 6.98 × 0.36)의 **그물만** 통나무로 바꾼다 — 이름·자리·회전은 그대로(고장 지지목 코드가 이름으로 찾는다).
        가로대는 통나무 토막을 눕혀(긴 축 Z → X) 이어 붙인다. 널(lag)은 그대로. PRP_straight_bulb(죽은 전구 8 cm)를 전등 소품으로 바꾸고(매다는 점 = 전선 밑) PRP_straight_socket 은 지운다.
자기 검사: TMB 이름 20개·자리 그대로 · 기둥 경계 상자 = 원본 ±5 % · 가로대 길이 = 원본 ±5 % · 전등 위 끝이 전선 밑 ±2 cm · 그림 파일 다 있음 · 원본 md5 그대로.
사보타주: SABOTAGE=renametmb(기둥 이름을 바꿈) → 이름 검사 FAIL · fatpost(기둥을 2배 굵게) → 경계 상자 FAIL"""
import bpy, os, sys, json, hashlib, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PIECES = os.path.join(ROOT, "Assets", "Tunnel", "Pieces")
PROPS = os.path.join(ROOT, "Assets", "Tunnel", "Props")
SRC = os.path.join(PIECES, "piece_straight.gltf")
OUT = os.path.join(PIECES, "piece_straight_v2.gltf")
SAB = os.environ.get("SABOTAGE", "")
MAX_STRETCH = 2.5                                   # 토막 하나를 결 방향으로 늘이는 상한 (무늬 왜곡 허용치)
def md5(p): return hashlib.md5(open(p, "rb").read()).hexdigest()
src_md5 = {f: md5(os.path.join(PIECES, f)) for f in ("piece_straight.gltf", "piece_straight.bin")}
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg); fails.append(msg) if not ok else None
def bbox(ob):
    pts = [Vector(c) for c in ob.bound_box]; lo = Vector(map(min, *pts)) if False else Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))); return lo, hi

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
piece_obs = set(bpy.data.objects)
before = {o.name: (o.matrix_world.copy(), bbox(o)) for o in piece_obs if o.name.startswith("TMB_")}

def load_prop(fn):
    old = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(PROPS, fn))
    new = [o for o in bpy.data.objects if o not in old and o.type == "MESH"]
    for o in [o for o in bpy.data.objects if o not in old and o.type != "MESH"]: bpy.data.objects.remove(o, do_unlink=True)
    assert len(new) == 1, fn
    return new[0]
log = load_prop("timber_log.glb"); lamp = load_prop("mine_lamp.glb")
# glTF Y-up → Blender Z-up: 소품의 긴 축(Y)은 Blender 에서 Z
llo, lhi = bbox(log); L_LEN = lhi.z - llo.z; L_DX, L_DY = lhi.x - llo.x, lhi.y - llo.y
print("timber_log: 길이 %.2f · 굵기 %.2f × %.2f" % (L_LEN, L_DX, L_DY))

def log_mesh(name, length, thick, along_x):
    """통나무 그물: 굵기를 맞춘 **균일 배율**(Meshy 통나무는 5:1 이라 4.8 m 기둥을 한 토막으로 늘이면 무늬가 2.8배 늘어져 검은 줄무늬가 됐다 — 09-23 1차 게임 그림)
    → 토막 n개(길이 ≈ 1.7 m)를 이어 붙인다. 토막은 같은 방향으로(윤곽이 맞아 이음이 안 보인다 — 무늬는 1.7 m 마다 되풀이). 이음 자리의 나이테 마구리는 겉면 안에 숨는다. 필요하면 눕힌다(Z → X). 원점(가운데)은 그대로"""
    fat = 2.0 if SAB == "fatpost" else 1.0
    sx, sy = thick / L_DX * fat, thick / L_DY * fat                       # 단면 두 축을 따로 굵기에 맞춘다 (Meshy 통나무 단면은 1.92 × 2.19 로 동그랗지 않다)
    s = (sx + sy) / 2                                                     # 결 방향 기본 배율 = 단면 평균 (토막 비율이 원본과 같게)
    seg = L_LEN * s; n = max(1, math.ceil(length / (seg * MAX_STRETCH))); stretch = length / (n * seg)   # 토막을 결 방향으로 MAX_STRETCH 까지 늘인다(매끈한 결은 늘여도 티가 안 난다) — timber_log3(2.2:1) 는 기둥 3 · 가로대 4 토막
    import bmesh
    bm = bmesh.new()
    for k in range(n):
        tmp = log.data.copy()
        M = Matrix.Translation((0, 0, (k + 0.5 - n / 2) * seg * stretch)) @ Matrix.Diagonal((sx, sy, s * stretch, 1.0))      # 토막을 돌리지 않는다 — 돌리면 마구리 윤곽이 안 맞아 이음 자리에 턱이 보였다(09-23)
        tmp.transform(M); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(name)
    for m in log.data.materials: me.materials.append(m)
    bm.to_mesh(me); bm.free()
    if along_x: me.transform(Matrix.Rotation(1.5707963, 4, "Y"))
    me.update()
    return me

for o in sorted(piece_obs, key=lambda o: o.name):
    if not o.name.startswith("TMB_"): continue
    lo, hi = bbox(o); ext = hi - lo
    if "_post_" in o.name:
        o.data = log_mesh(o.name + "_log", ext.z, max(ext.x, ext.y), along_x=False)
    elif o.name.endswith("_cap"):
        o.data = log_mesh(o.name + "_log", ext.x, max(ext.y, ext.z), along_x=True)
    if SAB == "renametmb" and o.name == "TMB_straight_0_post_R": o.name = "TMB_x_post_R"
# 전등: 전선(PRP_straight_cable)의 아랫면에 매단다. 옛 전구 자리(x, y)는 그대로
bulb = bpy.data.objects["PRP_straight_bulb"]; cable = bpy.data.objects["PRP_straight_cable"]
clo, chi = bbox(cable); cable_bottom = (cable.matrix_world @ Vector((0, 0, clo.z))).z
bulb.data = lamp.data.copy(); bulb.data.name = "PRP_straight_bulb"
bulb.location.z = cable_bottom; bulb.rotation_euler = (0, 0, 0); bulb.scale = (1, 1, 1)
bpy.data.objects.remove(bpy.data.objects["PRP_straight_socket"], do_unlink=True)
bpy.data.objects.remove(log, do_unlink=True); bpy.data.objects.remove(lamp, do_unlink=True)

# 소품 그림을 textures/ 에 파일로 풀어 놓는다 (조각의 다른 그림처럼 경로로 가리키게)
tex_dir = os.path.join(PIECES, "textures")
for im in bpy.data.images:
    if not im.name.startswith("prop_"): continue
    ext = ".jpg" if im.file_format == "JPEG" else ".png"
    im.filepath_raw = os.path.join(tex_dir, im.name + ext); im.file_format = "JPEG" if ext == ".jpg" else "PNG"; im.save()
    im.filepath = im.filepath_raw

# ---- 자기 검사
bpy.context.view_layer.update()
after = {o.name: (o.matrix_world.copy(), bbox(o)) for o in bpy.data.objects if o.name.startswith("TMB_")}
check(set(after) == set(before) and len(after) == 20, "TMB 이름 20개 그대로 (%d개, 빠진 것 %s)" % (len(after), sorted(set(before) - set(after))))
pose_ok = all(n in after and max(abs(a - b) for a, b in zip(after[n][0].translation, before[n][0].translation)) < 1e-4 for n in before)
check(pose_ok, "TMB 자리 그대로")
for n in ("TMB_straight_0_post_L", "TMB_straight_0_cap"):
    if n in after:
        b0, b1 = before[n][1], after[n][1]; e0, e1 = b0[1] - b0[0], b1[1] - b1[0]
        check(all(abs(e1[i] - e0[i]) <= e0[i] * 0.05 for i in range(3)), "%s 경계 상자 %.2f × %.2f × %.2f = 원본 %.2f × %.2f × %.2f ±5 %%" % (n, *e1, *e0))
blo, bhi = bbox(bulb); top = (bulb.matrix_world @ Vector((0, 0, bhi.z))).z
check(abs(top - cable_bottom) < 0.02, "전등 위 끝 z %.3f = 전선 밑 %.3f ±2 cm (전등 높이 %.2f)" % (top, cable_bottom, bhi.z - blo.z))

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLTF_SEPARATE", export_keep_originals=True, export_apply=True, export_yup=True, export_extras=True)
doc = json.load(open(OUT, encoding="utf-8"))
uris = [im["uri"] for im in doc.get("images", [])]
missing = [u for u in uris if not os.path.exists(os.path.join(PIECES, u.replace("%20", " ")))]
names = [n.get("name", "") for n in doc["nodes"]]
check(not missing and all(u.startswith("textures/") for u in uris), "그림 %d장 전부 textures/ 에 있음 (없는 것 %s)" % (len(uris), missing))
check(sum(n.startswith("TMB_straight_") for n in names) == 20 and sum(n.startswith("SLOT_Pocket_") for n in names) == 4 and sum(n.startswith("COL_") for n in names) == 3,
      "새 gltf 노드: TMB %d · SLOT 4 · COL 3" % sum(n.startswith("TMB_straight_") for n in names))
tris = sum(doc["accessors"][p["indices"]]["count"] // 3 for m in doc["meshes"] for p in m["primitives"])
print("wrote %s · 삼각형 %d (원본 4,976)" % (os.path.basename(OUT), tris))
check(all(md5(os.path.join(PIECES, f)) == h for f, h in src_md5.items()), "원본 조각 md5 그대로")
print("piece_v2: ALL PASS" if not fails else "piece_v2: FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
