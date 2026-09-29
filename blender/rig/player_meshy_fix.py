"""3D-P 차례 2 손질 — Meshy 몸의 모양 문제를 Blender 로 고친다(0 크레딧, 사용자 09-29 "Blender 와 Meshy 로 각각 고쳐라").
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender/rig/player_meshy_fix.py -- <이름> [<그림 이름>]
  예) -- player1                → 모양만 고침(그림은 원래 것)        → P2_player1_fix_*.png
      -- player1 player1_retex1 → 고친 모양 + Meshy 가 다시 입힌 그림 → P2_player1_fix_retex1_*.png
고치는 것(점을 옮기기만 한다 — 점 순서 · 그림 좌표(UV)는 그대로라 다시 입힌 그림을 바로 씌운다):
  ① 뒷머리: 안전모 안쪽(껍데기 4 mm + 틈 8 mm) 밖으로 나온 머리 · 챙 아래 뒤로 불룩한 머리를 안쪽으로
  ② 목 깁스: 목 둘레의 흰색 · 살색 덩어리(원래 그림 색으로 가림)를 목에 붙게 안으로 당기고, 코드 목수건을 두른다
  ③ 굵은 팔: 검은 소매만(원래 그림 색으로 가림) 팔 축 쪽으로 × 0.86 (※ 어림)
자리 값(목 · 안전모)은 밑그림 장면의 scene["player_info"] — 소품이 맞는 같은 틀.
검사(FAIL 이면 종료 1): 머리가 안전모 안쪽에 들어감 · 목 둘레 덩어리가 목에서 2.5 cm 안 · 소매 굵기가 줄었나 · 점 수 그대로
사보타주: SABOTAGE=nofix(아무것도 안 고침) → 세 검사 FAIL · helmetfwd(안전모를 옛 자리에 둠) → 챙 균형 FAIL · norepaint(목 옆 · 뒤통수 얼룩을 안 칠함, 그림 판에서만) → 얼룩 두 검사 FAIL
출력: build/player/player_<이름>_fix.blend · MineTunnel/mesh/meshy_<이름>_fix.glb(고친 몸, 원래 그림) · 그림 P2_*_fix*"""
import bpy, os, sys, math
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
ARM_SLIM = 0.86          # ※ 소매 굵기 배수(어림)
GAP = 0.012              # 안전모 껍데기 4 mm + 틈 8 mm

meshes = V.load(name, gear=True)
info = dict(bpy.context.scene["player_info"])
body = meshes[0]; me = body.data
body.data.transform(body.matrix_world); body.matrix_world = Matrix.Identity(4)     # 세계 좌표로 굳힌다(이름 · UV 그대로)
co0 = np.array([v.co[:] for v in me.vertices]); co = co0.copy(); n = len(co)
e = np.array([ed.vertices[:] for ed in me.edges]); deg = np.maximum(np.bincount(e.ravel(), minlength=n), 1).astype(float)

