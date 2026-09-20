"""m3 목: 새 몸의 목 살을 머리 쪽 / 몸 쪽으로 가르고, 속 목을 Meshy 로 뽑은 등뼈·근육 기둥(meshy_neck1)으로 바꾼다 (제안서 docs/제안서_m3_목_속_근육.md, 09-20 승인).
  blender -b --factory-startup -P blender/rig/m3_neck.py
입력: Documents/MineTunnel/blender/miner_v5_stage18_m3_fingers.blend (안 고친다) + mesh/meshy_neck1.glb
출력: Documents/MineTunnel/blender/miner_v5_stage19_m3_neck.blend → SRC_BLEND 로 walk_knuckle.py 에 (tools/bake_m3.sh)
하는 일: ① 네 그물(머리·몸·안감·속 몸통)의 걸친 살 점을 한쪽으로, 머리↔몸 잇는 면은 지우지 않고 몸 쪽에 남김 (add_long_neck.py ①② 와 같은 식)
        ② Meshy 목: 밑동 나팔(아래 18 %) 자름 → 곧게 폄(Meshy 가 깊이 쪽으로 휘게 지어냈다) → 길이 83 cm(머리 속 3 + 80) → 등뼈 돌기가 등 쪽을 보게
           목 마디 뼈 길(머리 속 → NeckExt_0~6)에서 새 목 가운데로 비켜 놓음 → 굵기 0.8(사용자 09-20) → 높이에 따라 마디 뼈에 나눠 붙임 + 머리 밑 마개
        ③ 옛 관 Miner_Neck(셈으로 만든 관·소매·마개, m2_body.py 가 0.15배로 줄여 둔 것)은 뺀다. 새 그물이 이름(Miner_Neck)·재질 이름(목_근육)을 물려받는다 — Unity 가 그 이름으로 찾는다
사보타주: SABOTAGE=blend(안 가름) -> 검사 1·2 FAIL · delstraddle(잇는 면 지움) -> 3 FAIL · nofit(굵기 1.0) -> 4 FAIL · bent(안 폄) -> 5 FAIL · flip(면 뒤집음) · nocap(머리 밑 마개 없음) -> 6 FAIL · loose(늘어진 가닥 안 누름) -> 4 FAIL"""
import bpy, bmesh, os, sys, math, numpy as np
from mathutils import Vector, Matrix

MT = os.path.join(os.path.expanduser("~"), "Documents", "MineTunnel")
SRC = os.environ.get("SRC_BLEND", os.path.join(MT, "blender", "miner_v5_stage18_m3_fingers.blend"))
OUT = os.environ.get("OUT_BLEND", os.path.join(MT, "blender", "miner_v5_stage19_m3_neck.blend"))
GLB = os.path.join(MT, "mesh", "meshy_neck1.glb")
SHOTS = os.environ.get("SHOTS", "")
SABOTAGE = os.environ.get("SABOTAGE", "")
P = "mixamorig:"
JOINTS, NECK_LEN, TOP_IN = 7, 0.80, 0.03         # add_long_neck.py · Tuning.STALKER_NECK_* 와 같은 값
LINK = NECK_LEN / JOINTS; TOTAL = TOP_IN + NECK_LEN
CUT = 0.18                                       # 밑동 나팔: 아래 18 % 를 버린다 (09-20 단면 반지름: 아래 10 % 0.17 → 18 % 부터 0.09)
DARK = float(os.environ.get("DARK", "0.45"))     # m2_body.py 가 다른 부위에 곱한 값과 같게 (램프에 하얗게 타지 않게)
OUT_UP = 0.4                                     # Tuning.STALKER_NECK_UP
HEADSIDE = ("Head", "Jaw", "JawTip", "HeadTop_End")

fails = []
def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
arm = bpy.data.objects["Miner_Rig"]; M = arm.matrix_world; Mi = M.inverted()
skins = [bpy.data.objects[n] for n in ("Miner_Head", "Miner_Body", "Miner_Liner", "Miner_Torso")]
ad = arm.animation_data; ad.action = None
for tr in ad.nla_tracks:
    tr.mute = True
