"""m3 손목: 팔 끝(m3_assemble.py 가 손목에서 잘라 막은 자리)이 손보다 굵고 손 속 뼈 토막이 튀어나와 게임에서 잘린 대롱 + 허연 마개 + 이어지지 않는 손으로 보였다(사용자 09-22 캡처).
팔 그물은 손목 앞 15 cm 에 점이 스무 개 남짓(Meshy 24k 면)이라 점을 빚어서는 안 된다(09-22: 톱니·구멍) →
**팔의 마지막 CUT cm 를 지우고, 팔 제 단면에서 손 단면으로 이어지는 소매 관을 새로 짠다**(둘레 SEG 점 × 고리 5개, 광선으로 잰 반지름):
  −CUT: 원래 팔 단면 + 1.5 mm(팔 끝을 덮는다) → −0.035: 손(뼈 토막까지) 단면 + INSET(손의 열린 고리를 감싼다) → −0.015: 손 + 2 mm → +0.01: 손 살 단면(±10° 최솟값) − INSET(관 끝이 손 속에) — 그 사이에서 팔·손 겉면이 엇갈려 이어진다.
  blender -b --factory-startup -P blender/rig/m3_wrist.py
입력: Documents/MineTunnel/blender/miner_v5_stage20_m3_glow.blend (안 고친다) · 출력: miner_v5_stage21_m3_wrist.blend → m3_props.py
2차(09-22 사용자 판정 "그림 뭉개짐 · 왼쪽 뒤틀림 · 고무 소매"): ① 관 UV 를 4 mm 네모에 몰던 것을 버리고 **관 면마다 가장 가까운 지운 팔 면의 UV 를 아핀으로 이어받는다**(팔 무늬·노멀이 관에 그대로 이어진다)
  ② 잘린 자리에 걸친 팔 면(한 점만 CUT 너머, 왼쪽 41개)이 관 위로 삐죽 남아 톱니로 보였다 → 걸친 면도 지우고 팔 경계 고리와 관 첫 고리를 bridge_loops 로 잇는다(구멍 0).
사보타주: SABOTAGE=nowrist(안 함) · flatuv(옛 4 mm 네모 UV) -> 검사 FAIL
SHOTS=<폴더> 를 주면 손목 확대 그림(Workbench TEXTURE) 64_wrist_uv_{L,R}_*.png"""
import bpy, bmesh, os, sys, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage20_m3_glow.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage21_m3_wrist.blend"))
SABOTAGE = os.environ.get("SABOTAGE", "")
SHOTS = os.environ.get("SHOTS", "")
P = "mixamorig:"
CUT, INSET, SEG = 0.12, 0.008, 36
RINGS = ((-0.08, "mix"), (-0.035, "wrap"), (-0.015, "wrap2"), (0.01, "end"))          # 첫 고리(−CUT)는 관이 아니라 bisect 로 자른 팔 제 경계 → bridge_loops 로 잇는다(2차)

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
arm = bpy.data.objects["Miner_Rig"]; arm.data.pose_position = "REST"; bpy.context.view_layer.update()
A = arm.matrix_world
body, hands = bpy.data.objects["Miner_Body"], bpy.data.objects["Miner_Hands"]
bw, hw = body.matrix_world, hands.matrix_world
def co_w(o): return np.array([o.matrix_world @ v.co for v in o.data.vertices])
def tree_of(o):
    V = co_w(o); return BVHTree.FromPolygons([tuple(p) for p in V], [p_.vertices[:] for p_ in o.data.polygons])
