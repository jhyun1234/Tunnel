"""3D-P 차례 2 손질 — Meshy 몸의 모양 문제를 Blender 로 고친다(0 크레딧, 사용자 09-29 "Blender 와 Meshy 로 각각 고쳐라").
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender/rig/player_meshy_fix.py -- <이름> [<그림 이름>]
  예) -- player1                → 모양만 고침(그림은 원래 것)        → P2_player1_fix_*.png
      -- player1 player1_retex2 → 고친 모양 + Meshy 가 다시 입힌 그림 → P2_player1_fix_retex2_*.png
몸의 점은 옮기지 않는다 — 판정 ⑦(09-29) 에서 점을 옮긴 손질(머리 밀어 넣기 · 목깃 밀어 넣기 · 소매 가늘게)이 뒤통수 · 목 · 어깨를 찢었다.
사용자 09-29 "1+3 으로 가고 팔 굵기는 그대로":
  ⓪ 안전모를 Meshy 머리 가운데로(판정 ⑤) — 이 자리에선 머리카락이 안전모 겉 밖으로 안 나온다(머리 밀어 넣기는 뺌)
  ① 목 깁스: 코드 목수건(밑그림 높이 그대로)에 완전히 가려진 몸 면은 지우고, 밖으로 보이는 목깃 덩어리는 작업복 깃 색으로(②)
     (목수건을 덩어리만큼 키우면 목 깁스처럼 보여 사용자 09-29 "가")
  ② 그림(다시 입힌 그림을 줄 때만): 장갑 · 손목 색 되살림 · 목 둘레 빨강 · 흰 얼룩만 칠함(얼룩 아닌 칸은 그대로) · 목깃 덩어리는 작업복 깃 색 ·
     목덜미(두 귀 사이) 머리 뭉치 윗면은 머리카락 색
자리 값(목 · 안전모)은 밑그림 장면의 scene["player_info"] — 소품이 맞는 같은 틀.
검사(FAIL 이면 종료 1): 머리카락이 안전모 겉 안 · 찢어짐 없음(뒤집힌 면 · 새로 뚫은 면 쌍 0) · 챙 앞뒤 균형 · 얼룩 · 목깃이 옷 색
사보타주: SABOTAGE=helmetfwd(안전모를 옛 자리에) → 챙 균형 · 머리카락 FAIL · push(옛 ② 목깃을 목 속으로 밀기) → 찢어짐 FAIL ·
          norepaint(그림을 안 칠함, 그림 판에서만) → 얼룩 · 목깃 색 FAIL
출력: build/player/player_<이름>_fix.blend · MineTunnel/mesh/meshy_<이름>_fix.glb(고친 몸, 원래 그림) · 그림 P2_*_fix*"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "blender", "props"))
import player_blockout as B
import player_meshy_views as V
import make_player_props as P

args = sys.argv[sys.argv.index("--") + 1:]; name = args[0]; tex = args[1] if len(args) > 1 else None
SAB = os.environ.get("SABOTAGE", "")

meshes = V.load(name, gear=True)
info = dict(bpy.context.scene["player_info"])
body = meshes[0]; me = body.data
body.data.transform(body.matrix_world); body.matrix_world = Matrix.Identity(4)     # 세계 좌표로 굳힌다(이름 · UV 그대로)
co0 = np.array([v.co[:] for v in me.vertices]); co = co0.copy(); n = len(co)
e = np.array([ed.vertices[:] for ed in me.edges]); deg = np.maximum(np.bincount(e.ravel(), minlength=n), 1).astype(float)

# 점마다 원래 그림 색(UV 로 base color 를 읽는다) — 흰 목수건 · 살색 목깃을 가르는 데 쓴다
img = next(i for i in bpy.data.images if i.size[0] == 4096 and "normal" not in i.name.lower())
W_, H_ = img.size; px = np.empty(W_ * H_ * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(H_, W_, 4)
uv = np.zeros((n, 2)); cnt = np.zeros(n)
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index; uv[vi] += me.uv_layers[0].data[li].uv; cnt[vi] += 1
uv /= np.maximum(cnt, 1)[:, None]
col = px[np.clip(((uv[:, 1] % 1) * H_).astype(int), 0, H_ - 1), np.clip(((uv[:, 0] % 1) * W_).astype(int), 0, W_ - 1), :3]
lum = col.mean(axis=1)
white = lum > 0.55
skin = (col[:, 0] > col[:, 2] + 0.06) & (lum > 0.25) & (col[:, 0] > 0.3) & (col[:, 1] > 0.18)   # 살색(빨간 고무장갑은 녹색이 낮아 빠진다)

rim, hcx, hcy0 = info["rim_z"], info["helmet_cx"], info["helmet_cy"]
# ⓪ 안전모를 Meshy 머리 가운데로(사용자 09-29 "안전모가 머리에서 좀 앞으로 튀어나와 있다 — 뒤로"): 밑그림 머리에 맞춘 자리는
#    Meshy 머리보다 3 cm 앞이었다. 챙 2~4.5 cm 아래 머리 단면(손질 전)의 앞 끝 · 뒤 끝 가운데로 옮기고 램프 줄을 다시 잇는다
sl = co0[(co0[:, 2] > rim - 0.045) & (co0[:, 2] < rim - 0.015) & (np.abs(co0[:, 0] - hcx) < 0.02) & (np.hypot(co0[:, 0] - hcx, co0[:, 1] - hcy0) < 0.2)]
head_front, head_back = float(sl[:, 1].min()), float(sl[:, 1].max())
hcy = hcy0 if SAB == "helmetfwd" else (head_front + head_back) / 2
helmet = bpy.data.objects["Helmet"]; helmet.matrix_world = Matrix.Translation((hcx, hcy, rim)) @ Matrix.Translation(-helmet.matrix_world.translation) @ helmet.matrix_world
info["helmet_cy"] = hcy; bpy.context.scene["player_info"] = info
print(f"INFO 안전모 가운데 y {hcy0:+.3f} → {hcy:+.3f} (머리 앞 {head_front:+.3f} · 뒤 {head_back:+.3f})")
x, y, z = co[:, 0], co[:, 1], co[:, 2]
head = (z > rim - 0.20) & (np.hypot(x - hcx, y - hcy) < 0.2)

nb = info["neck_back_z"]
# 목 가운데 · 반지름: 목깃 위(턱 아래) 살색 점들의 고리로 잰다(밑그림 값은 목 앞쪽으로 치우쳐 있다)
band = (z > nb + 0.02) & (z < nb + 0.06) & skin & (np.hypot(x - hcx, y - hcy0) < 0.11)   # 목 찾기는 안전모를 옮기기 전 기준(옮긴 기준이면 목깃을 너무 많이 잡는다)
nk_c = co[band, :2].mean(axis=0)
neck_r = float(np.median(np.hypot(co[band, 0] - nk_c[0], co[band, 1] - nk_c[1])))
print(f"INFO 목 가운데 ({nk_c[0]:+.3f}, {nk_c[1]:+.3f}) · 반지름 {neck_r*100:.1f} cm ({band.sum()} 점) · 밑그림 목 가운데 y {info['neck_cy']:+.3f}")
rn = np.hypot(x - nk_c[0], y - nk_c[1])
neck_zone = (z > nb - 0.08) & (z < nb + 0.03) & (rn < 0.105)                     # 턱(목 뒤 + 3 cm 위) · 어깨는 빼고 목깃만
lump = neck_zone & (white | skin) & (rn > neck_r + 0.004)


def ring_z(p, zb, zf):
    """목수건 가운데 줄 높이(B.towel_ring 과 같은 식 — 앞 zf 에서 뒤 zb 로) — 점 p 가 목 가운데에서 놓인 각도에서."""
    t = np.arctan2(p[:, 0] - nk_c[0], -(p[:, 1] - nk_c[1]))
    return zf + (zb - zf) * (1 - np.cos(t)) / 2


if SAB == "push":   # 옛 ②(판정 ⑦ 에서 찢어짐): 색으로 고른 목깃 점만 목 속으로 — 찢어짐 검사가 잡는지 본다
    tgt = neck_r - 0.008
    s_ = np.where(lump & (rn > tgt), tgt / np.maximum(rn, 1e-6), 1.0)
    co[:, 0] = nk_c[0] + (co[:, 0] - nk_c[0]) * s_; co[:, 1] = nk_c[1] + (co[:, 1] - nk_c[1]) * s_
for v, c in zip(me.vertices, co): v.co = c
me.update()

# ① 목수건(밑그림과 같은 높이 4.4 cm). 목깃 덩어리는 가운데 줄에서 위아래로 더 퍼져 있지만(5~95 %) 다 덮게 키우면 목 깁스처럼 보인다
#    (09-29 7.2 cm 로 해 봄 → 사용자 "가": 목수건 그대로, 밖으로 보이는 덩어리는 ②⑥ 에서 작업복 깃 색)
dz = z - ring_z(co, nb, nb - 0.055)
lo, hi = np.percentile(dz[lump], [5, 95])
bvh = BVHTree.FromPolygons([tuple(c) for c in co], [tuple(p.vertices) for p in me.polygons])
tw = B.towel_ring(bvh, float(nk_c[0]), float(nk_c[1]), nb, nb - 0.055)
tw.name = "Towel_Fix"
print(f"INFO 목깃 덩어리 {lump.sum()} 점 — 목수건 가운데 줄에서 {lo*100:+.1f} ~ {hi*100:+.1f} cm (목수건은 ±2.2 cm)")
old_cord = bpy.data.objects.get("Lamp_Cord")                                        # 안전모를 옮겼으니 줄을 다시 잇는다
if old_cord: bpy.data.objects.remove(old_cord)
bpy.context.view_layer.update()
B.lamp_cord(helmet.matrix_world, bvh, nb, info["belt_z"], info["cord_out"]).name = "Lamp_Cord"

# 목수건에 가려진 점: 목 축에서 밖으로 쏜 선(수평 · 위 30° · 아래 30°)이 모두 목수건에 닿는다
dg = bpy.context.evaluated_depsgraph_get(); tw_e = tw.evaluated_get(dg); tme = tw_e.to_mesh()
tbvh = BVHTree.FromPolygons([tuple(tw_e.matrix_world @ v.co) for v in tme.vertices], [tuple(p.vertices) for p in tme.polygons]); tw_e.to_mesh_clear()


def covered(i):
    h = Vector((co[i, 0] - nk_c[0], co[i, 1] - nk_c[1], 0)).normalized(); p = Vector(co[i])
    return all(tbvh.ray_cast(p + d * 0.001, d, 0.2)[0] is not None
               for d in (h, (h + Vector((0, 0, 0.577))).normalized(), (h - Vector((0, 0, 0.577))).normalized()))


near_tw = (rn < 0.16) & (np.abs(dz) < 0.042)
cov = np.zeros(n, bool); cov[near_tw] = [covered(i) for i in np.where(near_tw)[0]]
hide_f = np.array([cov[list(p_.vertices)].all() for p_ in me.polygons])            # 지울 면(① — 저장 앞에서 지운다)

# ── 검사 ──
fails = []
qo = ((x - hcx) / (P.SHELL_W / 2)) ** 2 + ((y - hcy) / (P.SHELL_L / 2)) ** 2 + ((z - rim) / P.DOME_H) ** 2   # 안전모 껍데기 겉
rr = ((x - hcx) / (P.HELMET_W / 2)) ** 2 + ((y - hcy) / (P.HELMET_L / 2)) ** 2                               # 챙 발자국
up = head & (z > rim); bl = head & (z <= rim) & (z > rim - 0.06) & (y > hcy)
B.check(fails, "fix_hair_in_helmet", qo[up].max() < 1 and rr[bl].max() < 1,
        f"챙 위 머리가 안전모 껍데기 겉 안 — 가장 큰 값 {qo[up].max():.2f} (< 1) · 챙 아래 6 cm 뒤통수가 챙 발자국 안 — {rr[bl].max():.2f} (< 1)")
tri = np.array([p_.vertices[:3] for p_ in me.polygons])                              # Meshy 면은 모두 삼각형


def normals(c): return np.cross(c[tri[:, 1]] - c[tri[:, 0]], c[tri[:, 2]] - c[tri[:, 0]])


flipped = int(((normals(co0) * normals(co)).sum(axis=1) < 0).sum())   # 비교는 늘 Meshy 원래 모양과
pl = [tuple(p_.vertices) for p_ in me.polygons]


def crossings(c):
    t_ = BVHTree.FromPolygons([tuple(v) for v in c], pl)
    return {(a, b) for a, b in t_.overlap(t_) if a < b and not (set(pl[a]) & set(pl[b]))}


new_x = len(crossings(co) - crossings(co0)) if np.abs(co - co0).max() > 0 else 0
B.check(fails, "fix_no_tear", flipped == 0 and new_x == 0,
        f"Meshy 원래 모양보다 뒤집힌 면 {flipped} · 새로 서로 뚫은 면 쌍 {new_x} (둘 다 0 — 판정 ⑦ 판은 뒤집힌 면 112) · 옮긴 점 {(np.linalg.norm(co - co0, axis=1) > 1e-6).sum()}")
fo = (head_front - (hcy - P.HELMET_L / 2)); bo = ((hcy + P.HELMET_L / 2) - head_back)
B.check(fails, "fix_helmet_balanced", abs(fo - bo) < 0.015,
        f"챙이 이마 앞으로 {fo*100:.1f} cm · 뒤통수 뒤로 {bo*100:.1f} cm (차이 < 1.5 — 옮기기 전 앞 {(head_front - (hcy0 - P.HELMET_L/2))*100:.1f} · 뒤 {((hcy0 + P.HELMET_L/2) - head_back)*100:.1f})")

# ── 저장 · 그림 ── (사보타주 때는 결과 파일을 덮어쓰지 않는다)
if SAB and SAB != "norepaint":
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails)); sys.exit(1 if fails else 0)
tag = f"{name}_fix"


def edit_bm(fn):
    bm = bmesh.new(); bm.from_mesh(me); fn(bm); bm.to_mesh(me); bm.free(); me.update()


# ① 목수건에 완전히 가려진 면을 지운다(점은 그림 칠하기가 점 번호를 쓰니 저장 앞에서 지운다)
edit_bm(lambda bm: (bm.faces.ensure_lookup_table(), bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(hide_f)[0]], context="FACES_ONLY")))
print(f"INFO 목수건에 가려진 면 {int(hide_f.sum())} 개를 지움 (남은 면 {len(me.polygons)})")
if tex:   # 같은 UV — Meshy 가 다시 입힌 그림(재질)으로 바꿔 씌운다
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=V.src_of(tex))
    donor = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    mat = donor.data.materials[0].copy(); me.materials.clear(); me.materials.append(mat)
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o)
    tag = f"{name}_fix_{tex.replace(name + '_', '')}"
    # 다시 입힌 그림은 장갑 · 손목까지 검게 칠했다 → 원래 그림의 적갈색 고무 · 흰 면(사용자 09-27 근로장갑)을 되살리고 새 그림의 때를 얹는다
    bsdf = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    tex_node = bsdf.inputs["Base Color"].links[0].from_node
    rt = tex_node.image; rw, rh = rt.size
    rp = np.empty(rw * rh * 4, dtype=np.float32); rt.pixels.foreach_get(rp); rp = rp.reshape(rh, rw, 4)
    op_ = px if (rw, rh) == (W_, H_) else None
    if op_ is not None:
        glove = (op_[..., 0] > 0.18) & (op_[..., 0] > 1.8 * op_[..., 1]) & (op_[..., 0] > 1.8 * op_[..., 2])
        cotton = (op_[..., :3].mean(axis=-1) > 0.6) & ((op_[..., :3].max(axis=-1) - op_[..., :3].min(axis=-1)) < 0.10)   # 흰 면 = 밝고 색이 거의 없다(살색은 빠진다)
        keep = glove | cotton
        grime = np.clip(rp[..., :3].mean(axis=-1) / 0.30, 0, 1)[..., None]
        out = rp.copy(); out[..., :3] = np.where(keep[..., None], op_[..., :3] * (0.55 + 0.45 * grime), rp[..., :3])
        # ⑤ 목 옆 얼룩(사용자 09-29 "목 옆 얼룩 고쳐라"): Meshy 목깃 자리의 빨강 · 흰색 — ① 귀 아래 ~ 목수건 위 목 ② 목 속으로 넣은 목깃 조각(목 살 사이로 비친다)
        #    은 목 살색으로, ③ 뒤통수 아래(두 귀 사이, 안전모 밑) 목깃 윗부분의 얼룩은 머리카락 색으로. 밝고 어두운 결(때)은 남기고 색만 바꾼다.
        #    구역 안에서도 얼룩 칸(+ 둘레 2 칸)만 칠한다 — 구역 전체를 칠했더니 턱 옆 · 볼 · 귀 뒤에 조각난 얼룩이 생겼다(판정 ⑦ 뒤 09-29)
        # 면(삼각형) 가운데 자리로 구역을 나눈다(09-29 두 번 해 보니 얼룩은 목 가운데에서 11~13 cm, 목수건 위 ~ 귀 높이 뒤통수 아래에 많았다)
        me.calc_loop_triangles(); uvl = me.uv_layers[0].data
        fc = np.array([co[list(p_.vertices)].mean(axis=0) for p_ in me.polygons])
        rn_c = np.hypot(fc[:, 0] - nk_c[0], fc[:, 1] - nk_c[1]); dy = fc[:, 1] - nk_c[1]; ax = np.abs(fc[:, 0] - hcx); fz = fc[:, 2]
        lump_f = np.array([lump[list(p_.vertices)].any() for p_ in me.polygons])
        front_face = (dy < -0.04) & (fz > nb + 0.02)                                   # 얼굴(방독면 속) — 입술 · 눈은 그대로
        ear = (ax > 0.062) & (fz > nb + 0.04) & (np.abs(dy) < 0.06)
        near = rn_c < 0.17
        hair_f = near & (fz > nb + 0.03) & (fz < rim) & (dy > 0.03) & (ax < 0.05)        # ③ 뒤통수 아래 두 귀 사이(목덜미 머리 뭉치 윗면의 살색 조각) → 머리카락 색 — 귀 뒤까지 칠하면 살에 검은 조각이 흩어진다
        neck_f = (near & (fz > nb - 0.06) & (fz < nb + 0.075) & ~front_face & ~ear & ~hair_f) | lump_f   # ①② 목 → 살색
        low_f = near & (fz > nb - 0.14) & (fz <= nb - 0.06) & ~neck_f                   # ④ 목수건 아래 옷깃 → 빨강 · 흰 칸만 옷 색
        def raster(fsel, grow=True):
            m_ = np.zeros((rh, rw), bool)
            for lt in me.loop_triangles:
                if not fsel[lt.polygon_index]: continue
                t3 = np.array([uvl[l].uv[:] for l in lt.loops]) * [rw, rh]
                x0, y0 = np.floor(t3.min(axis=0)).astype(int); x1, y1 = np.ceil(t3.max(axis=0)).astype(int)
                xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, rw - 1) + 1), np.arange(max(y0, 0), min(y1, rh - 1) + 1))
                if xs.size == 0: continue
                (ax_, ay_), (bx_, by_), (cx_, cy_) = t3; den = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
                if abs(den) < 1e-9: continue
                px_, py_ = xs + 0.5, ys + 0.5
                l1 = ((by_ - cy_) * (px_ - cx_) + (cx_ - bx_) * (py_ - cy_)) / den; l2 = ((cy_ - ay_) * (px_ - cx_) + (ax_ - cx_) * (py_ - cy_)) / den
                ins = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
                m_[ys[ins], xs[ins]] = True
            if grow:   # 그림 조각 밖 빈칸으로만 12 칸 넓힌다 — 멀리서 쓰는 흐린 그림(밉맵)이 옆 칸 색을 섞어 와 가장자리에 빨간 줄이 났다(09-29)
                for _ in range(12):
                    m_ = m_ | ((np.roll(m_, 1, 0) | np.roll(m_, -1, 0) | np.roll(m_, 1, 1) | np.roll(m_, -1, 1)) & pad)
            return m_
        pad = ~raster(np.ones(len(me.polygons), bool), grow=False)                   # 어느 조각에도 안 쓰이는 빈칸
        collar_v = (dz > lo - 0.01) & (dz < hi + 0.008) & (rn > neck_r + 0.006) & (rn < 0.13)   # ⑥ Meshy 목깃 덩어리(색 말고 모양으로 고름) → 작업복 깃 색
        collar_f = np.array([collar_v[list(p_.vertices)].all() for p_ in me.polygons])
        cmask = raster(collar_f, grow=False)
        nmask = raster(neck_f) & ~cmask; hmask = raster(hair_f) & ~nmask & ~cmask; lmask = raster(low_f, grow=False) & ~nmask & ~hmask & ~cmask
        allm = nmask | hmask | lmask
        def is_stain(c3):
            lum_ = c3.mean(axis=1); sat_ = c3.max(axis=1) - c3.min(axis=1)
            return ((c3[:, 0] > 1.55 * c3[:, 1]) & (c3[:, 0] > 0.3)) | ((lum_ > 0.6) & (sat_ < 0.15))
        def stains(img): return float(is_stain(img[allm][:, :3]).mean())
        st0 = stains(out)
        def repaint(m_, bad, base, ref):   # m_ 구역에서 bad 칸과 그 둘레 2 칸만
            sel = np.zeros_like(m_); sel[m_] = bad(out[m_][:, :3])
            for _ in range(2): sel = sel | ((np.roll(sel, 1, 0) | np.roll(sel, -1, 0) | np.roll(sel, 1, 1) | np.roll(sel, -1, 1)) & m_)
            c3 = out[sel][:, :3]; lum_ = c3.mean(axis=1)
            out[sel, :3] = base[None, :] * np.clip(lum_ / max(ref, 1e-3), 0.75, 1.15)[:, None] * 0.92
        c3 = out[nmask][:, :3]; lum_ = c3.mean(axis=1)
        skinlike = (c3[:, 0] > c3[:, 1]) & (c3[:, 1] > c3[:, 2]) & (lum_ > 0.2) & (lum_ < 0.7) & (c3[:, 0] < 1.45 * c3[:, 1])
        base = np.median(c3[skinlike], axis=0) * 0.85 if skinlike.sum() > 100 else np.array([0.40, 0.30, 0.23])   # 목은 그늘 · 때로 얼굴보다 조금 어둡게(어림)
        h3 = out[hmask][:, :3]; hl = h3.mean(axis=1)
        hbase = np.median(h3[hl < 0.15], axis=0) if (hl < 0.15).sum() > 100 else np.array([0.05, 0.045, 0.04])
        l3 = out[lmask][:, :3]; ll = l3.mean(axis=1)
        jbase = np.median(l3[ll < 0.2], axis=0) if (ll < 0.2).sum() > 100 else np.array([0.08, 0.08, 0.08])
        if SAB != "norepaint":
            repaint(nmask, is_stain, base, float(np.median(lum_[skinlike])) if skinlike.sum() > 100 else 0.35)
            repaint(hmask, lambda c3: np.ones(len(c3), bool), hbase, float(np.median(hl[hl < 0.15])) if (hl < 0.15).sum() > 100 else 0.05)
            lst = np.zeros_like(lmask); lst[lmask] = is_stain(out[lmask][:, :3])
            out[lst, :3] = jbase[None, :]
            c3_ = out[cmask][:, :3]; lc = c3_.mean(axis=1)                              # ⑥ 목깃은 통째로 옷 색(밝고 어두운 결은 남긴다)
            out[cmask, :3] = jbase[None, :] * np.clip(lc / max(float(np.median(lc)), 1e-3), 0.7, 1.3)[:, None]
        st1 = stains(out)
        B.check(fails, "fix_neck_stain", st1 < 0.01,
                f"목 · 뒤통수 아래 · 옷깃 그림 칸 {allm.sum()} 개 — 빨강 · 흰 얼룩 {st0*100:.1f} → {st1*100:.1f} % (< 1 %) · 칠한 살색 {tuple(round(float(v), 2) for v in base)} · 옷 색 {tuple(round(float(v), 2) for v in jbase)}")
        cc = out[cmask][:, :3]
        off = float(((cc.mean(axis=1) > 0.3) | (cc[:, 0] > 1.3 * cc[:, 2] + 0.03)).mean())
        B.check(fails, "fix_collar_color", off < 0.02,
                f"목깃 덩어리 그림 칸 {cmask.sum()} 개 중 옷 색이 아닌 것(밝거나 살색 · 빨강) {off*100:.1f} % (< 2 %)")
        if SAB == "norepaint":
            print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails)); sys.exit(1 if fails else 0)
        ni = bpy.data.images.new("player_fix_retex_base", rw, rh, alpha=True); ni.pixels.foreach_set(out.ravel())
        ni.filepath_raw = os.path.join(V.OUT, f"player_{tag}_base.png"); ni.file_format = "PNG"; ni.save(); tex_node.image = ni
        print(f"INFO 장갑 · 손목 색 되살림: 고무 {glove.mean()*100:.2f} % · 면(흰색) {cotton.mean()*100:.2f} % 의 그림 칸")
    tm = bpy.data.materials.new("PB_towel_dirty"); tm.use_nodes = True                       # 목수건도 새 그림처럼 때 묻은 회색
    tb = next(nd for nd in tm.node_tree.nodes if nd.type == "BSDF_PRINCIPLED"); tb.inputs["Base Color"].default_value = (0.36, 0.35, 0.32, 1)
    tb.inputs["Roughness"].default_value = 0.95
    for o in bpy.data.objects:
        if o.name.startswith("Towel_Fix"): o.data.materials.clear(); o.data.materials.append(tm)
edit_bm(lambda bm: bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS"))   # 지운 면에만 쓰이던 점
if not tex:
    for o in bpy.data.objects: o.select_set(o == body)
    bpy.context.view_layer.objects.active = body
    bpy.ops.export_scene.gltf(filepath=V.src_of(f"{name}_fix"), export_format="GLB", use_selection=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V.OUT, f"player_{tag}.blend"))
if os.environ.get("RENDER", "1") != "0":
    V.shoot_set(tag + "_소품", [body], close=False)
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith(V.GEAR_PREFIX): o.hide_render = True
    V.shoot_set(tag, [body], close=True)
print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
sys.exit(1 if fails else 0)
