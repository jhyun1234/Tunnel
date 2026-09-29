"""3D-P — 플레이어 소품(안전모 · 램프 · 배터리 · 수통 · 탄띠)을 조사 13 치수대로 코드로 만든다 (제안서 docs/제안서_3DP_플레이어_모델.md, 09-29 승인).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/props/make_player_props.py
출력: build/player/player_props.glb (차례 1 은 밑그림 판정용 — 게임 자리 Assets/Tunnel/Player/ 는 차례 3 에서)
모듈로도 쓴다: blender/rig/player_blockout.py 가 build_* 를 불러 몸에 단다(탄띠 둘레는 몸 허리에 맞춘다).
틀: Blender Z 위 · 앞 = −Y · 물체마다 재질 하나(glTFast 규칙과 같게 — 움직이지 않는 물건이라 꼭 필요하진 않지만 한 규칙으로).
자기 검사(내보낸 GLB 를 다시 읽어서, FAIL 이면 종료 1): 안전모 28 × 22.5 × 15 cm · 램프 머리 지름 6.5 · 깊이 7 cm ·
    배터리 13 × 5 × 19 cm(뚜껑 빼고) · 탄띠 폭 6 cm · 번호 세 곳 · 물체마다 재질 하나
사보타주: SABOTAGE=bighelmet(안전모 1.2 배) · flatbattery(배터리 두께 · 너비 바꿈) → 각각 FAIL"""
import bpy, bmesh, os, sys, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SAB = os.environ.get("SABOTAGE", "")

# ── 치수 (m) — 조사 13. ✎ = 기록 없음, 지어낸 값 ──
HELMET_L, HELMET_W, HELMET_H = 0.28, 0.225, 0.15   # 문경 28 × 22 × 15 · 영국 1981 275 × 216 × 125 mm
SHELL_L, SHELL_W, DOME_H = 0.24, 0.20, 0.128      # 챙 뺀 껍데기 — 보령 '지름 20' = 껍데기 폭, 앞뒤 챙 2 cm · 옆 1.25 cm(사진에서 잼)
BRIM_DROP = 0.010                                  # 챙이 바깥으로 처지는 만큼(사진에서 잼)
RIDGE_W, RIDGE_H = 0.024, 0.008                    # 위 가운데 골(k06 · k07, 사진에서 잼)
BRACKET_W, BRACKET_H = 0.050, 0.034                # 앞 네모 쇠 받침, 나사 4 (k07, 사진에서 잼)
LAMP_D, LAMP_DEPTH = 0.065, 0.070                  # 램프 머리 — 보령 사진 6~7 cm · 영국 70 × 75 × 73 mm
BAT_W, BAT_T, BAT_H, LID_H = 0.13, 0.05, 0.19, 0.022   # 보령 13 × 5 × 19 cm + 알루미늄 뚜껑(사진에서 잼)
BELT_W, BELT_LEN = 0.06, 0.88                      # 문경 요대 81~91 × 6 cm
CANTEEN = (0.12, 0.07, 0.17)                       # ✎ 수통 너비 · 두께 · 높이 — 기록 없음(군용 수통 모양 어림)
NUMBER = os.environ.get("HELMET_NUMBER", "127")    # ✎ 안전모 번호 — 기획서 '안전모 번호', 실제 기록 없음. 게임에선 그림만 바꾼다

if SAB == "bighelmet":
    HELMET_L, HELMET_W, HELMET_H, SHELL_L, SHELL_W, DOME_H = (v * 1.2 for v in (HELMET_L, HELMET_W, HELMET_H, SHELL_L, SHELL_W, DOME_H))
if SAB == "flatbattery":
    BAT_W, BAT_T = BAT_T, BAT_W

COL = dict(helmet=(0.72, 0.52, 0.08), metal=(0.55, 0.55, 0.56), alu=(0.70, 0.71, 0.72), lampbody=(0.05, 0.05, 0.05),
           bezel=(0.80, 0.62, 0.06), lens=(1.0, 0.93, 0.78), number=(0.85, 0.85, 0.82), battery=(0.45, 0.05, 0.035),
           olive=(0.17, 0.19, 0.10), cord=(0.03, 0.03, 0.03))