hand_tree = tree_of(hands)
rows = []
for side in ("Left", "Right"):
    sx = 1 if side == "Left" else -1
    wr = np.array(A @ arm.data.bones[P + side + "Hand"].head_local); fa = np.array(A @ arm.data.bones[P + side + "ForeArm"].head_local)
    u = (wr - fa) / np.linalg.norm(wr - fa); e1 = np.cross(u, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    B = co_w(body); rel = B - wr; tb = rel @ u; rad = rel - np.outer(tb, u)
    limb = (B[:, 0] * sx) > abs(fa[0])
    ring = limb & (np.abs(tb) < 0.03) & (np.linalg.norm(rad, axis=1) > 0.05)
    c = wr + rad[ring].mean(0)                                            # 손목 뼈는 단면 가장자리에 있다(09-22) → 단면 가운데 = 팔 끝 고리 점들의 평균
    body_tree = tree_of(body)
    def prof(tree, t, smooth=2):
        """둘레 SEG 칸: 밖에서 안으로 쏜 광선이 처음 닿는 거리(겉면). 빈 칸은 이웃에서 잇고 ±smooth 칸 최댓값으로 고르게"""
        out = np.full(SEG, np.nan)
        for j in range(SEG):
            th = j / SEG * 2 * math.pi; d = Vector(e1 * math.cos(th) + e2 * math.sin(th))
            hit = tree.ray_cast(Vector(c + u * t) + d * 0.4, -d, 0.4)
            if hit[0] is not None:
                out[j] = 0.4 - hit[3]
        ok = ~np.isnan(out); out = np.interp(np.arange(SEG), np.where(ok)[0], out[ok], period=SEG) if ok.sum() >= 4 else np.nan_to_num(out, nan=0.03)
        if not smooth:
            return out
        st = np.stack([np.roll(out, o) for o in range(-abs(smooth), abs(smooth) + 1)])
        return np.max(st, axis=0) if smooth > 0 else np.min(st, axis=0)                  # smooth < 0: ±칸 최솟값 (관 끝을 손 속에 넣을 때 보수적으로)
    r_arm = prof(body_tree, -CUT - 0.005, 0) + 0.0005
    r_wrap = np.maximum(prof(hand_tree, -0.035), prof(hand_tree, -0.025)) + INSET
    r_wrap2 = prof(hand_tree, -0.015) + 0.002
    r_end = np.minimum(np.minimum(prof(hand_tree, 0.0, -2), prof(hand_tree, 0.01, -2)), prof(hand_tree, 0.02, -2)) - INSET       # 손 살 겉의 ±10° 최솟값보다 INSET 안 — 최댓값으로 재면 울퉁불퉁한 곳에서 관이 손 밖으로 나온다
    r_mix = 0.5 * (r_arm + r_wrap)
    radii = {"arm": r_arm, "mix": r_mix, "wrap": r_wrap, "wrap2": r_wrap2, "end": r_end}
    if SABOTAGE != "nowrist":
        # 팔의 마지막 CUT cm 를 지운다: 뼈대 무게·UV 는 지운 점에서 가장 가까운 것을 새 관에 물려준다
        bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        dl = bm.verts.layers.deform.verify(); uvl = bm.loops.layers.uv.active
        def cut_t(v):
            p = np.array(bw @ v.co); return (p[0] * sx) > abs(fa[0]) and ((p - wr) @ u) > -CUT
        gone = [f for f in bm.faces if any(cut_t(v) for v in f.verts)]                       # 걸친 면(한 점만 CUT 너머)도 UV·무게 기부자로 — 형상은 bisect 로 평면에서 자른다(2차)
        donors = []                                                        # (세계 자리, 무게 dict, uv)
        tri_p, tri_uv = [], []                                             # UV 이어받기용 지운 면(마개 빼고): 세 점 세계 자리 · UV
        for f in gone:
            for lp in f.loops:
                donors.append((np.array(bw @ lp.vert.co), dict(lp.vert[dl]), tuple(lp[uvl].uv)))
            if abs(np.array(bw.to_3x3() @ f.normal) @ u) < 0.6 and len(f.verts) == 3:    # 팔 끝 마개(u 와 나란한 면, 허연 색)는 UV 주지 않음
                tri_p.append([np.array(bw @ lp.vert.co) for lp in f.loops]); tri_uv.append([np.array(lp[uvl].uv, dtype=float) for lp in f.loops])
        mat_idx = gone[0].material_index if gone else 0; n_gone = len(gone)
        # 평면 t = −CUT 에서 걸친 면을 자르고 CUT 너머를 버린다 → 경계가 평면 위 한 고리(UV 는 bisect 가 보간). 몸통까지 잘리지 않게 geom 은 걸친 면만
        geom = list({x for f in gone for x in (f, *f.edges, *f.verts)})
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=body.matrix_world.inverted() @ Vector(c + u * -CUT), plane_no=(body.matrix_world.inverted().to_3x3() @ Vector(u)).normalized(), clear_outer=True, clear_inner=False)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        dpos = np.array([d_[0] for d_ in donors])
        bwi = bw.inverted()
        uv_tree = BVHTree.FromPolygons([tuple(p) for t in tri_p for p in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tri_p))])
        def uv_affine(p_center, corners):
            """면 가운데에서 가장 가까운 지운 팔 면 하나를 골라, 그 면의 3D→UV 아핀을 네 모서리에 적용(모서리마다 다른 면을 고르면 섬이 갈려 얼룩)"""
            hit = uv_tree.find_nearest(Vector(p_center)); i = hit[2]
            P0, P1, P2 = tri_p[i]; U0, U1, U2 = tri_uv[i]
            E = np.stack([P1 - P0, P2 - P0], 1); J = np.stack([U1 - U0, U2 - U0], 1) @ np.linalg.pinv(E)   # 2×3
            return [tuple(U0 + J @ (q - P0)) for q in corners]
        k0 = int(np.argmin(np.linalg.norm(dpos - (c + u * -CUT), axis=1))); uc, vc = donors[k0][2]      # flatuv 사보타주(옛 방식)용
        # 평면 위 경계 고리: Meshy GLB 는 UV 솔기마다 점이 갈라져 있다(27,145 점 = 자리 10,754 개) → 고리 점을 합쳐 한 줄로
        def on_cut(v):
            p = np.array(bw @ v.co); return (p[0] * sx) > abs(fa[0]) and abs(((p - wr) @ u) + CUT) < 1e-3
        bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if on_cut(v)], dist=1e-4)
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
        bnd = [e for e in bm.edges if e.is_boundary and all(on_cut(v) for v in e.verts)]
        deg = {}
        for e in bnd:
            for v in e.verts:
                deg[v] = deg.get(v, 0) + 1
        n_loops = sum(1 for d_ in deg.values() if d_ != 2)                  # 0 이면 닫힌 고리(모든 점 차수 2)
        vs = []
        for ri, (t, key) in enumerate(RINGS):
            r = radii[key]; row = []
            for j in range(SEG):
                th = j / SEG * 2 * math.pi; pw = c + u * t + (e1 * math.cos(th) + e2 * math.sin(th)) * r[j]
                v = bm.verts.new(bwi @ Vector(pw)); k = int(np.argmin(np.linalg.norm(dpos - pw, axis=1)))
                for g, w in donors[k][1].items():
                    v[dl][g] = w
                row.append((v, pw, (uc + (j / SEG - 0.5) * 0.004, vc + (ri / len(RINGS) - 0.5) * 0.004)))
            vs.append(row)
        new_faces = []
        for a_, b_ in zip(vs[:-1], vs[1:]):
            for j in range(SEG):
                q = [a_[j], a_[(j + 1) % SEG], b_[(j + 1) % SEG], b_[j]]
                f = bm.faces.new([x[0] for x in q]); f.material_index = mat_idx; f.smooth = True; new_faces.append(f)
                if SABOTAGE == "flatuv":
                    for lp, x in zip(f.loops, q):
                        lp[uvl].uv = x[2]
        ring_v = set(x[0] for x in vs[0])
        ring0 = [e for e in bm.edges if e.verts[0] in ring_v and e.verts[1] in ring_v]
        br = bmesh.ops.bridge_loops(bm, edges=bnd + ring0, use_pairs=False, use_cyclic=False, use_merge=False, twist_offset=0)
        for f in br["faces"]:
            f.material_index = mat_idx; f.smooth = True; new_faces.append(f)
            if SABOTAGE == "flatuv":
                for lp in f.loops:
                    lp[uvl].uv = (uc, vc)
        for f in new_faces:
            if SABOTAGE != "flatuv":
                fc = np.array(bw @ f.calc_center_median())
                for lp, uv in zip(f.loops, uv_affine(fc, [np.array(bw @ lp.vert.co) for lp in f.loops])):
                    lp[uvl].uv = uv
            fc = np.array(bw @ f.calc_center_median())
            if (np.array(bw.to_3x3() @ f.normal) @ (fc - (c + u * ((fc - c) @ u)))) < 0:
                f.normal_flip()                                        # 겉면이 밖을 보게
        n_bridge = len(br["faces"]); n_bnd = len(bnd)
        if os.environ.get("DIAG"):
            ts_ = [((np.array(bw @ v.co) - wr) @ u) for e in bnd for v in e.verts]; rs_ = [np.linalg.norm((np.array(bw @ v.co) - c) - u * ((np.array(bw @ v.co) - c) @ u)) for e in bnd for v in e.verts]
            print("  cut loop edges", len(bnd), "odd-degree verts", n_loops, "t %.3f..%.3f r %.3f..%.3f" % (min(ts_), max(ts_), min(rs_), max(rs_)))
            L_ = [max((e.verts[0].co - e.verts[1].co).length for e in f.edges) for f in br["faces"]]
            print("  bridge faces", len(br["faces"]), "longest edge %.3f median %.3f" % (max(L_), float(np.median(L_))))
        # 검사 재료: ① 잘린 자리 둘레 구멍(경계 변) — 관 끝 고리(손 속) 빼고 0 이어야 ② 관 텍셀 밀도 — 지운 팔 면에 견줘
        end_v = set(x[0] for x in vs[-1])
        def in_zone(v):
            p = np.array(bw @ v.co); return (p[0] * sx) > abs(fa[0]) and -0.30 < ((p - wr) @ u) < 0.02
        # 진짜 구멍 변 = 경계 변 중 같은 자리에 쌍둥이 변(UV 솔기)이 없는 것
        key = lambda e: tuple(sorted(tuple(np.round(np.array(bw @ v.co), 4)) for v in e.verts))
        seen = {}
        for e in bm.edges:
            seen[key(e)] = seen.get(key(e), 0) + 1
        holes = sum(1 for e in bm.edges if e.is_boundary and all(in_zone(v) and v not in end_v for v in e.verts) and seen[key(e)] == 1)
        # 관 텍셀 밀도(UV 넓이 ÷ 3D 넓이)를 지운 팔 면에 견준다 — 옛 4 mm 네모 UV 는 0 에 가깝다(그림이 뭉개져 보인 까닭, 사용자 09-22)
        def uv_area(uvs):
            x, y = np.array(uvs).T; return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        dens_new = sum(uv_area([lp[uvl].uv for lp in f.loops]) for f in new_faces) / max(sum(f.calc_area() for f in new_faces), 1e-9)
        dens_arm = sum(uv_area(t) for t in tri_uv) / max(sum(0.5 * np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) for t in tri_p), 1e-9)
        tex_ratio = float(dens_new / max(dens_arm, 1e-9))
        bm.faces.index_update(); new_idx = {f.index for f in new_faces}
        smooth_pos = {tuple(np.round(v.co, 4)) for f in new_faces for v in f.verts} | {tuple(np.round(v.co, 4)) for e in bnd for v in e.verts}
        bm.to_mesh(body.data); bm.free(); body.data.update()
        # 법선: Meshy GLB 는 손질된 법선(custom normals)을 들고 있다(UV 솔기마다 갈라진 점을 매끈하게 잇는 것). 새 면·잘린 자리 점은 그 값이 없어 검은 띠·모난 고리로 보인다 →
        # 새 면과 경계의 점은 "같은 자리의 모든 면" 법선 넓이 평균으로, 나머지는 있던 값 그대로 다시 넣는다
        me = body.data; acc = {}
        for pg in me.polygons:
            for vi in pg.vertices:
                k_ = tuple(np.round(me.vertices[vi].co, 4))
                if k_ in smooth_pos:
                    acc[k_] = acc.get(k_, np.zeros(3)) + np.array(pg.normal) * pg.area
        cn = [tuple(l.vector) for l in me.corner_normals]
        for pg in me.polygons:
            for li in pg.loop_indices:
                k_ = tuple(np.round(me.vertices[me.loops[li].vertex_index].co, 4))
                if k_ in acc and (pg.index in new_idx or k_ in smooth_pos):
                    n_ = acc[k_]; cn[li] = tuple(n_ / max(np.linalg.norm(n_), 1e-9))
        me.normals_split_custom_set(cn)
        print("%s 손목: 팔 끝 면 %d 지우고 소매 관 %d 점 %d 면 + 팔 경계(%d 변, 차수≠2 점 %d)와 이음 %d 면" % (side, n_gone, SEG * len(RINGS), SEG * (len(RINGS) - 1), n_bnd, n_loops, n_bridge))
    body_tree = tree_of(body)
    b_end = prof(body_tree, 0.006, 0); h_end = prof(hand_tree, 0.006, 0)
    b_wrap = prof(body_tree, -0.03, 0); h_wrap = prof(hand_tree, -0.03, 0)
    b_cut = prof(body_tree, -CUT - 0.02, 0); b_cut2 = prof(body_tree, -CUT + 0.005, 0)
    inside = float(np.mean(b_end <= h_end - 0.002)); outside = float(np.mean(b_wrap >= h_wrap)); step = float(np.abs(b_cut2 - b_cut).max())
    if SABOTAGE != "nowrist":
        check(holes == 0 and 0.5 <= tex_ratio <= 2.0,
              "%s 손목 2차: 잘린 자리 둘레 구멍 변 %d (0) · 관 텍셀 밀도 / 팔 %.2f (0.5~2)" % (side, holes, tex_ratio))
    check(inside >= 0.85 and outside >= 0.8 and step <= 0.012,
          "%s 손목: 관 끝이 손 겉 안쪽인 칸 %.0f %% (≥ 85) · 손 시작(t −3 cm)을 관이 감싸는 칸 %.0f %% (≥ 80) · 관 시작에서 팔과의 턱 최대 %.1f mm (≤ 12) — 팔 %.3f → 관 끝 %.3f, 손 %.3f m" %
          (side, inside * 100, outside * 100, step * 1000, float(r_arm.mean()), float(b_end.mean()), float(h_end.mean())))
    rows.append((side[0], c, u))