arm.data.pose_position = "POSE"
def reset_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
def eval_co(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    V = np.array([o.matrix_world @ v.co for v in me.vertices]); ev.to_mesh_clear(); return V
reset_pose()
before = {o.name: eval_co(o) for o in skins}
faces_before = {o.name: len(o.data.polygons) for o in skins}

# ---- ① 가르기
ring_head = []                                  # 머리 그물에서 잇는 면의 머리 쪽 점 = 머리 밑 구멍 둘레 (마개 크기)
for ob in skins:
    if SABOTAGE == "blend":
        break
    hgs = {ob.vertex_groups[P + n].index for n in HEADSIDE if ob.vertex_groups.get(P + n)}
    to_head, to_body = [], []
    for v in ob.data.vertices:
        wh = sum(g.weight for g in v.groups if g.group in hgs); wb = sum(g.weight for g in v.groups if g.group not in hgs)
        if wh > 1e-6 and wb > 1e-6:
            (to_head if wh >= wb else to_body).append(v.index)
    for vg in ob.vertex_groups:
        vg.remove(to_body if vg.index in hgs else to_head)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    dl = bm.verts.layers.deform.verify()
    side = {v.index: sum(w for g, w in v[dl].items() if g in hgs) >= 0.5 for v in bm.verts}
    bridge = [f for f in bm.faces if len({side[v.index] for v in f.verts}) == 2]
    dup = {}; old_edges = {e for f in bridge for e in f.edges}
    for f in bridge:
        if SABOTAGE == "delstraddle":
            bm.faces.remove(f); continue
        src = min((v for v in f.verts if not side[v.index]), key=lambda v: v.index)      # 이 면의 몸 쪽 점 — 무게를 빌린다
        new_vs = []
        for v in f.verts:
            if side[v.index]:
                if ob.name == "Miner_Head":
                    ring_head.append(np.array(ob.matrix_world @ v.co))
                if v.index not in dup:
                    nv = bm.verts.new(v.co, v); nv[dl].clear()
                    for g, w in src[dl].items():
                        nv[dl][g] = w
                    dup[v.index] = nv
                new_vs.append(dup[v.index])
            else:
                new_vs.append(v)
        try:
            nf = bm.faces.new(new_vs, f)
        except ValueError:
            continue
        for ln, lo in zip(nf.loops, f.loops):
            ln.copy_from(lo)
        bm.faces.remove(f)
    for e in [e for e in old_edges if e.is_valid and e.is_wire]:
        bm.edges.remove(e)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    print("%s: 걸친 살 점 머리 쪽 %d · 몸 쪽 %d · 잇는 면 %d 개를 몸 쪽에 남김 (복사한 점 %d)" % (ob.name, len(to_head), len(to_body), len(bridge), len(dup)))

# ---- 길: 머리 속 꼭대기 → 목 마디 뼈 7개 → 그 아래로 곧게 (뼈는 add_long_neck.py 가 등뼈 길 위에 놓았다)
def rest_path():
    hb = arm.data.bones[P + "Head"]; up = (M.to_3x3() @ (hb.tail_local - hb.head_local)).normalized()
    pts = [M @ hb.head_local + up * TOP_IN] + [M @ arm.data.bones[P + "NeckExt_%d" % i].head_local for i in range(JOINTS)]
    pts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * (LINK + 0.05))
    return pts
def sampler(pts):
    seg = np.array([(b - a).length for a, b in zip(pts[:-1], pts[1:])]); cum = np.concatenate([[0], np.cumsum(seg)]); A = np.array(pts)
    def at(s):
        s = np.clip(np.asarray(s, float), 0, cum[-1] - 1e-9); i = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg) - 1)
        f = ((s - cum[i]) / seg[i])[..., None]
        return A[i] * (1 - f) + A[i + 1] * f
    return at
def frames(at, s):
    """길 위 자리 + 옆·등·위 세 축 (등 = 세상 +y 를 길에 수직으로 눕힌 것 — 얼굴이 −y 를 본다)"""
    c = at(s); up = at(s - 0.01) - at(s + 0.01); up /= np.linalg.norm(up, axis=1, keepdims=True)
    back = np.array([0.0, 1.0, 0.0]) - up * up[:, 1:2]; back /= np.linalg.norm(back, axis=1, keepdims=True)
    return c, np.cross(back, up), back, up
bone_s = np.array([TOP_IN + i * LINK for i in range(JOINTS)])

