"""갱도 조각 변형: 벽 틈 (3D-④ MR1 맵 단계, 제안서 docs/제안서_3D4_MR1_도망_구멍.md — 영상 R4 판정 통과 뒤 결정 2026-09-20)
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/make_gaps.py
입력(안 고친다): Assets/Tunnel/Pieces/piece_straight.gltf  — 이 저장소의 사본. Godot 쪽 export.sh·build_piece.py 는 안 돌린다.
출력(새 파일):  Assets/Tunnel/Pieces/piece_gap_big.gltf(.bin) · piece_gap_small.gltf(.bin) — 그림 파일은 새로 안 만들고 있는 textures/ 를 그대로 가리킨다.
  큰 틈  = 괴물 굴: 서쪽 벽(−x), 갱목 기둥 1–2 사이(빈 폭 1.35 m — 기둥이 문틀), 높이 2.6 · 깊이 3.5 m, 안쪽 끝 폭 1.1. 위에 갱목 가로대.
  작은 틈 = 플레이어 전용: 같은 자리, 폭 0.9 · 높이 1.3(숙여야 들어감) · 깊이 3.0 m, 곧은 폭.
  동쪽 벽(+x)에는 파이프·전선·전구가 조각 끝에서 끝까지 지나가서 틈을 안 낸다.
만드는 법: 보이는 벽 SHL 을 틈 네모의 세 변(y = ±폭/2, z = 높이)에서 자르고(bisect) 그 안의 벽면을 지운다 → 틈 안쪽은 고리(ring)를 깊이 따라 늘어놓은 바위 굴.
  첫 고리는 원래 벽면에 광선을 쏴 그 울퉁불퉁한 면 위에 앉힌다(안 그러면 입구에 상자 테두리가 튀어나온다). 안쪽 고리는 씨앗 고정 난수로 조금씩 흔든다.
  충돌: COL_straight_wall_W 상자를 지우고 → 틈 양옆 벽 · 틈 위 벽 · 틈의 두 옆면 · 천장 · 안쪽 끝 · 바닥, 볼록한 덩어리 일곱(이름 COL_*-convcolonly — BuildM1 이 COL_ 로 시작하는 것을 충돌로 쓴다).
자기 검사: 갱도 가운데서 틈 속으로 쏜 광선이 깊이만큼 들어간다(보이는 면·충돌 둘 다) · 틈 옆 벽은 그대로 막혀 있다 · 틈 안 두 옆면·천장이 다 있다 · 원본 조각 md5 가 안 바뀌었다 · 새 gltf 가 가리키는 그림 파일이 다 있다.
사보타주: SABOTAGE=nocut(보이는 벽을 안 판다) · solidcol(충돌 벽을 안 쪼갠다) → 저마다 FAIL 로 죽는다."""
import bpy, bmesh, os, sys, math, json, random, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
PIECES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Assets", "Tunnel", "Pieces")
PIECE_SRC = os.environ.get("PIECE_SRC", "piece_straight")     # A1: PIECE_SRC=piece_straight_v2 PIECE_SUFFIX=_v2 → Meshy 갱목·갓등 조각에서 틈 조각 _v2 를 만든다
SUFFIX = os.environ.get("PIECE_SUFFIX", "")
SRC = os.path.join(PIECES, PIECE_SRC + ".gltf")
SAB = os.environ.get("SABOTAGE", "")
WALL_X, COL_X0, COL_X1, CEIL = -3.16, -3.2, -3.5, 5.6           # 보이는 벽이 시작하는 곳 · 충돌 벽 상자의 두 면 · 천장 (piece_straight 에서 잰 값)
GAPS = {
    "piece_gap_big":   dict(y=-0.01, w=1.35, h=2.6, d=3.5, back=1.1, lintel=True),       # y = 기둥 1(−0.88)과 2(+0.86) 사이 한가운데
    "piece_gap_small": dict(y=-0.01, w=0.9, h=1.3, d=3.0, back=0.9, lintel=False),
}
def md5(path): return hashlib.md5(open(path, "rb").read()).hexdigest()
src_md5 = {f: md5(os.path.join(PIECES, f)) for f in (PIECE_SRC + ".gltf", PIECE_SRC + ".bin")}