# 점마다 원래 그림 색(UV 로 base color 를 읽는다) — 흰 목수건 · 살색 목깃 · 검은 소매를 가르는 데 쓴다
img = next(i for i in bpy.data.images if i.size[0] == 4096 and "normal" not in i.name.lower())
W_, H_ = img.size; px = np.empty(W_ * H_ * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(H_, W_, 4)
uv = np.zeros((n, 2)); cnt = np.zeros(n)
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index; uv[vi] += me.uv_layers[0].data[li].uv; cnt[vi] += 1
uv /= np.maximum(cnt, 1)[:, None]
col = px[np.clip(((uv[:, 1] % 1) * H_).astype(int), 0, H_ - 1), np.clip(((uv[:, 0] % 1) * W_).astype(int), 0, W_ - 1), :3]
lum = col.mean(axis=1); sat = col.max(axis=1) - col.min(axis=1)
white = lum > 0.55
skin = (col[:, 0] > col[:, 2] + 0.06) & (lum > 0.25) & (col[:, 0] > 0.3) & (col[:, 1] > 0.18)   # 살색(빨간 고무장갑은 녹색이 낮아 빠진다)
dark = lum < 0.12

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
a_, b_, c_ = P.SHELL_W / 2 - GAP, P.SHELL_L / 2 - GAP, P.DOME_H - GAP


def helmet_q(p):
    return ((p[:, 0] - hcx) / a_) ** 2 + ((p[:, 1] - hcy) / b_) ** 2 + ((p[:, 2] - rim) / c_) ** 2


def blur_vec(v, mask, iters):
    for _ in range(iters):
        acc = np.zeros_like(v); np.add.at(acc, e[:, 0], v[e[:, 1]]); np.add.at(acc, e[:, 1], v[e[:, 0]])
        v = np.where(mask[:, None], 0.5 * v + 0.5 * acc / deg[:, None], v)
    return v


nb = info["neck_back_z"]
# 목 가운데 · 반지름: 목깃 위(턱 아래) 살색 점들의 고리로 잰다(밑그림 값은 목 앞쪽으로 치우쳐 있다)
band = (z > nb + 0.02) & (z < nb + 0.06) & skin & (np.hypot(x - hcx, y - hcy0) < 0.11)   # 목 찾기는 안전모를 옮기기 전 기준(옮긴 기준이면 목깃을 너무 많이 잡아 목수건이 울퉁불퉁)
nk_c = co[band, :2].mean(axis=0)
neck_r = float(np.median(np.hypot(co[band, 0] - nk_c[0], co[band, 1] - nk_c[1])))
print(f"INFO 목 가운데 ({nk_c[0]:+.3f}, {nk_c[1]:+.3f}) · 반지름 {neck_r*100:.1f} cm ({band.sum()} 점) · 밑그림 목 가운데 y {info['neck_cy']:+.3f}")
rn = np.hypot(x - nk_c[0], y - nk_c[1])
neck_zone = (z > nb - 0.08) & (z < nb + 0.03) & (rn < 0.105)                     # 턱(목 뒤 + 3 cm 위) · 어깨는 빼고 목깃만
lump = neck_zone & (white | skin) & (rn > neck_r + 0.004)
arm = {}
for sd in (-1, 1):
    sel = (np.sign(x) == sd) & (np.abs(x) > 0.24) & (z > 0.9) & (z < 1.55)
    pts = co[sel & (np.abs(x) < 0.5)]; c = pts.mean(axis=0); d = np.linalg.svd(pts - c)[2][0]
    if d[0] * sd < 0: d = -d
    arm[sd] = (sel, c, d)

if SAB != "nofix":
    # ① 머리: 챙 위는 안전모 안쪽 면으로, 챙 아래 뒤쪽은 안전모 발자국(챙 안쪽 타원) 안으로
    up = head & (z > rim - 0.005)
    q = helmet_q(co); out = up & (q > 1)
    co[out] = np.array([hcx, hcy, rim]) + (co[out] - np.array([hcx, hcy, rim])) / np.sqrt(q[out])[:, None]
    below = head & (z <= rim - 0.005) & (y > hcy)                                   # 챙 아래 뒤쪽(얼굴은 안 건드림)
    rr = ((co[:, 0] - hcx) / a_) ** 2 + ((co[:, 1] - hcy) / b_) ** 2
    t = np.clip((rim - co[:, 2]) / 0.06, 0, 1)                                         # 챙에서 6 cm 내려가며 제한을 푼다
    lim = (1.0 + 0.6 * t) ** 2
    fix = below & (rr > lim) & (co[:, 2] > rim - 0.06)
    co[fix, :2] = np.array([hcx, hcy]) + (co[fix, :2] - np.array([hcx, hcy])) * np.sqrt(lim[fix] / rr[fix])[:, None]
    # ② 목 깁스: 목깃 흰색 · 살색 덩어리를 목 속(반지름 − 8 mm)으로 넣어 숨기고, 이음매는 코드 목수건이 덮는다
    tgt = neck_r - 0.008
    s_ = np.where(lump & (rn > tgt), tgt / np.maximum(rn, 1e-6), 1.0)
    co[:, 0] = nk_c[0] + (co[:, 0] - nk_c[0]) * s_; co[:, 1] = nk_c[1] + (co[:, 1] - nk_c[1]) * s_
    # ③ 굵은 팔: 어깨(|x| 0.20→0.28 에서 서서히) → 손목 면 소매 3 cm 앞(→ 0)까지 팔 축 쪽으로. 색으로 점을 고르면 찢어진다 — 색은 손목 자리만 찾는다
    for sd, (sel, c, d) in arm.items():
        tt_all = (co - c) @ d
        cuff_t = float(np.percentile(tt_all[sel & white], 5)) if (sel & white).sum() > 20 else float(tt_all[sel].max())
        w = np.clip((np.abs(co[:, 0]) - 0.20) / 0.08, 0, 1) * np.clip((cuff_t - 0.01 - tt_all) / 0.04, 0, 1) * (np.sign(co[:, 0]) == sd) * (co[:, 2] > 0.9)
        foot = c + tt_all[:, None] * d
        co += ((ARM_SLIM - 1) * w)[:, None] * (co - foot)
    moved = np.linalg.norm(co - co0, axis=1) > 1e-5
    ring_ = moved.copy()
    for _ in range(3):                                                                # 옮긴 곳 둘레까지 고르게
        acc = np.zeros(n); np.add.at(acc, e[:, 0], ring_[e[:, 1]]); np.add.at(acc, e[:, 1], ring_[e[:, 0]]); ring_ = ring_ | (acc > 0)
    co = blur_vec(co, ring_ & ~moved, 3)
    q = helmet_q(co); out = head & (co[:, 2] > rim - 0.005) & (q > 1)                 # 펴기가 되민 머리를 한 번 더 안쪽 면에
    co[out] = np.array([hcx, hcy, rim]) + (co[out] - np.array([hcx, hcy, rim])) / np.sqrt(q[out])[:, None]

for v, c in zip(me.vertices, co): v.co = c
me.update()

# 코드 목수건(밑그림과 같은 모양 · 자리)을 고친 몸 겉에 두른다
bvh = BVHTree.FromPolygons([tuple(c) for c in co], [tuple(p.vertices) for p in me.polygons])
tw = B.towel_ring(bvh, float(nk_c[0]), float(nk_c[1]), nb, nb - 0.055)
tw.name = "Towel_Fix"
old_cord = bpy.data.objects.get("Lamp_Cord")                                        # 안전모를 옮겼으니 줄을 다시 잇는다
if old_cord: bpy.data.objects.remove(old_cord)
bpy.context.view_layer.update()
B.lamp_cord(helmet.matrix_world, bvh, nb, info["belt_z"], info["cord_out"]).name = "Lamp_Cord"

# ── 검사 ──
fails = []
q = helmet_q(co)
B.check(fails, "fix_head_in_helmet", q[head & (co[:, 2] > rim - 0.005)].max() < 1.02,
        f"챙 위 머리가 안전모 안쪽에 — 가장 큰 값 {q[head & (co[:, 2] > rim - 0.005)].max():.2f} (< 1.02, 고치기 전 {helmet_q(co0)[head & (co0[:, 2] > rim - 0.005)].max():.2f})")
rn2 = np.hypot(co[:, 0] - nk_c[0], co[:, 1] - nk_c[1])
B.check(fails, "fix_neck_lump", (rn2[lump] - neck_r).max() < 0.025 if lump.any() else True,
        f"목깃 흰색 · 살색 덩어리 {lump.sum()} 점 — 목 겉에서 가장 먼 것 {(rn2[lump] - neck_r).max()*100:.1f} cm (< 2.5, 고치기 전 {(rn[lump] - neck_r).max()*100:.1f}) · 목 반지름 {neck_r*100:.1f} cm")
for sd, (sel, c, d) in arm.items():
    m = sel & dark & (((co0 - c) @ d) < 0.25)                                        # 팔 윗부분 소매로 잰다
    def girth(p):
        tt = (p - c) @ d; return float(np.median(np.linalg.norm((p - c) - tt[:, None] * d, axis=1)))
    g0, g1 = girth(co0[m]), girth(co[m])
    B.check(fails, f"fix_arm_{'R' if sd < 0 else 'L'}", g1 < g0 * 0.9, f"소매 반지름 가운데 {g0*100:.1f} → {g1*100:.1f} cm")
fo = (head_front - (hcy - P.HELMET_L / 2)); bo = ((hcy + P.HELMET_L / 2) - head_back)
B.check(fails, "fix_helmet_balanced", abs(fo - bo) < 0.015,
        f"챙이 이마 앞으로 {fo*100:.1f} cm · 뒤통수 뒤로 {bo*100:.1f} cm (차이 < 1.5 — 옮기기 전 앞 {(head_front - (hcy0 - P.HELMET_L/2))*100:.1f} · 뒤 {((hcy0 + P.HELMET_L/2) - head_back)*100:.1f})")
B.check(fails, "fix_same_vertices", len(me.vertices) == n and len(me.polygons) == 30762, f"점 {len(me.vertices)} · 면 {len(me.polygons)} (그대로여야 다시 입힌 그림이 맞는다)")

# ── 저장 · 그림 ── (사보타주 때는 결과 파일을 덮어쓰지 않는다)
if SAB and SAB != "norepaint":
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails)); sys.exit(1 if fails else 0)
tag = f"{name}_fix"
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
        #    은 목 살색으로, ③ 뒤통수 아래(두 귀 사이, 안전모 밑)에 드러난 살색 조각은 머리카락 색으로. 밝고 어두운 결(때)은 남기고 색만 바꾼다
        # 면(삼각형) 가운데 자리로 구역을 나눈다(09-29 두 번 해 보니 얼룩은 목 가운데에서 11~13 cm, 목수건 위 ~ 귀 높이 뒤통수 아래에 많았다)
        me.calc_loop_triangles(); uvl = me.uv_layers[0].data
        fc = np.array([co[list(p_.vertices)].mean(axis=0) for p_ in me.polygons])
        rn_c = np.hypot(fc[:, 0] - nk_c[0], fc[:, 1] - nk_c[1]); dy = fc[:, 1] - nk_c[1]; ax = np.abs(fc[:, 0] - hcx); fz = fc[:, 2]
        lump_f = np.array([lump[list(p_.vertices)].any() for p_ in me.polygons])
        front_face = (dy < -0.04) & (fz > nb + 0.02)                                   # 얼굴(방독면 속) — 입술 · 눈은 그대로
        ear = (ax > 0.062) & (fz > nb + 0.04) & (np.abs(dy) < 0.06)
        near = rn_c < 0.17
        hair_f = near & (fz > nb + 0.03) & (fz < rim) & (dy > 0.03) & ~ear              # ③ 뒤통수 아래(안전모 밑) → 머리카락 색
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
        nmask = raster(neck_f); hmask = raster(hair_f) & ~nmask; lmask = raster(low_f, grow=False) & ~nmask & ~hmask
        allm = nmask | hmask | lmask
        def is_stain(c3):
            lum_ = c3.mean(axis=1); sat_ = c3.max(axis=1) - c3.min(axis=1)
            return ((c3[:, 0] > 1.55 * c3[:, 1]) & (c3[:, 0] > 0.3)) | ((lum_ > 0.6) & (sat_ < 0.15))
        def stains(img): return float(is_stain(img[allm][:, :3]).mean())
        def bright(img): return float((img[hmask][:, :3].mean(axis=1) > 0.3).mean())
        st0, br0 = stains(out), bright(out)
        def repaint(m_, base, ref):
            c3 = out[m_][:, :3]; lum_ = c3.mean(axis=1)
            out[m_, :3] = base[None, :] * np.clip(lum_ / max(ref, 1e-3), 0.75, 1.15)[:, None] * 0.92
        c3 = out[nmask][:, :3]; lum_ = c3.mean(axis=1)
        skinlike = (c3[:, 0] > c3[:, 1]) & (c3[:, 1] > c3[:, 2]) & (lum_ > 0.2) & (lum_ < 0.7) & (c3[:, 0] < 1.45 * c3[:, 1])
        base = np.median(c3[skinlike], axis=0) * 0.85 if skinlike.sum() > 100 else np.array([0.40, 0.30, 0.23])   # 목은 그늘 · 때로 얼굴보다 조금 어둡게(어림)
        h3 = out[hmask][:, :3]; hl = h3.mean(axis=1)
        hbase = np.median(h3[hl < 0.15], axis=0) if (hl < 0.15).sum() > 100 else np.array([0.05, 0.045, 0.04])
        l3 = out[lmask][:, :3]; ll = l3.mean(axis=1)
        jbase = np.median(l3[ll < 0.2], axis=0) if (ll < 0.2).sum() > 100 else np.array([0.08, 0.08, 0.08])
        if SAB != "norepaint":
            repaint(nmask, base, float(np.median(lum_[skinlike])) if skinlike.sum() > 100 else 0.35)
            repaint(hmask, hbase, float(np.median(hl[hl < 0.15])) if (hl < 0.15).sum() > 100 else 0.05)
            lst = np.zeros_like(lmask); lst[lmask] = is_stain(out[lmask][:, :3])
            out[lst, :3] = jbase[None, :]
        st1, br1 = stains(out), bright(out)
        B.check(fails, "fix_neck_stain", st1 < 0.01,
                f"목 · 뒤통수 아래 · 옷깃 그림 칸 {allm.sum()} 개 — 빨강 · 흰 얼룩 {st0*100:.1f} → {st1*100:.1f} % (< 1 %) · 칠한 살색 {tuple(round(float(v), 2) for v in base)} · 옷 색 {tuple(round(float(v), 2) for v in jbase)}")
        B.check(fails, "fix_hair_patch", br1 < 0.02,
                f"뒤통수 아래 그림 칸 {hmask.sum()} 개 — 밝은 조각 {br0*100:.1f} → {br1*100:.1f} % (< 2 %) · 머리카락 색 {tuple(round(float(v), 3) for v in hbase)}")
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
else:
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