if SHOTS:
    os.makedirs(SHOTS, exist_ok=True); sc = bpy.context.scene
    hidden = {o: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name in ("Miner_Neck",)
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.45
    sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = 900; sc.render.resolution_y = 900
    sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_cavity = True; sh.show_backface_culling = True
    sc.view_settings.exposure = 2.0                                    # 살 그림이 어둡다(게임은 램프가 비춘다)
    for tag, c, u in rows:
        tgt = Vector(c + u * -0.06)
        for nm, d in (("front", (0, -1, 0)), ("top", (0, 0, 1)), ("under", (0, 0, -1)), ("back", (0, 1, 0))):
            cam.location = tgt + Vector(d) * 2.0; cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(SHOTS, "64_wrist_uv_%s_%s.png" % (tag, nm)); bpy.ops.render.render(write_still=True)
            if os.environ.get("DIAG"):
                sh.color_type = "RANDOM"; sc.render.filepath = os.path.join(SHOTS, "64_wrist_faces_%s_%s.png" % (tag, nm)); bpy.ops.render.render(write_still=True); sh.color_type = "TEXTURE"
    bpy.data.objects.remove(cam, do_unlink=True)
    for o, h in hidden.items():
        o.hide_render = h
arm.data.pose_position = "POSE"
if fails:
    sys.exit("m3_wrist FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_wrist ALL PASS →", OUT)