def convex(name, pts):
    """볼록한 충돌 덩어리 (꼭짓점 8개의 볼록 껍질)"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
def box(name, x0, x1, y0, y1, z0, z1):
    return convex(name, [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])

def build(name, g):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=SRC)
    shl = bpy.data.objects["SHL_straight"]
    Y, HW, H, D, HB = g["y"], g["w"] / 2, g["h"], g["d"], g["back"] / 2
    rnd = random.Random(20260920)
    deps = bpy.context.evaluated_depsgraph_get()
    wall = BVHTree.FromObject(shl, deps)                       # 파기 전의 벽 — 첫 고리를 그 면에 앉히는 데 쓴다
    def wall_x(y, z):
        hit = wall.ray_cast(Vector((0, y, max(z, 0.05))), Vector((-1, 0, 0)))
        return hit[0].x if hit[0] else WALL_X

    # ---- 보이는 벽: 틈 네모를 잘라 지운다
    bm = bmesh.new(); bm.from_mesh(shl.data); uv = bm.loops.layers.uv.active
    def region(): return [f for f in bm.faces if f.calc_center_median().x < -2.9 and abs(f.normal.z) < 0.7 and abs(f.calc_center_median().y - Y) < HW + 0.6 and f.calc_center_median().z < H + 0.6]
    ratios = [(l[uv].uv - l.link_loop_next[uv].uv).length / max((l.vert.co - l.link_loop_next.vert.co).length, 1e-6) for f in region() for l in f.loops]
    uv_per_m = sorted(ratios)[len(ratios) // 2]                # 벽 그림의 촘촘함 (UV / m) — 새 면도 같은 촘촘함으로
    mat_wall = region()[0].material_index
    mat_floor = next(f.material_index for f in bm.faces if f.normal.z > 0.9 and f.calc_center_median().z < 0.3)
    if SAB != "nocut":
        for co, no in (((0, Y - HW, 0), (0, 1, 0)), ((0, Y + HW, 0), (0, 1, 0)), ((0, 0, H), (0, 0, 1))):
            fs = region(); geom = list({v for f in fs for v in f.verts}) + list({e for f in fs for e in f.edges}) + fs
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=co, plane_no=no)
        inside = [f for f in region() if abs(f.calc_center_median().y - Y) < HW and f.calc_center_median().z < H]
        bmesh.ops.delete(bm, geom=inside, context="FACES")
    cut_faces = len(inside) if SAB != "nocut" else 0

    # ---- 틈 안쪽: 고리를 깊이 따라. 고리의 점 = 바닥 왼쪽 → 왼 옆면 위로 → 천장 → 오른 옆면 아래로 (바닥은 따로)
    def ring(t, k):
        hw = HW + (HB - HW) * t; h = H - 0.25 * t * (1 if g["lintel"] else 0.4)       # 안으로 갈수록 좁고 낮다
        nz, ny = max(2, round(H / 0.45)), max(2, round(2 * HW / 0.45))                 # 점 수는 고리마다 같아야 한다 (입구 크기로 정한다)
        pts = [(-hw, h * i / nz) for i in range(nz + 1)] + [(-hw + 2 * hw * i / ny, h) for i in range(1, ny)] + [(hw, h * (nz - i) / nz) for i in range(nz + 1)]
        out = []
        for (dy, z) in pts:
            if k == 0: x = wall_x(Y + dy * 0.999, min(z, H - 0.01)) + 0.04            # 첫 고리는 벽면 위에 (4 cm 앞)
            else: x = WALL_X - D * t
            j = 0.0 if k == 0 else 0.07
            out.append(Vector((x + rnd.uniform(-j, j), Y + dy + rnd.uniform(-j, j) * (0.3 if z < 0.05 else 1), max(0.0, z + rnd.uniform(-j, j)) if 0.05 < z else 0.015)))      # 바닥은 1.5 cm 띄운다 — 갱도 바닥(−3.5 까지 깔려 있다)과 겹쳐 지직거리지 않게
        return out
    def collar():
        """입구 테두리: 첫 고리에서 바깥으로 0.14 m 넓히고 벽 속으로 0.12 m 들어간 고리. 첫 고리(벽면 4 cm 앞)와 이으면 잘린 가장자리와 고리 사이의 실틈을 앞에서 덮는다
        (게임 그림 23_map_gap_small 에서 입구 왼쪽·아래에 검은 실틈이 보였다 — 벽이 점과 점 사이에서 울퉁불퉁해서)"""
        out = []
        for p0 in rings[0]:
            dy, z = p0.y - Y, p0.z
            oy = 0.14 * (1 if dy > 0 else -1) if abs(dy) > HW - 0.01 else 0.0
            oz = 0.14 if z > H - 0.01 else 0.0
            out.append(Vector((wall_x(p0.y + oy, min(z + oz, CEIL - 0.1)) - 0.12, p0.y + oy, z + oz if z > 0.05 else 0.0)))
        return out
    TS = [0.0, 0.08, 0.25, 0.45, 0.7, 1.0]
    rings = [ring(t, k) for k, t in enumerate(TS)]
    n = len(rings[0]); assert all(len(r) == n for r in rings)
    new_faces = []
    def face(vs, mat, axis_pt):
        f = bm.faces.new([bm.verts.new(p) for p in vs]); f.material_index = mat; f.smooth = True
        if f.normal.length == 0: f.normal_update()
        if f.normal.dot(axis_pt - f.calc_center_median()) < 0: f.normal_flip()      # 면은 틈 안쪽(가운데 축)을 본다
        for l in f.loops:                                      # 그림 좌표: 깊이(x) · 둘레(y+z)를 벽과 같은 촘촘함으로
            l[uv].uv = ((l.vert.co.x) * uv_per_m, (l.vert.co.y + l.vert.co.z) * uv_per_m) if mat == mat_wall else (l.vert.co.x * uv_per_m, l.vert.co.y * uv_per_m)
        new_faces.append(f)
    col_ = collar()
    for i in range(n - 1):
        face([col_[i], col_[i + 1], rings[0][i + 1], rings[0][i]], mat_wall, Vector((0, Y, H * 0.45)))      # 테두리는 갱도 쪽을 본다
    for a, b in zip(rings, rings[1:]):
        for i in range(n - 1):
            mid = (a[i] + b[i + 1]) / 2
            face([a[i], a[i + 1], b[i + 1], b[i]], mat_wall, Vector((mid.x, Y, H * 0.45)))
        face([a[0], b[0], b[-1], a[-1]], mat_floor, Vector(((a[0].x + b[0].x) / 2, Y, 1.0)))     # 바닥
    face(list(rings[-1]), mat_wall, Vector((WALL_X - D + 1.0, Y, H * 0.45)))                      # 안쪽 끝
    bmesh.ops.triangulate(bm, faces=[f for f in new_faces if f.is_valid and len(f.verts) > 4])
    bm.normal_update(); bm.to_mesh(shl.data); bm.free()

    # ---- 갱목 가로대 (큰 틈): 기둥 하나를 베껴 눕힌다
    if g["lintel"]:
        post = bpy.data.objects["TMB_straight_1_post_L"]
        lin = post.copy(); lin.data = post.data.copy(); lin.name = "TMB_gap_lintel"; bpy.context.scene.collection.objects.link(lin)
        lin.matrix_world = post.matrix_world.copy(); bpy.context.view_layer.update()
        zs = [(post.matrix_world @ v.co).z for v in post.data.vertices]; z0, z1 = min(zs), max(zs)
        ctr = sum(((post.matrix_world @ v.co) for v in post.data.vertices), Vector()) / len(post.data.vertices)
        for v in lin.data.vertices:                            # 기둥(z 방향 4.8 m)을 y 방향 1.9 m 가로대로: 세상 자리에서 축을 바꿔 놓는다
            w = post.matrix_world @ v.co
            along = (w.z - z0) / (z1 - z0) - 0.5
            p = Vector((WALL_X - 0.02 + (w.x - ctr.x) * 0.8, Y + along * (g["w"] + 0.75), H + 0.17 + (w.y - ctr.y) * 0.8))
            v.co = post.matrix_world.inverted() @ p
        bm2 = bmesh.new(); bm2.from_mesh(lin.data)             # 축을 바꾸는 건 거울 뒤집기다 — 면이 뒤집혀 Unity 에서 새까맣게 나왔다(게임 그림 23_map_gap_big) → 면을 다시 뒤집는다
        bmesh.ops.reverse_faces(bm2, faces=bm2.faces); bm2.normal_update(); bm2.to_mesh(lin.data); bm2.free()

    # ---- 충돌
    old = bpy.data.objects["COL_straight_wall_W-convcolonly"]
    if SAB != "solidcol":
        bpy.data.objects.remove(old, do_unlink=True)
        T = 0.3
        box("COL_gap_wall_S-convcolonly", COL_X1, COL_X0, -3.5, Y - HW, 0, CEIL); box("COL_gap_wall_N-convcolonly", COL_X1, COL_X0, Y + HW, 3.5, 0, CEIL)
        box("COL_gap_wall_top-convcolonly", COL_X1, COL_X0, Y - HW, Y + HW, H, CEIL)
        xe = COL_X0 - D
        for s_, nm in ((-1, "S"), (1, "N")):                  # 안으로 좁아지는 옆면 (두께 T 를 바깥쪽으로)
            convex("COL_gap_side_%s-convcolonly" % nm, [(x, Y + s_ * (hw + t_), z) for (x, hw) in ((COL_X0, HW), (xe, HB)) for t_ in (0, T) for z in (0, H)])
        box("COL_gap_roof-convcolonly", xe, COL_X0, Y - HW - T, Y + HW + T, H - (0.25 if g["lintel"] else 0.1) * 0.0, H + T)
        box("COL_gap_back-convcolonly", xe - T, xe, Y - HB - T, Y + HB + T, 0, H + T)
        box("COL_gap_floor-convcolonly", xe - T, COL_X1, Y - HW - T, Y + HW + T, -0.5, 0)

    # ---- 자기 검사
    bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
    vis = BVHTree.FromObject(shl, deps)
    cols = [(BVHTree.FromObject(o, deps), o.matrix_world.inverted()) for o in bpy.data.objects if o.name.startswith("COL_")]
    def reach(trees, y, z, dirv=(-1, 0, 0)):
        best = 99.0
        for t_, inv in trees:                                  # BVH 는 물체 제 좌표다 — 광선을 그 좌표로 옮겨 쏜다 (가져온 COL 은 제 변환이 있다)
            o_, d_ = inv @ Vector((0, y, z)), (inv.to_3x3() @ Vector(dirv))
            hit = t_.ray_cast(o_, d_.normalized())
            if hit[0] is not None: best = min(best, hit[3] / d_.length)
        return best
    zc = min(1.0, H * 0.5); vis1 = [(vis, shl.matrix_world.inverted())]
    r_vis, r_col = reach(vis1, Y, zc), reach(cols, Y, zc)
    r_side_vis, r_side_col = reach(vis1, Y + HW + 0.5, zc), reach(cols, Y + HW + 0.5, zc)
    r_above = reach(cols, Y, H + 0.4)
    # 틈 안 1 m 깊이에서 양옆·위로 쏴서 면이 다 있나 (보이는 면)
    inside_pt = Vector((WALL_X - 1.0, Y, zc)); holes = 0
    for dv in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        hit = vis.ray_cast(inside_pt, Vector(dv)); holes += hit[0] is None or hit[3] > 3.0
    print("CHECK %s: cut %d wall faces · ray into the gap travels %.2f m visible / %.2f m collision (tunnel wall at 3.2, gap end at %.2f) · beside the gap %.2f / %.2f · above the gap (collision) %.2f · open directions inside the gap %d · new faces %d · uv/m %.3f"
          % (name, cut_faces, r_vis, r_col, -WALL_X + D, r_side_vis, r_side_col, r_above, holes, len(new_faces), uv_per_m))
    assert r_vis > -WALL_X + D - 0.4, "FAIL: 보이는 벽이 안 뚫렸다"
    assert r_col > -COL_X0 + D - 0.1, "FAIL: 충돌 벽이 안 뚫렸다"
    assert r_vis < -WALL_X + D + 0.4 and r_col < -COL_X0 + D + 0.4, "FAIL: 틈 안쪽 끝이 없다"
    assert r_side_vis < 3.6 and r_side_col < 3.3 and r_above < 3.3, "FAIL: 틈 옆·위 벽이 사라졌다"
    assert holes == 0, "FAIL: 틈 안에 면이 빠진 데가 있다"

    # ---- 내보내기: 그림은 원래 파일을 그대로 가리킨다
    out = os.path.join(PIECES, name + SUFFIX + ".gltf")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLTF_SEPARATE", export_keep_originals=True, export_apply=True, export_yup=True, export_extras=True)
    doc = json.load(open(out, encoding="utf-8"))
    uris = [im["uri"] for im in doc.get("images", [])]
    missing = [u for u in uris if not os.path.exists(os.path.join(PIECES, u.replace("%20", " ")))]
    names = [n_.get("name", "") for n_ in doc["nodes"]]
    print("CHECK %s: wrote %s (%d KB bin) · %d images, missing %d · nodes %d (COL %d, SLOT %d)" % (name, os.path.basename(out), os.path.getsize(out[:-5] + ".bin") // 1024, len(uris), len(missing), len(names), sum(n_.startswith("COL_") for n_ in names), sum(n_.startswith("SLOT_Pocket_") for n_ in names)))
    assert not missing, "FAIL: 새 gltf 가 없는 그림을 가리킨다: %s" % missing
    assert all(u.startswith("textures/") for u in uris), "FAIL: 그림 경로가 textures/ 밖이다: %s" % uris
    assert sum(n_.startswith("SLOT_Pocket_") for n_ in names) == 4, "FAIL: 광맥 자리 넷이 다 안 남았다"

for name, g in GAPS.items():
    build(name, g)
for f, h in src_md5.items():
    assert md5(os.path.join(PIECES, f)) == h, "FAIL: 원본 조각이 바뀌었다: " + f
print("CHECK source piece untouched (md5 same) · ALL OK")
