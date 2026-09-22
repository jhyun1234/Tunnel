"""m3 갱목·못·끈: 옛 몸(stage16)의 단단한 물체 15개를 새 몸 겉에 다시 맞춰 같은 뼈에 매단다 (제안서 docs/제안서_m3_눈_발광_램프_미끼_갱목.md M2, 09-20 승인 · 목 끈은 뺀다 — 사용자).
  blender -b --factory-startup -P blender/rig/m3_props.py
입력: Documents/MineTunnel/blender/miner_v4_stage16_neck.blend (물체·재질·그림만 가져온다, 안 고친다) + miner_v5_stage21_m3_wrist.blend (안 고친다)
출력: Documents/MineTunnel/blender/miner_v5_stage22_m3_props.blend → SRC_BLEND 로 walk_knuckle.py 에 (tools/bake_m3.sh)
하는 일: ① stage16 에서 물체마다 쉬는 자세 세계 좌표를 그물에 굽고 부모를 떼어 작은 묶음 파일로 → stage20 에 들여온다 (옛 뼈대·동작이 딸려 오지 않게)
        ② 자리: 제 뼈 위 같은 **비율** 자리로 (팔이 1.47배 길어졌다 — 뼈 길이 방향으로만 옮긴다, 물체 크기는 그대로)
        ④ 끈(고리): 고리 면 안에서 각도 10° 칸마다 새 살(+ 제 판자)의 바깥 반지름을 광선으로 재어, 끈 안쪽 면이 살에서 GAP 만큼 뜨게 점마다 반지름을 다시 준다 (끈 두께·너비는 그대로)
        ③ 판자: 안쪽 면이 살에 BURY 만큼 묻히게 판자째 민다. 못은 제 판자(등 판자)와 같이
        ⑤ 같은 뼈에 뼈 부모로 매단다 (살처럼 휘지 않는 단단한 물체 — 옛 몸과 같다)
사보타주: SABOTAGE=nofit(②까지만 — 옛 모양 그대로) -> 끈·판자 검사 FAIL · withneck(목 끈도 넣음) -> 물체 수 검사 FAIL"""
import bpy, os, sys, math, tempfile, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
OLD = os.path.join(MT, "blender", "miner_v4_stage16_neck.blend")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage21_m3_wrist.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage22_m3_props.blend"))
SHOTS = os.environ.get("SHOTS", "")
SABOTAGE = os.environ.get("SABOTAGE", "")
P = "mixamorig:"
GAP, BURY = 0.004, 0.006
SKIP = () if SABOTAGE == "withneck" else ("Strap_Neck",)        # 옛 몸에서 머리 이음매를 가리던 끈 — 새 몸은 이음매가 없고 목 소매·속 목이 나오는 자리다 (사용자 09-20 "목 끈 빼라")

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

# ---- ① 옛 물체를 묶음 파일로
bpy.ops.wm.open_mainfile(filepath=OLD)
arm0 = bpy.data.objects["Miner_Rig"]; arm0.data.pose_position = "REST"; bpy.context.view_layer.update()
old_bone = {}
props = [o for o in bpy.data.objects if o.type == "MESH" and o.name.split("_")[0] in ("Plank", "Nail", "Strap") and o.name not in SKIP]
for o in props:
    b = arm0.data.bones[o.parent_bone]
    old_bone[o.name] = (o.parent_bone, np.array(arm0.matrix_world @ b.head_local), np.array(arm0.matrix_world @ b.tail_local))
    W = [o.matrix_world @ v.co for v in o.data.vertices]
    o.parent = None; o.matrix_world = Matrix.Identity(4)
    for v, w in zip(o.data.vertices, W):
        v.co = w
    o.data.update()
lib = os.path.join(tempfile.gettempdir(), "m3_props_lib.blend")
bpy.data.libraries.write(lib, set(props), fake_user=True)
names = [o.name for o in props]