# ---- ② Meshy 목
old = bpy.data.objects["Miner_Neck"]
for m_ in list(old.data.materials):
    m_.name = "old_" + m_.name
old_me = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(old_me)      # 그물 이름 Miner_Neck 을 비운다 — glTF 그물 이름이 된다(walk_knuckle.py 검사)
have = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in have]
neck = next(o for o in new if o.type == "MESH")
bpy.ops.object.select_all(action="DESELECT"); neck.select_set(True); bpy.context.view_layer.objects.active = neck
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in new:
    if o != neck:
        bpy.data.objects.remove(o, do_unlink=True)
bm = bmesh.new(); bm.from_mesh(neck.data)
zs = [v.co.z for v in bm.verts]; z_cut = min(zs) + (max(zs) - min(zs)) * CUT
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z_cut), plane_no=(0, 0, 1), clear_inner=True)
if SABOTAGE == "flip":
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bm.to_mesh(neck.data); bm.free(); neck.data.update()
L = np.array([v.co[:] for v in neck.data.vertices], float)
z_top, z_bot = L[:, 2].max(), L[:, 2].min(); k = TOTAL / (z_top - z_bot)
bins = np.linspace(z_bot, z_top, 41); mid = (bins[:-1] + bins[1:]) / 2
cen = np.array([L[(L[:, 2] >= a) & (L[:, 2] <= b)][:, :2].mean(0) for a, b in zip(bins[:-1], bins[1:])])
cen = np.stack([np.convolve(np.pad(cen[:, i], 2, mode="edge"), np.ones(5) / 5, "valid") for i in range(2)], 1)
lean = float(np.linalg.norm(cen - cen.mean(0), axis=1).max()) * k
if SABOTAGE != "bent":
    L[:, 0] -= np.interp(L[:, 2], mid, cen[:, 0]); L[:, 1] -= np.interp(L[:, 2], mid, cen[:, 1])
else:
    L[:, :2] -= cen.mean(0)
s_v = (z_top - L[:, 2]) * k                                   # 꼭대기에서 잰 길이 (m)
u_v, b_v = -L[:, 0] * k, -L[:, 1] * k                         # 180° 돌림: 뽑힌 그물은 등뼈 돌기가 −y(앞)를 본다 → 등 쪽으로
# 허공에 늘어진 힘줄 가닥(반지름이 기둥의 두 배까지)을 기둥 겉에 눌러 붙인다 — 굵기 0.8 에서 삐져나온 점 1.64 → 1.32 % (09-20 실측; 큰 원인은 아니다):
# 높이 칸마다 평균 반지름의 STRAND 배를 넘는 점은 그 반지름으로 당긴다 (가닥 모양·그림은 남고 뜬 것만 없어진다). SABOTAGE=loose 로 끈다
STRAND = float(os.environ.get("STRAND", "1.4"))
r_v = np.hypot(u_v, b_v); kbin = np.clip((s_v / TOTAL * 40).astype(int), 0, 39)
r_mean = np.array([r_v[kbin == j].mean() for j in range(40)]); lim = np.interp(s_v, (np.arange(40) + 0.5) * TOTAL / 40, r_mean) * STRAND
pull = np.where((r_v > lim) & (SABOTAGE != "loose"), lim / np.maximum(r_v, 1e-9), 1.0); pressed = int((pull < 1).sum())
u_v, b_v = u_v * pull, b_v * pull
print("늘어진 가닥: 눌러 붙인 점 %d / %d" % (pressed, len(L)))
print("Meshy 목: 점 %d · 면 %d · 자른 뒤 길이 %.3f → %.2f m (%.3f배) · 펴기 전 기울어짐 %.3f m · 반지름 평균 %.3f 최대 %.3f m (굵기 1.0 일 때)"
      % (len(L), len(neck.data.polygons), z_top - z_bot, TOTAL, k, lean, float(np.hypot(u_v, b_v).mean()), float(np.hypot(u_v, b_v).max())))