def mat(name, key, rough=0.6, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    c = COL[key]
    b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*c, 1); b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*c, 1)
    return m


def obj_from_bm(name, bm, material, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o


def dome_point(u, v):
    """껍데기 위 점. u = 둘레 각(0 = 앞 −Y), v = 0(밑) ~ π/2(꼭대기)."""
    return Vector((SHELL_W / 2 * math.cos(v) * math.sin(u), -SHELL_L / 2 * math.cos(v) * math.cos(u), DOME_H * math.sin(v)))


def dome_normal(u, v):
    p = dome_point(u, v)
    return Vector((p.x / (SHELL_W / 2) ** 2, p.y / (SHELL_L / 2) ** 2, p.z / DOME_H ** 2)).normalized()


def helmet_anchors():
    """안전모 틀(원점 = 껍데기 밑 가운데)에서 램프 줄이 나오는 곳 · 뒤 줄 걸이 자리. build_helmet 과 몸 손질(줄 다시 잇기)이 같이 쓴다."""
    vb = math.asin(0.055 / DOME_H); bp, bn = dome_point(0, vb), dome_normal(0, vb)
    lamp_c = bp + bn * 0.004 + Vector((0, -LAMP_DEPTH / 2, 0.004))
    cp, cn = dome_point(math.pi, 0.10), dome_normal(math.pi, 0.10)
    return dict(lamp_back=lamp_c + Vector((0, LAMP_DEPTH / 2 - 0.004, 0.018)), clip=cp + cn * 0.012)


def build_helmet(number=NUMBER):
    """안전모 + 램프. 원점 = 껍데기 밑 가운데(챙이 붙는 높이). 돌려받는 것: 물체 사전."""
    out = {}
    root = bpy.data.objects.new("Helmet", None); bpy.context.scene.collection.objects.link(root); out["root"] = root
    # 껍데기(두께 4 mm) + 챙
    bm = bmesh.new(); NU, NV = 64, 16
    rings = [[bm.verts.new(dome_point(2 * math.pi * i / NU, (math.pi / 2) * j / NV * 0.999)) for i in range(NU)] for j in range(NV + 1)]
    top = bm.verts.new(Vector((0, 0, DOME_H)))
    for j in range(NV):
        for i in range(NU):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % NU], rings[j + 1][(i + 1) % NU], rings[j + 1][i]))
    for i in range(NU): bm.faces.new((rings[NV][i], rings[NV][(i + 1) % NU], top))
    # 챙: 껍데기 밑 둘레 → 바깥 타원(전체 L × W), 바깥으로 처짐
    outer = [bm.verts.new(Vector((HELMET_W / 2 * math.sin(2 * math.pi * i / NU), -HELMET_L / 2 * math.cos(2 * math.pi * i / NU), -BRIM_DROP))) for i in range(NU)]
    for i in range(NU): bm.faces.new((rings[0][(i + 1) % NU], rings[0][i], outer[i], outer[(i + 1) % NU]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    shell = obj_from_bm("Helmet_Shell", bm, mat("PlayerHelmet", "helmet", 0.55), root)
    sol = shell.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.004; sol.offset = -1
    # 위 가운데 골: 앞 밑 → 꼭대기 → 뒤 밑, 폭 RIDGE_W 높이 RIDGE_H
    bm = bmesh.new(); N = 48; prev = None
    for k in range(N + 1):
        v = 0.12 + (math.pi - 0.12 - 0.62) * k / N   # 앞 밑(0.12) → 꼭대기 → 뒤는 0.62 에서 끝(뒤 번호를 안 가리게)
        vv, uu = (v, 0.0) if v <= math.pi / 2 else (math.pi - v, math.pi)
        p, n = dome_point(uu, vv), dome_normal(uu, vv)
        sx = Vector((1, 0, 0))
        quad = [bm.verts.new(p + sx * s * RIDGE_W / 2 + n * h) for s, h in ((-1, 0), (1, 0), (1, RIDGE_H), (-1, RIDGE_H))]
        if prev:
            for a in range(4): bm.faces.new((prev[a], prev[(a + 1) % 4], quad[(a + 1) % 4], quad[a]))
        prev = quad
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj_from_bm("Helmet_Ridge", bm, mat("PlayerHelmet", "helmet", 0.55), root)
    # 앞 쇠 받침 + 나사 4
    vb = math.asin(0.055 / DOME_H)
    bp, bn = dome_point(0, vb), dome_normal(0, vb)
    rot = bn.to_track_quat("-Y", "Z").to_matrix().to_4x4()   # 판의 앞(−Y) = 껍데기 밖
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(BRACKET_W, 0.004, BRACKET_H), verts=bm.verts)
    for sx in (-1, 1):
        for sz in (-1, 1):
            r = bmesh.ops.create_cone(bm, segments=10, radius1=0.0035, radius2=0.0035, depth=0.003,
                                      matrix=Matrix.Translation((sx * 0.017, -0.003, sz * 0.011)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(bp) @ rot, verts=bm.verts)
    out["bracket"] = obj_from_bm("Helmet_Bracket", bm, mat("PlayerMetal", "metal", 0.4, 0.8), root)
    # 램프 머리: 받침 앞에 붙은 둥근 통(앞 = −Y) · 노란 테 · 빛나는 렌즈
    lamp_c = bp + bn * 0.004 + Vector((0, -LAMP_DEPTH / 2, 0.004))
    def cyl(name, r1, depth, y, material, r2=None):
        b = bmesh.new()
        bmesh.ops.create_cone(b, segments=32, radius1=r1, radius2=r2 if r2 else r1, depth=depth, cap_ends=True,
                              matrix=Matrix.Translation(lamp_c + Vector((0, y, 0))) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        return obj_from_bm(name, b, material, root)
    out["lamp"] = cyl("Lamp_Body", LAMP_D / 2 * 0.92, LAMP_DEPTH - 0.012, 0.006, mat("PlayerLampBody", "lampbody", 0.5))
    out["bezel"] = cyl("Lamp_Bezel", LAMP_D / 2, 0.014, -LAMP_DEPTH / 2 + 0.007, mat("PlayerBezel", "bezel", 0.45))
    out["lens"] = cyl("Lamp_Lens", LAMP_D / 2 * 0.74, 0.004, -LAMP_DEPTH / 2 - 0.0005, mat("PlayerLens", "lens", 0.1, 0, 6.0))
    out.update(helmet_anchors())                                                  # 줄이 나오는 곳(뒤 위) · 뒤 줄 걸이
    # 뒤 줄 걸이
    cp, cn = dome_point(math.pi, 0.10), dome_normal(math.pi, 0.10)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=(0.03, 0.006, 0.022), verts=bm.verts)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(cp + cn * 0.003) @ cn.to_track_quat("-Y", "Z").to_matrix().to_4x4(), verts=bm.verts)
    obj_from_bm("Helmet_CordClip", bm, mat("PlayerMetal", "metal", 0.4, 0.8), root)
    # ✎ 번호: 뒤와 양옆 세 곳(사용자 09-29 승인), 흰 페인트
    out["numbers"] = []
    for tag, u, vn in (("Back", math.pi, 0.40), ("Left", math.pi / 2, 0.52), ("Right", -math.pi / 2, 0.52)):
        cu = bpy.data.curves.new("n", "FONT"); cu.body = number; cu.size = 0.034; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        cu.extrude = 0.0006
        t = bpy.data.objects.new("tmp", cu); bpy.context.scene.collection.objects.link(t)
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = bpy.data.meshes.new_from_object(t.evaluated_get(dg))
        bpy.data.objects.remove(t); bpy.data.curves.remove(cu)
        p, n = dome_point(u, vn), dome_normal(u, vn)
        side = Vector((0, 0, 1)).cross(n).normalized()                 # 글자 가로
        up = n.cross(side).normalized()
        m = Matrix((side, up, n)).transposed().to_4x4(); m.translation = p + n * 0.0012
        me.transform(m)
        o = bpy.data.objects.new("Helmet_Number" + tag, me); bpy.context.scene.collection.objects.link(o)
        me.materials.clear(); me.materials.append(mat("PlayerNumber", "number", 0.7)); o.parent = root
        out["numbers"].append(o)
    return out


def build_battery():
    """배터리. 원점 = 몸에 닿는 뒷면 가운데, 고리 위 끝 높이(= 띠 높이). 앞(−Y) = 바깥."""
    root = bpy.data.objects.new("Battery", None); bpy.context.scene.collection.objects.link(root)
    top = 0.03                                            # 띠 위로 올라온 만큼(사진에서 잼 — k17 · k25)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(BAT_W, BAT_T, BAT_H), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, -BAT_T / 2 - 0.006, top - BAT_H / 2), verts=bm.verts)
    body = obj_from_bm("Battery_Body", bm, mat("PlayerBattery", "battery", 0.55), root)
    bv = body.modifiers.new("b", "BEVEL"); bv.width = 0.006; bv.segments = 2
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(BAT_W + 0.006, BAT_T + 0.006, LID_H), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, -BAT_T / 2 - 0.006, top + LID_H / 2), verts=bm.verts)
    lid = obj_from_bm("Battery_Lid", bm, mat("PlayerAlu", "alu", 0.35, 0.9), root)
    bv = lid.modifiers.new("b", "BEVEL"); bv.width = 0.005; bv.segments = 2
    bm = bmesh.new()                                      # 뒤 고리 2(띠를 꿴다)
    for sx in (-1, 1):
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((sx * 0.035, -0.003, top - 0.045)) @ Matrix.Diagonal((0.024, 0.006, 0.09, 1)))
    obj_from_bm("Battery_Loops", bm, mat("PlayerBattery", "battery", 0.55), root)
    return dict(root=root, body=body, cord_out=Vector((BAT_W / 2 - 0.025, -BAT_T / 2 - 0.006, top + LID_H)))