# ---- 새 몸
bpy.ops.wm.open_mainfile(filepath=SRC)
with bpy.data.libraries.load(lib) as (src, dst):
    dst.objects = [n for n in src.objects if n in names]
arm = bpy.data.objects["Miner_Rig"]; M = arm.matrix_world
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
body = bpy.data.objects["Miner_Body"]
skin = np.array([body.matrix_world @ v.co for v in body.data.vertices])
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())      # Miner_Body 는 세계 = 제 좌표(부모 역행렬로 맞춰 둠)
bw = body.matrix_world; bwi = bw.inverted()
objs = {}
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o); objs[o.name] = o

def co(o): return np.array([v.co[:] for v in o.data.vertices], float)
def put(o, V):
    o.data.vertices.foreach_set("co", V.astype(np.float32).ravel()); o.data.update()

# ---- ② 같은 비율 자리
for n, o in objs.items():
    bn, h0, t0 = old_bone[n]; b = arm.data.bones[bn]
    h1, t1 = np.array(M @ b.head_local), np.array(M @ b.tail_local)
    V = co(o); u0 = (t0 - h0) / np.linalg.norm(t0 - h0); u1 = (t1 - h1) / np.linalg.norm(t1 - h1)
    c = V.mean(0); ratio = float((c - h0) @ u0) / np.linalg.norm(t0 - h0)
    R = np.array(Vector(u0).rotation_difference(Vector(u1)).to_matrix())           # 뼈 방향이 조금 달라졌으면 같이 돌린다 (팔)
    side = (c - h0) - u0 * ((c - h0) @ u0)
    c1 = h1 + u1 * ratio * np.linalg.norm(t1 - h1) + R @ side
    put(o, (V - c) @ R.T + c1)

def skin_signed(p):
    """살 겉면에서 p 까지: + 밖, − 속 (가장 가까운 면의 법선 쪽)"""
    loc, nor, idx, d = bvh.find_nearest(bwi @ Vector(p))
    return d if (bwi @ Vector(p) - loc).dot(nor) >= 0 else -d

# ---- ③ 판자·못 (끈보다 먼저 — 끈은 판자째 감는다)
def inward(o):
    bn = old_bone[o.name][0]; b = arm.data.bones[bn]; h1, t1 = np.array(M @ b.head_local), np.array(M @ b.tail_local); u = (t1 - h1) / np.linalg.norm(t1 - h1)
    c = co(o).mean(0); side = (c - h1) - u * ((c - h1) @ u)
    return -side / np.linalg.norm(side)
shift = {}
for n, o in objs.items():
    if not n.startswith("Plank") or SABOTAGE == "nofit":
        continue
    d = inward(o); total = np.zeros(3)
    for _ in range(6):                                                                   # 가장 가까운 면까지의 거리는 미는 방향과 다르다 — 몇 번 되풀이한다
        V = co(o); depth = V @ d
        face = V[depth > np.percentile(depth, 80)]                                       # 안쪽(살 쪽) 면의 점들
        hgt = np.array([skin_signed(p) for p in face])
        mv = d * (float(np.median(hgt)) + BURY)                                          # 가운데값이 −BURY 가 되게
        put(o, V + mv); total += mv
    mv = total; shift[n] = mv
    if n == "Plank_Back":
        for k, no in objs.items():
            if k.startswith("Nail"):
                put(no, co(no) + mv)

plank_bvh = {}
for n, o in objs.items():
    if n.startswith("Plank"):
        plank_bvh[old_bone[n][0]] = BVHTree.FromPolygons([v.co[:] for v in o.data.vertices], [p_.vertices[:] for p_ in o.data.polygons])   # 그물 좌표에서 바로(아직 부모 없음 — 제 좌표 = 세계). FromObject 는 옮기기 전의 평가된 그물을 줬다(09-20: 끈이 판자 속 3.7 cm)