at0 = sampler(rest_path())
# 옛 뼈대의 목 길은 새 몸의 목·몸통 가운데보다 4~7 cm 앞에 있다(09-20: 길 위에 그대로 놓으니 굵기와 상관없이 13 % 가 목 앞·갈비 사이로 보였다).
# 뼈는 그대로 두고 **그물만** 길에서 비켜 놓는다 — 높이마다 둘레 살 점(위쪽은 반지름 12 cm 안 = 새 목, 아래는 30 cm 안 = 몸통)의 가운데로. 뼈에 붙은 채라 뺄 때도 그 간격으로 따라 나온다
cloud = np.concatenate([eval_co(o) for o in skins])
s_k = np.linspace(0, TOTAL, 42); ck, ek_side, ek_back, ek_up = frames(at0, s_k); off_k = np.zeros((len(s_k), 2))
for j in range(len(s_k)):
    rel = cloud - ck[j]; h = rel @ ek_up[j]; a, b = rel @ ek_side[j], rel @ ek_back[j]
    m = (np.abs(h) < 0.02) & (np.hypot(a, b) < (0.12 if s_k[j] < 0.20 else 0.30))
    if m.sum() >= 30:
        off_k[j] = a[m].mean(), b[m].mean()
off_k = np.stack([np.convolve(np.pad(off_k[:, i], 3, mode="edge"), np.ones(7) / 7, "valid") for i in range(2)], 1)
if SABOTAGE == "onpath":
    off_k[:] = 0
print("그물을 길에서 비켜 놓는 거리 (옆, 등 쪽) m — 꼭대기 %s · 20 cm %s · 40 cm %s · 80 cm %s" % tuple(off_k[j].round(3) for j in (0, 10, 20, 40)))
def place(fit):
    c, e_side, e_back, e_up = frames(at0, s_v)
    c = c + e_side * np.interp(s_v, s_k, off_k[:, 0])[:, None] + e_back * np.interp(s_v, s_k, off_k[:, 1])[:, None]
    Wd = c + e_side * (u_v * fit)[:, None] + e_back * (b_v * fit)[:, None]
    neck.data.vertices.foreach_set("co", Wd.astype(np.float32).ravel()); neck.data.update()
    return Wd
mat = neck.data.materials[0]; mat.name = "목_근육"; mat.use_backface_culling = True
bs = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
if bs.inputs["Base Color"].links:                             # 색만 곱한다 — glTF 내보내기가 baseColorFactor 로 옮긴다 (m2_body.py 와 같은 식)
    lk = bs.inputs["Base Color"].links[0]; nt = mat.node_tree
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
    nt.links.new(lk.from_socket, mix.inputs[6]); mix.inputs[7].default_value = (DARK, DARK, DARK, 1); nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
neck.name = "Miner_Neck"; neck.data.name = "Miner_Neck"

# 굵기: 안 뺐을 때 밖(여덟 방향, 가슴~머리 높이 둘)에서 속 목이 보이는 점이 0.5 % 아래인 가장 큰 배율
rng = np.random.default_rng(3); pick = rng.choice(len(L), 2500, replace=False)
cams = [Vector((3 * math.cos(a), 3 * math.sin(a) + 0.07, z)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False) for z in (1.6, 2.2)]
# 새 몸은 가슴·목 살이 일부러 찢겨 있어(갈비·힘줄이 보인다) 속 목이 그 구멍으로 비치는 것은 굵기로 못 막는다(09-20: 굵기 0.3 에서도 12 %).
# 그래서 둘로 나눠 잰다 — **삐져나옴**: 밖에서 보이고, 여섯 방향 중 하나라도 살에 안 막힌 점(살 겉면 밖으로 나온 것) → 굵기는 이것으로 정한다 · **비침**: 보이지만 살 속(구멍으로 보임) → 숫자만 기록, 판정 몫
DIRS6 = [Vector(d).normalized() for d in ((1, .013, .007), (-1, .013, .007), (.013, 1, .007), (.013, -1, .007), (.013, .007, 1), (.013, .007, -1))]
def enclosed(dg, p):
    for d in DIRS6:
        o = p.copy(); hit = False
        for _ in range(20):
            ok, loc, nor, idx, ob, mt = scene.ray_cast(dg, o, d)
            if not ok:
                break
            if ob.name != "Miner_Neck":
                hit = True; break
            o = loc + d * 1e-4
        if not hit:
            return False
    return True
