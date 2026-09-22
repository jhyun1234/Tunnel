"""m3 손목: 팔 끝(m3_assemble.py 가 손목에서 잘라 막은 자리)이 손보다 굵고 손 속 뼈 토막이 튀어나와 게임에서 잘린 대롱 + 허연 마개 + 이어지지 않는 손으로 보였다(사용자 09-22 캡처).
팔 그물은 손목 앞 15 cm 에 점이 스무 개 남짓(Meshy 24k 면)이라 점을 빚어서는 안 된다(09-22: 톱니·구멍) →
**팔의 마지막 CUT cm 를 지우고, 팔 제 단면에서 손 단면으로 이어지는 소매 관을 새로 짠다**(둘레 SEG 점 × 고리 4개, 광선으로 잰 반지름):
  −CUT: 원래 팔 단면 + 1.5 mm(팔 끝을 덮는다) → −0.035: 손(뼈 토막까지) 단면 + INSET(손의 열린 고리를 감싼다) → −0.015: 손 + 2 mm → +0.01: 손 살 단면(±10° 최솟값) − INSET(관 끝이 손 속에) — 그 사이에서 팔·손 겉면이 엇갈려 이어진다.
  blender -b --factory-startup -P blender/rig/m3_wrist.py
입력: Documents/MineTunnel/blender/miner_v5_stage20_m3_glow.blend (안 고친다) · 출력: miner_v5_stage21_m3_wrist.blend → m3_props.py
사보타주: SABOTAGE=nowrist(안 함) -> 검사 FAIL"""
import bpy, bmesh, os, sys, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage20_m3_glow.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage21_m3_wrist.blend"))
SABOTAGE = os.environ.get("SABOTAGE", "")
P = "mixamorig:"
CUT, INSET, SEG = 0.12, 0.008, 36
RINGS = ((-CUT, "arm"), (-0.08, "mix"), (-0.035, "wrap"), (-0.015, "wrap2"), (0.01, "end"))

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
# 몸 색 그림 (관 UV 자리 고르기용) — BSDF 색 입력에서 그림 노드까지 거슬러 찾는다 (m2_body.py 가 곱하기 노드를 끼웠다)
_bs = next(n for n in body.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED"); _src = _bs.inputs["Base Color"].links[0].from_socket if _bs.inputs["Base Color"].links else None
while _src is not None and _src.node.type != "TEX_IMAGE":
    _src = next((i for i in _src.node.inputs if i.links), None); _src = _src.links[0].from_socket if _src else None
body_px = None
if _src is not None and _src.node.image is not None:
    _img = _src.node.image; body_px = np.empty(_img.size[0] * _img.size[1] * 4, np.float32); _img.pixels.foreach_get(body_px); body_px = body_px.reshape(_img.size[1], _img.size[0], 4)
    print("몸 색 그림", _img.name, body_px.shape)
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
        gone = [f for f in bm.faces if all((np.array(bw @ v.co)[0] * sx) > abs(fa[0]) and ((np.array(bw @ v.co) - wr) @ u) > -CUT for v in f.verts)]
        donors = []                                                        # (세계 자리, 무게 dict, uv)
        for f in gone:
            for lp in f.loops:
                donors.append((np.array(bw @ lp.vert.co), dict(lp.vert[dl]), tuple(lp[uvl].uv)))
        mat_idx = gone[0].material_index if gone else 0; n_gone = len(gone)
        bmesh.ops.delete(bm, geom=gone, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        dpos = np.array([d_[0] for d_ in donors])
        bwi = bw.inverted()
        # UV: 점마다 가장 가까운 옛 점의 UV 를 빌리면 Meshy 그림 조각이 제각각이라 줄무늬가 된다(09-22) → 관 전체를 관 시작 자리 옛 점의 UV 둘레 작은 네모(그림 몇 텍셀)에 편다 — 그 자리 색(팔 회색)이 고르게 입혀진다
        # 네모 자리 = 지운 팔 면들의 텍셀 색 가운데값에 가장 가까운 옛 점의 UV (가장 가까운 점의 UV 를 그냥 쓰면 어두운 텍셀에 걸려 게임에서 관이 팔보다 검은 띠로 보였다, 09-22)
        if body_px is not None:
            cols = np.array([body_px[int(d_[2][1] % 1 * (body_px.shape[0] - 1)), int(d_[2][0] % 1 * (body_px.shape[1] - 1)), :3] for d_ in donors])
            k0 = int(np.argmin(np.linalg.norm(cols - np.median(cols, axis=0), axis=1)))
        else:
            k0 = int(np.argmin(np.linalg.norm(dpos - (c + u * -CUT), axis=1)))
        uc, vc = donors[k0][2]
        vs = []
        for ri, (t, key) in enumerate(RINGS):
            r = radii[key]; row = []
            for j in range(SEG):
                th = j / SEG * 2 * math.pi; pw = c + u * t + (e1 * math.cos(th) + e2 * math.sin(th)) * r[j]
                v = bm.verts.new(bwi @ Vector(pw)); k = int(np.argmin(np.linalg.norm(dpos - pw, axis=1)))
                for g, w in donors[k][1].items():
                    v[dl][g] = w
                row.append((v, (uc + (j / SEG - 0.5) * 0.004, vc + (ri / len(RINGS) - 0.5) * 0.004)))
            vs.append(row)
        for a_, b_ in zip(vs[:-1], vs[1:]):
            for j in range(SEG):
                q = [a_[j], a_[(j + 1) % SEG], b_[(j + 1) % SEG], b_[j]]
                f = bm.faces.new([x[0] for x in q]); f.material_index = mat_idx; f.smooth = True
                for lp, x in zip(f.loops, q):
                    lp[uvl].uv = x[1]
                if (np.array(bw.to_3x3() @ f.normal) @ ((np.array(bw @ f.calc_center_median()) - (c + u * ((np.array(bw @ f.calc_center_median()) - c) @ u))))) < 0:
                    f.normal_flip()                                        # 겉면이 밖을 보게
        bm.to_mesh(body.data); bm.free(); body.data.update()
        print("%s 손목: 팔 끝 면 %d 지우고 소매 관 %d 점 %d 면 새로" % (side, n_gone, SEG * len(RINGS), SEG * (len(RINGS) - 1)))
    body_tree = tree_of(body)
    b_end = prof(body_tree, 0.006, 0); h_end = prof(hand_tree, 0.006, 0)
    b_wrap = prof(body_tree, -0.03, 0); h_wrap = prof(hand_tree, -0.03, 0)
    b_cut = prof(body_tree, -CUT - 0.02, 0); b_cut2 = prof(body_tree, -CUT + 0.005, 0)
    inside = float(np.mean(b_end <= h_end - 0.002)); outside = float(np.mean(b_wrap >= h_wrap)); step = float(np.abs(b_cut2 - b_cut).max())
    check(inside >= 0.85 and outside >= 0.8 and step <= 0.012,
          "%s 손목: 관 끝이 손 겉 안쪽인 칸 %.0f %% (≥ 85) · 손 시작(t −3 cm)을 관이 감싸는 칸 %.0f %% (≥ 80) · 관 시작에서 팔과의 턱 최대 %.1f mm (≤ 12) — 팔 %.3f → 관 끝 %.3f, 손 %.3f m" %
          (side, inside * 100, outside * 100, step * 1000, float(r_arm.mean()), float(b_end.mean()), float(h_end.mean())))
arm.data.pose_position = "POSE"
if fails:
    sys.exit("m3_wrist FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_wrist ALL PASS →", OUT)