def build_canteen():
    """✎ 수통(치수 기록 없음). 원점 = 몸에 닿는 뒷면 가운데, 띠 높이."""
    root = bpy.data.objects.new("Canteen", None); bpy.context.scene.collection.objects.link(root)
    w, t, h = CANTEEN
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(w, t, h), verts=bm.verts); bmesh.ops.translate(bm, vec=(0, -t / 2 - 0.006, 0.02 - h / 2), verts=bm.verts)
    o = obj_from_bm("Canteen_Cover", bm, mat("PlayerOlive", "olive", 0.8), root)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = 0.028; bv.segments = 4
    bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=20, radius1=0.016, radius2=0.016, depth=0.02, cap_ends=True,
                                            matrix=Matrix.Translation((0, -t / 2 - 0.006, 0.03)))
    obj_from_bm("Canteen_Cap", bm, mat("PlayerAlu", "alu", 0.35, 0.9), root)
    return dict(root=root)


def ellipse_ring(length=BELT_LEN, ratio=0.78, n=96):
    """둘레 length 인 타원(앞뒤 / 옆 = ratio). 몸이 없을 때 쓰는 기본 허리."""
    a = length / (2 * math.pi * math.sqrt((1 + ratio ** 2) / 2)); b = a * ratio
    return [(a * math.sin(2 * math.pi * i / n), -b * math.cos(2 * math.pi * i / n)) for i in range(n)]