def seen(Wd):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); poke = peek = 0
    for i in pick:
        p = Vector(Wd[i])
        for c in cams:
            ok, loc, nor, idx, ob, mt = scene.ray_cast(dg, c, (p - c).normalized())
            if ok and ob.name == "Miner_Neck" and (loc - p).length < 0.006:
                if enclosed(dg, p): peek += 1
                else: poke += 1
                break
    return poke / len(pick), peek / len(pick)
# 굵기 0.8 · 삐져나옴 ≤ 1.5 % = 사용자 09-20 A안 (1.0 → 3.0 % · 0.8 → 1.3 % · 0.6 → 0.9 % · 0.4 → 0.5 %; 0.8 이면 속 목 반지름 3.2 cm 로 새 목 살 3.5~4.4 cm 안). 속 목이 새 목 살 안에 들어가는 굵기
fit = 1.0 if SABOTAGE == "nofit" else float(os.environ.get("FIT", "0.8"))
Wd = place(fit); vis, peek = seen(Wd)
print("굵기 %.2f: 살 밖으로 삐져나온 속 목 점 %.2f %% · 살 구멍으로 비치는 점 %.2f %%" % (fit, vis * 100, peek * 100))

# 머리 밑 마개: 목을 빼고 밑에서 올려다보면 머리 밑 구멍과 속 목 사이로 머리 속이 보인다(굵기 1.0 에서 광선 192 중 11) → 구멍 2 cm 위(머리 속)에 아래를 보는 원판, 머리 뼈에 붙음.
# 그림은 속 목 그림의 한 점(어두운 근육색)을 쓴다 — 옛 관의 마개와 같은 구실
n_col = len(L)
if ring_head and SABOTAGE != "nocap":
    rh = np.array(ring_head); hc = rh.mean(0); hr = float(np.percentile(np.linalg.norm((rh - hc)[:, :2], axis=1), 90))
    bm = bmesh.new(); bm.from_mesh(neck.data); uvl = bm.loops.layers.uv.verify()
    cv = bm.verts.new((hc[0], hc[1], hc[2] + 0.02)); rim = [bm.verts.new((hc[0] + hr * 1.3 * math.cos(a), hc[1] + hr * 1.3 * math.sin(a), hc[2] + 0.02)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    for a_, b_ in zip(rim, rim[1:] + rim[:1]):
        f_ = bm.faces.new((cv, b_, a_))                       # 아래(−z)를 본다
        for lp in f_.loops:
            lp[uvl].uv = (0.5, 0.5)
    bm.to_mesh(neck.data); bm.free(); neck.data.update()
    print("머리 밑 마개: 구멍 가운데 %s · 반지름 %.3f m × 1.3" % (hc.round(3), hr))
else:
    hc = np.array(rest_path()[1]); hr = 0.05
n_all = len(neck.data.vertices)

# 무게: 꼭대기 3 cm 는 머리 뼈, 그 아래는 이웃 두 마디 뼈 사이를 길이로 나눔
for vg in list(neck.vertex_groups):
    neck.vertex_groups.remove(vg)
names = [P + "Head"] + [P + "NeckExt_%d" % i for i in range(JOINTS)]
Wt = np.zeros((n_all, len(names))); Wt[n_col:, 0] = 1
t = np.clip((s_v - TOP_IN) / LINK, 0, JOINTS - 1); i0 = np.floor(t).astype(int); i1 = np.minimum(i0 + 1, JOINTS - 1); f = t - i0
Wt[np.arange(n_col), 1 + i0] += 1 - f; Wt[np.arange(n_col), 1 + i1] += f
top = np.where(s_v < TOP_IN)[0]; Wt[top] = 0; Wt[top, 0] = 1
for c_, n_ in enumerate(names):
    g = neck.vertex_groups.new(name=n_); w = Wt[:, c_].round(3)
    for val in np.unique(w[w > 0]):
        g.add([int(i) for i in np.where(w == val)[0]], float(val), "REPLACE")
neck.parent = arm; neck.matrix_parent_inverse = M.inverted()
neck.modifiers.new("Armature", "ARMATURE").object = arm
bpy.context.view_layer.update()

# ---- 자세: Unity StalkerAnim.NeckOut 흉내 — 머리 뼈를 (얼굴 쪽 + 위 0.4) 로 밀고, 마디 뼈를 새 길(밀린 꼭대기 → 밀린 머리 → 쉬는 길) 위 같은 길이 자리에
def pose(ext, up_only=False):
    reset_pose()
    if ext <= 0:
        return
    d = Vector((0, 0, 1)) if up_only else Vector((0, -1, OUT_UP)).normalized()
    hb = arm.pose.bones[P + "Head"]; hb.matrix = Mi @ (Matrix.Translation(d * ext) @ (M @ hb.matrix)); bpy.context.view_layer.update()
    rp = rest_path(); at1 = sampler([rp[0] + d * ext, rp[0] + d * ext * 0.5] + rp[1:])     # 꼭대기에서 곧게 내려와 쉬는 길로
    for i in range(JOINTS):                                   # 자리 + 돌림(쉬는 길의 방향 → 새 길의 방향) — 돌림을 빼먹으면 단면이 누운 채 끌려가 목이 납작해 보인다
        pb = arm.pose.bones[P + "NeckExt_%d" % i]; Wm = M @ pb.matrix; cur = Wm.translation; si = bone_s[i]
        t0 = Vector(at0(si - 0.02) - at0(si + 0.02)); t1 = Vector(at1(si - 0.02) - at1(si + 0.02))
        R = t0.rotation_difference(t1).to_matrix().to_4x4()
        pb.matrix = Mi @ (Matrix.Translation(Vector(at1(si))) @ R @ Matrix.Translation(-cur) @ Wm)
    bpy.context.view_layer.update()

# ---- 검사
mixed = {}
for ob in skins:
    hgs = {ob.vertex_groups[P + n].index for n in HEADSIDE if ob.vertex_groups.get(P + n)}
    mixed[ob.name] = sum(1 for v in ob.data.vertices if 0.01 < sum(g.weight for g in v.groups if g.group in hgs) < 0.99)
check(sum(mixed.values()) == 0, "머리 뼈에 걸친 살 점 0: %s" % mixed)
grow = 0.0
for ob in skins:
    ed = np.array(sorted({e for p_ in ob.data.polygons for e in p_.edge_keys})); c0 = eval_co(ob)
    pose(0.30); c1 = eval_co(ob); reset_pose()
    grow = max(grow, float((np.linalg.norm(c1[ed[:, 0]] - c1[ed[:, 1]], axis=1) - np.linalg.norm(c0[ed[:, 0]] - c0[ed[:, 1]], axis=1)).max()))
check(grow <= 0.015, "머리를 30 cm 밀어도 살이 안 늘어난다: 가장 많이 늘어난 변 +%.4f m (≤ 0.015)" % grow)
after = {o.name: eval_co(o) for o in skins}
d0 = max(float(np.abs(after[n][:len(before[n])] - before[n]).max()) for n in before)
lost = {o.name: faces_before[o.name] - len(o.data.polygons) for o in skins if len(o.data.polygons) < faces_before[o.name]}
check(d0 < 1e-4 and not lost, "쉬는 자세의 살 점이 그대로 (최대 차 %.6f m < 0.0001) · 없어진 면 %s" % (d0, lost or 0))
check(vis <= 0.015 and fit >= 0.6, "안 뺐을 때 살 밖으로 삐져나온 속 목 점 %.2f %% (≤ 1.5) · 굵기 배율 %.2f (≥ 0.6) · 찢긴 살 구멍으로 비치는 점 %.2f %% (기록만 — 판정 몫)" % (vis * 100, fit, peek * 100))
reset_pose(); Wd = eval_co(neck)[:n_col]
c, e_side, e_back, e_up = frames(at0, s_v)
c = c + e_side * np.interp(s_v, s_k, off_k[:, 0])[:, None] + e_back * np.interp(s_v, s_k, off_k[:, 1])[:, None]; rel = Wd - c
off = []
for a, b in zip(np.linspace(0, TOTAL, 41)[:-1], np.linspace(0, TOTAL, 41)[1:]):
    m = (s_v >= a) & (s_v <= b)
    off.append(np.hypot((rel[m] * e_side[m]).sum(1).mean(), (rel[m] * e_back[m]).sum(1).mean()))
rad = np.hypot((rel * e_side).sum(1), (rel * e_back).sum(1))
flare = float(rad[s_v > TOTAL * 0.95].mean() / rad.mean())
check(max(off) <= 0.01 and abs(float(s_v.max()) - TOTAL) <= 0.01 and flare <= 1.5,
      "속 목이 곧다: 높이 칸 40개의 가운데가 길에서 가장 먼 %.4f m (≤ 0.01 — 안 펴면 0.06) · 길이 %.3f m (= %.2f ± 0.01) · 아래 끝 굵기 ÷ 평균 %.2f (≤ 1.5)" % (max(off), float(s_v.max()), TOTAL, flare))
ok_w = all(abs(sum(g.weight for g in v.groups) - 1) < 1e-3 and all(neck.vertex_groups[g.group].name in names for g in v.groups) for v in neck.data.vertices)
outward = 0
col_polys = [p_ for p_ in neck.data.polygons if max(p_.vertices) < n_col]
for poly in col_polys:
    pc = np.array(neck.matrix_world @ poly.center); ax = c[poly.vertices[0]]
    outward += 1 if (neck.matrix_world.to_3x3() @ poly.normal).dot(Vector(pc - ax)) > 0 else 0
out_share = outward / len(col_polys)
# 머리 밑: 머리를 60 cm 위로 밀고 비스듬히 밑 45° 에서 올려다본 광선이 목이나 살 겉면에 막히는가 (add_long_neck.py 와 같은 셈)
pose(0.6, up_only=True); dg = bpy.context.evaluated_depsgraph_get()
cen3 = Vector(hc) + Vector((0, 0, 0.6)); hits = n_ray = 0
for phi in np.linspace(0, 2 * math.pi, 12, endpoint=False):
    o0 = cen3 + Vector((0.35 * math.cos(phi), 0.35 * math.sin(phi), -0.35))
    for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
        for rr in (0.5, 0.85):
            d = (cen3 + Vector((hr * rr * math.cos(a), hr * rr * math.sin(a), 0)) - o0).normalized(); o = o0.copy(); blocked = False
            for _ in range(30):
                ok, loc, nor, idx, ob, mt = scene.ray_cast(dg, o, d)
                if not ok:
                    break
                if ob.name == "Miner_Neck" or nor.dot(d) < 0:
                    blocked = True; break
                o = loc + d * 1e-4
            n_ray += 1; hits += blocked
reset_pose()
check(ok_w and out_share >= 0.6 and hits >= 0.97 * n_ray,
      "속 목 점이 마디 뼈·머리 뼈에만 (무게 합 1: %s) · 겉면이 밖을 보는 면 %.1f %% (≥ 60 — 힘줄 가닥·돌기가 많아 71 쯤, 뒤집으면 29) · 밑에서 올려다본 광선 %d 중 막힌 것 %d (≥ 97 %%)" % (ok_w, out_share * 100, n_ray, hits))

if SHOTS:
    os.makedirs(SHOTS, exist_ok=True)
    keep = ("Miner_Body", "Miner_Head", "Miner_Neck", "Miner_Torso", "Miner_Liner")
    hidden = {o: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.8
    eng = scene.render.engine; scene.render.engine = "BLENDER_WORKBENCH"; scene.render.resolution_x = scene.render.resolution_y = 900
    sh = scene.display.shading; sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_cavity = True; sh.show_backface_culling = True
    for ext in (0.0, 0.15, 0.30):
        pose(ext)
        for nm, loc, rot in (("side", (4, -0.15, 2.15), (math.pi / 2, 0, math.pi / 2)), ("front", (0, -4, 2.15), (math.pi / 2, 0, 0)), ("back", (0, 4, 2.15), (math.pi / 2, 0, math.pi))):
            cam.location, cam.rotation_euler = loc, rot
            scene.render.filepath = os.path.join(SHOTS, "12_neck_after%s_%02dcm_%s.png" % (os.environ.get("TAG", ""), round(ext * 100), nm)); bpy.ops.render.render(write_still=True)
    reset_pose(); scene.render.engine = eng
    bpy.data.objects.remove(cam, do_unlink=True)
    for o, h in hidden.items():
        o.hide_render = h

reset_pose()
for tr in ad.nla_tracks:
    tr.mute = False
if fails:
    sys.exit("m3_neck FAIL %d — 저장 안 함: %s" % (len(fails), fails))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("m3_neck ALL PASS →", OUT)
