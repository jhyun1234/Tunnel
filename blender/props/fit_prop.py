"""Meshy 소품을 게임 크기·축·원점에 맞춘다 (제안서 A1, 2026-09-23 승인 — 1차 곡괭이·갱목·전등).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/props/fit_prop.py -- [이름 …]   (이름 없으면 표 전부)
입력(안 고친다): Documents/MineTunnel/mesh/props/meshy_<이름>.glb  (gen_meshy.py --text 가 받은 것)
출력(덮어쓴다): Assets/Tunnel/Props/<이름>.glb — 그림은 GLB 안에 (4K→1K 줄이기는 tools/fit_props.sh 가 shrink_glb.py 로 뒤에 한다)
하는 일: 그물을 하나로 합침 → PCA(점 구름의 긴 축·중간 축·짧은 축)로 축을 맞춤(긴 축 → Blender Z = glTF Y, 중간 축 → X) → "무거운 끝"(끝 15 % 구간의 옆 폭이 큰 쪽)을 표의 방향에
        → 긴 축 길이를 표의 실제 크기로 → 원점을 표의 규칙대로 → 면 예산 넘으면 Decimate → 곡괭이는 머리·자루로 가른다(ThrownPick 이 PICK_Head 를 찾는다)
자기 검사(FAIL 이면 종료 1): 긴 축 길이 = 표 ±1 % · 면 수 ≤ 예산 · 원점 규칙 · 곡괭이 머리 폭 ≥ 0.3 m(머리가 갈라졌나) · 그림이 다 들어 있나
사보타주: SABOTAGE=noscale(배율 안 맞춤) → 길이 FAIL · nosplit(곡괭이를 안 가름) → 머리 FAIL · mirror(왼손 좌표계) → det FAIL"""
import bpy, bmesh, os, sys, json, struct
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC_DIR = r"C:\Users\anjyo\Documents\MineTunnel\mesh\props"
OUT_DIR = os.path.join(ROOT, "Assets", "Tunnel", "Props")
SAB = os.environ.get("SABOTAGE", "")
os.makedirs(OUT_DIR, exist_ok=True)

# 표: long = 긴 축 실제 길이(m) · heavy = 무거운 끝을 위(+Z, glTF +Y)로(True) / 아래로(False) / 상관없음(None) · origin = "top"(위 끝을 origin_y 에) · "center" · "bottom"
#     Blender 는 Z 위 · glTF 는 Y 위 — 내보내기(export_yup)가 바꿔 준다. 아래의 "긴 축"은 Blender Z
#     src = mesh/props 의 Meshy 파일(다시 뽑으면 여기만 바꾼다) · tris = 면 예산 · normalmap=False = 노멀맵을 뗀다(통나무: 1.3k 면 원통에 얹으면 어두운 마름모 얼룩 — 09-23 게임 그림)
#     Meshy remesh API(timber_log3_6k, 5 크레딧)는 찢어진 껍데기가 왔다(경계 변 530) — 안 쓴다 · split = 곡괭이 머리·자루 가르기 · name = 내보낼 물체 이름
PROPS = {
    "pickaxe":    dict(src="meshy_pickaxe2.glb", long=0.88, heavy=True,  origin="top",    origin_y=0.73, tris=8000, split=True,  name="PICK_Handle"),   # pick.gltf 와 같은 틀: 자루 +Y, 머리 위(y 0.63~0.73), 머리 폭 X, 원점 = 쥐는 곳
    "pick_meshy": dict(src="meshy_pick_boryeong.glb", long=0.68, heavy=True, origin="top", origin_y=0.53, tris=8000, split=True, name="PICK_Handle",
                       center="handle", point="+X", head_min=0.25),   # PICK-1 B (09-27): make_pick.py 그림 4장 → Meshy. 한쪽 날이라 자루를 가운데에, 날은 +X(make_pick.py 와 같은 틀)
    "timber_log": dict(src="meshy_timber_log3.glb", long=4.80, heavy=None,  origin="center", origin_y=0.0,  tris=1600, normalmap=False, split=False, name="PRP_timber_log"),   # 굵기 0.34 로 균일하게 줄이면 토막 1.7 m — piece_v2.py 가 기둥 3 · 가로대 4 토막으로 잇는다(조각마다 40 토막이라 면을 아낀다)
    "mine_lamp":  dict(src="meshy_mine_lamp.glb", long=0.30, heavy=False, origin="top",    origin_y=0.0,  tris=3000, split=False, name="PRP_mine_lamp"),    # 매다는 점이 원점, 전구가 아래
}
want = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else list(PROPS)
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg); fails.append(msg) if not ok else None