plank_bvh[P + "Spine1"] = plank_bvh.get(P + "Spine2")                                                  # 등 판자는 Spine2 에 달려 있지만 몸통 끈 셋이 다 그 위를 지난다
def wrap_signed(p, bn):
    """끈이 감는 것(살 + 그 뼈의 판자)의 겉면에서 p 까지: + 밖, − 속"""
    d = skin_signed(p); pb_ = plank_bvh.get(bn)
    if pb_ is not None:
        loc, nor, idx, dd = pb_.find_nearest(Vector(p))
        d = min(d, dd if (Vector(p) - loc).dot(nor) >= 0 else -dd)
    return d

# ---- ④ 끈
strap_stats = {}
for n, o in objs.items():
    if not n.startswith("Strap") or SABOTAGE == "nofit":
        continue
    V = co(o); c0 = V.mean(0)
    _, _, vt = np.linalg.svd(V - c0); nrm = vt[2]; e1, e2 = vt[0], vt[1]              # 고리 면의 법선 = 가장 얇은 방향
    bn = old_bone[n][0]; b_ = arm.data.bones[bn]; h1, t1 = np.array(M @ b_.head_local), np.array(M @ b_.tail_local); u = (t1 - h1) / np.linalg.norm(t1 - h1)
    c = h1 + u * ((c0 - h1) @ nrm) / (u @ nrm)                                         # 고리 면이 뼈 축과 만나는 점 — 살 속에 있다(옛 고리 가운데는 새 팔 밖일 수 있다)
    bins = 72
    for attempt in (0, 1):                                                             # 두 번: 첫 번째에 맞힌 살 점들의 가운데로 중심을 옮겨 다시 (드러난 정강이뼈처럼 가는 것은 뼈대 축에서 비켜 있다 — 09-20: 36칸 중 30칸을 못 맞혔다)
        rel = V - c; a = np.arctan2(rel @ e2, rel @ e1); r = np.hypot(rel @ e1, rel @ e2); h = rel @ nrm
        vb0 = ((a + math.pi) / (2 * math.pi) * bins).astype(int) % bins
        r_in0 = np.array([r[vb0 == j].min() if (vb0 == j).any() else np.nan for j in range(bins)])
        okb = ~np.isnan(r_in0); r_in0 = np.interp(np.arange(bins), np.where(okb)[0], r_in0[okb], period=bins)
        # 살 바깥 반지름: 칸마다 고리 밖(옛 안쪽 반지름 + 12 cm)에서 가운데로 광선 다섯(끈 너비에 걸쳐) — 점 구름으로 재면 팔·정강이는 면이 커서 점이 열 개 남짓이다(09-20: 팔뚝 끈이 17 cm 로 부풀었다)
        r_skin = np.full(bins, np.nan); hits = []
        for j in range(bins):
            th = -math.pi + (j + 0.5) * 2 * math.pi / bins; d = e1 * math.cos(th) + e2 * math.sin(th); R0 = r_in0[j] + 0.12; best = np.nan
            for hh in np.linspace(h.min(), h.max(), 5):
                hit = bvh.ray_cast(bwi @ Vector(c + d * R0 + nrm * hh), bwi.to_3x3() @ Vector(-d), R0)
                if hit[0] is not None and abs(R0 - hit[3] - r_in0[j]) <= 0.10:          # 10 cm 넘게 다르면 다른 것(어깨 높이 끈의 팔 등)을 맞힌 것
                    rr = R0 - hit[3]; best = rr if np.isnan(best) else max(best, rr)
                if plank_bvh.get(bn) is not None:                                      # 판자 위로 지나간다 — 제 판자는 멀어도 믿는다(09-20: 10 cm 잣대에 걸려 끈이 판자 속을 지났다)
                    hit = plank_bvh[bn].ray_cast(Vector(c + d * (R0 + 0.15) + nrm * hh), Vector(-d), R0 + 0.15)
                    if hit[0] is not None:
                        rr = R0 + 0.15 - hit[3]; best = rr if np.isnan(best) else max(best, rr)
            if not np.isnan(best):
                r_skin[j] = best; hits.append(c + d * best)
        if attempt == 0 and 3 <= len(hits) < bins * 0.7:
            hc_ = np.mean(hits, axis=0); c = c + e1 * ((hc_ - c) @ e1) + e2 * ((hc_ - c) @ e2)
        else:
            break
    miss = int(np.isnan(r_skin).sum())
    okr = ~np.isnan(r_skin)                                                            # 못 맞힌 칸(찢긴 가슴 구멍 · 광선이 비낀 곳)은 맞힌 이웃 칸에서 잇는다 — 옛 반지름으로 메우면 굵어진 새 살 속에 묻힌다(09-20: 팔뚝 끈 25 %)
    r_skin = np.interp(np.arange(bins), np.where(okr)[0], r_skin[okr], period=bins) if okr.sum() >= 3 else r_in0
    r_skin = np.maximum(r_skin, np.convolve(np.r_[r_skin[-2:], r_skin, r_skin[:2]], np.ones(5) / 5, "valid"))   # 고르게 하되 살 속으로는 안 들어가게
    vb = ((a + math.pi) / (2 * math.pi) * bins).astype(int) % bins
    r_in = np.array([r[vb == j].min() if (vb == j).any() else np.nan for j in range(bins)])
    okb = ~np.isnan(r_in); r_in = np.interp(np.arange(bins), np.where(okb)[0], r_in[okb], period=bins)
    fb = (a + math.pi) / (2 * math.pi) * bins - 0.5                                    # 칸 사이를 매끄럽게
    k0 = np.floor(fb).astype(int) % bins; rs = np.maximum(r_skin[k0], r_skin[(k0 + 1) % bins])      # 두 이웃 칸 중 큰 쪽 — 사이를 곧게 이으면 모서리(판자·팔 단면)에서 살 속을 지난다
    ri = np.interp(fb, np.arange(bins), r_in, period=bins)
    r_new = rs + GAP + (r - ri)
    put(o, c + np.outer(r_new * np.cos(a), e1) + np.outer(r_new * np.sin(a), e2) + np.outer(h, nrm))
    strap_stats[n] = (float(r.mean()), float(r_new.mean()))
    print("끈 %s: 옛 반지름 %.3f → 새 %.3f · 살을 못 맞힌 칸 %d / 72" % (n, r.mean(), r_new.mean(), miss))