def build_belt(ring=None, z=0.0):
    """군용 탄띠: 허리 둘레 점들(닫힌 xy)을 폭 BELT_W 로 세운 띠 + 앞 쇠 버클. 원점 = 띠 가운데 높이."""
    ring = ring or ellipse_ring()
    root = bpy.data.objects.new("Belt", None); bpy.context.scene.collection.objects.link(root)
    bm = bmesh.new(); n = len(ring)
    lo = [bm.verts.new((x, y, z - BELT_W / 2)) for x, y in ring]; hi = [bm.verts.new((x, y, z + BELT_W / 2)) for x, y in ring]
    for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = obj_from_bm("Belt_Web", bm, mat("PlayerOlive", "olive", 0.8), root)
    s = o.modifiers.new("t", "SOLIDIFY"); s.thickness = 0.005; s.offset = 1
    i0 = min(range(n), key=lambda i: ring[i][1])                       # 가장 앞(−Y)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1,
        matrix=Matrix.Translation((ring[i0][0], ring[i0][1] - 0.007, z)) @ Matrix.Diagonal((0.055, 0.006, 0.05, 1)))
    obj_from_bm("Belt_Buckle", bm, mat("PlayerMetal", "metal", 0.4, 0.8), root)
    return dict(root=root, ring=ring, z=z)