def fit(name, spec):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = os.path.join(SRC_DIR, spec["src"])
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in bpy.data.objects:
        if o.type != "MESH": bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.objects.active = meshes[0]
    for o in meshes: o.select_set(True)
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = ob.data
    # Meshy GLB 는 UV 솔기마다 점이 갈라져 있고(변의 60 % 가 경계) 면 일부가 안쪽을 향해 감겨 있다 → 단면 컬링(URP)에서 그 면이 사라져 구멍처럼 보였다(09-23 timber_log2·3 게임 그림).
    # 자리로 점을 합치고(UV 는 loop 값이라 그대로) 면 방향을 바깥으로 다시 계산한 뒤 Meshy 손질 법선은 버리고 각도 스무딩으로
    bm = bmesh.new(); bm.from_mesh(me)
    n0 = [f.normal.copy() for f in bm.faces]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    flipped = sum(1 for f, n in zip(bm.faces, n0) if f.normal.dot(n) < 0) if len(bm.faces) == len(n0) else -1
    holes = sum(1 for e in bm.edges if e.is_boundary)
    bm.to_mesh(me); bm.free(); me.update()
    if hasattr(me, "normals_split_custom_clear"): me.normals_split_custom_clear()
    else: bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.shade_auto_smooth(angle=0.6981)                 # 40°
    check(holes <= 50, "%s 점 합친 뒤 진짜 경계 변 %d (≤ 50 — 그물이 닫혀 있나) · 바깥으로 뒤집은 면 %d" % (name, holes, flipped))
    P = np.array([v.co[:] for v in me.vertices])
    c = P.mean(axis=0); Q = P - c
    w, V = np.linalg.eigh(Q.T @ Q)                      # 고유값 오름차순 → V[:, 2] 긴 축, V[:, 1] 중간, V[:, 0] 짧은
    e_long, e_mid, e_short = V[:, 2], V[:, 1], V[:, 0]
    # 무거운 끝: 긴 축 좌표의 위 15 % 와 아래 15 % 에 든 점들의 옆 퍼짐(중간·짧은 축 표준편차 합)
    t = Q @ e_long; lo, hi = np.percentile(t, [15, 85])
    def spread(sel): return Q[sel] @ e_mid, Q[sel] @ e_short
    a, b = spread(t >= hi); top = a.std() + b.std()
    a, b = spread(t <= lo); bot = a.std() + b.std()
    if spec["heavy"] is not None and (top > bot) != spec["heavy"]:
        e_long = -e_long
    if spec.get("center") == "handle":       # 한쪽 날 곡괭이: 머리 무게 때문에 긴 축이 자루에서 기운다(09-27 pick_meshy 약 4°) → 아래 55 % (자루)만으로 긴 축을 다시
        t = Q @ e_long; H = Q[t < np.percentile(t, 55)]; H = H - H.mean(axis=0)
        e2 = np.linalg.eigh(H.T @ H)[1][:, 2]; e_long = e2 if np.dot(e2, e_long) > 0 else -e2
        e_mid = e_mid - np.dot(e_mid, e_long) * e_long; e_mid /= np.linalg.norm(e_mid); e_short = np.cross(e_long, e_mid)
    e_mid = e_mid if np.dot(np.cross(e_mid, e_short), e_long) > 0 else -e_mid       # 오른손 좌표계 유지 (거울이 되면 면이 뒤집힌다)
    e_short = np.cross(e_long, e_mid)
    if SAB == "mirror": e_short = -e_short                # 사보타주: 왼손 좌표계(1차 사고 재현) → det 검사 FAIL
    R = np.stack([e_mid, e_short, e_long], axis=1)        # 열 = 새 X·Y·Z(Blender) 가 원래 좌표에서 어느 방향인가. 긴 축 → Z(위), 중간 → X, 짧은 → Y. e_short = e_long × e_mid 라 X × Y = Z (오른손)
    check(np.linalg.det(R) > 0.99, "%s 축 행렬이 오른손 좌표계 (det %.2f) — 거울이면 그림이 뒤집힌다 (09-23 1차: −e_short 로 넣어 거울이었다)" % (name, np.linalg.det(R)))
    P2 = Q @ R
    LA = 2                                                 # 긴 축 = 열 2 (Blender Z)
    ext = P2.max(axis=0) - P2.min(axis=0)
    s = spec["long"] / ext[LA] if SAB != "noscale" else 1.0
    P2 *= s
    ymin, ymax = P2[:, LA].min(), P2[:, LA].max()
    if spec["origin"] == "top": P2[:, LA] += spec["origin_y"] - ymax
    elif spec["origin"] == "bottom": P2[:, LA] += spec["origin_y"] - ymin
    else: P2[:, LA] -= (ymin + ymax) / 2
    ys_ = P2[:, LA]
    ref = P2[ys_ < ys_.min() + 0.5 * (ys_.max() - ys_.min())] if spec.get("center") == "handle" else P2   # 한쪽 날: 전체 가운데로 맞추면 자루가 옆으로 밀린다 → 자루(아래 반) 가운데를 0 에
    P2[:, 0] -= (ref[:, 0].min() + ref[:, 0].max()) / 2; P2[:, 1] -= (ref[:, 1].min() + ref[:, 1].max()) / 2
    if spec.get("point") == "+X":
        hd = P2[ys_ > ys_.max() - 0.08]
        if hd[:, 0].max() < -hd[:, 0].min(): P2[:, 0] *= -1; P2[:, 1] *= -1     # Z 축으로 180° 돌림(거울 아님) — 날을 +X 로
        hd = P2[ys_ > ys_.max() - 0.08]
        check(hd[:, 0].max() > 3 * -hd[:, 0].min(), "%s 날이 +X 한쪽: +X %.3f · −X %.3f" % (name, hd[:, 0].max(), -hd[:, 0].min()))
    for v, p in zip(me.vertices, P2): v.co = p
    me.update()
    # 면 예산
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    if tris > spec["tris"]:
        mod = ob.modifiers.new("dec", "DECIMATE"); mod.ratio = spec["tris"] / tris * 0.98
        bpy.ops.object.modifier_apply(modifier=mod.name)
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
    ob.name = spec["name"]; me.name = spec["name"]
    for im in list(bpy.data.images):                      # 그림 이름에 소품 이름을 — 조각에 둘을 넣을 때 "Image_0" 이 겹치지 않게 (list() — 이름을 바꾸면 모음 순서가 바뀌어 같은 그림을 또 만난다)
        if not im.name.startswith("prop_"): im.name = "prop_%s_%s" % (name, im.name)
    for m in list(bpy.data.materials):
        if not m.name.startswith("MAT_prop_"): m.name = "MAT_prop_%s_%s" % (name, m.name)
        if not spec.get("normalmap", True) and m.use_nodes:
            for l in list(m.node_tree.links):
                if l.to_socket.name == "Normal": m.node_tree.links.remove(l)
        m.use_backface_culling = True                     # glTF doubleSided=false — Meshy 그물은 닫혀 있다. 양면이면 URP 에서 뒷면이 제 앞면에 그림자를 드리워 새까맣게 보였다(09-23 1차 게임 그림)
    ext2 = P2.max(axis=0) - P2.min(axis=0)
    check(abs(ext2[LA] - spec["long"]) <= spec["long"] * 0.01, "%s 긴 축(glTF Y) %.3f m = 표 %.2f ±1 %% · 옆 %.2f × %.2f" % (name, ext2[LA], spec["long"], ext2[0], ext2[1]))
    check(tris <= spec["tris"], "%s 면 %d ≤ 예산 %d" % (name, tris, spec["tris"]))
    ymin, ymax = P2[:, LA].min(), P2[:, LA].max()
    want_y = {"top": ymax, "bottom": ymin, "center": (ymin + ymax) / 2}[spec["origin"]]
    check(abs(want_y - spec["origin_y"]) < 1e-3, "%s 원점 %s: y %.3f = %.2f" % (name, spec["origin"], want_y, spec["origin_y"]))
    if spec["split"] and SAB != "nosplit":
        # 머리 = 옆 폭(XZ)이 자루 중간값의 3배를 넘기 시작하는 y 부터 위. 자루 폭은 아래 반의 폭 중간값
        ys = P2[:, LA]; bins = np.linspace(ymin, ymax, 41)
        widths = []
        for y0, y1 in zip(bins, bins[1:]):
            sel = (ys >= y0) & (ys < y1)
            widths.append((P2[sel, 0].max() - P2[sel, 0].min()) if sel.any() else 0.0)
        handle_w = float(np.median([w_ for w_ in widths[:20] if w_ > 0]))
        y_split = next((bins[i] for i in range(20, 40) if widths[i] > handle_w * 3), None)
        check(y_split is not None, "%s 머리 시작 높이를 찾았다 (자루 폭 %.3f)" % (name, handle_w))
        if y_split is not None:
            bm = bmesh.new(); bm.from_mesh(me)
            head = [f for f in bm.faces if sum(v.co.z for v in f.verts) / len(f.verts) >= y_split - 0.01]
            head_set = set(head)
            hv = {v for f in head for v in f.verts}
            bm2 = bmesh.new()                                 # 머리 면들을 새 그물로 복사
            vmap = {}
            for v in hv: vmap[v] = bm2.verts.new(v.co)
            uv0 = bm.loops.layers.uv.active; uv2 = bm2.loops.layers.uv.new(uv0.name)
            for f in head:
                try: nf = bm2.faces.new([vmap[v] for v in f.verts])
                except ValueError: continue
                nf.material_index = f.material_index
                for l0, l2 in zip(f.loops, nf.loops): l2[uv2].uv = l0[uv0].uv
            me_h = bpy.data.meshes.new("PICK_Head"); bm2.to_mesh(me_h); bm2.free()
            for m in me.materials: me_h.materials.append(m)
            bmesh.ops.delete(bm, geom=head, context="FACES"); bm.to_mesh(me); bm.free()
            oh = bpy.data.objects.new("PICK_Head", me_h); bpy.context.scene.collection.objects.link(oh)
            hp = np.array([v.co[:] for v in me_h.vertices])
            hmin = spec.get("head_min", 0.3)
            check(len(hp) > 0 and hp[:, 0].max() - hp[:, 0].min() >= hmin, "%s 머리(PICK_Head) 폭 %.2f m ≥ %.2f · 머리 시작 y %.3f" % (name, (hp[:, 0].max() - hp[:, 0].min()) if len(hp) else 0, hmin, y_split))
    elif spec["split"]:
        check(False, "%s 머리·자루를 안 갈랐다 (사보타주 nosplit)" % name)
    out = os.path.join(OUT_DIR, name + ".glb")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_image_format="AUTO")
    d = open(out, "rb").read(); jl = struct.unpack_from("<I", d, 12)[0]; js = json.loads(d[20:20 + jl])
    check(len(js.get("images", [])) >= 1 and all("bufferView" in im for im in js["images"]), "%s 그림 %d장이 GLB 안에" % (name, len(js.get("images", []))))
    print("wrote %s %.1f MB · nodes %s" % (out, len(d) / 1e6, [n.get("name") for n in js["nodes"]]))


for n in want:
    fit(n, PROPS[n])
print("fit_prop: ALL PASS" if not fails else "fit_prop: FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
