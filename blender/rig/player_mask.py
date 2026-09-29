"""3D-P — 얼굴을 가리는 마스크 두 가지를 20 대 얼굴 판에 맞춰 코드로 만든다(사용자 09-29 "가, 나 둘 다 만들어봐라", 0 크레딧).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender/rig/player_mask.py -- half|full
입력: build/player/player_player1_fix_retex2.blend (Blender 손질 모양 + 20 대 그림 + 코드 소품, player_meshy_fix.py 가 만든다)
  half = 가. 반쪽 방진마스크 — 문경석탄박물관 유물(조사 13 k16): 회청색 고무 컵이 코 · 입을 덮고, 앞면 대부분이 둥근 필터 하나(격자),
         머리끈 두 줄(코 위 · 볼 옆 네 곳에 걸림). 유물 15 × 10 × 9.5 cm. 1980 년대 후반부터 제대로 씀(조사 13 [E]) · 1992 장성 사진 k25.
  full = 나. 얼굴 전체 방독면 — ※ 1980 년대 한국 광부가 일할 때 쓴 기록 없음(지어낸 것). 흔한 민간 방독면 모양: 검은 고무 전면 ·
         둥근 눈 렌즈 둘 · 입 앞 정화통 · 머리끈 세 쌍(K-1 방독면 '각 끈(3쌍)', 나무위키).
만드는 법: 머리 속 한 점에서 얼굴 쪽으로 선을 쏘아 겉면을 찾고, 그 위로 띄운 그물(가장자리는 얼굴에 붙고 가운데는 뜬 컵)에 두께를 준다.
검사(FAIL 이면 종료 1): 마스크 안쪽이 얼굴에 안 파묻힘(≥ 2 mm) · 가리는 곳(half: 코끝 · 입 / full: 눈 · 코 · 입)을 앞에서 쏘면 마스크에 먼저 닿음 ·
    크기(half: 폭 15 · 높이 10 · 앞뒤 9.5 cm ±1.5) · full 은 윗 끝이 안전모 챙 아래
사보타주: SABOTAGE=nogap(얼굴에서 안 띄움 → 파묻힘 FAIL) · small(half 폭 0.6 배 → 크기 FAIL)
출력: build/player/player_mask_<half|full>.blend · 그림 P2_player1_fix_retex2_mask_<half|full>_*.png"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "blender", "props"))
import player_blockout as B
import player_meshy_views as V
import make_player_props as P

KIND = sys.argv[sys.argv.index("--") + 1]
SAB = os.environ.get("SABOTAGE", "")
assert KIND in ("half", "full")
bpy.ops.wm.open_mainfile(filepath=os.path.join(V.OUT, "player_player1_fix_retex2.blend"))
info = dict(bpy.context.scene["player_info"])
body = max((o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render), key=lambda o: len(o.data.vertices))
dg = bpy.context.evaluated_depsgraph_get()
bco = [body.matrix_world @ v.co for v in body.data.vertices]
bvh = BVHTree.FromPolygons([tuple(c) for c in bco], [tuple(p.vertices) for p in body.data.polygons])
co = np.array([c[:] for c in bco])
rim, hcx, hcy = info["rim_z"], info["helmet_cx"], info["helmet_cy"]

# 얼굴 자리: 코끝 = 챙 아래 4~12 cm, 가운데 3 cm 안에서 가장 앞(−Y)
face = co[(co[:, 2] < rim - 0.04) & (co[:, 2] > rim - 0.13) & (np.abs(co[:, 0] - hcx) < 0.03) & (np.hypot(co[:, 0] - hcx, co[:, 1] - hcy) < 0.2)]
nose = face[face[:, 1].argmin()]
eye_z, mouth_z, chin_z = nose[2] + 0.040, nose[2] - 0.035, nose[2] - 0.072        # 코끝 기준 어림(사람 얼굴 비율)
C = Vector((hcx, nose[1] + 0.095, nose[2] - 0.01))                                  # 머리 속 한 점(코끝 9.5 cm 뒤)
print(f"INFO 코끝 ({nose[0]:+.3f}, {nose[1]:+.3f}, {nose[2]:.3f}) · 눈 {eye_z:.3f} · 입 {mouth_z:.3f} · 턱 {chin_z:.3f} · 챙 {rim:.3f}")

MAT = {}
def mat(key, rgb, rough=0.6, metal=0.0, alpha=1.0):
    if key in MAT: return MAT[key]
    m = bpy.data.materials.new("PM_" + key); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    MAT[key] = m; return m


def obj(name, bm, material, mods=()):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    for kind_, kw in mods:
        m = o.modifiers.new(kind_, kind_)
        for k, v in kw.items(): setattr(m, k, v)
    return o


def shell(name, z_bot, z_top, a_of, gap_edge, gap_mid, material, thick=0.004, NU=28, NV=18):
    """얼굴 위 컵: v 0(아래)→1(위) 높이 z, u −1→1 좌우 = 반각 a_of(v)(도). 그 높이의 머리 속 점에서 수평으로 쏜 선이 얼굴에 닿는 곳 + 띄움
    (한 점에서 비스듬히 쏘면 닿는 높이가 절반쯤으로 줄어든다 — 09-29 첫 판 컵 높이 6 cm)."""
    grid = []
    for j in range(NV + 1):
        v = j / NV; zz = z_bot + (z_top - z_bot) * v; row = []
        for i in range(NU + 1):
            u = -1 + 2 * i / NU
            a = math.radians(a_of(v)) * u
            o_ = Vector((hcx, C.y, zz)); d = Vector((math.sin(a), -math.cos(a), 0))
            hit = bvh.ray_cast(o_, d)[0]
            if hit is None: hit = o_ + d * 0.10
            r2 = min(1.0, u * u + (2 * v - 1) ** 2)
            gap = 0.0 if SAB == "nogap" else gap_edge + (gap_mid - gap_edge) * (1 - r2)
            q = hit + d * gap
            if SAB != "nogap":                                                        # 얼굴 겉에서 3 mm 안이면 겉면 밖으로(가장자리 · 비스듬한 곳)
                n_ = bvh.find_nearest(q)
                if n_[0] is not None and (q - n_[0]).dot(n_[1]) < 0.003: q = n_[0] + n_[1] * 0.003
            row.append(q)
        grid.append(row)
    bm = bmesh.new(); vs = [[bm.verts.new(p) for p in r] for r in grid]
    for j in range(NV):
        for i in range(NU): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if sum((f.calc_center_median() - C).dot(f.normal) for f in bm.faces) < 0:     # 면 방향 = 머리 바깥(두께가 얼굴 쪽으로 안 붙게)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    o = obj(name, bm, material, [("SOLIDIFY", dict(thickness=thick, offset=1.0))])     # 고른 두께(even)는 넓이 0 칸에서 한없이 튄다
    return o, grid


def disc(name, center, axis, r, depth, material, seg=40):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=seg, radius1=r, radius2=r, depth=depth, cap_ends=True,
                          matrix=Matrix.Translation(center) @ Vector(axis).to_track_quat("Z", "Y").to_matrix().to_4x4())
    return obj(name, bm, material, [("BEVEL", dict(width=min(r, depth) * 0.25, segments=2))])


def strap(name, z_front, z_back, a0, width, material):
    """머리끈: 마스크 옆(방위각 a0)에서 뒤통수를 돌아 반대편으로 — 겉면에서 4 mm 띄운 납작한 띠."""
    pts = []
    for k in range(41):
        t = a0 + (2 * math.pi - 2 * a0) * k / 40; zz = z_front + (z_back - z_front) * (1 - math.cos(t)) / (1 - math.cos(math.pi)) if True else 0
        d = Vector((-math.sin(t), math.cos(t), 0))
        c0 = Vector((hcx, hcy, zz))
        hit = bvh.ray_cast(c0 - d * 0.3, d)[0]
        pts.append((hit if hit is not None else c0 - d * 0.09) - d * 0.004)
    prof = bpy.data.curves.new(name + "_p", "CURVE"); ps = prof.splines.new("POLY"); ps.points.add(3)
    for p_, q in zip(ps.points, ((-0.0015, -width / 2), (0.0015, -width / 2), (0.0015, width / 2), (-0.0015, width / 2))): p_.co = (*q, 0, 1)
    ps.use_cyclic_u = True
    po = bpy.data.objects.new(name + "_p", prof); bpy.context.scene.collection.objects.link(po); po.hide_render = True
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_mode = "OBJECT"; cu.bevel_object = po
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts): p_.co = (*q, 1)
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o); cu.materials.append(material)
    return o


parts = []
if KIND == "half":
    rub = mat("rubber_bluegrey", (0.10, 0.13, 0.17), 0.55)                     # 문경 유물 회청색(사진에서 잼)
    k = 0.6 if SAB == "small" else 1.0
    def w_half(v):   # 좌우 반각(도): 턱 밑 50 · 입 높이 62 · 콧등 16 — 유물 사진처럼 볼을 감싸고 콧등에서 좁아진다
        return k * (50 + (62 - 50) * min(1, v / 0.45)) if v < 0.45 else k * (62 - (62 - 16) * ((v - 0.45) / 0.55) ** 1.4)
    cup, grid = shell("Mask_Cup", chin_z - 0.004, nose[2] + 0.020, w_half, 0.006, 0.022, rub)
    mid = grid[7][14]; nrm = (mid - C).normalized()
    fc = mid + nrm * 0.004 + Vector((0, 0, -0.004))
    fax = (nrm + Vector((0, 0, -0.25))).normalized()
    parts += [cup, disc("Mask_Filter", fc + fax * 0.011, fax, 0.036 * k, 0.022, mat("filter", (0.05, 0.05, 0.05), 0.5))]
    ring_ = disc("Mask_FilterGrid", fc + fax * 0.0225, fax, 0.030 * k, 0.002, mat("filter_grid", (0.12, 0.12, 0.12), 0.4), seg=12)
    parts.append(ring_)
    metal = mat("buckle", (0.55, 0.55, 0.56), 0.35, 0.9)                        # 머리끈 거는 쇠고리 넷(유물 사진: 코 위 양옆 · 볼 아래 양옆)
    for jj, side in ((13, 0), (13, -1), (4, 0), (4, -1)):
        q = grid[jj][side]; out_ = (q - C); out_.z = 0; out_.normalize()
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=(0.008, 0.012, 0.016), verts=bm.verts)
        m4 = out_.to_track_quat("X", "Z").to_matrix().to_4x4(); m4.translation = q + out_ * 0.008
        bmesh.ops.transform(bm, matrix=m4, verts=bm.verts)
        parts.append(obj(f"Mask_Buckle{jj}{side}", bm, metal))
    white = mat("strap_clear", (0.70, 0.70, 0.66), 0.4)
    parts += [strap("Mask_StrapUp", nose[2] + 0.02, eye_z + 0.02, math.radians(38), 0.014, white),
              strap("Mask_StrapLow", mouth_z - 0.01, chin_z - 0.035, math.radians(55), 0.014, white)]
else:
    rub = mat("rubber_black", (0.03, 0.03, 0.03), 0.6)
    z_top = min(rim - P.BRIM_DROP - 0.008, eye_z + 0.045)
    def w_full(v):   # 좌우 반각(도): 턱 밑 55 · 광대(눈 높이) 78 · 이마 68 — 귀 앞까지
        return 55 + (78 - 55) * min(1, v / 0.72) if v < 0.72 else 78 - (78 - 68) * ((v - 0.72) / 0.28)
    cup, grid = shell("Mask_Face", chin_z - 0.022, z_top, w_full, 0.006, 0.016, rub, thick=0.005)
    parts.append(cup)
    glass = mat("lens", (0.02, 0.025, 0.03), 0.08, 0.3); rimm = mat("lens_rim", (0.25, 0.25, 0.26), 0.35, 0.9)
    for sx in (-1, 1):
        d = (Vector((hcx + sx * 0.032 * 1.9, C.y - 0.16, eye_z)) - C).normalized()
        hit = bvh.ray_cast(C, d)[0] or (C + d * 0.09)
        p = hit + d * 0.024
        parts += [disc("Mask_LensRim" + ("L" if sx > 0 else "R"), p, d, 0.029, 0.010, rimm),
                  disc("Mask_Lens" + ("L" if sx > 0 else "R"), p + d * 0.004, d, 0.024, 0.006, glass)]
    d = (Vector((hcx, C.y - 0.16, mouth_z - 0.008)) - C).normalized()
    hit = bvh.ray_cast(C, d)[0] or (C + d * 0.09)
    fax = (d + Vector((0, 0, -0.35))).normalized()
    boss = hit + d * 0.030
    parts += [disc("Mask_Boss", boss, fax, 0.026, 0.024, rub),
              disc("Mask_Canister", boss + fax * 0.045, fax, 0.042, 0.065, mat("canister", (0.10, 0.11, 0.08), 0.5, 0.2))]
    strapc = mat("strap_black", (0.05, 0.05, 0.05), 0.7)
    parts += [strap("Mask_StrapTop", z_top - 0.01, rim + 0.03, math.radians(50), 0.02, strapc),
              strap("Mask_StrapMid", eye_z, eye_z + 0.01, math.radians(62), 0.02, strapc),
              strap("Mask_StrapLow", mouth_z - 0.01, chin_z - 0.03, math.radians(62), 0.02, strapc)]

# ── 검사 ──
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
fails = []
shell_o = parts[0]; ev = shell_o.evaluated_get(dg); sm = ev.to_mesh()
inner = [shell_o.matrix_world @ v.co for v in sm.vertices]; ev.to_mesh_clear()
dist = [((p - bvh.find_nearest(p)[0]).length, p) for p in inner]
dmin = min(d for d, _ in dist)
# 파묻힘: 얼굴 겉에서 2 mm 안에 있거나, 몸 안쪽(겉면 법선 반대편)에 있는 점
inside = sum(1 for p in inner if (lambda h: h[0] is not None and (p - h[0]).dot(h[1]) < 0.0015)(bvh.find_nearest(p)))
B.check(fails, "mask_not_in_face", inside == 0, f"마스크 점 {len(inner)} 개 중 얼굴 겉 1.5 mm 안쪽(파묻힘) {inside} 개 · 가장 가까운 거리 {dmin*1000:.1f} mm")
mvh = BVHTree.FromObject(shell_o, dg)
extra = [o for o in parts[1:] if o.type == "MESH"]
def covered(pt):
    """앞에서 쏜 선이 몸보다 마스크(컵 · 렌즈 · 필터)에 먼저 닿나."""
    o_, d_ = Vector((pt[0], pt[1] - 0.5, pt[2])), Vector((0, 1, 0))
    hb = bvh.ray_cast(o_, d_)[0]; best = mvh.ray_cast(o_, d_)[0]
    for o in extra:
        h = BVHTree.FromObject(o, dg).ray_cast(o_, d_)[0]
        if h is not None and (best is None or h.y < best.y): best = h
    return best is not None and (hb is None or best.y < hb.y)
targets = {"코끝": (nose[0], nose[1], nose[2]), "입": (hcx, nose[1], mouth_z)}
if KIND == "full":
    targets.update({"왼눈": (hcx + 0.032, nose[1], eye_z), "오른눈": (hcx - 0.032, nose[1], eye_z)})
miss = [k for k, p in targets.items() if not covered(p)]
B.check(fails, "mask_covers", not miss, f"앞에서 가려지나 — {', '.join(targets)} (안 가려진 곳: {miss or '없음'})")
allp = np.array([(o.matrix_world @ Vector(c))[:] for o in [shell_o] + extra for c in o.bound_box])
lo, hi = allp.min(axis=0), allp.max(axis=0); dx, dz, dy = hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]
if KIND == "half":
    cb = np.array([(shell_o.matrix_world @ Vector(c))[:] for c in shell_o.bound_box]); cd = cb.max(axis=0) - cb.min(axis=0)
    print(f"INFO 컵만 폭 {cd[0]*100:.1f} · 높이 {cd[2]*100:.1f} · 앞뒤 {cd[1]*100:.1f} cm")
    B.check(fails, "mask_size", abs(dx - 0.15) < 0.015 and abs(dz - 0.10) < 0.015 and abs(dy - 0.095) < 0.02,
            f"폭 {dx*100:.1f} · 높이 {dz*100:.1f} · 앞뒤 {dy*100:.1f} cm (유물 15 × 10 × 9.5 ±1.5, 앞뒤 ±2)")
else:
    B.check(fails, "mask_under_brim", hi[2] < rim - P.BRIM_DROP, f"마스크 윗 끝 {hi[2]*100:.1f} cm · 챙 앞끝 {(rim - P.BRIM_DROP)*100:.1f} cm")
    print(f"INFO 방독면 폭 {dx*100:.1f} · 높이 {dz*100:.1f} · 앞뒤 {dy*100:.1f} cm (※ 기록 없음)")
if SAB:
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails)); sys.exit(1 if fails else 0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V.OUT, f"player_mask_{KIND}.blend"))
if os.environ.get("RENDER", "1") != "0":
    V.shoot_set(f"player1_fix_retex2_mask_{KIND}_소품", [body], close=False)
    B.setup_render((0.30, 0.30, 0.31), 0.9)
    B.shoot(os.path.join(V.OUT, f"P2_player1_fix_retex2_mask_{KIND}_얼굴_가까이.png"), "quarter", nose[2] + 0.01, 0.30, (900, 900))
print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
sys.exit(1 if fails else 0)