def cord(points, name="Lamp_Cord"):
    """램프 줄: 점들을 잇는 둥근 선(지름 1.2 cm)."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.006; cu.bevel_resolution = 3
    sp = cu.splines.new("NURBS"); sp.points.add(len(points) - 1)
    for p, q in zip(sp.points, points): p.co = (*q, 1)
    sp.use_endpoint_u = True; sp.order_u = 3
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat("PlayerCord", "cord", 0.6))
    return o


def bake_all(objs):
    """모디파이어 · 곡선을 그물로 굳힌다(내보내기 · 재기 전에)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in list(objs):
        if o.type not in ("MESH", "CURVE", "FONT") or (o.type == "MESH" and not o.modifiers): continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        n = bpy.data.objects.new(o.name, me); bpy.context.scene.collection.objects.link(n)
        n.parent = o.parent; n.matrix_world = o.matrix_world.copy()
        nm = o.name; bpy.data.objects.remove(o); n.name = nm


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))


def check(fails, name, ok, msg):
    print(("PASS " if ok else "FAIL ") + name + " — " + msg)
    if not ok: fails.append(name)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    h = build_helmet(); b = build_battery(); c = build_canteen(); belt = build_belt()
    b["root"].location = (0.5, 0, 0); c["root"].location = (0.8, 0, 0); belt["root"].location = (-0.6, 0, 0)
    bake_all(list(bpy.data.objects))
    out = os.environ.get("OUT", os.path.join(ROOT, "build", "player", "player_props.glb")); os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=False, export_apply=True)
    # ── 자기 검사: 다시 읽어서 잰다 ──
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=out)
    ob = {o.name: o for o in bpy.data.objects}
    fails = []
    hel = [o for n, o in ob.items() if n.startswith(("Helmet_Shell", "Helmet_Ridge"))]
    lo, hi = world_bbox(hel); d = hi - lo       # glTF → Blender 는 Z 위 그대로(가져오기가 되돌림)
    check(fails, "helmet_size", abs(d.y - 0.28) < 0.006 and abs(d.x - 0.225) < 0.006 and abs(d.z - 0.15) < 0.006,
          f"앞뒤 {d.y*100:.1f} · 옆 {d.x*100:.1f} · 높이 {d.z*100:.1f} cm (기준 28 · 22.5 · 15 ±0.6)")
    lo, hi = world_bbox([ob["Lamp_Bezel"]]); dd = hi - lo
    lo2, hi2 = world_bbox([ob["Lamp_Body"], ob["Lamp_Bezel"], ob["Lamp_Lens"]])
    check(fails, "lamp_size", abs(dd.x - 0.065) < 0.003 and abs((hi2 - lo2).y - 0.070) < 0.004,
          f"지름 {dd.x*100:.1f} · 깊이 {(hi2-lo2).y*100:.1f} cm (기준 6.5 · 7)")
    lo, hi = world_bbox([ob["Battery_Body"]]); d = hi - lo
    check(fails, "battery_size", abs(d.x - 0.13) < 0.004 and abs(d.y - 0.05) < 0.004 and abs(d.z - 0.19) < 0.004,
          f"{d.x*100:.1f} × {d.y*100:.1f} × {d.z*100:.1f} cm (기준 13 × 5 × 19)")
    lo, hi = world_bbox([ob["Belt_Web"]]); d = hi - lo
    check(fails, "belt_width", abs(d.z - 0.06) < 0.003, f"폭 {d.z*100:.1f} cm (기준 6)")
    nums = [n for n in ob if n.startswith("Helmet_Number")]
    check(fails, "helmet_numbers", len(nums) == 3, f"번호 {len(nums)} 곳 (기준 3: 뒤 · 양옆)")
    multi = [o.name for o in bpy.data.objects if o.type == "MESH" and len(o.data.materials) != 1]
    check(fails, "one_material_each", not multi, f"재질이 하나가 아닌 물체 {multi}")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    check(fails, "tris", tris <= 30000, f"삼각형 {tris} (≤ 30,000)")
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