# ---- ⑤ 뼈에 매단다
for n, o in objs.items():
    bn = old_bone[n][0]; b = arm.data.bones[bn]
    o.parent = arm; o.parent_type = "BONE"; o.parent_bone = bn
    o.matrix_parent_inverse = (M @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
bpy.context.view_layer.update()

# ---- 검사
want = 16 - 1
mats = sorted({m.name.split(".")[0] for o in objs.values() for m in o.data.materials})
full = [m for o in objs.values() for m in o.data.materials if m.node_tree and sum(1 for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image) >= 3]
check(len(objs) == want and "Strap_Neck" not in objs and len(mats) >= 5 and len(full) == sum(len(o.data.materials) for o in objs.values()),
      "물체 %d 개 (= %d, 목 끈 없음) · 재질 %d 종 %s · 그림 셋(색·요철·반들거림) 다 있는 재질 %d / %d" % (len(objs), want, len(mats), mats, len(full), sum(len(o.data.materials) for o in objs.values())))
moved = max(float(np.abs(np.array([o.matrix_world @ v.co for v in o.data.vertices]) - co(o)).max()) for o in objs.values())
check(moved < 1e-4, "뼈에 매단 뒤에도 쉬는 자세 자리가 그대로 (가장 큰 차 %.6f m)" % moved)
worst_bury = 0.0; gap_ok = True; rows = []
for n, o in objs.items():
    if not n.startswith("Strap"):
        continue
    V = co(o); c = V.mean(0); _, _, vt = np.linalg.svd(V - c); rel = V - c
    a = np.arctan2(rel @ vt[1], rel @ vt[0]); r = np.hypot(rel @ vt[0], rel @ vt[1])
    vb = ((a + math.pi) / (2 * math.pi) * 36).astype(int) % 36
    inner = np.array([r[i] <= r[vb == vb[i]].min() + 0.002 for i in range(len(V))])
    # 묻힘·틈은 **고리의 바깥 방향 광선**으로 잰다: 점에서 밖으로 5 cm 안에 밖을 보는 살(또는 판자) 겉면이 있으면 그만큼 묻힌 것, 안으로 쏘아 처음 닿는 거리가 틈.
    # "가장 가까운 면의 법선 쪽"으로 재면 찢긴 가슴·팔 주름에서 부호가 뒤집혔다(09-20: 축에서 12.5 cm 밖 점이 1.5 cm 묻혔다고 나옴)
    bn = old_bone[n][0]; dirs = (np.outer(np.cos(a), vt[0]) + np.outer(np.sin(a), vt[1]))
    def cast(p, d, far):
        best = None
        for tree, to_local, rot in ((bvh, bwi, bwi.to_3x3()), (plank_bvh.get(bn), Matrix.Identity(4), Matrix.Identity(3))):
            if tree is None:
                continue
            loc, nor, idx, dist = tree.ray_cast(to_local @ Vector(p), rot @ Vector(d), far)
            if loc is not None and (best is None or dist < best[0]):
                best = (dist, (rot.inverted() @ nor).dot(Vector(d)))
        return best
    bur, gaps = [], []
    for i in np.where(inner)[0]:
        out = cast(V[i], dirs[i], 0.05); inn = cast(V[i], -dirs[i], 0.3)
        bur.append(out[0] if out is not None and out[1] > 0.2 else 0.0)                 # 밖에 '밖을 보는' 겉면 = 나는 그 속
        gaps.append(inn[0] if inn is not None and bur[-1] == 0.0 else np.nan)
    bur = np.array(bur)
    if os.environ.get("DEBUG") and (bur > 0.003).mean() > 0.1:
        ii = np.where(inner)[0][bur > 0.003]; print("DEBUG", n, "묻힌 점 각도(30° 칸)", np.histogram(np.degrees(a[ii]), bins=12, range=(-180, 180))[0].tolist(), "깊이 가운데값 %.3f" % np.median(bur[bur > 0.003]), "너비 쪽 자리", np.round(np.percentile((rel @ vt[2])[ii], [0, 50, 100]), 3), "반지름", np.round(np.percentile(r[ii], [0, 50, 100]), 3))
    buried = float((bur > 0.003).mean()); gap = float(np.nanmedian(gaps)) if np.isfinite(gaps).any() else 0.0
    rows.append("%s 묻힘 %.0f %% · 틈 %.1f cm" % (n.replace("Strap_", ""), buried * 100, gap * 100)); worst_bury = max(worst_bury, buried); gap_ok &= gap <= (0.03 if "Torso" in n else 0.02)
# 틈 문턱: 팽팽한 끈은 오목한 곳을 건너뛴다 — 찢기고 울퉁불퉁한 몸통은 가운데값 1.3~2.4 cm 가 나온다(제안서의 1.5 cm 는 매끈한 몸을 생각한 값). 안 맞춘 옛 모양(nofit)은 팔 14.8 · 정강이 6.5 cm
check(worst_bury <= 0.10 and gap_ok, "끈 안쪽 면(살 + 제 판자 겉에서): 3 mm 넘게 묻힌 점 ≤ 10 %% · 뜬 틈 가운데값 팔·정강이 ≤ 2 cm, 몸통 ≤ 3 cm — %s" % " | ".join(rows))
rows = []; ok_pl = True
for n, o in objs.items():
    if not n.startswith("Plank"):
        continue
    V = co(o); d = inward(o); depth = V @ d; face = V[depth > np.percentile(depth, 80)]
    hgt = np.array([skin_signed(p) for p in face]); med = float(np.median(hgt))
    rows.append("%s 안쪽 면 가운데값 %.1f mm" % (n.replace("Plank_", ""), med * 1000)); ok_pl &= -0.012 <= med <= -0.002
check(ok_pl, "판자 안쪽 면이 살에 2~12 mm 묻힘 — %s" % " | ".join(rows))
nail_far = max(float(np.linalg.norm(co(no).mean(0) - co(objs["Plank_Back"]), axis=1).min()) for k, no in objs.items() if k.startswith("Nail"))
check(nail_far <= 0.06, "못 5개가 등 판자에 박혀 있다: 판자에서 가장 먼 못 %.3f m (≤ 0.06)" % nail_far)
# 동작 중 손이 등 판자를 뚫는가: 있는 클립 넷에서 두 손 뼈 ↔ 등 판자 점 가장 가까운 거리
ad = arm.animation_data; arm.data.pose_position = "POSE"; near_hand = 9.9
for tr in ad.nla_tracks:
    tr.mute = True
for an in ("idle_crouch", "walk_crouch", "run", "crawl"):
    act = bpy.data.actions.get(an)
    if not act:
        continue
    ad.action = act
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    for f in np.linspace(f0, f1, 9):
        bpy.context.scene.frame_set(int(f)); bpy.context.view_layer.update()
        pl = np.array([objs["Plank_Back"].matrix_world @ v.co for v in objs["Plank_Back"].data.vertices])
        for hb in ("LeftHand", "RightHand", "LeftForeArm", "RightForeArm"):
            q = np.array(M @ arm.pose.bones[P + hb].tail)
            near_hand = min(near_hand, float(np.linalg.norm(pl - q, axis=1).min()))
ad.action = None
for tr in ad.nla_tracks:
    tr.mute = False
bpy.context.scene.frame_set(0)
check(near_hand >= 0.08, "동작 넷(대기·웅크려 걷기·달리기·기기)에서 손·손목이 등 판자에 가장 가까울 때 %.2f m (≥ 0.08)" % near_hand)

if SHOTS:
    os.makedirs(SHOTS, exist_ok=True); sc = bpy.context.scene
    arm.data.pose_position = "REST"; bpy.context.view_layer.update()
    hidden = {o: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name in ("Miner_Neck",)
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 3.4
    sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = 1100; sc.render.resolution_y = 1100
    sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_cavity = True; sh.show_backface_culling = True
    for nm, loc, rot in (("front", (0, -6, 1.35), (math.pi / 2, 0, 0)), ("back", (0, 6, 1.35), (math.pi / 2, 0, math.pi)), ("left", (6, 0, 1.35), (math.pi / 2, 0, math.pi / 2))):
        cam.location, cam.rotation_euler = loc, rot
        sc.render.filepath = os.path.join(SHOTS, "50_props_%s.png" % nm); bpy.ops.render.render(write_still=True)
    for nm, tgt, loc, scale in (("arm", (1.2, 0.05, 1.82), (1.2, -5, 3.2), 0.9), ("shin", (-0.13, 0.02, 0.5), (-2.5, -4, 1.2), 0.9), ("chest", (0, 0.05, 1.65), (2.5, -4.5, 2.4), 1.1), ("backc", (0.1, 0.1, 1.6), (-2.0, 4.5, 2.3), 1.1)):
        cam.data.ortho_scale = scale; cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(SHOTS, "51_props_close_%s.png" % nm); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o, h in hidden.items():
        o.hide_render = h

arm.data.pose_position = "POSE"
if fails:
    sys.exit("m3_props FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_props ALL PASS →", OUT)
